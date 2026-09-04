from dataclasses import dataclass, field


@dataclass
class EvaluationScores:
    """
    Complete evaluation result for a single agent run.

    LLM-judged scores (1-5):
        groundedness:  Is the answer supported by tool data?
        relevance:     Does the answer address the question?
        hallucination: Does the answer avoid inventing facts?
                       (5 = no hallucination, 1 = severe)

    Deterministic scores:
        tool_selection:  Did the agent call expected tools?
        rbac_compliance: Was access control enforced correctly?

    Metadata:
        reasons: One-sentence justification per LLM-judged metric.
        tools_called: Actual tools the agent invoked.
    """

    # LLM-judged (1-5)
    groundedness: int = 0
    relevance: int = 0
    hallucination: int = 0

    # Deterministic (pass/fail as 1 or 0)
    tool_selection: int = 0
    rbac_compliance: int = 1  # default pass unless violation detected

    # Justifications
    reasons: dict[str, str] = field(default_factory=dict)  # type: ignore

    # Metadata
    tools_called: list[str] = field(default_factory=list)  # type: ignore

    def to_dict(self) -> dict[str, object]:
        """Convert to a dict for logging."""
        return {
            "groundedness": self.groundedness,
            "groundedness_reason": self.reasons.get("groundedness", ""),
            "relevance": self.relevance,
            "relevance_reason": self.reasons.get("relevance", ""),
            "hallucination": self.hallucination,
            "hallucination_reason": self.reasons.get("hallucination", ""),
            "tool_selection": self.tool_selection,
            "rbac_compliance": self.rbac_compliance,
            "tools_called": self.tools_called,
        }
