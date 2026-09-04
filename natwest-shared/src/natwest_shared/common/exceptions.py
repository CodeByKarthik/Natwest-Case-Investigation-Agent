class AuthError(Exception):
    """
    Raised when authentication fails.
    """


class PermissionDenied(Exception):
    """
    Raised when authorization fails.
    """


class AppUserNotFoundError(Exception):
    pass
