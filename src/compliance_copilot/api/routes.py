"""
Core business routes: POST /query, GET /corpus, POST /reindex.

Route handlers are intentionally thin: validate via Pydantic (handled
automatically by FastAPI from the schema type hints), delegate to the
service layer, translate domain results into response schemas. No
retrieval, prompting, or guardrail logic lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from compliance_copilot.api.deps import get_query_service, get_rag_engine
from compliance_copilot.api.schemas import (
    CitationResponse,
    CorpusDocument,
    CorpusResponse,
    QueryRequest,
    QueryResponse,
    ReindexResponse,
    RetrievedPassageResponse,
)
from compliance_copilot.infrastructure.logging_setup import get_request_id
from compliance_copilot.service.query_service import QueryService
from compliance_copilot.service.rag_engine import RagEngine

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, query_service: QueryService = Depends(get_query_service)) -> QueryResponse:
    """Ask a question against the indexed policy corpus. Always returns a
    grounded, citation-backed answer or an explicit refusal -- never an
    unqualified free-form generation."""
    request_id = get_request_id()
    answer = query_service.answer_query(request.question, request_id=request_id)

    return QueryResponse(
        query=answer.query,
        answer=answer.answer_text,
        citations=[
            CitationResponse(
                doc_id=c.doc_id,
                doc_title=c.doc_title,
                section_id=c.section_id,
                section_title=c.section_title,
                quote=c.quote,
            )
            for c in answer.citations
        ],
        refused=answer.refused,
        faithfulness_score=answer.faithfulness_score,
        retrieved_passages=[
            RetrievedPassageResponse(
                section_id=p.chunk.section_id,
                doc_title=p.chunk.doc_title,
                section_title=p.chunk.section_title,
                score=round(p.score, 4),
                retriever=p.retriever,
            )
            for p in answer.retrieved_passages
        ],
        generated_at=answer.generated_at,
        llm_provider=query_service.llm_provider_name,
        request_id=request_id,
    )


@router.get("/corpus", response_model=CorpusResponse)
def get_corpus(rag_engine: RagEngine = Depends(get_rag_engine)) -> CorpusResponse:
    """List indexed documents and their metadata."""
    docs = rag_engine.corpus_metadata()
    return CorpusResponse(
        document_count=len(docs),
        total_chunk_count=rag_engine.chunk_count,
        documents=[CorpusDocument(**d) for d in docs],
    )


@router.post("/reindex", response_model=ReindexResponse)
def reindex(rag_engine: RagEngine = Depends(get_rag_engine)) -> ReindexResponse:
    """Rebuild the retrieval index from the corpus directory on disk. Safe
    to call after adding/editing documents under `data/sample_policies/`."""
    chunk_count = rag_engine.build()
    return ReindexResponse(
        status="ok",
        chunk_count=chunk_count,
        document_count=len(rag_engine.corpus_metadata()),
    )
