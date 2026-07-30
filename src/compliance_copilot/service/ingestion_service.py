"""
Ingestion service: parses the synthetic policy corpus into `DocumentChunk`
objects and builds the hybrid (FAISS + BM25) retrieval index over them.

Parsing strategy: each source document (see `data/sample_policies/`) is a
Markdown file following a consistent, simple convention:

    # <Document Title>
    ...
    **Document ID:** <ID>
    ...
    ## Section N: <Section Title>
    <body text>
    ## Section N+1: <Section Title>
    <body text>

We deliberately parse this convention with regexes rather than pulling in a
full Markdown AST parser -- the corpus is small, internally authored, and
structurally uniform, so a heavier dependency would add complexity without
adding correctness. If this were extended to ingest arbitrary/uncontrolled
Markdown, swapping in a proper parser (e.g. `markdown-it-py`) would be the
right move -- noted in README Roadmap.

Section-level granularity matters here: `section_id` is what citation
enforcement (service/guardrails.py) checks candidate answers against, so
every chunk must carry a stable, traceable section identifier -- not just a
document identifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from compliance_copilot.domain.exceptions import IngestionError
from compliance_copilot.domain.models import ClassificationTier, DocumentChunk
from compliance_copilot.infrastructure.config import Settings
from compliance_copilot.infrastructure.logging_setup import get_logger

logger = get_logger(__name__)

_TITLE_RE = re.compile(r"(?m)^#\s+(.+)$")
_DOC_ID_RE = re.compile(r"\*\*Document ID:\*\*\s*(\S+)")
_SECTION_SPLIT_RE = re.compile(r"(?m)^##\s+(.+)$")
_SECTION_NUMBER_RE = re.compile(r"Section\s+(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedSection:
    section_id: str
    section_title: str
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    doc_id: str
    doc_title: str
    source_path: str
    sections: list[ParsedSection] = field(default_factory=list)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def parse_document(path: Path) -> ParsedDocument:
    """Parse a single Markdown policy file into structured sections."""
    content = path.read_text(encoding="utf-8")

    title_match = _TITLE_RE.search(content)
    doc_id_match = _DOC_ID_RE.search(content)
    if not title_match or not doc_id_match:
        raise IngestionError(
            f"Document '{path}' is missing a required '# Title' heading or "
            "'**Document ID:**' field; cannot ingest."
        )
    doc_title = title_match.group(1).strip()
    doc_id = doc_id_match.group(1).strip()

    parts = _SECTION_SPLIT_RE.split(content)
    # `parts[0]` is the preamble before the first "## " heading (title,
    # synthetic-data banner, metadata block) -- not itself a citable section.
    sections: list[ParsedSection] = []
    for heading, body in zip(parts[1::2], parts[2::2], strict=False):
        number_match = _SECTION_NUMBER_RE.search(heading)
        suffix = number_match.group(1) if number_match else _slugify(heading)
        section_id = f"{doc_id}#S{suffix}"
        sections.append(
            ParsedSection(section_id=section_id, section_title=heading.strip(), text=body.strip())
        )

    if not sections:
        raise IngestionError(f"Document '{path}' contains no '## Section' headings to index.")

    return ParsedDocument(
        doc_id=doc_id, doc_title=doc_title, source_path=str(path), sections=sections
    )


class IngestionService:
    """Reads the corpus directory, chunks it, and hands chunks to callers
    to build a retrieval index (see service/query_service.py wiring)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def parse_corpus(self) -> list[ParsedDocument]:
        corpus_dir = self._settings.corpus_path
        if not corpus_dir.exists():
            raise IngestionError(f"Corpus directory does not exist: {corpus_dir}")

        files = sorted(corpus_dir.glob("*.md"))
        if not files:
            raise IngestionError(f"No Markdown documents found in corpus directory: {corpus_dir}")

        parsed = [parse_document(f) for f in files]
        logger.info(
            "corpus_parsed",
            extra={"document_count": len(parsed), "corpus_dir": str(corpus_dir)},
        )
        return parsed

    def chunk_documents(self, documents: list[ParsedDocument]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for doc in documents:
            global_index = 0
            for section in doc.sections:
                # Internal policy documents default to Tier 2 (Internal)
                # per the sample Data Classification Standard, Section 4,
                # unless a future extension marks specific sections
                # Restricted -- see DocumentChunk.classification usage in
                # service/query_service.py for how this would gate access.
                for piece in self._splitter.split_text(section.text) or [section.text]:
                    chunk_id = f"{doc.doc_id}::{section.section_id}::{global_index}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=doc.doc_id,
                            doc_title=doc.doc_title,
                            section_id=section.section_id,
                            section_title=section.section_title,
                            text=piece,
                            classification=ClassificationTier.INTERNAL,
                            source_path=doc.source_path,
                            chunk_index=global_index,
                        )
                    )
                    global_index += 1
        return chunks

    def ingest(self) -> tuple[list[DocumentChunk], list[ParsedDocument]]:
        """Convenience: parse the full corpus and chunk it in one call."""
        documents = self.parse_corpus()
        chunks = self.chunk_documents(documents)
        logger.info("corpus_chunked", extra={"chunk_count": len(chunks)})
        return chunks, documents
