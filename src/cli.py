"""CLI interface for SeeClickFix Sentiment Analysis."""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.models.database import get_db, init_db

app = typer.Typer(help="SeeClickFix Sentiment Analysis CLI")
console = Console()

FORCE_HELP = "Re-run from scratch, ignoring cached/completed work"


def _require_llm():
    """Check LLM backend is available. Exit if not."""
    from src.config import LLM_BACKEND
    from src.sentiment.llm import check_llm, DEFAULT_MODEL

    if not check_llm():
        if LLM_BACKEND == "openai":
            console.print(
                "[bold red]OPENAI_API_KEY is not set.[/bold red]\n"
                "Export your key:\n"
                "  export OPENAI_API_KEY=sk-...\n"
            )
        else:
            console.print(
                f"[bold red]Ollama is not running or model '{DEFAULT_MODEL}' is not available.[/bold red]\n"
                f"Start Ollama and pull the model:\n"
                f"  ollama pull {DEFAULT_MODEL}\n"
            )
        sys.exit(1)


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
    from src.crawler.http_source import HTTPSource

    async def _run():
        async with HTTPSource(per_page=per_page) as source:
            crawler = SeeClickFixCrawler(source)
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
            console.print(f"  API calls: {source.api_calls}")

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
    from src.crawler.http_source import HTTPSource

    async def _run():
        async with HTTPSource(per_page=per_page) as source:
            crawler = SeeClickFixCrawler(source)
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
    from src.crawler.http_source import HTTPSource

    async def _run():
        async with HTTPSource() as source:
            crawler = SeeClickFixCrawler(source)
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
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Run sentiment analysis on employee comments."""
    _require_llm()
    from src.sentiment.analyzer import run_analysis

    stats = run_analysis(force=force)
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
    port: int = typer.Option(8000, help="Web server port"),
    force: bool = typer.Option(False, "--force", help=FORCE_HELP),
):
    """Run a demo: crawl a small sample, analyze, and launch the web server."""
    from src.crawler.client import SeeClickFixCrawler
    from src.crawler.http_source import HTTPSource
    from src.extraction.employees import run_extraction
    from src.sentiment.analyzer import run_analysis

    _require_llm()

    console.print("[bold cyan]SeeClickFix Sentiment Analysis - Demo Mode[/bold cyan]\n")

    # Step 1: Crawl
    console.print("[bold]Step 1: Crawling recent issues...[/bold]")

    async def _crawl():
        async with HTTPSource() as source:
            crawler = SeeClickFixCrawler(source)
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
    run_analysis(force=force)

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

    import uvicorn

    from src.pipeline import reanalyze as pipeline_reanalyze, run_pipeline

    _require_llm()
    init_db()

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

    try:
        if reanalyze:
            pipeline_reanalyze(noisy=noisy)
        else:
            asyncio.run(run_pipeline(
                start_date=start_date,
                end_date=end_date,
                per_page=per_page,
                force=force,
                noisy=noisy,
            ))
        # Pipeline finished — keep server alive
        console.print("[dim]Server running. Press Ctrl+C to stop.[/dim]")
        while True:
            import time
            time.sleep(1)
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
