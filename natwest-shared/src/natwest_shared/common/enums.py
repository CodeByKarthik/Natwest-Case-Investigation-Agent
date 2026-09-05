import enum
from enum import StrEnum
from typing import List


class AppRole(StrEnum):
    """
    Enum representing different application roles for banking case investigation users.
    """

    CUSTOMER_SUPPORT = "customer_support"
    FRAUD_INVESTIGATOR = "fraud_investigator"
    CASE_MANAGER = "case_manager"


class KycStatusEnum(StrEnum):
    """
    Enum representing customer KYC review states.
    """

    VERIFIED = "verified"
    PENDING_REVIEW = "pending_review"
    EXPIRED = "expired"
    NOT_STARTED = "not_started"


class TierEnum(StrEnum):
    """
    Enum representing customer tiers.
    """

    STANDARD = "standard"
    PREMIUM = "premium"
    PRIVATE_BANKING = "private_banking"


class CaseTypeEnum(StrEnum):
    """
    Enum representing the types of investigation cases.
    """

    FRAUD = "fraud"
    DISPUTE = "dispute"
    COMPLAINT = "complaint"


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
    be taken for a case.
    """

    CONTACT_CUSTOMER = "contact_customer"
    REQUEST_DOCUMENTS = "request_documents"
    ISSUE_REFUND = "issue_refund"
    ESCALATE_FRAUD = "escalate_fraud"
    ESCALATE_VULNERABILITY = "escalate_vulnerability"
    KYC_REFRESH = "kyc_refresh"
    ADD_CASE_NOTE = "add_case_note"


class NextActionStatusEnum(StrEnum):
    """
    Enum representing the status of a next action item.
    `overdue` is computed, never stored.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class SourceSystemEnum(StrEnum):
    """
    External source systems that generate alerts and signals.
    """

    FRAUD_ENGINE = "fraud_engine"
    TRANSACTION_MONITORING = "transaction_monitoring"
    KYC_MONITORING = "kyc_monitoring"


class VulnerabilityTypeEnum(StrEnum):
    """
    Vulnerability signal categories tracked in the vulnerability register.
    """

    HEALTH = "health"
    LIFE_EVENT = "life_event"
    RESILIENCE = "resilience"
    CAPABILITY = "capability"


class VulnerabilityStatusEnum(StrEnum):
    """
    Status of a vulnerability register entry.
    """

    ACTIVE = "active"
    RESOLVED = "resolved"


class StaffTeamEnum(StrEnum):
    """
    Team an app user belongs to.
    """

    CUSTOMER_SUPPORT = "customer_support"
    FRAUD = "fraud"
    CASE_MANAGEMENT = "case_management"


def enum_values(enum_class: type[enum.Enum]) -> List[str]:
    """
    Return list of enum values for SQLAlchemy Enum construction.
    """
    return [member.value for member in enum_class]
