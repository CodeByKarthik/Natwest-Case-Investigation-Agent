from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages  # type: ignore[import-untyped]
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    State that flows through every node in the agent graph.

    messages:        Conversation history (LangGraph's add_messages reducer
                     handles append/dedup automatically).
    route:           Intent classification set by the router node.
                     Determines which branch the graph follows.
    tool_call_count: Running count of tool invocations in the current
                     request. Used to enforce the iteration safety limit.
    skill_context:   Raw MCP data gathered by a skill node, stored outside
                     the message history so it never reaches the OpenAI API.
                     Used only by the evaluation pipeline.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    route: str
    tool_call_count: int
    skill_context: str
