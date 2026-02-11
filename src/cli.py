"""CLI interface for SeeClickFix Sentiment Analysis."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.models.database import get_db, init_db

app = typer.Typer(help="SeeClickFix Sentiment Analysis CLI")
console = Console()

FORCE_HELP = "Re-run from scratch, ignoring cached/completed work"


@app.command()
def crawl(
    start_date: str = typer.Option("2015-01-01", help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, help="End date (YYYY-MM-DD), defaults to today"),
    issue_limit: Optional[int] = typer.Option(None, "--issues", help="Max issues to fetch"),
    comment_limit: Optional[int] = typer.Option(None, "--comments", help="Max issues to fetch comments for"),
    per_page: int = typer.Option(100, help="Results per page"),
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Crawl SeeClickFix issues and comments."""
    from src.crawler.client import SeeClickFixCrawler

    async def _run():
        async with SeeClickFixCrawler(per_page=per_page) as crawler:
            stats = await crawler.crawl_all(
                start_date=start_date,
                end_date=end_date,
                issue_limit=issue_limit,
                comment_limit=comment_limit,
                force=force,
            )
            console.print(f"\n[bold green]Crawl complete![/bold green]")
            console.print(f"  Issues: {stats['issues_fetched']}")
            console.print(f"  Comments: {stats['comments_fetched']}")
            console.print(f"  API calls: {stats['api_calls']}")

    asyncio.run(_run())


@app.command()
def crawl_issues(
    start_date: str = typer.Option("2015-01-01", help="Start date"),
    end_date: Optional[str] = typer.Option(None, help="End date"),
    limit: Optional[int] = typer.Option(None, help="Max issues"),
    per_page: int = typer.Option(100, help="Results per page"),
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Crawl only issues (no comments)."""
    from src.crawler.client import SeeClickFixCrawler

    async def _run():
        async with SeeClickFixCrawler(per_page=per_page) as crawler:
            await crawler.crawl_issues(
                start_date=start_date, end_date=end_date, limit=limit, force=force
            )

    asyncio.run(_run())


@app.command()
def crawl_comments(
    limit: Optional[int] = typer.Option(None, help="Max issues to fetch comments for"),
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Fetch comments for already-crawled issues."""
    from src.crawler.client import SeeClickFixCrawler

    async def _run():
        async with SeeClickFixCrawler() as crawler:
            await crawler.crawl_comments(limit=limit, force=force)

    asyncio.run(_run())


@app.command()
def extract():
    """Extract employees and flag auto-generated comments."""
    from src.extraction.employees import run_extraction

    results = run_extraction()
    console.print(f"  Auto-generated flagged: {results['auto_generated_flagged']}")
    console.print(f"  Employees extracted: {results['employees_extracted']}")


@app.command()
def analyze(
    no_roberta: bool = typer.Option(False, "--no-roberta", help="Skip RoBERTa, use VADER only"),
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Run sentiment analysis on employee comments."""
    from src.sentiment.analyzer import run_analysis

    stats = run_analysis(use_roberta=not no_roberta, force=force)
    console.print(f"  Analyzed: {stats['analyzed']}")


def _serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Start the web UI server (internal)."""
    import uvicorn

    init_db()
    console.print(f"[green]Starting server at http://{host}:{port}[/green]")
    uvicorn.run(
        "src.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Start the web UI server."""
    _serve(host=host, port=port, reload=reload)


def _stats():
    """Show database statistics (internal)."""
    init_db()
    conn = get_db()

    table = Table(title="Database Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    queries = [
        ("Issues", "SELECT COUNT(*) FROM issues"),
        ("Issues with comments", "SELECT COUNT(*) FROM issues WHERE comments_fetched = 1"),
        ("Comments", "SELECT COUNT(*) FROM comments"),
        ("Auto-generated comments", "SELECT COUNT(*) FROM comments WHERE is_auto_generated = 1"),
        ("Employee comments", "SELECT COUNT(*) FROM comments WHERE commenter_role = 'Verified Official' AND is_auto_generated = 0"),
        ("Employees", "SELECT COUNT(*) FROM employees"),
        ("Departments", "SELECT COUNT(*) FROM departments"),
        ("Issues analyzed", "SELECT COUNT(*) FROM issue_sentiment"),
        ("Positive", "SELECT COUNT(*) FROM issue_sentiment WHERE resolved_label = 'positive'"),
        ("Negative", "SELECT COUNT(*) FROM issue_sentiment WHERE resolved_label = 'negative'"),
        ("Neutral", "SELECT COUNT(*) FROM issue_sentiment WHERE resolved_label = 'neutral'"),
        ("Mixed", "SELECT COUNT(*) FROM issue_sentiment WHERE resolved_label = 'mixed'"),
    ]

    for label, query in queries:
        try:
            count = conn.execute(query).fetchone()[0]
            table.add_row(label, f"{count:,}")
        except Exception:
            table.add_row(label, "N/A")

    console.print(table)

    # Crawl progress
    crawl_state = conn.execute(
        """SELECT status, COUNT(*) as cnt
           FROM crawl_state GROUP BY status"""
    ).fetchall()
    if crawl_state:
        console.print("\n[bold]Crawl Progress:[/bold]")
        for row in crawl_state:
            console.print(f"  {row['status']}: {row['cnt']} windows")

    conn.close()


@app.command()
def stats():
    """Show database statistics."""
    _stats()


@app.command()
def demo(
    issue_limit: int = typer.Option(200, help="Issues to crawl"),
    comment_limit: int = typer.Option(50, help="Issues to fetch comments for"),
    no_roberta: bool = typer.Option(False, "--no-roberta", help="Skip RoBERTa"),
    port: int = typer.Option(8000, help="Web server port"),
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Run a demo: crawl a small sample, analyze, and launch the web server."""
    from src.crawler.client import SeeClickFixCrawler
    from src.extraction.employees import run_extraction
    from src.sentiment.analyzer import run_analysis

    console.print("[bold cyan]SeeClickFix Sentiment Analysis - Demo Mode[/bold cyan]\n")

    # Step 1: Crawl
    console.print("[bold]Step 1: Crawling recent issues...[/bold]")

    async def _crawl():
        async with SeeClickFixCrawler() as crawler:
            await crawler.crawl_all(
                start_date="2025-01-01",
                issue_limit=issue_limit,
                comment_limit=comment_limit,
                force=force,
            )

    asyncio.run(_crawl())

    # Step 2: Extract
    console.print("\n[bold]Step 2: Extracting employees...[/bold]")
    run_extraction()

    # Step 3: Analyze
    console.print("\n[bold]Step 3: Running sentiment analysis...[/bold]")
    run_analysis(use_roberta=not no_roberta, force=force)

    # Step 4: Stats
    console.print("\n[bold]Step 4: Statistics[/bold]")
    _stats()

    # Step 5: Serve
    console.print(f"\n[bold]Step 5: Launching web server on port {port}...[/bold]")
    _serve(port=port)


@app.command()
def live(
    start_date: str = typer.Option("2015-01-01", help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, help="End date, defaults to today"),
    no_roberta: bool = typer.Option(False, "--no-roberta", help="Skip RoBERTa"),
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    per_page: int = typer.Option(100, help="Issues per API page"),
    noisy: bool = typer.Option(False, "--noisy", help="Verbose per-issue logging"),
    reanalyze: bool = typer.Option(False, "--reanalyze", help="Skip crawl/extract, re-run sentiment on all existing issues"),
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Crawl, extract, analyze, and serve — all at once, updating live.

    Starts the web server immediately, then crawls issues one by one.
    Each issue is fully processed (comments fetched, employees extracted,
    sentiment analyzed) before moving to the next, so you can refresh
    the browser at any time to see progress.

    Use --reanalyze to skip crawling and just re-score all existing issues.
    """
    import threading
    from datetime import datetime

    import uvicorn

    from src.crawler.client import SeeClickFixCrawler
    from src.extraction.employees import is_auto_generated, parse_employee_name
    from src.sentiment.analyzer import (
        analyze_vader,
        analyze_roberta,
        resolve_sentiment,
        build_summaries,
    )

    init_db()
    use_roberta = not no_roberta

    # --- Start web server in a background thread ---
    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs=dict(
            app="src.web.app:app",
            host=host,
            port=port,
            log_level="warning",
        ),
        daemon=True,
    )
    server_thread.start()
    console.print(f"[bold green]Web UI: http://{host}:{port}[/bold green]\n")

    # --- Per-issue processing (extract + analyze) ---
    def process_issue(conn, issue_id) -> bool:
        """Flag auto-generated comments, extract employees, analyze sentiment
        for a single issue. Returns True if sentiment was analyzed."""
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
            resident_count = conn.execute(
                """SELECT COUNT(*) FROM comments
                   WHERE issue_id = ? AND is_auto_generated = 0
                   AND comment != '' AND commenter_role != 'Verified Official'""",
                (issue_id,),
            ).fetchone()[0]
            console.print(
                f"    [dim]comments: {len(comments)} total, "
                f"{flagged} auto-generated, {resident_count} resident[/dim]"
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
                    console.print(
                        f"    [dim]skip system account: "
                        f"{row['commenter_name']}[/dim]"
                    )
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
                        console.print(
                            f"    [green]+ new dept:[/green] "
                            f"{parsed['department']}"
                        )

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
                console.print(
                    f"    [dim]employee:[/dim] {parsed['name_parsed'] or parsed['name_raw']}"
                    f" [dim]({parsed['department'] or '?'},"
                    f" {comment_count} comments)[/dim]"
                )

        conn.execute(
            """UPDATE departments SET employee_count = (
                   SELECT COUNT(*) FROM employees
                   WHERE department_id = departments.id
               )"""
        )

        # 3. Analyze sentiment if not already done and issue has official comments
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
                console.print("    [dim]sentiment: already analyzed[/dim]")
            return False
        if not has_official:
            if noisy:
                console.print("    [dim]sentiment: no official comments[/dim]")
            return False

        # Count all non-auto, non-empty comments
        all_texts = conn.execute(
            """SELECT comment FROM comments
               WHERE issue_id = ? AND is_auto_generated = 0 AND comment != ''
               ORDER BY created_at""",
            (issue_id,),
        ).fetchall()

        if not all_texts:
            if noisy:
                console.print(
                    "    [dim]sentiment: no analyzable text[/dim]"
                )
            return False

        total_comments = len(all_texts)

        # Get resident-only comments (non-official)
        resident_texts = conn.execute(
            """SELECT comment FROM comments
               WHERE issue_id = ? AND is_auto_generated = 0 AND comment != ''
               AND commenter_role != 'Verified Official'
               ORDER BY created_at""",
            (issue_id,),
        ).fetchall()

        resident_comment_count = len(resident_texts)

        if resident_comment_count == 0:
            # Employee-only thread — no resident signal
            from src.models.schema import SentimentLabel
            conn.execute(
                """INSERT OR REPLACE INTO issue_sentiment
                   (issue_id, total_comments, text_length, resident_comment_count,
                    vader_compound, vader_pos, vader_neg, vader_neu,
                    roberta_positive, roberta_negative, roberta_neutral,
                    resolved_label, resolved_confidence, resolved_by)
                   VALUES (?, ?, 0, 0, 0, 0, 0, 0, NULL, NULL, NULL, ?, 0, ?)""",
                (issue_id, total_comments, SentimentLabel.NEUTRAL.value, "no-resident"),
            )
            if noisy:
                console.print(
                    f"    [dim]comments: {total_comments} total, "
                    f"0 resident[/dim]"
                )
                console.print(
                    "    [bold]sentiment: neutral[/bold] (no resident comments)"
                )
            return True

        conversation = "\n".join(t["comment"] for t in resident_texts)
        vader_scores = analyze_vader(conversation)

        roberta_scores = None
        if use_roberta and abs(vader_scores["vader_compound"]) <= 0.5:
            roberta_scores = analyze_roberta(conversation)

        label, confidence, resolved_by = resolve_sentiment(
            vader_scores, roberta_scores
        )

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
                len(conversation),
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
        if noisy:
            console.print(
                f"    [dim]comments: {total_comments} total, "
                f"{resident_comment_count} resident[/dim]"
            )
            console.print(
                f"    [bold]sentiment: {label.value}[/bold] "
                f"({confidence:.0%} via {resolved_by}, "
                f"VADER={vader_scores['vader_compound']:.3f}, "
                f"{resident_comment_count} resident comments, "
                f"{len(conversation)} chars)"
            )
        return True

    # --- Reanalyze-only mode (no crawl/extract) ---
    def _reanalyze():
        conn = get_db()

        # Clear all existing sentiment
        conn.execute("DELETE FROM issue_sentiment")
        conn.commit()
        console.print("[yellow]Cleared all sentiment data — re-analyzing...[/yellow]")

        # Find all issues that have Verified Official comments
        issue_ids = conn.execute(
            """SELECT DISTINCT i.id, i.summary
               FROM issues i
               JOIN comments c ON c.issue_id = i.id
               WHERE c.commenter_role = 'Verified Official'
               ORDER BY i.created_at DESC"""
        ).fetchall()

        total = len(issue_ids)
        if total == 0:
            console.print("[yellow]No issues with official comments found.[/yellow]")
            conn.close()
            return

        console.print(f"[cyan]Re-analyzing {total:,} issues...[/cyan]\n")

        analyzed = 0
        for i, row in enumerate(issue_ids):
            issue_id = row["id"]

            if noisy:
                summary = (row["summary"] or "")[:60]
                console.print(
                    f"  [cyan]#{issue_id}[/cyan] {summary}"
                )

            # Count all non-auto, non-empty comments
            all_texts = conn.execute(
                """SELECT comment FROM comments
                   WHERE issue_id = ? AND is_auto_generated = 0
                   AND comment != ''
                   ORDER BY created_at""",
                (issue_id,),
            ).fetchall()

            if not all_texts:
                if noisy:
                    console.print(
                        "    [dim]sentiment: no analyzable text[/dim]"
                    )
                continue

            total_comments = len(all_texts)

            # Get resident-only comments (non-official)
            resident_texts = conn.execute(
                """SELECT comment FROM comments
                   WHERE issue_id = ? AND is_auto_generated = 0
                   AND comment != ''
                   AND commenter_role != 'Verified Official'
                   ORDER BY created_at""",
                (issue_id,),
            ).fetchall()

            resident_comment_count = len(resident_texts)

            if resident_comment_count == 0:
                # Employee-only thread — no resident signal
                from src.models.schema import SentimentLabel
                conn.execute(
                    """INSERT OR REPLACE INTO issue_sentiment
                       (issue_id, total_comments, text_length, resident_comment_count,
                        vader_compound, vader_pos, vader_neg, vader_neu,
                        roberta_positive, roberta_negative, roberta_neutral,
                        resolved_label, resolved_confidence, resolved_by)
                       VALUES (?, ?, 0, 0, 0, 0, 0, 0, NULL, NULL, NULL, ?, 0, ?)""",
                    (issue_id, total_comments, SentimentLabel.NEUTRAL.value, "no-resident"),
                )
                conn.commit()
                analyzed += 1
                if noisy:
                    console.print(
                        f"    [dim]comments: {total_comments} total, "
                        f"0 resident[/dim]"
                    )
                    console.print(
                        "    [bold]sentiment: neutral[/bold] (no resident comments)"
                    )
                continue

            conversation = "\n".join(t["comment"] for t in resident_texts)
            vader_scores = analyze_vader(conversation)

            roberta_scores = None
            if use_roberta and abs(vader_scores["vader_compound"]) <= 0.5:
                roberta_scores = analyze_roberta(conversation)

            label, confidence, resolved_by = resolve_sentiment(
                vader_scores, roberta_scores
            )

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
                    len(conversation),
                    resident_comment_count,
                    vader_scores["vader_compound"],
                    vader_scores["vader_pos"],
                    vader_scores["vader_neg"],
                    vader_scores["vader_neu"],
                    roberta_scores["roberta_positive"]
                    if roberta_scores else None,
                    roberta_scores["roberta_negative"]
                    if roberta_scores else None,
                    roberta_scores["roberta_neutral"]
                    if roberta_scores else None,
                    label.value,
                    confidence,
                    resolved_by,
                ),
            )
            conn.commit()
            analyzed += 1

            if noisy:
                console.print(
                    f"    [dim]comments: {total_comments} total, "
                    f"{resident_comment_count} resident[/dim]"
                )
                console.print(
                    f"    [bold]sentiment: {label.value}[/bold] "
                    f"({confidence:.0%} via {resolved_by}, "
                    f"VADER={vader_scores['vader_compound']:.3f}, "
                    f"{resident_comment_count} resident comments, "
                    f"{len(conversation)} chars)"
                )

            if analyzed % 10 == 0:
                build_summaries()
                if not noisy:
                    console.print(
                        f"  {analyzed:,}/{total:,} analyzed", end="\r"
                    )

        build_summaries()
        conn.close()
        console.print(
            f"\n[bold green]Re-analysis complete: "
            f"{analyzed:,}/{total:,} issues analyzed[/bold green]"
        )

    # --- Main async pipeline ---
    async def _pipeline():
        async with SeeClickFixCrawler(per_page=per_page) as crawler:
            conn = get_db()

            if force:
                conn.execute("DELETE FROM crawl_state")
                conn.execute("DELETE FROM issue_sentiment")
                conn.commit()
                console.print(
                    "[yellow]Force mode: reset crawl state and sentiment[/yellow]"
                )

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
                console.print(
                    f"[green]All windows completed ({existing:,} issues). "
                    f"Use --force to re-process.[/green]"
                )
                conn.close()
                console.print(
                    "[dim]Server running. Press Ctrl+C to stop.[/dim]"
                )
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    return

            completed = conn.execute(
                "SELECT COUNT(*) FROM crawl_state WHERE status = 'completed'"
            ).fetchone()[0]
            console.print(
                f"[cyan]{len(windows)} windows to crawl "
                f"({completed} already done)[/cyan]\n"
            )

            total_crawled = 0
            total_analyzed = 0

            for window in windows:
                window_id = window["id"]
                ws, we = window["window_start"], window["window_end"]
                page = window["page"]

                console.print(
                    f"[bold cyan]Window: {ws[:10]} to {we[:10]}[/bold cyan]"
                )

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
                        crawler._store_issue(conn, issue_data)

                        # Fetch and store comments immediately
                        raw_comments = await crawler.fetch_comments(issue_id)
                        if raw_comments:
                            crawler._store_comments(
                                conn, issue_id, raw_comments
                            )
                        conn.execute(
                            "UPDATE issues SET comments_fetched = 1 "
                            "WHERE id = ?",
                            (issue_id,),
                        )

                        if noisy:
                            summary = (issue_data.get("summary") or "")[:60]
                            console.print(
                                f"  [cyan]#{issue_id}[/cyan] {summary} "
                                f"[dim]({len(raw_comments)} comments)[/dim]"
                            )

                        # Extract + analyze this issue
                        if process_issue(conn, issue_id):
                            page_analyzed += 1
                            total_analyzed += 1

                        conn.commit()
                        total_crawled += 1

                        # Rebuild summaries every 10 issues so the UI
                        # stays fresh mid-page
                        if total_crawled % 10 == 0:
                            build_summaries()

                    # Always rebuild at page boundary too
                    build_summaries()

                    console.print(
                        f"  p.{page}: +{len(issues)} issues, "
                        f"+{page_analyzed} analyzed  "
                        f"[dim](total: {total_crawled:,} / "
                        f"{total_analyzed:,} analyzed)[/dim]"
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
            console.print(
                f"\n[bold green]Pipeline complete! "
                f"{total_crawled:,} issues, "
                f"{total_analyzed:,} analyzed[/bold green]"
            )
            console.print("[dim]Server running. Press Ctrl+C to stop.[/dim]")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                return

    try:
        if reanalyze:
            _reanalyze()
        asyncio.run(_pipeline())
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")


@app.command()
def reset(
    confirm: bool = typer.Option(False, "--yes", help="Skip confirmation"),
):
    """Reset the database (deletes all data)."""
    if not confirm:
        typer.confirm("This will delete all data. Continue?", abort=True)

    from src.models.database import DB_PATH

    if DB_PATH.exists():
        DB_PATH.unlink()
        console.print("[yellow]Database deleted[/yellow]")

    init_db()
    console.print("[green]Database re-initialized[/green]")


if __name__ == "__main__":
    app()
