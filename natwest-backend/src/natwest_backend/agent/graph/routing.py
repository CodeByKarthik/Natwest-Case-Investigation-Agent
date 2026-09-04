# --- Guardrail routes ---

BLOCKED_ROUTE = "blocked"
SAFE_ROUTE = "safe"

# --- Skill routes ---

SKILL_ROUTES: dict[str, str] = {
    "escalation_summary": "escalation_summary",
    # "next_skill": "next_skill_node_name",   ← add new skills here
}

# --- General route ---

DEFAULT_ROUTE = "general"

VALID_ROUTES = set(SKILL_ROUTES.keys()) | {DEFAULT_ROUTE}
