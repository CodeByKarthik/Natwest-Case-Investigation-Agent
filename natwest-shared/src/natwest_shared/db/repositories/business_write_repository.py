from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from natwest_shared.db.models.business import Case, CaseEvent, NextAction


class BusinessWriteRepository:
    """Repository for write operations on case and next-action entities."""

    @staticmethod
    def _get_str_value(
        fields: dict[str, object], key: str, default: str | None = None
    ) -> str | None:
        value = fields.get(key, default)
        if isinstance(value, str):
            return value
        return default

    @staticmethod
    def _get_uuid_value(
        fields: dict[str, object], key: str, default: UUID | None = None
    ) -> UUID | None:
        value = fields.get(key, default)
        if isinstance(value, UUID):
            return value
        return default

    @staticmethod
    def _get_datetime_value(
        fields: dict[str, object], key: str, default: datetime | None = None
    ) -> datetime | None:
        value = fields.get(key, default)
        if isinstance(value, datetime):
            return value
        return default

    def __init__(self, session: Session) -> None:
        self.session = session

    def update_case_status(
        self,
        *,
        case_id: UUID,
        new_status: str,
        reason: str,
        updated_by_user_id: UUID | None = None,
        updated_by_name: str | None = None,
        updated_by_role: str | None = None,
    ) -> Case | None:
        case = self.session.get(Case, case_id)
        if case is None:
            return None

        case.status = new_status
        case.last_updated = datetime.now(UTC)

        status_event = CaseEvent(
            case_id=case.id,
            event_type="status_change",
            event_description=f"Status changed to {new_status}: {reason}",
            is_internal=False,
            created_by_user_id=updated_by_user_id,
            created_by_name=updated_by_name,
            created_by_role=updated_by_role,
        )
        self.session.add(status_event)
        self.session.flush()
        self.session.refresh(case)
        return case

    def manage_next_action(
        self,
        *,
        operation: str,
        case_id: UUID | None = None,
        action_id: UUID | None = None,
        fields: dict[str, object] | None = None,
    ) -> NextAction | None:
        fields = fields or {}

        if operation == "create":
            if case_id is None:
                return None
            action_type = self._get_str_value(fields, "action_type", "add_case_note")
            description = self._get_str_value(fields, "description", "Action required")
            due_date = self._get_datetime_value(fields, "due_date", datetime.now(UTC))
            assigned_user_id = self._get_uuid_value(fields, "assigned_user_id")
            created_by_user_id = self._get_uuid_value(fields, "created_by_user_id")
            created_by_role = self._get_str_value(fields, "created_by_role")

            new_action = NextAction(
                case_id=case_id,
                action_type=action_type,
                description=description,
                due_date=due_date,
                status="open",
                assigned_user_id=assigned_user_id,
                created_by_user_id=created_by_user_id,
                created_by_role=created_by_role,
            )
            self.session.add(new_action)
            self.session.flush()
            self.session.refresh(new_action)
            return new_action

        if action_id is None:
            return None

        existing_action = self.session.get(NextAction, action_id)
        if existing_action is None:
            return None

        if operation == "update":
            action_type = self._get_str_value(fields, "action_type")
            if action_type is not None:
                existing_action.action_type = action_type

            description = self._get_str_value(fields, "description")
            if description is not None:
                existing_action.description = description

            due_date = self._get_datetime_value(fields, "due_date")
            if due_date is not None:
                existing_action.due_date = due_date

            assigned_user_id = self._get_uuid_value(fields, "assigned_user_id")
            if assigned_user_id is not None:
                existing_action.assigned_user_id = assigned_user_id

            status_value = self._get_str_value(fields, "status")
            if status_value is not None:
                existing_action.status = status_value

            if status_value == "completed":
                existing_action.completed_at = datetime.now(UTC)
            self.session.flush()
            self.session.refresh(existing_action)
            return existing_action

        if operation == "complete":
            existing_action.status = "completed"
            existing_action.completed_at = datetime.now(UTC)
            self.session.flush()
            self.session.refresh(existing_action)
            return existing_action

        return None

    def update_issue_status(
        self,
        *,
        issue_id: UUID,
        status: str,
    ) -> Case | None:
        return self.update_case_status(
            case_id=issue_id,
            new_status=status,
            reason="Status updated by repository",
        )

    def add_issue_update(
        self,
        *,
        issue_id: UUID,
        author_user_id: UUID | None,
        author_name: str | None,
        author_role: str | None,
        update_text: str,
        is_customer_visible: bool = True,
    ) -> CaseEvent:
        update = CaseEvent(
            case_id=issue_id,
            event_type="note",
            event_description=update_text,
            is_internal=not is_customer_visible,
            created_by_user_id=author_user_id,
            created_by_name=author_name,
            created_by_role=author_role,
        )
        self.session.add(update)
        self.session.flush()
        self.session.refresh(update)
        return update

    def create_next_action(
        self,
        *,
        issue_id: UUID,
        action_type: str,
        action_text: str,
        owner_user_id: UUID | None,
        due_at: datetime | None,
        created_by_user_id: UUID | None,
        created_by_role: str | None,
    ) -> NextAction:
        action = NextAction(
            case_id=issue_id,
            action_type=action_type,
            description=action_text,
            due_date=due_at or datetime.now(UTC),
            status="open",
            assigned_user_id=owner_user_id,
            created_by_user_id=created_by_user_id,
            created_by_role=created_by_role,
        )
        self.session.add(action)
        self.session.flush()
        self.session.refresh(action)
        return action

    def update_next_action(
        self,
        *,
        next_action_id: UUID,
        action_type: str | None = None,
        action_text: str | None = None,
        owner_user_id: UUID | None = None,
        due_at: datetime | None = None,
        status: str | None = None,
    ) -> NextAction | None:
        existing_action = self.session.get(NextAction, next_action_id)
        if existing_action is None:
            return None
        if action_type is not None:
            existing_action.action_type = action_type
        if action_text is not None:
            existing_action.description = action_text
        if owner_user_id is not None:
            existing_action.assigned_user_id = owner_user_id
        if due_at is not None:
            existing_action.due_date = due_at
        if status is not None:
            existing_action.status = status
            if status == "completed":
                existing_action.completed_at = datetime.now(UTC)
        self.session.flush()
        self.session.refresh(existing_action)
        return existing_action

    def complete_next_action(self, *, next_action_id: UUID) -> NextAction | None:
        return self.update_next_action(
            next_action_id=next_action_id, status="completed"
        )
