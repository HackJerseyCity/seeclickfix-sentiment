"""SQLite database initialization and connection management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_DIR / "seeclickfix.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY,
    status TEXT,
    summary TEXT,
    description TEXT,
    lat REAL,
    lng REAL,
    address TEXT,
    created_at TEXT,
    updated_at TEXT,
    closed_at TEXT,
    acknowledged_at TEXT,
    request_type TEXT,
    department TEXT,
    html_url TEXT,
    comment_count INTEGER DEFAULT 0,
    reporter_id INTEGER,
    reporter_name TEXT,
    comments_fetched INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY,
    issue_id INTEGER NOT NULL,
    comment TEXT DEFAULT '',
    created_at TEXT,
    updated_at TEXT,
    commenter_id INTEGER,
    commenter_name TEXT,
    commenter_role TEXT,
    is_auto_generated INTEGER DEFAULT 0,
    FOREIGN KEY (issue_id) REFERENCES issues(id)
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    employee_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commenter_id INTEGER UNIQUE NOT NULL,
    name_raw TEXT NOT NULL,
    name_parsed TEXT,
    title_parsed TEXT,
    department_id INTEGER,
    comment_count INTEGER DEFAULT 0,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS issue_sentiment (
    issue_id INTEGER PRIMARY KEY,
    total_comments INTEGER DEFAULT 0,
    text_length INTEGER DEFAULT 0,
    vader_compound REAL,
    vader_pos REAL,
    vader_neg REAL,
    vader_neu REAL,
    roberta_positive REAL,
    roberta_negative REAL,
    roberta_neutral REAL,
    resident_comment_count INTEGER DEFAULT 0,
    resolved_label TEXT,
    resolved_confidence REAL,
    resolved_by TEXT,
    FOREIGN KEY (issue_id) REFERENCES issues(id)
);

CREATE TABLE IF NOT EXISTS employee_sentiment_summary (
    employee_id INTEGER PRIMARY KEY,
    total_comments INTEGER DEFAULT 0,
    analyzed_comments INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    mixed_count INTEGER DEFAULT 0,
    avg_vader_compound REAL,
    avg_roberta_positive REAL,
    avg_roberta_negative REAL,
    positive_pct REAL,
    negative_pct REAL,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS department_sentiment_summary (
    department_id INTEGER PRIMARY KEY,
    total_comments INTEGER DEFAULT 0,
    analyzed_comments INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    mixed_count INTEGER DEFAULT 0,
    avg_vader_compound REAL,
    positive_pct REAL,
    negative_pct REAL,
    FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS crawl_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed
    page INTEGER DEFAULT 1,
    issues_fetched INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_comments_issue_id ON comments(issue_id);
CREATE INDEX IF NOT EXISTS idx_comments_commenter_id ON comments(commenter_id);
CREATE INDEX IF NOT EXISTS idx_comments_commenter_role ON comments(commenter_role);
CREATE INDEX IF NOT EXISTS idx_employees_department_id ON employees(department_id);
CREATE INDEX IF NOT EXISTS idx_issues_created_at ON issues(created_at);
CREATE INDEX IF NOT EXISTS idx_issues_department ON issues(department);
CREATE INDEX IF NOT EXISTS idx_issues_request_type ON issues(request_type);
"""


def get_db() -> sqlite3.Connection:
    """Get a database connection with WAL mode and foreign keys enabled."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Run lightweight migrations for schema changes."""
    # Add resident_comment_count to issue_sentiment if missing
    cols = {row[1] for row in conn.execute("PRAGMA table_info(issue_sentiment)").fetchall()}
    if cols and "resident_comment_count" not in cols:
        conn.execute("ALTER TABLE issue_sentiment ADD COLUMN resident_comment_count INTEGER DEFAULT 0")
        conn.commit()


def init_db() -> None:
    """Initialize the database schema."""
    conn = get_db()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.close()
