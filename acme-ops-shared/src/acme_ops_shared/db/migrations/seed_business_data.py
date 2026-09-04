from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from acme_ops_shared.common.enums import (
    CustomerHealthEnum,
    CustomerTierEnum,
    IssuePriorityEnum,
    IssueStatusEnum,
    NextActionStatusEnum,
    NextActionTypeEnum,
)
from acme_ops_shared.db.models.business import Customer, Issue, IssueUpdate, NextAction
from acme_ops_shared.db.models.user import AppUser
from acme_ops_shared.db.session import SessionLocal


def get_user_by_username(session: Session, username: str) -> AppUser:
    user = session.scalar(select(AppUser).where(AppUser.username == username))

    if user is None:
        raise RuntimeError(
            f"Required seed user '{username}' not found. "
            "Run seed_user_data before seed_business_data."
        )

    return user


def get_or_create_customer(
    session: Session,
    *,
    name: str,
    industry: str,
    tier: CustomerTierEnum,
    health_status: CustomerHealthEnum,
    account_owner_user_id: UUID | None,
    contract_value: Decimal,
    notes: str,
) -> Customer:
    existing = session.scalar(select(Customer).where(Customer.name == name))

    if existing is not None:
        return existing

    customer = Customer(
        name=name,
        industry=industry,
        tier=tier,
        health_status=health_status,
        account_owner_user_id=account_owner_user_id,
        contract_value=contract_value,
        notes=notes,
    )

    session.add(customer)
    session.flush()

    return customer


def get_or_create_issue(
    session: Session,
    *,
    external_ref: str,
    customer_id: UUID,
    title: str,
    description: str,
    status: IssueStatusEnum,
    priority: IssuePriorityEnum,
    assigned_to_user_id: UUID | None,
    source_system: str,
    opened_at: datetime,
    due_at: datetime | None,
) -> Issue:
    existing = session.scalar(select(Issue).where(Issue.external_ref == external_ref))

    if existing is not None:
        return existing

    issue = Issue(
        external_ref=external_ref,
        customer_id=customer_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        assigned_to_user_id=assigned_to_user_id,
        source_system=source_system,
        opened_at=opened_at,
        due_at=due_at,
    )

    session.add(issue)
    session.flush()

    return issue


def add_issue_update_if_missing(
    session: Session,
    *,
    issue_id: UUID,
    author_user_id: UUID | None,
    author_name: str,
    author_role: str,
    update_text: str,
    is_customer_visible: bool,
    created_at: datetime,
) -> None:
    existing = session.scalar(
        select(IssueUpdate).where(
            IssueUpdate.issue_id == issue_id,
            IssueUpdate.update_text == update_text,
        )
    )

    if existing is not None:
        return

    session.add(
        IssueUpdate(
            issue_id=issue_id,
            author_user_id=author_user_id,
            author_name=author_name,
            author_role=author_role,
            update_text=update_text,
            is_customer_visible=is_customer_visible,
            created_at=created_at,
        )
    )


def add_next_action_if_missing(
    session: Session,
    *,
    issue_id: UUID,
    action_type: NextActionTypeEnum,
    action_text: str,
    owner_user_id: UUID | None,
    due_at: datetime | None,
    status: NextActionStatusEnum,
    created_by_user_id: UUID | None,
    created_by_role: str,
) -> None:
    existing = session.scalar(
        select(NextAction).where(
            NextAction.issue_id == issue_id,
            NextAction.action_text == action_text,
        )
    )

    if existing is not None:
        return

    session.add(
        NextAction(
            issue_id=issue_id,
            action_type=action_type,
            action_text=action_text,
            owner_user_id=owner_user_id,
            due_at=due_at,
            status=status,
            created_by_user_id=created_by_user_id,
            created_by_role=created_by_role,
        )
    )


def seed_business_data() -> None:
    now = datetime.now(UTC)

    with SessionLocal() as session:
        customer_fraud_investigator_user = get_user_by_username(session, "customer_support")
        fraud_investigator_user = get_user_by_username(session, "fraud_investigator")
        compliance_officer_user = get_user_by_username(session, "compliance_officer")

        globex = get_or_create_customer(
            session,
            name="Globex Corporation",
            industry="Financial Services",
            tier=CustomerTierEnum.ENTERPRISE,
            health_status=CustomerHealthEnum.AT_RISK,
            account_owner_user_id=customer_fraud_investigator_user.id,
            contract_value=Decimal("250000.00"),
            notes=(
                "Strategic enterprise customer. Executive team is sensitive "
                "to support delays."
            ),
        )

        initech = get_or_create_customer(
            session,
            name="Initech",
            industry="Technology",
            tier=CustomerTierEnum.MID_MARKET,
            health_status=CustomerHealthEnum.HEALTHY,
            account_owner_user_id=customer_fraud_investigator_user.id,
            contract_value=Decimal("85000.00"),
            notes="Generally healthy account with moderate product usage growth.",
        )

        umbrella = get_or_create_customer(
            session,
            name="Umbrella Retail",
            industry="Retail",
            tier=CustomerTierEnum.ENTERPRISE,
            health_status=CustomerHealthEnum.WATCH,
            account_owner_user_id=customer_fraud_investigator_user.id,
            contract_value=Decimal("175000.00"),
            notes=(
                "Expansion opportunity, but recent integration issues need "
                "close monitoring."
            ),
        )

        stark = get_or_create_customer(
            session,
            name="Stark Industries",
            industry="Manufacturing",
            tier=CustomerTierEnum.ENTERPRISE,
            health_status=CustomerHealthEnum.CRITICAL,
            account_owner_user_id=customer_fraud_investigator_user.id,
            contract_value=Decimal("420000.00"),
            notes=(
                "High-value enterprise customer. Current outage is affecting "
                "executive dashboards and renewal confidence."
            ),
        )

        wayne = get_or_create_customer(
            session,
            name="Wayne Enterprises",
            industry="Logistics",
            tier=CustomerTierEnum.ENTERPRISE,
            health_status=CustomerHealthEnum.HEALTHY,
            account_owner_user_id=customer_fraud_investigator_user.id,
            contract_value=Decimal("310000.00"),
            notes=(
                "Stable enterprise customer with strong adoption and no major "
                "active escalations."
            ),
        )

        wonka = get_or_create_customer(
            session,
            name="Wonka Foods",
            industry="Food Manufacturing",
            tier=CustomerTierEnum.SMB,
            health_status=CustomerHealthEnum.WATCH,
            account_owner_user_id=customer_fraud_investigator_user.id,
            contract_value=Decimal("32000.00"),
            notes=(
                "Smaller account with intermittent operational issues and "
                "limited technical capacity."
            ),
        )

        cyberdyne = get_or_create_customer(
            session,
            name="Cyberdyne Systems",
            industry="Industrial Automation",
            tier=CustomerTierEnum.MID_MARKET,
            health_status=CustomerHealthEnum.AT_RISK,
            account_owner_user_id=customer_fraud_investigator_user.id,
            contract_value=Decimal("125000.00"),
            notes=(
                "Account is at risk due to repeated integration incidents and "
                "slow resolution cycles."
            ),
        )

        issue_101 = get_or_create_issue(
            session,
            external_ref="ISSUE-101",
            customer_id=globex.id,
            title="Billing exports failing for enterprise finance team",
            description=(
                "Scheduled billing exports are timing out before completion. "
                "Customer finance team cannot close monthly reporting."
            ),
            status=IssueStatusEnum.OPEN,
            priority=IssuePriorityEnum.P1,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=2),
            due_at=now + timedelta(days=1),
        )

        issue_102 = get_or_create_issue(
            session,
            external_ref="ISSUE-102",
            customer_id=globex.id,
            title="SSO login failures after certificate rotation",
            description=(
                "Several Globex users cannot authenticate through SAML SSO "
                "after the customer rotated their identity provider certificate."
            ),
            status=IssueStatusEnum.IN_PROGRESS,
            priority=IssuePriorityEnum.P2,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=5),
            due_at=now + timedelta(days=3),
        )

        issue_201 = get_or_create_issue(
            session,
            external_ref="ISSUE-201",
            customer_id=initech.id,
            title="Dashboard filters slow on large date ranges",
            description=(
                "Customer reports that dashboard filtering becomes slow when "
                "using date ranges longer than six months."
            ),
            status=IssueStatusEnum.OPEN,
            priority=IssuePriorityEnum.P3,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=1),
            due_at=now + timedelta(days=7),
        )

        issue_301 = get_or_create_issue(
            session,
            external_ref="ISSUE-301",
            customer_id=umbrella.id,
            title="Inventory sync delayed for regional stores",
            description=(
                "Inventory updates from regional stores are delayed before "
                "appearing in the operations dashboard."
            ),
            status=IssueStatusEnum.BLOCKED,
            priority=IssuePriorityEnum.P2,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=4),
            due_at=now + timedelta(days=2),
        )

        issue_401 = get_or_create_issue(
            session,
            external_ref="ISSUE-401",
            customer_id=stark.id,
            title="Executive analytics dashboard unavailable",
            description=(
                "Executive analytics dashboard returns 503 errors for all "
                "Stark Industries admin users."
            ),
            status=IssueStatusEnum.OPEN,
            priority=IssuePriorityEnum.P1,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(hours=10),
            due_at=now + timedelta(hours=6),
        )

        issue_402 = get_or_create_issue(
            session,
            external_ref="ISSUE-402",
            customer_id=stark.id,
            title="Webhook delivery failures to manufacturing systems",
            description=(
                "Webhook events are failing intermittently, delaying downstream "
                "manufacturing workflow updates."
            ),
            status=IssueStatusEnum.IN_PROGRESS,
            priority=IssuePriorityEnum.P2,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=3),
            due_at=now + timedelta(days=1),
        )

        issue_501 = get_or_create_issue(
            session,
            external_ref="ISSUE-501",
            customer_id=wayne.id,
            title="Archived shipment reports missing from export UI",
            description=(
                "Older shipment reports are not visible in the export UI, but "
                "API access still works."
            ),
            status=IssueStatusEnum.RESOLVED,
            priority=IssuePriorityEnum.P4,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=12),
            due_at=now - timedelta(days=7),
        )

        issue_601 = get_or_create_issue(
            session,
            external_ref="ISSUE-601",
            customer_id=wonka.id,
            title="Order notification emails delayed",
            description=(
                "Order notification emails are delayed by up to forty minutes "
                "during evening processing windows."
            ),
            status=IssueStatusEnum.OPEN,
            priority=IssuePriorityEnum.P3,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=2),
            due_at=now + timedelta(days=5),
        )

        issue_701 = get_or_create_issue(
            session,
            external_ref="ISSUE-701",
            customer_id=cyberdyne.id,
            title="Device telemetry ingestion backlog",
            description=(
                "Telemetry ingestion is falling behind during peak batch upload "
                "windows, causing delayed operational alerts."
            ),
            status=IssueStatusEnum.BLOCKED,
            priority=IssuePriorityEnum.P1,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=6),
            due_at=now - timedelta(hours=4),
        )

        issue_702 = get_or_create_issue(
            session,
            external_ref="ISSUE-702",
            customer_id=cyberdyne.id,
            title="Duplicate alerts generated for resolved incidents",
            description=(
                "Resolved incidents sometimes generate duplicate alerts after "
                "device reconnect events."
            ),
            status=IssueStatusEnum.OPEN,
            priority=IssuePriorityEnum.P3,
            assigned_to_user_id=fraud_investigator_user.id,
            source_system="natwest-support",
            opened_at=now - timedelta(days=1),
            due_at=now + timedelta(days=4),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_101.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Confirmed export job timeout in production logs. Customer is "
                "blocked on month-end finance reporting."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(days=2, hours=-2),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_101.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Temporary workaround identified, but customer has not confirmed "
                "whether the workaround satisfies finance reporting requirements."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(days=1),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_101.id,
            author_user_id=compliance_officer_user.id,
            author_name="Anita Admin",
            author_role="compliance_officer",
            update_text=(
                "Executive update requested because this is a P1 issue on an "
                "at-risk enterprise account."
            ),
            is_customer_visible=False,
            created_at=now - timedelta(hours=12),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_102.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Initial investigation points to a SAML certificate mismatch. "
                "Waiting for customer IdP metadata confirmation."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(days=4),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_201.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Reproduced dashboard slowdown using a nine-month date range. "
                "Need to inspect query performance logs."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(hours=20),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_301.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text="Issue is blocked pending store connector logs from the customer.",
            is_customer_visible=True,
            created_at=now - timedelta(days=3),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_401.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Confirmed dashboard API is returning 503 errors across all "
                "Stark admin workspaces."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(hours=8),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_401.id,
            author_user_id=compliance_officer_user.id,
            author_name="Anita Admin",
            author_role="compliance_officer",
            update_text=(
                "Incident review opened. Engineering escalation required because "
                "customer executives are directly impacted."
            ),
            is_customer_visible=False,
            created_at=now - timedelta(hours=6),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_402.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Webhook retry logs show elevated 429 responses from the customer "
                "endpoint during batch windows."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(days=2),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_501.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Report index was rebuilt and archived shipment exports are now "
                "visible in the UI."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(days=8),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_601.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Email queue delay appears correlated with evening batch order "
                "processing volume."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(days=1, hours=8),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_701.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Telemetry backlog exceeded alert threshold. Customer needs to "
                "provide latest device batch logs before ingestion tuning can continue."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(days=5),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_701.id,
            author_user_id=compliance_officer_user.id,
            author_name="Anita Admin",
            author_role="compliance_officer",
            update_text=(
                "SLA risk flagged because the issue is past due and affects "
                "operational alerting."
            ),
            is_customer_visible=False,
            created_at=now - timedelta(hours=10),
        )

        add_issue_update_if_missing(
            session,
            issue_id=issue_702.id,
            author_user_id=fraud_investigator_user.id,
            author_name="Sam Support",
            author_role="fraud_investigator_user",
            update_text=(
                "Duplicate alerts reproduced after forced reconnect. Need event "
                "deduplication review."
            ),
            is_customer_visible=True,
            created_at=now - timedelta(hours=18),
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_101.id,
            action_type=NextActionTypeEnum.CUSTOMER_UPDATE,
            action_text=(
                "Send Globex a concise status update covering impact, workaround "
                "status, and next engineering step."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now + timedelta(hours=8),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=compliance_officer_user.id,
            created_by_role="compliance_officer",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_201.id,
            action_type=NextActionTypeEnum.TECHNICAL_INVESTIGATION,
            action_text=(
                "Review dashboard query performance logs and confirm whether "
                "caching should be adjusted."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now + timedelta(days=2),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator_user",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_301.id,
            action_type=NextActionTypeEnum.CUSTOMER_UPDATE,
            action_text=(
                "Request regional store connector logs from Umbrella Retail "
                "operations team."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now + timedelta(hours=12),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator_user",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_401.id,
            action_type=NextActionTypeEnum.ENGINEERING_ESCALATION,
            action_text=(
                "Escalate dashboard 503 errors to engineering incident owner "
                "and request mitigation plan within four hours."
            ),
            owner_user_id=compliance_officer_user.id,
            due_at=now + timedelta(hours=4),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=compliance_officer_user.id,
            created_by_role="compliance_officer",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_401.id,
            action_type=NextActionTypeEnum.ACCOUNT_ESCALATION,
            action_text=(
                "Prepare executive-facing incident update for Stark Industries "
                "account sponsor."
            ),
            owner_user_id=customer_fraud_investigator_user.id,
            due_at=now + timedelta(hours=3),
            status=NextActionStatusEnum.IN_PROGRESS,
            created_by_user_id=compliance_officer_user.id,
            created_by_role="compliance_officer",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_402.id,
            action_type=NextActionTypeEnum.TECHNICAL_INVESTIGATION,
            action_text=(
                "Compare webhook retry volume with customer endpoint rate limits "
                "and recommend retry policy adjustment."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now + timedelta(days=1),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator_user",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_501.id,
            action_type=NextActionTypeEnum.CUSTOMER_UPDATE,
            action_text=(
                "Confirm with Wayne Enterprises that archived shipment exports "
                "are visible and close the customer loop."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now - timedelta(days=6),
            status=NextActionStatusEnum.COMPLETED,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator_user",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_601.id,
            action_type=NextActionTypeEnum.TECHNICAL_INVESTIGATION,
            action_text=(
                "Inspect email queue metrics during evening processing and "
                "identify whether worker scaling is required."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now + timedelta(days=2),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator_user",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_701.id,
            action_type=NextActionTypeEnum.SLA_REVIEW,
            action_text=(
                "Review SLA exposure for Cyberdyne because telemetry ingestion "
                "is past due and blocked on customer logs."
            ),
            owner_user_id=compliance_officer_user.id,
            due_at=now + timedelta(hours=2),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=compliance_officer_user.id,
            created_by_role="compliance_officer",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_701.id,
            action_type=NextActionTypeEnum.CUSTOMER_UPDATE,
            action_text=(
                "Ask Cyberdyne for latest device batch logs and confirm expected "
                "delivery time."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now + timedelta(hours=6),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator_user",
        )

        add_next_action_if_missing(
            session,
            issue_id=issue_702.id,
            action_type=NextActionTypeEnum.TECHNICAL_INVESTIGATION,
            action_text=(
                "Review duplicate alert generation after device reconnect and "
                "propose deduplication fix."
            ),
            owner_user_id=fraud_investigator_user.id,
            due_at=now + timedelta(days=3),
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=fraud_investigator_user.id,
            created_by_role="fraud_investigator_user",
        )

        session.commit()

    print("Seeded business data.")


if __name__ == "__main__":
    seed_business_data()