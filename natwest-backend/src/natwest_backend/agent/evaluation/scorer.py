from __future__ import annotations

import re
from typing import Any

from natwest_backend.agent.shared.parsing import content_to_text
from natwest_shared.utils.logger import get_logger
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langsmith import tracing_context  # type: ignore[attr-defined]

from .prompts import EVALUATION_PROMPT
from .scores import EvaluationScores

logger = get_logger(__name__)

_RBAC_ERROR_MARKERS = [
    "does not have the required role",
    "permission denied",
    "not permitted",
]


def _extract_user_question(messages: list[AnyMessage]) -> str:
    """
    Find the last HumanMessage in the conversation.
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return content_to_text(msg.content)  # type: ignore[arg-type]
    return ""


def _extract_tool_data(messages: list[AnyMessage]) -> str:
    """
    Collect all tool results from the conversation.

    Returns a formatted string of tool_name → result pairs
    that serves as the ground truth for evaluation.
    """
    sections: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            name = msg.name or "unknown_tool"
            content = content_to_text(msg.content)  # type: ignore[arg-type]
            sections.append(f"[{name}]\n{content}")

    return "\n\n".join(sections) if sections else "No tool data available."


def _extract_final_answer(messages: list[AnyMessage]) -> str:
    """
    Find the last AIMessage with content.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:  # type: ignore
            return content_to_text(msg.content)  # type: ignore[arg-type]
    return ""


def _extract_tool_names(messages: list[AnyMessage]) -> list[str]:
    """
    Collect unique tool names called during the run.
    """
    seen: set[str] = set()
    names: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name and msg.name not in seen:
            seen.add(msg.name)
            names.append(msg.name)
    return names


# ---- LLM-judged scoring -----


def _parse_llm_scores(text: str) -> dict[str, Any]:
    """
    Parse the structured evaluation output from the LLM.

    Expected format:
        GROUNDEDNESS: 4
        GROUNDEDNESS_REASON: ...
        RELEVANCE: 5
        RELEVANCE_REASON: ...
        HALLUCINATION: 4
        HALLUCINATION_REASON: ...
    """
    result: dict[str, Any] = {}

    patterns = {
        "groundedness": r"GROUNDEDNESS:\s*(\d)",
        "relevance": r"RELEVANCE:\s*(\d)",
        "hallucination": r"HALLUCINATION:\s*(\d)",
        "groundedness_reason": r"GROUNDEDNESS_REASON:\s*(.+)",
        "relevance_reason": r"RELEVANCE_REASON:\s*(.+)",
        "hallucination_reason": r"HALLUCINATION_REASON:\s*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if key.endswith("_reason"):
                result[key] = value
            else:
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = 0

    return result


async def _run_llm_judge(
    llm: ChatOpenAI,
    user_question: str,
    tool_data: str,
    assistant_answer: str,
) -> dict[str, Any]:
    """
    Run the LLM-as-judge evaluation.

    Returns parsed scores and reasons.
    """
    prompt = EVALUATION_PROMPT.format(
        user_question=user_question,
        tool_data=tool_data,
        assistant_answer=assistant_answer,
    )

    # tracing_context(enabled=False) suppresses the global LangSmith tracer
    with tracing_context(enabled=False):
        response = await llm.ainvoke([SystemMessage(content=prompt)])
    response_text = content_to_text(response.content)  # type: ignore[arg-type]

    return _parse_llm_scores(response_text)


# ----- Deterministic checks (RBAC & Tool Selection) -----


def _check_rbac_compliance(
    messages: list[AnyMessage],
    user_role: str,
) -> bool:
    """
    Check if RBAC was correctly enforced.

    Returns True (compliant) if:
    - Write tools were not called by read-only roles, OR
    - Write tools were called and correctly denied
    """
    write_tools = {
        "update_issue_status",
        "add_issue_update",
        "create_next_action",
        "update_next_action",
        "complete_next_action",
    }

    admin_tools = {
        "create_next_action",
        "update_next_action",
        "complete_next_action",
    }

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue

        tool_name = msg.name or ""
        content = content_to_text(msg.content).lower()  # type: ignore[arg-type]
        is_error = any(m in content for m in _RBAC_ERROR_MARKERS)

        # sales_user should never succeed with write tools
        if user_role == "sales_user" and tool_name in write_tools:
            if not is_error:
                return False

        # support_user should never succeed with admin tools
        if user_role == "support_user" and tool_name in admin_tools:
            if not is_error:
                return False

    return True


def _check_tool_selection(
    tools_called: list[str],
    expected_tools: list[str] | None,
) -> int:
    """
    Check if the expected tools were called.

    Returns 1 if all expected tools are present in tools_called,
    0 otherwise. Returns 1 if no expected tools are specified.
    """
    if not expected_tools:
        return 1

    called_set = set(tools_called)
    expected_set = set(expected_tools)

    return 1 if expected_set.issubset(called_set) else 0


# ---- Evaluation Response Scoring Pipeline -----


async def score_response(
    llm: ChatOpenAI,
    messages: list[AnyMessage],
    user_role: str = "unknown",
    expected_tools: list[str] | None = None,
    skill_context: str = "",
) -> EvaluationScores:
    """
    Run the full evaluation pipeline on an agent response.

    1. Extract question, tool data, and final answer from messages
    2. Run LLM-as-judge for groundedness, relevance, hallucination
    3. Run deterministic checks for tool selection and RBAC
    4. Return complete EvaluationScores

    This is designed to run as a background task — it does not
    block the user response.
    """
    user_question = _extract_user_question(messages)
    # Prefer skill_context (MCP data from skill routes) over ToolMessages
    tool_data = skill_context if skill_context else _extract_tool_data(messages)
    final_answer = _extract_final_answer(messages)
    tools_called = _extract_tool_names(messages)

    scores = EvaluationScores(tools_called=tools_called)

    # --- LLM-judged scores ---
    try:
        if final_answer:
            llm_scores = await _run_llm_judge(
                llm, user_question, tool_data, final_answer
            )

            scores.groundedness = llm_scores.get("groundedness", 0)
            scores.relevance = llm_scores.get("relevance", 0)
            scores.hallucination = llm_scores.get("hallucination", 0)
            scores.reasons = {
                "groundedness": llm_scores.get("groundedness_reason", ""),
                "relevance": llm_scores.get("relevance_reason", ""),
                "hallucination": llm_scores.get("hallucination_reason", ""),
            }
        else:
            logger.info("Skipping LLM judge — no final answer found")

    except Exception:
        logger.exception("LLM judge evaluation failed")

    # --- Deterministic checks ---
    scores.tool_selection = _check_tool_selection(tools_called, expected_tools)
    scores.rbac_compliance = 1 if _check_rbac_compliance(messages, user_role) else 0

    return scores
