"""Tests for hybrid (dense + sparse) retrieval: a known, specific query
should surface the document that actually discusses it near the top of
the ranked results."""

from __future__ import annotations

from compliance_copilot.service.rag_engine import RagEngine


def test_retrieval_surfaces_relevant_document_for_known_query(rag_engine: RagEngine) -> None:
    # "Enhanced Due Diligence" is a distinctive term that appears only in
    # the Customer Due Diligence Standard (CDD-STD-002).
    passages = rag_engine.retriever.retrieve("What are the requirements for Enhanced Due Diligence?")

    assert len(passages) > 0
    doc_ids = {p.chunk.doc_id for p in passages}
    assert "CDD-STD-002" in doc_ids

    top_passage = passages[0]
    assert top_passage.chunk.doc_id == "CDD-STD-002"
    assert top_passage.score > 0


def test_retrieval_respects_top_k_limit(rag_engine: RagEngine, settings) -> None:
    passages = rag_engine.retriever.retrieve("access control and multi-factor authentication")

    assert len(passages) <= settings.retrieval_top_k


def test_retrieval_results_are_sorted_by_score_descending(rag_engine: RagEngine) -> None:
    passages = rag_engine.retriever.retrieve("business continuity recovery time objective")

    scores = [p.score for p in passages]
    assert scores == sorted(scores, reverse=True)


def test_retrieval_for_vendor_risk_query_surfaces_vendor_policy(rag_engine: RagEngine) -> None:
    passages = rag_engine.retriever.retrieve(
        "What third-party risk tiering applies to hosted AI vendors?"
    )

    doc_ids = {p.chunk.doc_id for p in passages}
    assert "TPRM-POL-003" in doc_ids
