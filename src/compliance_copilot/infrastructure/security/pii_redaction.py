"""
Lightweight, dependency-free PII redaction utility.

Used in two places:
  1. Audit logging (service/guardrails.py) -- so that if a user pastes PII
     into a free-text query, it is not persisted verbatim in the audit
     trail (governance requirement -- see GOVERNANCE.md).
  2. Optionally on API responses, gated by `ENABLE_PII_REDACTION`.

This is intentionally a set of conservative regex heuristics, not a claim
of comprehensive PII detection. A production deployment handling real
customer data should back this with a dedicated PII/DLP service (e.g. a
named-entity-recognition model or a vendor DLP API) -- see README Roadmap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Ordered (label, compiled pattern) pairs. Order matters only for
# readability of the redaction reason; patterns do not overlap in practice
# for the synthetic test inputs this project ships with.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    # US Social Security Number style: 123-45-6789
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    # Generic 13-19 digit payment-card-like sequence, with optional
    # separators, using a word boundary so it doesn't clip longer numbers.
    ("CARD_NUMBER", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    # US-style phone numbers.
    ("PHONE", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
]


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted_count: int
    labels_found: list[str]


def redact_pii(text: str) -> RedactionResult:
    """Replace detected PII substrings with a `[REDACTED:<LABEL>]` marker.

    Returns the redacted text plus a count/labels summary so callers (e.g.
    the audit logger) can record *that* redaction occurred without ever
    persisting the original sensitive value.
    """
    redacted_text = text
    total = 0
    labels: list[str] = []

    for label, pattern in _PATTERNS:
        def _sub(match: re.Match[str], _label: str = label) -> str:
            nonlocal total, labels
            total += 1
            labels.append(_label)
            return f"[REDACTED:{_label}]"

        redacted_text = pattern.sub(_sub, redacted_text)

    return RedactionResult(text=redacted_text, redacted_count=total, labels_found=labels)
