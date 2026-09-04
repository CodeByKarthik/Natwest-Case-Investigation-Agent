import json
from typing import Any

import jwt
from jwt import PyJWKClient
from pydantic import ValidationError

from ..common.exceptions import AuthError
from ..config import settings
from ..schema.auth_schema import AuthenticatedUser, KeycloakTokenPayload


class KeycloakTokenVerifier:
    """
    Verifies and decodes JWT access tokens issued by Keycloak.
    """

    def __init__(self) -> None:
        """
        Initialize the token verifier using settings from
        environment variables.
        """
        self.issuers = [settings.keycloak_issuer]
        if settings.keycloak_issuer_docker:
            self.issuers.append(settings.keycloak_issuer_docker)
        self.client_id = settings.keycloak_client_id
        self.jwks_url = settings.keycloak_jwks_url
        self._jwks_client = PyJWKClient(self.jwks_url)

    def verify(self, token: str) -> AuthenticatedUser:
        """
        Verify a Keycloak JWT token and return an authenticated user.

        Attributes:
        -----------
        - token: The JWT access token string (from Authorization header).

        Returns:
        --------
        - AuthenticatedUser containing Keycloak user ID, username, email, and roles.

        Raises:
        -------
            AuthError: If the token is invalid, expired, or missing required claims.
        """
        raw_payload = self._decode(token)
        payload = self._validate_payload(raw_payload)
        return self._to_user(payload)

    def _decode(self, token: str) -> dict[str, Any]:
        """
        Decode and verify JWT signature, expiry, issuer, and client binding.
        """
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)

            payload: dict[str, Any] | None = None
            for issuer in dict.fromkeys(self.issuers):
                try:
                    payload = jwt.decode(
                        token,
                        signing_key.key,
                        algorithms=[settings.keycloak_jwt_algorithm],
                        issuer=issuer,
                        options={"verify_aud": False},
                    )
                    break
                except jwt.InvalidIssuerError:
                    continue

            if payload is None:
                raise AuthError("Invalid access token")

            self._validate_client(payload)
            return payload

        except jwt.ExpiredSignatureError as exc:
            raise AuthError("Access token has expired") from exc
        except jwt.PyJWTError as exc:
            raise AuthError("Invalid access token") from exc

    def _validate_payload(self, raw_payload: dict[str, Any]) -> KeycloakTokenPayload:
        """
        Validate the decoded payload against the KeycloakTokenPayload schema.

        This ensures all required claims (sub, preferred_username, email,
        realm_access.roles) are present and have correct types.
        """
        try:
            return KeycloakTokenPayload.model_validate(raw_payload)
        except ValidationError as exc:
            print("Token payload validation failed")
            print(json.dumps(raw_payload, indent=2))
            print(exc)
            raise AuthError("Token payload is missing required claims") from exc

    @staticmethod
    def _to_user(payload: KeycloakTokenPayload) -> AuthenticatedUser:
        """
        Convert the validated payload to an AuthenticatedUser
        domain object.
        """
        return AuthenticatedUser(
            keycloak_user_id=payload.sub,
            username=payload.preferred_username,
            email=payload.email,
            roles=set(payload.realm_access.roles),
        )

    def _validate_client(self, payload: dict[str, Any]) -> None:
        """
        Ensure the token was issued for this application client.

        Keycloak access tokens often use the `azp` claim to identify the
        authorized party. Some configurations also include the client ID in `aud`.
        """
        authorized_party = payload.get("azp")
        audience = payload.get("aud")

        audience_matches = False

        if isinstance(audience, str):
            audience_matches = audience == self.client_id
        elif isinstance(audience, list):
            audience_matches = self.client_id in audience

        if authorized_party != self.client_id and not audience_matches:
            raise AuthError("Access token was not issued for this client")
