"""Dashboard route - main landing page."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.models.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/")
async def dashboard(request: Request):
    conn = get_db()

    # Overall stats
    issue_count = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    comment_count = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    employee_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    dept_count = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    analyzed_count = conn.execute("SELECT COUNT(*) FROM issue_sentiment").fetchone()[0]

    # Crawl progress
    crawl_windows = conn.execute(
        """SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress
           FROM crawl_state"""
    ).fetchone()

    # Top 10 employees by positive sentiment
    top_employees = conn.execute(
        """SELECT e.id, e.name_parsed, e.name_raw, e.title_parsed, d.name as dept_name,
                  s.analyzed_comments, s.positive_pct, s.negative_pct,
                  s.avg_vader_compound
           FROM employee_sentiment_summary s
           JOIN employees e ON e.id = s.employee_id
           LEFT JOIN departments d ON d.id = e.department_id
           WHERE s.analyzed_comments >= 5
           ORDER BY s.positive_pct DESC
           LIMIT 10"""
    ).fetchall()

    # Bottom 10 employees by sentiment (most negative)
    bottom_employees = conn.execute(
        """SELECT e.id, e.name_parsed, e.name_raw, e.title_parsed, d.name as dept_name,
                  s.analyzed_comments, s.positive_pct, s.negative_pct,
                  s.avg_vader_compound
           FROM employee_sentiment_summary s
           JOIN employees e ON e.id = s.employee_id
           LEFT JOIN departments d ON d.id = e.department_id
           WHERE s.analyzed_comments >= 5
           ORDER BY s.negative_pct DESC
           LIMIT 10"""
    ).fetchall()

    # Department rankings
    dept_rankings = conn.execute(
        """SELECT d.id, d.name, d.employee_count,
                  s.analyzed_comments, s.positive_pct, s.negative_pct,
                  s.avg_vader_compound
           FROM department_sentiment_summary s
           JOIN departments d ON d.id = s.department_id
           WHERE s.analyzed_comments >= 5
           ORDER BY s.positive_pct DESC"""
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "issue_count": issue_count,
            "comment_count": comment_count,
            "employee_count": employee_count,
            "dept_count": dept_count,
            "analyzed_count": analyzed_count,
            "crawl_windows": dict(crawl_windows) if crawl_windows else {},
            "top_employees": [dict(r) for r in top_employees],
            "bottom_employees": [dict(r) for r in bottom_employees],
            "dept_rankings": [dict(r) for r in dept_rankings],
        },
    )
