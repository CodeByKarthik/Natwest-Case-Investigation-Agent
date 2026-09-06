"""Tests for the NatWest tool result cache.

Only the three immutable customer read tools should be cached. Case/action
tools and write tools must never be cached, and the cache must degrade
gracefully (fall through to the real call) when Redis is unavailable.
"""

from __future__ import annotations

import asyncio
from typing import Any

from natwest_backend.agent.cache.tool_cache import (
    CACHEABLE_TOOLS,
    ToolResultCache,
    _make_cache_key,
)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


class FakeRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.set_calls = 0
        self.get_calls = 0

    async def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.set_calls += 1
        self.store[key] = value


class FailingRedis:
    """Simulates Redis being unreachable — every call raises."""

    async def get(self, key: str) -> str | None:
        raise ConnectionError("Redis unavailable")

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        raise ConnectionError("Redis unavailable")


def test_only_the_three_immutable_customer_tools_are_cacheable() -> None:
    assert set(CACHEABLE_TOOLS) == {
        "list_customers",
        "get_customer_profile",
        "get_customer_accounts",
    }


def test_case_and_action_tools_are_never_cached() -> None:
    cache = ToolResultCache(FakeRedis())  # type: ignore[arg-type]
    for tool_name in (
        "list_cases",
        "get_case_details",
        "get_case_timeline",
        "get_next_actions",
        "update_case_status",
        "manage_next_action",
    ):
        assert cache.is_cacheable(tool_name) is False


def test_set_then_get_round_trips_for_cacheable_tool() -> None:
    redis = FakeRedis()
    cache = ToolResultCache(redis)  # type: ignore[arg-type]

    run(
        cache.set(
            "get_customer_profile", {"customer_id": "abc-123"}, '{"id":"abc-123"}'
        )
    )
    result = run(cache.get("get_customer_profile", {"customer_id": "abc-123"}))

    assert result == '{"id":"abc-123"}'
    assert redis.set_calls == 1


def test_set_is_a_noop_for_non_cacheable_tool() -> None:
    redis = FakeRedis()
    cache = ToolResultCache(redis)  # type: ignore[arg-type]

    run(cache.set("get_case_details", {"case_ref": "CASE-1001"}, '{"status":"open"}'))

    assert redis.set_calls == 0
    assert run(cache.get("get_case_details", {"case_ref": "CASE-1001"})) is None


def test_set_skips_error_responses() -> None:
    redis = FakeRedis()
    cache = ToolResultCache(redis)  # type: ignore[arg-type]

    run(cache.set("get_customer_profile", {"customer_id": "x"}, "Error: not found"))

    assert redis.set_calls == 0


def test_cache_key_is_human_readable_and_omits_role() -> None:
    key = _make_cache_key(
        "list_customers",
        {"name_contains": "aisha", "limit": 50, "offset": 0},
    )
    assert key == "tool_cache:list_customers:limit=50:name_contains=aisha:offset=0"
    assert "role" not in key


def test_cache_key_is_stable_regardless_of_argument_order() -> None:
    key_a = _make_cache_key("get_customer_profile", {"customer_id": "abc", "limit": 1})
    key_b = _make_cache_key("get_customer_profile", {"limit": 1, "customer_id": "abc"})
    assert key_a == key_b


def test_cache_degrades_gracefully_when_redis_is_unavailable() -> None:
    cache = ToolResultCache(FailingRedis())  # type: ignore[arg-type]

    get_result = run(cache.get("get_customer_profile", {"customer_id": "abc"}))
    assert get_result is None  # falls through to a real call, no exception raised

    # set() must also swallow the error rather than propagate it.
    run(cache.set("get_customer_profile", {"customer_id": "abc"}, '{"id":"abc"}'))
