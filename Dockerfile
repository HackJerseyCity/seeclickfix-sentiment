FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .
RUN mkdir -p /app/data

ENV DATA_DIR=/app/data \
    OLLAMA_URL=http://seeclickfix-ollama:11434 \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/').raise_for_status()"

CMD ["python", "-m", "src.entrypoint"]
