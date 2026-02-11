"""Extracted pipeline logic — crawl, extract, analyse in one pass.

Shared by the CLI ``live`` command and the production ``entrypoint``.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Optional

from src.models.database import get_db, init_db
from src.sentiment.llm import analyze_sentiment as llm_analyze, DEFAULT_MODEL
from src.sentiment.analyzer import build_summaries
from src.extraction.employees import is_auto_generated, parse_employee_name

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-issue processing (extract + analyse)
# ---------------------------------------------------------------------------

def process_issue(conn, issue_id: int, noisy: bool = False) -> bool:
    """Flag auto-generated comments, extract employees, analyse sentiment
    for a single issue.  Returns True if sentiment was analysed."""

    # 1. Flag auto-generated comments on this issue
    comments = conn.execute(
        "SELECT id, comment FROM comments "
        "WHERE issue_id = ? AND is_auto_generated = 0",
        (issue_id,),
    ).fetchall()
    flagged = 0
    for c in comments:
        if is_auto_generated(c["comment"]):
            conn.execute(
                "UPDATE comments SET is_auto_generated = 1 WHERE id = ?",
                (c["id"],),
            )
            flagged += 1
    if noisy:
        log.info(
            "    comments: %d total, %d auto-generated",
            len(comments), flagged,
        )

    # 2. Upsert employees from officials on this issue
    officials = conn.execute(
        """SELECT DISTINCT commenter_id, commenter_name FROM comments
           WHERE issue_id = ? AND commenter_role = 'Verified Official'
           AND commenter_id IS NOT NULL AND commenter_name IS NOT NULL""",
        (issue_id,),
    ).fetchall()

    for row in officials:
        parsed = parse_employee_name(row["commenter_name"])
        if parsed["is_system"]:
            if noisy:
                log.info("    skip system account: %s", row["commenter_name"])
            continue

        dept_id = None
        if parsed["department"]:
            existing = conn.execute(
                "SELECT id FROM departments WHERE name = ?",
                (parsed["department"],),
            ).fetchone()
            if existing:
                dept_id = existing["id"]
            else:
                cursor = conn.execute(
                    "INSERT INTO departments (name) VALUES (?)",
                    (parsed["department"],),
                )
                dept_id = cursor.lastrowid
                if noisy:
                    log.info("    + new dept: %s", parsed["department"])

        comment_count = conn.execute(
            "SELECT COUNT(*) FROM comments "
            "WHERE commenter_id = ? AND is_auto_generated = 0",
            (row["commenter_id"],),
        ).fetchone()[0]

        conn.execute(
            """INSERT INTO employees
               (commenter_id, name_raw, name_parsed, title_parsed,
                department_id, comment_count)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(commenter_id) DO UPDATE SET
                   name_raw = excluded.name_raw,
                   name_parsed = excluded.name_parsed,
                   title_parsed = excluded.title_parsed,
                   department_id = excluded.department_id,
                   comment_count = excluded.comment_count""",
            (
                row["commenter_id"],
                parsed["name_raw"],
                parsed["name_parsed"],
                parsed["title_parsed"],
                dept_id,
                comment_count,
            ),
        )
        if noisy:
            log.info(
                "    employee: %s (%s, %d comments)",
                parsed["name_parsed"] or parsed["name_raw"],
                parsed["department"] or "?",
                comment_count,
            )

    conn.execute(
        """UPDATE departments SET employee_count = (
               SELECT COUNT(*) FROM employees
               WHERE department_id = departments.id
           )"""
    )

    # 3. Analyse sentiment if not already done and issue has official comments
    already = conn.execute(
        "SELECT 1 FROM issue_sentiment WHERE issue_id = ?", (issue_id,)
    ).fetchone()

    has_official = conn.execute(
        "SELECT 1 FROM comments "
        "WHERE issue_id = ? AND commenter_role = 'Verified Official'",
        (issue_id,),
    ).fetchone()

    if already:
        if noisy:
            log.info("    sentiment: already analysed")
        return False
    if not has_official:
        if noisy:
            log.info("    sentiment: no official comments")
        return False

    # Get issue summary and status
    issue_row = conn.execute(
        "SELECT summary, status FROM issues WHERE id = ?", (issue_id,)
    ).fetchone()
    issue_summary = (issue_row["summary"] or "") if issue_row else ""
    issue_status = (issue_row["status"] or "") if issue_row else ""

    # Get ALL comments with metadata for LLM
    all_comments = conn.execute(
        """SELECT comment, created_at, commenter_name,
                  commenter_role, is_auto_generated
           FROM comments
           WHERE issue_id = ? AND comment != ''
           ORDER BY created_at""",
        (issue_id,),
    ).fetchall()

    if not all_comments:
        if noisy:
            log.info("    sentiment: no analysable text")
        return False

    total_comments = len(all_comments)
    comment_dicts = [dict(c) for c in all_comments]

    # Count resident comments (metadata)
    resident_comment_count = sum(
        1 for c in comment_dicts
        if not c["is_auto_generated"]
        and c.get("commenter_role") != "Verified Official"
    )

    # Send to LLM
    result = llm_analyze(issue_summary, issue_status, comment_dicts)

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
    if noisy:
        i_res = result["interaction"]
        o_res = result["outcome"]
        log.info(
            "    sentiment: %s/%s (%.0f%%/%.0f%%, interaction: \"%s\" | outcome: \"%s\")",
            i_res["label"], o_res["label"],
            i_res["confidence"] * 100, o_res["confidence"] * 100,
            i_res["reasoning"], o_res["reasoning"],
        )
    return True


# ---------------------------------------------------------------------------
# Reanalyse-only mode
# ---------------------------------------------------------------------------

def reanalyze(noisy: bool = False) -> None:
    """Clear all sentiment and re-score every issue that has official comments."""
    conn = get_db()

    conn.execute("DELETE FROM issue_sentiment")
    conn.commit()
    log.info("Cleared all sentiment data — re-analysing...")

    issue_ids = conn.execute(
        """SELECT DISTINCT i.id, i.summary, i.status
           FROM issues i
           JOIN comments c ON c.issue_id = i.id
           WHERE c.commenter_role = 'Verified Official'
           ORDER BY i.created_at DESC"""
    ).fetchall()

    total = len(issue_ids)
    if total == 0:
        log.warning("No issues with official comments found.")
        conn.close()
        return

    log.info("Re-analysing %d issues via LLM...", total)

    analyzed = 0
    for _i, row in enumerate(issue_ids):
        issue_id = row["id"]
        summary = row["summary"] or ""
        status = row["status"] or ""

        if noisy:
            log.info("  #%d %s", issue_id, summary[:60])

        all_comments = conn.execute(
            """SELECT comment, created_at, commenter_name,
                      commenter_role, is_auto_generated
               FROM comments
               WHERE issue_id = ? AND comment != ''
               ORDER BY created_at""",
            (issue_id,),
        ).fetchall()

        if not all_comments:
            if noisy:
                log.info("    sentiment: no analysable text")
            continue

        total_comments = len(all_comments)
        comment_dicts = [dict(c) for c in all_comments]

        resident_comment_count = sum(
            1 for c in comment_dicts
            if not c["is_auto_generated"]
            and c.get("commenter_role") != "Verified Official"
        )

        result = llm_analyze(summary, status, comment_dicts)

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
        conn.commit()
        analyzed += 1

        if noisy:
            i_res = result["interaction"]
            o_res = result["outcome"]
            log.info(
                "    sentiment: %s/%s (%.0f%%/%.0f%%, interaction: \"%s\" | outcome: \"%s\")",
                i_res["label"], o_res["label"],
                i_res["confidence"] * 100, o_res["confidence"] * 100,
                i_res["reasoning"], o_res["reasoning"],
            )

        if analyzed % 10 == 0:
            build_summaries()
            if not noisy:
                log.info("  %d/%d analysed", analyzed, total)

    build_summaries()
    conn.close()
    log.info("Re-analysis complete: %d/%d issues analysed", analyzed, total)


# ---------------------------------------------------------------------------
# Main async pipeline — crawl + extract + analyse in one pass
# ---------------------------------------------------------------------------

async def run_pipeline(
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    per_page: int = 100,
    force: bool = False,
    noisy: bool = False,
) -> None:
    """Crawl issues, fetch comments, extract employees, and analyse sentiment.

    After all windows are complete the function returns.
    """
    from src.crawler.client import SeeClickFixCrawler

    async with SeeClickFixCrawler(per_page=per_page) as crawler:
        conn = get_db()

        if force:
            conn.execute("DELETE FROM crawl_state")
            conn.execute("DELETE FROM issue_sentiment")
            conn.commit()
            log.info("Force mode: reset crawl state and sentiment")

        ed = end_date or datetime.now().strftime("%Y-%m-%d")
        crawler._init_crawl_windows(conn, start_date, ed)

        windows = conn.execute(
            """SELECT * FROM crawl_state
               WHERE status != 'completed'
               ORDER BY window_start"""
        ).fetchall()

        if not windows:
            existing = conn.execute(
                "SELECT COUNT(*) FROM issues"
            ).fetchone()[0]
            log.info(
                "All windows completed (%d issues). Use --force to re-process.",
                existing,
            )
            conn.close()
            return

        completed = conn.execute(
            "SELECT COUNT(*) FROM crawl_state WHERE status = 'completed'"
        ).fetchone()[0]
        log.info(
            "%d windows to crawl (%d already done)", len(windows), completed,
        )

        total_crawled = 0
        total_analyzed = 0

        for window in windows:
            window_id = window["id"]
            ws, we = window["window_start"], window["window_end"]
            page = window["page"]

            log.info("Window: %s to %s", ws[:10], we[:10])

            conn.execute(
                "UPDATE crawl_state SET status='in_progress', "
                "started_at=? WHERE id=?",
                (datetime.now().isoformat(), window_id),
            )
            conn.commit()

            while True:
                issues, pagination = await crawler.fetch_issues_page(
                    page=page, after=ws, before=we
                )
                if not issues:
                    break

                page_analyzed = 0
                for issue_data in issues:
                    issue_id = issue_data["id"]
                    if not crawler._store_issue(conn, issue_data):
                        continue

                    raw_comments = await crawler.fetch_comments(issue_id)
                    if raw_comments:
                        crawler._store_comments(conn, issue_id, raw_comments)
                    conn.execute(
                        "UPDATE issues SET comments_fetched = 1 "
                        "WHERE id = ?",
                        (issue_id,),
                    )

                    if noisy:
                        summary = (issue_data.get("summary") or "")[:60]
                        log.info(
                            "  #%d %s (%d comments)",
                            issue_id, summary, len(raw_comments),
                        )

                    if process_issue(conn, issue_id, noisy=noisy):
                        page_analyzed += 1
                        total_analyzed += 1

                    conn.commit()
                    total_crawled += 1

                    if total_crawled % 10 == 0:
                        build_summaries()

                build_summaries()

                log.info(
                    "  p.%d: +%d issues, +%d analysed  (total: %d / %d analysed)",
                    page, len(issues), page_analyzed,
                    total_crawled, total_analyzed,
                )

                conn.execute(
                    "UPDATE crawl_state SET page=?, issues_fetched=? "
                    "WHERE id=?",
                    (page + 1, total_crawled, window_id),
                )
                conn.commit()

                next_page = pagination.get("next_page")
                if not next_page:
                    break
                page = next_page

            conn.execute(
                "UPDATE crawl_state SET status='completed', "
                "completed_at=? WHERE id=?",
                (datetime.now().isoformat(), window_id),
            )
            conn.commit()

        conn.close()
        log.info(
            "Pipeline complete! %d issues, %d analysed",
            total_crawled, total_analyzed,
        )


# ---------------------------------------------------------------------------
# Background thread convenience wrapper
# ---------------------------------------------------------------------------

def start_pipeline_thread(
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    per_page: int = 100,
    force: bool = False,
    noisy: bool = False,
    reanalyze_mode: bool = False,
    loop_interval: int = 3600,
) -> threading.Thread:
    """Run the pipeline (or reanalyse) in a daemon thread.

    When *loop_interval* > 0 the pipeline re-runs after sleeping that many
    seconds so new SeeClickFix issues are picked up continuously.
    """

    def _target():
        while True:
            try:
                if reanalyze_mode:
                    reanalyze(noisy=noisy)
                else:
                    asyncio.run(run_pipeline(
                        start_date=start_date,
                        end_date=end_date,
                        per_page=per_page,
                        force=force,
                        noisy=noisy,
                    ))
            except Exception:
                log.exception("Pipeline error — will retry in %ds", loop_interval)

            if loop_interval <= 0:
                break
            log.info("Pipeline sleeping %ds before next run...", loop_interval)
            time.sleep(loop_interval)

    t = threading.Thread(target=_target, daemon=True, name="pipeline")
    t.start()
    return t
