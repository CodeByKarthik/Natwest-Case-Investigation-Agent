# NatWest Case Investigation Agent

NatWest Case Investigation Agent is an internal investigation assistant for NatWest operations teams. It supports customer support, fraud investigators, and case managers by helping them review customer profiles, investigate flagged cases, access the case timeline, and complete approved case actions within a governed workflow.

## Product use case

The platform is designed for NatWest case handling and customer-risk investigations. It gives authorised staff the ability to:

- search and review customer and account information
- inspect active and historical case details
- review source-system signals and vulnerability data
- track the full case timeline and next actions
- update case status and add case notes according to role-based permissions
- receive AI-assisted investigation summaries in a controlled operational workflow

## Quick start

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Update the required values in `.env` for PostgreSQL, Redis, Keycloak, and LLM settings.

3. Start the full stack:

   ```bash
   docker compose up -d 
   ```

4. After startup, the platform will bring up:

   - PostgreSQL
   - Redis
   - Keycloak with the NatWest realm
   - database migration and seed tasks
   - the MCP server
   - the backend API
   - the Streamlit frontend


## Core services

- `natwest-backend` — API, agent orchestration, guardrails, routing, workflow execution, evaluation hooks
- `natwest-mcp` — external tool layer exposing business operations to the agent with JWT validation
- `natwest-shared` — shared auth and domain model layer for database access, RBAC, and schemas
- `natwest-frontend` — user-facing interface for authenticated NatWest staff

## Role model

The platform enforces a clear operating model for case handling:

- `customer_support` — read access to customer and case information
- `fraud_investigator` — read access and ability to progress active investigation statuses
- `case_manager` — full operational access, including closure and next-action management.

## Typical workflow

1. Staff signs in through the NatWest frontend using Keycloak.
2. The backend receives the authenticated request and routes it through the agent.
3. The agent chooses an investigation flow or operational query route.
4. The MCP layer executes the required case and customer actions under RBAC.
5. The system returns a grounded response with case references, event context, and evidence-based guidance.

## Local validation

The backend includes a golden-dataset harness for validating investigation flows and permission boundaries.

```bash
cd natwest-backend
uv run python scripts/run_golden_dataset.py
```

This check validates the actual investigation workflow, RBAC enforcement, and response behaviour against a curated set of NatWest case scenarios.

