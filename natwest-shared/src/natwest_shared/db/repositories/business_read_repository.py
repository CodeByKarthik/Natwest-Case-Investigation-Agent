from uuid import UUID

from natwest_shared.db.models.business import (
    Account,
    Case,
    CaseEvent,
    Customer,
    NextAction,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


class BusinessReadRepository:
    """Repository for read-only customer, case, event, and next-action queries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_customers(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Customer]:
        stmt = (
            select(Customer)
            .order_by(Customer.full_name.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())

    def get_customer_by_name(
        self,
        *,
        name: str,
    ) -> Customer | None:
        stmt = (
            select(Customer)
            .where(Customer.full_name.ilike(f"%{name}%"))
            .order_by(Customer.full_name.asc())
        )
        return self.session.scalar(stmt)

    def get_customer_profile(self, *, customer_id: UUID) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def get_customer_accounts(self, *, customer_id: UUID) -> list[Account]:
        stmt = (
            select(Account)
            .where(Account.customer_id == customer_id)
            .order_by(Account.opened_date.desc(), Account.account_number.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_cases(
        self,
        *,
        filters: dict[str, object] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Case]:
        stmt = select(Case)

        if filters:
            if filters.get("status") is not None:
                stmt = stmt.where(Case.status == filters["status"])
            if filters.get("priority") is not None:
                stmt = stmt.where(Case.priority == filters["priority"])
            if filters.get("assigned_team") is not None:
                stmt = stmt.where(Case.assigned_team == filters["assigned_team"])
            if filters.get("assigned_user_id") is not None:
                stmt = stmt.where(Case.assigned_user_id == filters["assigned_user_id"])
            if filters.get("case_type") is not None:
                stmt = stmt.where(Case.case_type == filters["case_type"])
            if filters.get("customer_id") is not None:
                stmt = stmt.where(Case.customer_id == filters["customer_id"])
            if filters.get("consumer_duty_flag") is not None:
                stmt = stmt.where(
                    Case.consumer_duty_flag.is_(filters["consumer_duty_flag"])
                )

        stmt = stmt.order_by(Case.last_updated.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())

    def get_case_details(
        self, *, case_id: UUID | None = None, case_ref: str | None = None
    ) -> Case | None:
        if case_id is not None:
            return self.session.get(Case, case_id)
        if case_ref is not None:
            return self.session.scalar(select(Case).where(Case.case_ref == case_ref))
        return None

    def get_case_timeline(self, *, case_id: UUID) -> list[CaseEvent]:
        stmt = (
            select(CaseEvent)
            .where(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def get_next_actions(self, *, case_id: UUID) -> list[NextAction]:
        stmt = (
            select(NextAction)
            .where(NextAction.case_id == case_id)
            .order_by(
                NextAction.due_date.asc().nulls_last(), NextAction.created_at.desc()
            )
        )
        return list(self.session.scalars(stmt).all())

    def list_open_issues(
        self,
        *,
        customer_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Case]:
        stmt = (
            select(Case)
            .where(Case.customer_id == customer_id)
            .where(
                Case.status.in_(
                    ["open", "under_investigation", "pending_customer", "escalated"]
                )
            )
            .order_by(Case.priority.asc(), Case.last_updated.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt).all())

    def get_issue_by_external_ref(self, *, external_ref: str) -> Case | None:
        return self.session.scalar(select(Case).where(Case.case_ref == external_ref))

    def list_issue_updates(
        self,
        *,
        issue_id: UUID,
        customer_visible_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CaseEvent]:
        stmt = (
            select(CaseEvent)
            .where(CaseEvent.case_id == issue_id)
            .order_by(CaseEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if customer_visible_only:
            stmt = stmt.where(CaseEvent.is_internal.is_(False))
        return list(self.session.scalars(stmt).all())

    def list_next_actions(
        self,
        *,
        issue_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NextAction]:
        stmt = (
            select(NextAction)
            .where(NextAction.case_id == issue_id)
            .order_by(
                NextAction.due_date.asc().nulls_last(), NextAction.created_at.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            stmt = stmt.where(NextAction.status == status)
        return list(self.session.scalars(stmt).all())
