"""
FastAPI application entrypoint.

Responsibilities kept here, and only here:
  - App construction and lifespan (startup builds the retrieval index and
    wires the LLM client, so the first request is never slow).
  - Cross-cutting HTTP middleware (request/correlation ID assignment).
  - Health (`/healthz`) and readiness (`/readyz`) endpoints -- these are
    intentionally NOT under the versioned business router below, since
    orchestrators (Kubernetes) probe them unauthenticated and independent
    of API versioning.

Run locally with: `uvicorn compliance_copilot.api.main:app --reload`
(see Makefile `run` target / README "Getting Started").
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from compliance_copilot.api.routes import router as api_router
from compliance_copilot.api.schemas import HealthResponse, ReadinessResponse
from compliance_copilot.domain.exceptions import ComplianceCopilotError
from compliance_copilot.infrastructure.config import get_settings
from compliance_copilot.infrastructure.llm.provider_factory import build_llm_client
from compliance_copilot.infrastructure.logging_setup import (
    configure_logging,
    get_logger,
    set_request_id,
)
from compliance_copilot.infrastructure.observability.tracing import configure_tracing
from compliance_copilot.service.guardrails import AuditLogger
from compliance_copilot.service.query_service import QueryService
from compliance_copilot.service.rag_engine import RagEngine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing(service_name=settings.app_name, enabled=settings.otel_tracing_enabled)

    rag_engine = RagEngine(settings)
    rag_engine.build()

    llm_client = build_llm_client(settings)
    audit_logger = AuditLogger(settings.audit_log_file, settings.enable_pii_redaction)
    query_service = QueryService(
        settings=settings,
        rag_engine=rag_engine,
        llm_client=llm_client,
        audit_logger=audit_logger,
    )

    app.state.settings = settings
    app.state.rag_engine = rag_engine
    app.state.llm_client = llm_client
    app.state.audit_logger = audit_logger
    app.state.query_service = query_service

    logger.info(
        "app_startup_complete",
        extra={"llm_provider": llm_client.provider_name, "chunk_count": rag_engine.chunk_count},
    )
    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Policy & Regulatory Research Copilot",
        description=(
            "Self-hosted LangChain RAG API for financial compliance research over a "
            "synthetic policy corpus (fictional 'Northbridge Financial Group' demo data)."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Assign a request/correlation ID to every inbound request, bind
        it for structured logging, and echo it back on the response so a
        caller (or a downstream system) can correlate logs end to end."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(ComplianceCopilotError)
    async def domain_error_handler(request: Request, exc: ComplianceCopilotError) -> JSONResponse:
        """Translate domain errors into a safe HTTP response. We never leak
        raw exception internals (which could include prompt content or
        stack traces) to the client -- only the exception's message, which
        by construction in domain/exceptions.py never contains secrets."""
        logger.error("domain_error", extra={"error": str(exc), "type": type(exc).__name__})
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(api_router, tags=["compliance-copilot"])

    @app.get("/healthz", response_model=HealthResponse, tags=["ops"])
    def healthz() -> HealthResponse:
        """Liveness probe: is the process up and able to handle a request
        at all? Does not check index readiness -- see /readyz for that."""
        return HealthResponse(status="ok")

    @app.get("/readyz", response_model=ReadinessResponse, tags=["ops"])
    def readyz(request: Request) -> ReadinessResponse:
        """Readiness probe: has the retrieval index finished building?
        Kubernetes should not route traffic to a pod that answers healthy
        but not ready -- it would serve `/query` requests against an empty
        index."""
        rag_engine: RagEngine = request.app.state.rag_engine
        return ReadinessResponse(
            status="ready" if rag_engine.is_ready else "not_ready",
            index_ready=rag_engine.is_ready,
            chunk_count=rag_engine.chunk_count,
        )

    return app


app = create_app()
