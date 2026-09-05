from __future__ import annotations

from typing import Any

from natwest_backend.agent.graph.routing import (
    DEFAULT_CATEGORY,
    VALID_CATEGORIES,
    IntentCategory,
)
from natwest_backend.agent.prompts import ROUTER_CLASSIFICATION_PROMPT
from natwest_backend.agent.shared.parsing import content_to_text
from natwest_backend.agent.shared.state import AgentState
from natwest_shared.utils.logger import get_logger
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

logger = get_logger(__name__)

_MAX_HISTORY_MESSAGES = 10


def _format_history(state: AgentState) -> str:
    """
    Render recent conversation history as plain text for the classifier.

    Excludes the current (final) user message — that is passed separately.
    """
    lines: list[str] = []
    for msg in state["messages"][-_MAX_HISTORY_MESSAGES - 1 : -1]:
        role = getattr(msg, "type", "unknown")
        text = content_to_text(getattr(msg, "content", ""))
        if text:
            lines.append(f"{role}: {text[:300]}")
    return "\n".join(lines) if lines else "(no prior conversation)"


def parse_category(raw: str) -> IntentCategory:
    """
    Normalise the router LLM's response into an IntentCategory.

    Tolerates quotes, trailing punctuation, and mixed case. Falls back to
    UNCLEAR for anything unexpected — asking a clarifying question is
    safer than guessing.
    """
    cleaned = raw.strip().strip('"').strip("'").strip().rstrip(".").lower()
    if cleaned in VALID_CATEGORIES:
        return IntentCategory(cleaned)
    logger.warning(
        "Router returned unknown category '%s', defaulting to '%s'",
        cleaned,
        DEFAULT_CATEGORY,
    )
    return DEFAULT_CATEGORY


def create_router_node(llm: ChatOpenAI) -> Any:
    """
    Factory that returns the router node function.

    The router is an LLM-only intent classifier. It never does pattern
    matching and never extracts identifiers — it classifies the message
    (with conversation history for context) and writes the category to
    state. The agent reads the category and binds tools accordingly.
    """

    async def router_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        last_message = state["messages"][-1]
        user_text = content_to_text(getattr(last_message, "content"))  # type: ignore[arg-type]
        history = _format_history(state)

        try:
            response = await llm.ainvoke(
                [
                    HumanMessage(
                        content=ROUTER_CLASSIFICATION_PROMPT.format(
                            user_message=user_text,
                            conversation_history=history,
                        )
                    ),
                ],
                config=config,
            )
            raw = content_to_text(getattr(response, "content"))  # type: ignore[arg-type]
        except Exception:
            # If classification fails, treat the message as an operational
            # query so the agent can still try to help with the full toolset.
            logger.exception("Router LLM call failed, defaulting to operational_query")
            return {"category": IntentCategory.OPERATIONAL_QUERY.value}

        category = parse_category(raw)
        logger.info("Router classified intent as: %s", category)
        return {"category": category.value}

    return router_node
