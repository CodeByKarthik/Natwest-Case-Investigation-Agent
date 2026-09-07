# System Architecture

The NatWest Case Investigation Agent is an internal AI assistant for NatWest customer case handling and investigation workflows. It enables authorised staff to review customer profiles, inspect case records, understand risk indicators, manage case timelines, and take approved operational actions within a controlled and auditable environment.

The architecture is designed as a multi-layered system where each layer enforces its own security and trust boundary so the agent operates in a governed, policy-aware way.

## Five-layer architecture

The application follows a five-layer architecture:

1. Presentation Layer
2. Backend/API Layer
3. Intelligence Layer
4. Tool Layer
5. Data Layer

This extends a traditional web application design by adding an intelligence layer for reasoning and a tool layer for controlled business operations.

## Architecture decisions

- **Security First Architecture:** Agent is the least trusted layer and Role-based access control is enforced in code at the tool layer.
- **AI Harness (LLM Boundary):** The LLM handles reasoning, decision-making, and pattern-spotting. Everything the user sees such as tool responses, permission denials, report formatting, error messages, approval prompts are produced by deterministic code. This is the boundary that makes agentic AI safe to deploy in a regulated environment.
- **Responsible AI principles:** The agent surfaces data gaps honestly, refuses actions outside its scope, and never fabricates source citations. Every claim traces to retrieved data, every response is scored by an LLM-as-judge evaluator for groundedness, relevance, tool selection and hallucination and end to end request are traced using Langsmith.
- **Enterprise Integration:** Keycloak provides identity provider abstraction, integrating with existing enterprise IAM (e.g. Azure Entra) via SSO so that staff use their existing bank credentials and no new identity required. Secrets are managed via Azure Managed Identity and Key Vault, keeping credentials out of code and configuration.
- **Data Residence:** LLM calls use Azure OpenAI, keeping data within the customer's Azure tenant to align with UK regulatory requirements.
- **Golden Dataset:** Tested via a golden dataset of 27 end-to-end scenarios covering all roles, read/write paths, RBAC allow-and-deny boundaries, prompt-injection attempts and edge cases.

### 1. Presentation layer

The **Streamlit frontend** provides the conversation interface for case workers.

Users authenticate through **Keycloak** using the OAuth 2.0 authorization code flow. After successful sign-in, the frontend stores the access token and forwards it with API calls to the backend.

The frontend is responsible for:

- login and session handling
- chat input and message rendering
- passing authenticated requests to the backend

The frontend does not access the database or tool layer directly.

### 2. Backend/API layer

The **FastAPI backend** is the main entry point for authenticated NatWest operations requests.

For each request, the backend validates the JWT, resolves the application user, and loads the associated role, such as `customer_support`, `fraud_investigator`, or `case_manager`.

The backend is responsible for:

- chat requests via `/api/chat`
- health and identity endpoints
- auth validation and user context resolution
- request middleware and observability
- passing user context into the agent workflow

This ensures the agent receives both the user message and the caller’s role before any tool or case operation is attempted.

### 3. Intelligence layer

The LangGraph-based agent is the reasoning engine of the system. It uses a controlled state graph to manage the request lifecycle.

The workflow includes:

- input guardrails
- router node
- ReAct reasoning node
- tool execution node
- case investigation workflow
- final response assembly

Every user message passes through a guardrail check before routing. The router decides whether the request should proceed through an operational query path or a structured investigation workflow. The agent may reason over the request and call tools, but it never touches the database directly.

### 4. Tool layer

The **MCP server** exposes controlled business tools used by the backend agent.

The MCP layer is responsible for:

- registering NatWest business tools
- executing case and account actions on behalf of the agent
- passing requests into shared services
- enforcing RBAC before sensitive operations are performed

Tool calls are executed with the authenticated user context. This ensures that read and write operations follow the permissions associated with the user’s role.

For example:

- `customer_support` can read customer and case data
- `fraud_investigator` can read data and update active investigation statuses
- `case_manager` can manage case progression and next actions

This prevents the agent from bypassing role restrictions even if the user prompt is manipulative or unexpected.

### 5. Data layer

The **PostgreSQL database** stores durable NatWest investigation data, including:

- application users and roles
- customers and account records
- cases and case events
- vulnerability signals and source system records
- next actions and operational notes

Redis provides short-lived conversation memory and tool caching for runtime efficiency. Write operations are never cached and error responses are not persisted, which helps preserve data accuracy and consistency.

## Security model

The NatWest Case Investigation Agent uses layered enforcement points across the architecture.

The frontend authenticates staff through Keycloak OAuth 2.0 and never exposes raw credentials. The API layer validates every JWT independently and resolves the application role. The intelligence layer applies input guardrails to block prompt injection, jailbreak attempts, and out-of-scope requests. The tool layer re-validates authentication and enforces role-based rules before executing each business action. The data layer is only accessed through the shared repository and service layers.

This defence-in-depth approach means that compromising one layer does not grant access to the layers below it. The bearer token flows through the stack, and permissions are enforced at the point of operation.

## Governance and policies

The application is designed with governance at its core. Every interaction with the LLM is scoped to the authenticated user and the business permissions attached to that user.

- The backend uses OpenAI as the primary LLM provider and Azure OpenAI as a fallback option.
- In regulated enterprise deployments, the Azure path is the default choice for data residency and tenant-level controls.
- The agent is not treated as a trusted actor; all operations are mediated through approved tools and domain services.

## Observability and evaluation

Every request is traced end-to-end through LangSmith, capturing the full flow from user input to tool invocation and final response. Traces include the authenticated user, role, conversation ID, routing decision, and evaluation metadata.

After each response, a background evaluation task scores the output across a set of dimensions:

- groundedness
- relevance
- hallucination risk
- tool selection accuracy
- RBAC compliance

These scores are recorded as feedback on each trace, allowing the team to monitor quality and investigate issues in a structured way.

Example of LangSmith logs are shown below:

- https://eu.smith.langchain.com/public/26af45c2-aa65-48cc-8109-f8d15eb3224a/t

## Deployment

The system is containerised and orchestrated using **Docker Compose**. The stack brings up:

- PostgreSQL
- Redis
- Keycloak
- the database bootstrap and migration step
- the NatWest MCP server
- the FastAPI backend
- the Streamlit frontend

The application can be started with:

```bash
docker compose up -d --build
```

The architecture is stateless at the application layer. All session context is stored in Redis, while the durable business domain data remains in PostgreSQL.
