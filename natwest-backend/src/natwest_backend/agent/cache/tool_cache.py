from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from natwest_shared.utils.logger import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "tool_cache:"

# 5 minutes — these tools return data that is immutable within a workflow
# run (customer identity, profile, vulnerability register, accounts).
CUSTOMER_CACHE_TTL = 300

# Tools safe to cache: read-only, no RBAC scope-filtering (identical
# response regardless of caller role), and not mutated by any write tool
# in this workflow. Case/action tools are deliberately excluded — cases
# change via update_case_status, timelines grow, and next actions change
# status, so those reads must always be fresh.
CACHEABLE_TOOLS: dict[str, int] = {
    "list_customers": CUSTOMER_CACHE_TTL,
    "get_customer_profile": CUSTOMER_CACHE_TTL,
    "get_customer_accounts": CUSTOMER_CACHE_TTL,
}


def _make_cache_key(tool_name: str, arguments: dict[str, Any]) -> str:
    """
    Build a deterministic, human-readable cache key from the tool name and
    its full parameter set, sorted so argument order never affects the key.

    Role is intentionally omitted: none of the cacheable tools filter
    their results by caller role, so the response is identical for every
    role and including it would only fragment the cache.
    """
    params = ":".join(f"{key}={arguments[key]}" for key in sorted(arguments))
    return (
        f"{_KEY_PREFIX}{tool_name}:{params}" if params else f"{_KEY_PREFIX}{tool_name}"
    )


class ToolResultCache:
    """
    Redis-backed cache for immutable, read-only MCP tool results.

    Usage:
        cache = ToolResultCache(redis_client)

        # Check cache before calling MCP
        cached = await cache.get("get_customer_profile", {"customer_id": customer_id})
        if cached is not None:
            return cached

        # Call MCP and cache the result
        result = await mcp_connection.call_tool(...)
        await cache.set("get_customer_profile", {"customer_id": customer_id}, result)
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
