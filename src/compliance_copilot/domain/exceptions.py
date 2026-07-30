"""
Domain-level exceptions.

Kept distinct from HTTP concerns -- the API layer is responsible for
translating these into appropriate status codes (see api/routes.py). This
keeps the service/domain layers free of any FastAPI/HTTP coupling.
"""

from __future__ import annotations


class ComplianceCopilotError(Exception):
    """Base class for all domain-level errors in this project."""


class NoGroundingFoundError(ComplianceCopilotError):
    """Raised internally when retrieval returns nothing above the
    similarity threshold. The service layer catches this and converts it
    into a `GroundedAnswer(refused=True, ...)` rather than letting it
    propagate -- refusal is a normal, expected outcome, not a system error.
    """


class CitationEnforcementError(ComplianceCopilotError):
    """Raised when a candidate answer cites a section_id that is not
    present in the retrieved passage set, or cites nothing at all. This is
    the concrete guardrail check described in the README's Governance
    section -- it is a real assertion, not a documentation-only claim.
    """

    def __init__(self, message: str, invalid_section_ids: list[str] | None = None) -> None:
        super().__init__(message)
        self.invalid_section_ids = invalid_section_ids or []


class IngestionError(ComplianceCopilotError):
    """Raised when the ingestion pipeline cannot process the corpus
    (missing directory, empty corpus, malformed document metadata)."""


class LLMProviderError(ComplianceCopilotError):
    """Raised when a configured LLM provider call fails after retries are
    exhausted. Wraps the underlying provider exception so callers only
    need to handle one error type across providers."""
