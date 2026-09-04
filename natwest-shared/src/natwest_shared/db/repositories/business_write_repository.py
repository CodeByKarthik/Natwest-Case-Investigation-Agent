from datetime import UTC, datetime
from uuid import UUID

from natwest_shared.common.enums import (
    IssueStatusEnum,
    NextActionStatusEnum,
    NextActionTypeEnum,
)
from natwest_shared.db.models.business import Issue, IssueUpdate, NextAction
from sqlalchemy.orm import Session


class BusinessWriteRepository:
    """
    Repository for write operations on business entities
    for issues, updates, and next actions.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the repository with a SQLAlchemy session.
        """
        self.session = session

    def update_issue_status(
        self,
        *,
        issue_id: UUID,
        status: IssueStatusEnum,
    ) -> Issue | None:
        """
        Update an issue status and maintain
        resolved_at when needed.
        """
        issue = self.session.get(Issue, issue_id)

        if issue is None:
            return None

        issue.status = status

        if status == IssueStatusEnum.RESOLVED:
            issue.resolved_at = datetime.now(UTC)

        if status in {
            IssueStatusEnum.OPEN,
            IssueStatusEnum.IN_PROGRESS,
            IssueStatusEnum.BLOCKED,
        }:
            issue.resolved_at = None

        self.session.flush()
        self.session.refresh(issue)

        return issue

    def add_issue_update(
        self,
        *,
        issue_id: UUID,
        author_user_id: UUID | None,
        author_name: str | None,
        author_role: str | None,
        update_text: str,
        is_customer_visible: bool = True,
    ) -> IssueUpdate:
        """
        Add a progress update or comment to an issue.
        """

        issue_update = IssueUpdate(
            issue_id=issue_id,
            author_user_id=author_user_id,
            author_name=author_name,
            author_role=author_role,
            update_text=update_text,
            is_customer_visible=is_customer_visible,
        )

        self.session.add(issue_update)
        self.session.flush()
        self.session.refresh(issue_update)

        return issue_update

    def create_next_action(
        self,
        *,
        issue_id: UUID,
        action_type: NextActionTypeEnum,
        action_text: str,
        owner_user_id: UUID | None,
        due_at: datetime | None,
        created_by_user_id: UUID | None,
        created_by_role: str | None,
    ) -> NextAction:
        """
        Create an open next action for an issue.
        """

        next_action = NextAction(
            issue_id=issue_id,
            action_type=action_type,
            action_text=action_text,
            owner_user_id=owner_user_id,
            due_at=due_at,
            status=NextActionStatusEnum.OPEN,
            created_by_user_id=created_by_user_id,
            created_by_role=created_by_role,
        )

        self.session.add(next_action)
        self.session.flush()
        self.session.refresh(next_action)

        return next_action

    def update_next_action(
        self,
        *,
        next_action_id: UUID,
        action_type: NextActionTypeEnum | None = None,
        action_text: str | None = None,
        owner_user_id: UUID | None = None,
        due_at: datetime | None = None,
        status: NextActionStatusEnum | None = None,
    ) -> NextAction | None:
        """
        Update next action fields and maintain
        completed_at when needed.
        """
        next_action = self.session.get(NextAction, next_action_id)

        if next_action is None:
            return None

        if action_type is not None:
            next_action.action_type = action_type

        if action_text is not None:
            next_action.action_text = action_text

        if owner_user_id is not None:
            next_action.owner_user_id = owner_user_id

        if due_at is not None:
            next_action.due_at = due_at

        if status is not None:
            next_action.status = status

            if status == NextActionStatusEnum.COMPLETED:
                next_action.completed_at = datetime.now(UTC)

            if status in {
                NextActionStatusEnum.OPEN,
                NextActionStatusEnum.IN_PROGRESS,
                NextActionStatusEnum.CANCELLED,
            }:
                next_action.completed_at = None

        self.session.flush()
        self.session.refresh(next_action)

        return next_action

    def complete_next_action(
        self,
        *,
        next_action_id: UUID,
    ) -> NextAction | None:
        """
        Mark a next action as completed.
        """
        return self.update_next_action(
            next_action_id=next_action_id,
            status=NextActionStatusEnum.COMPLETED,
        )
