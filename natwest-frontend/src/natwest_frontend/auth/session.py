from __future__ import annotations

import base64
import json
import time
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st

from natwest_frontend.auth.oauth import create_oauth_state, validate_oauth_state
from natwest_frontend.config import settings  # type: ignore[import-untyped]
from natwest_frontend.utils.logger import get_logger

logger = get_logger(__name__)

KEYCLOAK_URL = settings.keycloak_url
KEYCLOAK_EXTERNAL_URL = settings.keycloak_external_url
REALM = settings.keycloak_realm
CLIENT_ID = settings.keycloak_client_id
CLIENT_SECRET = settings.keycloak_client_secret
REDIRECT_URI = settings.redirect_uri

TOKEN_REFRESH_SKEW_SECONDS = 30


def get_query_param(name: str) -> str | None:
    value = st.query_params.get(name)

    if isinstance(value, list):
        return value[0] if value else None

    if isinstance(value, str):
        return value

    return None


def get_auth_url() -> str:
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email",
        "state": create_oauth_state(),
    }

    return (
        f"{KEYCLOAK_EXTERNAL_URL}/realms/{REALM}"
        f"/protocol/openid-connect/auth?{urlencode(params)}"
    )


def exchange_code_for_token(code: str) -> dict[str, Any] | None:
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    try:
        response = requests.post(token_url, data=payload, timeout=10)
    except requests.RequestException as exc:
        logger.error("Token exchange failed | error: %s", str(exc))
        st.error("Unable to complete sign-in. Please try again.")
        return None

    if response.status_code != 200:
        logger.warning(
            "Token exchange rejected | status: %d",
            response.status_code,
        )
        st.error("Authentication failed. Please try again.")
        return None

    logger.info("Token exchange successful")
    token_data: dict[str, Any] = response.json()
    return token_data


def store_token_response(token_response: dict[str, Any]) -> None:
    st.session_state["access_token"] = token_response["access_token"]
    st.session_state["refresh_token"] = token_response.get("refresh_token")
    st.session_state["id_token"] = token_response.get("id_token")

    expires_in = int(token_response.get("expires_in", 300))
    st.session_state["expires_at"] = time.time() + expires_in

    logger.info("Token stored | expires_in: %ds", expires_in)


def refresh_access_token() -> bool:
    refresh_token = st.session_state.get("refresh_token")

    if not isinstance(refresh_token, str):
        logger.warning("Token refresh failed — no refresh token available")
        return False

    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    try:
        response = requests.post(token_url, data=payload, timeout=10)
    except requests.RequestException as exc:
        logger.error("Token refresh request failed | error: %s", str(exc))
        return False

    if response.status_code != 200:
        logger.warning(
            "Token refresh rejected | status: %d",
            response.status_code,
        )
        return False

    token_data: dict[str, Any] = response.json()
    store_token_response(token_data)
    logger.info("Token refreshed successfully")
    return True


def ensure_valid_token() -> bool:
    if "access_token" not in st.session_state:
        return False

    expires_at = st.session_state.get("expires_at")

    if not isinstance(expires_at, float):
        return True

    if time.time() < expires_at - TOKEN_REFRESH_SKEW_SECONDS:
        return True

    logger.info("Token nearing expiry, attempting refresh")
    return refresh_access_token()


def decode_jwt_payload(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
        data: dict[str, Any] = json.loads(decoded)
        return data
    except Exception:
        return {}


def get_logged_in_user() -> str:
    token = st.session_state.get("id_token") or st.session_state.get("access_token")

    if not isinstance(token, str):
        return "Authenticated user"

    claims = decode_jwt_payload(token)

    return str(
        claims.get("preferred_username")
        or claims.get("name")
        or claims.get("email")
        or "Authenticated user"
    )


def logout() -> None:
    id_token = st.session_state.get("id_token")
    username = get_logged_in_user()

    for key in [
        "access_token",
        "refresh_token",
        "id_token",
        "expires_at",
        "messages",
        "conversation_id",
    ]:
        st.session_state.pop(key, None)

    st.query_params.clear()

    logger.info("User logged out | username: %s", username)

    if isinstance(id_token, str):
        logout_params = {
            "id_token_hint": id_token,
            "post_logout_redirect_uri": REDIRECT_URI,
        }

        logout_url = (
            f"{KEYCLOAK_EXTERNAL_URL}/realms/{REALM}"
            f"/protocol/openid-connect/logout?{urlencode(logout_params)}"
        )

        st.markdown(
            f"<meta http-equiv='refresh' content='0; url={logout_url}'>",
            unsafe_allow_html=True,
        )
        st.stop()

    st.rerun()


def handle_auth_callback() -> bool:
    code = get_query_param("code")

    if not code:
        return False

    returned_state = get_query_param("state")

    if not validate_oauth_state(returned_state):
        logger.warning("OAuth callback rejected — invalid state")
        st.error("Invalid authentication response. Please sign in again.")
        st.query_params.clear()
        return True

    token_response = exchange_code_for_token(code)

    if token_response:
        store_token_response(token_response)
        logger.info("OAuth callback completed — user authenticated")
        st.query_params.clear()
        st.rerun()

    st.query_params.clear()
    return True
