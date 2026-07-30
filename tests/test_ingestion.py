"""Tests for the ingestion pipeline: parsing and chunking a sample policy
document into DocumentChunk objects with correct metadata."""

from __future__ import annotations

from pathlib import Path

from compliance_copilot.domain.models import ClassificationTier
from compliance_copilot.infrastructure.config import Settings
from compliance_copilot.service.ingestion_service import IngestionService, parse_document

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DOC = REPO_ROOT / "data" / "sample_policies" / "model_risk_management_policy.md"


def test_parse_document_extracts_doc_id_and_title() -> None:
    parsed = parse_document(SAMPLE_DOC)

    assert parsed.doc_id == "MRM-POL-001"
    assert parsed.doc_title == "Model Risk Management Policy"
    assert len(parsed.sections) == 6  # Sections 1 through 6 in the source file


def test_parse_document_section_ids_are_stable_and_unique() -> None:
    parsed = parse_document(SAMPLE_DOC)

    section_ids = [s.section_id for s in parsed.sections]
    assert section_ids == [
        "MRM-POL-001#S1",
        "MRM-POL-001#S2",
        "MRM-POL-001#S3",
        "MRM-POL-001#S4",
        "MRM-POL-001#S5",
        "MRM-POL-001#S6",
    ]
    assert len(section_ids) == len(set(section_ids))


def test_chunk_documents_produces_expected_metadata(settings: Settings) -> None:
    ingestion = IngestionService(settings)
    parsed = parse_document(SAMPLE_DOC)

    chunks = ingestion.chunk_documents([parsed])

    assert len(chunks) > 0
    # Every chunk from this document must trace back to a real section id
    # from the parsed document, and carry consistent doc-level metadata.
    valid_section_ids = {s.section_id for s in parsed.sections}
    for chunk in chunks:
        assert chunk.doc_id == "MRM-POL-001"
        assert chunk.doc_title == "Model Risk Management Policy"
        assert chunk.section_id in valid_section_ids
        assert chunk.classification == ClassificationTier.INTERNAL
        assert chunk.text.strip() != ""
        assert chunk.chunk_id.startswith("MRM-POL-001::")


def test_full_corpus_ingestion_produces_chunks_for_every_document(settings: Settings) -> None:
    ingestion = IngestionService(settings)

    chunks, documents = ingestion.ingest()

    assert len(documents) >= 6  # README requires 6-10 sample policies
    doc_ids_with_chunks = {c.doc_id for c in chunks}
    assert doc_ids_with_chunks == {d.doc_id for d in documents}
