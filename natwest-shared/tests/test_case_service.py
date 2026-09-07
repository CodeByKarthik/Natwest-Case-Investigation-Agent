from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from natwest_shared.auth.rbac import ADMIN_ROLES, READ_ROLES, WRITE_ROLES
from natwest_shared.common.enums import (
    AppRole,
    CaseStatusEnum,
    NextActionTypeEnum,
)
from natwest_shared.common.exceptions import PermissionDenied
from natwest_shared.db.models.business import Case, CaseEvent, Customer, NextAction
from natwest_shared.db.repositories.business_read_repository import (
    BusinessReadRepository,
)
from natwest_shared.db.repositories.business_write_repository import (
    BusinessWriteRepository,
)
from natwest_shared.schema.auth_schema import AuthContext
from natwest_shared.services.business_service import BusinessService


class FakeReadRepository:
    def __init__(self) -> None:
        self.customer = Customer(
            id=uuid4(),
            full_name="Jane Doe",
            date_of_birth=datetime(1990, 1, 1, tzinfo=UTC).date(),
            email="jane.doe@example.com",
            phone="+44 7700 900000",
            kyc_status="verified",
            kyc_last_reviewed=datetime(2024, 1, 1, tzinfo=UTC),
            is_flagged=True,
            customer_since=datetime(2018, 1, 1, tzinfo=UTC).date(),
            tier="premium",
        )
        self.case = Case(
            id=uuid4(),
            customer_id=self.customer.id,
            case_ref="CS-018",
            case_type="fraud",
            status="open",
            priority="p1",
            assigned_user_id=uuid4(),
            opened_date=datetime(2025, 1, 15, tzinfo=UTC),
            updated_at=datetime(2025, 1, 16, tzinfo=UTC),
            disputed_amount=1500,
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
        self.actions = [
            NextAction(
                id=uuid4(),
                case_id=self.case.id,
                action_type="contact_customer",
                description="Call customer",
                due_date=datetime(2025, 1, 25, tzinfo=UTC),
                status="open",
                assigned_user_id=uuid4(),
                created_by_user_id=uuid4(),
                created_at=datetime(2025, 1, 16, tzinfo=UTC),
                updated_at=datetime(2025, 1, 16, tzinfo=UTC),
            )
        ]

    def list_cases(self, **_kwargs):
        return [self.case]

    def get_customer_profile(self, _customer_id):
        return self.customer

    def get_customer_accounts(self, customer_id):
        return []

    def get_case_details(self, *, case_id=None, case_ref=None):
        return self.case

    def get_case_timeline(self, *, case_id):
        return self.timeline

    def get_next_actions(self, *, case_id):
        return self.actions

    def update_case_status(
        self,
        *,
        case_id,
        new_status,
        reason,
        updated_by_user_id=None,
    ):
        self.case.status = new_status
        return self.case

    def manage_next_action(
        self,
        *,
        operation,
        case_id=None,
        action_id=None,
        fields=None,
    ):
        if operation == "create":
            return self.actions[0]
        if operation == "update":
            return self.actions[0]
        if operation == "complete":
            self.actions[0].status = "completed"
            return self.actions[0]
        raise AssertionError(f"Unsupported operation: {operation}")


class FakeWriteRepository:
    def __init__(self) -> None:
        self.case = Case(
            id=uuid4(),
            customer_id=uuid4(),
            case_ref="CS-019",
            case_type="dispute",
            status="open",
            priority="p2",
            assigned_user_id=uuid4(),
            opened_date=datetime(2025, 2, 1, tzinfo=UTC),
            updated_at=datetime(2025, 2, 1, tzinfo=UTC),
            disputed_amount=400,
            merchant_name="Northwind",
            consumer_duty_flag=True,
            description="Disputed payment",
            created_at=datetime(2025, 2, 1, tzinfo=UTC),
        )
        self.action = NextAction(
            id=uuid4(),
            case_id=self.case.id,
            action_type="request_documents",
            description="Collect evidence",
            due_date=datetime(2025, 2, 10, tzinfo=UTC),
            status="open",
            assigned_user_id=uuid4(),
            created_by_user_id=uuid4(),
            created_at=datetime(2025, 2, 1, tzinfo=UTC),
            updated_at=datetime(2025, 2, 1, tzinfo=UTC),
        )

    def update_case_status(
        self,
        *,
        case_id,
        new_status,
        reason,
        updated_by_user_id=None,
        updated_by_name=None,
        updated_by_role=None,
    ):
        self.case.status = new_status
        return self.case

    def manage_next_action(
        self,
        *,
        operation,
        case_id=None,
        action_id=None,
        fields=None,
        created_by_user_id=None,
    ):
        if operation == "create":
            self.action.id = uuid4()
            return self.action
        if operation == "update":
            self.action.description = fields.get("description", self.action.description)
            return self.action
        if operation == "complete":
            self.action.status = "completed"
            return self.action
        raise AssertionError(f"Unsupported operation: {operation}")

    def add_case_note(self, *, case_id, note_text, created_by_user_id=None):
        return CaseEvent(
            id=uuid4(),
            case_id=case_id,
            event_type="note",
            event_description=note_text,
            created_by_user_id=created_by_user_id,
            created_by_system=None,
            source_record_id=None,
            created_at=datetime(2025, 2, 1, tzinfo=UTC),
        )


def test_natwest_roles_and_permissions_are_configured() -> None:
    assert {role.value for role in AppRole} == {
        "customer_support",
        "fraud_investigator",
        "case_manager",
    }
    assert READ_ROLES == {
        AppRole.CUSTOMER_SUPPORT,
        AppRole.FRAUD_INVESTIGATOR,
        AppRole.CASE_MANAGER,
    }
    assert WRITE_ROLES == {
        AppRole.FRAUD_INVESTIGATOR,
        AppRole.CASE_MANAGER,
    }
    assert ADMIN_ROLES == {AppRole.CASE_MANAGER}
    assert "assigned_user_id" in Case.__table__.columns


def test_business_service_list_cases_filters_support_visibility() -> None:
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, FakeReadRepository()),
        write_repository=cast(BusinessWriteRepository, FakeWriteRepository()),
        auth_context=AuthContext(
            app_user_id=str(uuid4()),
            username="support_user",
            role=AppRole.CUSTOMER_SUPPORT,
        ),
    )

    cases = service.list_cases(status="open")

    assert len(cases) == 1
    assert cases[0].case_ref == "CS-018"


def test_case_status_enum_matches_natwest_case_workflow() -> None:
    assert {status.value for status in CaseStatusEnum} == {
        "open",
        "under_investigation",
        "pending_customer",
        "escalated",
        "resolved",
        "closed",
    }


def test_business_service_update_case_status_creates_status_change_event() -> None:
    read_repo = FakeReadRepository()
    write_repo = FakeWriteRepository()
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, read_repo),
        write_repository=cast(BusinessWriteRepository, write_repo),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="fraud", role=AppRole.FRAUD_INVESTIGATOR
        ),
    )

    updated = service.update_case_status(
        case_id=write_repo.case.id,
        new_status=CaseStatusEnum.UNDER_INVESTIGATION,
        reason="Escalated for deeper review",
    )

    assert updated is not None
    assert updated.status == CaseStatusEnum.UNDER_INVESTIGATION.value


def test_business_service_manage_next_action_supports_create_update_and_complete() -> (
    None
):
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, FakeReadRepository()),
        write_repository=cast(BusinessWriteRepository, FakeWriteRepository()),
        auth_context=AuthContext(
            app_user_id=str(uuid4()),
            username="case_manager",
            role=AppRole.CASE_MANAGER,
        ),
    )

    created = service.manage_next_action(
        operation="create",
        case_id=uuid4(),
        fields={
            "action_type": NextActionTypeEnum.REQUEST_DOCUMENTS,
            "description": "Request recent bank statements",
            "due_date": datetime(2025, 2, 12, tzinfo=UTC),
        },
    )
    updated = service.manage_next_action(
        operation="update",
        action_id=uuid4(),
        fields={"description": "Follow up with customer"},
    )
    completed = service.manage_next_action(
        operation="complete",
        action_id=uuid4(),
        fields={},
    )

    assert created is not None
    assert updated is not None
    assert completed is not None


def test_fraud_investigator_can_update_status_on_any_case_type() -> None:
    read_repo = FakeReadRepository()
    write_repo = FakeWriteRepository()
    write_repo.case.case_type = "complaint"
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, read_repo),
        write_repository=cast(BusinessWriteRepository, write_repo),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="fraud", role=AppRole.FRAUD_INVESTIGATOR
        ),
    )

    updated = service.update_case_status(
        case_id=write_repo.case.id,
        new_status=CaseStatusEnum.ESCALATED,
        reason="Consumer Duty review required",
    )

    assert updated is not None
    assert updated.status == CaseStatusEnum.ESCALATED.value


def test_fraud_investigator_blocked_from_terminal_status() -> None:
    read_repo = FakeReadRepository()
    write_repo = FakeWriteRepository()
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, read_repo),
        write_repository=cast(BusinessWriteRepository, write_repo),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="fraud", role=AppRole.FRAUD_INVESTIGATOR
        ),
    )

    with pytest.raises(PermissionDenied, match="Only case_manager can set status"):
        service.update_case_status(
            case_id=write_repo.case.id,
            new_status=CaseStatusEnum.RESOLVED,
            reason="Case complete",
        )


def test_case_manager_can_set_terminal_status() -> None:
    read_repo = FakeReadRepository()
    write_repo = FakeWriteRepository()
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, read_repo),
        write_repository=cast(BusinessWriteRepository, write_repo),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="manager", role=AppRole.CASE_MANAGER
        ),
    )

    updated = service.update_case_status(
        case_id=write_repo.case.id,
        new_status=CaseStatusEnum.CLOSED,
        reason="Resolved and closed",
    )

    assert updated is not None
    assert updated.status == CaseStatusEnum.CLOSED.value


def test_customer_support_blocked_from_update_case_status() -> None:
    read_repo = FakeReadRepository()
    write_repo = FakeWriteRepository()
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, read_repo),
        write_repository=cast(BusinessWriteRepository, write_repo),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="support", role=AppRole.CUSTOMER_SUPPORT
        ),
    )

    with pytest.raises(
        PermissionDenied, match="Customer support cannot update case status"
    ):
        service.update_case_status(
            case_id=write_repo.case.id,
            new_status=CaseStatusEnum.UNDER_INVESTIGATION,
            reason="Attempted update",
        )


def test_customer_support_blocked_from_manage_next_action() -> None:
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, FakeReadRepository()),
        write_repository=cast(BusinessWriteRepository, FakeWriteRepository()),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="support", role=AppRole.CUSTOMER_SUPPORT
        ),
    )

    with pytest.raises(
        PermissionDenied, match="Customer support cannot create or manage next actions"
    ):
        service.manage_next_action(operation="complete", action_id=uuid4(), fields={})


def test_fraud_investigator_blocked_from_manage_next_action() -> None:
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, FakeReadRepository()),
        write_repository=cast(BusinessWriteRepository, FakeWriteRepository()),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="fraud", role=AppRole.FRAUD_INVESTIGATOR
        ),
    )

    with pytest.raises(
        PermissionDenied,
        match="Fraud investigators cannot create or manage next actions",
    ):
        service.manage_next_action(operation="complete", action_id=uuid4(), fields={})


@pytest.mark.parametrize(
    "role",
    [AppRole.CUSTOMER_SUPPORT, AppRole.FRAUD_INVESTIGATOR, AppRole.CASE_MANAGER],
)
def test_add_case_note_available_to_every_role(role: AppRole) -> None:
    read_repo = FakeReadRepository()
    write_repo = FakeWriteRepository()
    service = BusinessService(
        read_repository=cast(BusinessReadRepository, read_repo),
        write_repository=cast(BusinessWriteRepository, write_repo),
        auth_context=AuthContext(app_user_id=str(uuid4()), username="user", role=role),
    )

    event = service.add_case_note(
        case_id=read_repo.case.id, note_text="Called customer"
    )

    assert event is not None
    assert event.event_type == "note"
    assert event.event_description == "Called customer"


def test_add_case_note_returns_none_for_missing_case() -> None:
    class EmptyReadRepository(FakeReadRepository):
        def get_case_details(self, *, case_id=None, case_ref=None):
            return None

    service = BusinessService(
        read_repository=cast(BusinessReadRepository, EmptyReadRepository()),
        write_repository=cast(BusinessWriteRepository, FakeWriteRepository()),
        auth_context=AuthContext(
            app_user_id=str(uuid4()), username="support", role=AppRole.CUSTOMER_SUPPORT
        ),
    )

    assert service.add_case_note(case_id=uuid4(), note_text="Note") is None
