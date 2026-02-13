"""Sentiment analysis pipeline using LLM via Ollama."""

from __future__ import annotations

from rich.console import Console
from rich.progress import Progress

from src.models.database import get_db
from src.sentiment.llm import analyze_sentiment, DEFAULT_MODEL

console = Console()


def analyze_issues(batch_size: int = 20, force: bool = False) -> dict:
    """Run LLM sentiment analysis on full issue conversations.

    For each issue with employee comments, sends the full comment thread
    to the LLM for holistic analysis.

    Returns stats dict.
    """
    conn = get_db()

    if force:
        conn.execute("DELETE FROM issue_sentiment")
        conn.commit()
        console.print("[yellow]Force mode: cleared all previous sentiment results[/yellow]")

    # Get issues that have Verified Official comments and aren't yet analyzed
    issue_ids = conn.execute(
        """SELECT DISTINCT i.id, i.summary, i.status
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

    console.print(f"[cyan]Analyzing {total} issue conversations via LLM...[/cyan]")

    stats = {"analyzed": 0}

    with Progress() as progress:
        task = progress.add_task("Analyzing sentiment...", total=total)

        for row in issue_ids:
            issue_id = row["id"]
            summary = row["summary"] or ""
            status = row["status"] or ""

            # Get ALL comments with metadata
            comments = conn.execute(
                """SELECT comment, created_at, commenter_name,
                          commenter_role, is_auto_generated
                   FROM comments
                   WHERE issue_id = ? AND comment != ''
                   ORDER BY created_at""",
                (issue_id,),
            ).fetchall()

            if not comments:
                progress.update(task, advance=1)
                continue

            total_comments = len(comments)
            comment_dicts = [dict(c) for c in comments]

            # Count resident comments (metadata, still useful)
            resident_comment_count = sum(
                1 for c in comment_dicts
                if not c["is_auto_generated"]
                and c.get("commenter_role") != "Verified Official"
            )

            # Send to LLM
            result = analyze_sentiment(summary, status, comment_dicts)

            conn.execute(
                """INSERT OR REPLACE INTO issue_sentiment
                   (issue_id, total_comments, text_length, resident_comment_count,
                    vader_compound, vader_pos, vader_neg, vader_neu,
                    roberta_positive, roberta_negative, roberta_neutral,
                    resolved_label, resolved_confidence, resolved_by, llm_reasoning,
                    outcome_label, outcome_confidence, outcome_reasoning)
                   VALUES (?, ?, 0, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                           ?, ?, ?, ?, ?, ?, ?)""",
                (
                    issue_id,
                    total_comments,
                    resident_comment_count,
                    result["interaction"]["label"],
                    result["interaction"]["confidence"],
                    f"llm:{DEFAULT_MODEL}",
                    result["interaction"]["reasoning"],
                    result["outcome"]["label"],
                    result["outcome"]["confidence"],
                    result["outcome"]["reasoning"],
                ),
            )

            stats["analyzed"] += 1
            progress.update(task, advance=1)

            # Commit and rebuild summaries in batches
            if stats["analyzed"] % batch_size == 0:
                conn.commit()
                build_summaries()

    conn.commit()
    conn.close()

    console.print(
        f"[green]Analysis complete: {stats['analyzed']} issues analyzed via LLM[/green]"
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
            positive_pct, negative_pct,
            outcome_positive_count, outcome_negative_count,
            outcome_positive_pct, outcome_negative_pct)
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
                    ELSE NULL END,
               SUM(CASE WHEN di.outcome_label = 'positive' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.outcome_label = 'negative' THEN 1 ELSE 0 END),
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.outcome_label = 'positive' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END,
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.outcome_label = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END
           FROM employees e
           JOIN (
               SELECT DISTINCT c.commenter_id, isent.issue_id,
                      isent.resolved_label, isent.outcome_label,
                      isent.vader_compound,
                      isent.roberta_positive, isent.roberta_negative
               FROM comments c
               JOIN issue_sentiment isent ON isent.issue_id = c.issue_id
               WHERE c.is_auto_generated = 0
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
            avg_vader_compound, positive_pct, negative_pct,
            outcome_positive_count, outcome_negative_count,
            outcome_positive_pct, outcome_negative_pct)
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
                    ELSE NULL END,
               SUM(CASE WHEN di.outcome_label = 'positive' THEN 1 ELSE 0 END),
               SUM(CASE WHEN di.outcome_label = 'negative' THEN 1 ELSE 0 END),
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.outcome_label = 'positive' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END,
               CASE WHEN COUNT(*) > 0
                    THEN ROUND(100.0 * SUM(CASE WHEN di.outcome_label = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1)
                    ELSE NULL END
           FROM departments d
           JOIN (
               SELECT DISTINCT e.department_id, isent.issue_id,
                      isent.resolved_label, isent.outcome_label,
                      isent.vader_compound
               FROM employees e
               JOIN comments c ON c.commenter_id = e.commenter_id
                   AND c.is_auto_generated = 0
               JOIN issue_sentiment isent ON isent.issue_id = c.issue_id
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


def run_analysis(force: bool = False) -> dict:
    """Run the full analysis pipeline: analyze then summarize."""
    stats = analyze_issues(force=force)
    build_summaries()
    return stats
