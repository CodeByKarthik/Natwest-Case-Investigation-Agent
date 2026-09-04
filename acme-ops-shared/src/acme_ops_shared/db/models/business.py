# db/models/business.py
import uuid
from datetime import date, datetime
from decimal import Decimal

from acme_ops_shared.db.base import Base
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Customer(Base):
    """
    Represents a customer for the NatWest investigation domain.
    """

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    primary_account_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    primary_sort_code: Mapped[str] = mapped_column(String(10), nullable=False)
    kyc_status: Mapped[str] = mapped_column(
        SAEnum(
            "verified",
            "pending_review",
            "expired",
            "not_started",
            name="kyc_status",
        ),
        nullable=False,
        default="not_started",
    )
    kyc_last_reviewed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    vulnerability_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    vulnerability_type: Mapped[str | None] = mapped_column(
        SAEnum(
            "health",
            "life_event",
            "resilience",
            "capability",
            name="vulnerability_type",
        ),
        nullable=True,
    )
    vulnerability_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_since: Mapped[date] = mapped_column(Date, nullable=False)
    tier: Mapped[str] = mapped_column(
        SAEnum("standard", "premium", "private_banking", name="customer_tier"),
        nullable=False,
        default="standard",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer")
    cases: Mapped[list["Issue"]] = relationship(back_populates="customer")

    __table_args__ = (
        Index("ix_customers_full_name", "full_name"),
        Index("ix_customers_kyc_status", "kyc_status"),
        Index("ix_customers_primary_account_number", "primary_account_number"),
    )


class Account(Base):
    """
    Represents an account tied to a customer.
    """

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    sort_code: Mapped[str] = mapped_column(String(10), nullable=False)
    account_type: Mapped[str] = mapped_column(
        SAEnum(
            "current",
            "savings",
            "isa",
            "business",
            "loan",
            "credit_card",
            name="account_type",
        ),
        nullable=False,
    )
    balance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "frozen", "closed", "restricted", name="account_status"),
        nullable=False,
        default="active",
    )
    opened_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer: Mapped[Customer] = relationship(back_populates="accounts")

    __table_args__ = (
        Index("ix_accounts_customer_id", "customer_id"),
        Index("ix_accounts_status", "status"),
    )


class Issue(Base):
    """
    Represents a case in the NatWest investigation workflow.
    """

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_ref: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    case_type: Mapped[str] = mapped_column(
        SAEnum(
            "dispute",
            "fraud",
            "complaint",
            "kyc_review",
            "vulnerability_review",
            name="case_type",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(
            "open",
            "under_investigation",
            "pending_customer",
            "escalated",
            "resolved",
            "closed",
            name="case_status",
        ),
        nullable=False,
        default="open",
    )
    priority: Mapped[str] = mapped_column(
        SAEnum("p1", "p2", "p3", "p4", name="case_priority"),
        nullable=False,
        default="p3",
    )
    opened_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    assigned_team: Mapped[str] = mapped_column(
        SAEnum("customer_support", "fraud", "compliance", name="assigned_team"),
        nullable=False,
        default="customer_support",
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    disputed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    merchant_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consumer_duty_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="cases")
    events: Mapped[list["IssueUpdate"]] = relationship(back_populates="case")
    next_actions: Mapped[list["NextAction"]] = relationship(back_populates="case")

    __table_args__ = (
        Index("ix_cases_customer_id", "customer_id"),
        Index("ix_cases_case_ref", "case_ref"),
        Index("ix_cases_status", "status"),
        Index("ix_cases_priority", "priority"),
        Index("ix_cases_assigned_user_id", "assigned_user_id"),
    )


class IssueUpdate(Base):
    """
    Represents a case event in the NatWest investigation domain.
    """

    __tablename__ = "case_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(
        SAEnum(
            "note",
            "status_change",
            "escalation",
            "customer_contact",
            "document_received",
            "system_alert",
            name="case_event_type",
        ),
        nullable=False,
    )
    event_description: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped[Issue] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_case_events_case_id", "case_id"),
        Index("ix_case_events_created_by_user_id", "created_by_user_id"),
    )


class NextAction(Base):
    """
    Represents the next action for a NatWest case.
    """

    __tablename__ = "next_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(
        SAEnum(
            "contact_customer",
            "request_documents",
            "issue_refund",
            "escalate_fraud",
            "escalate_vulnerability",
            "kyc_refresh",
            "add_case_note",
            name="next_action_type",
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(
            "open",
            "in_progress",
            "completed",
            "overdue",
            name="next_action_status",
        ),
        nullable=False,
        default="open",
    )
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped[Issue] = relationship(back_populates="next_actions")

    __table_args__ = (
        Index("ix_next_actions_case_id", "case_id"),
        Index("ix_next_actions_due_date", "due_date"),
        Index("ix_next_actions_status", "status"),
        Index("ix_next_actions_assigned_user_id", "assigned_user_id"),
    )
