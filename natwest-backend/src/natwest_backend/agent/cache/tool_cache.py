from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis
from natwest_shared.utils.logger import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "tool_cache:"

# Default TTLs in seconds
CUSTOMER_CACHE_TTL = 300  # 5 minutes — customer profiles change rarely
DEFAULT_TOOL_CACHE_TTL = 300  # 5 minutes — other read-only results

# Tools that are safe to cache (read-only, no side effects)
CACHEABLE_TOOLS: dict[str, int] = {
    "get_customer_profile": CUSTOMER_CACHE_TTL,
    "get_customer_accounts": CUSTOMER_CACHE_TTL,
    "list_cases": DEFAULT_TOOL_CACHE_TTL,
    "get_case_details": DEFAULT_TOOL_CACHE_TTL,
    "get_case_timeline": DEFAULT_TOOL_CACHE_TTL,
    "get_next_actions": DEFAULT_TOOL_CACHE_TTL,
}


def _make_cache_key(tool_name: str, arguments: dict[str, Any]) -> str:
    """
    Build a deterministic cache key from tool name and arguments.

    Arguments are sorted and hashed to keep keys short and
    avoid issues with argument ordering.
    """
    args_str = json.dumps(arguments, sort_keys=True, default=str)
    args_hash = hashlib.sha256(args_str.encode()).hexdigest()[:16]
    return f"{_KEY_PREFIX}{tool_name}:{args_hash}"


class ToolResultCache:
    """
    Redis-backed cache for read-only MCP tool results.

    Usage:
        cache = ToolResultCache(redis_client)

        # Check cache before calling MCP
        cached = await cache.get("get_customer_by_name", {"name": "Globex"})
        if cached is not None:
            return cached

        # Call MCP and cache the result
        result = await mcp_connection.call_tool(...)
        await cache.set("get_customer_by_name", {"name": "Globex"}, result)
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def is_cacheable(self, tool_name: str) -> bool:
        """Return True if this tool's results should be cached."""
        return tool_name in CACHEABLE_TOOLS

    async def get(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str | None:
        """
        Look up a cached tool result.

        Returns None on cache miss or if the tool is not cacheable.
        """
        if not self.is_cacheable(tool_name):
            return None

        key = _make_cache_key(tool_name, arguments)

        try:
            result = await self._redis.get(key)
            if result is not None:
                logger.info("Cache HIT | tool: %s | key: %s", tool_name, key)
                return result  # type: ignore
            logger.info("Cache MISS | tool: %s | key: %s", tool_name, key)
        except Exception:
            logger.exception("Cache GET failed | tool: %s", tool_name)

        return None

    async def set(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
    ) -> None:
        """
        Cache a tool result with the appropriate TTL.

        Only caches if the tool is in CACHEABLE_TOOLS and
        the result is not an error.
        """
        if not self.is_cacheable(tool_name):
            return

        if result.startswith("Error:"):
            return

        key = _make_cache_key(tool_name, arguments)
        ttl = CACHEABLE_TOOLS[tool_name]

        try:
            await self._redis.set(key, result, ex=ttl)
            logger.info(
                "Cache SET | tool: %s | key: %s | ttl: %ds",
                tool_name,
                key,
                ttl,
            )
        except Exception:
            logger.exception("Cache SET failed | tool: %s", tool_name)

    async def invalidate(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Explicitly remove a cached result."""
        key = _make_cache_key(tool_name, arguments)
        try:
            await self._redis.delete(key)
        except Exception:
            logger.exception("Cache invalidate failed | tool: %s", tool_name)
