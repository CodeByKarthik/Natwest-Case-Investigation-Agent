from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class CustomerRead(BaseModel):
    """Read model for a NatWest customer profile."""

    id: UUID
    full_name: str
    date_of_birth: date
    primary_account_number: str
    primary_sort_code: str
    kyc_status: str
    kyc_last_reviewed: datetime | None = None
    vulnerability_flag: bool
    vulnerability_type: str | None = None
    vulnerability_notes: str | None = None
    customer_since: date
    tier: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountRead(BaseModel):
    """Read model for a NatWest customer account."""

    id: UUID
    customer_id: UUID
    account_number: str
    sort_code: str
    account_type: str
    balance: str | None = None
    status: str
    opened_date: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("balance", mode="before")
    @classmethod
    def stringify_balance(cls, value: Decimal | str | None) -> str | None:
        if value is None:
            return None
        return str(value)


class CaseRead(BaseModel):
    """Read model for a NatWest case."""

    id: UUID
    customer_id: UUID
    case_ref: str
    case_type: str
    status: str
    priority: str
    opened_date: datetime
    last_updated: datetime
    assigned_team: str
    assigned_user_id: UUID | None = None
    disputed_amount: str | None = None
    merchant_name: str | None = None
    merchant_category: str | None = None
    consumer_duty_flag: bool
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("disputed_amount", mode="before")
    @classmethod
    def stringify_disputed_amount(cls, value: Decimal | str | None) -> str | None:
        if value is None:
            return None
        return str(value)


class CaseEventRead(BaseModel):
    """Read model for a NatWest case event or timeline entry."""

    id: UUID
    case_id: UUID
    event_type: str
    event_description: str
    is_internal: bool
    created_by_user_id: UUID | None = None
    created_by_name: str | None = None
    created_by_role: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NextActionRead(BaseModel):
    """Read model for a natural next action on a case."""

    id: UUID
    case_id: UUID
    action_type: str
    description: str
    due_date: datetime
    status: str
    assigned_user_id: UUID | None = None
    created_by_user_id: UUID | None = None
    created_by_role: str | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
