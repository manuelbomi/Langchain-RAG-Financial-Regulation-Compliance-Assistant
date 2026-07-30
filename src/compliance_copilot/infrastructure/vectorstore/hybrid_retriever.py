"""
Hybrid (dense + sparse) retrieval, combining the FAISS dense store with a
BM25 sparse retriever through LangChain's `EnsembleRetriever`.

Why hybrid instead of dense-only: compliance policy text is full of
identifiers, acronyms, and exact-match-sensitive terms (e.g. "MRM-POL-001",
"EDD", "SEV-1") that keyword/BM25 search handles very reliably, while
paraphrased natural-language questions ("what happens if a vendor won't
delete our data after the contract ends?") are better served by semantic
(dense) similarity. `EnsembleRetriever` fuses both ranked lists so neither
failure mode dominates.

We use LangChain's `EnsembleRetriever` for the actual result fusion/ordering
(satisfying the architectural requirement to genuinely combine dense+sparse
via that abstraction), and separately compute an explicit, inspectable
hybrid score per passage -- `HYBRID_DENSE_WEIGHT * cosine + HYBRID_SPARSE_WEIGHT
* normalized_bm25` -- because the refusal and citation-enforcement guardrails
need a concrete number to check against `SIMILARITY_REFUSAL_THRESHOLD`, and
`EnsembleRetriever` itself does not surface its internal reciprocal-rank
fusion score on returned documents.
"""

from __future__ import annotations

import re

from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from rank_bm25 import BM25Okapi

from compliance_copilot.domain.models import DocumentChunk, RetrievedPassage
from compliance_copilot.infrastructure.vectorstore.faiss_store import (
    FaissDenseStore,
    chunk_to_lc_document,
)

_TOKEN_RE = re.compile(r"[a-zA-Z]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class HybridRetriever:
    """Combines FAISS dense retrieval and BM25 sparse retrieval."""

    def __init__(
        self,
        dense_store: FaissDenseStore,
        chunks: list[DocumentChunk],
        dense_weight: float,
        sparse_weight: float,
        top_k: int,
    ) -> None:
        if not chunks:
            raise ValueError("HybridRetriever requires a non-empty chunk set.")

        self._dense_store = dense_store
        self._chunks = chunks
        self._dense_weight = dense_weight
        self._sparse_weight = sparse_weight
        self._top_k = top_k

        self._chunk_by_id = {c.chunk_id: c for c in chunks}
        self._index_by_chunk_id = {c.chunk_id: i for i, c in enumerate(chunks)}

        # Raw rank_bm25 index, used only to compute an explicit numeric
        # score per passage (see module docstring).
        self._bm25_index = BM25Okapi([_tokenize(c.text) for c in chunks])

        bm25_lc_retriever = BM25Retriever.from_documents(
            [chunk_to_lc_document(c) for c in chunks]
        )
        bm25_lc_retriever.k = top_k
        dense_lc_retriever = dense_store.as_langchain_retriever(k=top_k)

        self._ensemble = EnsembleRetriever(
            retrievers=[dense_lc_retriever, bm25_lc_retriever],
            weights=[dense_weight, sparse_weight],
        )

    def retrieve(self, query: str) -> list[RetrievedPassage]:
        """Return up to `top_k` passages, ordered by an explicit hybrid
        score, deduplicated by chunk id (EnsembleRetriever already dedupes
        by document content, but we defend against edge cases explicitly)."""
        fused_docs = self._ensemble.invoke(query)

        query_tokens = _tokenize(query)
        bm25_scores = self._bm25_index.get_scores(query_tokens)
        max_bm25 = max(bm25_scores) if len(bm25_scores) and max(bm25_scores) > 0 else 1.0

        dense_similarity_by_id = {
            p.chunk.chunk_id: p.score
            for p in self._dense_store.similarity_search_with_score(query, k=len(self._chunks))
        }

        seen: set[str] = set()
        passages: list[RetrievedPassage] = []
        for doc in fused_docs:
            chunk_id = doc.metadata["chunk_id"]
            if chunk_id in seen:
                continue
            seen.add(chunk_id)

            chunk = self._chunk_by_id[chunk_id]
            idx = self._index_by_chunk_id[chunk_id]
            bm25_normalized = float(bm25_scores[idx]) / max_bm25 if max_bm25 > 0 else 0.0
            dense_similarity = dense_similarity_by_id.get(chunk_id, 0.0)

            hybrid_score = (
                self._dense_weight * dense_similarity + self._sparse_weight * bm25_normalized
            )
            passages.append(RetrievedPassage(chunk=chunk, score=hybrid_score, retriever="hybrid"))

        passages.sort(key=lambda p: p.score, reverse=True)
        return passages[: self._top_k]
