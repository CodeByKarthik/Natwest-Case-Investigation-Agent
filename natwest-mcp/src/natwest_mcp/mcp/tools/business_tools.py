from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from pydantic import Field

from natwest_mcp.mcp.dependencies import get_business_service
from natwest_shared.common.enums import (
    IssueStatusEnum,
    NextActionStatusEnum,
    NextActionTypeEnum,
)
from natwest_shared.schema.business_schema import (
    CustomerRead,
    IssueRead,
    IssueUpdateRead,
    NextActionRead,
)
from natwest_shared.services.business_service import BusinessService


async def list_customers(
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    service: BusinessService = Depends(get_business_service),
) -> list[CustomerRead]:
    """List customers visible to the authenticated user."""
    customers = service.list_customers(limit=limit, offset=offset)
    return [CustomerRead.model_validate(customer) for customer in customers]


async def get_customer_by_name(
    name: Annotated[str, Field(min_length=1, max_length=255)],
    service: BusinessService = Depends(get_business_service),
) -> CustomerRead | None:
    """Find a customer by partial name match."""
    customer = service.get_customer_by_name(name=name)

    if customer is None:
        return None

    return CustomerRead.model_validate(customer)


async def list_open_issues(
    customer_id: UUID,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    service: BusinessService = Depends(get_business_service),
) -> list[IssueRead]:
    """List open, in-progress, or blocked issues for a customer."""
    issues = service.list_open_issues(
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )

    return [IssueRead.model_validate(issue) for issue in issues]


async def get_issue_by_external_ref(
    external_ref: Annotated[str, Field(min_length=1, max_length=50)],
    service: BusinessService = Depends(get_business_service),
) -> IssueRead | None:
    """Find an issue by external reference such as ISSUE-101."""
    issue = service.get_issue_by_external_ref(
        external_ref=external_ref,
    )

    if issue is None:
        return None

    return IssueRead.model_validate(issue)


async def list_issue_updates(
    issue_id: UUID,
    customer_visible_only: bool = False,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    service: BusinessService = Depends(get_business_service),
) -> list[IssueUpdateRead]:
    """List updates for an issue, newest first."""
    updates = service.list_issue_updates(
        issue_id=issue_id,
        customer_visible_only=customer_visible_only,
        limit=limit,
        offset=offset,
    )

    return [IssueUpdateRead.model_validate(update) for update in updates]


async def list_next_actions(
    issue_id: UUID,
    status: NextActionStatusEnum | None = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    offset: Annotated[int, Field(ge=0)] = 0,
    service: BusinessService = Depends(get_business_service),
) -> list[NextActionRead]:
    """List next actions for an issue."""
    next_actions = service.list_next_actions(
        issue_id=issue_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [NextActionRead.model_validate(action) for action in next_actions]


async def update_issue_status(
    issue_id: UUID,
    status: IssueStatusEnum,
    service: BusinessService = Depends(get_business_service),
) -> IssueRead:
    """Update an issue status. Requires support_user or admin."""
    issue = service.update_issue_status(
        issue_id=issue_id,
        status=status,
    )

    if issue is None:
        raise ToolError("Issue not found")

    return IssueRead.model_validate(issue)


async def add_issue_update(
    issue_id: UUID,
    update_text: Annotated[str, Field(min_length=1, max_length=8000)],
    is_customer_visible: bool = True,
    service: BusinessService = Depends(get_business_service),
) -> IssueUpdateRead:
    """Add a progress update to an issue. Requires support_user or admin."""
    issue_update = service.add_issue_update(
        issue_id=issue_id,
        update_text=update_text,
        is_customer_visible=is_customer_visible,
    )

    return IssueUpdateRead.model_validate(issue_update)


async def create_next_action(
    issue_id: UUID,
    action_type: NextActionTypeEnum,
    action_text: Annotated[str, Field(min_length=1, max_length=8000)],
    owner_user_id: UUID | None = None,
    due_at: datetime | None = None,
    service: BusinessService = Depends(get_business_service),
) -> NextActionRead:
    """Create a next action for an issue. Requires admin."""
    next_action = service.create_next_action(
        issue_id=issue_id,
        action_type=action_type,
        action_text=action_text,
        owner_user_id=owner_user_id,
        due_at=due_at,
    )

    return NextActionRead.model_validate(next_action)


async def update_next_action(
    next_action_id: UUID,
    action_type: NextActionTypeEnum | None = None,
    action_text: Annotated[str | None, Field(max_length=8000)] = None,
    owner_user_id: UUID | None = None,
    due_at: datetime | None = None,
    status: NextActionStatusEnum | None = None,
    service: BusinessService = Depends(get_business_service),
) -> NextActionRead:
    """Update next action fields. Requires admin."""
    next_action = service.update_next_action(
        next_action_id=next_action_id,
        action_type=action_type,
        action_text=action_text,
        owner_user_id=owner_user_id,
        due_at=due_at,
        status=status,
    )

    if next_action is None:
        raise ToolError("Next action not found")

    return NextActionRead.model_validate(next_action)


async def complete_next_action(
    next_action_id: UUID,
    service: BusinessService = Depends(get_business_service),
) -> NextActionRead:
    """Mark a next action as completed. Requires admin."""
    next_action = service.complete_next_action(
        next_action_id=next_action_id,
    )

    if next_action is None:
        raise ToolError("Next action not found")

    return NextActionRead.model_validate(next_action)
