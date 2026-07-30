# Multi-stage build: keeps the final runtime image free of compilers,
# build tooling, and pip caches, and runs as a non-root user throughout.

# ---- Stage 1: builder ----
FROM python:3.10-slim-bookworm AS builder

WORKDIR /build

# Build tooling is needed here only (not in the final image) to compile
# any dependency that ships without a prebuilt wheel for the target arch.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 2: runtime ----
FROM python:3.10-slim-bookworm AS runtime

# Pinned, minimal runtime -- no compilers, no package manager cache.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appgroup \
    && useradd --system --gid appgroup --home-dir /app --create-home appuser

WORKDIR /app

# Bring in only the installed Python packages from the builder stage. This
# MUST land under appuser's actual $HOME (/app, per the `useradd
# --home-dir /app` above) -- Python's user-site mechanism resolves
# `~/.local` from $HOME at *runtime*, not from where the files physically
# live, so copying to any other path silently breaks `import` for every
# dependency once running as `appuser`.
COPY --from=builder --chown=appuser:appgroup /root/.local /app/.local

COPY src/ ./src/
COPY data/ ./data/
COPY pyproject.toml ./

ENV PATH=/app/.local/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    CORPUS_DIR=/app/data/sample_policies \
    VECTOR_INDEX_DIR=/app/.index/faiss \
    AUDIT_LOG_PATH=/app/.audit/audit.log.jsonl

# Runtime-writable directories for the local index/audit log, owned by the
# non-root user the process actually runs as.
RUN mkdir -p /app/.index /app/.audit \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "compliance_copilot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
