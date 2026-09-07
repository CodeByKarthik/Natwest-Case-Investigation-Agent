# natwest-frontend

Streamlit user interface for the NatWest Case Investigation Agent. It provides the internal case worker experience for sign-in, conversation handling, and safe interaction with the backend investigation API.

## Structure

```
src/natwest_frontend/
├── app.py                                              # Streamlit entry point with authentication gate and page setup
├── config.py                                           # Frontend configuration for Keycloak and API endpoints
│
├── auth/                                               # Session and OAuth handling
│   ├── oauth.py                                        # OAuth state creation and HMAC validation
│   └── session.py                                      # Token exchange, validation, refresh and logout logic
│
├── client/                                             # API integration layer
│   └── api_client.py                                   # Calls the backend /api/chat endpoint with the user bearer token
│
├── ui/                                                 # User-facing screens
│   ├── login.py                                        # Keycloak SSO login screen for NatWest staff
│   └── assistant.py                                    # Assistant chat view with session state and message rendering
│
├── utils/                                              # Supporting helpers
│   └── logger.py                                       # Frontend logging utilities
│
├── __init__.py                                         # Package marker
└── py.typed                                            # Typing marker for the package
```

## Auth flow

1. The user opens the Streamlit app and lands on the login screen.
2. The frontend generates a secure OAuth state and redirects the user to Keycloak.
3. Keycloak returns the code and the frontend exchanges it for tokens.
4. Access tokens are stored in the session and included in backend API calls.
5. Expired tokens are refreshed automatically before the user continues the flow.

## Chat flow

1. The user enters a case or operational query in the chat UI.
2. The frontend sends the message to the backend API with the current bearer token.
3. The backend runs the investigation workflow and returns a grounded response.
4. The frontend renders the response and keeps the conversation history in session state.

## Operational use

The frontend is intentionally simple and secure:

- single sign-on is handled through Keycloak
- each request uses the user’s validated token
- the session can be reset with a fresh conversation
- the sidebar surfaces authenticated user and role context

## Local run

```bash
cd natwest-frontend
uv run streamlit run src/natwest_frontend/app.py
```

This is typically used in conjunction with the Docker Compose stack for normal application execution.
