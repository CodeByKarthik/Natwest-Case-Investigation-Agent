from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from natwest_backend.agent.shared.state import AgentState
from natwest_backend.agent.tools.investigation_tool import InvestigationWorkflowTool


def create_investigation_finalize_node(
    investigation_tool: InvestigationWorkflowTool,
) -> Any:
    """
    Factory that returns the investigation finalize node.

    Converts the investigation workflow tool's output directly into the
    final AI message, bypassing any further LLM turn so the rendered
    report is returned verbatim instead of being paraphrased. Also copies
    the raw MCP data gathered by the workflow into `skill_context` so the
    evaluation pipeline has real ground truth to check citations against,
    instead of comparing the report to itself.
    """

    async def investigation_finalize_node(
        state: AgentState, config: RunnableConfig
    ) -> dict[str, Any]:
        last_message = state["messages"][-1]
        content = last_message.content if isinstance(last_message, ToolMessage) else ""
        return {
            "messages": [AIMessage(content=content)],
            "skill_context": investigation_tool.last_tool_data,
        }

    return investigation_finalize_node
