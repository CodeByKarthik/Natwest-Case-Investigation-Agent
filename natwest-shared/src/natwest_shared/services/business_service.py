from uuid import UUID

from natwest_shared.auth.rbac import (
    ADMIN_ROLES,
    READ_ROLES,
    TERMINAL_CASE_STATUSES,
    WRITE_ROLES,
    require_role,
)
from natwest_shared.common.enums import (
    AppRole,
    CaseStatusEnum,
    CaseTypeEnum,
    KycStatusEnum,
    NextActionStatusEnum,
    NextActionTypeEnum,
    TierEnum,
)
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

_VALID_OPERATIONS = {"create", "update", "complete"}


class BusinessService:
    """Permission-aware service for NatWest customer and case operations.

    Authorization model: every role can read; write actions depend on role.
    """

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

    # ----- Reads (all roles) -----

    def list_customers(
        self,
        *,
        is_flagged: bool | None = None,
        kyc_status: str | None = None,
        tier: str | None = None,
        name_contains: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Customer]:
        require_role(self.auth_context, READ_ROLES)

        if kyc_status is not None and kyc_status not in set(KycStatusEnum):
            raise ValueError(f"Invalid KYC status filter: {kyc_status}")
        if tier is not None and tier not in set(TierEnum):
            raise ValueError(f"Invalid customer tier filter: {tier}")

        return self.read_repository.list_customers(
            is_flagged=is_flagged,
            kyc_status=kyc_status,
            tier=tier,
            name_contains=name_contains,
            limit=limit,
            offset=offset,
        )

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
        case_type: str | None = None,
        customer_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
        consumer_duty_flag: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Case]:
        require_role(self.auth_context, READ_ROLES)

        if status is not None and status not in set(CaseStatusEnum):
            raise ValueError(f"Invalid case status filter: {status}")
        if case_type is not None and case_type not in set(CaseTypeEnum):
            raise ValueError(f"Invalid case type filter: {case_type}")

        filters: dict[str, object] = {}
        if status is not None:
            filters["status"] = status
        if priority is not None:
            filters["priority"] = priority
        if case_type is not None:
            filters["case_type"] = case_type
        if customer_id is not None:
            filters["customer_id"] = customer_id
        if assigned_user_id is not None:
            filters["assigned_user_id"] = assigned_user_id
        if consumer_duty_flag is not None:
            filters["consumer_duty_flag"] = consumer_duty_flag

        return self.read_repository.list_cases(
            filters=filters, limit=limit, offset=offset
        )

    def get_case_details(
        self, *, case_id: UUID | None = None, case_ref: str | None = None
    ) -> Case | None:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_case_details(case_id=case_id, case_ref=case_ref)

    def get_case_timeline(self, *, case_id: UUID) -> list[CaseEvent]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_case_timeline(case_id=case_id)

    def get_next_actions(self, *, case_id: UUID) -> list[NextAction]:
        require_role(self.auth_context, READ_ROLES)
        return self.read_repository.get_next_actions(case_id=case_id)

    # ----- Writes (role-dependent) -----

    def update_case_status(
        self, *, case_id: UUID, new_status: str | CaseStatusEnum, reason: str
    ) -> Case | None:
        """Update a case status. fraud_investigator can set any status
        except the terminal ones (resolved, closed), which require
        case_manager. customer_support cannot update case status at all."""
        if self.auth_context.role not in WRITE_ROLES:
            raise PermissionDenied(
                "Customer support cannot update case status. Case status "
                "changes require fraud_investigator (for active investigation "
                "states) or case_manager (for closure or resolution)."
            )

        new_status_value = (
            new_status.value if isinstance(new_status, CaseStatusEnum) else new_status
        )
        if new_status_value not in set(CaseStatusEnum):
            raise ValueError(f"Invalid case status: {new_status_value}")

        case = self.read_repository.get_case_details(case_id=case_id)
        if case is None:
            return None

        if (
            self.auth_context.role == AppRole.FRAUD_INVESTIGATOR
            and new_status_value in TERMINAL_CASE_STATUSES
        ):
            raise PermissionDenied(
                f"Only case_manager can set status to '{new_status_value}'. "
                "Fraud investigators can update status to open, "
                "under_investigation, pending_customer, or escalated. Final "
                "resolution or closure requires case_manager approval."
            )

        return self.write_repository.update_case_status(
            case_id=case_id,
            new_status=new_status_value,
            reason=reason,
            updated_by_user_id=UUID(self.auth_context.app_user_id),
        )

    def manage_next_action(
        self,
        *,
        operation: str,
        case_id: UUID | None = None,
        action_id: UUID | None = None,
        fields: dict[str, object] | None = None,
    ) -> NextAction | None:
        """Create, update, or complete a next action. Case managers only."""
        if self.auth_context.role not in ADMIN_ROLES:
            if self.auth_context.role == AppRole.FRAUD_INVESTIGATOR:
                raise PermissionDenied(
                    "Fraud investigators cannot create or manage next actions. "
                    "Assigning follow-up work is a case management function — "
                    "only case_manager can create, update, or complete next "
                    "actions."
                )
            raise PermissionDenied(
                "Customer support cannot create or manage next actions. Next "
                "actions require case_manager permissions. You can still add "
                "notes to the case for audit purposes using add_case_note."
            )

        if operation not in _VALID_OPERATIONS:
            raise ValueError(
                f"Invalid operation: {operation}. "
                "Must be one of: create, update, complete"
            )

        fields = dict(fields or {})

        if operation == "create":
            if case_id is None:
                raise ValueError("case_id is required for operation=create")
            for required_field in ("action_type", "description", "due_date"):
                if required_field not in fields:
                    raise ValueError(
                        f"fields.{required_field} is required for operation=create"
                    )
            action_type = fields.get("action_type")
            if action_type not in set(NextActionTypeEnum):
                raise ValueError(f"Invalid action_type: {action_type}")
            if self.read_repository.get_case_details(case_id=case_id) is None:
                return None

        if operation in {"update", "complete"} and action_id is None:
            raise ValueError(f"action_id is required for operation={operation}")

        if operation == "update":
            action_type = fields.get("action_type")
            if action_type is not None and action_type not in set(NextActionTypeEnum):
                raise ValueError(f"Invalid action_type: {action_type}")
            status = fields.get("status")
            if status is not None and status not in set(NextActionStatusEnum):
                raise ValueError(f"Invalid next action status: {status}")

        return self.write_repository.manage_next_action(
            operation=operation,
            case_id=case_id,
            action_id=action_id,
            fields=fields,
            created_by_user_id=UUID(self.auth_context.app_user_id),
        )

    def add_case_note(self, *, case_id: UUID, note_text: str) -> CaseEvent | None:
        """Append a free-text note to a case's timeline. Available to every
        role — notes are audit-trail additions, not case management
        decisions, so there is no RBAC restriction here."""
        if self.read_repository.get_case_details(case_id=case_id) is None:
            return None

        return self.write_repository.add_case_note(
            case_id=case_id,
            note_text=note_text,
            created_by_user_id=UUID(self.auth_context.app_user_id),
        )
