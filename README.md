# SeeClickFix Sentiment Analysis

Sentiment analysis of Jersey City employee responses on [SeeClickFix](https://seeclickfix.com), a civic issue reporting platform. Crawls ~164k issues and their comment threads, identifies city employees ("Verified Officials"), and classifies the sentiment of their responses to residents.

The result is a web dashboard for browsing employee and department sentiment scores, with links back to the original SeeClickFix posts.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Run a demo: crawl a small sample, analyze, and launch the web UI
python -m src.cli demo --no-roberta
```

Then open http://127.0.0.1:8000.

The `--no-roberta` flag uses VADER-only sentiment (fast, no model download). Drop it to enable the full tiered pipeline with RoBERTa (more accurate on ambiguous comments, but requires downloading a ~500MB model on first run).

## Full Pipeline

Each step is a separate CLI command. Run them in order, or re-run individually as needed.

### 1. Crawl

```bash
# Full crawl (all issues since 2015, then all comments)
python -m src.cli crawl

# Crawl a specific date range
python -m src.cli crawl --start-date 2024-01-01 --end-date 2024-12-31

# Crawl with limits (useful for testing)
python -m src.cli crawl --issues 500 --comments 100

# Issues and comments can be crawled separately
python -m src.cli crawl-issues --start-date 2025-01-01
python -m src.cli crawl-comments --limit 200
```

The crawler uses date-windowed pagination (monthly windows) to work around the API's internal result-count cap. It checkpoints after each window, so you can stop and resume at any time by re-running the same command.

Rate limiting is handled automatically at 20 requests/minute with `Retry-After` header respect and exponential backoff on server errors.

### 2. Extract employees

```bash
python -m src.cli extract
```

This does two things:
- **Flags auto-generated comments** (assignment notifications, status changes) so they're excluded from sentiment analysis
- **Parses employee names** from the `commenter.name` field of Verified Official comments into structured name, title, and department fields

### 3. Analyze sentiment

```bash
# Full tiered pipeline (VADER + RoBERTa)
python -m src.cli analyze

# VADER only (faster, no model download)
python -m src.cli analyze --no-roberta
```

**Tiered approach:**

| Tier | Model | When used | Speed |
|------|-------|-----------|-------|
| Pre-filter | regex | Auto-generated comments (assignments, status changes) | instant |
| Tier 1 | VADER | All conversations; accepts if \|compound\| > 0.5 | ~1k issues/sec |
| Tier 2 | RoBERTa (`cardiffnlp/twitter-roberta-base-sentiment-latest`) | VADER-ambiguous conversations | ~50 issues/sec |

Sentiment is analyzed per **issue conversation** — all non-auto-generated comments (resident + employee) are concatenated and scored as a single unit. Each issue gets a resolved label (`positive`, `negative`, `neutral`, `mixed`) with a confidence score and which tier resolved it. Results are aggregated into per-employee and per-department summary tables.

### 4. Serve the web UI

```bash
python -m src.cli serve
python -m src.cli serve --port 3000 --reload  # dev mode
```

### All-in-one: `live`

Starts the web server immediately, then crawls, extracts, and analyzes issue by issue. Refresh the browser at any time to see progress.

```bash
# Full pipeline with live UI
python -m src.cli live --start-date 2024-01-01

# VADER-only, verbose per-issue logging
python -m src.cli live --start-date 2024-01-01 --no-roberta --noisy

# Re-run sentiment analysis on existing data (no crawling)
python -m src.cli live --reanalyze
python -m src.cli live --reanalyze --no-roberta --noisy
```

| Flag | Effect |
|------|--------|
| `--start-date` / `--end-date` | Date range to crawl |
| `--no-roberta` | VADER-only (fast, no model download) |
| `--noisy` | Per-issue logging: comments, employees, sentiment scores |
| `--reanalyze` | Skip crawl/extract, wipe and re-score all existing issues |
| `--force` | Reset crawl progress and sentiment, start over |
| `--per-page` | Issues per API page (default 100) |
| `--host` / `--port` | Web server bind address (default 127.0.0.1:8000) |

### Other commands

```bash
python -m src.cli stats    # Show database statistics
python -m src.cli reset    # Delete all data and reinitialize
```

## Web UI

Server-rendered HTML with [Pico CSS](https://picocss.com/) and [HTMX](https://htmx.org/). No JS build step.

| Route | Page |
|-------|------|
| `/` | Dashboard: crawl progress, top/bottom employees, department rankings |
| `/employees` | Sortable employee table with sentiment distribution bars |
| `/employees/{id}` | Employee detail: sentiment breakdown, recent comments with labels, issue history |
| `/departments` | Department list with aggregate scores |
| `/departments/{id}` | Department detail: employee roster, recent issues |
| `/issues/{id}` | Full comment thread with conversation-level sentiment |

Every issue and employee page links to the original SeeClickFix post.

## Project Structure

```
src/
  models/
    schema.py          # Pydantic models (API responses + DB records)
    database.py        # SQLite schema, connection management
  crawler/
    client.py          # Async API client, rate limiter, date-windowed crawl
  extraction/
    employees.py       # Auto-comment detection, name/title/dept parsing
  sentiment/
    analyzer.py        # VADER + RoBERTa pipeline, summary builder
  web/
    app.py             # FastAPI application
    routes/            # dashboard, employees, departments, issues
    templates/         # Jinja2 templates
  cli.py               # Typer CLI
data/                  # SQLite database (gitignored)
```

## How It Works

**Crawling**: The SeeClickFix API is rate-limited to 20 requests/minute and caps results at ~1000 per query. The crawler splits the full date range into monthly windows and paginates within each, checkpointing progress to SQLite. Issues are fetched first (list endpoint), then comments are fetched individually per issue.

**Employee extraction**: Verified Official commenter names follow patterns like `"Code Compliance Inspector - Brian"` or `"Traffic: Sean G"`. The extractor splits on separator characters and maps title keywords to departments. Auto-generated comments ("assigned this issue to...", "changed the status...") are flagged and excluded from analysis.

**Sentiment analysis**: All non-auto-generated comments on an issue are concatenated into a single conversation text and scored together. VADER handles clear-cut cases quickly (~70% of issues). Ambiguous conversations (VADER compound score between -0.5 and 0.5) fall through to RoBERTa for a more nuanced classification. Results are stored per-issue and aggregated into employee and department summary tables.

## Requirements

- Python 3.11+
- ~500MB disk for the RoBERTa model (downloaded on first `analyze` without `--no-roberta`)
- ~100MB for the full SQLite database after a complete crawl
