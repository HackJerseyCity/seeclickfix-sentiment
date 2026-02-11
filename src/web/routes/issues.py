"""Issue routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.models.database import get_db

router = APIRouter(prefix="/issues")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/{issue_id}")
async def issue_detail(request: Request, issue_id: int):
    conn = get_db()

    # Get issue with conversation-level sentiment
    issue = conn.execute(
        """SELECT i.*, isent.resolved_label as sentiment_label,
                  isent.resolved_confidence as sentiment_confidence,
                  isent.vader_compound as sentiment_vader,
                  isent.resolved_by as sentiment_by,
                  isent.total_comments as sentiment_comments
           FROM issues i
           LEFT JOIN issue_sentiment isent ON isent.issue_id = i.id
           WHERE i.id = ?""",
        (issue_id,),
    ).fetchone()

    if not issue:
        conn.close()
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    # Get all comments (no per-comment sentiment)
    comments = conn.execute(
        """SELECT c.id, c.comment, c.created_at, c.commenter_name,
                  c.commenter_role, c.is_auto_generated
           FROM comments c
           WHERE c.issue_id = ?
           ORDER BY c.created_at""",
        (issue_id,),
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        "issue_detail.html",
        {
            "request": request,
            "issue": dict(issue),
            "comments": [dict(r) for r in comments],
        },
    )
