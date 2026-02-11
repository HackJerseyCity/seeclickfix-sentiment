"""Rate-limited SeeClickFix API client with checkpoint/resume crawling."""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console

from src.models.database import get_db, init_db, DATA_DIR
from src.models.schema import APIIssue, APIComment, APICommenter

console = Console()

BASE_URL = "https://seeclickfix.com/api/v2"

# Jersey City bounding box
JC_BOUNDS = {
    "min_lat": 40.651530,
    "min_lng": -74.149293,
    "max_lat": 40.776051,
    "max_lng": -74.003896,
}

STATUSES = "open,acknowledged,closed,archived"
RATE_LIMIT = 20  # requests per minute
RATE_WINDOW = 60  # seconds

# Crawl state file for quick resume info
CRAWL_STATE_FILE = DATA_DIR / "crawl_state.json"


class RateLimiter:
    """Token bucket rate limiter: max `rate` requests per `window` seconds."""

    def __init__(self, rate: int = RATE_LIMIT, window: float = RATE_WINDOW):
        self.rate = rate
        self.window = window
        self.tokens: list[float] = []

    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        while True:
            now = time.monotonic()
            # Remove expired tokens
            self.tokens = [t for t in self.tokens if now - t < self.window]
            if len(self.tokens) < self.rate:
                self.tokens.append(now)
                return
            # Wait until the oldest token expires
            wait_time = self.window - (now - self.tokens[0]) + 0.1
            await asyncio.sleep(wait_time)


class SeeClickFixCrawler:
    """Async crawler for SeeClickFix API with date-windowed pagination."""

    def __init__(self, per_page: int = 100):
        self.per_page = per_page
        self.rate_limiter = RateLimiter()
        self.client: Optional[httpx.AsyncClient] = None
        self.stats = {"issues_fetched": 0, "comments_fetched": 0, "api_calls": 0}

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "SeeClickFix-Sentiment-Analyzer/0.1"},
        )
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def _request(self, url: str, params: dict | None = None) -> dict | None:
        """Make a rate-limited request with retry on 429/5xx."""
        await self.rate_limiter.acquire()
        self.stats["api_calls"] += 1

        for attempt in range(5):
            try:
                resp = await self.client.get(url, params=params)

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    console.print(
                        f"[yellow]Rate limited. Waiting {retry_after}s...[/yellow]"
                    )
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code >= 500:
                    wait = min(2 ** (attempt + 1), 60)
                    console.print(
                        f"[yellow]Server error {resp.status_code}. Retrying in {wait}s...[/yellow]"
                    )
                    await asyncio.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.TimeoutException:
                wait = min(2 ** (attempt + 1), 60)
                console.print(
                    f"[yellow]Timeout. Retrying in {wait}s...[/yellow]"
                )
                await asyncio.sleep(wait)
            except httpx.HTTPStatusError as e:
                console.print(f"[red]HTTP error: {e}[/red]")
                return None

        console.print("[red]Max retries exceeded[/red]")
        return None

    async def fetch_issues_page(
        self,
        page: int = 1,
        after: str | None = None,
        before: str | None = None,
    ) -> tuple[list[dict], dict]:
        """Fetch a single page of issues. Returns (issues, pagination_metadata)."""
        params = {
            **JC_BOUNDS,
            "status": STATUSES,
            "page": page,
            "per_page": self.per_page,
        }
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        data = await self._request(f"{BASE_URL}/issues", params=params)
        if not data:
            return [], {}

        issues = data.get("issues", [])
        metadata = data.get("metadata", {}).get("pagination", {})
        return issues, metadata

    async def fetch_comments(self, issue_id: int) -> list[dict]:
        """Fetch all comments for an issue."""
        data = await self._request(f"{BASE_URL}/issues/{issue_id}/comments")
        if not data:
            return []
        return data.get("comments", [])

    def _store_issue(self, conn, issue_data: dict) -> None:
        """Upsert an issue into the database."""
        request_type = issue_data.get("request_type")
        rt_title = None
        rt_org = None
        if isinstance(request_type, dict):
            rt_title = request_type.get("title")
            rt_org = request_type.get("organization")
        elif isinstance(request_type, str):
            rt_title = request_type

        reporter = issue_data.get("reporter") or {}
        html_url = issue_data.get("html_url") or f"https://seeclickfix.com/issues/{issue_data['id']}"

        conn.execute(
            """INSERT OR REPLACE INTO issues
               (id, status, summary, description, lat, lng, address,
                created_at, updated_at, closed_at, acknowledged_at,
                request_type, department, html_url, comment_count,
                reporter_id, reporter_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                issue_data["id"],
                issue_data.get("status"),
                issue_data.get("summary"),
                issue_data.get("description"),
                issue_data.get("lat"),
                issue_data.get("lng"),
                issue_data.get("address"),
                issue_data.get("created_at"),
                issue_data.get("updated_at"),
                issue_data.get("closed_at"),
                issue_data.get("acknowledged_at"),
                rt_title,
                rt_org or rt_title,
                html_url,
                issue_data.get("comment_count", 0),
                reporter.get("id") if isinstance(reporter, dict) else None,
                reporter.get("name") if isinstance(reporter, dict) else None,
            ),
        )

    def _store_comments(self, conn, issue_id: int, comments: list[dict]) -> int:
        """Store comments for an issue. Returns count stored."""
        count = 0
        for c in comments:
            # Extract comment ID from flag_url or generate from issue_id + index
            comment_id = None
            flag_url = c.get("flag_url", "")
            if flag_url:
                match = re.search(r"/comments/(\d+)/", flag_url)
                if match:
                    comment_id = int(match.group(1))

            if not comment_id:
                # Fallback: hash based on issue_id + created_at + comment text
                raw = f"{issue_id}:{c.get('created_at', '')}:{c.get('comment', '')[:50]}"
                comment_id = abs(hash(raw)) % (2**31)

            commenter = c.get("commenter") or {}

            conn.execute(
                """INSERT OR REPLACE INTO comments
                   (id, issue_id, comment, created_at, updated_at,
                    commenter_id, commenter_name, commenter_role)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    comment_id,
                    issue_id,
                    c.get("comment", ""),
                    c.get("created_at"),
                    c.get("updated_at"),
                    commenter.get("id"),
                    commenter.get("name"),
                    commenter.get("role"),
                ),
            )
            count += 1
        return count

    def _generate_windows(
        self, start_date: str, end_date: str, months: int = 1
    ) -> list[tuple[str, str]]:
        """Generate date windows for crawling."""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        windows = []

        current = start
        while current < end:
            window_end = current + timedelta(days=30 * months)
            if window_end > end:
                window_end = end
            windows.append(
                (current.strftime("%Y-%m-%dT00:00:00-05:00"),
                 window_end.strftime("%Y-%m-%dT23:59:59-05:00"))
            )
            current = window_end + timedelta(days=1)

        return windows

    def _get_crawl_state(self, conn) -> list[dict]:
        """Get current crawl state from the database."""
        rows = conn.execute(
            "SELECT * FROM crawl_state ORDER BY window_start"
        ).fetchall()
        return [dict(r) for r in rows]

    def _init_crawl_windows(
        self, conn, start_date: str, end_date: str
    ) -> None:
        """Initialize crawl windows, adding any that don't already exist."""
        windows = self._generate_windows(start_date, end_date)

        # Get existing window starts to avoid duplicates
        existing = {
            row["window_start"]
            for row in conn.execute("SELECT window_start FROM crawl_state").fetchall()
        }

        added = 0
        for ws, we in windows:
            if ws not in existing:
                conn.execute(
                    """INSERT INTO crawl_state (window_start, window_end, status, page)
                       VALUES (?, ?, 'pending', 1)""",
                    (ws, we),
                )
                added += 1

        if added > 0:
            conn.commit()
            console.print(f"[green]Added {added} new crawl windows[/green]")
        else:
            console.print(
                f"[dim]All {len(windows)} crawl windows already initialized[/dim]"
            )

    async def crawl_issues(
        self,
        start_date: str = "2015-01-01",
        end_date: str | None = None,
        limit: int | None = None,
        force: bool = False,
    ) -> None:
        """Crawl all issues using date-windowed pagination with checkpoint/resume."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        init_db()
        conn = get_db()

        if force:
            conn.execute("DELETE FROM crawl_state")
            conn.commit()
            console.print("[yellow]Force mode: reset all crawl windows[/yellow]")

        self._init_crawl_windows(conn, start_date, end_date)

        # Find incomplete windows
        windows = conn.execute(
            """SELECT * FROM crawl_state
               WHERE status != 'completed'
               ORDER BY window_start"""
        ).fetchall()

        if not windows:
            existing = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
            console.print(
                f"[green]All crawl windows completed ({existing:,} issues in DB). "
                f"Use --force to re-crawl.[/green]"
            )
            conn.close()
            return

        completed = conn.execute(
            "SELECT COUNT(*) FROM crawl_state WHERE status = 'completed'"
        ).fetchone()[0]
        console.print(
            f"[cyan]Resuming crawl: {len(windows)} windows remaining "
            f"({completed} already completed)[/cyan]"
        )

        total_issues = 0
        for window in windows:
            window_id = window["id"]
            ws = window["window_start"]
            we = window["window_end"]
            start_page = window["page"]

            console.print(
                f"\n[cyan]Crawling window: {ws[:10]} to {we[:10]} (page {start_page})[/cyan]"
            )

            conn.execute(
                "UPDATE crawl_state SET status='in_progress', started_at=? WHERE id=?",
                (datetime.now().isoformat(), window_id),
            )
            conn.commit()

            page = start_page
            while True:
                issues, pagination = await self.fetch_issues_page(
                    page=page, after=ws, before=we
                )

                if not issues:
                    break

                for issue_data in issues:
                    self._store_issue(conn, issue_data)
                    total_issues += 1
                    self.stats["issues_fetched"] += 1

                conn.commit()

                # Update checkpoint
                conn.execute(
                    "UPDATE crawl_state SET page=?, issues_fetched=? WHERE id=?",
                    (page + 1, total_issues, window_id),
                )
                conn.commit()

                console.print(
                    f"  Page {page}: {len(issues)} issues "
                    f"(total: {total_issues})"
                )

                if limit and total_issues >= limit:
                    console.print(f"[yellow]Reached limit of {limit} issues[/yellow]")
                    conn.close()
                    return

                next_page = pagination.get("next_page")
                if not next_page:
                    break
                page = next_page

            # Mark window complete
            conn.execute(
                "UPDATE crawl_state SET status='completed', completed_at=? WHERE id=?",
                (datetime.now().isoformat(), window_id),
            )
            conn.commit()

        conn.close()
        console.print(
            f"\n[green]Issue crawl complete. {total_issues} issues fetched.[/green]"
        )

    async def crawl_comments(self, limit: int | None = None, force: bool = False) -> None:
        """Fetch comments for all issues that don't have them yet."""
        conn = get_db()

        if force:
            conn.execute("UPDATE issues SET comments_fetched = 0")
            conn.commit()
            console.print("[yellow]Force mode: will re-fetch all comments[/yellow]")

        issues = conn.execute(
            """SELECT id FROM issues
               WHERE comments_fetched = 0
               ORDER BY created_at DESC"""
        ).fetchall()

        total = len(issues)
        if total == 0:
            existing = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
            console.print(
                f"[green]All issues already have comments fetched "
                f"({existing:,} comments in DB). Use --force to re-fetch.[/green]"
            )
            conn.close()
            return

        console.print(f"\n[cyan]Fetching comments for {total} issues...[/cyan]")

        for i, row in enumerate(issues):
            issue_id = row["id"]
            comments = await self.fetch_comments(issue_id)

            if comments:
                count = self._store_comments(conn, issue_id, comments)
                self.stats["comments_fetched"] += count

            conn.execute(
                "UPDATE issues SET comments_fetched = 1 WHERE id = ?",
                (issue_id,),
            )
            conn.commit()

            if (i + 1) % 10 == 0 or i == total - 1:
                console.print(
                    f"  Progress: {i + 1}/{total} issues, "
                    f"{self.stats['comments_fetched']} comments"
                )

            if limit and (i + 1) >= limit:
                console.print(f"[yellow]Reached limit of {limit} issues[/yellow]")
                break

        conn.close()
        console.print(
            f"\n[green]Comment crawl complete. "
            f"{self.stats['comments_fetched']} comments fetched.[/green]"
        )

    async def crawl_all(
        self,
        start_date: str = "2015-01-01",
        end_date: str | None = None,
        issue_limit: int | None = None,
        comment_limit: int | None = None,
        force: bool = False,
    ) -> dict:
        """Full crawl: issues then comments."""
        await self.crawl_issues(
            start_date=start_date, end_date=end_date, limit=issue_limit, force=force
        )
        await self.crawl_comments(limit=comment_limit, force=force)
        return self.stats
