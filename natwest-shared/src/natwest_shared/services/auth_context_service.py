from natwest_shared.auth.keycloak import KeycloakTokenVerifier
from natwest_shared.common.enums import AppRole
from natwest_shared.common.exceptions import (
    AppUserNotFoundError,
    AuthError,
    PermissionDenied,
)
from natwest_shared.db.repositories.user_repository import AppUserRepository
from natwest_shared.schema.auth_schema import AuthContext


class AuthContextService:
    """
    Service that orchestrates authentication and authorization.

    Responsibilities:
    1. Verify the incoming JWT token via Keycloak.
    2. Fetch the corresponding application user from the database.
    3. Ensure the token's roles match the user's assigned application role.
    4. Return a normalized AuthContext for downstream use.
    """

    def __init__(
        self,
        token_verifier: KeycloakTokenVerifier,
        user_repository: AppUserRepository,
    ) -> None:
        """
        Initialize the authentication service.

        Attributes:
        -----------
        - token_verifier: Component that validates Keycloak
            tokens and extracts user data.
        - user_repository: Repository for accessing application users.
        """
        self.token_verifier = token_verifier
        self.user_repository = user_repository

    def authenticate(self, token: str) -> AuthContext:
        """
        Authenticate a user using a Keycloak JWT token.

        Steps:
        1. Verify the token and extract Keycloak user information.
        2. Retrieve the application user by username (from the token).
        3. Validate that the token's roles include the user's stored
           application role.
        4. Return an AuthContext object containing user identity and role.

        Attributes:
        -----------
            - token: The JWT token from the incoming request.

        Returns:
        --------
            - AuthContext containing user ID, username, role, and Keycloak user ID.

        Raises:
        -------
            - AuthError: If the token is invalid or the user is not
            found in the app DB.

            - PermissionDenied: If the token's roles do not match
              the application role.
        """
        token_user = self.token_verifier.verify(token)

        try:
            app_user = self.user_repository.get_active_user_by_username(
                token_user.username
            )
        except AppUserNotFoundError as exc:
            raise AuthError(
                "Authenticated user is not registered in the application"
            ) from exc

        self._ensure_token_role_matches_app_role(
            token_roles=token_user.roles,
            app_role=app_user.role,
        )

        if app_user.keycloak_user_id is None:
            if token_user.keycloak_user_id is None:
                raise AuthError("Token missing Keycloak user ID (sub claim)")
            self.user_repository.set_keycloak_user_id(
                app_user_id=app_user.id,
                keycloak_user_id=token_user.keycloak_user_id,
            )
            app_user.keycloak_user_id = token_user.keycloak_user_id

        elif app_user.keycloak_user_id != token_user.keycloak_user_id:
            raise AuthError(
                "Authenticated token does not match the registered Keycloak user"
            )

        try:
            app_role = AppRole(app_user.role)
        except ValueError as exc:
            raise AuthError("Registered application user has an invalid role") from exc

        return AuthContext(
            app_user_id=app_user.id,
            username=app_user.username,
            role=app_role,
            keycloak_user_id=token_user.keycloak_user_id,
        )

    @staticmethod
    def _ensure_token_role_matches_app_role(
        token_roles: set[str],
        app_role: str,
    ) -> None:
        """
        Validate that the application role is present in the token's roles.

        This prevents a scenario where a user's role in Keycloak is different
        from the role stored in our application database.

        Attributes:
        -----------
            token_roles: Set of roles extracted from the Keycloak token.
            app_role: The role assigned to the user in our application DB.

        Raises:
            PermissionDenied: If app_role is not found in token_roles.
        """
        if app_role not in token_roles:
            raise PermissionDenied(
                "Token role does not match registered application role"
            )
