from __future__ import annotations

from typing import cast

MessageContent = str | list[str | dict[str, object]]
IssueRecord = dict[str, object]


def content_to_text(content: MessageContent) -> str:
    """
    Normalize LangChain message content into plain text.
    """
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        else:
            text_value = item.get("text")
            if isinstance(text_value, str):
                parts.append(text_value)
            else:
                parts.append(repr(item))
    return " ".join(parts)


def parse_issue_list(raw: object) -> list[IssueRecord]:
    """
    Narrow a parsed JSON value into a list of issue-like dict records.
    """
    if not isinstance(raw, list):
        return []

    raw_items = cast(list[object], raw)
    issues: list[IssueRecord] = []
    for item in raw_items:
        if isinstance(item, dict):
            issues.append(cast(IssueRecord, item))
    return issues
