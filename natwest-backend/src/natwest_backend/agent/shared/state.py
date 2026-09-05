from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages  # type: ignore[import-untyped]
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    State that flows through every node in the agent graph.

    messages:        Conversation history (LangGraph's add_messages reducer
                     handles append/dedup automatically).
    route:           Guardrail verdict ("safe" / "blocked"). Set by the
                     input guardrail node before routing.
    category:        Intent classification set by the router node
                     (investigation / operational_query / unclear).
                     The agent reads this to bind the right tools.
    tool_call_count: Running count of tool invocations in the current
                     request. Used to enforce the iteration safety limit.
    skill_context:   Raw MCP data gathered by a workflow tool run, stored
                     outside the message history so it never reaches the
                     OpenAI API. Used only by the evaluation pipeline.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    route: str
    category: str
    tool_call_count: int
    skill_context: str
