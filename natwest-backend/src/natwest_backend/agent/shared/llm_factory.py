from __future__ import annotations

from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from natwest_shared.utils.logger import get_logger
from pydantic import SecretStr

from natwest_backend.config import settings

logger = get_logger(__name__)


class _LLMCallLogger(AsyncCallbackHandler):
    async def on_chat_model_start(
        self, serialized: dict[str, Any], messages: list[Any], **kwargs: Any
    ) -> None:
        params = kwargs.get("invocation_params", {})
        if "azure_deployment" in params:
            logger.info(
                "LLM call | Fallback used, Azure OpenAI (%s)",
                params["azure_deployment"],
            )
        else:
            logger.info("LLM call | OpenAI (%s)", params.get("model_name", "unknown"))


_call_logger = _LLMCallLogger()


def create_llm() -> BaseChatModel:
    """
    Build the LLM with OpenAI as primary and Azure OpenAI as fallback,
    using the factory pattern.
    """

    openai_llm = ChatOpenAI(
        model=settings.llm_model,
        temperature=0,
        api_key=(
            SecretStr(settings.openai_api_key) if settings.openai_api_key else None
        ),
        # Models like gpt-5.6-luna reject function tools unless reasoning
        # effort is explicitly disabled on the chat-completions endpoint.
        reasoning_effort="none",
        callbacks=[_call_logger],
    )

    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        azure_llm = AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            api_key=SecretStr(settings.azure_openai_api_key),
            callbacks=[_call_logger],
        )

        logger.info(
            "LLM configured | primary=OpenAI (%s) | fallback=Azure OpenAI (%s)",
            settings.llm_model,
            settings.azure_openai_deployment,
        )

        return openai_llm.with_fallbacks([azure_llm])  # type: ignore[return-value]

    logger.info("LLM configured | OpenAI only (%s)", settings.llm_model)
    return openai_llm
