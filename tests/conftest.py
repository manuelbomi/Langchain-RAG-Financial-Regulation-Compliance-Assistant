"""Shared pytest fixtures.

Tests always point `Settings.corpus_dir` at the real
`data/sample_policies/` directory (resolved relative to this file, not the
process cwd, so tests pass regardless of where pytest is invoked from) and
use a per-test temp directory for the audit log / vector index paths so
tests never write into the repo or interfere with each other.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compliance_copilot.infrastructure.config import Settings
from compliance_copilot.infrastructure.llm.mock_llm import MockLLM
from compliance_copilot.service.guardrails import (
    AuditLogger,
    CitationEnforcer,
    FaithfulnessEvaluator,
)
from compliance_copilot.service.query_service import QueryService
from compliance_copilot.service.rag_engine import RagEngine

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "data" / "sample_policies"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        corpus_dir=str(CORPUS_DIR),
        vector_index_dir=str(tmp_path / "index"),
        audit_log_path=str(tmp_path / "audit" / "audit.log.jsonl"),
        llm_provider="mock",
        # Console span export is noisy in test output and unnecessary for
        # unit/integration assertions; tracing itself is still exercised
        # (traced_span is a no-op-safe context manager either way).
        otel_tracing_enabled=False,
    )


@pytest.fixture
def rag_engine(settings: Settings) -> RagEngine:
    engine = RagEngine(settings)
    engine.build()
    return engine


@pytest.fixture
def query_service(settings: Settings, rag_engine: RagEngine) -> QueryService:
    return QueryService(
        settings=settings,
        rag_engine=rag_engine,
        llm_client=MockLLM(),
        citation_enforcer=CitationEnforcer(),
        faithfulness_evaluator=FaithfulnessEvaluator(),
        audit_logger=AuditLogger(settings.audit_log_file, settings.enable_pii_redaction),
    )
