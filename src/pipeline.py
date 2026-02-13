"""Extracted pipeline logic — crawl, extract, analyse in one pass.

Shared by the CLI ``live`` command and the production ``entrypoint``.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from src.models.database import get_db, init_db
from src.config import LLM_CONCURRENCY
from src.sentiment.llm import analyze_sentiment as llm_analyze, DEFAULT_MODEL
from src.sentiment.analyzer import build_summaries
from src.extraction.employees import is_auto_generated, parse_employee_name

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-issue processing (extract + analyse)
# ---------------------------------------------------------------------------

def _extract_issue(conn, issue_id: int, noisy: bool = False) -> None:
    """Flag auto-generated comments and upsert employees for a single issue."""

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


def _prepare_llm_data(conn, issue_id: int, noisy: bool = False) -> dict | None:
    """Return the data needed for the LLM call, or None if analysis should be skipped."""

    already = conn.execute(
        "SELECT 1 FROM issue_sentiment WHERE issue_id = ?", (issue_id,)
    ).fetchone()
    if already:
        if noisy:
            log.info("    sentiment: already analysed")
        return None

    has_official = conn.execute(
        "SELECT 1 FROM comments "
        "WHERE issue_id = ? AND commenter_role = 'Verified Official'",
        (issue_id,),
    ).fetchone()
    if not has_official:
        if noisy:
            log.info("    sentiment: no official comments")
        return None

    issue_row = conn.execute(
        "SELECT summary, status FROM issues WHERE id = ?", (issue_id,)
    ).fetchone()
    issue_summary = (issue_row["summary"] or "") if issue_row else ""
    issue_status = (issue_row["status"] or "") if issue_row else ""

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
        return None

    comment_dicts = [dict(c) for c in all_comments]

    return {
        "issue_id": issue_id,
        "summary": issue_summary,
        "status": issue_status,
        "comments": comment_dicts,
        "total_comments": len(all_comments),
        "resident_comment_count": sum(
            1 for c in comment_dicts
            if not c["is_auto_generated"]
            and c.get("commenter_role") != "Verified Official"
        ),
    }


def _store_sentiment(conn, data: dict, result: dict, noisy: bool = False) -> None:
    """Write an LLM sentiment result to the DB."""
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
            data["issue_id"],
            data["total_comments"],
            data["resident_comment_count"],
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
            "    #%d sentiment: %s/%s (%.0f%%/%.0f%%, interaction: \"%s\" | outcome: \"%s\")",
            data["issue_id"],
            i_res["label"], o_res["label"],
            i_res["confidence"] * 100, o_res["confidence"] * 100,
            i_res["reasoning"], o_res["reasoning"],
        )


def process_issue(conn, issue_id: int, noisy: bool = False) -> bool:
    """Flag auto-generated comments, extract employees, analyse sentiment
    for a single issue.  Returns True if sentiment was analysed."""
    _extract_issue(conn, issue_id, noisy=noisy)
    data = _prepare_llm_data(conn, issue_id, noisy=noisy)
    if data is None:
        return False
    result = llm_analyze(data["summary"], data["status"], data["comments"])
    _store_sentiment(conn, data, result, noisy=noisy)
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

    log.info(
        "Re-analysing %d issues via LLM (%d concurrent)...",
        total, LLM_CONCURRENCY,
    )

    # Prepare all work items up front (DB reads only)
    work = []
    for row in issue_ids:
        issue_id = row["id"]
        summary = row["summary"] or ""
        status = row["status"] or ""

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
                log.info("  #%d — no analysable text, skipping", issue_id)
            continue

        comment_dicts = [dict(c) for c in all_comments]
        work.append({
            "issue_id": issue_id,
            "summary": summary,
            "status": status,
            "comments": comment_dicts,
            "total_comments": len(all_comments),
            "resident_comment_count": sum(
                1 for c in comment_dicts
                if not c["is_auto_generated"]
                and c.get("commenter_role") != "Verified Official"
            ),
        })

    # Run LLM calls concurrently
    analyzed = 0
    with ThreadPoolExecutor(max_workers=LLM_CONCURRENCY) as pool:
        future_map = {
            pool.submit(
                llm_analyze, item["summary"], item["status"], item["comments"],
            ): item
            for item in work
        }

        for future in as_completed(future_map):
            data = future_map[future]
            try:
                result = future.result()
            except Exception as e:
                log.error("LLM error for #%d: %s", data["issue_id"], e)
                continue

            _store_sentiment(conn, data, result, noisy=noisy)
            conn.commit()
            analyzed += 1

            if analyzed % 10 == 0:
                build_summaries()
                if not noisy:
                    log.info("  %d/%d analysed", analyzed, len(work))

    build_summaries()
    conn.close()
    log.info("Re-analysis complete: %d/%d issues analysed", analyzed, len(work))


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
    from src.crawler.http_source import HTTPSource

    async with HTTPSource(per_page=per_page) as source:
        crawler = SeeClickFixCrawler(source)
        conn = get_db()

        if force:
            conn.execute("DELETE FROM crawl_state")
            conn.execute("DELETE FROM issue_sentiment")
            conn.commit()
            log.info("Force mode: reset crawl state and sentiment")

        ed = end_date or datetime.now().strftime("%Y-%m-%d")
        crawler.init_crawl_windows(conn, start_date, ed)

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
                issues, pagination = await source.fetch_issues_page(
                    page=page, after=ws, before=we
                )
                if not issues:
                    break

                # Crawl all issues in this page, do DB extraction,
                # and collect items that need LLM analysis.
                pending_llm = []
                for issue_data in issues:
                    issue_id = issue_data["id"]
                    if not crawler.store_issue(conn, issue_data):
                        continue

                    raw_comments = await source.fetch_comments(issue_id)
                    if raw_comments:
                        crawler.store_comments(conn, issue_id, raw_comments)
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

                    _extract_issue(conn, issue_id, noisy=noisy)
                    data = _prepare_llm_data(conn, issue_id, noisy=noisy)
                    if data:
                        pending_llm.append(data)

                    conn.commit()
                    total_crawled += 1

                # Run LLM calls for this page concurrently
                page_analyzed = 0
                if pending_llm:
                    with ThreadPoolExecutor(max_workers=LLM_CONCURRENCY) as pool:
                        future_map = {
                            pool.submit(
                                llm_analyze,
                                d["summary"], d["status"], d["comments"],
                            ): d
                            for d in pending_llm
                        }
                        for future in as_completed(future_map):
                            data = future_map[future]
                            try:
                                result = future.result()
                            except Exception as e:
                                log.error(
                                    "LLM error for #%d: %s",
                                    data["issue_id"], e,
                                )
                                continue
                            _store_sentiment(conn, data, result, noisy=noisy)
                            page_analyzed += 1
                            total_analyzed += 1
                    conn.commit()

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
