# natwest-mcp

FastMCP server for the NatWest Case Investigation Agent. It exposes the customer and case operations used by the agent behind a secure HTTP transport and validates every request with the NatWest auth model before the operation is executed.

## Structure

```
src/natwest_mcp/
├── __init__.py                                         # Package marker
├── mcp/                                               # MCP server implementation
│   ├── server.py                                       # Creates the FastMCP server and exposes the tool registry
│   ├── dependencies.py                                 # Extracts bearer tokens and resolves the business service for a request
│   └── tools/                                          # Business tools exposed to the agent
│       ├── tool_registry.py                            # Registers available NatWest tools with FastMCP
│       └── business_tools.py                           # Implements customer, case and action operations exposed to the agent
└── py.typed                                            # Typing marker for the package
```

## Tool categories

### Read access tools

These tools are available to authorised readers across the NatWest roles:

- `list_customers` — returns customers with filters such as tier, KYC state or vulnerability flag
- `get_customer_profile` — fetches the full customer profile and linked account context
- `get_customer_accounts` — lists accounts attached to a customer
- `list_cases` — finds cases using filters such as status, priority or case type
- `get_case_details` — fetches a single case by ID or case reference
- `get_case_timeline` — returns the chronological case event history
- `get_next_actions` — lists open follow-up work on a case

### Write access tools

These tools are available to investigators and managers who have case write permissions:

- `update_case_status` — moves a case through its operational lifecycle
- `add_case_note` — appends a note to the case timeline for audit purposes

### Manager-only tools

These tools are restricted to `case_manager` and enforce stricter operational control:

- `manage_next_action` — create, update or complete follow-up action items

## Security model

Every MCP request goes through the same principles as the rest of the app:

1. extract the bearer token from the `Authorization` header
2. validate the token with the Keycloak JWKS configuration
3. resolve the authenticated NatWest user and role from the database
4. load the appropriate business service for permission checks and repository access

The MCP layer does not trust upstream callers. Any invalid, expired or unauthorised request is rejected before the tool executes.

## Transport and runtime

The server runs over streamable HTTP on port `9001` so the backend can make tool calls as a networked service. This also keeps the MCP contract independent from the backend’s own local process boundaries.

## Local run

```bash
cd natwest-mcp
uv run python -m natwest_mcp.mcp.server
```

This is usually launched by Docker Compose, but it can also be started directly during local debugging or smoke testing.
