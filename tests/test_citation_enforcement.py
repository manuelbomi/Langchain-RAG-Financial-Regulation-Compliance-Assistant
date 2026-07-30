"""Tests for the citation-enforcement guardrail: a candidate answer that
cites a section not present in the retrieved set (or cites nothing at
all) must be rejected -- this is the concrete check backing the README's
governance claims, not a documentation-only assertion."""

from __future__ import annotations

import pytest

from compliance_copilot.domain.exceptions import CitationEnforcementError
from compliance_copilot.service.guardrails import CitationEnforcer, FaithfulnessEvaluator
from compliance_copilot.service.rag_engine import RagEngine


def test_citation_enforcement_rejects_answer_with_no_citation_tags(rag_engine: RagEngine) -> None:
    passages = rag_engine.retriever.retrieve("customer due diligence requirements")
    enforcer = CitationEnforcer()

    ungrounded_answer = "Customers must always be onboarded within 24 hours."

    with pytest.raises(CitationEnforcementError):
        enforcer.enforce(ungrounded_answer, passages)


def test_citation_enforcement_rejects_fabricated_section_id(rag_engine: RagEngine) -> None:
    passages = rag_engine.retriever.retrieve("customer due diligence requirements")
    enforcer = CitationEnforcer()

    # This section id does not exist anywhere in the corpus.
    fabricated_answer = "Customers must be onboarded within 24 hours. [SECTION:FAKE-POL-999#S1]"

    with pytest.raises(CitationEnforcementError) as exc_info:
        enforcer.enforce(fabricated_answer, passages)

    assert "FAKE-POL-999#S1" in exc_info.value.invalid_section_ids


def test_citation_enforcement_accepts_valid_grounded_citation(rag_engine: RagEngine) -> None:
    passages = rag_engine.retriever.retrieve("customer due diligence requirements")
    enforcer = CitationEnforcer()
    real_section_id = passages[0].chunk.section_id

    grounded_answer = f"Customer risk ratings drive due diligence depth. [SECTION:{real_section_id}]"

    citations = enforcer.enforce(grounded_answer, passages)

    assert len(citations) == 1
    assert citations[0].section_id == real_section_id


def test_faithfulness_evaluator_scores_grounded_answer_higher_than_ungrounded() -> None:
    from compliance_copilot.domain.models import ClassificationTier, DocumentChunk, RetrievedPassage

    chunk = DocumentChunk(
        chunk_id="X::Y#S1::0",
        doc_id="X",
        doc_title="Test Policy",
        section_id="Y#S1",
        section_title="Section 1: Test",
        text="Enhanced due diligence requires senior management approval before onboarding.",
        classification=ClassificationTier.INTERNAL,
        source_path="test.md",
        chunk_index=0,
    )
    passages = [RetrievedPassage(chunk=chunk, score=0.9, retriever="hybrid")]
    evaluator = FaithfulnessEvaluator()

    grounded = "Enhanced due diligence requires senior management approval. [SECTION:Y#S1]"
    ungrounded = "All customers receive a complimentary gift basket. [SECTION:Y#S1]"

    grounded_score = evaluator.score(grounded, passages)
    ungrounded_score = evaluator.score(ungrounded, passages)

    assert grounded_score > ungrounded_score
