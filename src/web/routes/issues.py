"""Issue routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.models.database import get_db

router = APIRouter(prefix="/issues")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

SORT_COLUMNS = {
    "id": "i.id",
    "date": "i.created_at",
    "interaction": "isent.resolved_label",
    "outcome": "isent.outcome_label",
    "confidence": "isent.resolved_confidence",
}


@router.get("")
async def issue_list(
    request: Request,
    sort: str = Query("date", alias="sort"),
    order: str = Query("desc", alias="order"),
    label: str = Query("", alias="label"),
    outcome: str = Query("", alias="outcome"),
):
    conn = get_db()

    order_col = SORT_COLUMNS.get(sort, "i.created_at")
    order_dir = "ASC" if order == "asc" else "DESC"

    where_clauses = ["isent.issue_id IS NOT NULL"]
    params: list = []

    if label in ("positive", "negative", "neutral", "mixed"):
        where_clauses.append("isent.resolved_label = ?")
        params.append(label)

    if outcome in ("positive", "negative", "neutral", "mixed"):
        where_clauses.append("isent.outcome_label = ?")
        params.append(outcome)

    where_sql = " AND ".join(where_clauses)

    issues = conn.execute(
        f"""SELECT i.id, i.summary, i.status, i.created_at, i.department,
                   isent.resolved_label as sentiment_label,
                   isent.resolved_confidence as sentiment_confidence,
                   isent.llm_reasoning as sentiment_reasoning,
                   isent.outcome_label,
                   isent.outcome_confidence,
                   isent.outcome_reasoning,
                   isent.total_comments as sentiment_comments
            FROM issues i
            JOIN issue_sentiment isent ON isent.issue_id = i.id
            WHERE {where_sql}
            ORDER BY {order_col} {order_dir}""",
        params,
    ).fetchall()

    # Counts for filter badges
    counts = conn.execute(
        """SELECT resolved_label, COUNT(*) as cnt
           FROM issue_sentiment
           GROUP BY resolved_label"""
    ).fetchall()
    label_counts = {r["resolved_label"]: r["cnt"] for r in counts}

    outcome_counts_rows = conn.execute(
        """SELECT outcome_label, COUNT(*) as cnt
           FROM issue_sentiment
           WHERE outcome_label IS NOT NULL
           GROUP BY outcome_label"""
    ).fetchall()
    outcome_counts = {r["outcome_label"]: r["cnt"] for r in outcome_counts_rows}

    total = conn.execute("SELECT COUNT(*) FROM issue_sentiment").fetchone()[0]

    conn.close()

    return templates.TemplateResponse(
        "issues.html",
        {
            "request": request,
            "issues": [dict(r) for r in issues],
            "total": total,
            "sort": sort,
            "order": order,
            "label": label,
            "outcome": outcome,
            "label_counts": label_counts,
            "outcome_counts": outcome_counts,
        },
    )


@router.get("/{issue_id}")
async def issue_detail(request: Request, issue_id: int):
    conn = get_db()

    # Get issue with conversation-level sentiment
    issue = conn.execute(
        """SELECT i.*, isent.resolved_label as sentiment_label,
                  isent.resolved_confidence as sentiment_confidence,
                  isent.vader_compound as sentiment_vader,
                  isent.resolved_by as sentiment_by,
                  isent.total_comments as sentiment_comments,
                  isent.llm_reasoning as sentiment_reasoning,
                  isent.outcome_label,
                  isent.outcome_confidence,
                  isent.outcome_reasoning
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
