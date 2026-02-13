"""DataSource protocol — the seam between data fetching and orchestration."""

from __future__ import annotations

from typing import Protocol


class DataSource(Protocol):
    """Anything that can supply SeeClickFix-shaped issues and comments.

    Implementations might hit the HTTP API, read from a direct DB connection,
    or replay from a local fixture file.
    """

    async def fetch_issues_page(
        self,
        page: int = 1,
        after: str | None = None,
        before: str | None = None,
    ) -> tuple[list[dict], dict]:
        """Return (issues, pagination_metadata) for one page."""
        ...

    async def fetch_comments(self, issue_id: int) -> list[dict]:
        """Return all comments for a single issue."""
        ...
