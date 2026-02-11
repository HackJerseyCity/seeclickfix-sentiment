"""Production entrypoint — uvicorn as PID 1, serves pre-computed data.

The pipeline and LLM analysis are run locally; data is pushed to the
server's persistent volume.

Usage:  python -m src.entrypoint
"""

from __future__ import annotations

import logging

import uvicorn

from src.config import WEB_HOST, WEB_PORT
from src.models.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def main() -> None:
    init_db()

    log.info("Starting uvicorn on %s:%d", WEB_HOST, WEB_PORT)
    uvicorn.run(
        "src.web.app:app",
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
