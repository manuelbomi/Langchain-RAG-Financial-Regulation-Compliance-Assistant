# Contributing

This is a personal portfolio project, but it is built and tested like a
real one -- contributions, issues, and forks are welcome.

## Local Development

```bash
git clone <this-repo-url>
cd langchain-rag-compliance-assistant
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
make install
make test
```

See the README "Getting Started" section for the full walkthrough,
including running the API server locally.

## Before Opening a PR

```bash
make lint        # ruff
make typecheck    # mypy
make test         # pytest, with coverage
python scripts/run_faithfulness_eval.py   # offline eval harness
```

All four must pass -- this mirrors exactly what CI runs
(`.github/workflows/ci.yml`).

## Code Style

- Layering is intentional: `api/` -> `service/` -> `domain/` +
  `infrastructure/`. New code should respect that boundary -- route
  handlers stay thin, business logic lives in `service/`, framework/I/O
  code lives in `infrastructure/`.
- Every non-trivial function/class should have a docstring explaining its
  role; comments should explain *why*, not restate *what* the code does.
- Formatting/linting is enforced by `ruff` (config in `pyproject.toml`);
  run `make fmt` to auto-fix what's fixable.
- Type hints are required on public function signatures; `mypy` runs in CI.

## Adding a Sample Policy Document

Documents under `data/sample_policies/` must:

1. Start with the synthetic-data disclaimer banner (copy the format from
   an existing document).
2. Use the `# Title` / `**Document ID:**` / `## Section N: Title` Markdown
   convention that `service/ingestion_service.py::parse_document()`
   parses -- see that module's docstring for the exact grammar.
3. Never reference a real employer, institution, or actual regulation as
   if authoritative -- keep language illustrative/generic, in the voice of
   the fictional "Northbridge Financial Group."

## Adding a New LLM Provider

Implement the `infrastructure/llm/base.py::LLMClient` protocol (just
`generate()` and `provider_name`), wire it into
`infrastructure/llm/provider_factory.py::build_llm_client()`, and make sure
it degrades gracefully (falls back to `MockLLM`) if its API key is absent
-- consistent with every existing provider.

## Reporting Issues

Open a GitHub issue with a clear description and, if applicable, the
command/request that reproduces the problem.
