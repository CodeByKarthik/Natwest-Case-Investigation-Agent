"""Case investigation workflow.

Takes exactly one of case_id, case_ref, or customer_name as input and
produces a structured InvestigationReport.

Steps 1-6 are deterministic MCP tool calls (read tools only).
Steps 7-9 are LLM reasoning steps producing citation-aware findings.

The workflow never calls write tools — it is a read-only investigation.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from natwest_shared.utils.logger import get_logger
from pydantic import BaseModel, Field, model_validator

from natwest_backend.agent.mcp_client import MCPConnection, safe_json_parse
from natwest_backend.agent.prompts.skills.investigation import (
    EVIDENCE_GAPS_PROMPT,
    RECOMMENDATION_PROMPT,
    RISK_INDICATORS_PROMPT,
)
from natwest_backend.agent.shared.parsing import content_to_text

logger = get_logger(__name__)

PRIORITY_ORDER = {"p1": 0, "p2": 1, "p3": 2, "p4": 3}

# Cases in these statuses are still ongoing work — everything except the
# two terminal statuses counts as "active" for customer-name resolution.
ACTIVE_CASE_STATUSES = {"open", "under_investigation", "pending_customer", "escalated"}

# Identifier fields stripped before data reaches the LLM prompts — internal
# UUIDs are not useful citations and the LLM sometimes cites them instead of
# the human-readable ref (case_ref, source_ref, account_number all stay).
_UUID_FIELDS = {
    "id",
    "customer_id",
    "case_id",
    "action_id",
    "event_id",
    "source_record_id",
    "assigned_user_id",
    "created_by_user_id",
    "role_id",
}

_DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$"
)


def _humanize_date_string(value: str) -> str:
    """Reformat an ISO date/datetime string as 'DD Mon YYYY[, HH:MM]',
    leaving anything that isn't a recognisable date untouched (case_ref,
    source_ref, account_number, etc.)."""
    if _DATE_ONLY_PATTERN.match(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y")
        except ValueError:
            return value

    if _DATETIME_PATTERN.match(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
            return parsed.strftime("%d %b %Y")
        return parsed.strftime("%d %b %Y, %H:%M")

    return value


def _serialise_for_prompt(data: Any) -> Any:
    """Recursively strip internal UUID fields and humanize ISO date/
    datetime strings so the LLM cannot cite raw UUIDs or microsecond
    timestamps in the narrative."""
    if isinstance(data, dict):
        return {
            key: _serialise_for_prompt(value)
            for key, value in data.items()
            if key not in _UUID_FIELDS
        }
    if isinstance(data, list):
        return [_serialise_for_prompt(item) for item in data]
    if isinstance(data, str):
        return _humanize_date_string(data)
    return data


class InvestigationInput(BaseModel):
    """Workflow input — exactly one identifier must be provided."""

    case_id: UUID | None = None
    case_ref: str | None = None
    customer_name: str | None = None

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> InvestigationInput:
        provided = [
            value
            for value in (self.case_id, self.case_ref, self.customer_name)
            if value is not None
        ]
        if len(provided) != 1:
            raise ValueError(
                "Exactly one of case_id, case_ref, or customer_name must be provided"
            )
        return self


class CitedFinding(BaseModel):
    """A finding (risk indicator or evidence gap) with its source citation."""

    finding: str
    source_type: str
    source_id: str | None = None
    source_system: str | None = None
    confidence: str | None = None
    detected_at: str | None = None
    explanation: str


class InvestigationReport(BaseModel):
    """Structured output of the case investigation workflow."""

    case_ref: str = ""
    case_summary: str = ""
    customer_context: str = ""
    vulnerability_context: str | None = None
    risk_indicators: list[CitedFinding] = Field(default_factory=list)
    evidence_gaps: list[CitedFinding] = Field(default_factory=list)
    recommended_action: str = ""
    recommended_action_type: str | None = None
    reasoning: str = ""
    disambiguation_note: str | None = None


class _RecommendationResult(BaseModel):
    """Expected JSON shape returned by the Step 9 LLM call."""

    case_summary: str = ""
    customer_context: str = ""
    vulnerability_context: str | None = None
    recommended_action: str = ""
    recommended_action_type: str | None = None
    reasoning: str = ""


def _parse_cited_findings(raw: str) -> list[CitedFinding]:
    """Parse a JSON array of CitedFinding objects, skipping malformed entries."""
    parsed = safe_json_parse(raw)
    if not isinstance(parsed, list):
        return []

    findings: list[CitedFinding] = []
    for item in parsed:
        if isinstance(item, dict):
            try:
                findings.append(CitedFinding.model_validate(item))
            except Exception:  # noqa: BLE001 — skip malformed entries
                continue
    return findings


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return datetime.min.replace(tzinfo=UTC)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return datetime.min.replace(tzinfo=UTC)


class CaseInvestigationWorkflow:
    """Deterministic data gathering (steps 1-6) followed by LLM reasoning
    (steps 7-9) producing a structured investigation report."""

    def __init__(self, connection: MCPConnection, llm: BaseChatModel) -> None:
        self._connection = connection
        self._llm = llm

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self, workflow_input: InvestigationInput) -> InvestigationReport:
        resolved_case_id = workflow_input.case_id
        resolved_case_ref = workflow_input.case_ref
        disambiguation_note: str | None = None

        # --- Input resolution (customer_name → single active case) ---
        if workflow_input.customer_name is not None:
            resolution = await self._resolve_customer_name(workflow_input.customer_name)
            if resolution.error is not None:
                return self._error_report(resolution.error)
            resolved_case_ref = resolution.case_ref
            disambiguation_note = resolution.note

        # --- Step 1: case details ---
        case_args: dict[str, Any] = {}
        if resolved_case_id is not None:
            case_args["case_id"] = str(resolved_case_id)
        else:
            case_args["case_ref"] = resolved_case_ref

        case = await self._call_tool("get_case_details", case_args)
        if not case:
            return self._error_report("Case not found")

        case_id = case.get("id")
        customer_id = case.get("customer_id")
        case_ref = str(case.get("case_ref", resolved_case_ref or ""))

        # --- Steps 2-6: gather context ---
        customer = await self._call_tool(
            "get_customer_profile", {"customer_id": customer_id}
        )
        accounts = await self._call_tool(
            "get_customer_accounts", {"customer_id": customer_id}
        )
        related = await self._call_tool(
            "list_cases", {"customer_id": customer_id, "limit": 20}
        )
        logger.info(
            "Investigation step 4 | list_cases | customer_id=%s | got=%s",
            customer_id,
            "None" if related is None else f"{len(self._as_list(related))} case(s)",
        )
        related_cases = [
            item for item in self._as_list(related) if item.get("id") != case_id
        ]
        timeline = await self._call_tool("get_case_timeline", {"case_id": case_id})
        next_actions = await self._call_tool("get_next_actions", {"case_id": case_id})

        gathered = {
            "case_data": json.dumps(_serialise_for_prompt(case), default=str),
            "customer_data": json.dumps(_serialise_for_prompt(customer), default=str),
            "accounts_data": json.dumps(_serialise_for_prompt(accounts), default=str),
            "related_cases_data": json.dumps(
                _serialise_for_prompt(related_cases), default=str
            ),
            "timeline_data": json.dumps(_serialise_for_prompt(timeline), default=str),
            "next_actions_data": json.dumps(
                _serialise_for_prompt(next_actions), default=str
            ),
        }

        # --- Step 7: risk indicators (LLM) ---
        risk_indicators, step7_error = await self._run_findings_step(
            RISK_INDICATORS_PROMPT, gathered
        )

        # --- Step 8: evidence gaps (LLM) ---
        evidence_gaps, step8_error = await self._run_findings_step(
            EVIDENCE_GAPS_PROMPT, gathered
        )

        # --- Step 9: recommendation + narrative (LLM) ---
        recommendation, step9_error = await self._run_recommendation_step(
            gathered, risk_indicators, evidence_gaps
        )

        llm_notes = [
            note for note in (step7_error, step8_error, step9_error) if note is not None
        ]
        reasoning = recommendation.reasoning
        if llm_notes:
            reasoning = (
                (reasoning + " " if reasoning else "")
                + "LLM reasoning incomplete: "
                + "; ".join(llm_notes)
            )

        return InvestigationReport(
            case_ref=case_ref,
            case_summary=recommendation.case_summary,
            customer_context=recommendation.customer_context,
            vulnerability_context=recommendation.vulnerability_context,
            risk_indicators=risk_indicators,
            evidence_gaps=evidence_gaps,
            recommended_action=recommendation.recommended_action,
            recommended_action_type=recommendation.recommended_action_type,
            reasoning=reasoning,
            disambiguation_note=disambiguation_note,
        )

    # ------------------------------------------------------------------
    # Input resolution
    # ------------------------------------------------------------------

    async def _resolve_customer_name(self, customer_name: str) -> _Resolution:
        customers = self._as_list(
            await self._call_tool(
                "list_customers", {"name_contains": customer_name, "limit": 10}
            )
        )

        if not customers:
            return _Resolution(error="No customer found matching name")
        if len(customers) > 1:
            return _Resolution(
                error=(
                    "Multiple customers match this name — "
                    "please provide a case_ref or customer_id"
                )
            )

        customer_id = customers[0].get("id")

        customer_cases = self._as_list(
            await self._call_tool(
                "list_cases", {"customer_id": customer_id, "limit": 20}
            )
        )
        active_cases = [
            c for c in customer_cases if c.get("status") in ACTIVE_CASE_STATUSES
        ]

        if not active_cases:
            return _Resolution(error="No active cases for this customer")

        active_cases.sort(
            key=lambda c: (
                PRIORITY_ORDER.get(str(c.get("priority", "p4")), 3),
                -_parse_datetime(c.get("opened_date")).timestamp(),
            )
        )
        chosen = active_cases[0]
        chosen_ref = str(chosen.get("case_ref", ""))

        if len(active_cases) > 1:
            others = [str(c.get("case_ref", "")) for c in active_cases[1:]]
            note = (
                f"Multiple active cases found — investigating {chosen_ref} "
                f"(highest priority, most recent). "
                f"Other cases: {', '.join(others)}."
            )
        else:
            note = f"Resolved from customer name {customer_name} to case {chosen_ref}."

        return _Resolution(case_ref=chosen_ref, note=note)

    # ------------------------------------------------------------------
    # Tool calls
    # ------------------------------------------------------------------

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call an MCP tool, logging failures with full context for debugging.

        Retries once on a transient empty MCP response ("No output
        returned") before giving up — this has been observed occasionally
        under rapid back-to-back requests and is not a data error.

        Returns parsed JSON (dict/list) or None on failure.
        """
        for attempt in range(2):
            try:
                raw = await self._connection.call_tool(name, arguments)
            except Exception:
                logger.exception(
                    "Investigation tool call %s raised | args=%s", name, arguments
                )
                return None

            if raw == "No output returned" and attempt == 0:
                logger.warning(
                    "Investigation tool call %s returned no output, retrying | args=%s",
                    name,
                    arguments,
                )
                continue

            if isinstance(raw, str) and raw.startswith("Error:"):
                logger.warning(
                    "Investigation tool call %s failed | args=%s | response=%.300s",
                    name,
                    arguments,
                    raw,
                )
                return None

            try:
                # json.loads handles "null" (not found) distinctly from garbage.
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Investigation tool call %s returned unparseable data | args=%s | response=%.300s",
                    name,
                    arguments,
                    raw,
                )
                return None
        return None

    # ------------------------------------------------------------------
    # LLM steps
    # ------------------------------------------------------------------

    async def _run_findings_step(
        self, prompt: str, gathered: dict[str, str]
    ) -> tuple[list[CitedFinding], str | None]:
        """Run an LLM step expected to return a JSON array of CitedFinding objects."""
        try:
            response = await self._llm.ainvoke(
                [SystemMessage(content=prompt.format(**gathered))]
            )
            return _parse_cited_findings(content_to_text(response.content)), None
        except Exception as exc:  # noqa: BLE001 — report partial results
            logger.warning("Investigation LLM step failed: %s", exc)
            return [], str(exc)

    async def _run_recommendation_step(
        self,
        gathered: dict[str, str],
        risk_indicators: list[CitedFinding],
        evidence_gaps: list[CitedFinding],
    ) -> tuple[_RecommendationResult, str | None]:
        try:
            response = await self._llm.ainvoke(
                [
                    SystemMessage(
                        content=RECOMMENDATION_PROMPT.format(
                            **gathered,
                            risk_indicators=json.dumps(
                                [item.model_dump() for item in risk_indicators]
                            ),
                            evidence_gaps=json.dumps(
                                [item.model_dump() for item in evidence_gaps]
                            ),
                        )
                    )
                ]
            )
            parsed = safe_json_parse(content_to_text(response.content))
            if not isinstance(parsed, dict):
                return _RecommendationResult(), (
                    "recommendation step returned unparseable output"
                )
            return _RecommendationResult.model_validate(parsed), None
        except Exception as exc:  # noqa: BLE001 — report partial results
            logger.warning("Investigation recommendation step failed: %s", exc)
            return _RecommendationResult(), str(exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _as_list(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    def _error_report(self, message: str) -> InvestigationReport:
        return InvestigationReport(case_summary=message)


class _Resolution:
    """Internal result of resolving a customer name to a case."""

    def __init__(
        self,
        case_ref: str | None = None,
        note: str | None = None,
        error: str | None = None,
    ) -> None:
        self.case_ref = case_ref
        self.note = note
        self.error = error


def _format_detected_at(value: str | None) -> str | None:
    """Render an ISO date string as 'DD Mon YYYY', falling back to the raw value."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d %b %Y")


def _render_finding(item: CitedFinding) -> str:
    """Render one CitedFinding as a markdown bullet with an inline citation,
    omitting any citation parts that are missing."""
    lead = f"flagged by {item.source_system}" if item.source_system else None
    detected_at = _format_detected_at(item.detected_at)
    date_part = f"on {detected_at}" if detected_at else None
    parenthetical = ", ".join(
        part for part in (item.source_id, item.confidence) if part
    )

    if lead or date_part:
        citation = " ".join(
            part
            for part in (
                lead,
                date_part,
                f"({parenthetical})" if parenthetical else None,
            )
            if part
        )
    elif parenthetical:
        citation = f"citing {parenthetical}"
    else:
        citation = ""

    if citation:
        return f"- **{item.finding}** — {citation}. {item.explanation}"
    return f"- **{item.finding}** — {item.explanation}"


def render_report_markdown(report: InvestigationReport) -> str:
    """Render an InvestigationReport as a markdown answer for the chat."""

    if (
        not report.risk_indicators
        and not report.recommended_action
        and report.case_summary
    ):
        # Error report — surface the message directly.
        return f"### Investigation\n\n{report.case_summary}"

    lines: list[str] = [f"### Investigation Report — {report.case_ref}", ""]
    if report.disambiguation_note:
        lines += [f"> {report.disambiguation_note}", ""]
    lines += ["#### Case Summary", report.case_summary or "—", ""]
    lines += ["#### Customer Context", report.customer_context or "—", ""]
    if report.vulnerability_context:
        lines += ["#### Vulnerability Context", report.vulnerability_context, ""]
    lines += ["#### Risk Indicators"]
    lines += [_render_finding(item) for item in report.risk_indicators] or [
        "- None identified"
    ]
    lines += ["", "#### Evidence Gaps"]
    lines += [_render_finding(item) for item in report.evidence_gaps] or [
        "- None identified"
    ]
    lines += ["", "#### Recommended Action"]
    action = report.recommended_action or "—"
    if report.recommended_action_type:
        action = f"{action} (`{report.recommended_action_type}`)"
    lines += [action, "", "#### Reasoning", report.reasoning or "—", ""]
    return "\n".join(lines)
