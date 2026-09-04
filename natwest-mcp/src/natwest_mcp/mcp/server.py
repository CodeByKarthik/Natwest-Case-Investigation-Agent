from fastmcp import FastMCP

from .tools.tool_registry import register_all_tools


def create_mcp_server() -> FastMCP:
    """
    Create and configure the NatWest Operations MCP server.

    - Defines server instructions for tool usage and authentication.
    - Registers all business tools on the server.
    - Returns the configured FastMCP instance ready to run.
    """
    mcp = FastMCP(
        name="NatWest Operations MCP",
        instructions=(
            "Use these tools to retrieve and update NatWest customer, "
            "case, case event, and next-action data. Authentication is provided "
            "through the HTTP Authorization bearer token. Do not ask users for tokens."
        ),
    )

    register_all_tools(mcp)
    return mcp


mcp = create_mcp_server()


def main() -> None:
    """
    Run the MCP server.
    """
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",  # nosec B104
        port=9001,
    )


if __name__ == "__main__":
    main()
