"""
LLM provider factory: the single place that decides which `LLMClient`
implementation the rest of the application uses.

Selection logic (deliberately conservative, favoring the offline default):
  1. If `LLM_PROVIDER=mock` (the default) -> always MockLLM.
  2. If `LLM_PROVIDER=openai` but `OPENAI_API_KEY` is empty -> log a
     warning and fall back to MockLLM rather than crashing the app. This
     means the app is always runnable regardless of misconfiguration.
  3. If `LLM_PROVIDER=openai` and a key is present -> real OpenAIChatClient.
  4. Same pattern for `anthropic`.
"""

from __future__ import annotations

from compliance_copilot.infrastructure.config import Settings
from compliance_copilot.infrastructure.llm.base import LLMClient
from compliance_copilot.infrastructure.llm.mock_llm import MockLLM
from compliance_copilot.infrastructure.logging_setup import get_logger

logger = get_logger(__name__)


def build_llm_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider.strip().lower()

    if provider == "openai":
        if not settings.openai_api_key:
            logger.warning(
                "llm_provider_fallback",
                extra={"requested_provider": "openai", "reason": "missing_api_key"},
            )
            return MockLLM()
        from compliance_copilot.infrastructure.llm.real_providers import OpenAIChatClient

        return OpenAIChatClient(api_key=settings.openai_api_key)

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            logger.warning(
                "llm_provider_fallback",
                extra={"requested_provider": "anthropic", "reason": "missing_api_key"},
            )
            return MockLLM()
        from compliance_copilot.infrastructure.llm.real_providers import AnthropicChatClient

        return AnthropicChatClient(api_key=settings.anthropic_api_key)

    if provider != "mock":
        logger.warning(
            "unknown_llm_provider_fallback",
            extra={"requested_provider": provider},
        )

    return MockLLM()
