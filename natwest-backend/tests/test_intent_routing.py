"""Tests for the intent-based routing architecture.

Covers:
- Router LLM classification → IntentCategory (no pattern matching)
- Agent tool binding per category
- The investigation workflow tool wrapper end-to-end (fake MCP + fake LLM)
- Agent behaviour for UNCLEAR (no tools, clarifying question)
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from natwest_backend.agent.graph.routing import (
    DEFAULT_CATEGORY,
    IntentCategory,
)
from natwest_backend.agent.nodes.react_agent_node import get_tools_for_category
from natwest_backend.agent.nodes.router_node import create_router_node, parse_category
from natwest_backend.agent.tools.investigation_tool import (
    InvestigationWorkflowTool,
)


def run(coro: Any) -> Any:
    return asyncio.run(coro)


# ----------------------------------------------------------------------
# Router classification
# ----------------------------------------------------------------------


class FakeRouterLLM:
    """Returns a fixed classification regardless of input."""

    def __init__(self, verdict: str) -> None:
        self.verdict = verdict
        self.last_prompt: str = ""

    async def ainvoke(self, messages: list[Any], config: Any = None) -> Any:
        self.last_prompt = messages[0].content
        return SimpleNamespace(content=self.verdict)


def _router_state(text: str, history: list[Any] | None = None) -> dict[str, Any]:
    messages = list(history or []) + [HumanMessage(content=text)]
    return {
        "messages": messages,
        "route": "safe",
        "category": "",
        "tool_call_count": 0,
        "skill_context": "",
    }


def test_router_classifies_investigation_intent() -> None:
    llm = FakeRouterLLM("INVESTIGATION")
    node = create_router_node(llm)  # type: ignore[arg-type]

    for message in (
        "investigate CASE-1001",
        "investigate a case for Aisha",
        "run investigation on Aisha Rahman's fraud case",
        "look into what's happening with the Sarah Malik case",
    ):
        result = run(node(_router_state(message), {}))
        assert result["category"] == IntentCategory.INVESTIGATION.value, message


def test_router_classifies_operational_query() -> None:
    llm = FakeRouterLLM("OPERATIONAL_QUERY")
    node = create_router_node(llm)  # type: ignore[arg-type]

    result = run(node(_router_state("show me open P1 cases"), {}))
    assert result["category"] == IntentCategory.OPERATIONAL_QUERY.value


def test_router_classifies_unclear() -> None:
    llm = FakeRouterLLM("UNCLEAR")
    node = create_router_node(llm)  # type: ignore[arg-type]

    result = run(node(_router_state("help me with this"), {}))
    assert result["category"] == IntentCategory.UNCLEAR.value


def test_router_passes_conversation_history_to_llm() -> None:
    llm = FakeRouterLLM("INVESTIGATION")
    node = create_router_node(llm)  # type: ignore[arg-type]
    history = [
        HumanMessage(content="show me CASE-1004"),
        AIMessage(content="CASE-1004 is an open fraud case for David Thompson."),
    ]

    run(node(_router_state("investigate this one", history), {}))

    assert "CASE-1004" in llm.last_prompt
    assert "investigate this one" in llm.last_prompt


def test_router_unknown_output_falls_back_to_unclear() -> None:
    llm = FakeRouterLLM("banana")
    node = create_router_node(llm)  # type: ignore[arg-type]

    result = run(node(_router_state("anything"), {}))
    assert result["category"] == DEFAULT_CATEGORY.value


def test_parse_category_tolerates_formatting() -> None:
    assert parse_category("INVESTIGATION") == IntentCategory.INVESTIGATION
    assert parse_category('"operational_query"') == IntentCategory.OPERATIONAL_QUERY
    assert parse_category("Unclear.") == IntentCategory.UNCLEAR
    assert parse_category("nonsense") == DEFAULT_CATEGORY


# ----------------------------------------------------------------------
# Tool binding per category
# ----------------------------------------------------------------------


class _StubTool:
    def __init__(self, name: str) -> None:
        self.name = name


OPERATIONAL = [_StubTool(name) for name in ["list_customers", "list_cases"]]
INVESTIGATION = [_StubTool("invoke_investigation_workflow")]


def test_investigation_category_binds_only_workflow_tool() -> None:
    tools = get_tools_for_category(
        IntentCategory.INVESTIGATION,
        operational_tools=OPERATIONAL,  # type: ignore[list-item]
        investigation_tools=INVESTIGATION,  # type: ignore[list-item]
    )
    assert [t.name for t in tools] == ["invoke_investigation_workflow"]


def test_operational_category_binds_all_mcp_tools() -> None:
    tools = get_tools_for_category(
        IntentCategory.OPERATIONAL_QUERY,
        operational_tools=OPERATIONAL,  # type: ignore[list-item]
        investigation_tools=INVESTIGATION,  # type: ignore[list-item]
    )
    assert [t.name for t in tools] == ["list_customers", "list_cases"]


def test_unclear_category_binds_no_tools() -> None:
    tools = get_tools_for_category(
        IntentCategory.UNCLEAR,
        operational_tools=OPERATIONAL,  # type: ignore[list-item]
        investigation_tools=INVESTIGATION,  # type: ignore[list-item]
    )
    assert tools == []


# ----------------------------------------------------------------------
# Investigation workflow tool wrapper
# ----------------------------------------------------------------------

CUSTOMER_ID = str(uuid4())
CASE_ID = str(uuid4())

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

CUSTOMER = {
    "id": CUSTOMER_ID,
    "full_name": "Aisha Rahman",
    "date_of_birth": "1988-06-14",
    "email": "aisha.rahman@example.com",
    "phone": "+44 7700 900101",
    "kyc_status": "verified",
    "kyc_last_reviewed": "2026-01-01T00:00:00+00:00",
    "is_flagged": False,
    "customer_since": "2018-02-01",
    "tier": "premium",
    "created_at": "2024-01-01T00:00:00+00:00",
    "active_vulnerability_signals": [],
    "resolved_vulnerability_signals": [],
}

RECOMMENDATION_JSON = json.dumps(
    {
        "case_summary": "Fraud case involving unrecognised card transactions in Spain.",
        "customer_context": "Aisha Rahman is a premium customer since 2018.",
        "vulnerability_context": None,
        "recommended_action": "Contact the customer to verify the transactions.",
        "recommended_action_type": "contact_customer",
        "reasoning": "High-value fraud case flagged by the fraud engine.",
    }
)


class FakeMCPConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        self.calls.append((name, arguments))
        if name == "list_customers":
            needle = str(arguments.get("name_contains", "")).lower()
            return json.dumps([CUSTOMER] if needle in "aisha rahman" else [])
        if name == "get_case_details":
            ref = arguments.get("case_ref")
            if ref is not None:
                return json.dumps(CASE) if ref == "CASE-1001" else "null"
            return json.dumps(CASE)
        if name == "get_customer_profile":
            return json.dumps(CUSTOMER)
        if name == "get_customer_accounts":
            return json.dumps([])
        if name == "list_cases":
            status = arguments.get("status")
            cases = [CASE]
            if status is not None:
                cases = [c for c in cases if c["status"] == status]
            return json.dumps(cases)
        if name in {"get_case_timeline", "get_next_actions"}:
            return json.dumps([])
        raise AssertionError(f"Unexpected tool call: {name}")


class FakeWorkflowLLM:
    async def ainvoke(self, messages: list[Any], config: Any = None) -> Any:
        prompt = messages[0].content
        if "identify risk indicators" in prompt:
            return SimpleNamespace(
                content=json.dumps(
                    [
                        {
                            "finding": "Disputed amount £3,475.80 exceeds £1,000",
                            "source_type": "case_attribute",
                            "source_id": None,
                            "source_system": None,
                            "confidence": None,
                            "detected_at": None,
                            "explanation": "Disputed amount exceeds the £1,000 threshold.",
                        }
                    ]
                )
            )
        if "spot what is *missing*" in prompt:
            return SimpleNamespace(content="[]")
        if "completing a NatWest case investigation report" in prompt:
            return SimpleNamespace(content=RECOMMENDATION_JSON)
        raise AssertionError(f"Unexpected prompt: {prompt[:80]}")


def _make_tool() -> InvestigationWorkflowTool:
    return InvestigationWorkflowTool(
        connection=FakeMCPConnection(),  # type: ignore[arg-type]
        llm=FakeWorkflowLLM(),  # type: ignore[arg-type]
    )


def test_workflow_tool_with_case_ref() -> None:
    tool = _make_tool()
    result = run(tool._arun(case_ref="CASE-1001"))

    assert "CASE-1001" in result
    assert "Fraud case involving unrecognised card transactions" in result
    called = {name for name, _ in tool.connection.calls}
    assert "get_case_details" in called
    assert "list_customers" not in called  # no name resolution for case_ref


def test_workflow_tool_with_customer_name() -> None:
    tool = _make_tool()
    result = run(tool._arun(customer_name="Aisha"))

    assert "CASE-1001" in result
    called = [name for name, _ in tool.connection.calls]
    assert called[0] == "list_customers"
    assert "get_case_details" in called


def test_workflow_tool_rejects_missing_identifier() -> None:
    tool = _make_tool()
    try:
        run(tool._arun())
    except ValueError as exc:
        assert "Exactly one" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for empty input")


def test_workflow_tool_case_not_found() -> None:
    tool = _make_tool()
    result = run(tool._arun(case_ref="CASE-9999"))

    assert "Case not found" in result
