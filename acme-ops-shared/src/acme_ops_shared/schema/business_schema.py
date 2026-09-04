from datetime import datetime
from decimal import Decimal
from uuid import UUID

from acme_ops_shared.common.enums import (
    CustomerHealthEnum,
    CustomerTierEnum,
    IssuePriorityEnum,
    IssueStatusEnum,
    NextActionStatusEnum,
    NextActionTypeEnum,
)
from pydantic import BaseModel, Field, field_validator


class CustomerCreate(BaseModel):
    """
    Represents the data required to create a new customer
    in the system.
    """

    name: str = Field(min_length=1, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    tier: CustomerTierEnum
    account_owner_user_id: UUID | None = None
    contract_value: Decimal | None = None
    health_status: CustomerHealthEnum
    notes: str | None = None


class CustomerRead(BaseModel):
    """
    Represents the data of a customer as stored in the system,
    including metadata such as creation and update timestamps.
    """

    id: UUID
    name: str
    industry: str | None
    tier: CustomerTierEnum
    account_owner_user_id: UUID | None
    contract_value: str | None
    health_status: CustomerHealthEnum
    notes: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("contract_value", mode="before")
    @classmethod
    def convert_contract_value(cls, value: Decimal | str | None) -> str | None:
        """
        Serialize Decimal contract values as strings.
        """
        if value is None:
            return None

        return str(value)


class IssueCreate(BaseModel):
    """
    Represents the data required to create a new issue in
    the system.
    """

    customer_id: UUID
    external_ref: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: IssueStatusEnum
    priority: IssuePriorityEnum
    assigned_to_user_id: UUID | None = None
    source_system: str = Field(default="natwest-support", max_length=100)
    opened_at: datetime
    due_at: datetime | None = None


class IssueRead(BaseModel):
    """
    Represents the data of an issue as stored in the system.
    """

    id: UUID
    customer_id: UUID
    external_ref: str
    title: str
    description: str | None
    status: IssueStatusEnum
    priority: IssuePriorityEnum
    assigned_to_user_id: UUID | None
    source_system: str
    opened_at: datetime
    due_at: datetime | None
    resolved_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueUpdateCreate(BaseModel):
    """
    Represents the data required to create a new update for an
    issue in the system.
    """

    issue_id: UUID
    author_user_id: UUID | None = None
    author_name: str | None = Field(default=None, max_length=255)
    author_role: str | None = Field(default=None, max_length=50)
    update_text: str = Field(min_length=1)
    is_customer_visible: bool = True


class IssueUpdateRead(BaseModel):
    """
    Represents the data of an issue update as stored in the system.
    """

    id: UUID
    issue_id: UUID
    author_user_id: UUID | None
    author_name: str | None
    author_role: str | None
    update_text: str
    is_customer_visible: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NextActionCreate(BaseModel):
    """
    Represents the data required to create a new next action for an
    issue in the system.
    """

    issue_id: UUID
    action_type: NextActionTypeEnum
    action_text: str = Field(min_length=1)
    owner_user_id: UUID | None = None
    due_at: datetime | None = None
    created_by_user_id: UUID | None = None
    created_by_role: str | None = Field(default=None, max_length=50)


class NextActionRead(BaseModel):
    """
    Represents the data of a next action as stored in the system.
    """

    id: UUID
    issue_id: UUID
    action_type: NextActionTypeEnum
    action_text: str
    owner_user_id: UUID | None
    due_at: datetime | None
    status: NextActionStatusEnum
    created_by_user_id: UUID | None
    created_by_role: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
