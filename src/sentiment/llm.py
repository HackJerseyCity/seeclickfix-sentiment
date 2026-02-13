"""LLM-based sentiment analysis via OpenAI or Ollama."""

from __future__ import annotations

import json
import os
import re

import httpx

from src.config import (
    LLM_BACKEND,
    OLLAMA_URL,
    OLLAMA_MODEL,
    OPENAI_MODEL,
)

DEFAULT_MODEL = OPENAI_MODEL if LLM_BACKEND == "openai" else OLLAMA_MODEL

SYSTEM_PROMPT = (
    "You are a sentiment classifier for city government service requests. "
    "You analyze conversations between residents and city officials. "
    "Respond with ONLY valid JSON, no other text."
)


def build_prompt(summary: str, status: str, comments: list[dict]) -> str:
    """Format the full comment thread for the LLM.

    Each comment dict should have: created_at, commenter_role, commenter_name,
    comment, is_auto_generated.
    """
    lines = [f"Issue: {summary}", f"Status: {status}", "", "Comments (chronological):"]

    for c in comments:
        date = (c.get("created_at") or "")[:10]
        name = c.get("commenter_name") or "Unknown"
        text = c.get("comment") or ""

        if c.get("is_auto_generated"):
            tag = "Auto"
        elif c.get("commenter_role") == "Verified Official":
            tag = "Official"
        else:
            tag = "Resident"

        lines.append(f"  [{date}] [{tag}] {name}: {text}")

    lines.append("")
    lines.append(
        "Analyze this conversation on TWO dimensions.\n"
        "\n"
        "IMPORTANT: All analysis is from the REPORTING USER's perspective.\n"
        "\n"
        "FILTERING RULES (apply before analysis):\n"
        "- Ignore auto-generated administrative messages (e.g. 'X assigned this to Y',\n"
        "  'Status changed to ...', 'Issue moved to ...'). These carry no sentiment.\n"
        "- If a thread contains ONLY official/auto comments with NO resident comments,\n"
        "  rate interaction as NEUTRAL — there is no resident interaction to evaluate.\n"
        "\n"
        "1. INTERACTION quality: How did city staff communicate with residents?\n"
        "   - If there are NO resident comments in the thread, interaction is NEUTRAL.\n"
        "     Officials talking among themselves or posting updates with no resident\n"
        "     response does not count as an interaction.\n"
        "   - POSITIVE = productive back-and-forth between residents and officials.\n"
        "     Officials are responsive, helpful, and professional.\n"
        "   - NEGATIVE = city officials are confrontational, dismissive, or unhelpful.\n"
        "     Includes aggressive language, ignored complaints, or hostile exchanges.\n"
        "   - Repeated follow-ups from residents asking for updates or ETAs with vague\n"
        "     or deflecting responses from officials is a NEGATIVE signal — it means\n"
        "     the resident is not getting a satisfactory answer.\n"
        "   - ALL-CAPS responses from officials are a negative signal (reads as shouting).\n"
        "\n"
        "2. OUTCOME: Was the reported problem resolved, from the REPORTING USER's perspective?\n"
        "   - POSITIVE = the city took action that benefits the reporter: fixed the\n"
        "     problem, issued summons/violations against an offending party, scheduled\n"
        "     repairs, confirmed resolution. Enforcement actions (summons, citations,\n"
        "     violations) are POSITIVE outcomes — the reporter wanted action and got it.\n"
        "   - NEGATIVE = the issue was ignored, brushed off, or closed without action\n"
        "     despite the reporter's dissatisfaction. Resident complaints after closure\n"
        "     are a strong negative signal.\n"
        "   - A long delay between the initial report and final resolution (weeks or\n"
        "     more) is a negative signal for outcome, especially for urgent issues.\n"
        "   - NEUTRAL = factual closure (e.g. 'this is county jurisdiction', 'work is\n"
        "     scheduled but not yet done'), in progress, acknowledged but unclear\n"
        "     resolution, or not enough information to judge.\n"
        "\n"
        "Respond with ONLY valid JSON:\n"
        '{"interaction": {"label": "positive"|"negative"|"neutral"|"mixed", '
        '"confidence": 0.0-1.0, "reasoning": "one sentence"}, '
        '"outcome": {"label": "positive"|"negative"|"neutral"|"mixed", '
        '"confidence": 0.0-1.0, "reasoning": "one sentence"}}'
    )

    return "\n".join(lines)


def _parse_llm_json(text: str) -> dict | None:
    """Extract JSON from LLM response, handling code fences and leading text."""
    # Try to find JSON in code fences first
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find a raw JSON object (greedy to capture nested braces)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _normalize_dimension(data: dict) -> dict:
    """Normalize a single sentiment dimension dict."""
    label = data.get("label", "neutral")
    if label not in ("positive", "negative", "neutral", "mixed"):
        label = "neutral"

    confidence = data.get("confidence", 0.0)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "label": label,
        "confidence": confidence,
        "reasoning": data.get("reasoning", ""),
    }


_NEUTRAL_DIMENSION = {"label": "neutral", "confidence": 0.0, "reasoning": ""}


def _call_openai(prompt: str, model: str) -> str:
    """Call OpenAI API and return the response text."""
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


def _call_ollama(prompt: str, model: str) -> str:
    """Call Ollama API and return the response text."""
    resp = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def analyze_sentiment(
    summary: str,
    status: str,
    comments: list[dict],
    model: str = DEFAULT_MODEL,
) -> dict:
    """Analyze sentiment of an issue thread via LLM.

    Returns {"interaction": {"label", "confidence", "reasoning"},
             "outcome": {"label", "confidence", "reasoning"}}.
    """
    prompt = build_prompt(summary, status, comments)

    try:
        if LLM_BACKEND == "openai":
            response_text = _call_openai(prompt, model)
        else:
            response_text = _call_ollama(prompt, model)
    except Exception as e:
        fallback = {**_NEUTRAL_DIMENSION, "reasoning": f"LLM request failed: {e}"}
        return {"interaction": fallback, "outcome": dict(fallback)}

    parsed = _parse_llm_json(response_text)

    if not parsed:
        fallback = {
            **_NEUTRAL_DIMENSION,
            "reasoning": f"Failed to parse LLM response: {response_text[:200]}",
        }
        return {"interaction": fallback, "outcome": dict(fallback)}

    # Handle new two-dimension format
    if "interaction" in parsed and isinstance(parsed["interaction"], dict):
        interaction = _normalize_dimension(parsed["interaction"])
        outcome = _normalize_dimension(parsed.get("outcome", {}))
        return {"interaction": interaction, "outcome": outcome}

    # Fallback: old single-dimension response — treat as interaction, neutral outcome
    interaction = _normalize_dimension(parsed)
    return {"interaction": interaction, "outcome": dict(_NEUTRAL_DIMENSION)}


def check_ollama(model: str = OLLAMA_MODEL) -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        available = [m.get("name", "") for m in models]
        # Model names may include tag like "llama3.1:8b" or just "llama3.1"
        return any(model in name or name.startswith(model.split(":")[0]) for name in available)
    except (httpx.HTTPError, httpx.TimeoutException):
        return False


def check_openai() -> bool:
    """Check if OpenAI API key is set."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def check_llm() -> bool:
    """Check if the configured LLM backend is available."""
    if LLM_BACKEND == "openai":
        return check_openai()
    return check_ollama()
