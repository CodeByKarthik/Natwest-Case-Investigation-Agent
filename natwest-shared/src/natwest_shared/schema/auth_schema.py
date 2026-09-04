from natwest_shared.common.enums import AppRole
from pydantic import BaseModel, Field


class RealmAccess(BaseModel):
    """
    Represents the realm access information in the Keycloak
    token payload, including the roles assigned to the user.
    """

    roles: list[str] = Field(default_factory=list)


class KeycloakTokenPayload(BaseModel):
    """
    Represents the payload of a Keycloak token, containing user
    information and access details.
    """

    iss: str
    azp: str
    preferred_username: str

    sub: str | None = None
    email: str | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    email_verified: bool | None = None

    realm_access: RealmAccess = Field(default_factory=RealmAccess)


class AuthenticatedUser(BaseModel):
    """
    Represents an authenticated user in the application, containing
    the user's ID, username, roles, and optional Keycloak
    user ID and email.
    """

    username: str
    roles: set[str]

    keycloak_user_id: str | None = None
    email: str | None = None

    def has_role(self, role: str) -> bool:
        return role in self.roles


class AppUserDTO(BaseModel):
    """
    Data Transfer Object (DTO) representing an application
    user, containing the user's ID, username, email,
    full name, role, and active status.
    """

    id: str
    username: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool
    keycloak_user_id: str | None = None


class AuthContext(BaseModel):
    """
    Represents the authentication context for a user,
    containing the application user details.
    """

    app_user_id: str
    username: str
    role: AppRole

    keycloak_user_id: str | None = None
