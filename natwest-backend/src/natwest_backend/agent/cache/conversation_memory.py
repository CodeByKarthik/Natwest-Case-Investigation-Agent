from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from natwest_shared.utils.logger import get_logger
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

logger = get_logger(__name__)

CONVERSATION_TTL_SECONDS = 1800  # 30 minutes

_KEY_PREFIX = "conversation:"


# Message serialization — handles tool_calls, tool_call_id, etc.

_TYPE_MAP = {  # type: ignore
    "human": HumanMessage,
    "ai": AIMessage,
    "tool": ToolMessage,
    "system": SystemMessage,
}


def _serialize_message(msg: AnyMessage) -> dict[str, Any]:
    """
    Convert a LangChain message to a JSON-safe dict.
    """
    data: dict[str, Any] = {
        "type": msg.type,
        "content": msg.content,  # type: ignore
    }

    if hasattr(msg, "id") and msg.id:
        data["id"] = msg.id

    # AIMessage with tool_calls
    if isinstance(msg, AIMessage):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            data["tool_calls"] = msg.tool_calls

    # ToolMessage needs name and tool_call_id
    if isinstance(msg, ToolMessage):
        if msg.name:
            data["name"] = msg.name
        if hasattr(msg, "tool_call_id") and msg.tool_call_id:
            data["tool_call_id"] = msg.tool_call_id

    return data


def _deserialize_message(data: dict[str, Any]) -> AnyMessage:
    """
    Reconstruct a LangChain message from a serialized dict.
    """
    msg_type = data.get("type", "human")

    cls = _TYPE_MAP.get(msg_type, HumanMessage)  # type: ignore

    kwargs: dict[str, Any] = {"content": data["content"]}

    if data.get("id"):
        kwargs["id"] = data["id"]

    if msg_type == "ai" and data.get("tool_calls"):
        kwargs["tool_calls"] = data["tool_calls"]

    if msg_type == "tool":
        if data.get("name"):
            kwargs["name"] = data["name"]
        if data.get("tool_call_id"):
            kwargs["tool_call_id"] = data["tool_call_id"]

    return cls(**kwargs)  # type: ignore


class ConversationMemory:
    """
    Redis-backed conversation history store.

    Usage:
        memory = ConversationMemory(redis_client)

        # Load previous messages
        messages = await memory.load("conv-123")

        # Save updated messages after agent run
        await memory.save("conv-123", result_messages)
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        ttl: int = CONVERSATION_TTL_SECONDS,
    ) -> None:
        self._redis = redis
        self._ttl = ttl

    async def load(self, conversation_id: str) -> list[AnyMessage]:
        """
        Load conversation history from Redis.

        Returns an empty list if the conversation doesn't
        exist or has expired.
        """
        key = f"{_KEY_PREFIX}{conversation_id}"

        try:
            raw = await self._redis.get(key)
        except Exception:
            logger.exception("Failed to load conversation from Redis: %s", key)
            return []

        if raw is None:
            return []

        try:
            data = json.loads(raw)
            messages = [_deserialize_message(d) for d in data]
            logger.info(
                "Loaded %d messages from Redis | conversation: %s",
                len(messages),
                conversation_id,
            )
            return messages
        except Exception:
            logger.exception("Failed to deserialize conversation: %s", key)
            return []

    async def save(
        self,
        conversation_id: str,
        messages: list[AnyMessage],
    ) -> None:
        """
        Save conversation history to Redis with TTL.

        Overwrites the previous history for this conversation.
        TTL resets on each save, so active conversations stay alive.
        """
        key = f"{_KEY_PREFIX}{conversation_id}"

        try:
            data = [_serialize_message(msg) for msg in messages]
            raw = json.dumps(data, default=str)
            await self._redis.set(key, raw, ex=self._ttl)

            logger.info(
                "Saved %d messages to Redis | conversation: %s | ttl: %ds",
                len(messages),
                conversation_id,
                self._ttl,
            )
        except Exception:
            logger.exception("Failed to save conversation to Redis: %s", key)

    async def delete(self, conversation_id: str) -> None:
        """Delete a conversation from Redis."""
        key = f"{_KEY_PREFIX}{conversation_id}"
        try:
            await self._redis.delete(key)
        except Exception:
            logger.exception("Failed to delete conversation: %s", key)
