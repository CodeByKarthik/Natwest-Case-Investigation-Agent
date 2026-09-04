from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from natwest_shared.db.models.business import Account, Customer, Issue, IssueUpdate, NextAction
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
    primary_account_number: str,
    primary_sort_code: str,
    customer_since: date,
    kyc_status: str,
    vulnerability_flag: bool,
    vulnerability_type: str | None,
    vulnerability_notes: str | None,
    tier: str,
) -> Customer:
    existing = session.scalar(
        select(Customer).where(Customer.primary_account_number == primary_account_number)
    )

    if existing is not None:
        return existing

    customer = Customer(
        full_name=full_name,
        date_of_birth=date_of_birth,
        primary_account_number=primary_account_number,
        primary_sort_code=primary_sort_code,
        customer_since=customer_since,
        kyc_status=kyc_status,
        vulnerability_flag=vulnerability_flag,
        vulnerability_type=vulnerability_type,
        vulnerability_notes=vulnerability_notes,
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
    existing = session.scalar(select(Account).where(Account.account_number == account_number))

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


def get_or_create_case(
    session: Session,
    *,
    case_ref: str,
    customer_id: UUID,
    case_type: str,
    status: str,
    priority: str,
    opened_date: datetime,
    assigned_team: str,
    assigned_user_id: UUID | None,
    disputed_amount: Decimal | None,
    merchant_name: str | None,
    merchant_category: str | None,
    consumer_duty_flag: bool,
    description: str,
) -> Issue:
    existing = session.scalar(select(Issue).where(Issue.case_ref == case_ref))

    if existing is not None:
        return existing

    case = Issue(
        customer_id=customer_id,
        case_ref=case_ref,
        case_type=case_type,
        status=status,
        priority=priority,
        opened_date=opened_date,
        assigned_team=assigned_team,
        assigned_user_id=assigned_user_id,
        disputed_amount=disputed_amount,
        merchant_name=merchant_name,
        merchant_category=merchant_category,
        consumer_duty_flag=consumer_duty_flag,
        description=description,
    )

    session.add(case)
    session.flush()
    return case


def add_case_event_if_missing(
    session: Session,
    *,
    case_id: UUID,
    event_type: str,
    event_description: str,
    is_internal: bool,
    created_by_user_id: UUID | None,
    created_by_name: str | None,
    created_by_role: str | None,
    created_at: datetime,
) -> None:
    existing = session.scalar(
        select(IssueUpdate).where(
            IssueUpdate.case_id == case_id,
            IssueUpdate.event_description == event_description,
        )
    )

    if existing is not None:
        return

    session.add(
        IssueUpdate(
            case_id=case_id,
            event_type=event_type,
            event_description=event_description,
            is_internal=is_internal,
            created_by_user_id=created_by_user_id,
            created_by_name=created_by_name,
            created_by_role=created_by_role,
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
    created_by_role: str | None,
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
            created_by_role=created_by_role,
        )
    )


def seed_business_data() -> None:
    now = datetime.now(UTC)

    with SessionLocal() as session:
        customer_support_user = get_user_by_username(session, "customer_support")
        fraud_investigator_user = get_user_by_username(session, "fraud_investigator")
        compliance_officer_user = get_user_by_username(session, "compliance_officer")

        aisha = get_or_create_customer(
            session,
            full_name="Aisha Rahman",
            date_of_birth=date(1988, 6, 14),
            primary_account_number="1234567890",
            primary_sort_code="040004",
            customer_since=date(2018, 2, 1),
            kyc_status="verified",
            vulnerability_flag=False,
            vulnerability_type=None,
            vulnerability_notes=None,
            tier="premium",
        )

        michael = get_or_create_customer(
            session,
            full_name="Michael Osei",
            date_of_birth=date(1992, 11, 7),
            primary_account_number="2345678901",
            primary_sort_code="112233",
            customer_since=date(2021, 8, 15),
            kyc_status="pending_review",
            vulnerability_flag=False,
            vulnerability_type=None,
            vulnerability_notes=None,
            tier="standard",
        )

        priya = get_or_create_customer(
            session,
            full_name="Priya Nair",
            date_of_birth=date(1979, 3, 26),
            primary_account_number="3456789012",
            primary_sort_code="203040",
            customer_since=date(2015, 6, 10),
            kyc_status="verified",
            vulnerability_flag=True,
            vulnerability_type="life_event",
            vulnerability_notes="Recent bereavement and reduced financial resilience.",
            tier="private_banking",
        )

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
            customer_id=michael.id,
            account_number="10023456789",
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
            status="restricted",
            opened_date=date(2015, 6, 10),
        )

        case_1001 = get_or_create_case(
            session,
            case_ref="CASE-1001",
            customer_id=aisha.id,
            case_type="fraud",
            status="under_investigation",
            priority="p1",
            opened_date=now - timedelta(days=4),
            assigned_team="fraud",
            assigned_user_id=fraud_investigator_user.id,
            disputed_amount=Decimal("3475.80"),
            merchant_name="Northlake Travel",
            merchant_category="travel",
            consumer_duty_flag=True,
            description="Unrecognised card transactions in the customer travel profile after an ATM withdrawal in Spain.",
        )

        case_1002 = get_or_create_case(
            session,
            case_ref="CASE-1002",
            customer_id=michael.id,
            case_type="complaint",
            status="pending_customer",
            priority="p2",
            opened_date=now - timedelta(days=9),
            assigned_team="customer_support",
            assigned_user_id=customer_support_user.id,
            disputed_amount=Decimal("1240.00"),
            merchant_name="Harbor Broadband",
            merchant_category="utilities",
            consumer_duty_flag=False,
            description="Customer disputes a duplicate payment after service cancellation and is waiting on evidence from the merchant.",
        )

        case_1003 = get_or_create_case(
            session,
            case_ref="CASE-1003",
            customer_id=priya.id,
            case_type="vulnerability_review",
            status="escalated",
            priority="p1",
            opened_date=now - timedelta(days=2),
            assigned_team="compliance",
            assigned_user_id=compliance_officer_user.id,
            disputed_amount=None,
            merchant_name=None,
            merchant_category=None,
            consumer_duty_flag=False,
            description="Customer has a documented vulnerability and needs a compliance review before any outbound action is taken.",
        )

        add_case_event_if_missing(
            session,
            case_id=case_1001.id,
            event_type="status_change",
            event_description="Case moved to under investigation after initial fraud screening flagged a pattern of foreign transactions.",
            is_internal=True,
            created_by_user_id=fraud_investigator_user.id,
            created_by_name="Fraud Investigator User",
            created_by_role="fraud_investigator",
            created_at=now - timedelta(days=3),
        )

        add_case_event_if_missing(
            session,
            case_id=case_1002.id,
            event_type="customer_contact",
            event_description="Customer asked for confirmation that the merchant dispute was being reviewed and requested a short update timeline.",
            is_internal=False,
            created_by_user_id=customer_support_user.id,
            created_by_name="Customer Support User",
            created_by_role="customer_support",
            created_at=now - timedelta(days=1),
        )

        add_case_event_if_missing(
            session,
            case_id=case_1003.id,
            event_type="escalation",
            event_description="Compliance team requested a full vulnerability review and specialist handling plan before any case action.",
            is_internal=True,
            created_by_user_id=compliance_officer_user.id,
            created_by_name="Compliance Officer User",
            created_by_role="compliance_officer",
            created_at=now - timedelta(hours=8),
        )

        add_next_action_if_missing(
            session,
            case_id=case_1001.id,
            action_type="escalate_fraud",
            description="Escalate the suspected merchant abuse pattern to the specialist fraud operations team and request a merchant review.",
            due_date=now + timedelta(days=1),
            status="open",
            assigned_user_id=fraud_investigator_user.id,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator",
        )

        add_next_action_if_missing(
            session,
            case_id=case_1002.id,
            action_type="request_documents",
            description="Request the merchant cancellation confirmation and bank statement evidence from the customer.",
            due_date=now + timedelta(days=3),
            status="in_progress",
            assigned_user_id=customer_support_user.id,
            created_by_user_id=customer_support_user.id,
            created_by_role="customer_support",
        )

        add_next_action_if_missing(
            session,
            case_id=case_1003.id,
            action_type="kyc_refresh",
            description="Complete the vulnerability review, refresh the customer profile, and confirm adviser-led handling before any next action.",
            due_date=now + timedelta(days=2),
            status="open",
            assigned_user_id=compliance_officer_user.id,
            created_by_user_id=compliance_officer_user.id,
            created_by_role="compliance_officer",
        )

        session.commit()
        print("Seeded NatWest business data.")


if __name__ == "__main__":
    seed_business_data()