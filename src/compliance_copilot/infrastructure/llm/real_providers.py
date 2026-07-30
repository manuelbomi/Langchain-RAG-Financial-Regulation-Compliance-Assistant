"""
Real (paid, network-calling) LLM provider adapters.

These are only ever instantiated by `provider_factory.build_llm_client()`
when a matching API key environment variable is present -- by default this
project never imports the underlying SDKs at all, so `pip install`ing this
project's base `requirements.txt` and running the demo never touches the
network.

The `openai` / `anthropic` packages are intentionally NOT in
`requirements.txt` (kept out of the default, offline install). Install
them yourself (`pip install openai` / `pip install anthropic`) only if you
want to exercise real-provider mode; see README "Getting Started ->
Optional: real LLM providers".

Every call is wrapped with:
  - a hard timeout (`REQUEST_TIMEOUT_SECONDS`)
  - `tenacity`-managed retry with exponential backoff + jitter
  - a `CircuitBreaker` so repeated failures fail fast instead of retrying
    forever against a degraded upstream
"""

from __future__ import annotations

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from compliance_copilot.domain.exceptions import LLMProviderError
from compliance_copilot.infrastructure.llm.circuit_breaker import CircuitBreaker
from compliance_copilot.infrastructure.logging_setup import get_logger

logger = get_logger(__name__)

REQUEST_TIMEOUT_SECONDS = 30.0


class _RetryableProviderError(Exception):
    """Internal marker distinguishing retryable transport errors from
    non-retryable ones (e.g. bad request / auth failure)."""


class OpenAIChatClient:
    """Adapter over the OpenAI Chat Completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        try:
            import openai  # noqa: F401  (import guarded -- optional dependency)
        except ImportError as exc:  # pragma: no cover - exercised only without extra installed
            raise LLMProviderError(
                "LLM_PROVIDER=openai requires the 'openai' package. "
                "Install it with: pip install openai"
            ) from exc

        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
        self._model = model
        self._breaker = CircuitBreaker()

    @property
    def provider_name(self) -> str:
        return f"openai:{self._model}"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self._breaker.before_call()
        try:
            result = self._call_with_retry(system_prompt, user_prompt)
        except Exception as exc:
            self._breaker.record_failure()
            raise LLMProviderError(f"OpenAI generation failed: {exc}") from exc
        self._breaker.record_success()
        return result

    @retry(
        wait=wait_random_exponential(multiplier=1, max=20),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(_RetryableProviderError),
        reraise=True,
    )
    def _call_with_retry(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )
        except Exception as exc:  # broad: SDK raises several transient error types
            raise _RetryableProviderError(str(exc)) from exc
        return response.choices[0].message.content or ""


class AnthropicChatClient:
    """Adapter over the Anthropic Messages API."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest") -> None:
        try:
            import anthropic  # noqa: F401  (import guarded -- optional dependency)
        except ImportError as exc:  # pragma: no cover
            raise LLMProviderError(
                "LLM_PROVIDER=anthropic requires the 'anthropic' package. "
                "Install it with: pip install anthropic"
            ) from exc

        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
        self._model = model
        self._breaker = CircuitBreaker()

    @property
    def provider_name(self) -> str:
        return f"anthropic:{self._model}"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self._breaker.before_call()
        try:
            result = self._call_with_retry(system_prompt, user_prompt)
        except Exception as exc:
            self._breaker.record_failure()
            raise LLMProviderError(f"Anthropic generation failed: {exc}") from exc
        self._breaker.record_success()
        return result

    @retry(
        wait=wait_random_exponential(multiplier=1, max=20),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(_RetryableProviderError),
        reraise=True,
    )
    def _call_with_retry(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            raise _RetryableProviderError(str(exc)) from exc
        return "".join(block.text for block in response.content if hasattr(block, "text"))
