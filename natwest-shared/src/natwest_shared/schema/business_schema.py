from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class SourceSystemRecordRead(BaseModel):
    """Read model for a raw source system record."""

    id: UUID
    source_system: str
    source_ref: str
    record_type: str
    confidence_score: str | None = None
    payload: dict[str, Any]
    generated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("confidence_score", mode="before")
    @classmethod
    def stringify_confidence(cls, value: Decimal | str | None) -> str | None:
        if value is None:
            return None
        return str(value)


class VulnerabilityRegisterRead(BaseModel):
    """Read model for one vulnerability register signal."""

    id: UUID
    vulnerability_type: str
    status: str
    notes: str | None = None
    source_record_id: UUID | None = None
    source_record: SourceSystemRecordRead | None = None
    detected_at: datetime
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerRead(BaseModel):
    """Read model for a NatWest customer profile including the full
    vulnerability register, split into active and resolved signals."""

    id: UUID
    full_name: str
    date_of_birth: date
    email: str
    phone: str
    kyc_status: str
    kyc_last_reviewed: datetime | None = None
    is_flagged: bool
    customer_since: date
    tier: str
    created_at: datetime
    active_vulnerability_signals: list[VulnerabilityRegisterRead] = Field(
        default_factory=list
    )
    resolved_vulnerability_signals: list[VulnerabilityRegisterRead] = Field(
        default_factory=list
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "active_vulnerability_signals", "resolved_vulnerability_signals", mode="before"
    )
    @classmethod
    def split_signals(cls, value: Any) -> Any:
        # Populated explicitly by from_customer(); default to empty otherwise.
        if value is None:
            return []
        return value

    @classmethod
    def from_customer(cls, customer: Any) -> "CustomerRead":
        """Build the read model from an ORM Customer, eagerly splitting the
        vulnerability register into active and resolved signals."""
        signals = getattr(customer, "vulnerability_signals", []) or []
        active = [
            VulnerabilityRegisterRead.model_validate(signal)
            for signal in signals
            if signal.status == "active"
        ]
        resolved = [
            VulnerabilityRegisterRead.model_validate(signal)
            for signal in signals
            if signal.status == "resolved"
        ]
        return cls(
            id=customer.id,
            full_name=customer.full_name,
            date_of_birth=customer.date_of_birth,
            email=customer.email,
            phone=customer.phone,
            kyc_status=customer.kyc_status,
            kyc_last_reviewed=customer.kyc_last_reviewed,
            is_flagged=customer.is_flagged,
            customer_since=customer.customer_since,
            tier=customer.tier,
            created_at=customer.created_at,
            active_vulnerability_signals=active,
            resolved_vulnerability_signals=resolved,
        )


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
    assigned_user_id: UUID | None = None
    disputed_amount: str | None = None
    merchant_name: str | None = None
    consumer_duty_flag: bool
    description: str
    opened_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("disputed_amount", mode="before")
    @classmethod
    def stringify_disputed_amount(cls, value: Decimal | str | None) -> str | None:
        if value is None:
            return None
        return str(value)


class AppUserRead(BaseModel):
    """Read model for an application user referenced by events/actions."""

    id: UUID
    username: str
    full_name: str
    role: str | None = None

    @classmethod
    def from_user(cls, user: Any) -> "AppUserRead":
        role = getattr(user, "role", None)
        return cls(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=getattr(role, "name", None),
        )


class CaseEventRead(BaseModel):
    """Read model for a case event, with nested source system record for
    system-generated events and nested user for user-generated events."""

    id: UUID
    case_id: UUID
    event_type: str
    event_description: str
    created_by_user_id: UUID | None = None
    created_by_system: str | None = None
    source_record_id: UUID | None = None
    created_at: datetime
    created_by_user: AppUserRead | None = None
    source_record: SourceSystemRecordRead | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_by_user", mode="before")
    @classmethod
    def coerce_user(cls, value: Any) -> Any:
        if value is None or isinstance(value, AppUserRead):
            return value
        return AppUserRead.from_user(value)


class NextActionRead(BaseModel):
    """Read model for a next action on a case, with computed overdue flag."""

    id: UUID
    case_id: UUID
    action_type: str
    description: str
    due_date: datetime
    status: str
    assigned_user_id: UUID | None = None
    created_by_user_id: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        """overdue is computed: status = 'open' AND due_date < now()."""
        due = self.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        return self.status == "open" and due < datetime.now(UTC)
