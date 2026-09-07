from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from natwest_shared.common.exceptions import AppUserNotFoundError
from natwest_shared.db.models import AppRole, AppUser
from natwest_shared.schema.auth_schema import AppUserDTO


class AppUserRepository:
    """
    Repository for performing database operations related
    to application users.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active_user_by_username(self, username: str) -> AppUserDTO:
        """
        Retrieve an active app user by their username.

        Attributes:
        -----------
        - username: The username of the app user to retrieve.

        Returns:
        --------
        - An AppUserDTO containing the user's details.
        """
        stmt = (
            select(
                AppUser.id,
                AppUser.username,
                AppUser.email,
                AppUser.full_name,
                AppUser.is_active,
                AppUser.keycloak_user_id,
                AppRole.name.label("role"),
            )
            .join(AppRole, AppUser.role_id == AppRole.id)
            .where(AppUser.username == username)
            .where(AppUser.is_active.is_(True))
        )

        row = self.db.execute(stmt).mappings().one_or_none()

        if row is None:
            raise AppUserNotFoundError(f"Active app user not found: {username}")

        return AppUserDTO(
            id=str(row["id"]),
            username=row["username"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            is_active=row["is_active"],
            keycloak_user_id=row["keycloak_user_id"],
        )

    def set_keycloak_user_id(
        self,
        app_user_id: str,
        keycloak_user_id: str,
    ) -> None:
        """
        Persist the Keycloak user ID for an application user.
        """
        app_user_uuid: UUID = UUID(app_user_id)
        app_user = self.db.get(AppUser, app_user_uuid)

        if app_user is None:
            raise AppUserNotFoundError(f"App user not found: {app_user_id}")

        app_user.keycloak_user_id = keycloak_user_id
