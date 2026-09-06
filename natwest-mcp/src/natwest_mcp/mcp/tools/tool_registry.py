from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .business_tools import (
    add_case_note,
    get_case_details,
    get_case_timeline,
    get_customer_accounts,
    get_customer_profile,
    get_next_actions,
    list_cases,
    list_customers,
    manage_next_action,
    update_case_status,
)

TOOLS: list[tuple[Callable[..., Any], ToolAnnotations | None]] = [
    (list_customers, ToolAnnotations(read_only_hint=True)),
    (list_cases, ToolAnnotations(read_only_hint=True)),
    (get_customer_profile, ToolAnnotations(read_only_hint=True)),
    (get_customer_accounts, ToolAnnotations(read_only_hint=True)),
    (get_case_details, ToolAnnotations(read_only_hint=True)),
    (get_case_timeline, ToolAnnotations(read_only_hint=True)),
    (update_case_status, None),
    (get_next_actions, ToolAnnotations(read_only_hint=True)),
    (manage_next_action, None),
    (add_case_note, None),
]


def register_all_tools(mcp: FastMCP) -> None:
    """Register all NatWest business tools on the MCP server."""
    for func, annotations in TOOLS:
        if annotations is not None:
            mcp.tool(name=func.__name__, annotations=annotations)(func)
        else:
            mcp.tool(name=func.__name__)(func)
