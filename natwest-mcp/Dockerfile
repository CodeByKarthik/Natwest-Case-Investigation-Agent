FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Keep the workspace root so uv can identify natwest-shared as a workspace member.
COPY pyproject.toml uv.lock ./
COPY natwest-shared ./natwest-shared
COPY natwest-mcp ./natwest-mcp

WORKDIR /app/natwest-mcp

ENV UV_PROJECT_ENVIRONMENT="/app/natwest-mcp/.venv"
RUN uv sync --no-dev

ENV PATH="/app/natwest-mcp/.venv/bin:$PATH"
ENV PYTHONPATH="/app/natwest-mcp/src:/app/natwest-shared/src"
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "natwest_mcp.mcp.server"]