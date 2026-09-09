from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from natwest_shared.db.models.business import (
    Account,
    Case,
    CaseEvent,
    Customer,
    NextAction,
    VulnerabilityRegister,
)
from natwest_shared.db.models.user import AppRole, AppUser


class BusinessReadRepository:
    """Repository for read-only customer, case, event, and next-action queries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_customers(
        self,
        *,
        is_flagged: bool | None = None,
        kyc_status: str | None = None,
        tier: str | None = None,
        name_contains: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Customer]:
        stmt = select(Customer)

        if is_flagged is not None:
            stmt = stmt.where(Customer.is_flagged.is_(is_flagged))
        if kyc_status is not None:
            stmt = stmt.where(Customer.kyc_status == kyc_status)
        if tier is not None:
            stmt = stmt.where(Customer.tier == tier)
        if name_contains is not None:
            stmt = stmt.where(Customer.full_name.ilike(f"%{name_contains}%"))

        stmt = stmt.order_by(Customer.full_name.asc()).limit(limit).offset(offset)
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
        """Fetch a customer with the full vulnerability register eagerly loaded
        (including the source system records behind each signal)."""
        stmt = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(
                selectinload(Customer.vulnerability_signals).selectinload(
                    VulnerabilityRegister.source_record
                )
            )
        )
        return self.session.scalar(stmt)

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
            if filters.get("case_type") is not None:
                stmt = stmt.where(Case.case_type == filters["case_type"])
            if filters.get("customer_id") is not None:
                stmt = stmt.where(Case.customer_id == filters["customer_id"])
            if filters.get("assigned_user_id") is not None:
                stmt = stmt.where(Case.assigned_user_id == filters["assigned_user_id"])
            if filters.get("consumer_duty_flag") is not None:
                stmt = stmt.where(
                    Case.consumer_duty_flag.is_(filters["consumer_duty_flag"])
                )

        stmt = stmt.order_by(Case.updated_at.desc()).limit(limit).offset(offset)
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
        """Fetch the chronological timeline, eagerly loading source system
        records for system events and the authoring user (with role) for
        user events."""
        stmt = (
            select(CaseEvent)
            .where(CaseEvent.case_id == case_id)
            .options(
                selectinload(CaseEvent.source_record),
                selectinload(CaseEvent.created_by_user).selectinload(AppUser.role),
            )
            .order_by(CaseEvent.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def get_next_actions(self, *, case_id: UUID) -> list[NextAction]:
        stmt = (
            select(NextAction)
            .where(NextAction.case_id == case_id)
            .order_by(NextAction.due_date.asc(), NextAction.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_staff_users(
        self,
        *,
        name_contains: str | None = None,
        role: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AppUser]:
        """Resolve staff by partial name/username match and/or role, so
        callers never need to already know a user's UUID."""
        stmt = select(AppUser).options(selectinload(AppUser.role))
        stmt = stmt.where(AppUser.is_active.is_(True))

        if name_contains is not None:
            pattern = f"%{name_contains}%"
            stmt = stmt.where(
                or_(
                    AppUser.full_name.ilike(pattern),
                    AppUser.username.ilike(pattern),
                )
            )
        if role is not None:
            stmt = stmt.join(AppRole, AppUser.role_id == AppRole.id).where(
                AppRole.name == role
            )

        stmt = stmt.order_by(AppUser.full_name.asc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())
