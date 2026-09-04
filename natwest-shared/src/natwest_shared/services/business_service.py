from datetime import datetime
from uuid import UUID

from natwest_shared.auth.rbac import ADMIN_ROLES, READ_ROLES, WRITE_ROLES, require_role
from natwest_shared.common.enums import AppRole, CaseStatusEnum
from natwest_shared.common.exceptions import PermissionDenied
from natwest_shared.db.models.business import (
    Account,
    Case,
    CaseEvent,
    Customer,
    NextAction,
)
from natwest_shared.db.repositories.business_read_repository import (
    BusinessReadRepository,
)
from natwest_shared.db.repositories.business_write_repository import (
    BusinessWriteRepository,
)
from natwest_shared.schema.auth_schema import AuthContext


class BusinessService:
    """Permission-aware service for NatWest customer and case operations."""

    def __init__(
        self,
        *,
        read_repository: BusinessReadRepository,
        write_repository: BusinessWriteRepository,
        auth_context: AuthContext,
    ) -> None:
        self.read_repository = read_repository
        self.write_repository = write_repository
        self.auth_context = auth_context

    def list_customers(self, *, limit: int = 50, offset: int = 0) -> list[Customer]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.list_customers(limit=limit, offset=offset)

    def get_customer_by_name(self, *, name: str) -> Customer | None:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_customer_by_name(name=name)

    def get_customer_profile(self, *, customer_id: UUID) -> Customer | None:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_customer_profile(customer_id=customer_id)

    def get_customer_accounts(self, *, customer_id: UUID) -> list[Account]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_customer_accounts(customer_id=customer_id)

    def list_cases(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        assigned_team: str | None = None,
        assigned_user_id: UUID | None = None,
        case_type: str | None = None,
        customer_id: UUID | None = None,
        consumer_duty_flag: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Case]:
        require_role(self.auth_context, READ_ROLES)
        filters: dict[str, object] = {}

        if status is not None:
            filters["status"] = status
        if priority is not None:
            filters["priority"] = priority
        if assigned_team is not None:
            filters["assigned_team"] = assigned_team
        if assigned_user_id is not None:
            filters["assigned_user_id"] = assigned_user_id
        if case_type is not None:
            filters["case_type"] = case_type
        if customer_id is not None:
            filters["customer_id"] = customer_id
        if consumer_duty_flag is not None:
            filters["consumer_duty_flag"] = consumer_duty_flag

        if self.auth_context.role == AppRole.CUSTOMER_SUPPORT:
            filters["assigned_team"] = "customer_support"

        return self.read_repository.list_cases(
            filters=filters, limit=limit, offset=offset
        )

    def get_case_details(
        self, *, case_id: UUID | None = None, case_ref: str | None = None
    ) -> Case | None:
        require_role(self.auth_context, READ_ROLES)
        case = self.read_repository.get_case_details(case_id=case_id, case_ref=case_ref)
        if case is None:
            return None
        if (
            self.auth_context.role == AppRole.CUSTOMER_SUPPORT
            and case.assigned_team != "customer_support"
        ):
            raise PermissionDenied("Customer support users cannot access this case")
        return case

    def get_case_timeline(self, *, case_id: UUID) -> list[CaseEvent]:
        require_role(self.auth_context, READ_ROLES)
        timeline = self.read_repository.get_case_timeline(case_id=case_id)
        if self.auth_context.role == AppRole.CUSTOMER_SUPPORT:
            return [event for event in timeline if not event.is_internal]
        return timeline

    def get_next_actions(self, *, case_id: UUID) -> list[NextAction]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_next_actions(case_id=case_id)

    def list_open_issues(
        self, *, customer_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Case]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.list_open_issues(
            customer_id=customer_id, limit=limit, offset=offset
        )

    def get_issue_by_external_ref(self, *, external_ref: str) -> Case | None:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_issue_by_external_ref(external_ref=external_ref)

    def list_issue_updates(
        self,
        *,
        issue_id: UUID,
        customer_visible_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CaseEvent]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.list_issue_updates(
            issue_id=issue_id,
            customer_visible_only=customer_visible_only,
            limit=limit,
            offset=offset,
        )

    def list_next_actions(
        self,
        *,
        issue_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NextAction]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.list_next_actions(
            issue_id=issue_id, status=status, limit=limit, offset=offset
        )

    def update_case_status(
        self, *, case_id: UUID, new_status: str | CaseStatusEnum, reason: str
    ) -> Case | None:
        require_role(self.auth_context, WRITE_ROLES)

        case = self.read_repository.get_case_details(case_id=case_id)
        if case is None:
            return None

        if (
            self.auth_context.role == AppRole.FRAUD_INVESTIGATOR
            and case.case_type not in {"fraud", "dispute"}
        ):
            raise PermissionDenied(
                "Fraud investigators may only update fraud and dispute cases"
            )
        if self.auth_context.role == AppRole.CUSTOMER_SUPPORT:
            raise PermissionDenied("Customer support users cannot update case status")

        new_status_value = (
            new_status.value if isinstance(new_status, CaseStatusEnum) else new_status
        )
        return self.write_repository.update_case_status(
            case_id=case_id,
            new_status=new_status_value,
            reason=reason,
            updated_by_user_id=UUID(self.auth_context.app_user_id),
            updated_by_name=self.auth_context.username,
            updated_by_role=self.auth_context.role.value,
        )

    def update_issue_status(
        self, *, issue_id: UUID, status: str | CaseStatusEnum
    ) -> Case | None:
        return self.update_case_status(
            case_id=issue_id, new_status=status, reason="Status updated"
        )

    def add_issue_update(
        self, *, issue_id: UUID, update_text: str, is_customer_visible: bool = True
    ) -> CaseEvent:
        require_role(self.auth_context, WRITE_ROLES)
        return self.write_repository.add_issue_update(
            issue_id=issue_id,
            author_user_id=UUID(self.auth_context.app_user_id),
            author_name=self.auth_context.username,
            author_role=self.auth_context.role.value,
            update_text=update_text,
            is_customer_visible=is_customer_visible,
        )

    def manage_next_action(
        self,
        *,
        operation: str,
        case_id: UUID | None = None,
        action_id: UUID | None = None,
        fields: dict[str, object] | None = None,
    ) -> NextAction | None:
        require_role(self.auth_context, ADMIN_ROLES)
        fields = fields or {}
        if operation == "create":
            if case_id is None:
                return None
            fields.setdefault("created_by_user_id", UUID(self.auth_context.app_user_id))
            fields.setdefault("created_by_role", self.auth_context.role.value)
            return self.write_repository.manage_next_action(
                operation="create", case_id=case_id, fields=fields
            )
        if operation in {"update", "complete"}:
            if action_id is None:
                return None
            return self.write_repository.manage_next_action(
                operation=operation, action_id=action_id, fields=fields
            )
        return None

    def create_next_action(
        self,
        *,
        issue_id: UUID,
        action_type: str,
        action_text: str,
        owner_user_id: UUID | None = None,
        due_at: datetime | None = None,
    ) -> NextAction:
        require_role(self.auth_context, ADMIN_ROLES)
        return self.write_repository.create_next_action(
            issue_id=issue_id,
            action_type=action_type,
            action_text=action_text,
            owner_user_id=owner_user_id,
            due_at=due_at,
            created_by_user_id=UUID(self.auth_context.app_user_id),
            created_by_role=self.auth_context.role.value,
        )

    def update_next_action(
        self,
        *,
        next_action_id: UUID,
        action_type: str | None = None,
        action_text: str | None = None,
        owner_user_id: UUID | None = None,
        due_at: datetime | None = None,
        status: str | None = None,
    ) -> NextAction | None:
        require_role(self.auth_context, ADMIN_ROLES)
        return self.write_repository.update_next_action(
            next_action_id=next_action_id,
            action_type=action_type,
            action_text=action_text,
            owner_user_id=owner_user_id,
            due_at=due_at,
            status=status,
        )

    def complete_next_action(self, *, next_action_id: UUID) -> NextAction | None:
        require_role(self.auth_context, ADMIN_ROLES)
        return self.write_repository.complete_next_action(next_action_id=next_action_id)
