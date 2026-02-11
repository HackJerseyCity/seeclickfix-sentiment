"""LLM-based sentiment analysis via Ollama."""

from __future__ import annotations

import json
import re

import httpx

from src.config import OLLAMA_URL, OLLAMA_MODEL as DEFAULT_MODEL


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
        "IMPORTANT FILTERING RULES (apply before analysis):\n"
        "- Ignore auto-generated administrative messages (e.g. 'X assigned this to Y',\n"
        "  'Status changed to ...', 'Issue moved to ...'). These carry no sentiment.\n"
        "- If a thread contains ONLY administrative/auto messages followed by a closure,\n"
        "  rate both interaction and outcome as NEUTRAL.\n"
        "\n"
        "1. INTERACTION quality: How did city staff communicate with residents?\n"
        "   - Focus primarily on threads where RESIDENTS participate. A back-and-forth\n"
        "     between a resident and an official is the strongest signal.\n"
        "   - Threads with only official/auto comments (no resident voices) have very\n"
        "     limited interaction signal — lean toward NEUTRAL unless tone is notable.\n"
        "   - POSITIVE = productive communication that advances the issue. Officials are\n"
        "     responsive, helpful, and use professional language. A polite explanation\n"
        "     of why no action is needed counts as positive.\n"
        "   - NEGATIVE = city officials are confrontational, dismissive, or generally\n"
        "     mean. Includes aggressive or unhelpful language, ignored complaints, or\n"
        "     hostile exchanges.\n"
        "   - ALL-CAPS responses from officials are a negative signal (reads as shouting).\n"
        "\n"
        "2. OUTCOME: Was the reported problem resolved with action?\n"
        "   - POSITIVE = the city took action to address the issue (fixed, repaired,\n"
        "     scheduled work, etc.), ideally confirmed by positive resident feedback.\n"
        "   - NEGATIVE = a closure followed by resident complaints or continued\n"
        "     dissatisfaction. Also negative: 'warnings' or citations issued for\n"
        "     behavior that is objectively problematic (e.g. code violations on\n"
        "     someone's property reported by a neighbor — the warning itself is a\n"
        "     negative outcome for the subject). Also negative: the issue was ignored,\n"
        "     brushed off, or actively disputed.\n"
        "   - NEUTRAL = factual closure (e.g. 'this is county jurisdiction', 'work is\n"
        "     scheduled but not yet done'), in progress, acknowledged but unclear\n"
        "     resolution, or not applicable. A factual statement about why something\n"
        "     can't be done is NOT negative — it is neutral.\n"
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


def analyze_sentiment(
    summary: str,
    status: str,
    comments: list[dict],
    model: str = DEFAULT_MODEL,
) -> dict:
    """Analyze sentiment of an issue thread via Ollama.

    Returns {"interaction": {"label", "confidence", "reasoning"},
             "outcome": {"label", "confidence", "reasoning"}}.
    """
    prompt = build_prompt(summary, status, comments)

    try:
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
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        fallback = {**_NEUTRAL_DIMENSION, "reasoning": f"Ollama request failed: {e}"}
        return {"interaction": fallback, "outcome": dict(fallback)}

    response_text = resp.json().get("response", "")
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


def check_ollama(model: str = DEFAULT_MODEL) -> bool:
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
