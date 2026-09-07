from __future__ import annotations

from langsmith import Client
from natwest_shared.utils.logger import get_logger

from .scores import EvaluationScores

logger = get_logger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    """
    Lazily initialize the LangSmith client.
    """
    global _client
    if _client is None:
        _client = Client()
    return _client


def log_evaluation_to_langsmith(
    run_id: str,
    scores: EvaluationScores,
) -> None:
    """
    Submit evaluation scores as feedback on a LangSmith trace.

    Each metric becomes a separate feedback entry so they can
    be filtered and charted independently in the LangSmith UI.

    Scores are normalized to 0.0-1.0 range for LangSmith
    (which expects float scores).
    """
    client = _get_client()

    feedback_entries = [
        ("groundedness", scores.groundedness, scores.reasons.get("groundedness", "")),
        ("relevance", scores.relevance, scores.reasons.get("relevance", "")),
        (
            "hallucination",
            scores.hallucination,
            scores.reasons.get("hallucination", ""),
        ),
        ("tool_selection", scores.tool_selection * 5, ""),
        ("rbac_compliance", scores.rbac_compliance * 5, ""),
    ]

    for key, score, comment in feedback_entries:
        if score == 0 and key in ("groundedness", "relevance", "hallucination"):
            continue

        try:
            client.create_feedback(  # type: ignore
                run_id=run_id,
                key=key,
                score=score / 5.0,  # Normalize 1-5 to 0.0-1.0
                comment=comment if comment else None,
            )
        except Exception:
            logger.exception(
                "Failed to log feedback to LangSmith | key=%s | run_id=%s",
                key,
                run_id,
            )

    logger.info(
        "Logged evaluation feedback to LangSmith | run_id=%s | "
        "groundedness=%.2f | relevance=%.2f | hallucination=%.2f | "
        "tool_selection=%.2f | rbac=%.2f",
        run_id,
        scores.groundedness / 5.0,
        scores.relevance / 5.0,
        scores.hallucination / 5.0,
        float(scores.tool_selection),
        float(scores.rbac_compliance),
    )
