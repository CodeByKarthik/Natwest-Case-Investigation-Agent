FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY natwest-shared ./natwest-shared

WORKDIR /app/natwest-shared

USER root

ENV UV_PROJECT_ENVIRONMENT="/app/natwest-shared/.venv"

RUN uv sync --no-dev

ENV PATH="/app/natwest-shared/.venv/bin:$PATH"
ENV PYTHONPATH="/app/natwest-shared/src"

RUN chmod +x scripts/db_entrypoint.sh