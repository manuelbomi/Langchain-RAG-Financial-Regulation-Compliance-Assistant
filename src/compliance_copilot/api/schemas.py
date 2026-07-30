"""
API request/response schemas (Pydantic models).

Every value that crosses the HTTP boundary -- inbound or outbound -- is
validated through one of these models. In particular, `QueryRequest`
enforces a non-empty, length-bounded question, which is the first line of
defense against malformed or abusive input before it ever reaches
retrieval or the LLM.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="A natural-language question about the indexed policy corpus.",
    )


class CitationResponse(BaseModel):
    doc_id: str
    doc_title: str
    section_id: str
    section_title: str
    quote: str


class RetrievedPassageResponse(BaseModel):
    section_id: str
    doc_title: str
    section_title: str
    score: float
    retriever: str


class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationResponse]
    refused: bool
    faithfulness_score: float | None
    retrieved_passages: list[RetrievedPassageResponse]
    generated_at: datetime
    llm_provider: str
    request_id: str


class CorpusDocument(BaseModel):
    doc_id: str
    doc_title: str
    source_path: str
    section_count: int
    chunk_count: int
    classification: str


class CorpusResponse(BaseModel):
    document_count: int
    total_chunk_count: int
    documents: list[CorpusDocument]


class ReindexResponse(BaseModel):
    status: str
    chunk_count: int
    document_count: int


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    index_ready: bool
    chunk_count: int
