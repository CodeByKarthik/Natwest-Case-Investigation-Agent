import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from natwest_mcp.mcp.tools.business_tools import (
    get_case_details,
    get_customer_profile,
    list_cases,
    list_customers,
    manage_next_action,
    update_case_status,
)
from natwest_mcp.mcp.tools.tool_registry import TOOLS
from natwest_shared.db.models.business import (
    Account,
    Case,
    CaseEvent,
    Customer,
    NextAction,
)


class FakeMCPService:
    def __init__(self) -> None:
        self.customer = Customer(
            id=uuid4(),
            full_name="Aisha Rahman",
            date_of_birth=datetime(1988, 6, 14, tzinfo=UTC).date(),
            email="aisha.rahman@example.com",
            phone="+44 7700 900101",
            customer_since=datetime(2018, 2, 1, tzinfo=UTC).date(),
            kyc_status="verified",
            kyc_last_reviewed=datetime(2025, 1, 1, tzinfo=UTC),
            is_flagged=False,
            tier="premium",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        self.account = Account(
            id=uuid4(),
            customer_id=self.customer.id,
            account_number="12345678",
            sort_code="040004",
            account_type="current",
            balance=2500.00,
            status="active",
            opened_date=datetime(2018, 2, 1, tzinfo=UTC).date(),
        )
        self.case = Case(
            id=uuid4(),
            customer_id=self.customer.id,
            case_ref="CASE-1001",
            case_type="fraud",
            status="open",
            priority="p1",
            assigned_user_id=uuid4(),
            opened_date=datetime(2025, 1, 15, tzinfo=UTC),
            updated_at=datetime(2025, 1, 16, tzinfo=UTC),
            disputed_amount=Decimal("1500.00"),
            merchant_name="Contoso",
            consumer_duty_flag=True,
            description="Suspicious card use",
            created_at=datetime(2025, 1, 15, tzinfo=UTC),
        )
        self.timeline = [
            CaseEvent(
                id=uuid4(),
                case_id=self.case.id,
                event_type="system_alert",
                event_description="Fraud engine flagged the transaction",
                created_by_user_id=None,
                created_by_system="fraud_engine",
                source_record_id=None,
                created_at=datetime(2025, 1, 16, tzinfo=UTC),
            )
        ]
        self.next_action = NextAction(
            id=uuid4(),
            case_id=self.case.id,
            action_type="request_documents",
            description="Collect recent statements",
            due_date=datetime(2025, 1, 25, tzinfo=UTC),
            status="open",
            assigned_user_id=uuid4(),
            created_by_user_id=uuid4(),
            completed_at=None,
            created_at=datetime(2025, 1, 17, tzinfo=UTC),
            updated_at=datetime(2025, 1, 17, tzinfo=UTC),
        )

    def get_customer_by_name(self, *, name):
        return self.customer

    def list_customers(self, **_kwargs: object) -> list[Customer]:
        return [self.customer]

    def get_customer_profile(self, *, customer_id):
        return self.customer

    def get_customer_accounts(self, *, customer_id):
        return [self.account]

    def list_cases(self, **_kwargs: object) -> list[Case]:
        return [self.case]

    def get_case_details(self, *, case_id=None, case_ref=None):
        return self.case

    def get_case_timeline(self, *, case_id):
        return self.timeline

    def get_next_actions(self, *, case_id):
        return [self.next_action]

    def update_case_status(
        self, *, case_id, new_status, reason, **_kwargs: object
    ) -> Case:
        self.case.status = new_status
        return self.case

    def manage_next_action(
        self, *, operation, case_id=None, action_id=None, fields=None
    ):
        return self.next_action


def test_registry_exposes_expected_natwest_tool_names() -> None:
    tool_names = {func.__name__ for func, _ in TOOLS}

    expected = {
        "list_customers",
        "list_cases",
        "get_customer_profile",
        "get_customer_accounts",
        "get_case_details",
        "get_case_timeline",
        "update_case_status",
        "get_next_actions",
        "manage_next_action",
    }

    assert tool_names == expected


def test_customer_and_case_tools_return_natwest_read_models() -> None:
    service = FakeMCPService()

    customer = asyncio.run(
        get_customer_profile(customer_id=service.customer.id, service=service)
    )
    assert customer is not None
    assert customer.full_name == "Aisha Rahman"
    assert customer.tier == "premium"

    customers = asyncio.run(list_customers(name_contains="Aisha", service=service))
    assert len(customers) == 1
    assert customers[0].email == "aisha.rahman@example.com"

    case = asyncio.run(get_case_details(case_id=service.case.id, service=service))
    assert case is not None
    assert case.case_ref == "CASE-1001"
    assert case.case_type == "fraud"

    cases = asyncio.run(list_cases(service=service))
    assert len(cases) == 1
    assert cases[0].case_ref == "CASE-1001"


def test_case_update_and_next_action_tools_are_accepted() -> None:
    service = FakeMCPService()

    updated = asyncio.run(
        update_case_status(
            case_id=service.case.id,
            new_status="under_investigation",
            reason="Escalated for deeper review",
            service=service,
        )
    )
    assert updated.status == "under_investigation"

    action = asyncio.run(
        manage_next_action(
            operation="update",
            action_id=service.next_action.id,
            fields={"description": "Follow up with customer"},
            service=service,
        )
    )
    assert action is not None
    assert action.description == "Collect recent statements"
