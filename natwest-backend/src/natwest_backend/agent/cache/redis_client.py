from __future__ import annotations

import redis.asyncio as aioredis
from natwest_shared.utils.logger import get_logger

from natwest_backend.config import settings

logger = get_logger(__name__)

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    Return a shared async Redis client.

    Creates the connection pool on first call.
    Subsequent calls return the same instance.
    """
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        logger.info("Redis connection pool created: %s", settings.redis_url)
    return _pool


async def close_redis() -> None:
    """
    Close the Redis connection pool on shutdown.
    """
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection pool closed")
