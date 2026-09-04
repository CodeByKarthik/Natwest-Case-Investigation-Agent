from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from natwest_frontend.config import settings  # type: ignore[import-untyped]

CLIENT_SECRET = settings.keycloak_client_secret
OAUTH_STATE_MAX_AGE_SECONDS = 300


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def b64url_decode(data: str) -> bytes:
    data += "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_oauth_state() -> str:
    payload = {  # type: ignore[var-annotated]
        "iat": int(time.time()),
        "nonce": secrets.token_urlsafe(24),
    }

    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = b64url_encode(payload_json)

    signature = hmac.new(
        CLIENT_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return f"{payload_b64}.{b64url_encode(signature)}"


def validate_oauth_state(state: str | None) -> bool:
    if not state or "." not in state:
        return False

    payload_b64, signature_b64 = state.split(".", 1)

    expected_signature = hmac.new(
        CLIENT_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    try:
        actual_signature = b64url_decode(signature_b64)
    except Exception:
        return False

    if not hmac.compare_digest(expected_signature, actual_signature):
        return False

    try:
        payload = json.loads(b64url_decode(payload_b64))
    except Exception:
        return False

    issued_at = payload.get("iat")

    if not isinstance(issued_at, int):
        return False

    return time.time() - issued_at <= OAUTH_STATE_MAX_AGE_SECONDS
