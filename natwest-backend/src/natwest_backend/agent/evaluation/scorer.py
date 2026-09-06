from __future__ import annotations

import re
from typing import Any

from natwest_backend.agent.shared.parsing import content_to_text
from natwest_shared.utils.logger import get_logger
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langsmith import tracing_context

from .prompts import EVALUATION_PROMPT
from .scores import EvaluationScores

logger = get_logger(__name__)

_RBAC_ERROR_MARKERS = [
    "does not have the required role",
    "permission denied",
    "not permitted",
    "requires case_manager",
    "requires fraud_investigator",
    "insufficient permission",
    "requires case_manager approval",
    "cannot update case status",
    "cannot create or manage next actions",
    "only case_manager can",
    "case management function",
]


def _extract_user_question(messages: list[AnyMessage]) -> str:
    """
    Find the last HumanMessage in the conversation.
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return content_to_text(msg.content)
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
            content = content_to_text(msg.content)
            sections.append(f"[{name}]\n{content}")

    return "\n\n".join(sections) if sections else "No tool data available."


def _extract_final_answer(messages: list[AnyMessage]) -> str:
    """
    Find the last AIMessage with content.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return content_to_text(msg.content)
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
    llm: BaseChatModel,
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
    response_text = content_to_text(response.content)

    return _parse_llm_scores(response_text)


# ----- Deterministic checks (RBAC & Tool Selection) -----


def _check_rbac_compliance(
    messages: list[AnyMessage],
    user_role: str,
) -> bool:
    """
    Check if RBAC was correctly enforced for NatWest role permissions.

    Returns True if:
    - The user's role permitted the write tool call and it succeeded, OR
    - The user's role did not permit the call and it was denied

    Returns False if a forbidden tool call succeeded (RBAC violation).

    NatWest role permissions (tool-name level):
    - customer_support: update_case_status and manage_next_action forbidden
    - fraud_investigator: update_case_status allowed, manage_next_action forbidden
    - case_manager: all tools allowed

    Note: this check operates at the tool-name level only. It does not
    capture the finer-grained terminal-status restriction (fraud_investigator
    is blocked from setting status to resolved/closed — only case_manager
    can). add_case_note is universal and is never forbidden for any role.
    """
    write_tools = {"update_case_status", "manage_next_action"}
    admin_tools = {"manage_next_action"}

    forbidden_for_role = {
        "customer_support": write_tools,
        "fraud_investigator": admin_tools,
        "case_manager": set(),
    }

    forbidden = forbidden_for_role.get(user_role, set())

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue

        tool_name = msg.name or ""
        if tool_name not in forbidden:
            continue

        content = content_to_text(msg.content).lower()
        is_error = any(m in content for m in _RBAC_ERROR_MARKERS)

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
    llm: BaseChatModel,
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
