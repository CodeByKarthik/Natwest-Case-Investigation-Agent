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
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                return default
        return default

    @staticmethod
    def _get_datetime_value(
        fields: dict[str, object], key: str, default: datetime | None = None
    ) -> datetime | None:
        value = fields.get(key, default)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return default
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
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
    ) -> Case | None:
        """Update a case status and append a user-generated status_change
        case event as a side effect."""
        case = self.session.get(Case, case_id)
        if case is None:
            return None

        case.status = new_status
        case.updated_at = datetime.now(UTC)

        status_event = CaseEvent(
            case_id=case.id,
            event_type="status_change",
            event_description=f"Status changed to {new_status}: {reason}",
            created_by_user_id=updated_by_user_id,
            created_by_system=None,
            source_record_id=None,
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
        created_by_user_id: UUID | None = None,
    ) -> NextAction | None:
        fields = fields or {}

        if operation == "create":
            if case_id is None:
                return None
            action_type = self._get_str_value(fields, "action_type", "add_case_note")
            description = self._get_str_value(fields, "description", "Action required")
            due_date = self._get_datetime_value(fields, "due_date", datetime.now(UTC))
            assigned_user_id = self._get_uuid_value(fields, "assigned_user_id")

            new_action = NextAction(
                case_id=case_id,
                action_type=action_type,
                description=description,
                due_date=due_date,
                status="open",
                assigned_user_id=assigned_user_id,
                created_by_user_id=created_by_user_id,
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

            existing_action.updated_at = datetime.now(UTC)
            self.session.flush()
            self.session.refresh(existing_action)
            return existing_action

        if operation == "complete":
            existing_action.status = "completed"
            existing_action.completed_at = datetime.now(UTC)
            existing_action.updated_at = datetime.now(UTC)
            self.session.flush()
            self.session.refresh(existing_action)
            return existing_action

        return None
