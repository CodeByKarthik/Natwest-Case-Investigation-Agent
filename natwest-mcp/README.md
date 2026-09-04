# natwest-mcp

FastMCP server exposing eleven business tools over streamable HTTP with per-request JWT validation and RBAC enforcement.

## Structure

```
src/natwest_mcp/
├── mcp/
│   ├── server.py              # FastMCP app factory, server entry point
│   ├── dependencies.py        # Bearer token extraction, auth context builder
│   └── tools/
│       ├── tool_registry.py   # Tool registration with read-only annotations
│       └── business_tools.py  # All 11 tool implementations
```

## Tools

### Read tools (all roles)

| Tool | Description |
|------|-------------|
| `list_customers` | List all customers with health status |
| `get_customer_by_name` | Find customer by partial name match |
| `list_open_issues` | Open, in-progress, or blocked issues for a customer |
| `get_issue_by_external_ref` | Find issue by reference (e.g. ISSUE-101) |
| `list_issue_updates` | Timeline of updates for an issue |
| `list_next_actions` | Pending actions for an issue |

### Write tools (support + admin)

| Tool | Description |
|------|-------------|
| `update_issue_status` | Change issue status |
| `add_issue_update` | Add a progress note to an issue |

### Admin tools (admin only)

| Tool | Description |
|------|-------------|
| `create_next_action` | Create a follow-up action |
| `update_next_action` | Modify an existing action |
| `complete_next_action` | Mark an action as completed |

## Security

Every tool call goes through `dependencies.py` which:

1. Extracts the bearer token from the HTTP `Authorization` header
2. Validates the JWT against Keycloak's JWKS endpoint
3. Resolves the application user and role from PostgreSQL
4. Builds a permission-aware `BusinessService` that enforces RBAC

This validation is independent of the backend's authentication — the MCP server does not trust upstream callers. A tool call with an invalid or expired token is rejected regardless of how it was initiated.

## Transport

The server runs on streamable HTTP (port 9001) rather than stdio, enabling network-based communication from the backend container. Bearer tokens are forwarded on every request by the backend's MCP client adapter.
