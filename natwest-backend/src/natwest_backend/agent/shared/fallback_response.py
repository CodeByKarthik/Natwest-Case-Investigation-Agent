from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from natwest_backend.agent.prompts.skills import DATA_FALLBACK_RESPONSE_PROMPT
from natwest_backend.agent.shared.parsing import content_to_text
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI


@dataclass(frozen=True)
class DataFallbackContext:
    reason: str
    entity_type: str
    requested_value: str | None = None
    tool_name: str | None = None
    raw_result: str | None = None
    details: str | None = None


async def build_data_fallback_response(
    llm: ChatOpenAI,
    *,
    user_message: str,
    context: DataFallbackContext,
) -> str:
    """
    Generate a reusable LLM-authored fallback response from
    structured error data.
    """
    error_payload = json.dumps(asdict(context), indent=2, sort_keys=True)
    prompt = DATA_FALLBACK_RESPONSE_PROMPT.format(
        user_message=user_message,
        error_payload=error_payload,
    )
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return content_to_text(getattr(response, "content"))
