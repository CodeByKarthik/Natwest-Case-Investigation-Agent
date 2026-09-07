from __future__ import annotations

import time
import uuid
from typing import Any

import requests
import streamlit as st

from natwest_frontend.auth.session import ensure_valid_token
from natwest_frontend.config import settings  # type: ignore[import-untyped]
from natwest_frontend.utils.logger import get_logger

logger = get_logger(__name__)

API_BASE_URL = settings.api_base_url


def _get_conversation_id() -> str:
    """Return a stable conversation ID for the current session."""
    if "conversation_id" not in st.session_state:
        st.session_state["conversation_id"] = str(uuid.uuid4())
        logger.info(
            "New conversation started | conversation_id: %s",
            st.session_state["conversation_id"],
        )
    return st.session_state["conversation_id"]


def call_agent_api(message: str) -> str:
    """
    Send a message to the agent and return the response.
    """
    if not ensure_valid_token():
        logger.warning("Token validation failed — session expired")
        return "Your session has expired. Please sign in again."

    token = st.session_state["access_token"]
    conversation_id = _get_conversation_id()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "message": message,
        "conversation_id": conversation_id,
    }

    logger.info(
        "API request | conversation: %s | message: %.100s",
        conversation_id,
        message,
    )

    start_time = time.time()

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat",
            json=payload,
            headers=headers,
            timeout=60,
        )
    except requests.RequestException as exc:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "API request failed | duration: %.0fms | error: %s",
            duration_ms,
            str(exc),
        )
        return "I could not reach the assistant service. Please try again."

    duration_ms = (time.time() - start_time) * 1000

    if response.status_code != 200:
        logger.warning(
            "API error response | status: %d | duration: %.0fms",
            response.status_code,
            duration_ms,
        )

    if response.status_code == 401:
        return "Your session is no longer valid. Please sign in again."

    if response.status_code == 403:
        return "You do not have permission to perform this action."

    if response.status_code != 200:
        return "The assistant could not process this request. Please try again."

    try:
        data: dict[str, Any] = response.json()
    except ValueError:
        logger.error("Failed to parse API response as JSON")
        return "The assistant returned an unreadable response."

    answer = str(data.get("answer") or "No answer was returned.")

    logger.info(
        "API response | status: %d | duration: %.0fms | answer_length: %d | conversation: %s",
        response.status_code,
        duration_ms,
        len(answer),
        conversation_id,
    )

    return answer
