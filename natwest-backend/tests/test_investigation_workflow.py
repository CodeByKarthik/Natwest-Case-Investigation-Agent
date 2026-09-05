"""End-to-end tests for the case investigation workflow.

Uses a fake MCPConnection returning canned tool JSON and a fake LLM
returning deterministic step 7-9 outputs. No network, no database.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from natwest_backend.agent.skills.investigation_workflow import (
    CaseInvestigationWorkflow,
    InvestigationInput,
)

CUSTOMER_ID = str(uuid4())
CASE_ID = str(uuid4())
OTHER_CASE_ID = str(uuid4())

CASE = {
    "id": CASE_ID,
    "customer_id": CUSTOMER_ID,
    "case_ref": "CASE-1001",
    "case_type": "fraud",
    "status": "open",
    "priority": "p1",
    "assigned_user_id": str(uuid4()),
    "disputed_amount": "3475.80",
    "merchant_name": "Northlake Travel",
    "consumer_duty_flag": True,
    "description": "Unrecognised card transactions in Spain.",
    "opened_date": "2026-09-01T09:00:00+00:00",
    "created_at": "2026-09-01T09:00:00+00:00",
    "updated_at": "2026-09-01T09:00:00+00:00",
}

OTHER_CASE = {
    **CASE,
    "id": OTHER_CASE_ID,
    "case_ref": "CASE-1004",
    "case_type": "complaint",
    "priority": "p2",
    "consumer_duty_flag": False,
    "opened_date": "2026-09-03T09:00:00+00:00",
}

CUSTOMER = {
    "id": CUSTOMER_ID,
    "full_name": "Jane Doe",
    "date_of_birth": "1990-01-01",
    "email": "jane.doe@example.com",
    "phone": "+44 7700 900000",
    "kyc_status": "verified",
    "kyc_last_reviewed": "2026-01-01T00:00:00+00:00",
    "is_flagged": True,
    "customer_since": "2018-01-01",
    "tier": "premium",
    "created_at": "2024-01-01T00:00:00+00:00",
    "active_vulnerability_signals": [
        {
            "id": str(uuid4()),
            "vulnerability_type": "life_event",
            "status": "active",
            "notes": "Recent bereavement.",
            "source_record_id": None,
            "source_record": None,
            "detected_at": "2026-09-02T00:00:00+00:00",
            "resolved_at": None,
            "created_at": "2026-09-02T00:00:00+00:00",
        }
    ],
    "resolved_vulnerability_signals": [],
}

RECOMMENDATION_JSON = json.dumps(
    {
        "case_summary": "Fraud case involving unrecognised card transactions in Spain.",
        "customer_context": "Jane Doe is a premium customer since 2018 with verified KYC.",
        "vulnerability_context": "Active life_event vulnerability (recent bereavement).",
        "recommended_action": "Contact the customer using sensitive handling to verify the transactions.",
        "recommended_action_type": "contact_customer",
        "reasoning": "High-value fraud case with an active vulnerability signal.",
    }
)


class FakeMCPConnection:
    """Mimics MCPConnection.call_tool with canned JSON responses."""

    def __init__(
        self, cases_by_ref: dict[str, dict[str, Any]], all_cases: list[dict[str, Any]]
    ) -> None:
        self._cases_by_ref = cases_by_ref
        self._all_cases = all_cases
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        self.calls.append((name, arguments))

        if name == "list_customers":
            name_filter = str(arguments.get("name_contains", "")).lower()
            matches = [CUSTOMER] if name_filter in CUSTOMER["full_name"].lower() else []
            return json.dumps(matches)

        if name == "get_case_details":
            ref = arguments.get("case_ref")
            if ref is not None:
                case = self._cases_by_ref.get(str(ref))
                return json.dumps(case) if case else "null"
            return json.dumps(CASE)

        if name == "get_customer_profile":
            return json.dumps(CUSTOMER)

        if name == "get_customer_accounts":
            return json.dumps([])

        if name == "list_cases":
            status = arguments.get("status")
            cases = self._all_cases
            if status is not None:
                cases = [c for c in cases if c["status"] == status]
            return json.dumps(cases)

        if name == "get_case_timeline":
            return json.dumps([])

        if name == "get_next_actions":
            return json.dumps([])

        raise AssertionError(f"Unexpected tool call: {name}")


class FakeLLM:
    """Mimics ChatOpenAI.ainvoke with deterministic placeholder answers."""

    async def ainvoke(self, messages: list[Any], config: Any = None) -> Any:
        prompt = messages[0].content
        if "identify risk indicators" in prompt:
            return SimpleNamespace(
                content=json.dumps(
                    [
                        {
                            "finding": "Active life_event vulnerability signal",
                            "source_type": "vulnerability_register",
                            "source_id": None,
                            "source_system": None,
                            "confidence": None,
                            "detected_at": "2026-09-02T00:00:00+00:00",
                            "explanation": "Customer has a recent bereavement-related vulnerability signal.",
                        }
                    ]
                )
            )
        if "spot what is *missing*" in prompt:
            return SimpleNamespace(
                content=json.dumps(
                    [
                        {
                            "finding": "No request_documents action despite an open disputed transaction",
                            "source_type": "next_actions",
                            "source_id": None,
                            "source_system": None,
                            "confidence": None,
                            "detected_at": None,
                            "explanation": "Disputed amount is £3,475.80 but no request_documents action exists.",
                        }
                    ]
                )
            )
        if "completing a NatWest case investigation report" in prompt:
            return SimpleNamespace(content=RECOMMENDATION_JSON)
        raise AssertionError(f"Unexpected prompt: {prompt[:80]}")


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_investigation_input_requires_exactly_one_identifier() -> None:
    with pytest.raises(ValueError):
        InvestigationInput()
    with pytest.raises(ValueError):
        InvestigationInput(case_ref="CASE-1001", customer_name="Jane Doe")


def test_happy_path_with_case_ref() -> None:
    connection = FakeMCPConnection(cases_by_ref={"CASE-1001": CASE}, all_cases=[CASE])
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(case_ref="CASE-1001")))

    assert report.case_ref == "CASE-1001"
    assert report.case_summary
    assert report.customer_context
    assert report.vulnerability_context is not None
    assert report.risk_indicators
    assert report.evidence_gaps
    assert report.recommended_action
    assert report.recommended_action_type == "contact_customer"
    assert report.reasoning
    assert report.disambiguation_note is None
    assert report.data_sources == [
        "get_case_details",
        "get_customer_profile",
        "get_customer_accounts",
        "list_cases",
        "get_case_timeline",
        "get_next_actions",
    ]


def test_happy_path_with_customer_name_single_case() -> None:
    connection = FakeMCPConnection(cases_by_ref={"CASE-1001": CASE}, all_cases=[CASE])
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(customer_name="Jane Doe")))

    assert report.case_ref == "CASE-1001"
    assert report.disambiguation_note == (
        "Resolved from customer name Jane Doe to case CASE-1001."
    )
    assert report.data_sources[0] == "list_customers"
    assert "get_case_details" in report.data_sources


def test_customer_name_with_multiple_cases_picks_highest_priority() -> None:
    connection = FakeMCPConnection(
        cases_by_ref={"CASE-1001": CASE, "CASE-1004": OTHER_CASE},
        all_cases=[OTHER_CASE, CASE],
    )
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(customer_name="Jane Doe")))

    # CASE-1001 is p1; CASE-1004 is p2 but more recent — priority wins.
    assert report.case_ref == "CASE-1001"
    assert report.disambiguation_note is not None
    assert "Multiple active cases found" in report.disambiguation_note
    assert "CASE-1004" in report.disambiguation_note


def test_case_not_found_returns_error_report() -> None:
    connection = FakeMCPConnection(cases_by_ref={}, all_cases=[])
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(case_ref="CASE-9999")))

    assert report.case_summary == "Case not found"
    assert report.risk_indicators == []
    assert report.recommended_action == ""
    assert report.data_sources == ["get_case_details"]


def test_unknown_customer_name_returns_error_report() -> None:
    connection = FakeMCPConnection(cases_by_ref={}, all_cases=[])
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(customer_name="Nobody Smith")))

    assert report.case_summary == "No customer found matching name"
    assert report.data_sources == ["list_customers"]


def test_failed_tool_call_is_marked_in_data_sources() -> None:
    connection = FakeMCPConnection(cases_by_ref={"CASE-1001": CASE}, all_cases=[CASE])

    async def failing_call_tool(name: str, arguments: dict[str, Any]) -> str:
        if name == "get_case_timeline":
            return "Error: MCP server unavailable"
        return await FakeMCPConnection.call_tool(connection, name, arguments)

    connection.call_tool = failing_call_tool  # type: ignore[method-assign]
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(case_ref="CASE-1001")))

    assert "get_case_timeline (failed)" in report.data_sources
    assert report.case_ref == "CASE-1001"
    assert report.case_summary  # workflow continued with partial data
