"""Department routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.models.database import get_db

router = APIRouter(prefix="/departments")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("")
async def list_departments(request: Request):
    conn = get_db()

    departments = conn.execute(
        """SELECT d.id, d.name, d.employee_count,
                  s.analyzed_comments, s.total_comments,
                  s.positive_count, s.negative_count, s.neutral_count, s.mixed_count,
                  s.positive_pct, s.negative_pct,
                  s.avg_vader_compound,
                  s.outcome_positive_pct, s.outcome_negative_pct
           FROM departments d
           LEFT JOIN department_sentiment_summary s ON s.department_id = d.id
           ORDER BY d.name"""
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        "departments.html",
        {
            "request": request,
            "departments": [dict(r) for r in departments],
        },
    )


@router.get("/{department_id}")
async def department_detail(request: Request, department_id: int):
    conn = get_db()

    department = conn.execute(
        "SELECT * FROM departments WHERE id = ?", (department_id,)
    ).fetchone()

    if not department:
        conn.close()
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    summary = conn.execute(
        "SELECT * FROM department_sentiment_summary WHERE department_id = ?",
        (department_id,),
    ).fetchone()

    # Employees in this department with their sentiment
    employees = conn.execute(
        """SELECT e.id, e.name_parsed, e.name_raw, e.title_parsed,
                  s.analyzed_comments, s.positive_pct, s.negative_pct,
                  s.avg_vader_compound,
                  s.outcome_positive_pct, s.outcome_negative_pct
           FROM employees e
           LEFT JOIN employee_sentiment_summary s ON s.employee_id = e.id
           WHERE e.department_id = ?
           ORDER BY s.analyzed_comments DESC NULLS LAST""",
        (department_id,),
    ).fetchall()

    # Recent issues handled by this department, with issue-level sentiment
    recent_issues = conn.execute(
        """SELECT DISTINCT i.id, i.summary, i.status, i.created_at,
                  i.html_url, i.address, i.request_type,
                  isent.resolved_label, isent.resolved_confidence,
                  isent.outcome_label, isent.outcome_confidence
           FROM issues i
           JOIN comments c ON c.issue_id = i.id
           JOIN employees e ON e.commenter_id = c.commenter_id
           LEFT JOIN issue_sentiment isent ON isent.issue_id = i.id
           WHERE e.department_id = ?
           AND c.is_auto_generated = 0
           ORDER BY i.created_at DESC
           LIMIT 50""",
        (department_id,),
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        "department_detail.html",
        {
            "request": request,
            "department": dict(department),
            "summary": dict(summary) if summary else None,
            "employees": [dict(r) for r in employees],
            "recent_issues": [dict(r) for r in recent_issues],
        },
    )
