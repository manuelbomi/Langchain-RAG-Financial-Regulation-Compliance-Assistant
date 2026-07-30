"""
LLM provider interface.

Every concrete provider (MockLLM, OpenAI, Anthropic, ...) implements this
`Protocol`. The service layer (service/query_service.py) type-hints against
`LLMClient`, never against a concrete class, which is what makes it
possible to run this entire project with zero API keys and zero network
calls: `provider_factory.build_llm_client()` returns a `MockLLM` unless a
provider is explicitly configured AND its API key is present.

Prompt-injection note: the `system_prompt` and `user_prompt` are passed
separately (never concatenated ad hoc) so that concrete providers can use
each backend's native system/user role separation, which is part of this
project's prompt-injection mitigation strategy -- retrieved document text
is always placed in the user turn, clearly delimited, and never in the
system turn. See service/query_service.py for how prompts are assembled.
"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Minimal interface required of any LLM backend used by this service."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return a single completion string for the given prompt pair.

        Implementations are expected to apply their own timeout/retry
        policy (see infrastructure/llm/provider_factory.py for how real
        providers are wrapped with `tenacity`) and to raise
        `domain.exceptions.LLMProviderError` on unrecoverable failure.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Short identifier used in audit logs and API responses, e.g.
        'mock', 'openai:gpt-4o-mini', 'anthropic:claude-3-5-sonnet'."""
        ...
