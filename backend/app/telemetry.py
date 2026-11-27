"""W3C traceparent correlation and optional OpenTelemetry span instrumentation."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("nidan.telemetry")

_TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_or_create_traceparent(header_value: str | None) -> tuple[str, str, str]:
    """Return (trace_id_32hex, parent_or_span_id_16hex, formatted_traceparent)."""
    if header_value:
        match = _TRACEPARENT_RE.match(header_value.strip().lower())
        if match:
            trace_id = match.group(1)
            span_id = uuid.uuid4().hex[:16]
            flags = match.group(3)
            return trace_id, span_id, f"00-{trace_id}-{span_id}-{flags}"

    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    return trace_id, span_id, f"00-{trace_id}-{span_id}-01"


@contextmanager
def trace_http_span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Start an OpenTelemetry span when opentelemetry-api is installed, else no-op."""
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]

        tracer = trace.get_tracer("nidan.api")
        with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
            yield span
            return
    except ImportError:
        yield None


def configure_opentelemetry(service_name: str, otlp_endpoint: str) -> bool:
    """Configure OTLP span export if opentelemetry-sdk and endpoint are configured."""
    if not otlp_endpoint:
        return False
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace.export import (  # type: ignore[import-not-found]
            BatchSpanProcessor,
        )

        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry OTLP exporter configured -> %s", otlp_endpoint)
        return True
    except ImportError:
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT set (%s), but opentelemetry-sdk is not installed.",
            otlp_endpoint,
        )
        return False
