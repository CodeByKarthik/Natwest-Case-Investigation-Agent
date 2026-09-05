"""Seed NatWest demo business data.

10 customers covering every dimension of the schema:
- All case types (fraud, dispute, complaint) and all case statuses
  (open, under_investigation, pending_customer, escalated, resolved, closed)
- All priorities (p1-p4) and all three staff assignees
- All three source systems (fraud_engine, transaction_monitoring, kyc_monitoring)
  with raw source_system_records wired to case events and vulnerability signals
- Active and resolved vulnerability register entries across all four types
- Next actions in open / in_progress / completed states, including an
  open past-due action to demonstrate computed overdue behaviour
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from natwest_shared.db.models.business import (
    Account,
    Case,
    CaseEvent,
    Customer,
    NextAction,
    SourceSystemRecord,
    VulnerabilityRegister,
)
from natwest_shared.db.models.user import AppUser
from natwest_shared.db.session import SessionLocal


def get_user_by_username(session: Session, username: str) -> AppUser:
    user = session.scalar(select(AppUser).where(AppUser.username == username))

    if user is None:
        raise RuntimeError(
            f"Required seed user '{username}' not found. "
            "Run seed_users before seed_business_data."
        )

    return user


def get_or_create_customer(
    session: Session,
    *,
    full_name: str,
    date_of_birth: date,
    email: str,
    phone: str,
    kyc_status: str,
    kyc_last_reviewed: datetime | None,
    is_flagged: bool,
    customer_since: date,
    tier: str,
) -> Customer:
    existing = session.scalar(select(Customer).where(Customer.email == email))

    if existing is not None:
        return existing

    customer = Customer(
        full_name=full_name,
        date_of_birth=date_of_birth,
        email=email,
        phone=phone,
        kyc_status=kyc_status,
        kyc_last_reviewed=kyc_last_reviewed,
        is_flagged=is_flagged,
        customer_since=customer_since,
        tier=tier,
    )

    session.add(customer)
    session.flush()
    return customer


def get_or_create_account(
    session: Session,
    *,
    customer_id: UUID,
    account_number: str,
    sort_code: str,
    account_type: str,
    balance: Decimal | None,
    status: str,
    opened_date: date,
) -> Account:
    existing = session.scalar(
        select(Account).where(Account.account_number == account_number)
    )

    if existing is not None:
        return existing

    account = Account(
        customer_id=customer_id,
        account_number=account_number,
        sort_code=sort_code,
        account_type=account_type,
        balance=balance,
        status=status,
        opened_date=opened_date,
    )

    session.add(account)
    session.flush()
    return account


def get_or_create_source_record(
    session: Session,
    *,
    source_system: str,
    source_ref: str,
    record_type: str,
    confidence_score: Decimal | None,
    payload: dict[str, Any],
    generated_at: datetime,
) -> SourceSystemRecord:
    existing = session.scalar(
        select(SourceSystemRecord).where(SourceSystemRecord.source_ref == source_ref)
    )

    if existing is not None:
        return existing

    record = SourceSystemRecord(
        source_system=source_system,
        source_ref=source_ref,
        record_type=record_type,
        confidence_score=confidence_score,
        payload=payload,
        generated_at=generated_at,
    )

    session.add(record)
    session.flush()
    return record


def get_or_create_case(
    session: Session,
    *,
    case_ref: str,
    customer_id: UUID,
    case_type: str,
    status: str,
    priority: str,
    assigned_user_id: UUID | None,
    disputed_amount: Decimal | None,
    merchant_name: str | None,
    consumer_duty_flag: bool,
    description: str,
    opened_date: datetime,
) -> Case:
    existing = session.scalar(select(Case).where(Case.case_ref == case_ref))

    if existing is not None:
        return existing

    case = Case(
        customer_id=customer_id,
        case_ref=case_ref,
        case_type=case_type,
        status=status,
        priority=priority,
        assigned_user_id=assigned_user_id,
        disputed_amount=disputed_amount,
        merchant_name=merchant_name,
        consumer_duty_flag=consumer_duty_flag,
        description=description,
        opened_date=opened_date,
    )

    session.add(case)
    session.flush()
    return case


def add_vulnerability_signal_if_missing(
    session: Session,
    *,
    customer_id: UUID,
    vulnerability_type: str,
    status: str,
    notes: str | None,
    source_record_id: UUID | None,
    detected_at: datetime,
    resolved_at: datetime | None,
) -> None:
    existing = session.scalar(
        select(VulnerabilityRegister).where(
            VulnerabilityRegister.customer_id == customer_id,
            VulnerabilityRegister.vulnerability_type == vulnerability_type,
            VulnerabilityRegister.detected_at == detected_at,
        )
    )

    if existing is not None:
        return

    session.add(
        VulnerabilityRegister(
            customer_id=customer_id,
            vulnerability_type=vulnerability_type,
            status=status,
            notes=notes,
            source_record_id=source_record_id,
            detected_at=detected_at,
            resolved_at=resolved_at,
        )
    )


def add_case_event_if_missing(
    session: Session,
    *,
    case_id: UUID,
    event_type: str,
    event_description: str,
    created_by_user_id: UUID | None,
    created_by_system: str | None,
    source_record_id: UUID | None,
    created_at: datetime,
) -> None:
    existing = session.scalar(
        select(CaseEvent).where(
            CaseEvent.case_id == case_id,
            CaseEvent.event_description == event_description,
        )
    )

    if existing is not None:
        return

    session.add(
        CaseEvent(
            case_id=case_id,
            event_type=event_type,
            event_description=event_description,
            created_by_user_id=created_by_user_id,
            created_by_system=created_by_system,
            source_record_id=source_record_id,
            created_at=created_at,
        )
    )


def add_next_action_if_missing(
    session: Session,
    *,
    case_id: UUID,
    action_type: str,
    description: str,
    due_date: datetime,
    status: str,
    assigned_user_id: UUID | None,
    created_by_user_id: UUID | None,
    completed_at: datetime | None = None,
) -> None:
    existing = session.scalar(
        select(NextAction).where(
            NextAction.case_id == case_id,
            NextAction.description == description,
        )
    )

    if existing is not None:
        return

    session.add(
        NextAction(
            case_id=case_id,
            action_type=action_type,
            description=description,
            due_date=due_date,
            status=status,
            assigned_user_id=assigned_user_id,
            created_by_user_id=created_by_user_id,
            completed_at=completed_at,
        )
    )


def seed_business_data() -> None:
    now = datetime.now(UTC)

    with SessionLocal() as session:
        support = get_user_by_username(session, "customer_support")
        investigator = get_user_by_username(session, "fraud_investigator")
        manager = get_user_by_username(session, "case_manager")

        # ---------- Customers (10) ----------
        aisha = get_or_create_customer(
            session,
            full_name="Aisha Rahman",
            date_of_birth=date(1988, 6, 14),
            email="aisha.rahman@example.com",
            phone="+44 7700 900101",
            kyc_status="verified",
            kyc_last_reviewed=now - timedelta(days=120),
            is_flagged=False,
            customer_since=date(2018, 2, 1),
            tier="premium",
        )
        michael = get_or_create_customer(
            session,
            full_name="Michael Osei",
            date_of_birth=date(1992, 11, 7),
            email="michael.osei@example.com",
            phone="+44 7700 900102",
            kyc_status="pending_review",
            kyc_last_reviewed=now - timedelta(days=400),
            is_flagged=False,
            customer_since=date(2021, 8, 15),
            tier="standard",
        )
        priya = get_or_create_customer(
            session,
            full_name="Priya Nair",
            date_of_birth=date(1979, 3, 26),
            email="priya.nair@example.com",
            phone="+44 7700 900103",
            kyc_status="verified",
            kyc_last_reviewed=now - timedelta(days=60),
            is_flagged=True,
            customer_since=date(2015, 6, 10),
            tier="private_banking",
        )
        david = get_or_create_customer(
            session,
            full_name="David Thompson",
            date_of_birth=date(1985, 1, 22),
            email="david.thompson@example.com",
            phone="+44 7700 900104",
            kyc_status="verified",
            kyc_last_reviewed=now - timedelta(days=200),
            is_flagged=False,
            customer_since=date(2019, 5, 30),
            tier="standard",
        )
        fatima = get_or_create_customer(
            session,
            full_name="Fatima Begum",
            date_of_birth=date(1968, 9, 3),
            email="fatima.begum@example.com",
            phone="+44 7700 900105",
            kyc_status="verified",
            kyc_last_reviewed=now - timedelta(days=30),
            is_flagged=False,
            customer_since=date(2010, 11, 12),
            tier="premium",
        )
        george = get_or_create_customer(
            session,
            full_name="George Whitfield",
            date_of_birth=date(1955, 4, 17),
            email="george.whitfield@example.com",
            phone="+44 7700 900106",
            kyc_status="expired",
            kyc_last_reviewed=now - timedelta(days=800),
            is_flagged=True,
            customer_since=date(2001, 3, 8),
            tier="private_banking",
        )
        hannah = get_or_create_customer(
            session,
            full_name="Hannah Kim",
            date_of_birth=date(1995, 12, 1),
            email="hannah.kim@example.com",
            phone="+44 7700 900107",
            kyc_status="verified",
            kyc_last_reviewed=now - timedelta(days=45),
            is_flagged=False,
            customer_since=date(2022, 7, 19),
            tier="premium",
        )
        raj = get_or_create_customer(
            session,
            full_name="Raj Patel",
            date_of_birth=date(1982, 8, 25),
            email="raj.patel@example.com",
            phone="+44 7700 900108",
            kyc_status="pending_review",
            kyc_last_reviewed=now - timedelta(days=300),
            is_flagged=False,
            customer_since=date(2020, 2, 14),
            tier="standard",
        )
        elena = get_or_create_customer(
            session,
            full_name="Elena Popescu",
            date_of_birth=date(1990, 6, 30),
            email="elena.popescu@example.com",
            phone="+44 7700 900109",
            kyc_status="verified",
            kyc_last_reviewed=now - timedelta(days=90),
            is_flagged=True,
            customer_since=date(2023, 1, 5),
            tier="standard",
        )
        tom = get_or_create_customer(
            session,
            full_name="Tom Baker",
            date_of_birth=date(2001, 10, 11),
            email="tom.baker@example.com",
            phone="+44 7700 900110",
            kyc_status="not_started",
            kyc_last_reviewed=None,
            is_flagged=False,
            customer_since=date(2026, 1, 15),
            tier="standard",
        )

        # ---------- Accounts ----------
        get_or_create_account(
            session,
            customer_id=aisha.id,
            account_number="10012345678",
            sort_code="040004",
            account_type="current",
            balance=Decimal("18542.76"),
            status="active",
            opened_date=date(2018, 2, 1),
        )
        get_or_create_account(
            session,
            customer_id=aisha.id,
            account_number="60012345678",
            sort_code="040004",
            account_type="credit_card",
            balance=Decimal("-1240.55"),
            status="active",
            opened_date=date(2019, 3, 12),
        )
        get_or_create_account(
            session,
            customer_id=michael.id,
            account_number="10023456789",
            sort_code="112233",
            account_type="current",
            balance=Decimal("3210.40"),
            status="active",
            opened_date=date(2021, 8, 15),
        )
        get_or_create_account(
            session,
            customer_id=michael.id,
            account_number="20023456789",
            sort_code="112233",
            account_type="savings",
            balance=Decimal("21650.12"),
            status="active",
            opened_date=date(2021, 8, 15),
        )
        get_or_create_account(
            session,
            customer_id=priya.id,
            account_number="10034567890",
            sort_code="203040",
            account_type="current",
            balance=Decimal("48200.00"),
            status="active",
            opened_date=date(2015, 6, 10),
        )
        get_or_create_account(
            session,
            customer_id=priya.id,
            account_number="40034567890",
            sort_code="203040",
            account_type="mortgage",
            balance=Decimal("-312500.00"),
            status="active",
            opened_date=date(2017, 9, 1),
        )
        get_or_create_account(
            session,
            customer_id=david.id,
            account_number="10045678901",
            sort_code="162534",
            account_type="current",
            balance=Decimal("2210.18"),
            status="active",
            opened_date=date(2019, 5, 30),
        )
        get_or_create_account(
            session,
            customer_id=david.id,
            account_number="60045678901",
            sort_code="162534",
            account_type="credit_card",
            balance=Decimal("-89.99"),
            status="frozen",
            opened_date=date(2020, 1, 20),
        )
        get_or_create_account(
            session,
            customer_id=fatima.id,
            account_number="20056789012",
            sort_code="070116",
            account_type="savings",
            balance=Decimal("76800.00"),
            status="active",
            opened_date=date(2010, 11, 12),
        )
        get_or_create_account(
            session,
            customer_id=fatima.id,
            account_number="50056789012",
            sort_code="070116",
            account_type="loan",
            balance=None,
            status="closed",
            opened_date=date(2014, 4, 2),
        )
        get_or_create_account(
            session,
            customer_id=george.id,
            account_number="10067890123",
            sort_code="309972",
            account_type="current",
            balance=Decimal("96400.75"),
            status="active",
            opened_date=date(2001, 3, 8),
        )
        get_or_create_account(
            session,
            customer_id=george.id,
            account_number="40067890123",
            sort_code="309972",
            account_type="mortgage",
            balance=None,
            status="closed",
            opened_date=date(2005, 6, 21),
        )
        get_or_create_account(
            session,
            customer_id=hannah.id,
            account_number="10078901234",
            sort_code="404784",
            account_type="current",
            balance=Decimal("5430.22"),
            status="active",
            opened_date=date(2022, 7, 19),
        )
        get_or_create_account(
            session,
            customer_id=hannah.id,
            account_number="20078901234",
            sort_code="404784",
            account_type="savings",
            balance=Decimal("12800.00"),
            status="active",
            opened_date=date(2022, 7, 19),
        )
        get_or_create_account(
            session,
            customer_id=raj.id,
            account_number="10089012345",
            sort_code="839181",
            account_type="current",
            balance=Decimal("1875.66"),
            status="active",
            opened_date=date(2020, 2, 14),
        )
        get_or_create_account(
            session,
            customer_id=raj.id,
            account_number="60089012345",
            sort_code="839181",
            account_type="credit_card",
            balance=Decimal("-512.40"),
            status="active",
            opened_date=date(2020, 5, 2),
        )
        get_or_create_account(
            session,
            customer_id=elena.id,
            account_number="10090123456",
            sort_code="560036",
            account_type="current",
            balance=Decimal("640.10"),
            status="active",
            opened_date=date(2023, 1, 5),
        )
        get_or_create_account(
            session,
            customer_id=tom.id,
            account_number="20001234567",
            sort_code="608301",
            account_type="savings",
            balance=Decimal("150.00"),
            status="dormant",
            opened_date=date(2026, 1, 15),
        )

        # ---------- Source system records ----------
        fe_8891 = get_or_create_source_record(
            session,
            source_system="fraud_engine",
            source_ref="FE-2026-8891",
            record_type="transaction_alert",
            confidence_score=Decimal("87.40"),
            payload={
                "rules_fired": [
                    "foreign_atm_velocity",
                    "merchant_mismatch",
                    "night_time_spend",
                ],
                "risk_score": 87.4,
                "transactions": [
                    {
                        "amount": "1250.00",
                        "currency": "EUR",
                        "merchant": "Northlake Travel",
                        "country": "ES",
                    },
                    {
                        "amount": "2225.80",
                        "currency": "EUR",
                        "merchant": "Northlake Travel",
                        "country": "ES",
                    },
                ],
                "customer_location_at_alert": "GB",
            },
            generated_at=now - timedelta(days=4),
        )
        tm_1042 = get_or_create_source_record(
            session,
            source_system="transaction_monitoring",
            source_ref="TM-2026-1042",
            record_type="duplicate_payment_pattern",
            confidence_score=Decimal("72.10"),
            payload={
                "rules_fired": ["duplicate_amount_same_merchant"],
                "merchant": "Harbor Broadband",
                "duplicate_amount": "1240.00",
                "occurrences": 2,
                "window_days": 3,
            },
            generated_at=now - timedelta(days=9),
        )
        kyc_3310 = get_or_create_source_record(
            session,
            source_system="kyc_monitoring",
            source_ref="KYC-2026-3310",
            record_type="vulnerability_indicator",
            confidence_score=Decimal("91.00"),
            payload={
                "rules_fired": ["bereavement_indicator", "reduced_account_activity"],
                "vulnerability_type": "life_event",
                "evidence": "Bereavement notification processed; contact preferences flagged for sensitive handling.",
            },
            generated_at=now - timedelta(days=2),
        )
        fe_9055 = get_or_create_source_record(
            session,
            source_system="fraud_engine",
            source_ref="FE-2026-9055",
            record_type="transaction_alert",
            confidence_score=Decimal("64.25"),
            payload={
                "rules_fired": ["card_testing_pattern"],
                "risk_score": 64.25,
                "transactions": [
                    {"amount": "1.99", "merchant": "QuickPay Digital"},
                    {"amount": "89.99", "merchant": "QuickPay Digital"},
                ],
            },
            generated_at=now - timedelta(days=1),
        )
        kyc_3455 = get_or_create_source_record(
            session,
            source_system="kyc_monitoring",
            source_ref="KYC-2026-3455",
            record_type="kyc_review_overdue",
            confidence_score=Decimal("98.00"),
            payload={
                "rules_fired": ["kyc_expired_over_12_months"],
                "vulnerability_type": "resilience",
                "evidence": "KYC expired over 24 months ago; large balance with no recent review.",
            },
            generated_at=now - timedelta(days=10),
        )
        tm_1188 = get_or_create_source_record(
            session,
            source_system="transaction_monitoring",
            source_ref="TM-2026-1188",
            record_type="income_shock_pattern",
            confidence_score=Decimal("80.50"),
            payload={
                "rules_fired": ["salary_credit_stopped", "essential_spend_ratio_spike"],
                "vulnerability_type": "health",
                "evidence": "Regular salary credit absent for 3 months; increased reliance on credit.",
            },
            generated_at=now - timedelta(days=6),
        )
        tm_0920 = get_or_create_source_record(
            session,
            source_system="transaction_monitoring",
            source_ref="TM-2025-0920",
            record_type="capability_indicator",
            confidence_score=Decimal("75.00"),
            payload={
                "rules_fired": ["repeated_failed_payments", "assisted_channel_usage"],
                "vulnerability_type": "capability",
                "evidence": "Multiple failed direct debits and repeated assisted-service contacts.",
            },
            generated_at=now - timedelta(days=350),
        )
        fe_9120 = get_or_create_source_record(
            session,
            source_system="fraud_engine",
            source_ref="FE-2026-9120",
            record_type="transaction_alert",
            confidence_score=Decimal("79.90"),
            payload={
                "rules_fired": ["account_takeover_signal"],
                "risk_score": 79.9,
                "merchant": "Online Electronics Hub",
            },
            generated_at=now - timedelta(days=60),
        )

        # ---------- Cases ----------
        case_1001 = get_or_create_case(
            session,
            case_ref="CASE-1001",
            customer_id=aisha.id,
            case_type="fraud",
            status="under_investigation",
            priority="p1",
            assigned_user_id=investigator.id,
            disputed_amount=Decimal("3475.80"),
            merchant_name="Northlake Travel",
            consumer_duty_flag=True,
            description="Unrecognised card transactions in Spain flagged by the fraud engine with high confidence.",
            opened_date=now - timedelta(days=4),
        )
        case_1002 = get_or_create_case(
            session,
            case_ref="CASE-1002",
            customer_id=michael.id,
            case_type="dispute",
            status="pending_customer",
            priority="p2",
            assigned_user_id=support.id,
            disputed_amount=Decimal("1240.00"),
            merchant_name="Harbor Broadband",
            consumer_duty_flag=False,
            description="Duplicate payment after service cancellation; waiting on evidence from the customer.",
            opened_date=now - timedelta(days=9),
        )
        case_1003 = get_or_create_case(
            session,
            case_ref="CASE-1003",
            customer_id=priya.id,
            case_type="complaint",
            status="escalated",
            priority="p1",
            assigned_user_id=manager.id,
            disputed_amount=None,
            merchant_name=None,
            consumer_duty_flag=True,
            description="Customer with an active life-event vulnerability complained about insensitive collections contact.",
            opened_date=now - timedelta(days=2),
        )
        case_1004 = get_or_create_case(
            session,
            case_ref="CASE-1004",
            customer_id=david.id,
            case_type="fraud",
            status="open",
            priority="p2",
            assigned_user_id=investigator.id,
            disputed_amount=Decimal("89.99"),
            merchant_name="QuickPay Digital",
            consumer_duty_flag=False,
            description="Card-testing pattern detected; card frozen as a precaution pending customer contact.",
            opened_date=now - timedelta(days=1),
        )
        case_1005 = get_or_create_case(
            session,
            case_ref="CASE-1005",
            customer_id=fatima.id,
            case_type="complaint",
            status="resolved",
            priority="p4",
            assigned_user_id=support.id,
            disputed_amount=None,
            merchant_name=None,
            consumer_duty_flag=False,
            description="Complaint about branch waiting times; resolved with an apology and service recovery.",
            opened_date=now - timedelta(days=40),
        )
        case_1006 = get_or_create_case(
            session,
            case_ref="CASE-1006",
            customer_id=elena.id,
            case_type="complaint",
            status="pending_customer",
            priority="p2",
            assigned_user_id=manager.id,
            disputed_amount=None,
            merchant_name=None,
            consumer_duty_flag=True,
            description="Customer in financial difficulty disputes fees applied after her salary credits stopped.",
            opened_date=now - timedelta(days=6),
        )
        case_1007 = get_or_create_case(
            session,
            case_ref="CASE-1007",
            customer_id=raj.id,
            case_type="fraud",
            status="closed",
            priority="p3",
            assigned_user_id=investigator.id,
            disputed_amount=Decimal("512.40"),
            merchant_name="Online Electronics Hub",
            consumer_duty_flag=False,
            description="Account takeover attempt confirmed as genuine customer activity; refund issued and case closed.",
            opened_date=now - timedelta(days=60),
        )
        case_1008 = get_or_create_case(
            session,
            case_ref="CASE-1008",
            customer_id=raj.id,
            case_type="complaint",
            status="under_investigation",
            priority="p3",
            assigned_user_id=support.id,
            disputed_amount=None,
            merchant_name=None,
            consumer_duty_flag=False,
            description="Complaint about the time taken to resolve the earlier fraud case.",
            opened_date=now - timedelta(days=3),
        )

        # ---------- Vulnerability register ----------
        add_vulnerability_signal_if_missing(
            session,
            customer_id=priya.id,
            vulnerability_type="life_event",
            status="active",
            notes="Recent bereavement. Sensitive handling and adviser-led contact only.",
            source_record_id=kyc_3310.id,
            detected_at=now - timedelta(days=2),
            resolved_at=None,
        )
        add_vulnerability_signal_if_missing(
            session,
            customer_id=george.id,
            vulnerability_type="resilience",
            status="active",
            notes="KYC expired over 24 months; large balances with no recent review. Possible financial resilience risk.",
            source_record_id=kyc_3455.id,
            detected_at=now - timedelta(days=10),
            resolved_at=None,
        )
        add_vulnerability_signal_if_missing(
            session,
            customer_id=elena.id,
            vulnerability_type="health",
            status="active",
            notes="Salary credits stopped three months ago; pattern suggests health-related income shock.",
            source_record_id=tm_1188.id,
            detected_at=now - timedelta(days=6),
            resolved_at=None,
        )
        add_vulnerability_signal_if_missing(
            session,
            customer_id=fatima.id,
            vulnerability_type="capability",
            status="resolved",
            notes="Digital capability support completed; customer now banking independently.",
            source_record_id=tm_0920.id,
            detected_at=now - timedelta(days=350),
            resolved_at=now - timedelta(days=120),
        )

        # ---------- Case events (system-generated by default) ----------
        add_case_event_if_missing(
            session,
            case_id=case_1001.id,
            event_type="system_alert",
            event_description="Fraud engine flagged foreign ATM velocity and merchant mismatch with a risk score of 87.4.",
            created_by_user_id=None,
            created_by_system="fraud_engine",
            source_record_id=fe_8891.id,
            created_at=now - timedelta(days=4),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1001.id,
            event_type="status_change",
            event_description="Status changed to under_investigation: fraud patterns confirmed, contacting merchant acquirer.",
            created_by_user_id=investigator.id,
            created_by_system=None,
            source_record_id=None,
            created_at=now - timedelta(days=3),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1002.id,
            event_type="system_alert",
            event_description="Transaction monitoring detected a duplicate payment pattern at Harbor Broadband.",
            created_by_user_id=None,
            created_by_system="transaction_monitoring",
            source_record_id=tm_1042.id,
            created_at=now - timedelta(days=9),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1002.id,
            event_type="customer_contact",
            event_description="Customer asked for confirmation that the duplicate payment dispute is being reviewed.",
            created_by_user_id=support.id,
            created_by_system=None,
            source_record_id=None,
            created_at=now - timedelta(days=1),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1003.id,
            event_type="system_alert",
            event_description="KYC monitoring raised a life-event vulnerability indicator requiring sensitive handling.",
            created_by_user_id=None,
            created_by_system="kyc_monitoring",
            source_record_id=kyc_3310.id,
            created_at=now - timedelta(days=2),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1003.id,
            event_type="escalation",
            event_description="Escalated to case management for Consumer Duty review before any further customer contact.",
            created_by_user_id=manager.id,
            created_by_system=None,
            source_record_id=None,
            created_at=now - timedelta(hours=8),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1004.id,
            event_type="system_alert",
            event_description="Fraud engine detected a card-testing pattern; card frozen automatically.",
            created_by_user_id=None,
            created_by_system="fraud_engine",
            source_record_id=fe_9055.id,
            created_at=now - timedelta(days=1),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1005.id,
            event_type="status_change",
            event_description="Status changed to resolved: apology issued and service recovery payment made.",
            created_by_user_id=manager.id,
            created_by_system=None,
            source_record_id=None,
            created_at=now - timedelta(days=35),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1006.id,
            event_type="system_alert",
            event_description="Transaction monitoring detected an income-shock pattern consistent with financial difficulty.",
            created_by_user_id=None,
            created_by_system="transaction_monitoring",
            source_record_id=tm_1188.id,
            created_at=now - timedelta(days=6),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1007.id,
            event_type="system_alert",
            event_description="Fraud engine raised an account takeover signal for an online electronics purchase.",
            created_by_user_id=None,
            created_by_system="fraud_engine",
            source_record_id=fe_9120.id,
            created_at=now - timedelta(days=60),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1007.id,
            event_type="status_change",
            event_description="Status changed to closed: customer confirmed the transaction; refund issued.",
            created_by_user_id=investigator.id,
            created_by_system=None,
            source_record_id=None,
            created_at=now - timedelta(days=45),
        )
        add_case_event_if_missing(
            session,
            case_id=case_1008.id,
            event_type="note",
            event_description="Complaint logged regarding handling time of the previous fraud case.",
            created_by_user_id=support.id,
            created_by_system=None,
            source_record_id=None,
            created_at=now - timedelta(days=3),
        )

        # ---------- Next actions ----------
        add_next_action_if_missing(
            session,
            case_id=case_1001.id,
            action_type="escalate_fraud",
            description="Escalate the suspected merchant abuse pattern to specialist fraud operations.",
            due_date=now - timedelta(days=1),
            status="open",
            assigned_user_id=investigator.id,
            created_by_user_id=investigator.id,
        )
        add_next_action_if_missing(
            session,
            case_id=case_1001.id,
            action_type="contact_customer",
            description="Confirm travel plans and verify the flagged transactions with the customer.",
            due_date=now + timedelta(days=1),
            status="in_progress",
            assigned_user_id=investigator.id,
            created_by_user_id=investigator.id,
        )
        add_next_action_if_missing(
            session,
            case_id=case_1002.id,
            action_type="request_documents",
            description="Request the merchant cancellation confirmation and bank statement evidence.",
            due_date=now + timedelta(days=2),
            status="in_progress",
            assigned_user_id=support.id,
            created_by_user_id=support.id,
        )
        add_next_action_if_missing(
            session,
            case_id=case_1003.id,
            action_type="escalate_vulnerability",
            description="Confirm sensitive-handling plan with the vulnerability support team.",
            due_date=now + timedelta(days=1),
            status="open",
            assigned_user_id=manager.id,
            created_by_user_id=manager.id,
        )
        add_next_action_if_missing(
            session,
            case_id=case_1003.id,
            action_type="kyc_refresh",
            description="Refresh the customer profile and record updated contact preferences.",
            due_date=now + timedelta(days=3),
            status="open",
            assigned_user_id=manager.id,
            created_by_user_id=manager.id,
        )
        add_next_action_if_missing(
            session,
            case_id=case_1004.id,
            action_type="contact_customer",
            description="Verify the QuickPay Digital transactions and confirm whether to reissue the card.",
            due_date=now + timedelta(days=2),
            status="open",
            assigned_user_id=investigator.id,
            created_by_user_id=investigator.id,
        )
        add_next_action_if_missing(
            session,
            case_id=case_1005.id,
            action_type="add_case_note",
            description="Record the service recovery payment reference on the case.",
            due_date=now - timedelta(days=35),
            status="completed",
            assigned_user_id=support.id,
            created_by_user_id=support.id,
            completed_at=now - timedelta(days=34),
        )
        add_next_action_if_missing(
            session,
            case_id=case_1006.id,
            action_type="contact_customer",
            description="Discuss a fee refund and affordable repayment options with the customer.",
            due_date=now + timedelta(days=4),
            status="open",
            assigned_user_id=manager.id,
            created_by_user_id=manager.id,
        )
        add_next_action_if_missing(
            session,
            case_id=case_1007.id,
            action_type="issue_refund",
            description="Issue the £512.40 refund for the confirmed transaction.",
            due_date=now - timedelta(days=50),
            status="completed",
            assigned_user_id=investigator.id,
            created_by_user_id=investigator.id,
            completed_at=now - timedelta(days=48),
        )
        add_next_action_if_missing(
            session,
            case_id=case_1008.id,
            action_type="request_documents",
            description="Collect the timeline of the previous fraud case for the complaint review.",
            due_date=now + timedelta(days=5),
            status="open",
            assigned_user_id=support.id,
            created_by_user_id=support.id,
        )

        session.commit()
        print("Seeded NatWest business data.")


if __name__ == "__main__":
    seed_business_data()
