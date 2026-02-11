"""Employee routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, Query
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.models.database import get_db

router = APIRouter(prefix="/employees")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def list_employees(
    request: Request,
    sort: str = Query("positive_pct", pattern="^(name|dept|positive_pct|negative_pct|comments|avg_sentiment)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    conn = get_db()

    sort_map = {
        "name": "e.name_parsed",
        "dept": "d.name",
        "positive_pct": "s.positive_pct",
        "negative_pct": "s.negative_pct",
        "comments": "s.analyzed_comments",
        "avg_sentiment": "s.avg_vader_compound",
    }
    sort_col = sort_map.get(sort, "s.positive_pct")
    order_dir = "DESC" if order == "desc" else "ASC"

    employees = conn.execute(
        f"""SELECT e.id, e.name_parsed, e.name_raw, e.title_parsed,
                   d.name as dept_name, d.id as dept_id,
                   s.analyzed_comments, s.total_comments,
                   s.positive_count, s.negative_count, s.neutral_count, s.mixed_count,
                   s.positive_pct, s.negative_pct,
                   s.avg_vader_compound
            FROM employees e
            LEFT JOIN departments d ON d.id = e.department_id
            LEFT JOIN employee_sentiment_summary s ON s.employee_id = e.id
            ORDER BY {sort_col} {order_dir} NULLS LAST"""
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        "employees.html",
        {
            "request": request,
            "employees": [dict(r) for r in employees],
            "sort": sort,
            "order": order,
        },
    )


@router.get("/{employee_id}")
async def employee_detail(request: Request, employee_id: int):
    conn = get_db()

    employee = conn.execute(
        """SELECT e.*, d.name as dept_name
           FROM employees e
           LEFT JOIN departments d ON d.id = e.department_id
           WHERE e.id = ?""",
        (employee_id,),
    ).fetchone()

    if not employee:
        conn.close()
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    summary = conn.execute(
        "SELECT * FROM employee_sentiment_summary WHERE employee_id = ?",
        (employee_id,),
    ).fetchone()

    # Get all issues this employee commented on, with issue-level sentiment
    issues = conn.execute(
        """SELECT DISTINCT i.id, i.summary, i.status, i.created_at, i.html_url,
                  i.request_type, i.address,
                  isent.resolved_label, isent.resolved_confidence
           FROM issues i
           JOIN comments c ON c.issue_id = i.id
           LEFT JOIN issue_sentiment isent ON isent.issue_id = i.id
           WHERE c.commenter_id = ?
           AND c.is_auto_generated = 0
           ORDER BY i.created_at DESC
           LIMIT 100""",
        (employee["commenter_id"],),
    ).fetchall()

    # Get recent comments (no per-comment sentiment)
    recent_comments = conn.execute(
        """SELECT c.id, c.comment, c.created_at, c.issue_id,
                  i.summary as issue_summary, i.html_url
           FROM comments c
           JOIN issues i ON i.id = c.issue_id
           WHERE c.commenter_id = ?
           AND c.is_auto_generated = 0
           AND c.comment != ''
           ORDER BY c.created_at DESC
           LIMIT 50""",
        (employee["commenter_id"],),
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        "employee_detail.html",
        {
            "request": request,
            "employee": dict(employee),
            "summary": dict(summary) if summary else None,
            "issues": [dict(r) for r in issues],
            "recent_comments": [dict(r) for r in recent_comments],
        },
    )
