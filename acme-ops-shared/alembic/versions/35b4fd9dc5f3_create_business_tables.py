"""create NatWest business tables

Revision ID: 35b4fd9dc5f3
Revises: 97b1ddf51c6c
Create Date: 2026-05-28 14:24:57.423115

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "35b4fd9dc5f3"
down_revision: Union[str, Sequence[str], None] = "97b1ddf51c6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to the NatWest case-investigation model."""
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("primary_account_number", sa.String(length=20), nullable=False),
        sa.Column("primary_sort_code", sa.String(length=10), nullable=False),
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
        sa.Column("vulnerability_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "vulnerability_type",
            sa.Enum("health", "life_event", "resilience", "capability", name="vulnerability_type"),
            nullable=True,
        ),
        sa.Column("vulnerability_notes", sa.Text(), nullable=True),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("primary_account_number"),
    )
    op.create_index("ix_customers_full_name", "customers", ["full_name"], unique=False)
    op.create_index("ix_customers_kyc_status", "customers", ["kyc_status"], unique=False)
    op.create_index(
        "ix_customers_primary_account_number",
        "customers",
        ["primary_account_number"],
        unique=False,
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
                "isa",
                "business",
                "loan",
                "credit_card",
                name="account_type",
            ),
            nullable=False,
        ),
        sa.Column("balance", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "frozen", "closed", "restricted", name="account_status"),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_number"),
    )
    op.create_index("ix_accounts_customer_id", "accounts", ["customer_id"], unique=False)
    op.create_index("ix_accounts_status", "accounts", ["status"], unique=False)

    op.create_table(
        "cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("case_ref", sa.String(length=20), nullable=False),
        sa.Column(
            "case_type",
            sa.Enum(
                "dispute",
                "fraud",
                "complaint",
                "kyc_review",
                "vulnerability_review",
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
        sa.Column("opened_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "assigned_team",
            sa.Enum("customer_support", "fraud", "compliance", name="assigned_team"),
            nullable=False,
            server_default="customer_support",
        ),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("disputed_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("merchant_name", sa.String(length=200), nullable=True),
        sa.Column("merchant_category", sa.String(length=100), nullable=True),
        sa.Column("consumer_duty_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["app_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_ref"),
    )
    op.create_index("ix_cases_customer_id", "cases", ["customer_id"], unique=False)
    op.create_index("ix_cases_case_ref", "cases", ["case_ref"], unique=False)
    op.create_index("ix_cases_status", "cases", ["status"], unique=False)
    op.create_index("ix_cases_priority", "cases", ["priority"], unique=False)
    op.create_index("ix_cases_assigned_user_id", "cases", ["assigned_user_id"], unique=False)

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
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_by_name", sa.String(length=100), nullable=True),
        sa.Column("created_by_role", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_events_case_id", "case_events", ["case_id"], unique=False)
    op.create_index(
        "ix_case_events_created_by_user_id",
        "case_events",
        ["created_by_user_id"],
        unique=False,
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
            sa.Enum("open", "in_progress", "completed", "overdue", name="next_action_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_by_role", sa.String(length=50), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["app_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_next_actions_case_id", "next_actions", ["case_id"], unique=False)
    op.create_index("ix_next_actions_due_date", "next_actions", ["due_date"], unique=False)
    op.create_index("ix_next_actions_status", "next_actions", ["status"], unique=False)
    op.create_index(
        "ix_next_actions_assigned_user_id",
        "next_actions",
        ["assigned_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema back to the previous business shape."""
    op.drop_index("ix_next_actions_assigned_user_id", table_name="next_actions")
    op.drop_index("ix_next_actions_status", table_name="next_actions")
    op.drop_index("ix_next_actions_due_date", table_name="next_actions")
    op.drop_index("ix_next_actions_case_id", table_name="next_actions")
    op.drop_table("next_actions")

    op.drop_index("ix_case_events_created_by_user_id", table_name="case_events")
    op.drop_index("ix_case_events_case_id", table_name="case_events")
    op.drop_table("case_events")

    op.drop_index("ix_cases_assigned_user_id", table_name="cases")
    op.drop_index("ix_cases_priority", table_name="cases")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_case_ref", table_name="cases")
    op.drop_index("ix_cases_customer_id", table_name="cases")
    op.drop_table("cases")

    op.drop_index("ix_accounts_status", table_name="accounts")
    op.drop_index("ix_accounts_customer_id", table_name="accounts")
    op.drop_table("accounts")

    op.drop_index("ix_customers_primary_account_number", table_name="customers")
    op.drop_index("ix_customers_kyc_status", table_name="customers")
    op.drop_index("ix_customers_full_name", table_name="customers")
    op.drop_table("customers")
