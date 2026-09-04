from natwest_shared.common.enums import AppRole
from natwest_shared.schema.auth_schema import AuthContext

from ..common.exceptions import PermissionDenied

READ_ROLES = {
    AppRole.CUSTOMER_SUPPORT,
    AppRole.FRAUD_INVESTIGATOR,
    AppRole.COMPLIANCE_OFFICER,
}

WRITE_ROLES = {
    AppRole.FRAUD_INVESTIGATOR,
    AppRole.COMPLIANCE_OFFICER,
}

ADMIN_ROLES = {
    AppRole.COMPLIANCE_OFFICER,
}


def require_role(context: AuthContext, allowed_roles: set[AppRole]) -> None:
    """
    Enforce that the authenticated user has one
    of the allowed roles.
    """
    if context.role not in allowed_roles:
        raise PermissionDenied("User does not have the required role")


def can_read(context: AuthContext) -> bool:
    """
    Check if the user has read permission.
    """
    return context.role in READ_ROLES


def can_write(context: AuthContext) -> bool:
    """
    Check if the user has write/modify permission.
    """
    return context.role in WRITE_ROLES


def is_admin(context: AuthContext) -> bool:
    """
    Check if the user has admin privileges.
    """
    return context.role == AppRole.COMPLIANCE_OFFICER
