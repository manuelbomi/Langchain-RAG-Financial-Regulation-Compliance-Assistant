"""
A minimal in-process circuit breaker.

`tenacity` (used for retry/backoff on real provider calls) does not ship a
circuit breaker primitive, so this small stateful class fills that gap:
after `failure_threshold` consecutive failures, the breaker "opens" and
fails fast (without attempting the network call) for `reset_after_seconds`,
protecting the service from hammering a degraded upstream LLM provider and
from cascading latency into every incoming request.

This is process-local (in-memory) state, which is the right tradeoff for a
single-instance demo; a multi-replica production deployment would back
this with a shared store (Redis) if cross-replica circuit state is
desired -- noted in README Roadmap.
"""

from __future__ import annotations

import threading
import time

from compliance_copilot.domain.exceptions import LLMProviderError


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_after_seconds: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._reset_after_seconds = reset_after_seconds
        self._failure_count = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def _is_open(self) -> bool:
        if self._opened_at is None:
            return False
        # Half-open: once reset_after_seconds has elapsed, allow the next
        # call through to probe recovery rather than staying open forever.
        return time.monotonic() - self._opened_at < self._reset_after_seconds

    def before_call(self) -> None:
        with self._lock:
            if self._is_open():
                raise LLMProviderError(
                    "Circuit breaker open: upstream LLM provider recently failed "
                    f"{self._failure_count} times consecutively; failing fast."
                )

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._opened_at = time.monotonic()
