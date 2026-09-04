from __future__ import annotations

import json
from typing import Any

from natwest_shared.utils.logger import get_logger
from mcp.types import TextContent

logger = get_logger(__name__)


def extract_text_content(content_blocks: list[Any]) -> str:
    """
    Extract text from MCP response content blocks.

    Joins all TextContent blocks with newlines.
    Returns a fallback message if no text is found.
    """
    texts: list[str] = []
    for block in content_blocks:
        if isinstance(block, TextContent):
            texts.append(block.text)

    return "\n".join(texts) if texts else "No output returned"


def safe_json_parse(text: str) -> Any:
    """
    Attempt to parse JSON from MCP tool output.

    Returns None on failure rather than raising, so
    callers can handle missing data gracefully.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse MCP response as JSON: %.200s", text)
        return None
