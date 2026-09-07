from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request, status
from natwest_shared.auth.keycloak import KeycloakTokenVerifier
from natwest_shared.common.exceptions import AuthError, PermissionDenied
from natwest_shared.db.repositories.user_repository import AppUserRepository
from natwest_shared.db.session import SessionLocal
from natwest_shared.schema.auth_schema import AuthContext
from natwest_shared.services.auth_context_service import AuthContextService
from sqlalchemy.orm import Session


def get_db_session() -> Iterator[Session]:
    """
    Provide a database session for a FastAPI request.

    The API request boundary owns session lifecycle.
    """
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def extract_bearer_token(authorization: str | None) -> str:
    """
    Extract a bearer token from the Authorization header.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer token format",
        )

    return token


def get_auth_context(
    request: Request,
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db_session),
) -> AuthContext:
    token = extract_bearer_token(authorization)

    auth_service = AuthContextService(
        token_verifier=KeycloakTokenVerifier(),
        user_repository=AppUserRepository(session),
    )

    try:
        auth_context = auth_service.authenticate(token)
        request.state.auth_context = auth_context
        return auth_context
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except PermissionDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
