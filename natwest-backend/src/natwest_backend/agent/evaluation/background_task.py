from __future__ import annotations

from langchain_core.messages import AnyMessage
from natwest_shared.utils.logger import get_logger

from natwest_backend.agent.shared.llm_factory import create_llm

from .langsmith_feedback import log_evaluation_to_langsmith
from .scorer import score_response

logger = get_logger(__name__)


async def run_background_evaluation(
    messages: list[AnyMessage],
    run_id: str,
    user_role: str,
    expected_tools: list[str] | None = None,
    skill_context: str = "",
) -> None:
    """
    Background task that evaluates the agent response and
    logs scores to LangSmith.

    Attributes:
    -----------

    - messages: Full message history from the agent run.
    - run_id: LangSmith trace run ID to attach feedback to.
    - user_role: User's RBAC role for compliance checks.
    - expected_tools: Optional list of expected tool names for
    tool selection scoring.
    - skill_context: Raw MCP data from a skill node run, used as
    ground truth for evaluation instead of ToolMessages.
    """
    try:
        llm = create_llm()

        scores = await score_response(
            llm=llm,
            messages=messages,
            user_role=user_role,
            expected_tools=expected_tools,
            skill_context=skill_context,
        )

        log_evaluation_to_langsmith(run_id=run_id, scores=scores)

    except Exception:
        logger.exception(
            "Background evaluation failed | run_id=%s",
            run_id,
        )
