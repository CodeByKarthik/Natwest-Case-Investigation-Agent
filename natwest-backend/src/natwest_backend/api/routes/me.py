from fastapi import APIRouter, Depends
from natwest_shared.schema.auth_schema import AuthContext

from natwest_backend.api.auth import get_auth_context

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=AuthContext)
def me(
    auth_context: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """
    Return the authenticated user's app context.
    """
    return auth_context
