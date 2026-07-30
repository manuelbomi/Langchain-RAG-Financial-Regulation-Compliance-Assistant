"""
compliance_copilot
===================

Policy & Regulatory Research Copilot: a self-hosted LangChain RAG system for
financial compliance teams.

This package is organized into four layers, in dependency order (outer
layers depend on inner ones, never the reverse):

    api/            FastAPI HTTP boundary: request/response schemas, routes.
    service/        Application/use-case orchestration (query answering,
                    ingestion, guardrail enforcement). Coordinates domain +
                    infrastructure but contains no framework-specific code.
    domain/         Framework-agnostic core types and business rules
                    (documents, citations, answers, exceptions). No
                    dependency on FastAPI, LangChain, or any I/O library.
    infrastructure/ Concrete adapters: FAISS vector store, BM25 sparse
                    index, LLM provider clients, config, logging, tracing,
                    PII redaction. Implements interfaces the service layer
                    depends on.

This is a portfolio/demo project. All sample data under `data/sample_policies/`
is synthetic and references a fictional bank, "Northbridge Financial Group",
invented solely for this demo.
"""

__all__: list[str] = []
__version__ = "0.1.0"
