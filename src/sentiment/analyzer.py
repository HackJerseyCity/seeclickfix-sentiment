"""Tiered sentiment analysis pipeline: VADER -> RoBERTa."""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.progress import Progress

from src.models.database import get_db
from src.models.schema import SentimentLabel

console = Console()

# Lazy-loaded models
_vader = None
_roberta_pipeline = None


def _get_vader():
    global _vader
    if _vader is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _vader = SentimentIntensityAnalyzer()
    return _vader


def _get_roberta():
    global _roberta_pipeline
    if _roberta_pipeline is None:
        console.print("[cyan]Loading RoBERTa model (first time may take a moment)...[/cyan]")
        from transformers import pipeline
        _roberta_pipeline = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            top_k=None,
            truncation=True,
            max_length=512,
        )
    return _roberta_pipeline


def analyze_vader(text: str) -> dict:
    """Run VADER sentiment analysis. Returns scores dict."""
    vader = _get_vader()
    scores = vader.polarity_scores(text)
    return {
        "vader_compound": scores["compound"],
        "vader_pos": scores["pos"],
        "vader_neg": scores["neg"],
        "vader_neu": scores["neu"],
    }


def analyze_roberta(text: str) -> dict:
    """Run RoBERTa sentiment analysis. Returns scores dict."""
    pipe = _get_roberta()
    results = pipe(text[:512])  # Truncate to model max

    scores = {"roberta_positive": 0.0, "roberta_negative": 0.0, "roberta_neutral": 0.0}
    if results and isinstance(results[0], list):
        for item in results[0]:
            label = item["label"].lower()
            if label in ("positive", "pos"):
                scores["roberta_positive"] = item["score"]
            elif label in ("negative", "neg"):
                scores["roberta_negative"] = item["score"]
            elif label in ("neutral", "neu"):
                scores["roberta_neutral"] = item["score"]

    return scores


def resolve_sentiment(
    vader_scores: dict,
    roberta_scores: Optional[dict] = None,
) -> tuple[SentimentLabel, float, str]:
    """Resolve final sentiment from VADER and optionally RoBERTa scores.

    Returns (label, confidence, resolved_by).
    """
    compound = vader_scores["vader_compound"]

    # Tier 1: VADER clear cases (|compound| > 0.5)
    if abs(compound) > 0.5:
        if compound > 0.5:
            return SentimentLabel.POSITIVE, min(abs(compound), 1.0), "vader"
        else:
            return SentimentLabel.NEGATIVE, min(abs(compound), 1.0), "vader"

    # Tier 2: Use RoBERTa for ambiguous cases
    if roberta_scores:
        pos = roberta_scores.get("roberta_positive", 0)
        neg = roberta_scores.get("roberta_negative", 0)
        neu = roberta_scores.get("roberta_neutral", 0)
        max_score = max(pos, neg, neu)

        if max_score > 0.7:
            if pos == max_score:
                return SentimentLabel.POSITIVE, pos, "roberta"
            elif neg == max_score:
                return SentimentLabel.NEGATIVE, neg, "roberta"
            else:
                return SentimentLabel.NEUTRAL, neu, "roberta"

        # Mixed signal: high pos AND neg
        if pos > 0.3 and neg > 0.3:
            return SentimentLabel.MIXED, max(pos, neg), "roberta"

        # Default to highest RoBERTa score
        if pos >= neg and pos >= neu:
            return SentimentLabel.POSITIVE, pos, "roberta"
        elif neg >= pos and neg >= neu:
            return SentimentLabel.NEGATIVE, neg, "roberta"
        else:
            return SentimentLabel.NEUTRAL, neu, "roberta"

    # VADER-only fallback for ambiguous range
    if compound > 0.05:
        return SentimentLabel.POSITIVE, abs(compound), "vader"
    elif compound < -0.05:
        return SentimentLabel.NEGATIVE, abs(compound), "vader"
    else:
        return SentimentLabel.NEUTRAL, 1.0 - abs(compound), "vader"


def analyze_issues(use_roberta: bool = True, batch_size: int = 50, force: bool = False) -> dict:
    """Run sentiment analysis on full issue conversations.

    For each issue with employee comments, concatenates all non-auto-generated
    comments into one conversation text and analyzes the whole thing.

    Returns stats dict.
    """
    conn = get_db()

    if force:
        conn.execute("DELETE FROM issue_sentiment")
        conn.commit()
        console.print("[yellow]Force mode: cleared all previous sentiment results[/yellow]")

    # Get issues that have Verified Official comments and aren't yet analyzed
    issue_ids = conn.execute(
        """SELECT DISTINCT i.id
           FROM issues i
           JOIN comments c ON c.issue_id = i.id
           WHERE c.commenter_role = 'Verified Official'
           AND i.id NOT IN (SELECT issue_id FROM issue_sentiment)"""
    ).fetchall()

    total = len(issue_ids)
    if total == 0:
        console.print("[yellow]No new issues to analyze[/yellow]")
        conn.close()
        return {"analyzed": 0}

    console.print(f"[cyan]Analyzing {total} issue conversations...[/cyan]")

    stats = {"analyzed": 0, "vader_resolved": 0, "roberta_resolved": 0}

    with Progress() as progress:
        task = progress.add_task("Analyzing sentiment...", total=total)

        for row in issue_ids:
            issue_id = row["id"]

            # Count all non-auto-generated, non-empty comments
            all_comments = conn.execute(
                """SELECT comment FROM comments
                   WHERE issue_id = ? AND is_auto_generated = 0 AND comment != ''
                   ORDER BY created_at""",
                (issue_id,),
            ).fetchall()

            if not all_comments:
                progress.update(task, advance=1)
                continue

            total_comments = len(all_comments)

            # Get resident-only comments (non-official)
            resident_comments = conn.execute(
                """SELECT comment FROM comments
                   WHERE issue_id = ? AND is_auto_generated = 0 AND comment != ''
                   AND commenter_role != 'Verified Official'
                   ORDER BY created_at""",
                (issue_id,),
            ).fetchall()

            resident_comment_count = len(resident_comments)

            if resident_comment_count == 0:
                # Employee-only thread — no resident signal
                conn.execute(
                    """INSERT OR REPLACE INTO issue_sentiment
                       (issue_id, total_comments, text_length, resident_comment_count,
                        vader_compound, vader_pos, vader_neg, vader_neu,
                        roberta_positive, roberta_negative, roberta_neutral,
                        resolved_label, resolved_confidence, resolved_by)
                       VALUES (?, ?, 0, 0, 0, 0, 0, 0, NULL, NULL, NULL, ?, 0, ?)""",
                    (issue_id, total_comments, SentimentLabel.NEUTRAL.value, "no-resident"),
                )
                stats["analyzed"] += 1
                progress.update(task, advance=1)
                continue

            # Analyze ONLY resident text
            conversation_text = "\n".join(c["comment"] for c in resident_comments)
            text_length = len(conversation_text)

            # Tier 1: VADER
            vader_scores = analyze_vader(conversation_text)

            roberta_scores = None
            # Tier 2: RoBERTa for ambiguous VADER results
            if use_roberta and abs(vader_scores["vader_compound"]) <= 0.5:
                roberta_scores = analyze_roberta(conversation_text)

            label, confidence, resolved_by = resolve_sentiment(
                vader_scores, roberta_scores
            )

            if resolved_by == "vader":
                stats["vader_resolved"] += 1
            else:
                stats["roberta_resolved"] += 1

            conn.execute(
                """INSERT OR REPLACE INTO issue_sentiment
                   (issue_id, total_comments, text_length, resident_comment_count,
                    vader_compound, vader_pos, vader_neg, vader_neu,
                    roberta_positive, roberta_negative, roberta_neutral,
                    resolved_label, resolved_confidence, resolved_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    issue_id,
                    total_comments,
                    text_length,
                    resident_comment_count,
                    vader_scores["vader_compound"],
                    vader_scores["vader_pos"],
                    vader_scores["vader_neg"],
                    vader_scores["vader_neu"],
                    roberta_scores["roberta_positive"] if roberta_scores else None,
                    roberta_scores["roberta_negative"] if roberta_scores else None,
                    roberta_scores["roberta_neutral"] if roberta_scores else None,
                    label.value,
                    confidence,
                    resolved_by,
                ),
            )

            stats["analyzed"] += 1
            progress.update(task, advance=1)

            # Commit in batches
            if stats["analyzed"] % batch_size == 0:
                conn.commit()

    conn.commit()
    conn.close()

    console.print(
        f"[green]Analysis complete: {stats['analyzed']} issues analyzed "
        f"({stats['vader_resolved']} by VADER, {stats['roberta_resolved']} by RoBERTa)[/green]"
    )
    return stats


def build_summaries() -> None:
    """Build/rebuild employee and department sentiment summary tables."""
    conn = get_db()

    # Employee summaries — deduplicate first so each (employee, issue) pair
    # is counted exactly once, even if the employee left multiple comments
    conn.execute("DELETE FROM employee_sentiment_summary")
    conn.execute(
        """INSERT INTO employee_sentiment_summary
           (employee_id, total_comments, analyzed_comments,
            positive_count, negative_count, neutral_count, mixed_count,
            avg_vader_compound, avg_roberta_positive, avg_roberta_negative,
            positive_pct, negative_pct)
           SELECT
               e.id,
               e.comment_count,
               COUNT(*),
               SUM(CASE WHEN di.resolved_label = 'positive' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.resolved_label = 'negative' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.resolved_label = 'neutral' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.resolved_label = 'mixed' THEN 1 ELSE 0 END),
               AVG(di.vader_compound),
               AVG(di.roberta_positive),
               AVG(di.roberta_negative),
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.resolved_label = 'positive' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END,
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.resolved_label = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END
           FROM employees e
           JOIN (
               SELECT DISTINCT c.commenter_id, isent.issue_id,
                      isent.resolved_label, isent.vader_compound,
                      isent.roberta_positive, isent.roberta_negative
               FROM comments c
               JOIN issue_sentiment isent ON isent.issue_id = c.issue_id
               WHERE c.is_auto_generated = 0
               AND isent.resolved_by != 'no-resident'
           ) di ON di.commenter_id = e.commenter_id
           GROUP BY e.id"""
    )

    # Department summaries — deduplicate so each (department, issue) pair
    # is counted once, even with multiple employees on the same thread
    conn.execute("DELETE FROM department_sentiment_summary")
    conn.execute(
        """INSERT INTO department_sentiment_summary
           (department_id, total_comments, analyzed_comments,
            positive_count, negative_count, neutral_count, mixed_count,
            avg_vader_compound, positive_pct, negative_pct)
           SELECT
               d.id,
               (SELECT SUM(e2.comment_count) FROM employees e2
                WHERE e2.department_id = d.id),
               COUNT(*),
               SUM(CASE WHEN di.resolved_label = 'positive' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.resolved_label = 'negative' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.resolved_label = 'neutral' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.resolved_label = 'mixed' THEN 1 ELSE 0 END),
               AVG(di.vader_compound),
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.resolved_label = 'positive' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END,
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.resolved_label = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END
           FROM departments d
           JOIN (
               SELECT DISTINCT e.department_id, isent.issue_id,
                      isent.resolved_label, isent.vader_compound
               FROM employees e
               JOIN comments c ON c.commenter_id = e.commenter_id
                   AND c.is_auto_generated = 0
               JOIN issue_sentiment isent ON isent.issue_id = c.issue_id
               WHERE isent.resolved_by != 'no-resident'
           ) di ON di.department_id = d.id
           GROUP BY d.id"""
    )

    conn.commit()

    emp_count = conn.execute("SELECT COUNT(*) FROM employee_sentiment_summary").fetchone()[0]
    dept_count = conn.execute("SELECT COUNT(*) FROM department_sentiment_summary").fetchone()[0]
    conn.close()

    console.print(
        f"[green]Built summaries: {emp_count} employees, {dept_count} departments[/green]"
    )


def run_analysis(use_roberta: bool = True, force: bool = False) -> dict:
    """Run the full analysis pipeline: analyze then summarize."""
    stats = analyze_issues(use_roberta=use_roberta, force=force)
    build_summaries()
    return stats
