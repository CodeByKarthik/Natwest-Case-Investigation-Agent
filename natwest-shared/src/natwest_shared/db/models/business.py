# db/models/business.py
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from natwest_shared.db.base import Base


class Customer(Base):
    """
    The persistent record of a person NatWest banks with.
    Vulnerability details live in vulnerability_register — is_flagged is a
    denormalised summary that is true when at least one active signal exists.
    """

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
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
    is_flagged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    customer_since: Mapped[date] = mapped_column(Date, nullable=False)
    tier: Mapped[str] = mapped_column(
        SAEnum("standard", "premium", "private_banking", name="customer_tier"),
        nullable=False,
        default="standard",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer")
    cases: Mapped[list["Case"]] = relationship(back_populates="customer")
    vulnerability_signals: Mapped[list["VulnerabilityRegister"]] = relationship(
        back_populates="customer"
    )

    __table_args__ = (
        Index("ix_customers_full_name", "full_name"),
        Index("ix_customers_kyc_status", "kyc_status"),
        Index("ix_customers_is_flagged", "is_flagged"),
    )


class Account(Base):
    """
    Financial products held by a customer. One customer can have many.
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
            "credit_card",
            "mortgage",
            "loan",
            name="account_type",
        ),
        nullable=False,
    )
    balance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            "active",
            "dormant",
            "closed",
            "frozen",
            name="account_status",
        ),
        nullable=False,
        default="active",
    )
    opened_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="accounts")

    __table_args__ = (
        Index("ix_accounts_customer_id", "customer_id"),
        Index("ix_accounts_status", "status"),
    )


class Case(Base):
    """
    Investigation cases raised against a customer. The core work object.
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
            "fraud",
            "dispute",
            "complaint",
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
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    disputed_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    merchant_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    consumer_duty_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    opened_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
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

    customer: Mapped[Customer] = relationship(back_populates="cases")
    assigned_user: Mapped["AppUser | None"] = relationship()
    events: Mapped[list["CaseEvent"]] = relationship(back_populates="case")
    next_actions: Mapped[list["NextAction"]] = relationship(back_populates="case")

    __table_args__ = (
        Index("ix_cases_customer_id", "customer_id"),
        Index("ix_cases_status", "status"),
        Index("ix_cases_priority", "priority"),
        Index("ix_cases_assigned_user_id", "assigned_user_id"),
        Index("ix_cases_consumer_duty_flag", "consumer_duty_flag"),
    )


class SourceSystemRecord(Base):
    """
    Raw records from external source systems (fraud engine, transaction
    monitoring, KYC monitoring). Each row is a snapshot of what the source
    system knew at the moment it generated an alert or signal.
    """

    __tablename__ = "source_system_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_system: Mapped[str] = mapped_column(
        SAEnum(
            "fraud_engine",
            "transaction_monitoring",
            "kyc_monitoring",
            name="source_system",
        ),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    record_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_source_system_records_source_system", "source_system"),
        Index("ix_source_system_records_generated_at", "generated_at"),
    )


class VulnerabilityRegister(Base):
    """
    One detected vulnerability signal for a customer. Signals persist after
    resolution, providing full history for Consumer Duty audit.
    """

    __tablename__ = "vulnerability_register"

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
    vulnerability_type: Mapped[str] = mapped_column(
        SAEnum(
            "health",
            "life_event",
            "resilience",
            "capability",
            name="vulnerability_type",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        SAEnum("active", "resolved", name="vulnerability_status"),
        nullable=False,
        default="active",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_system_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="vulnerability_signals")
    source_record: Mapped[SourceSystemRecord | None] = relationship()

    __table_args__ = (
        Index("ix_vulnerability_register_customer_id", "customer_id"),
        Index("ix_vulnerability_register_status", "status"),
        Index("ix_vulnerability_register_vulnerability_type", "vulnerability_type"),
        Index("ix_vulnerability_register_source_record_id", "source_record_id"),
        Index("ix_vulnerability_register_detected_at", "detected_at"),
    )


class CaseEvent(Base):
    """
    Chronological timeline of what has happened on a case. Immutable — events
    are never updated, only appended. Every event is either user-created or
    system-created, never both.
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
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_system: Mapped[str | None] = mapped_column(
        SAEnum(
            "fraud_engine",
            "transaction_monitoring",
            "kyc_monitoring",
            name="created_by_system",
        ),
        nullable=True,
    )
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_system_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped[Case] = relationship(back_populates="events")
    created_by_user: Mapped["AppUser | None"] = relationship()
    source_record: Mapped[SourceSystemRecord | None] = relationship()

    __table_args__ = (
        Index("ix_case_events_case_id", "case_id"),
        Index("ix_case_events_created_by_user_id", "created_by_user_id"),
        Index("ix_case_events_created_by_system", "created_by_system"),
        Index("ix_case_events_source_record_id", "source_record_id"),
        Index("ix_case_events_created_at", "created_at"),
    )


class NextAction(Base):
    """
    Outstanding follow-up tasks on a case. Mutable — status changes as work
    progresses. `overdue` is not stored — compute it from status + due_date.
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
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    case: Mapped[Case] = relationship(back_populates="next_actions")
    assigned_user: Mapped["AppUser | None"] = relationship(
        foreign_keys=[assigned_user_id]
    )
    created_by_user: Mapped["AppUser | None"] = relationship(
        foreign_keys=[created_by_user_id]
    )

    __table_args__ = (
        Index("ix_next_actions_case_id", "case_id"),
        Index("ix_next_actions_assigned_user_id", "assigned_user_id"),
        Index("ix_next_actions_status", "status"),
        Index("ix_next_actions_due_date", "due_date"),
    )


# Avoid circular import at runtime: only needed for relationship typing.
from natwest_shared.db.models.user import AppUser
