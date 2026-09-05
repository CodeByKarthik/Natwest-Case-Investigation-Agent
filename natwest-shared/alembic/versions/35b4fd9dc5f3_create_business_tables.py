"""create business tables

Revision ID: 35b4fd9dc5f3
Revises: 97b1ddf51c6c
Create Date: 2026-05-27 23:00:00.000000

Creates the NatWest investigation domain schema:
customers, accounts, cases, source_system_records, vulnerability_register,
case_events, next_actions.

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "35b4fd9dc5f3"
down_revision: Union[str, Sequence[str], None] = "97b1ddf51c6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the business domain tables."""
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column(
            "kyc_status",
            sa.Enum(
                "verified",
                "pending_review",
                "expired",
                "not_started",
                name="kyc_status",
            ),
            nullable=False,
            server_default="not_started",
        ),
        sa.Column("kyc_last_reviewed", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_flagged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("customer_since", sa.Date(), nullable=False),
        sa.Column(
            "tier",
            sa.Enum("standard", "premium", "private_banking", name="customer_tier"),
            nullable=False,
            server_default="standard",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_full_name", "customers", ["full_name"], unique=False)
    op.create_index(
        "ix_customers_kyc_status", "customers", ["kyc_status"], unique=False
    )
    op.create_index(
        "ix_customers_is_flagged", "customers", ["is_flagged"], unique=False
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("account_number", sa.String(length=20), nullable=False),
        sa.Column("sort_code", sa.String(length=10), nullable=False),
        sa.Column(
            "account_type",
            sa.Enum(
                "current",
                "savings",
                "credit_card",
                "mortgage",
                "loan",
                name="account_type",
            ),
            nullable=False,
        ),
        sa.Column("balance", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "dormant",
                "closed",
                "frozen",
                name="account_status",
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("opened_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_number"),
    )
    op.create_index(
        "ix_accounts_customer_id", "accounts", ["customer_id"], unique=False
    )
    op.create_index("ix_accounts_status", "accounts", ["status"], unique=False)

    op.create_table(
        "source_system_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "source_system",
            sa.Enum(
                "fraud_engine",
                "transaction_monitoring",
                "kyc_monitoring",
                name="source_system",
            ),
            nullable=False,
        ),
        sa.Column("source_ref", sa.String(length=100), nullable=False),
        sa.Column("record_type", sa.String(length=100), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_ref"),
    )
    op.create_index(
        "ix_source_system_records_source_system",
        "source_system_records",
        ["source_system"],
        unique=False,
    )
    op.create_index(
        "ix_source_system_records_generated_at",
        "source_system_records",
        ["generated_at"],
        unique=False,
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("case_ref", sa.String(length=20), nullable=False),
        sa.Column(
            "case_type",
            sa.Enum(
                "fraud",
                "dispute",
                "complaint",
                name="case_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "under_investigation",
                "pending_customer",
                "escalated",
                "resolved",
                "closed",
                name="case_status",
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "priority",
            sa.Enum("p1", "p2", "p3", "p4", name="case_priority"),
            nullable=False,
            server_default="p3",
        ),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("disputed_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("merchant_name", sa.String(length=200), nullable=True),
        sa.Column(
            "consumer_duty_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("opened_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"], ["app_users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_ref"),
    )
    op.create_index("ix_cases_customer_id", "cases", ["customer_id"], unique=False)
    op.create_index("ix_cases_status", "cases", ["status"], unique=False)
    op.create_index("ix_cases_priority", "cases", ["priority"], unique=False)
    op.create_index(
        "ix_cases_assigned_user_id", "cases", ["assigned_user_id"], unique=False
    )
    op.create_index(
        "ix_cases_consumer_duty_flag", "cases", ["consumer_duty_flag"], unique=False
    )

    op.create_table(
        "vulnerability_register",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column(
            "vulnerability_type",
            sa.Enum(
                "health",
                "life_event",
                "resilience",
                "capability",
                name="vulnerability_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "resolved", name="vulnerability_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_record_id", sa.UUID(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_record_id"], ["source_system_records.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vulnerability_register_customer_id",
        "vulnerability_register",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_vulnerability_register_status",
        "vulnerability_register",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_vulnerability_register_vulnerability_type",
        "vulnerability_register",
        ["vulnerability_type"],
        unique=False,
    )
    op.create_index(
        "ix_vulnerability_register_source_record_id",
        "vulnerability_register",
        ["source_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_vulnerability_register_detected_at",
        "vulnerability_register",
        ["detected_at"],
        unique=False,
    )

    op.create_table(
        "case_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "note",
                "status_change",
                "escalation",
                "customer_contact",
                "document_received",
                "system_alert",
                name="case_event_type",
            ),
            nullable=False,
        ),
        sa.Column("event_description", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_by_system",
            sa.Enum(
                "fraud_engine",
                "transaction_monitoring",
                "kyc_monitoring",
                name="created_by_system",
            ),
            nullable=True,
        ),
        sa.Column("source_record_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["app_users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"], ["source_system_records.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_events_case_id", "case_events", ["case_id"], unique=False)
    op.create_index(
        "ix_case_events_created_by_user_id",
        "case_events",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_case_events_created_by_system",
        "case_events",
        ["created_by_system"],
        unique=False,
    )
    op.create_index(
        "ix_case_events_source_record_id",
        "case_events",
        ["source_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_case_events_created_at", "case_events", ["created_at"], unique=False
    )

    op.create_table(
        "next_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column(
            "action_type",
            sa.Enum(
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
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "in_progress", "completed", name="next_action_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"], ["app_users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["app_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_next_actions_case_id", "next_actions", ["case_id"], unique=False
    )
    op.create_index(
        "ix_next_actions_assigned_user_id",
        "next_actions",
        ["assigned_user_id"],
        unique=False,
    )
    op.create_index("ix_next_actions_status", "next_actions", ["status"], unique=False)
    op.create_index(
        "ix_next_actions_due_date", "next_actions", ["due_date"], unique=False
    )


def downgrade() -> None:
    """Drop the business domain tables."""
    op.drop_index("ix_next_actions_due_date", table_name="next_actions")
    op.drop_index("ix_next_actions_status", table_name="next_actions")
    op.drop_index("ix_next_actions_assigned_user_id", table_name="next_actions")
    op.drop_index("ix_next_actions_case_id", table_name="next_actions")
    op.drop_table("next_actions")

    op.drop_index("ix_case_events_created_at", table_name="case_events")
    op.drop_index("ix_case_events_source_record_id", table_name="case_events")
    op.drop_index("ix_case_events_created_by_system", table_name="case_events")
    op.drop_index("ix_case_events_created_by_user_id", table_name="case_events")
    op.drop_index("ix_case_events_case_id", table_name="case_events")
    op.drop_table("case_events")

    op.drop_index(
        "ix_vulnerability_register_detected_at", table_name="vulnerability_register"
    )
    op.drop_index(
        "ix_vulnerability_register_source_record_id",
        table_name="vulnerability_register",
    )
    op.drop_index(
        "ix_vulnerability_register_vulnerability_type",
        table_name="vulnerability_register",
    )
    op.drop_index(
        "ix_vulnerability_register_status", table_name="vulnerability_register"
    )
    op.drop_index(
        "ix_vulnerability_register_customer_id", table_name="vulnerability_register"
    )
    op.drop_table("vulnerability_register")

    op.drop_index("ix_cases_consumer_duty_flag", table_name="cases")
    op.drop_index("ix_cases_assigned_user_id", table_name="cases")
    op.drop_index("ix_cases_priority", table_name="cases")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_customer_id", table_name="cases")
    op.drop_table("cases")

    op.drop_index(
        "ix_source_system_records_generated_at", table_name="source_system_records"
    )
    op.drop_index(
        "ix_source_system_records_source_system", table_name="source_system_records"
    )
    op.drop_table("source_system_records")

    op.drop_index("ix_accounts_status", table_name="accounts")
    op.drop_index("ix_accounts_customer_id", table_name="accounts")
    op.drop_table("accounts")

    op.drop_index("ix_customers_is_flagged", table_name="customers")
    op.drop_index("ix_customers_kyc_status", table_name="customers")
    op.drop_index("ix_customers_full_name", table_name="customers")
    op.drop_table("customers")
