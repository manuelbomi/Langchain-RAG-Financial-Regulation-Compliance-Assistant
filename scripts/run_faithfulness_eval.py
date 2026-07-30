#!/usr/bin/env python
"""
Standalone faithfulness eval harness.

Runs a small fixed set of representative questions through the full RAG
pipeline (real ingestion, real hybrid retrieval, MockLLM generation) and
reports each answer's faithfulness score (see
service/guardrails.py::FaithfulnessEvaluator) plus whether citation
enforcement passed. This is the offline counterpart to the citation
enforcement guardrail exercised live on every `/query` call -- useful for
catching a faithfulness regression after changing the prompt template,
chunking parameters, or retrieval weights, before it reaches users.

Usage:
    python scripts/run_faithfulness_eval.py

Exit code is non-zero if any case scores below MIN_ACCEPTABLE_FAITHFULNESS
or is unexpectedly refused, making this suitable as a CI gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from compliance_copilot.infrastructure.config import get_settings  # noqa: E402
from compliance_copilot.infrastructure.llm.mock_llm import MockLLM  # noqa: E402
from compliance_copilot.infrastructure.logging_setup import configure_logging  # noqa: E402
from compliance_copilot.service.query_service import QueryService  # noqa: E402
from compliance_copilot.service.rag_engine import RagEngine  # noqa: E402

MIN_ACCEPTABLE_FAITHFULNESS = 0.3

# (question, expected_doc_id) -- expected_doc_id is asserted to appear
# among the answer's citations, as a coarse relevance check alongside the
# faithfulness score.
EVAL_CASES: list[tuple[str, str]] = [
    ("What is required for enhanced due diligence on high risk customers?", "CDD-STD-002"),
    ("What third-party risk tiering applies to hosted AI vendors?", "TPRM-POL-003"),
    ("How often must access entitlements be recertified?", "ISEC-POL-005"),
    ("What is the recovery time objective for a Tier 1 process?", "BCP-POL-006"),
    ("What must independent model validation assess?", "MRM-POL-001"),
]


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = RagEngine(settings)
    engine.build()
    service = QueryService(settings=settings, rag_engine=engine, llm_client=MockLLM())

    failures = 0
    for question, expected_doc_id in EVAL_CASES:
        answer = service.answer_query(question)
        cited_doc_ids = {c.doc_id for c in answer.citations}
        score = answer.faithfulness_score or 0.0

        ok = (
            not answer.refused
            and expected_doc_id in cited_doc_ids
            and score >= MIN_ACCEPTABLE_FAITHFULNESS
        )
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1

        print(f"[{status}] faithfulness={score:.2f} refused={answer.refused} q={question!r}")

    print(f"\n{len(EVAL_CASES) - failures}/{len(EVAL_CASES)} cases passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
