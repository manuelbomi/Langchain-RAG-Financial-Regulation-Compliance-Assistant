"""
Domain models.

These are the core, framework-agnostic types shared across the service and
infrastructure layers. They intentionally do NOT import LangChain, FastAPI,
or FAISS types directly, so the domain stays testable and portable if any
of those libraries are swapped out later (see README "Key Design
Decisions" for the FAISS -> pgvector swap-in rationale).

We use plain `dataclasses` here (not pydantic) because these objects flow
through internal service/domain logic only; pydantic validation belongs at
the system boundary (see `api/schemas.py`), not scattered through the core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ClassificationTier(str, Enum):
    """Mirrors the tiers defined in the sample Data Classification Standard.

    Kept here (not just in sample data) because retrieval-layer access
    control decisions key off this enum -- see the Data Classification
    Standard, Section 5, which requires classification tier to travel as
    retrievable metadata on every indexed chunk.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class DocumentChunk:
    """A single retrievable unit of text produced by the ingestion pipeline.

    `section_id` is the load-bearing field for citation enforcement: every
    synthesized answer must cite a `section_id` that traces back to a chunk
    actually present in the retrieved set (see service/guardrails.py).
    """

    chunk_id: str
    doc_id: str
    doc_title: str
    section_id: str
    section_title: str
    text: str
    classification: ClassificationTier
    source_path: str
    chunk_index: int


@dataclass(frozen=True)
class RetrievedPassage:
    """A chunk plus the retrieval score(s) that surfaced it."""

    chunk: DocumentChunk
    score: float
    retriever: str  # "dense" | "sparse" | "hybrid"


@dataclass(frozen=True)
class Citation:
    """A single citation attached to a synthesized answer.

    Deliberately carries both the human-readable document title and the
    machine-checkable `section_id`, since citation *enforcement* validates
    against `section_id` (stable identifier) while the API response
    surfaces `doc_title` + `section_title` for readability.
    """

    doc_id: str
    doc_title: str
    section_id: str
    section_title: str
    quote: str


@dataclass
class QueryPlan:
    """Output of the query-decomposition step.

    Multi-part questions (e.g. "What are the CDD requirements AND how does
    that interact with vendor risk tiering?") are split into independently
    retrievable sub-questions so retrieval quality doesn't degrade on
    compound queries. A single-part question decomposes to a plan with one
    sub-question equal to the original.
    """

    original_query: str
    sub_questions: list[str] = field(default_factory=list)


@dataclass
class GroundedAnswer:
    """Final synthesized answer, always carrying its supporting evidence.

    `refused` is True when no passage cleared the similarity threshold, or
    when citation enforcement rejected every candidate answer -- in both
    cases `answer_text` explains the refusal rather than asserting an
    ungrounded claim.
    """

    query: str
    answer_text: str
    citations: list[Citation]
    refused: bool
    retrieved_passages: list[RetrievedPassage]
    faithfulness_score: float | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
