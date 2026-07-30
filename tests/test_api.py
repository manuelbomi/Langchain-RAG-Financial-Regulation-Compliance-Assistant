"""Integration-style tests for the FastAPI HTTP boundary, exercised
end-to-end (real ingestion, real hybrid retrieval, MockLLM generation --
no network calls). This is the "at least one integration-style test using
the mock LLM" required for this project.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from compliance_copilot.infrastructure.config import get_settings

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Point the app at the real sample corpus but an isolated, per-test
    # index/audit directory so tests never write into the repo tree.
    monkeypatch.setenv("CORPUS_DIR", str(REPO_ROOT / "data" / "sample_policies"))
    monkeypatch.setenv("VECTOR_INDEX_DIR", str(tmp_path / "index"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit" / "audit.log.jsonl"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("OTEL_TRACING_ENABLED", "false")
    get_settings.cache_clear()

    from compliance_copilot.api.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def test_healthz_is_always_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_ready_after_startup_build(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["index_ready"] is True
    assert body["chunk_count"] > 0


def test_corpus_endpoint_lists_all_sample_documents(client: TestClient) -> None:
    response = client.get("/corpus")
    assert response.status_code == 200
    body = response.json()

    assert body["document_count"] >= 6
    doc_ids = {d["doc_id"] for d in body["documents"]}
    assert "MRM-POL-001" in doc_ids
    assert "CDD-STD-002" in doc_ids


def test_query_endpoint_returns_grounded_answer_with_citations(client: TestClient) -> None:
    response = client.post(
        "/query",
        json={"question": "What is required for enhanced due diligence on high risk customers?"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["refused"] is False
    assert len(body["citations"]) > 0
    assert body["citations"][0]["doc_id"] == "CDD-STD-002"
    assert "X-Request-ID" in response.headers


def test_query_endpoint_refuses_out_of_corpus_question(client: TestClient) -> None:
    response = client.post(
        "/query",
        json={"question": "What is the airspeed velocity of an unladen swallow?"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["refused"] is True
    assert body["citations"] == []


def test_query_endpoint_rejects_too_short_question(client: TestClient) -> None:
    response = client.post("/query", json={"question": "hi"})
    assert response.status_code == 422  # Pydantic min_length validation


def test_reindex_endpoint_rebuilds_index(client: TestClient) -> None:
    response = client.post("/reindex")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "ok"
    assert body["chunk_count"] > 0
    assert body["document_count"] >= 6
