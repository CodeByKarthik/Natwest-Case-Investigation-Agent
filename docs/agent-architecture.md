# Agent Architecture

The NatWest Case Investigation Agent is a custom LangGraph `StateGraph` not a generic ReAct wrapper. This gives explicit control over safety, routing, tool usage, and case-investigation workflow logic.

## Agent workflow diagram

<img width="2720" height="2480" alt="natwest-agent-architecture" src="https://github.com/user-attachments/assets/a748a18a-ab74-4e12-907d-8cc9ed1b99da" />


## Why a custom StateGraph

A standard prebuilt ReAct setup is not enough because the system needs:

- input guardrails before any reasoning begins
- role-aware routing based on intent
- deterministic case-investigation workflow steps
- per-request evaluation hooks
- explicit safety and tool-call limits

A custom `StateGraph` lets each stage of the request lifecycle be controlled, audited, and extended predictably.

## AI Harness (bounded LLM execution)

The AI Harness separates what the LLM does from what deterministic code does. It is the single most important design decision for deploying agentic AI safely in a regulated environment.

**What the LLM does:**
- Reasoning (identifying risks, spotting patterns)
- Decision-making (which tool to call, which action to recommend)
- Natural language understanding (interpreting requests, resolving references)
- Structured summarisation (case summaries, recommendations)

**What deterministic code does — everything the user sees:**
- **Tool responses** — data structures produced by code from the database
- **Permission denials** — specific messages returned by the tool layer, forwarded verbatim by the LLM
- **Investigation report formatting** — the renderer converts structured LLM output into the final markdown
- **Error messages** — case not found, tool failures, validation errors
- **Approval prompts** — human-in-the-loop confirmations triggered by code based on action type
- **Audit trail entries** — case events, LangSmith traces, evaluation scores captured automatically

**Why this matters:**

Without the AI Harness, an LLM under adversarial prompting could invent a permission response, fabricate a citation, or hallucinate an approval confirmation. With the AI Harness, none of these are possible — the LLM is never the source of these outputs. It reasons about them; the deterministic layer produces them.

This is the boundary that makes agentic AI safe to deploy in a regulated environment.

## Request flow

Every request enters the graph in the same structured sequence:

```text
User message
  → Input guardrail
  → Router
  → Investigation workflow / operational query path
  → MCP tool execution
  → Final response
  → Background evaluation
```

Responsibilities are split cleanly:

- guardrail blocks unsafe or out-of-scope prompts
- router decides how the request is handled
- investigation workflow performs case-based reasoning and evidence gathering
- tool layer executes NatWest data operations under RBAC
- final response is composed only from grounded tool results

## Graph structure

The graph is built around five explicit nodes:

1. input guardrail
2. router
3. agent or investigation
4. tool
5. finalization

This is easier to reason about than a single large agent loop.

## Nodes

### Input guardrail

Two-step safety check:

- **Layer 1:** regex checks for prompt injection, role takeover, jailbreak, prompt-extraction, off-topic bypasses
- **Layer 2:** LLM classifier that decides `SAFE` or `BLOCKED`

If either layer flags the request, it stops before the router.

### Router

Small LLM-based intent classifier. Routes into:

- `INVESTIGATION` — full NatWest case investigation
- `OPERATIONAL_QUERY` — direct question about customers, accounts, cases, or status

The router only classifies intent. It does not extract data or select tools.

### Investigation workflow

The central NatWest-specific execution path — deterministic, structured, evidence-based (detailed in the next section).

### Agent node

Handles the operational query path for non-investigation requests. Receives the system prompt, conversation turns, role context, and available MCP tools. The LLM decides whether to chain tool calls to answer.

### Tool node

Wraps MCP execution. Invokes NatWest business tools, tracks tool call count, keeps the workflow bounded and auditable, returns structured results. Every tool invocation is constrained by the current app role and the business service layer — the model cannot bypass authorization by reasoning around the prompt.

### Finalization node

Converts the investigation or agent output into the final user-facing response. Ensures the answer is grounded in evidence and aligned with the request scope.

## The 9-step investigation workflow

When the router classifies a request as `INVESTIGATION`, the workflow follows a fixed order. The LLM contributes reasoning within each step, but never decides which step runs next or which tool to invoke.

**Phase 1 — Data gathering (deterministic tool calls):**

1. **Resolve case identifier.** Accepts case_id, case_ref, or customer_name. If a customer_name is given, `list_customers` resolves the customer, then their most relevant active case is selected.

2. **Fetch case details.** `get_case_details` retrieves status, priority, case type, disputed amount, merchant, Consumer Duty flag, assigned team.

3. **Fetch customer profile.** `get_customer_profile` retrieves KYC status, tier, and vulnerability register entries (active and resolved).

4. **Fetch customer accounts.** `get_customer_accounts` retrieves active accounts for financial context.

5. **Retrieve related cases.** `list_cases` filtered by customer_id retrieves all other cases — active and historical — enabling pattern detection.

6. **Retrieve case timeline.** `get_case_timeline` fetches every event: system alerts, status changes, notes, customer contacts, document exchanges, with source system records where applicable.

**Phase 2 — LLM reasoning (structured LLM calls):**

7. **Identify risk indicators.** The LLM produces a structured list of risks — each cited to a specific source (record, system, confidence score) with an explanation of why it matters in this case.

8. **Identify evidence gaps.** The LLM identifies what should be present but isn't — no customer contact despite an active vulnerability signal, no `request_documents` action despite a disputed amount above threshold. Each gap is cited to the record or attribute that highlights it.

9. **Recommend next action.** The LLM produces a single recommended action from a fixed enum (contact_customer, request_documents, issue_refund, escalate_fraud, escalate_vulnerability, kyc_refresh, add_case_note). It also produces case summary, customer context, vulnerability context, and reasoning that cite the earlier risks and gaps.

The workflow terminates at step 9. The rendered investigation report becomes the final AI message — no further LLM turn. The deterministic renderer produces the user-facing markdown from the structured LLM output.

This design gives two properties simultaneously: **the LLM does the reasoning that requires judgment**, and **the workflow guarantees the same six systems get consulted every time** — regardless of what the LLM might otherwise skip.

## State model

The agent state moves the request through the graph explicitly. It stores:

- conversation messages
- selected route
- current tool-call count
- workflow context needed by the investigation path

This makes data flow explicit and prevents hidden state changes between nodes.

```python
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    route: str
    tool_call_count: int
    skill_context: str
```

## Safety and control limits

| Limit | Value | Enforced by |
|---|---:|---|
| Max tool calls per request | 15 | `conditions.py` |
| Conversation window | 10 turns | `memory.py` |
| Investigation workflow depth | bounded by graph logic | workflow orchestration |

The system works with internal NatWest case data — accuracy and policy compliance matter more than unrestricted agentic exploration.

## Why this design fits the NatWest use case

- routes case-related requests into a structured investigation flow
- enforces consented access through the MCP and business service layers
- keeps the LLM inside permission boundaries
- supports customer, case, and operational queries in a governed way
- provides a clear audit trail through evaluation, tool use, and response output

The agent is not a freeform assistant. It is a controlled investigation copilot operating inside a role-aware banking operations environment.
