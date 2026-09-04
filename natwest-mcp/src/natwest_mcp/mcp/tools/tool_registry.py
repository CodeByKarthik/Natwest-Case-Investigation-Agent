from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .business_tools import (
    add_issue_update,
    complete_next_action,
    create_next_action,
    get_customer_by_name,
    get_issue_by_external_ref,
    list_customers,
    list_issue_updates,
    list_next_actions,
    list_open_issues,
    update_issue_status,
    update_next_action,
)

# ----- Define tool metadata (function, annotations) ------

TOOLS: list[tuple[Callable[..., Any], ToolAnnotations | None]] = [
    (list_customers, ToolAnnotations(readOnlyHint=True)),
    (get_customer_by_name, ToolAnnotations(readOnlyHint=True)),
    (list_open_issues, ToolAnnotations(readOnlyHint=True)),
    (get_issue_by_external_ref, ToolAnnotations(readOnlyHint=True)),
    (list_issue_updates, ToolAnnotations(readOnlyHint=True)),
    (list_next_actions, ToolAnnotations(readOnlyHint=True)),
    (update_issue_status, None),
    (add_issue_update, None),
    (create_next_action, None),
    (update_next_action, None),
    (complete_next_action, None),
    # ---- Add new tools above this line ----
]


def register_all_tools(mcp: FastMCP) -> None:
    """
    Register all business tools on the MCP server.
    """
    for func, annotations in TOOLS:
        if annotations is not None:
            mcp.tool(name=func.__name__, annotations=annotations)(func)
        else:
            mcp.tool(name=func.__name__)(func)
