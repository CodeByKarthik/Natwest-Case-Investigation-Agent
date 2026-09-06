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
    _serialise_for_prompt,
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

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def ainvoke(self, messages: list[Any], config: Any = None) -> Any:
        prompt = messages[0].content
        self.prompts.append(prompt)
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


def test_serialise_for_prompt_strips_uuid_fields_but_keeps_human_refs() -> None:
    raw = {
        "id": "d438c96f-23fe-4583-a292-2eff0854a983",
        "customer_id": "0d4eff6d-c530-4c9b-bbee-2abd5101c53e",
        "case_ref": "CASE-1001",
        "assigned_user_id": "1938aeda-b7b4-47bc-aceb-66e7e042d854",
        "nested": [
            {
                "source_record_id": "11111111-1111-1111-1111-111111111111",
                "source_ref": "FE-2026-8891",
                "account_number": "12345678",
            }
        ],
    }

    cleaned = _serialise_for_prompt(raw)

    assert "id" not in cleaned
    assert "customer_id" not in cleaned
    assert "assigned_user_id" not in cleaned
    assert cleaned["case_ref"] == "CASE-1001"
    assert "source_record_id" not in cleaned["nested"][0]
    assert cleaned["nested"][0]["source_ref"] == "FE-2026-8891"
    assert cleaned["nested"][0]["account_number"] == "12345678"


def test_serialise_for_prompt_humanizes_dates_but_keeps_non_dates() -> None:
    raw = {
        "opened_date": "2026-09-01T01:54:28.526588Z",
        "created_at": "2026-09-05T00:00:00+00:00",
        "customer_since": "2018-02-01",
        "case_ref": "CASE-1001",
        "source_ref": "FE-2026-8891",
        "disputed_amount": "3475.80",
    }

    cleaned = _serialise_for_prompt(raw)

    assert cleaned["opened_date"] == "01 Sep 2026, 01:54"
    assert cleaned["created_at"] == "05 Sep 2026"
    assert cleaned["customer_since"] == "01 Feb 2018"
    assert cleaned["case_ref"] == "CASE-1001"
    assert cleaned["source_ref"] == "FE-2026-8891"
    assert cleaned["disputed_amount"] == "3475.80"


def test_happy_path_with_case_ref() -> None:
    connection = FakeMCPConnection(cases_by_ref={"CASE-1001": CASE}, all_cases=[CASE])
    llm = FakeLLM()
    workflow = CaseInvestigationWorkflow(connection=connection, llm=llm)  # type: ignore[arg-type]

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
    called = {name for name, _ in connection.calls}
    assert called == {
        "get_case_details",
        "get_customer_profile",
        "get_customer_accounts",
        "list_cases",
        "get_case_timeline",
        "get_next_actions",
    }

    for prompt in llm.prompts:
        assert CASE_ID not in prompt
        assert CUSTOMER_ID not in prompt
        assert "CASE-1001" in prompt


def test_happy_path_with_customer_name_single_case() -> None:
    connection = FakeMCPConnection(cases_by_ref={"CASE-1001": CASE}, all_cases=[CASE])
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(customer_name="Jane Doe")))

    assert report.case_ref == "CASE-1001"
    assert report.disambiguation_note == (
        "Resolved from customer name Jane Doe to case CASE-1001."
    )
    called = [name for name, _ in connection.calls]
    assert called[0] == "list_customers"
    assert "get_case_details" in called


def test_customer_name_resolves_pending_customer_case_as_active() -> None:
    """Regression: a case in pending_customer status is still active work and
    must resolve, not be treated as inactive like resolved/closed."""
    pending_case = {**CASE, "case_ref": "CASE-1006", "status": "pending_customer"}
    connection = FakeMCPConnection(
        cases_by_ref={"CASE-1006": pending_case}, all_cases=[pending_case]
    )
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(customer_name="Jane Doe")))

    assert report.case_ref == "CASE-1006"
    assert report.case_summary != "No active cases for this customer"


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
    assert [name for name, _ in connection.calls] == ["get_case_details"]


def test_unknown_customer_name_returns_error_report() -> None:
    connection = FakeMCPConnection(cases_by_ref={}, all_cases=[])
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(customer_name="Nobody Smith")))

    assert report.case_summary == "No customer found matching name"
    assert [name for name, _ in connection.calls] == ["list_customers"]


def test_failed_tool_call_continues_with_partial_data() -> None:
    connection = FakeMCPConnection(cases_by_ref={"CASE-1001": CASE}, all_cases=[CASE])

    async def failing_call_tool(name: str, arguments: dict[str, Any]) -> str:
        if name == "get_case_timeline":
            return "Error: MCP server unavailable"
        return await FakeMCPConnection.call_tool(connection, name, arguments)

    connection.call_tool = failing_call_tool  # type: ignore[method-assign]
    workflow = CaseInvestigationWorkflow(connection=connection, llm=FakeLLM())  # type: ignore[arg-type]

    report = run(workflow.execute(InvestigationInput(case_ref="CASE-1001")))

    assert report.case_ref == "CASE-1001"
    assert (
        report.case_summary
    )  # workflow continued with partial data despite the failed call
