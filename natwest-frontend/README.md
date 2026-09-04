# natwest-frontend

Streamlit chat interface with Keycloak OAuth 2.0 authentication.

## Structure

```
src/natwest_frontend/
├── app.py                  # Streamlit entry point — auth routing, page config
├── config.py               # Frontend settings (Keycloak URLs, API endpoint, ports)
│
├── auth/                   # Authentication
│   ├── oauth.py            # OAuth state generation and HMAC validation
│   └── session.py          # Token exchange, refresh, storage, logout, JWT decoding
│
├── client/                 # API communication
│   └── api_client.py       # POST /api/chat with bearer token, conversation ID, timeouts
│
├── ui/                     # User interface
│   ├── login.py            # Branded login page with Keycloak SSO link
│   └── assistant.py        # Chat UI — message history, sidebar, input handling
│
└── utils/
    └── logger.py           # Structured logging for frontend events
```

## Auth flow

1. User opens the app → `login.py` renders with a Keycloak SSO link
2. User authenticates at Keycloak → redirected back with an auth code
3. `session.py` exchanges the code for JWT tokens (access + refresh)
4. Tokens stored in `st.session_state`, forwarded with every API call
5. Token refresh happens automatically before expiry (30-second skew)

## Chat flow

1. User types a message in `st.chat_input`
2. `api_client.py` sends `POST /api/chat` with the bearer token and conversation ID
3. Response displayed via `st.chat_message`
4. Full message history maintained in `st.session_state` for the session

## Features

- OAuth 2.0 with HMAC-signed state parameter to prevent CSRF
- Automatic token refresh before expiry
- Conversation ID tracking for Redis-backed multi-turn memory
- New conversation button clears session and generates a fresh ID
- Sidebar shows authenticated user and role
