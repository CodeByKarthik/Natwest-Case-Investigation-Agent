from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from natwest_backend.agent.cache import ConversationMemory, ToolResultCache, get_redis
from natwest_backend.config import settings
from natwest_shared.schema.auth_schema import AuthContext
from natwest_shared.utils.logger import get_logger
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage

from .graph_builder import build_graph
from .mcp_client import connect_mcp
from .shared.tool_adapter import create_mcp_tools

logger = get_logger(__name__)

_RBAC_ERROR_MARKERS = [
    "does not have the required role",
    "permission denied",
    "not permitted",
]


@dataclass
class AgentResult:
    """
    Result from an agent run, used by the chat endpoint.
    """

    answer: str
    messages: list[AnyMessage] = field(default_factory=list)
    run_id: str = ""
    route: str = ""
    tools_called: list[str] = field(default_factory=list)
    skill_context: str = ""


def _detect_rbac_denial(messages: list[Any]) -> bool:
    """
    Scan tool responses for RBAC denial indicators.
    """
    for msg in messages:
        if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
            content_lower = msg.content.lower()
            if any(marker in content_lower for marker in _RBAC_ERROR_MARKERS):
                return True
    return False


def _collect_tool_names(messages: list[Any]) -> list[str]:
    """
    Extract unique tool names from the message history.
    """
    seen: set[str] = set()
    names: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name and msg.name not in seen:
            seen.add(msg.name)
            names.append(msg.name)
    return names


class AgentService:
    """
    Agent service with Redis-backed conversation memory and tool caching.

    A new MCP session and agent graph are created per request
    so each call carries the correct user token. Conversation
    history and tool results persist in Redis.
    """

    def __init__(self) -> None:
        self.mcp_url = f"http://{settings.mcp_host}:{settings.mcp_port}/mcp"
        self._conversation_memory: ConversationMemory | None = None
        self._tool_cache: ToolResultCache | None = None

    async def _ensure_cache(self) -> None:
        """Lazily initialize Redis-backed caches on first use."""
        if self._conversation_memory is None:
            redis = await get_redis()
            self._conversation_memory = ConversationMemory(redis)
            self._tool_cache = ToolResultCache(redis)
            logger.info("Redis caches initialized")

    def _build_config(
        self,
        auth_context: AuthContext | None,
        conversation_id: str | None,
        run_id: str,
    ) -> dict[str, Any]:
        """
        Build the RunnableConfig passed to graph.ainvoke().
        """
        username = auth_context.username if auth_context else "unknown"
        role = auth_context.role.value if auth_context else "unknown"
        user_id = auth_context.app_user_id if auth_context else ""

        return {
            "run_id": run_id,
            "run_name": "natwest_chat",
            "configurable": {
                "username": username,
                "role": role,
                "user_id": user_id,
                "conversation_id": conversation_id or "",
            },
            "metadata": {
                "username": username,
                "user_id": user_id,
                "role": role,
                "conversation_id": conversation_id or "",
                "route": "/api/chat",
                "app_version": settings.app_version,
            },
            "tags": [
                "api_chat",
                f"role:{role}",
            ],
        }

    async def run(
        self,
        message: str,
        token: str,
        auth_context: AuthContext | None = None,
        conversation_id: str | None = None,
    ) -> AgentResult:
        """
        Execute the agent graph for a single user query.

        Flow:
        1. Load conversation history from Redis
        2. Append the new user message
        3. Run the graph (no checkpointer — history is in the initial state)
        4. Save the updated history back to Redis
        5. Return the agent's final answer
        """
        username = auth_context.username if auth_context else "unknown"
        run_id = str(uuid4())

        logger.info(
            "Agent run started | user: %s | conversation: %s | run_id: %s | message: %.100s",
            username,
            conversation_id or "new",
            run_id,
            message,
        )

        await self._ensure_cache()
        assert self._conversation_memory is not None  # nosec: B101
        config = self._build_config(auth_context, conversation_id, run_id)

        # --- Load conversation history from Redis ---
        previous_messages = []
        if conversation_id:
            previous_messages = await self._conversation_memory.load(conversation_id)

        # Build initial messages: history + new user message
        initial_messages = previous_messages + [HumanMessage(content=message)]

        async with connect_mcp(
            self.mcp_url,
            token,
            tool_cache=self._tool_cache,
        ) as connection:
            tools = await create_mcp_tools(connection)
            graph = build_graph(tools, connection)

            result = await graph.ainvoke(
                {
                    "messages": initial_messages,
                    "route": "",
                    "category": "",
                    "tool_call_count": 0,
                    "skill_context": "",
                },
                config=config,
            )

            messages = result.get("messages", [])

            # --- Save conversation history to Redis ---
            if conversation_id:
                await self._conversation_memory.save(conversation_id, messages)

            # --- Post-run logging ---
            tool_names = _collect_tool_names(messages)
            for name in tool_names:
                config["tags"].append(f"tool:{name}")

            if _detect_rbac_denial(messages):
                config["tags"].append("rbac_denied")
                logger.info("RBAC denial detected in tool responses")

            route = result.get("route", "unknown")
            logger.info(
                "Agent run completed | route: %s | tools_called: %s | "
                "total_messages: %d | conversation: %s | tags: %s",
                route,
                tool_names,
                len(messages),
                conversation_id or "none",
                config["tags"],
            )

            # --- Extract final answer ---
            answer = "I was unable to process your request. Please try again."
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    answer = str(msg.content)
                    break

            return AgentResult(
                answer=answer,
                messages=messages,
                run_id=run_id,
                route=route,
                tools_called=tool_names,
                skill_context=result.get("skill_context", ""),
            )
