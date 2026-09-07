# natwest-backend

FastAPI backend service for the NatWest Case Investigation Agent. It handles authenticated requests, routes them through the investigation graph, invokes the MCP tool layer, stores short-lived conversational state in Redis, and emits post-response evaluation signals for quality and RBAC checks.

## Structure

```
src/natwest_backend/
├── config.py                                             # Application settings for LLM, Redis, Keycloak, LangSmith and API configuration
│
├── api/                                                  # API layer
│   ├── app.py                                            # FastAPI application factory and router registration
│   ├── auth.py                                           # JWT extraction, Keycloak token validation and auth-context derivation
│   ├── routes/                                           # HTTP entry points
│   │   ├── chat.py                                       # POST /api/chat — executes the agent workflow for a user request
│   │   ├── health.py                                     # GET /health — liveness probe for the service container
│   │   └── me.py                                         # GET /me — returns the authenticated user and role metadata
│   └── middleware/                                       # Request timing, logging and observability
│       ├── middleware.py                                 # Request-id and latency middleware
│       └── observability.py                              # Structured logger and context configuration
│
├── agent/                                                # Intelligence and orchestration layer
│   ├── graph_builder.py                                  # Builds the LangGraph workflow and links all nodes together
│   ├── service.py                                        # AgentService — coordinates requests, Redis memory and MCP access
│   ├── graph/                                            # Workflow routes and decision logic
│   │   ├── routing.py                                    # Intent route constants and category definitions
│   │   ├── conditions.py                                 # Edge functions for continuation and guardrail handling
│   │   └── registry.py                                   # Skill and tool registration for graph assembly
│   ├── nodes/                                            # Graph nodes for routing, guardrails and execution
│   │   ├── input_guardrail_node.py                       # Security guardrail checks and prompt-injection screening
│   │   ├── router_node.py                                # Maps user intent to investigation or operational routes
│   │   ├── react_agent_node.py                           # ReAct reasoning loop with tool invocation
│   │   ├── tool_node.py                                  # Executes MCP calls and tracks tool usage
│   │   ├── investigation_finalize_node.py                # Finalises the investigation response
│   │   └── investigation_node.py                         # Case investigation workflow node
│   ├── skills/                                           # Structured agent workflows
│   │   └── investigation_workflow.py                     # Full case investigation sequence across evidence and status checks
│   ├── tools/                                            # Agent-facing workflow tools
│   │   └── investigation_tool.py                         # Tool wrapper that calls the investigation workflow
│   ├── prompts/                                          # Prompt templates used by guardrails and reasoning
│   │   ├── system.py                                     # Main system prompt for the NatWest investigation assistant
│   │   ├── router.py                                     # Prompt used to classify user intent
│   │   ├── guardrails.py                                # Safe vs blocked classification prompt
│   │   └── skills/                                       # Investigation and fallback response prompts
│   │       ├── investigation.py                          # Structured case investigation instructions
│   │       └── fallback_response.py                      # Prompt for user-safe fallback responses
│   ├── shared/                                           # Shared agent utilities
│   │   ├── llm_factory.py                                # LLM factory with OpenAI and Azure OpenAI handling
│   │   ├── state.py                                      # Typed state for graph execution
│   │   ├── memory.py                                     # Conversation trimming and turn-window management
│   │   ├── skill_limits.py                               # Caps for tool usage and workflow depth
│   │   ├── tool_adapter.py                               # MCP schema adaptation into LangChain tools
│   │   ├── parsing.py                                    # Normalisation for tool outputs and message content
│   │   └── fallback_response.py                          # Structured fallback generation for blocked or failed requests
│   ├── mcp_client/                                       # MCP server communication layer
│   │   ├── transport.py                                  # Connection setup and streamable HTTP transport handling
│   │   ├── client_connection.py                          # Tool discovery, invocation and Redis-based result caching
│   │   └── result_parser.py                              # Safe parsing of MCP content payloads
│   ├── cache/                                            # Redis-backed caching and memory
│   │   ├── redis_client.py                               # Shared async Redis connection
│   │   ├── conversation_memory.py                        # Session memory persistence for recent turns
│   │   └── tool_cache.py                                 # Cache for read-only tool results
│   └── evaluation/                                       # Quality gates and response scoring
│       ├── scorer.py                                     # Evaluates groundedness, relevance and RBAC compliance
│       ├── scores.py                                     # Typed evaluation score result object
│       ├── prompts.py                                    # Judge prompt for post-response assessment
│       ├── langsmith_feedback.py                         # Publishes evaluation feedback to LangSmith
│       ├── background_task.py                            # Async evaluation task runner
│       └── run_eval.py                                   # Legacy evaluation runner for local benchmarking
│
└── scripts/                                              # Operational scripts
    └── run_golden_dataset.py                             # End-to-end golden dataset validation for NatWest case scenarios
```

## Agent pipeline

Every request follows a similar operational path:

```
User message
  → input guardrail
  → intent routing
  → investigation workflow or operational query
  → MCP tool execution
  → final response generation
  → background evaluation and logging
```

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat` | Submit a user message to the investigation assistant |
| GET | `/health` | Service health check |
| GET | `/me` | Return the authenticated user and role information |

## Evaluation and safety

The backend includes both runtime guardrails and evaluation checks:

- prompt-injection and off-topic detection before execution
- intent routing to either investigation or safe fallback behaviour
- RBAC compliance checks against the NatWest role model
- post-response quality scoring for groundedness and relevance
- Redis-based memory and tool caching to reduce repetitive data fetches

## Local run

```bash
cd natwest-backend
uv run python -m natwest_backend.api.app
```

The service is designed to run behind the Docker Compose stack, but the module can also be exercised locally for debugging and test runs.
