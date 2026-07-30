"""
RagEngine: owns the lifecycle of the retrieval index (parse corpus -> chunk
-> embed -> build FAISS + BM25 hybrid retriever) and exposes corpus
metadata for the `GET /corpus` endpoint and rebuild for `POST /reindex`.

Separated from `QueryService` (which answers a single question) because
index lifecycle management (build/rebuild/persist) and per-query answering
are different responsibilities with different failure modes and different
callers -- `POST /reindex` only needs this class, not the LLM/guardrail
stack.
"""

from __future__ import annotations

import threading

from compliance_copilot.domain.exceptions import IngestionError
from compliance_copilot.domain.models import DocumentChunk
from compliance_copilot.infrastructure.config import Settings
from compliance_copilot.infrastructure.logging_setup import get_logger
from compliance_copilot.infrastructure.observability.tracing import traced_span
from compliance_copilot.infrastructure.vectorstore.faiss_store import FaissDenseStore
from compliance_copilot.infrastructure.vectorstore.hybrid_retriever import HybridRetriever
from compliance_copilot.service.ingestion_service import IngestionService, ParsedDocument

logger = get_logger(__name__)


class RagEngine:
    """Holds the current retrieval index and provides thread-safe rebuild."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ingestion_service = IngestionService(settings)
        self._dense_store = FaissDenseStore()
        self._retriever: HybridRetriever | None = None
        self._chunks: list[DocumentChunk] = []
        self._documents: list[ParsedDocument] = []
        self._lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self._retriever is not None

    @property
    def retriever(self) -> HybridRetriever:
        if self._retriever is None:
            raise IngestionError("RagEngine has not been built yet; call build() first.")
        return self._retriever

    def build(self) -> int:
        """(Re)build the index from the corpus directory. Returns the
        number of chunks indexed. Thread-safe: concurrent `/reindex` calls
        (or a reindex racing a startup build) serialize rather than
        corrupting the in-memory index."""
        with self._lock, traced_span("ingestion.build_index"):
            chunks, documents = self._ingestion_service.ingest()

            dense_store = FaissDenseStore()
            dense_store.build(chunks)

            retriever = HybridRetriever(
                dense_store=dense_store,
                chunks=chunks,
                dense_weight=self._settings.hybrid_dense_weight,
                sparse_weight=self._settings.hybrid_sparse_weight,
                top_k=self._settings.retrieval_top_k,
            )

            self._dense_store = dense_store
            self._retriever = retriever
            self._chunks = chunks
            self._documents = documents

            logger.info(
                "index_built",
                extra={"chunk_count": len(chunks), "document_count": len(documents)},
            )
            return len(chunks)

    def corpus_metadata(self) -> list[dict]:
        """Summary used by `GET /corpus`: one entry per indexed document."""
        summary: list[dict] = []
        for doc in self._documents:
            doc_chunks = [c for c in self._chunks if c.doc_id == doc.doc_id]
            summary.append(
                {
                    "doc_id": doc.doc_id,
                    "doc_title": doc.doc_title,
                    "source_path": doc.source_path,
                    "section_count": len(doc.sections),
                    "chunk_count": len(doc_chunks),
                    "classification": doc_chunks[0].classification.value if doc_chunks else "internal",
                }
            )
        return summary

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)
