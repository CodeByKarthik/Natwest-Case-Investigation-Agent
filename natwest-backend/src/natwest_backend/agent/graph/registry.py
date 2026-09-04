from __future__ import annotations

from typing import Any, Callable

from natwest_backend.agent.mcp_client import MCPConnection
from natwest_backend.agent.nodes.skill_node import create_escalation_summary_node
from natwest_backend.agent.shared.skill_limits import DEFAULT_SKILL_LIMITS, SkillLimits
from langchain_openai import ChatOpenAI

# Type alias for skill node builder functions
SkillNodeBuilder = Callable[..., Any]

SKILL_NODE_BUILDERS: dict[str, SkillNodeBuilder] = {
    "escalation_summary": create_escalation_summary_node,
    # "next_skill": create_next_skill_node,   ← register new skills here
}


def build_skill_nodes(
    connection: MCPConnection,
    llm: ChatOpenAI,
    limits: SkillLimits = DEFAULT_SKILL_LIMITS,
) -> dict[str, Any]:
    """
    Instantiate all registered skill nodes with their dependencies.

    Returns a dict of {route_name: node_function} ready to
    be added to the StateGraph.
    """
    nodes: dict[str, Any] = {}

    for name, builder in SKILL_NODE_BUILDERS.items():
        nodes[name] = builder(connection=connection, llm=llm, limits=limits)

    return nodes
