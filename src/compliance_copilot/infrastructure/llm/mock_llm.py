"""
MockLLM: a deterministic, fully offline "LLM" used as the default provider
for this project.

Why a mock instead of always requiring a real API key:
  - The whole point of this repo is that a reviewer can `git clone`, `make
    install`, `make run`, and exercise the full RAG pipeline (ingestion,
    hybrid retrieval, query decomposition, citation-grounded synthesis,
    refusal behavior, citation enforcement) with **no signup, no billing,
    no network egress**. That's also a realistic constraint in some
    regulated-environment CI/sandbox setups.
  - It still has to behave like a real extractive/grounded LLM: it parses
    the structured `<retrieved_passages>` block out of the user prompt
    (see service/query_service.py for the exact template), picks the
    passage(s) most relevant to the question via simple keyword overlap,
    and returns an answer that (a) only uses text present in those
    passages and (b) tags every claim with `[SECTION:<section_id>]` so the
    downstream citation-enforcement guardrail has something real to check.

This is intentionally simple (no embeddings, no neural network) -- it is a
stand-in for a real generation model, not an attempt to be one.
"""

from __future__ import annotations

import re

_PASSAGE_BLOCK_RE = re.compile(
    r'\[\d+\]\s*section_id=(?P<section_id>\S+)\s+doc_title="(?P<doc_title>[^"]*)"'
    r'\s+section_title="(?P<section_title>[^"]*)"\s*\n(?P<text>.*?)(?=\n\[\d+\]|\n</retrieved_passages>)',
    re.DOTALL,
)

_REFUSAL_TEXT = (
    "I don't have sufficient grounded information in the indexed policy "
    "corpus to answer this question."
)

_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "of",
    "to",
    "for",
    "and",
    "or",
    "what",
    "how",
    "does",
    "do",
    "in",
    "on",
    "at",
    "must",
    "be",
    "this",
    "that",
    "with",
    "as",
}


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]+", text.lower()) if w not in _STOPWORDS and len(w) > 2}


class MockLLM:
    """Deterministic, no-network stand-in for a real generation model."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        question_match = re.search(r"Question:\s*(.+)", user_prompt)
        question = question_match.group(1).strip() if question_match else ""

        passages = [m.groupdict() for m in _PASSAGE_BLOCK_RE.finditer(user_prompt)]
        if not passages:
            return _REFUSAL_TEXT

        query_terms = _tokenize(question)
        scored: list[tuple[int, dict[str, str]]] = []
        for passage in passages:
            passage_terms = _tokenize(passage["text"])
            overlap = len(query_terms & passage_terms)
            scored.append((overlap, passage))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        # Only keep passages with at least one shared term with the query;
        # otherwise nothing in context actually answers the question.
        relevant = [p for score, p in scored if score > 0]
        if not relevant:
            return _REFUSAL_TEXT

        # Build an extractive, citation-tagged answer from up to the top 2
        # relevant passages -- mirrors how a real grounded LLM should
        # behave: synthesize briefly, cite precisely, don't over-claim.
        sentences: list[str] = []
        for passage in relevant[:2]:
            first_sentence = re.split(r"(?<=[.:])\s+", passage["text"].strip())[0].strip()
            first_sentence = first_sentence.rstrip(".") + "."
            tag = f"[SECTION:{passage['section_id']}]"
            sentences.append(f"{first_sentence} {tag}")

        return " ".join(sentences)
