"""
Application configuration, loaded from environment variables (and an
optional local `.env` file for developer convenience) via pydantic-settings.

Design decision: a single `Settings` object is constructed once (see
`get_settings()`, which is `lru_cache`d) and threaded through the app via
FastAPI dependency injection (see api/deps.py). Nothing in this codebase
reads `os.environ` directly outside this module -- that keeps all
configuration surfaced in one place and makes it trivial to audit for
accidentally hardcoded secrets.

No secret ever has a real default value here: API keys default to empty
string, which the LLM provider factory (infrastructure/llm/provider_factory.py)
treats as "provider unavailable" and falls back to the offline MockLLM.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings. See `.env.example` for documented
    defaults and the meaning of each field."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_name: str = Field(default="compliance-copilot", alias="APP_NAME")

    # --- API server ---
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # --- LLM provider ---
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # --- Retrieval / RAG tuning ---
    corpus_dir: str = Field(default="data/sample_policies", alias="CORPUS_DIR")
    vector_index_dir: str = Field(default=".index/faiss", alias="VECTOR_INDEX_DIR")
    chunk_size: int = Field(default=800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=120, alias="CHUNK_OVERLAP")
    retrieval_top_k: int = Field(default=4, alias="RETRIEVAL_TOP_K")
    hybrid_dense_weight: float = Field(default=0.6, alias="HYBRID_DENSE_WEIGHT")
    hybrid_sparse_weight: float = Field(default=0.4, alias="HYBRID_SPARSE_WEIGHT")
    similarity_refusal_threshold: float = Field(
        default=0.22, alias="SIMILARITY_REFUSAL_THRESHOLD"
    )

    # --- Governance ---
    audit_log_path: str = Field(default=".audit/audit.log.jsonl", alias="AUDIT_LOG_PATH")
    enable_pii_redaction: bool = Field(default=True, alias="ENABLE_PII_REDACTION")

    # --- Observability ---
    otel_tracing_enabled: bool = Field(default=True, alias="OTEL_TRACING_ENABLED")

    @property
    def corpus_path(self) -> Path:
        return Path(self.corpus_dir)

    @property
    def vector_index_path(self) -> Path:
        return Path(self.vector_index_dir)

    @property
    def audit_log_file(self) -> Path:
        return Path(self.audit_log_path)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Using `lru_cache` (rather than a module
    global) makes it easy for tests to bypass the cache by constructing
    `Settings(...)` directly with overrides, while production code paths
    all share one instance."""
    return Settings()
