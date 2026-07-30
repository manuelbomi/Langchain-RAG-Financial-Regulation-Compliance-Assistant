"""
Tracing setup using the OpenTelemetry SDK, configured with an in-process
console/no-op exporter by default so the demo has zero external
dependencies (no collector required to run this repo out of the box).

In a real deployment, swap `ConsoleSpanExporter` for an OTLP exporter
pointed at your collector (Tempo, Jaeger, Honeycomb, etc.) -- see README
"Observability" for the drop-in change. The span *structure* (retrieval
span -> generation span -> guardrail span, all children of a request span)
does not need to change.

We wrap span creation in a tiny helper (`traced_span`) rather than
sprinkling `tracer.start_as_current_span` everywhere, so tracing can be
globally disabled via `OTEL_TRACING_ENABLED=false` (useful in constrained
CI environments) with a single no-op fallback.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

_configured = False


def configure_tracing(service_name: str = "compliance-copilot", enabled: bool = True) -> None:
    """Configure a process-wide TracerProvider. Idempotent."""
    global _configured
    if _configured or not enabled:
        return
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    # ConsoleSpanExporter keeps this demo dependency-free; a production
    # deployment would use OTLPSpanExporter here instead.
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str = "compliance_copilot"):
    return trace.get_tracer(name)


@contextmanager
def traced_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[None]:
    """Start a span if tracing has been configured; otherwise this is a
    cheap no-op so call sites don't need to branch on configuration state."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield
