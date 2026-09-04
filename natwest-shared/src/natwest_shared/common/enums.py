import enum
from enum import StrEnum
from typing import List


class AppRole(StrEnum):
    """
    Enum representing different application roles for banking case investigation users.
    """

    CUSTOMER_SUPPORT = "customer_support"
    FRAUD_INVESTIGATOR = "fraud_investigator"
    COMPLIANCE_OFFICER = "compliance_officer"


class CustomerTierEnum(StrEnum):
    """
    Enum representing different customer tiers
    based on their size and revenue.
    """

    SMB = "smb"
    MID_MARKET = "mid_market"
    ENTERPRISE = "enterprise"


class CustomerHealthEnum(StrEnum):
    """
    Enum representing the health status of a customer
    based on various factors such as usage, support.
    """

    HEALTHY = "healthy"
    WATCH = "watch"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


class CaseStatusEnum(StrEnum):
    """
    Enum representing the status values allowed on a NatWest case.
    """

    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    PENDING_CUSTOMER = "pending_customer"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriorityEnum(StrEnum):
    """
    Enum representing the priority levels of an issue
    to help with resolution.
    """

    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class NextActionTypeEnum(StrEnum):
    """
    Enum representing the types of next actions that can
    be taken for an issue or customer interaction.
    """

    CONTACT_CUSTOMER = "contact_customer"
    REQUEST_DOCUMENTS = "request_documents"
    ISSUE_REFUND = "issue_refund"
    ESCALATE_FRAUD = "escalate_fraud"
    ESCALATE_VULNERABILITY = "escalate_vulnerability"
    KYC_REFRESH = "kyc_refresh"
    ADD_CASE_NOTE = "add_case_note"
    CUSTOMER_UPDATE = "customer_update"
    TECHNICAL_INVESTIGATION = "technical_investigation"
    WORKAROUND_CONFIRMATION = "workaround_confirmation"
    ENGINEERING_ESCALATION = "engineering_escalation"
    ACCOUNT_ESCALATION = "account_escalation"
    SLA_REVIEW = "sla_review"
    FOLLOW_UP_MEETING = "follow_up_meeting"
    OTHER = "other"


class NextActionStatusEnum(StrEnum):
    """
    Enum representing the status of a next action item.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def enum_values(enum_class: type[enum.Enum]) -> List[str]:
    """
    Return list of enum values for SQLAlchemy Enum construction.
    """
    return [member.value for member in enum_class]
