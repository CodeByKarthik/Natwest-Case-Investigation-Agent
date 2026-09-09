from typing import Annotated, cast
from uuid import UUID

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from natwest_shared.common.exceptions import PermissionDenied
from natwest_shared.schema.business_schema import (
    AccountRead,
    AppUserRead,
    CaseEventRead,
    CaseRead,
    CustomerRead,
    NextActionRead,
)
from natwest_shared.services.business_service import BusinessService
from pydantic import Field

from natwest_mcp.mcp.dependencies import get_business_service


def _raise_as_tool_error(exc: Exception) -> None:
    raise ToolError(str(exc)) from exc


async def list_customers(
    is_flagged: Annotated[
        bool | None,
        Field(description="Filter for customers with an active vulnerability signal"),
    ] = None,
    kyc_status: Annotated[
        str | None,
        Field(description="Filter: verified, pending_review, expired, not_started"),
    ] = None,
    tier: Annotated[
        str | None, Field(description="Filter: standard, premium, private_banking")
    ] = None,
    name_contains: Annotated[
        str | None,
        Field(description="Case-insensitive partial match on customer full name"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    *,
    service: BusinessService = Depends(get_business_service),
) -> list[CustomerRead]:
    """Browse customers when you don't have a customer_id. Supports filters
    for vulnerability flag, KYC status, tier, and partial name match."""
    business_service = cast(BusinessService, service)
    try:
        customers = business_service.list_customers(
            is_flagged=is_flagged,
            kyc_status=kyc_status,
            tier=tier,
            name_contains=name_contains,
            limit=limit,
            offset=offset,
        )
    except (ValueError, PermissionDenied) as exc:
        _raise_as_tool_error(exc)
    return [CustomerRead.from_customer(customer) for customer in customers]


async def list_staff_users(
    name_contains: Annotated[
        str | None,
        Field(
            description="Case-insensitive partial match on staff full name or username"
        ),
    ] = None,
    role: Annotated[
        str | None,
        Field(description="Filter: customer_support, fraud_investigator, case_manager"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    *,
    service: BusinessService = Depends(get_business_service),
) -> list[AppUserRead]:
    """Resolve a colleague or role to a user_id — e.g. "fraud investigator"
    or a name like "Alex" — for use as assigned_user_id in list_cases.
    Never ask the user for a raw UUID; look it up here first."""
    business_service = cast(BusinessService, service)
    try:
        staff = business_service.list_staff_users(
            name_contains=name_contains, role=role, limit=limit, offset=offset
        )
    except (ValueError, PermissionDenied) as exc:
        _raise_as_tool_error(exc)
    return [AppUserRead.from_user(user) for user in staff]


async def list_cases(
    status: Annotated[
        str | None,
        Field(
            description="Filter: open, under_investigation, pending_customer, "
            "escalated, resolved, closed"
        ),
    ] = None,
    priority: Annotated[str | None, Field(description="Filter: p1, p2, p3, p4")] = None,
    case_type: Annotated[
        str | None, Field(description="Filter: fraud, dispute, complaint")
    ] = None,
    customer_id: Annotated[
        UUID | None, Field(description="Filter by specific customer")
    ] = None,
    assigned_user_id: Annotated[
        UUID | None, Field(description="Filter by the staff member handling the case")
    ] = None,
    consumer_duty_flag: Annotated[
        bool | None, Field(description="Filter for Consumer Duty flagged cases")
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    *,
    service: BusinessService = Depends(get_business_service),
) -> list[CaseRead]:
    """Discovery tool. Find NatWest investigation cases matching filters, e.g.
    "show me open P1 cases" or "which cases have Consumer Duty flagged?"."""
    business_service = cast(BusinessService, service)
    try:
        cases = business_service.list_cases(
            status=status,
            priority=priority,
            case_type=case_type,
            customer_id=customer_id,
            assigned_user_id=assigned_user_id,
            consumer_duty_flag=consumer_duty_flag,
            limit=limit,
            offset=offset,
        )
    except (ValueError, PermissionDenied) as exc:
        _raise_as_tool_error(exc)
    return [CaseRead.model_validate(case) for case in cases]


async def get_customer_profile(
    customer_id: UUID,
    *,
    service: BusinessService = Depends(get_business_service),
) -> CustomerRead | None:
    """Get full customer detail including the vulnerability register — both
    active and resolved signals, with the source system records that
    generated them nested inline."""
    business_service = cast(BusinessService, service)
    try:
        customer = business_service.get_customer_profile(customer_id=customer_id)
    except PermissionDenied as exc:
        _raise_as_tool_error(exc)
    return None if customer is None else CustomerRead.from_customer(customer)


async def get_customer_accounts(
    customer_id: UUID,
    *,
    service: BusinessService = Depends(get_business_service),
) -> list[AccountRead]:
    """List all accounts held by a customer."""
    business_service = cast(BusinessService, service)
    try:
        accounts = business_service.get_customer_accounts(customer_id=customer_id)
    except PermissionDenied as exc:
        _raise_as_tool_error(exc)
    return [AccountRead.model_validate(account) for account in accounts]


async def get_case_details(
    case_id: UUID | None = None,
    case_ref: Annotated[
        str | None, Field(description='Human-readable case reference, e.g. "CS-018"')
    ] = None,
    *,
    service: BusinessService = Depends(get_business_service),
) -> CaseRead | None:
    """Get full detail on one specific case by UUID or human-readable
    case_ref. Exactly one of case_id or case_ref must be provided."""
    business_service = cast(BusinessService, service)
    if case_id is None and case_ref is None:
        raise ToolError("Either case_id or case_ref must be provided")
    try:
        case = business_service.get_case_details(case_id=case_id, case_ref=case_ref)
    except PermissionDenied as exc:
        _raise_as_tool_error(exc)
    return None if case is None else CaseRead.model_validate(case)


async def get_case_timeline(
    case_id: UUID,
    *,
    service: BusinessService = Depends(get_business_service),
) -> list[CaseEventRead]:
    """Get the chronological event history for a case. System-generated events
    include the full source system record (rules fired, confidence score,
    payload) nested inline."""
    business_service = cast(BusinessService, service)
    try:
        timeline = business_service.get_case_timeline(case_id=case_id)
    except PermissionDenied as exc:
        _raise_as_tool_error(exc)
    return [CaseEventRead.model_validate(entry) for entry in timeline]


async def get_next_actions(
    case_id: UUID,
    *,
    service: BusinessService = Depends(get_business_service),
) -> list[NextActionRead]:
    """Get outstanding follow-up tasks on a case. Each action includes a
    computed is_overdue flag (status open and due_date in the past)."""
    business_service = cast(BusinessService, service)
    try:
        actions = business_service.get_next_actions(case_id=case_id)
    except PermissionDenied as exc:
        _raise_as_tool_error(exc)
    return [NextActionRead.model_validate(action) for action in actions]


async def update_case_status(
    case_id: UUID,
    new_status: Annotated[
        str,
        Field(
            description="One of: open, under_investigation, pending_customer, "
            "escalated, resolved, closed"
        ),
    ],
    reason: Annotated[
        str, Field(description="Short explanation recorded in the case timeline")
    ],
    *,
    service: BusinessService = Depends(get_business_service),
) -> CaseRead:
    """Update a case's lifecycle status. Write operation — requires
    fraud_investigator (fraud/dispute cases) or case_manager (all cases).
    Automatically appends a status_change event to the case timeline."""
    business_service = cast(BusinessService, service)
    try:
        case = business_service.update_case_status(
            case_id=case_id, new_status=new_status, reason=reason
        )
    except (ValueError, PermissionDenied) as exc:
        _raise_as_tool_error(exc)
    if case is None:
        raise ToolError("Case not found")
    return CaseRead.model_validate(case)


async def manage_next_action(
    operation: Annotated[str, Field(description="One of: create, update, complete")],
    case_id: Annotated[
        UUID | None,
        Field(description="Required for create, ignored for update/complete"),
    ] = None,
    action_id: Annotated[
        UUID | None,
        Field(description="Required for update and complete, ignored for create"),
    ] = None,
    fields: Annotated[
        dict[str, object] | None,
        Field(
            description="create requires action_type, description, due_date "
            "(assigned_user_id optional). update accepts action_type, "
            "description, due_date, status, assigned_user_id. "
            "Ignored for complete."
        ),
    ] = None,
    *,
    service: BusinessService = Depends(get_business_service),
) -> NextActionRead | None:
    """Create, update, or complete a next action on a case. Write operation —
    requires the case_manager role."""
    business_service = cast(BusinessService, service)
    try:
        action = business_service.manage_next_action(
            operation=operation, case_id=case_id, action_id=action_id, fields=fields
        )
    except (ValueError, PermissionDenied) as exc:
        _raise_as_tool_error(exc)
    if action is None:
        raise ToolError("Next action not found")
    return NextActionRead.model_validate(action)


async def add_case_note(
    case_id: UUID,
    note_text: Annotated[
        str,
        Field(
            description="Free-text note to append to the case timeline",
            min_length=1,
            max_length=8000,
        ),
    ],
    *,
    service: BusinessService = Depends(get_business_service),
) -> CaseEventRead:
    """Append a free-text note to a case's timeline. Write operation —
    available to every role (customer_support, fraud_investigator,
    case_manager) with no RBAC restriction, since notes are audit-trail
    additions rather than case management decisions."""
    business_service = cast(BusinessService, service)
    try:
        event = business_service.add_case_note(
            case_id=case_id, note_text=note_text.strip()
        )
    except (ValueError, PermissionDenied) as exc:
        _raise_as_tool_error(exc)
    if event is None:
        raise ToolError("Case not found")
    return CaseEventRead.model_validate(event)
