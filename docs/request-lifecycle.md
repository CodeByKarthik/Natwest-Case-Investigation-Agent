# Request Lifecycle and Component Relationship

## Overview

This document explains the runtime flow of the **NatWest Case Investigation Agent** from authentication to final response generation.

The diagram follows the actual product flow for NatWest customer and case investigations: a user signs in, sends a prompt, the backend routes the request through the investigation graph, the MCP server executes approved tools, and the system returns a grounded response using case and customer data from PostgreSQL.

The purpose of this view is to show:

- how internal staff authenticate before accessing the investigation workflow
- how chat requests move from the frontend to the backend
- how the backend resolves user identity and role
- how the agent routes requests and decides whether to investigate or answer operationally
- how tool calls are executed through the MCP server
- how case data is read from PostgreSQL
- how responses are returned to the user
- how traces and evaluation scores are logged asynchronously

## Request lifecycle diagram

The runtime interaction is built from the following components:

| Component | Responsibility |
|---|---|
| User | NatWest staff member using the browser-based interface |
| Streamlit | Frontend interface for sign-in and case investigation chat |
| Keycloak | Identity provider for SSO and JWT issuance |
| Backend | FastAPI service that validates requests and runs the investigation workflow |
| Redis | Stores short-lived conversation memory and cached tool results |
| MCP Server | Executes controlled NatWest business tools with RBAC enforcement |
| PostgreSQL | Stores customers, accounts, cases, events, vulnerability data, and next actions |
| LangSmith | Receives traces, evaluations, and response quality data |

## Request flow

### 1. Authentication flow

When a user opens the app for the first time, the frontend starts the sign-in flow.

```text
User → Streamlit → Keycloak → Streamlit
```

The authentication sequence is:

1. The user opens the Streamlit application.
2. Streamlit redirects the user to Keycloak using OAuth 2.0.
3. The user signs in with their NatWest identity.
4. Keycloak redirects back to the application with an authorization code.
5. Streamlit exchanges the code for access and refresh tokens.
6. Streamlit stores the JWT in the session state.
7. Future requests include the JWT as a bearer token.

This ensures every request carries both identity and role context.

---

### 2. Chat request flow

After authentication, the user submits a natural-language request about a customer or case.

```text
User → Streamlit → Backend
```

The sequence is:

1. The user submits a case investigation prompt in the chat UI.
2. Streamlit sends a `POST /api/chat` request to the backend.
3. The request includes the bearer token.
4. The backend validates the JWT and resolves the app user and assigned role.
5. The backend loads recent conversation history from Redis.
6. The request enters the backend agent workflow.

At this point, the backend has:

- the user message
- the authenticated user identity
- the role context
- the relevant conversation memory

---

### 3. Agent processing flow

The backend sends the request through the investigation graph.

```text
Backend → Input Guardrail → Router → Investigation Workflow / Tool Path
```

The flow is:

1. The input guardrail reviews the prompt before reasoning begins.
2. The router classifies the request as investigation, operational query, or unclear.
3. The backend decides whether a structured investigation workflow is needed.
4. The agent may reason directly or decide to invoke MCP tools.
5. If business data is required, the backend makes the tool request to the MCP server.

The agent is responsible for reasoning and response composition, but it does not access the database directly.

---

### 4. Tool execution flow

When a case, account, or customer fact is required, the backend calls the MCP server.

```text
Backend → MCP Server → PostgreSQL → MCP Server → Backend
```

The tool execution sequence is:

1. The backend sends a business-tool request to the MCP server.
2. The tool request includes the caller’s JWT.
3. The MCP server validates the token and resolves the app user.
4. The MCP server applies RBAC rules before executing the operation.
5. The server queries PostgreSQL when customer or case data is required.
6. PostgreSQL returns the relevant business records.
7. The MCP server sends a structured tool result back to the backend.
8. The backend uses the returned data to continue the investigation or response generation.

This keeps the tool layer as the controlled access boundary for NatWest case data.

---

### 5. Conversation persistence and response flow

After the agent completes reasoning, the backend saves the updated conversation state and returns the final response.

```text
Backend → Redis
Backend → Streamlit → User
```

The response sequence is:

1. The backend stores the updated conversation state in Redis.
2. The backend returns the response payload to Streamlit.
3. Streamlit renders the answer in the chat UI.

Redis is used for short-lived memory so the conversation remains coherent across turns without directly exposing data access patterns.

---

### 6. Observability and evaluation flow

The application sends trace and evaluation data asynchronously to LangSmith.

```text
Backend → LangSmith
```

This happens after the user-facing response is returned, so it does not add user-perceived latency.

LangSmith is used for:

- workflow trace visibility
- tool-call inspection
- routing review
- feedback and evaluation logging
- debugging and quality monitoring
