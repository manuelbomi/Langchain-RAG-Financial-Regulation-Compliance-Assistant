"""
Structured (JSON) logging setup with correlation/request ID support.

Every log line emitted through the logger configured here is a single JSON
object, which makes this service's logs directly ingestible by log
aggregation stacks (e.g. Loki, ELK, Splunk) without a custom parser --
important for a regulated environment where audit trails must be reliable
and machine-parseable.

Correlation IDs: `request_id` is bound via `contextvars` so that every log
line emitted while handling a given HTTP request automatically carries the
same ID, without threading it through every function signature by hand.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    """Bind a request/correlation ID for the current async context."""
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx.get()


class _RequestIdFilter(logging.Filter):
    """Injects the current correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


# Field names that must NEVER appear with real values in log output. This is
# a defense-in-depth belt-and-suspenders check on top of never passing
# secrets into `extra=` in the first place -- see SECURITY.md.
_SENSITIVE_KEYS = {"api_key", "openai_api_key", "anthropic_api_key", "authorization", "password"}


class _RedactSensitiveFilter(logging.Filter):
    """Strips known-sensitive keys from the record's `__dict__` if a caller
    accidentally passes them via `extra=`."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__.keys()):
            if key.lower() in _SENSITIVE_KEYS:
                record.__dict__[key] = "***REDACTED***"
        return True


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Idempotently configure the root logger for JSON structured output.

    Safe to call multiple times (e.g. once at app startup, once per test
    module) -- it clears existing handlers first so log lines are never
    duplicated.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(_RequestIdFilter())
    handler.addFilter(_RedactSensitiveFilter())
    root.addHandler(handler)
    return root


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
