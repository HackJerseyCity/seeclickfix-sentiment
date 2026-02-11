# SeeClickFix Sentiment Analysis

Sentiment analysis of Jersey City employee responses on [SeeClickFix](https://seeclickfix.com), a civic issue reporting platform. Crawls ~164k issues and their comment threads, identifies city employees ("Verified Officials"), and uses a local LLM to classify sentiment across two dimensions: **interaction quality** (was the employee professional?) and **outcome** (was the problem fixed?).

The result is a web dashboard for browsing employee and department sentiment scores, with links back to the original SeeClickFix posts.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Install and start Ollama, then pull the model
ollama pull llama3.1:8b

# Run a demo: crawl a small sample, analyze, and launch the web UI
python -m src.cli demo
```

Then open http://127.0.0.1:8000.

## How Sentiment Works

Each issue's full comment thread is sent to a local LLM (Llama 3.1 8B via [Ollama](https://ollama.ai)) which scores two independent dimensions:

| Dimension | What it measures | Example |
|-----------|-----------------|---------|
| **Interaction** | Tone and quality of communication — professional, responsive, helpful? | A polite explanation of why no action is needed scores *positive* |
| **Outcome** | Was the reported problem actually resolved? | Issue acknowledged but not fixed scores *negative* |

This separation prevents conflating a professional response with a good outcome. An employee can be courteous (interaction: positive) while the pothole remains unfixed (outcome: negative). Employee and department aggregate scores use **interaction** sentiment as the performance metric.

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
python -m src.cli analyze
```

Requires Ollama running with the `llama3.1:8b` model. Each issue's full comment thread (resident + employee, excluding auto-generated messages) is sent to the LLM as a single prompt. The LLM returns JSON with both interaction and outcome scores. Results are aggregated into per-employee and per-department summary tables.

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

# Verbose per-issue logging
python -m src.cli live --start-date 2024-01-01 --noisy

# Re-run sentiment analysis on existing data (no crawling)
python -m src.cli live --reanalyze --noisy
```

| Flag | Effect |
|------|--------|
| `--start-date` / `--end-date` | Date range to crawl |
| `--noisy` | Per-issue logging: comments, employees, sentiment scores |
| `--reanalyze` | Skip crawl/extract, wipe and re-score all existing issues (newest first) |
| `--force` | Reset crawl progress and sentiment, start over |
| `--per-page` | Issues per API page (default 100) |
| `--host` / `--port` | Web server bind address (default 127.0.0.1:8000) |

### Other commands

```bash
python -m src.cli stats    # Show database statistics
python -m src.cli reset    # Delete all data and reinitialize
```

## Web UI

Server-rendered HTML with Jinja2 templates. No JS build step.

| Route | Page |
|-------|------|
| `/` | Dashboard: crawl progress, top/bottom employees, department rankings |
| `/issues` | All analyzed issues with interaction/outcome badges and filtering |
| `/employees` | Sortable employee table with interaction and outcome percentages |
| `/employees/{id}` | Employee detail: dual sentiment bars, recent comments, issue history |
| `/departments` | Department list with aggregate interaction and outcome scores |
| `/departments/{id}` | Department detail: employee roster, recent issues with both dimensions |
| `/issues/{id}` | Full comment thread with interaction and outcome sentiment |

Every issue and employee page links to the original SeeClickFix post.

## Project Structure

```
src/
  models/
    schema.py          # Pydantic models (API responses + DB records)
    database.py        # SQLite schema, connection management, migrations
  crawler/
    client.py          # Async API client, rate limiter, date-windowed crawl
  extraction/
    employees.py       # Auto-comment detection, name/title/dept parsing
  sentiment/
    llm.py             # Ollama LLM prompt + response parsing
    analyzer.py        # Analysis pipeline, summary builder
  web/
    app.py             # FastAPI application
    routes/            # dashboard, employees, departments, issues
    templates/         # Jinja2 templates
  cli.py               # Typer CLI
data/                  # SQLite database (gitignored)
```

## How It Works

**Crawling**: The SeeClickFix API is rate-limited to 20 requests/minute and caps results at ~1000 per query. The crawler splits the full date range into monthly windows and paginates within each, checkpointing progress to SQLite. Issues are fetched first (list endpoint), then comments are fetched individually per issue. Issues from outside Jersey City (e.g. Town of Kearny) are filtered out by organization name.

**Employee extraction**: Verified Official commenter names follow patterns like `"Code Compliance Inspector - Brian"` or `"Traffic: Sean G"`. The extractor splits on separator characters and maps title keywords to departments. Auto-generated comments ("assigned this issue to...", "changed the status...") are flagged and excluded from analysis.

**Sentiment analysis**: All non-auto-generated comments on an issue are sent to Llama 3.1 8B (via Ollama) as a structured prompt. The LLM returns two independent assessments — interaction quality and outcome resolution — each with a label, confidence score, and one-sentence reasoning. Results are stored per-issue and aggregated into employee and department summary tables using interaction sentiment as the performance metric.

## Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) running locally with `llama3.1:8b` pulled
- ~100MB for the full SQLite database after a complete crawl
