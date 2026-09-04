from __future__ import annotations

from typing import Any

from natwest_backend.agent.shared.state import AgentState
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode


def create_tool_node(tool_executor: ToolNode) -> Any:
    """
    Factory that returns the tool execution node function.

    Wraps LangGraph's prebuilt ToolNode with a call counter
    so the graph can enforce iteration limits.
    """

    async def tool_node_with_count(
        state: AgentState, config: RunnableConfig
    ) -> dict[str, Any]:
        result = await tool_executor.ainvoke(state, config=config)
        new_messages = result.get("messages", [])

        return {
            "messages": new_messages,
            "tool_call_count": state["tool_call_count"] + len(new_messages),
        }

    return tool_node_with_count
