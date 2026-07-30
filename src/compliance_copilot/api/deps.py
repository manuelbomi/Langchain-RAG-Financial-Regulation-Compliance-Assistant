"""
FastAPI dependency providers.

The RagEngine, LLM client, and QueryService are constructed once at app
startup (see api/main.py `lifespan`) and stored on `app.state`. These
dependency functions simply retrieve them per-request, which keeps route
handlers free of any construction logic and makes it trivial to override
these dependencies in tests via `app.dependency_overrides`.
"""

from __future__ import annotations

from fastapi import Request

from compliance_copilot.infrastructure.config import Settings
from compliance_copilot.service.guardrails import AuditLogger
from compliance_copilot.service.query_service import QueryService
from compliance_copilot.service.rag_engine import RagEngine


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_rag_engine(request: Request) -> RagEngine:
    return request.app.state.rag_engine


def get_query_service(request: Request) -> QueryService:
    return request.app.state.query_service


def get_audit_logger(request: Request) -> AuditLogger:
    return request.app.state.audit_logger
