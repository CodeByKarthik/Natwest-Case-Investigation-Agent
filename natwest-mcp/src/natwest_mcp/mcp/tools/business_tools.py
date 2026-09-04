from typing import Annotated
from uuid import UUID

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from natwest_shared.schema.business_schema import (
    AccountRead,
    CaseEventRead,
    CaseRead,
    CustomerRead,
    NextActionRead,
)
from natwest_shared.services.business_service import BusinessService
from pydantic import Field

from natwest_mcp.mcp.dependencies import get_business_service


async def get_customer_profile(
    customer_id: UUID,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> CustomerRead | None:
    """Fetch the full customer profile for a customer identifier."""
    customer = service.get_customer_profile(customer_id=customer_id)
    return None if customer is None else CustomerRead.model_validate(customer)


async def get_customer_accounts(
    customer_id: UUID,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> list[AccountRead]:
    """List all accounts held by a customer."""
    accounts = service.get_customer_accounts(customer_id=customer_id)
    return [AccountRead.model_validate(account) for account in accounts]


async def list_cases(
    status: str | None = None,
    priority: str | None = None,
    assigned_team: str | None = None,
    assigned_user_id: UUID | None = None,
    case_type: str | None = None,
    customer_id: UUID | None = None,
    consumer_duty_flag: bool | None = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> list[CaseRead]:
    """List NatWest investigation cases matching the provided filters."""
    cases = service.list_cases(
        status=status,
        priority=priority,
        assigned_team=assigned_team,
        assigned_user_id=assigned_user_id,
        case_type=case_type,
        customer_id=customer_id,
        consumer_duty_flag=consumer_duty_flag,
        limit=limit,
        offset=offset,
    )
    return [CaseRead.model_validate(case) for case in cases]


async def get_case_details(
    case_id: UUID | None = None,
    case_ref: str | None = None,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> CaseRead | None:
    """Load the full details for a single case by ID or case reference."""
    if case_id is None and case_ref is None:
        raise ToolError("Either case_id or case_ref must be provided")
    case = service.get_case_details(case_id=case_id, case_ref=case_ref)
    return None if case is None else CaseRead.model_validate(case)


async def get_case_timeline(
    case_id: UUID,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> list[CaseEventRead]:
    """Retrieve the timeline for a case."""
    timeline = service.get_case_timeline(case_id=case_id)
    return [CaseEventRead.model_validate(entry) for entry in timeline]


async def get_next_actions(
    case_id: UUID,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> list[NextActionRead]:
    """Fetch the next actions associated with a case."""
    actions = service.get_next_actions(case_id=case_id)
    return [NextActionRead.model_validate(action) for action in actions]


async def update_case_status(
    case_id: UUID,
    new_status: str,
    reason: str,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> CaseRead:
    """Update the lifecycle status of a case."""
    case = service.update_case_status(
        case_id=case_id, new_status=new_status, reason=reason
    )
    if case is None:
        raise ToolError("Case not found")
    return CaseRead.model_validate(case)


async def manage_next_action(
    operation: str,
    case_id: UUID | None = None,
    action_id: UUID | None = None,
    fields: dict[str, object] | None = None,
    *,
    service: Annotated[BusinessService, Depends(get_business_service)],
) -> NextActionRead | None:
    """Create, update, or complete a case next action."""
    action = service.manage_next_action(
        operation=operation, case_id=case_id, action_id=action_id, fields=fields
    )
    return None if action is None else NextActionRead.model_validate(action)
