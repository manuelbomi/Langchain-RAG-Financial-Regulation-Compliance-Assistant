# Security

This is a portfolio/demo project, not a production system, but it is built
to production-hardening standards so the practices below are real and
enforced in code, not aspirational.

## Reporting a Concern

This is a personal portfolio project with no production deployment or user
data. If you spot a security issue in the code or configuration, please
open an issue in the repository describing it. There is no bug bounty and
no SLA, but genuine reports are welcome.

## Dependency Management

- All dependencies are version-pinned in `requirements.txt` and
  `requirements-dev.txt` (no floating `>=` ranges) so builds are
  reproducible and a supply-chain change upstream cannot silently alter
  this project's behavior.
- The Docker image uses a pinned base image tag (`python:3.10-slim-bookworm`)
  and a multi-stage build so the final runtime image contains no compiler
  toolchain, no `pip` cache, and no dev/test dependencies -- reducing the
  attack surface of the shipped artifact.
- CI (`.github/workflows/ci.yml`) installs from the pinned lockfile-style
  requirements files on every run.

## Secrets Handling

- No secret has a real default value anywhere in this codebase.
  `.env.example` ships placeholder/empty values only; a real `.env` is
  gitignored (see `.gitignore`).
- `infrastructure/config.py` is the single place environment variables are
  read (via `pydantic-settings`) -- nothing else in the codebase calls
  `os.environ` directly, which makes it straightforward to audit for
  accidental secret exposure.
- `infrastructure/logging_setup.py` includes a logging filter
  (`_RedactSensitiveFilter`) that strips known-sensitive field names
  (`api_key`, `authorization`, `password`, etc.) from any log record,
  as defense-in-depth on top of never intentionally logging a secret.
- Kubernetes API keys are supplied via a `Secret`
  (`deploy/k8s/secret.yaml.example`), never a `ConfigMap`, and the example
  file is explicitly marked as a template that must not be committed
  filled-in.

## Network Egress

The default configuration (`LLM_PROVIDER=mock`) makes **zero** outbound
network calls: FAISS and the BM25 index are local/in-process, and MockLLM
is a pure-Python, no-network implementation. Outbound calls to a real LLM
provider only happen if `LLM_PROVIDER` is explicitly set to `openai` or
`anthropic` **and** the corresponding API key environment variable is
non-empty (`infrastructure/llm/provider_factory.py`).

## Resilience Against Upstream Failures

Every external LLM provider call (used only in non-default, opt-in
provider modes) goes through:

- A hard request timeout (`REQUEST_TIMEOUT_SECONDS` in
  `infrastructure/llm/real_providers.py`).
- `tenacity`-managed retry with exponential backoff and jitter
  (`wait_random_exponential`), capped at 3 attempts.
- A per-client in-process circuit breaker
  (`infrastructure/llm/circuit_breaker.py`) that fails fast after repeated
  consecutive failures rather than continuing to hammer a degraded
  upstream.

## Prompt-Injection Mitigation

Retrieved document text is always treated as untrusted input, never as
instructions -- see the detailed explanation in
`service/query_service.py`'s module docstring and `GOVERNANCE.md` section
6. This matters specifically for RAG systems: unlike a typical web app
where untrusted input is a request body, in a RAG system the "untrusted
input" also includes every document your own retrieval pipeline surfaces,
including ones an adversary may have been able to write to a source
repository.

## Input Validation

Every request to the API is validated by a Pydantic model at the boundary
(`api/schemas.py`) before it reaches any business logic -- e.g. `POST
/query` enforces a bounded question length (`3-2000` characters), which
also acts as a basic guard against pathological/oversized prompts.

## Container Security

- Runs as a non-root user (`appuser`) end to end, in both the Dockerfile
  and the Kubernetes `securityContext` (`deploy/k8s/deployment.yaml`),
  which also drops all Linux capabilities and disables privilege
  escalation.
- See `deploy/OPENSHIFT.md` for the additional constraints this satisfies
  under OpenShift's default restricted Security Context Constraint.
