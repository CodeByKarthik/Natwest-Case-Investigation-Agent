from dataclasses import dataclass


@dataclass(frozen=True)
class AgentLimits:
    """
    Configurable limits for general agent execution.
    """

    max_conversation_turns: int = 10
    max_tool_calls: int = 15


@dataclass(frozen=True)
class SkillLimits:
    """
    Configurable caps for skill workflows.

    - max_issues: Maximum open issues to process. Issues beyond this
    limit are noted in the summary as truncated.

    - max_updates_per_issue:  Maximum timeline updates to fetch
    per issue (newest first).

    - max_actions_per_issue:  Maximum next actions to fetch
    per issue.

    - max_mcp_calls: Hard cap on total MCP tool calls
    within a single skill execution.
    """

    max_issues: int = 5
    max_updates_per_issue: int = 5
    max_actions_per_issue: int = 5
    max_mcp_calls: int = 20


# Default instance used across the application

DEFAULT_AGENT_LIMITS = AgentLimits()
DEFAULT_SKILL_LIMITS = SkillLimits()
