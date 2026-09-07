"""
Chat assistant UI with full conversation history.

Uses Streamlit's built-in chat components (st.chat_message,
st.chat_input) for a familiar chat interface. Message history
persists in st.session_state for the duration of the session.
"""

from __future__ import annotations

import streamlit as st

from natwest_frontend.auth.session import get_logged_in_user, logout
from natwest_frontend.client.api_client import call_agent_api
from natwest_frontend.utils.logger import get_logger

logger = get_logger(__name__)


def _initialize_chat_state() -> None:
    """Ensure chat history exists in session state."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []


def _render_sidebar() -> None:
    """Render the sidebar with user info and controls."""
    with st.sidebar:
        st.markdown(f"**Signed in as:** {get_logged_in_user()}")
        st.divider()

        if st.button("New conversation", use_container_width=True):
            logger.info("User started a new conversation")
            st.session_state["messages"] = []
            st.session_state.pop("conversation_id", None)
            st.rerun()

        if st.button("Logout", use_container_width=True):
            logger.info("User logged out")
            logout()


def _render_chat_history() -> None:
    """Display all previous messages in the chat window."""
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def _handle_user_input() -> None:
    """Process new user input and get agent response."""
    prompt = st.chat_input(
        placeholder="Ask about customers, issues, or request an escalation summary..."
    )

    if not prompt:
        return

    logger.info("User input received | length: %d", len(prompt))

    # Display and store user message
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = call_agent_api(prompt)
        st.markdown(answer)

    # Store assistant response
    st.session_state["messages"].append({"role": "assistant", "content": answer})

    logger.info(
        "Turn completed | total_messages: %d",
        len(st.session_state["messages"]),
    )


def render_assistant() -> None:
    """Main entry point for the chat assistant UI."""
    _initialize_chat_state()
    _render_sidebar()
    _render_chat_history()
    _handle_user_input()
