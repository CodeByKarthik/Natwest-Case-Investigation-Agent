# natwest-backend

FastAPI backend service housing the LangGraph agent, per-request evaluation pipeline, Redis caching layer, and MCP client adapter. This is the core of the NatWest Case Investigation Agent — it receives authenticated requests, runs the agent pipeline, and returns evaluated responses.

## Structure

```
src/natwest_backend/
├── config.py                           # App settings (LLM, Redis, LangSmith, Azure OpenAI)
│
├── api/                                # ── API layer ──
│   ├── app.py                          # App factory, middleware + router registration
│   ├── auth.py                         # JWT extraction, Keycloak JWKS validation, AuthContext
│   ├── routes/
│   │   ├── chat.py                     # POST /api/chat — entry point, background eval trigger
│   │   ├── health.py                   # GET /health — container liveness probe
│   │   └── me.py                       # GET /me — returns authenticated user context
│   └── middleware/
│       ├── middleware.py               # Request/response logging, latency, correlation IDs
│       └── observability.py            # Structlog JSON config, request ID context var
│
├── agent/                              # ── Intelligence layer ──
│   ├── graph_builder.py                # StateGraph assembly — wires all nodes and edges
│   ├── service.py                      # AgentService — orchestrates MCP, graph, Redis per request
│   │
│   ├── nodes/                          # Graph node factories
│   │   ├── input_guardrail_node.py     # Layer 1: 20+ regex patterns, Layer 2: LLM classifier
│   │   ├── router_node.py             # LLM intent classification → route string
│   │   ├── react_agent_node.py        # ReAct loop — LLM reasoning with bound tools
│   │   ├── tool_node.py               # Tool executor wrapper with call counter
│   │   └── skill_node.py             # Skill node factories (escalation summary)
│   │
│   ├── graph/                          # Graph wiring and control flow
│   │   ├── routing.py                 # Route constants (SKILL_ROUTES, DEFAULT_ROUTE, BLOCKED)
│   │   ├── conditions.py             # Edge functions (should_continue, route_after_guardrail)
│   │   └── registry.py               # Skill builder registry — add new skills here
│   │
│   ├── skills/                         # Skill implementations
│   │   └── escalation_summary.py      # Extract → fetch → gather → synthesise workflow
│   │
│   ├── prompts/                        # All LLM prompts (separated from logic)
│   │   ├── system.py                  # Agent system prompt (templated with {username}, {role})
│   │   ├── router.py                  # Intent classification with examples
│   │   ├── guardrails.py             # Security classifier (SAFE / BLOCKED)
│   │   └── skills/
│   │       ├── escalation_summary.py  # Name extraction + executive summary synthesis
│   │       └── fallback_response.py   # Structured error → user-facing message
│   │
│   ├── shared/                         # Shared agent utilities
│   │   ├── llm_factory.py            # OpenAI primary + Azure OpenAI fallback with logging
│   │   ├── state.py                  # AgentState TypedDict (messages, route, tool_call_count)
│   │   ├── memory.py                 # Conversation trimming — keeps last 10 turns
│   │   ├── skill_limits.py           # Configurable caps (max tools, max issues, max MCP calls)
│   │   ├── tool_adapter.py           # MCP schema → Pydantic → LangChain BaseTool conversion
│   │   ├── parsing.py                # Content normalisation (str | list → plain text)
│   │   └── fallback_response.py      # LLM-authored error responses from structured context
│   │
│   ├── mcp_client/                     # MCP server integration
│   │   ├── transport.py               # Streamable HTTP connection with bearer token forwarding
│   │   ├── client_connection.py       # Tool discovery, invocation, Redis cache check/set
│   │   └── result_parser.py           # TextContent extraction, safe JSON parsing
│   │
│   ├── cache/                          # Redis caching layer
│   │   ├── redis_client.py            # Async connection pool (singleton, shared across requests)
│   │   ├── conversation_memory.py     # Chat history serialisation/deserialisation (30-min TTL)
│   │   └── tool_cache.py             # Read-only tool result cache (5-min TTL, write-through)
│   │
│   └── evaluation/                     # Response quality scoring
│       ├── scorer.py                  # LLM-as-judge (groundedness, relevance, hallucination)
│       ├── scores.py                  # EvaluationScores dataclass
│       ├── prompts.py                 # Judge prompt (factual vs advisory distinction)
│       ├── langsmith_feedback.py      # Submit scores as feedback on LangSmith traces
│       ├── background_task.py         # Async runner — zero latency impact on user
│       └── run_eval.py               # 20-test automated evaluation harness
```

## Agent pipeline

Every user message passes through these stages in order:

```
User message
  → Input guardrail (pattern matching → LLM classifier)
  → Router (intent classification)
  → Agent node (ReAct reasoning) ↔ Tool node (MCP calls)    [loop, max 15 calls]
     OR
  → Skill node (deterministic multi-step workflow)
  → Response delivered
  → Background evaluation (async, logged to LangSmith)
```

## API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/chat` | Bearer JWT | Send a message to the agent, receive a response |
| GET | `/health` | None | Container health check |
| GET | `/me` | Bearer JWT | Returns the authenticated user's role and identity |

## Agent nodes

| Node | Purpose | Implementation |
|------|---------|----------------|
| Input guardrail | Block prompt injection, jailbreaks, social engineering | 20+ regex patterns + LLM classifier |
| Router | Classify intent → choose graph branch | LLM with examples for each route |
| Agent | ReAct reasoning with tool selection | LLM with 11 MCP tools bound |
| Tool | Execute MCP tool calls | ToolNode wrapper with call counter |
| Escalation skill | Structured executive summary workflow | 5-step MCP data gathering + LLM synthesis |

## Caching

| Cache | Key pattern | TTL | What it stores |
|-------|-------------|-----|----------------|
| Conversation memory | `conversation:{id}` | 30 min | Serialised message history (survives restarts) |
| Customer lookups | `tool_cache:get_customer_by_name:{hash}` | 5 min | Customer profile JSON |
| Read-only tools | `tool_cache:{tool}:{hash}` | 5 min | Issue listings, updates, actions |

Write tool results and error responses are never cached.

## Evaluation

Every response is scored automatically after delivery:

| Metric | Method | Scale |
|--------|--------|-------|
| Groundedness | LLM-as-judge | 1–5 |
| Relevance | LLM-as-judge | 1–5 |
| Hallucination | LLM-as-judge | 1–5 |
| Tool selection | Deterministic | pass / fail |
| RBAC compliance | Deterministic | pass / fail |

Scores are logged to LangSmith as feedback on each trace. The evaluation LLM call runs with tracing disabled to avoid polluting the trace board.

## LLM factory

`llm_factory.py` creates the LLM with OpenAI as primary and Azure OpenAI as automatic fallback via LangChain's `.with_fallbacks()`. A callback handler logs which provider handled each call. Switching providers is an environment variable change with zero code modifications.

## Safety limits

| Limit | Value | Enforced by |
|-------|-------|-------------|
| Max tool calls per request | 15 | `conditions.py` |
| Conversation window | 10 turns | `memory.py` |
| Skill MCP calls | 20 | `skill_limits.py` |
| Skill issues processed | 5 | `skill_limits.py` |
