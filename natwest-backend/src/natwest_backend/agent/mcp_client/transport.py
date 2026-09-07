from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from natwest_shared.utils.logger import get_logger

from .client_connection import MCPConnection

logger = get_logger(__name__)


@asynccontextmanager
async def connect_mcp(
    url: str,
    token: str,
    tool_cache: Any | None = None,
) -> AsyncIterator[MCPConnection]:
    """
    Open an authenticated MCP client session.

    The bearer token is forwarded to the MCP server on every
    request so that server-side RBAC can enforce permissions.

    When a ToolResultCache is provided, it is passed to the
    MCPConnection for read-only tool result caching.
    """
    headers = {"Authorization": f"Bearer {token}"}
    http_client = httpx.AsyncClient(headers=headers)

    async with (
        http_client,
        streamable_http_client(
            url=url,
            http_client=http_client,  # type: ignore[arg-type]
        ) as (read_stream, write_stream),
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            logger.info("MCP session established: %s", url)
            yield MCPConnection(session, tool_cache=tool_cache)
