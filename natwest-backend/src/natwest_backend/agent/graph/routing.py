from enum import StrEnum

# --- Guardrail routes ---

BLOCKED_ROUTE = "blocked"
SAFE_ROUTE = "safe"


class IntentCategory(StrEnum):
    """
    User intent categories produced by the router's LLM classification.

    The router only classifies — it never extracts identifiers and never
    invokes workflows. The agent reads this category from the graph state
    and binds the appropriate tools.
    """

    INVESTIGATION = "investigation"
    OPERATIONAL_QUERY = "operational_query"
    UNCLEAR = "unclear"


VALID_CATEGORIES = set(IntentCategory)

# Fallback when the router LLM returns something unexpected — asking a
# clarifying question is safer than guessing.
DEFAULT_CATEGORY = IntentCategory.UNCLEAR
