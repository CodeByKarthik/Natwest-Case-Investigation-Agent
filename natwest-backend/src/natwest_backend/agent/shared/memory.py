from __future__ import annotations

from natwest_backend.agent.shared.skill_limits import DEFAULT_AGENT_LIMITS
from natwest_shared.utils.logger import get_logger
from langchain_core.messages import AnyMessage, HumanMessage

logger = get_logger(__name__)

MAX_CONVERSATION_TURNS = DEFAULT_AGENT_LIMITS.max_conversation_turns


def trim_to_turns(
    messages: list[AnyMessage],
    max_turns: int = MAX_CONVERSATION_TURNS,
) -> list[AnyMessage]:
    """
    Keep the last ``max_turns`` conversation turns.

    A turn starts with each HumanMessage. Everything before
    the oldest kept HumanMessage is discarded. This preserves
    tool call / tool result sequences within each turn.

    The full history remains in the checkpointer — this only
    affects what the LLM sees in its context window.
    """
    human_indices = [
        i for i, msg in enumerate(messages) if isinstance(msg, HumanMessage)
    ]

    if len(human_indices) <= max_turns:
        return messages

    start_index = human_indices[-max_turns]
    trimmed = messages[start_index:]

    logger.info(
        "Trimmed conversation from %d to %d messages (%d turns kept)",
        len(messages),
        len(trimmed),
        max_turns,
    )

    return trimmed
