from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool
from langgraph.graph import (
    END,
    START,
    StateGraph,
)
from langgraph.prebuilt import ToolNode
from natwest_shared.utils.logger import get_logger

from .graph.conditions import route_after_guardrail, route_after_tools, should_continue
from .mcp_client import MCPConnection
from .nodes import (
    create_agent_node,
    create_input_guardrail_node,
    create_investigation_finalize_node,
    create_router_node,
    create_tool_node,
)
from .shared.llm_factory import create_llm
from .shared.state import AgentState
from .tools import create_investigation_tool

logger = get_logger(__name__)


def build_graph(
    tools: list[BaseTool],
    connection: MCPConnection,
) -> Any:
    """
    Build and compile the full agent graph.

    Called once per request because:
    - Tools are discovered dynamically from the MCP server
    - The MCPConnection carries the user's auth token
    - The investigation workflow tool needs the connection

    Flow:
        input_guardrail → router → agent → response

    The router is an LLM-only intent classifier (no pattern matching,
    no identifier extraction). The agent reads the category from state
    and binds the appropriate tools:
    - INVESTIGATION: only the investigation workflow tool
    - OPERATIONAL_QUERY: the 9 MCP tools
    - UNCLEAR: no tools (clarifying question)

    When the investigation workflow tool runs, its rendered report becomes
    the final answer directly — the graph terminates without a further
    LLM turn so the report is never paraphrased.

    Returns a compiled LangGraph ready for ainvoke().
    """

    # --- Shared LLM ---
    llm = create_llm()

    # --- Tools ---
    # The ToolNode must know every tool the agent could call under any
    # category; the agent node restricts which are bound per request.
    investigation_tool = create_investigation_tool(connection=connection, llm=llm)
    all_tools = [*tools, investigation_tool]
    tool_executor = ToolNode(all_tools)

    # --- Create nodes ---
    guardrail = create_input_guardrail_node(llm)
    router = create_router_node(llm)
    agent = create_agent_node(
        llm,
        operational_tools=tools,
        investigation_tools=[investigation_tool],
    )
    tools_node = create_tool_node(tool_executor)
    investigation_finalize = create_investigation_finalize_node()

    # --- Assemble graph ---
    graph: Any = StateGraph(AgentState)

    graph.add_node("input_guardrail", guardrail)
    graph.add_node("router", router)
    graph.add_node("agent", agent)
    graph.add_node("tools", tools_node)
    graph.add_node("finalize_investigation", investigation_finalize)

    # --- Edges ---

    # Entry: START → guardrail
    graph.add_edge(START, "input_guardrail")

    # Guardrail → blocked or router
    graph.add_conditional_edges(
        "input_guardrail",
        route_after_guardrail,
        {"blocked": END, "safe": "router"},
    )

    # Router always hands off to the agent — the category in state
    # determines which tools the agent binds.
    graph.add_edge("router", "agent")

    # Agent ReAct loop
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )

    # After tools: investigation category terminates immediately with the
    # workflow's rendered report; other categories continue the ReAct loop.
    graph.add_conditional_edges(
        "tools",
        route_after_tools,
        {"agent": "agent", "finalize_investigation": "finalize_investigation"},
    )
    graph.add_edge("finalize_investigation", END)

    compiled: Any = graph.compile()

    logger.info(
        "Built agent graph | %d operational tools | workflow tool bound on demand",
        len(tools),
    )

    return compiled
