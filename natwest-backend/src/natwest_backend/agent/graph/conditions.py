from __future__ import annotations

from typing import Literal

from natwest_backend.agent.graph.routing import BLOCKED_ROUTE, IntentCategory
from natwest_backend.agent.shared.skill_limits import DEFAULT_AGENT_LIMITS
from natwest_backend.agent.shared.state import AgentState
from langchain_core.messages import AIMessage

MAX_TOOL_CALLS = DEFAULT_AGENT_LIMITS.max_tool_calls


def route_after_guardrail(state: AgentState) -> Literal["safe", "blocked"]:
    """
    After the guardrail node, decide whether the request
    is safe to proceed or should be blocked.
    """
    if state["route"] == BLOCKED_ROUTE:
        return "blocked"
    return "safe"


def should_continue(
    state: AgentState,
) -> Literal["tools", "end"]:
    """
    After the agent node, decide whether to execute
    pending tool calls or finish the response.

    Returns 'end' if:
    - The LLM did not request any tool calls, or
    - The tool call safety limit has been reached
    """
    last_message = state["messages"][-1]

    has_tool_calls = (
        isinstance(last_message, AIMessage)
        and hasattr(last_message, "tool_calls")
        and last_message.tool_calls
    )

    if has_tool_calls and state["tool_call_count"] < MAX_TOOL_CALLS:
        return "tools"

    return "end"


def route_after_tools(state: AgentState) -> Literal["agent", "finalize_investigation"]:
    """
    After tool execution, decide whether to continue the ReAct loop or
    finalize immediately.

    The investigation workflow tool's output is the final report — no
    further LLM turn should be allowed to rewrite it.
    """
    if state["category"] == IntentCategory.INVESTIGATION.value:
        return "finalize_investigation"
    return "agent"
