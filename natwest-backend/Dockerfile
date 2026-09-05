FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY natwest-shared ./natwest-shared
COPY natwest-backend ./natwest-backend

WORKDIR /app/natwest-backend

USER root

ENV UV_PROJECT_ENVIRONMENT="/app/natwest-backend/.venv"

RUN uv sync --no-dev

ENV PATH="/app/natwest-backend/.venv/bin:$PATH"
ENV PYTHONPATH="/app/natwest-backend/src"

CMD ["sh", "-c", "uvicorn natwest_backend.api.app:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000}"]