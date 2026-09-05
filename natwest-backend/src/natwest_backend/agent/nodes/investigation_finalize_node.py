from __future__ import annotations

from typing import Any

from natwest_backend.agent.shared.state import AgentState
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig


def create_investigation_finalize_node() -> Any:
    """
    Factory that returns the investigation finalize node.

    Converts the investigation workflow tool's output directly into the
    final AI message, bypassing any further LLM turn so the rendered
    report is returned verbatim instead of being paraphrased.
    """

    async def investigation_finalize_node(
        state: AgentState, config: RunnableConfig
    ) -> dict[str, Any]:
        last_message = state["messages"][-1]
        content = last_message.content if isinstance(last_message, ToolMessage) else ""
        return {"messages": [AIMessage(content=content)]}

    return investigation_finalize_node
