"""FastAPI application with Jinja2 templates and HTMX support."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.routes import dashboard, employees, departments, issues

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="SeeClickFix Sentiment Analysis")

# Mount static files
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

@app.get("/up")
def health_check():
    return PlainTextResponse("ok")

# Include routers
app.include_router(dashboard.router)
app.include_router(employees.router)
app.include_router(departments.router)
app.include_router(issues.router)
