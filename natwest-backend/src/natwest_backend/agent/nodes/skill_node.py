from __future__ import annotations

from typing import Any

from natwest_backend.agent.mcp_client import MCPConnection
from natwest_backend.agent.shared.parsing import content_to_text
from natwest_backend.agent.shared.skill_limits import DEFAULT_SKILL_LIMITS, SkillLimits
from natwest_backend.agent.shared.state import AgentState
from natwest_backend.agent.skills.escalation_summary import EscalationSummarySkill
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI


def create_escalation_summary_node(
    connection: MCPConnection,
    llm: ChatOpenAI,
    limits: SkillLimits = DEFAULT_SKILL_LIMITS,
) -> Any:
    """
    Factory that returns the escalation summary skill node.

    This node runs a deterministic multi-step workflow:
    data gathering via MCP tools, then LLM synthesis.
    """

    async def escalation_summary_node(
        state: AgentState, config: RunnableConfig
    ) -> dict[str, Any]:
        skill = EscalationSummarySkill(
            connection=connection,
            llm=llm,
            limits=limits,
        )

        last_message = state["messages"][-1]
        user_text = content_to_text(getattr(last_message, "content"))  # type: ignore[arg-type]

        result = await skill.execute(user_text)

        return {
            "messages": [AIMessage(content=result.answer)],  # type: ignore
            "skill_context": result.raw_data or "",  # type: ignore
        }

    return escalation_summary_node
