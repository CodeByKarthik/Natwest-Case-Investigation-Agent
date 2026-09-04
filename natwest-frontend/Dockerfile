FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

ENV UV_PROJECT_ENVIRONMENT="/app/.venv"
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"


CMD ["sh", "-c", "streamlit run src/natwest_frontend/app.py --server.port=${STREAMLIT_PORT} --server.address=${STREAMLIT_HOST}"]