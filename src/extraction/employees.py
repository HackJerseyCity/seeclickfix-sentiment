"""Employee name/title/department extraction from Verified Official commenter names."""

from __future__ import annotations

import re

from rich.console import Console

from src.models.database import get_db

console = Console()

# Patterns for auto-generated comments
AUTO_GENERATED_PATTERNS = [
    re.compile(r"assigned this issue to", re.IGNORECASE),
    re.compile(r"marked as\s+(closed|open|acknowledged)", re.IGNORECASE),
    re.compile(r"changed the status", re.IGNORECASE),
    re.compile(r"reopened this issue", re.IGNORECASE),
    re.compile(r"flagged this issue", re.IGNORECASE),
    re.compile(r"voted for this issue", re.IGNORECASE),
]

# Template closer patterns (kept but flagged)
TEMPLATE_PATTERNS = [
    re.compile(
        r"Thank you for reporting an issue to the City",
        re.IGNORECASE,
    ),
]

# Department keyword mappings
# Sorted longest-first so "building & streets" matches before "building"
DEPARTMENT_KEYWORDS = [
    ("office of code compliance", "Code Compliance"),
    ("health & human services", "Health & Human Services"),
    ("building & streets", "Building & Streets"),
    ("tenant and landlord", "Tenant & Landlord Services"),
    ("tenant & landlord", "Tenant & Landlord Services"),
    ("code compliance", "Code Compliance"),
    ("code enforcement", "Code Compliance"),
    ("animal control", "Animal Control"),
    ("municipal court", "Municipal Court"),
    ("quality of life", "Quality of Life"),
    ("public works", "DPW"),
    ("construction", "Construction"),
    ("engineering", "Engineering"),
    ("constituent", "Constituent Services"),
    ("infrastructure", "Infrastructure"),
    ("sanitation", "Sanitation"),
    ("recreation", "Recreation"),
    ("traffic", "Traffic"),
    ("parking", "Parking"),
    ("housing", "Housing"),
    ("streets", "Streets"),
    ("zoning", "Zoning"),
    ("health", "Health"),
    ("building", "Building"),
    ("police", "Police"),
    ("water", "Water"),
    ("sewer", "Water/Sewer"),
    ("parks", "Parks"),
    ("noise", "Quality of Life"),
    ("fire", "Fire"),
    ("dpw", "DPW"),
    ("occ", "Code Compliance"),
    ("rrc", "Resident Response Center"),
    ("hhs", "Health & Human Services"),
]

# Names that indicate system accounts, not real employees
SYSTEM_NAMES = {"Jersey City, NJ", "SeeClickFix", "System"}


def is_auto_generated(comment_text: str) -> bool:
    """Check if a comment is auto-generated (assignment, status change, etc.)."""
    for pattern in AUTO_GENERATED_PATTERNS:
        if pattern.search(comment_text):
            return True
    return False


def is_template(comment_text: str) -> bool:
    """Check if a comment is a template response."""
    for pattern in TEMPLATE_PATTERNS:
        if pattern.search(comment_text):
            return True
    return False


def parse_employee_name(raw_name: str) -> dict:
    """Parse an employee's raw name into title, name, and department.

    Examples:
        "Code Compliance Inspector: Anissa" -> {title: "Code Compliance Inspector", name: "Anissa", dept: "Code Compliance"}
        "Code Compliance Commercial Unit Supervisor - David" -> {title: "CC Commercial Unit Supervisor", name: "David", dept: "Code Compliance"}
        "Traffic - Sean G" -> {title: "Traffic", name: "Sean G", dept: "Traffic"}
        "Jersey City, NJ" -> {title: None, name: None, dept: None, is_system: True}
    """
    result = {
        "name_raw": raw_name,
        "name_parsed": None,
        "title_parsed": None,
        "department": None,
        "is_system": False,
    }

    if raw_name in SYSTEM_NAMES:
        result["is_system"] = True
        return result

    # Try splitting on separators (various spacing patterns)
    # " - ", "- ", " -", ": "
    split_match = re.split(r'\s*[-–]\s+|\s+[-–]\s*|:\s+', raw_name, maxsplit=1)
    if len(split_match) == 2:
        result["title_parsed"] = split_match[0].strip()
        result["name_parsed"] = split_match[1].strip()
    else:
        # No separator found - try matching known department prefix + name
        name_lower = raw_name.lower()
        matched = False
        for keyword, dept in DEPARTMENT_KEYWORDS:
            if name_lower.startswith(keyword + " "):
                result["title_parsed"] = raw_name[:len(keyword)]
                result["name_parsed"] = raw_name[len(keyword):].strip()
                result["department"] = dept
                matched = True
                break
        if not matched:
            result["name_parsed"] = raw_name

    # Map title to department (if not already set)
    if result["title_parsed"] and not result["department"]:
        title_lower = result["title_parsed"].lower()
        for keyword, dept in DEPARTMENT_KEYWORDS:
            if keyword in title_lower:
                result["department"] = dept
                break

    return result


def flag_auto_generated_comments() -> int:
    """Flag auto-generated comments in the database. Returns count flagged."""
    conn = get_db()
    comments = conn.execute(
        "SELECT id, comment FROM comments WHERE is_auto_generated = 0"
    ).fetchall()

    flagged = 0
    for row in comments:
        if is_auto_generated(row["comment"]):
            conn.execute(
                "UPDATE comments SET is_auto_generated = 1 WHERE id = ?",
                (row["id"],),
            )
            flagged += 1

    conn.commit()
    conn.close()
    console.print(f"[green]Flagged {flagged} auto-generated comments[/green]")
    return flagged


def extract_employees() -> int:
    """Extract employees from Verified Official commenters. Returns count extracted."""
    conn = get_db()

    # Clear dependent summary tables before rebuilding employees
    conn.execute("DELETE FROM employee_sentiment_summary")
    conn.execute("DELETE FROM department_sentiment_summary")

    # Get unique Verified Official commenters
    officials = conn.execute(
        """SELECT DISTINCT commenter_id, commenter_name
           FROM comments
           WHERE commenter_role = 'Verified Official'
           AND commenter_id IS NOT NULL
           AND commenter_name IS NOT NULL"""
    ).fetchall()

    extracted = 0
    for row in officials:
        parsed = parse_employee_name(row["commenter_name"])

        if parsed["is_system"]:
            continue

        # Get or create department
        dept_id = None
        if parsed["department"]:
            existing = conn.execute(
                "SELECT id FROM departments WHERE name = ?",
                (parsed["department"],),
            ).fetchone()

            if existing:
                dept_id = existing["id"]
            else:
                cursor = conn.execute(
                    "INSERT INTO departments (name) VALUES (?)",
                    (parsed["department"],),
                )
                dept_id = cursor.lastrowid

        # Get comment count for this employee
        count = conn.execute(
            """SELECT COUNT(*) FROM comments
               WHERE commenter_id = ? AND is_auto_generated = 0""",
            (row["commenter_id"],),
        ).fetchone()[0]

        conn.execute(
            """INSERT OR REPLACE INTO employees
               (commenter_id, name_raw, name_parsed, title_parsed,
                department_id, comment_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                row["commenter_id"],
                parsed["name_raw"],
                parsed["name_parsed"],
                parsed["title_parsed"],
                dept_id,
                count,
            ),
        )
        extracted += 1

    # Update department employee counts
    conn.execute(
        """UPDATE departments SET employee_count = (
               SELECT COUNT(*) FROM employees WHERE department_id = departments.id
           )"""
    )

    conn.commit()
    conn.close()
    console.print(f"[green]Extracted {extracted} employees[/green]")
    return extracted


def run_extraction() -> dict:
    """Run the full extraction pipeline."""
    flagged = flag_auto_generated_comments()
    extracted = extract_employees()
    return {"auto_generated_flagged": flagged, "employees_extracted": extracted}
