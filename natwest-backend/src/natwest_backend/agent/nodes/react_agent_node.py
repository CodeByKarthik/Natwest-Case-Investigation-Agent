from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from natwest_shared.utils.logger import get_logger

from natwest_backend.agent.graph.conditions import MAX_TOOL_CALLS
from natwest_backend.agent.graph.routing import IntentCategory
from natwest_backend.agent.prompts import (
    CATEGORY_INSTRUCTIONS,
    SYSTEM_PROMPT,
    TOOL_LIMIT_MESSAGE,
)
from natwest_backend.agent.shared.memory import trim_to_turns
from natwest_backend.agent.shared.state import AgentState

logger = get_logger(__name__)


def get_tools_for_category(
    category: str,
    *,
    operational_tools: list[BaseTool],
    investigation_tools: list[BaseTool],
) -> list[BaseTool]:
    """
    Select which tools the agent may use for the classified intent.

    - INVESTIGATION: only the investigation workflow tool — the agent's
      job is to extract the identifier and call it.
    - OPERATIONAL_QUERY: the 9 MCP read/write tools for ReAct reasoning.
    - UNCLEAR: no tools — the agent must ask a clarifying question.
    """
    if category == IntentCategory.INVESTIGATION:
        return investigation_tools
    if category == IntentCategory.OPERATIONAL_QUERY:
        return operational_tools
    return []


def create_agent_node(
    llm: BaseChatModel,
    *,
    operational_tools: list[BaseTool],
    investigation_tools: list[BaseTool],
) -> Any:
    """
    Factory that returns the ReAct agent node function.

    The agent reads the router's intent category from state and binds
    only the tools relevant to that category on each invocation.
    """

    async def agent_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        configurable = config.get("configurable", {})
        username = configurable.get("username", "unknown")
        role = configurable.get("role", "unknown")

        category = state.get("category") or IntentCategory.UNCLEAR.value
        category_instructions = CATEGORY_INSTRUCTIONS.get(
            category, CATEGORY_INSTRUCTIONS[IntentCategory.UNCLEAR.value]
        )

        system_prompt = SYSTEM_PROMPT.format(
            username=username,
            role=role,
            category_instructions=category_instructions,
        )
        trimmed = trim_to_turns(list(state["messages"]))
        messages = [SystemMessage(content=system_prompt)] + trimmed

        tools = get_tools_for_category(
            category,
            operational_tools=operational_tools,
            investigation_tools=investigation_tools,
        )

        if not tools:
            # UNCLEAR — no tools bound, the agent can only ask a
            # clarifying question.
            logger.info("Agent running with no tools | category=%s", category)
            response = await llm.ainvoke(messages, config=config)
        elif state["tool_call_count"] >= MAX_TOOL_CALLS:
            logger.warning(
                "Tool call limit reached (%d), forcing response",
                MAX_TOOL_CALLS,
            )
            messages.append(SystemMessage(content=TOOL_LIMIT_MESSAGE))
            response = await llm.ainvoke(messages, config=config)
        else:
            response = await llm.bind_tools(tools).ainvoke(messages, config=config)

        return {"messages": [response]}

    return agent_node
