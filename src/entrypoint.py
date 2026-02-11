"""Production entrypoint — uvicorn as PID 1, pipeline in background.

Usage:  python -m src.entrypoint
"""

from __future__ import annotations

import logging
import time

import httpx
import uvicorn

from src.config import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    PIPELINE_PER_PAGE,
    PIPELINE_START_DATE,
    WEB_HOST,
    WEB_PORT,
)
from src.models.database import init_db
from src.pipeline import start_pipeline_thread

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

OLLAMA_TIMEOUT = 300  # seconds to wait for Ollama to become ready


def ensure_ollama() -> None:
    """Wait for the Ollama sidecar to be reachable and pull the model if needed."""
    deadline = time.monotonic() + OLLAMA_TIMEOUT
    log.info("Waiting for Ollama at %s ...", OLLAMA_URL)

    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            if any(OLLAMA_MODEL in n or n.startswith(OLLAMA_MODEL.split(":")[0]) for n in models):
                log.info("Ollama ready — model %s available", OLLAMA_MODEL)
                return
            # Ollama is up but model not pulled yet
            log.info("Pulling model %s (this may take a while) ...", OLLAMA_MODEL)
            pull_resp = httpx.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": OLLAMA_MODEL, "stream": False},
                timeout=1800.0,  # 30 min for large model downloads
            )
            pull_resp.raise_for_status()
            log.info("Model %s pulled successfully", OLLAMA_MODEL)
            return
        except (httpx.HTTPError, httpx.TimeoutException):
            time.sleep(5)

    raise RuntimeError(
        f"Ollama at {OLLAMA_URL} not reachable after {OLLAMA_TIMEOUT}s"
    )


def main() -> None:
    init_db()
    ensure_ollama()

    start_pipeline_thread(
        start_date=PIPELINE_START_DATE,
        per_page=PIPELINE_PER_PAGE,
        noisy=True,
    )

    log.info("Starting uvicorn on %s:%d", WEB_HOST, WEB_PORT)
    uvicorn.run(
        "src.web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
