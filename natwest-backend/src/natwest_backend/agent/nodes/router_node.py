from __future__ import annotations

from typing import Any

from natwest_backend.agent.graph.routing import DEFAULT_ROUTE, VALID_ROUTES
from natwest_backend.agent.prompts import ROUTER_PROMPT
from natwest_backend.agent.shared.parsing import content_to_text
from natwest_backend.agent.shared.state import AgentState
from natwest_shared.utils.logger import get_logger
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

logger = get_logger(__name__)


def create_router_node(llm: ChatOpenAI) -> Any:
    """
    Factory that returns a router node function.

    The router classifies the user's message into a route
    name that determines which graph branch handles the request.
    """

    async def router_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        last_message = state["messages"][-1]
        user_text = content_to_text(getattr(last_message, "content"))  # type: ignore[arg-type]

        response = await llm.ainvoke(
            [
                SystemMessage(content=ROUTER_PROMPT),
                HumanMessage(content=user_text),
            ],
            config=config,
        )

        route = (
            content_to_text(getattr(response, "content"))
            .strip()
            .lower()
            .strip('"')
            .strip("'")
        )  # type: ignore[arg-type]

        if route not in VALID_ROUTES:
            logger.warning(
                "Router returned unknown route '%s', defaulting to '%s'",
                route,
                DEFAULT_ROUTE,
            )
            route = DEFAULT_ROUTE

        logger.info("Router classified intent as: %s", route)
        return {"route": route}

    return router_node
