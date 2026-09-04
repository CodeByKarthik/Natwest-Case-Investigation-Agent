from uuid import UUID

from natwest_shared.common.enums import IssueStatusEnum, NextActionStatusEnum
from natwest_shared.db.models.business import Customer, Issue, IssueUpdate, NextAction
from sqlalchemy import select
from sqlalchemy.orm import Session


class BusinessReadRepository:
    """
    Repository for read-only business data access,
    including customers, issues, updates
    and next actions.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the repository with a SQLAlchemy session.
        """
        self.session = session

    def list_customers(
        self,
        *,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Customer]:
        """
        Return customers ordered by name.
        """
        stmt = select(Customer).order_by(Customer.name).limit(limit).offset(offset)

        if not include_deleted:
            stmt = stmt.where(Customer.deleted_at.is_(None))

        return list(self.session.scalars(stmt).all())

    def get_customer_by_name(
        self,
        name: str,
        *,
        include_deleted: bool = False,
    ) -> Customer | None:
        """
        Return the first customer matching a partial name.
        """
        stmt = select(Customer).where(Customer.name.ilike(f"%{name}%"))

        if not include_deleted:
            stmt = stmt.where(Customer.deleted_at.is_(None))

        return self.session.scalar(stmt.order_by(Customer.name))

    def list_open_issues(
        self,
        *,
        customer_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Issue]:
        """
        Return non-deleted open, in-progress, or blocked
        issues for a customer.
        """
        open_statuses = [
            IssueStatusEnum.OPEN,
            IssueStatusEnum.IN_PROGRESS,
            IssueStatusEnum.BLOCKED,
        ]

        stmt = (
            select(Issue)
            .where(Issue.customer_id == customer_id)
            .where(Issue.status.in_(open_statuses))
            .where(Issue.deleted_at.is_(None))
            .order_by(Issue.priority, Issue.opened_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.session.scalars(stmt).all())

    def get_issue_by_external_ref(
        self,
        *,
        external_ref: str,
    ) -> Issue | None:
        """
        Return an issue by its external reference.
        """
        stmt = (
            select(Issue)
            .where(Issue.external_ref == external_ref)
            .where(Issue.deleted_at.is_(None))
        )

        return self.session.scalar(stmt)

    def list_issue_updates(
        self,
        *,
        issue_id: UUID,
        customer_visible_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IssueUpdate]:
        """
        Return updates for an issue, newest first.
        """
        stmt = (
            select(IssueUpdate)
            .where(IssueUpdate.issue_id == issue_id)
            .order_by(IssueUpdate.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if customer_visible_only:
            stmt = stmt.where(IssueUpdate.is_customer_visible.is_(True))

        return list(self.session.scalars(stmt).all())

    def list_next_actions(
        self,
        *,
        issue_id: UUID,
        status: NextActionStatusEnum | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NextAction]:
        """
        Return next actions for an issue, ordered by due date.
        """
        stmt = (
            select(NextAction)
            .where(NextAction.issue_id == issue_id)
            .order_by(
                NextAction.due_at.asc().nulls_last(),
                NextAction.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        if status is not None:
            stmt = stmt.where(NextAction.status == status)

        return list(self.session.scalars(stmt).all())
