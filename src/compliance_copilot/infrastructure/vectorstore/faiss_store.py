"""
FAISS-backed dense vector store adapter.

Architecture note (see README "Why LangChain + a self-hosted vector store"
for the full rationale): FAISS is an in-process, local library -- indexing
and search happen inside this Python process, on local disk, with no
network call and no data leaving the host. That is a deliberate choice for
a compliance-document RAG system where source text may be Confidential per
the sample Data Classification Standard.

Swap-in path to pgvector: this class exposes the same shape of interface
(`build`, `save`, `load`, `as_retriever`) that a `PgVectorStore` adapter
would need to implement. Swapping to Postgres/pgvector for a multi-replica
production deployment (so every pod shares one index without a
save/load-to-disk step) means writing one new adapter class here and
changing `provider_factory`-style wiring in `service/ingestion_service.py`
-- nothing in the service or API layers would need to change, because they
depend only on the `as_retriever()` / `similarity_search_with_score()`
surface, not on FAISS specifically.
"""

from __future__ import annotations

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from compliance_copilot.domain.models import ClassificationTier, DocumentChunk, RetrievedPassage
from compliance_copilot.infrastructure.vectorstore.local_embeddings import LocalHashingEmbeddings


def chunk_to_lc_document(chunk: DocumentChunk) -> Document:
    return Document(
        page_content=chunk.text,
        metadata={
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "doc_title": chunk.doc_title,
            "section_id": chunk.section_id,
            "section_title": chunk.section_title,
            "classification": chunk.classification.value,
            "source_path": chunk.source_path,
            "chunk_index": chunk.chunk_index,
        },
    )


def lc_document_to_chunk(doc: Document) -> DocumentChunk:
    meta = doc.metadata
    return DocumentChunk(
        chunk_id=meta["chunk_id"],
        doc_id=meta["doc_id"],
        doc_title=meta["doc_title"],
        section_id=meta["section_id"],
        section_title=meta["section_title"],
        text=doc.page_content,
        classification=ClassificationTier(meta["classification"]),
        source_path=meta["source_path"],
        chunk_index=meta["chunk_index"],
    )


class FaissDenseStore:
    """Thin, testable wrapper around `langchain_community.vectorstores.FAISS`."""

    def __init__(self, embeddings: LocalHashingEmbeddings | None = None) -> None:
        # Swap `LocalHashingEmbeddings()` for `OpenAIEmbeddings()` or
        # `HuggingFaceEmbeddings(...)` here to use a real semantic embedding
        # model in production -- everything downstream is unaffected since
        # both implement LangChain's `Embeddings` interface.
        self._embeddings = embeddings or LocalHashingEmbeddings()
        self._store: FAISS | None = None

    @property
    def is_built(self) -> bool:
        return self._store is not None

    def build(self, chunks: list[DocumentChunk]) -> None:
        documents = [chunk_to_lc_document(c) for c in chunks]
        self._store = FAISS.from_documents(documents, self._embeddings)

    def save(self, path: Path) -> None:
        if self._store is None:
            raise RuntimeError("Cannot save an unbuilt FAISS store.")
        path.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(path))

    def load(self, path: Path) -> bool:
        """Returns True if a saved index was found and loaded."""
        if not path.exists():
            return False
        self._store = FAISS.load_local(
            str(path),
            self._embeddings,
            # Loading a locally-produced index we built ourselves; safe to
            # allow deserialization (this flag guards against loading
            # untrusted pickled indexes from third parties).
            allow_dangerous_deserialization=True,
        )
        return True

    def similarity_search_with_score(self, query: str, k: int) -> list[RetrievedPassage]:
        if self._store is None:
            raise RuntimeError("FAISS store has not been built or loaded.")
        results = self._store.similarity_search_with_score(query, k=k)
        passages: list[RetrievedPassage] = []
        for doc, distance in results:
            # LocalHashingEmbeddings always emits unit-length vectors, so for
            # unit vectors a and b: ||a-b||^2 = 2 - 2*cos(a,b). Inverting
            # that gives cosine similarity directly from FAISS's L2 distance,
            # bounded in [-1, 1] with 0 = orthogonal (no shared vocabulary).
            # This is a much cleaner, more discriminative refusal signal
            # than an arbitrary 1/(1+distance) transform would be.
            cosine_similarity = 1.0 - (float(distance) ** 2) / 2.0
            passages.append(
                RetrievedPassage(
                    chunk=lc_document_to_chunk(doc), score=cosine_similarity, retriever="dense"
                )
            )
        return passages

    def as_langchain_retriever(self, k: int):
        """Expose the underlying LangChain retriever interface for use in a
        LangChain `EnsembleRetriever` (see hybrid_retriever.py)."""
        if self._store is None:
            raise RuntimeError("FAISS store has not been built or loaded.")
        return self._store.as_retriever(search_kwargs={"k": k})

    def all_documents(self) -> list[DocumentChunk]:
        if self._store is None:
            return []
        return [
            lc_document_to_chunk(doc) for doc in self._store.docstore._dict.values()  # type: ignore[attr-defined]
        ]
