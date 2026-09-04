from datetime import datetime
from uuid import UUID

from natwest_shared.auth.rbac import ADMIN_ROLES, READ_ROLES, WRITE_ROLES, require_role
from natwest_shared.common.enums import (
    IssueStatusEnum,
    NextActionStatusEnum,
    NextActionTypeEnum,
)
from natwest_shared.db.models.business import Customer, Issue, IssueUpdate, NextAction
from natwest_shared.db.repositories.business_read_repository import (
    BusinessReadRepository,
)
from natwest_shared.db.repositories.business_write_repository import (
    BusinessWriteRepository,
)
from natwest_shared.schema.auth_schema import AuthContext


class BusinessService:
    """
    Permission-aware business service for customer, issue, update,
    and next-action operations.
    """

    def __init__(
        self,
        *,
        read_repository: BusinessReadRepository,
        write_repository: BusinessWriteRepository,
        auth_context: AuthContext,
    ) -> None:
        self.read_repository = read_repository
        self.write_repository = write_repository
        self.auth_context = auth_context

    def list_customers(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Customer]:
        """
        Return customers visible to users with read access.
        """
        require_role(self.auth_context, READ_ROLES)

        return self.read_repository.list_customers(
            limit=limit,
            offset=offset,
        )

    def get_customer_by_name(
        self,
        *,
        name: str,
    ) -> Customer | None:
        """
        Return the first customer matching a partial name.
        """
        require_role(self.auth_context, READ_ROLES)

        return self.read_repository.get_customer_by_name(name=name)

    def list_open_issues(
        self,
        *,
        customer_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Issue]:
        """
        Return open issues for a customer.
        """
        require_role(self.auth_context, READ_ROLES)

        return self.read_repository.list_open_issues(
            customer_id=customer_id,
            limit=limit,
            offset=offset,
        )

    def get_issue_by_external_ref(
        self,
        *,
        external_ref: str,
    ) -> Issue | None:
        """
        Return an issue by its external reference.
        """
        require_role(self.auth_context, READ_ROLES)

        return self.read_repository.get_issue_by_external_ref(
            external_ref=external_ref,
        )

    def list_issue_updates(
        self,
        *,
        issue_id: UUID,
        customer_visible_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IssueUpdate]:
        """
        Return updates for an issue.
        """
        require_role(self.auth_context, READ_ROLES)

        return self.read_repository.list_issue_updates(
            issue_id=issue_id,
            customer_visible_only=customer_visible_only,
            limit=limit,
            offset=offset,
        )

    def list_next_actions(
        self,
        *,
        issue_id: UUID,
        status: NextActionStatusEnum | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NextAction]:
        """
        Return next actions for an issue.
        """
        require_role(self.auth_context, READ_ROLES)

        return self.read_repository.list_next_actions(
            issue_id=issue_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def update_issue_status(
        self,
        *,
        issue_id: UUID,
        status: IssueStatusEnum,
    ) -> Issue | None:
        """
        Update an issue status for users with write access.
        """
        require_role(self.auth_context, WRITE_ROLES)

        return self.write_repository.update_issue_status(
            issue_id=issue_id,
            status=status,
        )

    def add_issue_update(
        self,
        *,
        issue_id: UUID,
        update_text: str,
        is_customer_visible: bool = True,
    ) -> IssueUpdate:
        """
        Add an issue update for users with write access.
        """
        require_role(self.auth_context, WRITE_ROLES)

        return self.write_repository.add_issue_update(
            issue_id=issue_id,
            author_user_id=UUID(self.auth_context.app_user_id),
            author_name=self.auth_context.username,
            author_role=self.auth_context.role.value,
            update_text=update_text,
            is_customer_visible=is_customer_visible,
        )

    def create_next_action(
        self,
        *,
        issue_id: UUID,
        action_type: NextActionTypeEnum,
        action_text: str,
        owner_user_id: UUID | None = None,
        due_at: datetime | None = None,
    ) -> NextAction:
        """
        Create a next action for admin users.
        """
        require_role(self.auth_context, ADMIN_ROLES)

        return self.write_repository.create_next_action(
            issue_id=issue_id,
            action_type=action_type,
            action_text=action_text,
            owner_user_id=owner_user_id,
            due_at=due_at,
            created_by_user_id=UUID(self.auth_context.app_user_id),
            created_by_role=self.auth_context.role.value,
        )

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
        Update a next action for admin users.
        """
        require_role(self.auth_context, ADMIN_ROLES)

        return self.write_repository.update_next_action(
            next_action_id=next_action_id,
            action_type=action_type,
            action_text=action_text,
            owner_user_id=owner_user_id,
            due_at=due_at,
            status=status,
        )

    def complete_next_action(
        self,
        *,
        next_action_id: UUID,
    ) -> NextAction | None:
        """
        Mark a next action as completed for admin users.
        """
        require_role(self.auth_context, ADMIN_ROLES)

        return self.write_repository.complete_next_action(
            next_action_id=next_action_id,
        )
