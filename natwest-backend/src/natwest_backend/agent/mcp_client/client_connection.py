from __future__ import annotations

import json
from typing import Any

from natwest_shared.utils.logger import get_logger
from mcp import ClientSession
from mcp.types import Tool as MCPToolDefinition

from .result_parser import extract_text_content

logger = get_logger(__name__)


class MCPConnection:
    """
    Active authenticated connection to the MCP server.

    Provides tool discovery (cached per connection) and
    tool invocation with result serialisation.

    When a ToolResultCache is provided, read-only tool
    results are checked against Redis before making
    MCP round-trips.
    """

    def __init__(
        self,
        session: ClientSession,
        tool_cache: Any | None = None,
    ) -> None:
        self._session = session
        self._tools: list[MCPToolDefinition] | None = None
        self._tool_cache = tool_cache

    async def list_tools(self) -> list[MCPToolDefinition]:
        """
        Discover available MCP tools.

        Results are cached for the lifetime of the connection so
        multiple calls within a single agent run do not re-fetch.
        """
        if self._tools is None:
            result = await self._session.list_tools()
            self._tools = result.tools
            logger.info("Discovered %d MCP tools", len(self._tools))
        return self._tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> str:
        """
        Invoke an MCP tool and return the serialised text result.

        If a ToolResultCache is configured, checks Redis first
        for cacheable tools. Cache hits skip the MCP round-trip.
        """
        # --- Check cache ---
        if self._tool_cache is not None:
            cached = await self._tool_cache.get(name, arguments)
            if cached is not None:
                return cached

        logger.info(
            "MCP tool call: %s | args: %s",
            name,
            json.dumps(arguments, default=str),
        )

        result = await self._session.call_tool(name, arguments)
        response = extract_text_content(result.content)

        if result.isError:
            logger.warning("MCP tool %s returned error: %s", name, response)
            return f"Error: {response}"

        logger.info("MCP tool %s completed successfully", name)

        # --- Cache result ---
        if self._tool_cache is not None:
            await self._tool_cache.set(name, arguments, response)

        return response
