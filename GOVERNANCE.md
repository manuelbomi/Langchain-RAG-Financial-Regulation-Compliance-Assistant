# Governance

This document describes the governance controls implemented in this
project, why they exist, and where in the code to find them. It is written
in the register of an internal control document because that is the
audience this project is built to demonstrate fluency with -- but nothing
here describes a real institution's actual program.

> All data, policy documents, and scenarios referenced in this repository
> belong to the fictional demo bank **"Northbridge Financial Group"** and
> are entirely synthetic. See the README for the full disclaimer.

## 1. Citation Enforcement

Every answer this system returns must be grounded in the retrieved
passages it was given, or it is not returned at all.

- **Mechanism:** `service/guardrails.py::CitationEnforcer.enforce()`
  extracts every `[SECTION:<section_id>]` tag from a candidate answer and
  checks each `section_id` against the set of `section_id`s actually
  present in the retrieved passage set for that query. An answer with zero
  citation tags, or with a citation tag not present in the retrieved set,
  is **rejected** -- not flagged, rejected -- and the system either retries
  generation once or falls back to an explicit refusal.
- **Why this matters:** a model that free-lances a plausible-sounding
  section number (or answers from parametric knowledge instead of the
  retrieved text) is indistinguishable from a correct answer unless
  something actually checks the citation against ground truth. This is
  that check.
- **Tested:** `tests/test_citation_enforcement.py` exercises this against
  a deliberately fabricated citation and a deliberately citation-free
  answer, and asserts both are rejected.

## 2. Refusal Behavior

If retrieval does not surface a passage above
`SIMILARITY_REFUSAL_THRESHOLD` (default `0.22`, see `.env.example`), the
system refuses rather than answers. See `service/query_service.py::
QueryService.answer_query()`.

This is a deliberate tradeoff: a compliance research tool that
occasionally says "I don't have grounded information for that" is far
safer than one that occasionally fabricates policy guidance with
confidence. Refusal is treated as a normal, successful outcome in this
system's design (see `domain/models.py::GroundedAnswer.refused`), not an
error path.

## 3. Faithfulness Evaluation

`service/guardrails.py::FaithfulnessEvaluator` scores the lexical overlap
between an answer's claims and the text of the passages it cites, applied
both inline (surfaced in every `/query` response as
`faithfulness_score`) and via the standalone offline harness at
`scripts/run_faithfulness_eval.py`, which can be wired into CI as a
regression gate (see `.github/workflows/ci.yml`).

This is a lexical-overlap proxy, not an NLI/entailment model -- an
intentional scope decision for a self-hosted demo. See README Roadmap for
the production upgrade path.

## 4. Audit Logging

Every query and its resulting answer -- grounded or refused -- is appended
to a local, append-only JSONL audit log (`AUDIT_LOG_PATH`, default
`.audit/audit.log.jsonl`) by `service/guardrails.py::AuditLogger`. Each
record includes: timestamp, request/correlation ID, the (PII-redacted)
query text, whether the answer was refused, the citations returned, the
faithfulness score, the LLM provider used, and the section IDs retrieved.

This gives a compliance/audit function exactly what it needs to
reconstruct "what did this system tell someone, and what did it base that
on" after the fact -- a baseline expectation for any AI system operating
in a regulated context.

## 5. PII Redaction

Query text is passed through `infrastructure/security/pii_redaction.py`
before being written to the audit log (gated by `ENABLE_PII_REDACTION`,
default `true`). This is a conservative regex-based redaction of common
PII patterns (email, SSN-shaped numbers, card-number-shaped digit
sequences, phone numbers) -- see the module docstring for why this is
explicitly scoped as a heuristic, not a comprehensive DLP solution.

## 6. Prompt-Injection Resistance

Retrieved document text is treated as **untrusted data**, never as
instructions, throughout this system. See the detailed explanation in
`service/query_service.py`'s module docstring and the README's "Governance
& Guardrails" section for the full mechanism (delimiter-based isolation,
explicit system-prompt instruction to ignore embedded instructions, and
citation enforcement as a backstop even if that instruction is ignored by
the model).

## 7. Access to Classified Content

The sample corpus's Data Classification Standard
(`data/sample_policies/data_classification_standard.md`) specifies that a
production retrieval system must carry classification tier as retrievable
chunk metadata and gate access accordingly. This demo implements the
metadata plumbing (`domain/models.py::DocumentChunk.classification`,
surfaced in `GET /corpus`) but does not implement per-user entitlement
enforcement, since this demo has no authentication layer -- see README
Roadmap for the intended extension (an auth middleware that scopes
retrieval to a requester's entitled classification tiers).

## 8. Human Accountability

This system has no write-capable tools and takes no autonomous action --
it only answers questions with citations, or refuses. Every response is
explicitly framed (in the system prompt and, implicitly, by requiring
citations) as a starting point for a human researcher to verify against
source policy, not a final determination. Production deployment of any
higher-autonomy extension of this pattern (e.g. an agent that drafts a
customer communication) should require human review before any
consequential action, consistent with the human-in-the-loop expectations
described in the sample Model Risk Management Policy.
