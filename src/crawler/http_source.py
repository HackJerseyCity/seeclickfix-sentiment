"""HTTP implementation of DataSource — talks to the SeeClickFix REST API."""

from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx
from rich.console import Console

console = Console()

BASE_URL = "https://seeclickfix.com/api/v2"
REQUEST_DELAY = 3.0  # seconds between requests (20 req/min)

# Jersey City bounding box (used to scope API queries)
JC_BOUNDS = {
    "min_lat": 40.651530,
    "min_lng": -74.149293,
    "max_lat": 40.776051,
    "max_lng": -74.003896,
}

STATUSES = "open,acknowledged,closed,archived"


class RateLimiter:
    """Simple per-request delay rate limiter."""

    def __init__(self, delay: float = REQUEST_DELAY):
        self.delay = delay
        self.last_request: float = 0.0

    async def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_request
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        self.last_request = time.monotonic()


class HTTPSource:
    """DataSource backed by the SeeClickFix v2 REST API."""

    def __init__(self, per_page: int = 100):
        self.per_page = per_page
        self.rate_limiter = RateLimiter()
        self.client: Optional[httpx.AsyncClient] = None
        self.api_calls = 0

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
        self.api_calls += 1

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
