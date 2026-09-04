# db/models/business.py
import uuid
from datetime import datetime
from decimal import Decimal

from acme_ops_shared.common.enums import (
    CustomerHealthEnum,
    CustomerTierEnum,
    IssuePriorityEnum,
    IssueStatusEnum,
    NextActionStatusEnum,
    NextActionTypeEnum,
    enum_values,
)
from acme_ops_shared.db.base import Base
from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Customer(Base):
    """
    Represents a Customer Model in the system.
    """

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    tier: Mapped[CustomerTierEnum] = mapped_column(
        SAEnum(
            CustomerTierEnum,
            name="customer_tier",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    account_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    contract_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    health_status: Mapped[CustomerHealthEnum] = mapped_column(
        SAEnum(
            CustomerHealthEnum,
            name="customer_health",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
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

    issues: Mapped[list["Issue"]] = relationship(back_populates="customer")

    __table_args__ = (
        Index("ix_customers_name", "name"),
        Index("ix_customers_health_status", "health_status"),
        Index("ix_customers_deleted_at", "deleted_at"),
    )


class Issue(Base):
    """
    Represents an Issue Model in the system.
    """

    __tablename__ = "issues"

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
    external_ref: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[IssueStatusEnum] = mapped_column(
        SAEnum(
            IssueStatusEnum,
            name="issue_status",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    priority: Mapped[IssuePriorityEnum] = mapped_column(
        SAEnum(
            IssuePriorityEnum,
            name="issue_priority",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_system: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="natwest-support",
    )

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
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

    customer: Mapped[Customer] = relationship(back_populates="issues")
    updates: Mapped[list["IssueUpdate"]] = relationship(back_populates="issue")
    next_actions: Mapped[list["NextAction"]] = relationship(back_populates="issue")

    __table_args__ = (
        Index("ix_issues_customer_id", "customer_id"),
        Index("ix_issues_status", "status"),
        Index("ix_issues_priority", "priority"),
        Index("ix_issues_customer_id_status", "customer_id", "status"),
        Index("ix_issues_assigned_to_user_id", "assigned_to_user_id"),
        Index("ix_issues_deleted_at", "deleted_at"),
    )


class IssueUpdate(Base):
    """
    Represents an Issue Update Model in the system.
    """

    __tablename__ = "issue_updates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    update_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_customer_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    issue: Mapped[Issue] = relationship(back_populates="updates")

    __table_args__ = (
        Index("ix_issue_updates_issue_id", "issue_id"),
        Index("ix_issue_updates_issue_id_created_at", "issue_id", created_at.desc()),
        Index("ix_issue_updates_author_user_id", "author_user_id"),
    )


class NextAction(Base):
    """
    Represents a Next Action Model in the system.
    """

    __tablename__ = "next_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[NextActionTypeEnum] = mapped_column(
        SAEnum(
            NextActionTypeEnum,
            name="next_action_type",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[NextActionStatusEnum] = mapped_column(
        SAEnum(
            NextActionStatusEnum,
            name="next_action_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=NextActionStatusEnum.OPEN,
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    issue: Mapped[Issue] = relationship(back_populates="next_actions")

    __table_args__ = (
        Index("ix_next_actions_issue_id", "issue_id"),
        Index("ix_next_actions_status", "status"),
        Index("ix_next_actions_owner_user_id", "owner_user_id"),
        Index("ix_next_actions_created_by_user_id", "created_by_user_id"),
        Index("ix_next_actions_due_at", "due_at"),
    )
