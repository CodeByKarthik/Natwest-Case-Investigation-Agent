from __future__ import annotations

import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from natwest_shared.utils.logger import get_logger

from natwest_backend.agent.prompts.guardrails import INPUT_GUARDRAIL_PROMPT
from natwest_backend.agent.shared.parsing import content_to_text
from natwest_backend.agent.shared.state import AgentState

logger = get_logger(__name__)

DENIAL_MESSAGE = (
    "I'm unable to process this request. Your message was flagged "
    "by our security review. Please rephrase your question as a "
    "normal business operations query."
)


# ----- Layer 1: Pattern-based detection -------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # Direct instruction override
        r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directions?)",
        r"disregard\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?)",
        r"forget\s+(all\s+)?(previous|prior|above|your)\s+(instructions?|prompts?|rules?)",
        r"override\s+(your|the|all|system)\s+(instructions?|prompts?|rules?|settings?)",
        # Persona hijacking
        r"you\s+are\s+now\s+(?:a\s+)?(?:different|new|my|an?\s+)",
        r"act\s+as\s+(?:if\s+)?(?:you\s+(?:are|were)\s+)?(?:a\s+)?(?:different|unrestricted|unfiltered)",
        r"pretend\s+(?:you\s+are|to\s+be)\s+(?:a\s+)?(?:different|unrestricted|evil)",
        r"switch\s+to\s+(?:a\s+)?(?:different|new|unrestricted)\s+(?:mode|persona|role)",
        r"enter\s+(?:developer|admin|debug|god|sudo|jailbreak)\s+mode",
        # System prompt extraction
        r"(?:show|print|display|reveal|output|repeat|dump)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions|rules|configuration)",
        r"what\s+(?:are|is)\s+your\s+(?:system\s+)?(?:prompt|instructions|rules|initial\s+instructions)",
        r"(?:copy|paste|echo)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)",
        # Delimiter / context escape
        r"<\s*/?\s*(?:system|instructions?|prompt|rules)\s*>",
        r"\[\s*(?:system|INST|instructions?)\s*\]",
        r"```\s*(?:system|prompt|instructions)",
        r"#{3,}\s*(?:system|new\s+instructions|override)",
        # Role elevation
        r"i\s+am\s+(?:a|an|the)\s+(?:admin|administrator|developer|root|superuser|system)",
        r"(?:give|grant)\s+(?:me|yourself)\s+(?:admin|root|elevated|full)\s+(?:access|permissions?|privileges?)",
        r"bypass\s+(?:all\s+)?(?:security|authentication|authorization|rbac|permissions?|restrictions?)",
        # DAN / known jailbreaks
        r"\bDAN\b",
        r"do\s+anything\s+now",
        r"jailbreak",
        r"opposite\s+mode",
    ]
]


def _pattern_check(text: str) -> str | None:
    """
    Run all injection patterns against the input.

    Returns the matched pattern string if found, None if clean.
    """
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


# ----- Node factory -----


def create_input_guardrail_node(llm: BaseChatModel) -> Any:
    """
    Factory that returns the input guardrail node function.

    Layer 1 (patterns) runs first. If clean, layer 2 (LLM) runs.
    If either flags the input, the node blocks the request.
    """

    async def input_guardrail_node(
        state: AgentState, config: RunnableConfig
    ) -> dict[str, Any]:
        last_message = state["messages"][-1]
        user_text = content_to_text(last_message.content)

        # --- Layer 1: Pattern matching ---
        matched = _pattern_check(user_text)
        if matched:
            logger.warning(
                "Guardrail BLOCKED (pattern) | match: '%s' | input: %.100s",
                matched,
                user_text,
            )
            return {
                "route": "blocked",
                "messages": [AIMessage(content=DENIAL_MESSAGE)],
            }

        # --- Layer 2: LLM classification ---
        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content=INPUT_GUARDRAIL_PROMPT),
                    HumanMessage(content=user_text),
                ],
                config=config,
            )

            verdict_raw = content_to_text(response.content).strip().upper()
            # Only block on an unambiguous verdict — strip surrounding quotes
            # and take the first word so trailing commentary cannot trigger
            # a false positive.
            verdict = (
                verdict_raw.strip('"').strip("'").split()[0] if verdict_raw else ""
            )

            if verdict == "BLOCKED":
                logger.warning(
                    "Guardrail BLOCKED (llm) | input: %.100s",
                    user_text,
                )
                return {
                    "route": "blocked",
                    "messages": [AIMessage(content=DENIAL_MESSAGE)],
                }
            if verdict != "SAFE":
                logger.warning(
                    "Guardrail returned unexpected verdict '%s' — allowing request | input: %.100s",
                    verdict_raw[:50],
                    user_text,
                )

        except Exception:
            # If the guardrail LLM call fails, allow the request
            # through rather than blocking legitimate queries.
            logger.exception("Guardrail LLM call failed, allowing request")

        logger.info("Guardrail passed | input: %.100s", user_text)
        return {"route": "safe"}

    return input_guardrail_node
