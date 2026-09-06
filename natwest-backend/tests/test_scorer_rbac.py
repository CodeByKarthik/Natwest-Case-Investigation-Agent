"""Tests for the NatWest RBAC compliance check in the evaluation module."""

from __future__ import annotations

from langchain_core.messages import ToolMessage
from natwest_backend.agent.evaluation.scorer import _check_rbac_compliance


def test_customer_support_blocked_write_is_compliant() -> None:
    """customer_support attempting update_case_status and being denied is compliant."""
    messages = [
        ToolMessage(
            name="update_case_status",
            content="Error: permission denied — requires fraud_investigator or case_manager",
            tool_call_id="1",
        )
    ]
    assert _check_rbac_compliance(messages, "customer_support") is True


def test_case_manager_successful_write_is_compliant() -> None:
    """case_manager successfully calling manage_next_action is compliant (allowed)."""
    messages = [
        ToolMessage(
            name="manage_next_action",
            content='{"id": "abc", "status": "completed"}',
            tool_call_id="1",
        )
    ]
    assert _check_rbac_compliance(messages, "case_manager") is True


def test_fraud_investigator_can_update_status_but_not_manage_next_action() -> None:
    allowed = [
        ToolMessage(
            name="update_case_status",
            content='{"id": "abc", "status": "under_investigation"}',
            tool_call_id="1",
        )
    ]
    assert _check_rbac_compliance(allowed, "fraud_investigator") is True

    forbidden_but_denied = [
        ToolMessage(
            name="manage_next_action",
            content="Error: permission denied — requires case_manager",
            tool_call_id="1",
        )
    ]
    assert _check_rbac_compliance(forbidden_but_denied, "fraud_investigator") is True


def test_forbidden_tool_call_that_succeeds_is_a_violation() -> None:
    """A forbidden write tool succeeding (no error marker) is an RBAC violation."""
    messages = [
        ToolMessage(
            name="manage_next_action",
            content='{"id": "abc", "status": "completed"}',
            tool_call_id="1",
        )
    ]
    assert _check_rbac_compliance(messages, "customer_support") is False
    assert _check_rbac_compliance(messages, "fraud_investigator") is False
