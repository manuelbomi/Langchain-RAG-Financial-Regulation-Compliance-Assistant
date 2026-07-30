"""
LocalHashingEmbeddings: a fully offline, dependency-light embedding
implementation used as the default embedder for the FAISS dense index.

Why not a real neural embedding model by default: sentence-transformers /
HuggingFace embedding models require downloading model weights on first
use (a network call, and a multi-hundred-MB one), which would violate this
project's core promise that the RAG demo runs with **no external network
calls needed**. Swapping in a real embedding model (HuggingFaceEmbeddings,
OpenAIEmbeddings, etc.) is a one-line change in `faiss_store.py` -- see the
comment there -- and is the recommended production upgrade path (documented
in the README "Key Design Decisions" section).

This implementation is a deterministic hashed bag-of-words vectorizer:
each token is hashed (via `hashlib.md5`, NOT Python's `hash()`, because the
latter is randomized per-process unless `PYTHONHASHSEED` is fixed, which
would make the index non-reproducible across runs) into a fixed-width
vector, weighted by term frequency, and L2-normalized so cosine/L2 FAISS
similarity behaves sensibly. It captures keyword/topic overlap well enough
to meaningfully complement the BM25 sparse retriever in the hybrid
ensemble, though it is obviously not a substitute for a trained semantic
embedding model in production.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from langchain_core.embeddings import Embeddings

_TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")
_DEFAULT_DIMENSIONS = 384

# Common function words are deliberately excluded from the embedding, not
# just down-weighted: with a small, topically-distinct demo corpus, letting
# stopwords contribute at all is enough accidental hash-bucket overlap to
# make unrelated queries (e.g. "birthday cake topping") register a
# nontrivial cosine similarity against policy text purely from shared
# words like "the", "for", "and". Filtering them keeps the embedding's
# similarity signal tied to actual topical/content overlap, which is what
# the refusal-threshold guardrail depends on.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "for", "and", "or", "in", "on", "at", "by", "with", "as",
    "this", "that", "these", "those", "it", "its", "from", "into", "than",
    "then", "so", "not", "no", "if", "but", "can", "may", "must", "will",
    "shall", "should", "would", "could", "any", "all", "each", "such",
    "what", "how", "when", "where", "why", "who", "which", "does", "do",
    "did", "have", "has", "had", "you", "your", "our", "their", "his",
    "her", "there", "here", "also", "per", "upon",
}


def _tokenize(text: str) -> list[str]:
    return [
        t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOPWORDS
    ]


def _hash_index(token: str, dimensions: int) -> int:
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % dimensions


class LocalHashingEmbeddings(Embeddings):
    """Deterministic, offline stand-in for a neural embedding model.

    Implements LangChain's `Embeddings` interface so it is a drop-in
    argument to `langchain_community.vectorstores.FAISS`.
    """

    def __init__(self, dimensions: int = _DEFAULT_DIMENSIONS) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        tokens = _tokenize(text)
        vector = [0.0] * self.dimensions
        if not tokens:
            return vector

        counts = Counter(tokens)
        for token, count in counts.items():
            idx = _hash_index(token, self.dimensions)
            # log-dampened term frequency, akin to a simplified TF weight.
            vector[idx] += 1.0 + math.log(count)

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
