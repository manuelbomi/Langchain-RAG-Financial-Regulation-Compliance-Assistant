"""
Guardrails: citation enforcement, a lightweight faithfulness eval harness,
and audit logging.

These implement the "Governance & Guardrails" claims made in the README as
actual runnable checks, not documentation-only assertions:

  1. `CitationEnforcer` -- rejects any candidate answer that either cites no
     section, or cites a `section_id` that is not present in the retrieved
     passage set. This is what actually prevents the system from
     fabricating a citation to a document/section it never retrieved.
  2. `FaithfulnessEvaluator` -- a simple lexical-overlap check between the
     answer's claims and the text of the passages it cites, used both as a
     defense-in-depth signal on live answers and as a standalone offline
     eval harness (see tests/test_citation_enforcement.py and
     scripts/run_faithfulness_eval.py).
  3. `AuditLogger` -- appends one JSON line per query/answer to a local
     audit log, with PII redaction applied to the raw query text before
     it is persisted (governance requirement -- see GOVERNANCE.md).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from compliance_copilot.domain.exceptions import CitationEnforcementError
from compliance_copilot.domain.models import Citation, GroundedAnswer, RetrievedPassage
from compliance_copilot.infrastructure.logging_setup import get_logger
from compliance_copilot.infrastructure.security.pii_redaction import redact_pii

logger = get_logger(__name__)

_CITATION_TAG_RE = re.compile(r"\[SECTION:([^\]]+)\]")
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


def _content_tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]+", text.lower()) if w not in _STOPWORDS and len(w) > 2}


class CitationEnforcer:
    """Validates that every claim in a candidate answer is grounded in a
    retrieved passage's section_id."""

    @staticmethod
    def extract_cited_section_ids(answer_text: str) -> list[str]:
        return _CITATION_TAG_RE.findall(answer_text)

    def enforce(self, answer_text: str, retrieved: list[RetrievedPassage]) -> list[Citation]:
        """Returns the validated `Citation` list on success. Raises
        `CitationEnforcementError` if the answer is a refusal-equivalent
        with no citations, or cites any section_id absent from `retrieved`.
        """
        cited_ids = self.extract_cited_section_ids(answer_text)
        valid_ids = {p.chunk.section_id for p in retrieved}

        if not cited_ids:
            raise CitationEnforcementError(
                "Candidate answer contains no [SECTION:...] citation tags; "
                "cannot verify grounding."
            )

        invalid = [cid for cid in cited_ids if cid not in valid_ids]
        if invalid:
            raise CitationEnforcementError(
                f"Candidate answer cites section id(s) not present in the retrieved "
                f"passage set: {invalid}. This indicates a fabricated or stale citation.",
                invalid_section_ids=invalid,
            )

        passages_by_section = {p.chunk.section_id: p for p in retrieved}
        citations: list[Citation] = []
        seen: set[str] = set()
        for cid in cited_ids:
            if cid in seen:
                continue
            seen.add(cid)
            chunk = passages_by_section[cid].chunk
            # First sentence as the "quote" -- a short, inspectable excerpt
            # a reviewer can eyeball against the source document.
            quote = re.split(r"(?<=[.:])\s+", chunk.text.strip())[0]
            citations.append(
                Citation(
                    doc_id=chunk.doc_id,
                    doc_title=chunk.doc_title,
                    section_id=chunk.section_id,
                    section_title=chunk.section_title,
                    quote=quote,
                )
            )
        return citations


class FaithfulnessEvaluator:
    """Lightweight, dependency-free faithfulness scorer.

    Computes the fraction of content-bearing (non-stopword) tokens in the
    answer text that also appear in the text of the passages it cites. This
    is a lexical-overlap proxy for faithfulness, not an NLI-based
    entailment check -- appropriate for a portfolio demo; a production
    deployment could swap this for a proper entailment model or an
    LLM-as-judge harness while keeping the same call signature (see README
    Roadmap).
    """

    def score(self, answer_text: str, retrieved: list[RetrievedPassage]) -> float:
        cited_ids = set(CitationEnforcer.extract_cited_section_ids(answer_text))
        if not cited_ids:
            return 0.0

        cited_text = " ".join(
            p.chunk.text for p in retrieved if p.chunk.section_id in cited_ids
        )
        answer_tokens = _content_tokens(_CITATION_TAG_RE.sub("", answer_text))
        source_tokens = _content_tokens(cited_text)

        if not answer_tokens:
            return 0.0
        overlap = len(answer_tokens & source_tokens)
        return round(overlap / len(answer_tokens), 4)


class AuditLogger:
    """Append-only JSONL audit trail of every query/answer, with the raw
    query PII-redacted before persistence."""

    def __init__(self, log_path: Path, enable_pii_redaction: bool = True) -> None:
        self._log_path = log_path
        self._enable_pii_redaction = enable_pii_redaction
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, answer: GroundedAnswer, request_id: str, llm_provider: str) -> None:
        query_to_log = answer.query
        redaction_labels: list[str] = []
        if self._enable_pii_redaction:
            result = redact_pii(answer.query)
            query_to_log = result.text
            redaction_labels = result.labels_found

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "query": query_to_log,
            "pii_redacted_labels": redaction_labels,
            "refused": answer.refused,
            "answer_text": answer.answer_text,
            "citations": [asdict(c) for c in answer.citations],
            "faithfulness_score": answer.faithfulness_score,
            "llm_provider": llm_provider,
            "retrieved_section_ids": [p.chunk.section_id for p in answer.retrieved_passages],
        }
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info(
            "audit_record_written",
            extra={"request_id": request_id, "refused": answer.refused},
        )
