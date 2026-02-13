"""Centralised configuration — all tunables read from env vars with safe defaults."""

import os
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
LLM_BACKEND = os.environ.get("LLM_BACKEND", "openai")  # "openai" or "ollama"
LLM_CONCURRENCY = int(os.environ.get("LLM_CONCURRENCY", "4"))

DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent.parent / "data")))
DB_PATH = DATA_DIR / "seeclickfix.db"

PIPELINE_START_DATE = os.environ.get("PIPELINE_START_DATE", "2015-01-01")
PIPELINE_PER_PAGE = int(os.environ.get("PIPELINE_PER_PAGE", "100"))

WEB_HOST = os.environ.get("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("WEB_PORT", "8000"))
