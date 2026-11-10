"""Export one sanitized Catalyst run as standard OpenTelemetry OTLP spans."""

from __future__ import annotations

import json
import re
from collections import deque
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from .trace_log import JsonlTraceStore


class OTelExportError(RuntimeError):
    """The run cannot be exported or the optional OTel packages are unavailable."""


def _time_ns(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(parsed.timestamp() * 1_000_000_000)


def _attributes(value: Any) -> Any:
    """Convert safe JSON values to OpenTelemetry attribute values."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)) and all(
        isinstance(item, (str, bool, int, float)) for item in value
    ):
        return list(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def export_run_otlp(
    workspace,
    run_id: str,
    endpoint: str,
    *,
    exporter=None,
) -> dict[str, Any]:
    """Convert versioned run spans to OTLP and synchronously export them.

    ``endpoint`` is a complete OTLP/HTTP traces URL such as
    ``http://127.0.0.1:4318/v1/traces``. No authorization headers are read from
    environment variables. Incomplete operations export with zero duration plus
    an explicit ``catalyst.end_observed=false`` attribute; their durations are
    not fabricated.
    """
    if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
        raise ValueError("endpoint must be a complete http:// or https:// OTLP traces URL")
    parsed_endpoint = urlsplit(endpoint)
    if (
        not parsed_endpoint.hostname
        or parsed_endpoint.username is not None
        or parsed_endpoint.password is not None
        or parsed_endpoint.query
        or parsed_endpoint.fragment
    ):
        raise ValueError(
            "endpoint must not contain embedded credentials, query parameters, or a fragment"
        )
    try:
        from opentelemetry import trace
        from opentelemetry.context import Context
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.id_generator import IdGenerator
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.trace import SpanKind, Status, StatusCode
    except ImportError as exc:
        raise OTelExportError(
            "OpenTelemetry export needs requirements-observability.txt installed"
        ) from exc

    inspected = JsonlTraceStore(workspace).inspect_run(run_id)
    if inspected is None:
        raise OTelExportError(f"run {run_id!r} was not found in the local trace")
    events = inspected["events"]
    starts = {
        event["span_id"]: event
        for event in events
        if event.get("event_type") == "span.started" and isinstance(event.get("span_id"), str)
    }
    ends = {
        event["span_id"]: event
        for event in events
        if event.get("event_type") == "span.ended" and isinstance(event.get("span_id"), str)
    }
    if not starts:
        raise OTelExportError("the run contains no versioned span.started events")
    trace_ids = {event.get("trace_id") for event in events if event.get("trace_id")}
    if len(trace_ids) != 1:
        raise OTelExportError("the run does not have one consistent trace_id")
    trace_id = next(iter(trace_ids))
    if not re.fullmatch(r"[0-9a-fA-F]{32}", trace_id):
        raise OTelExportError("the run trace_id is not a W3C 128-bit hexadecimal trace ID")

    ordered_span_ids = [
        event["span_id"]
        for event in events
        if event.get("event_type") == "span.started" and event.get("span_id") in starts
    ]

    class ReplayIdGenerator(IdGenerator):
        def __init__(self):
            self._span_ids = deque(int(item, 16) for item in ordered_span_ids)
            self._trace_id = int(trace_id, 16)

        def generate_span_id(self) -> int:
            return self._span_ids.popleft() if self._span_ids else 1

        def generate_trace_id(self) -> int:
            return self._trace_id

    destination = exporter or OTLPSpanExporter(endpoint=endpoint, headers={})
    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": "catalyst-platform", "service.version": "R5"}
        ),
        id_generator=ReplayIdGenerator(),
    )
    provider.add_span_processor(SimpleSpanProcessor(destination))
    tracer = provider.get_tracer("catalyst.observability", "1.0")

    start_by_id = starts
    spans: dict[str, Any] = {}
    ordered_starts = sorted(
        (event for event in starts.values()), key=lambda event: event["sequence"]
    )
    root_span_id = next(
        (event["span_id"] for event in ordered_starts if event.get("parent_span_id") is None),
        ordered_starts[0]["span_id"],
    )
    context = Context()
    for event in ordered_starts:
        parent_id = event.get("parent_span_id")
        parent = spans.get(parent_id)
        parent_context = trace.set_span_in_context(parent, context) if parent is not None else context
        kind = str(event.get("span_kind", "INTERNAL")).upper()
        span_kind = SpanKind.CLIENT if kind == "LLM" else SpanKind.INTERNAL
        attributes: dict[str, Any] = {
            "catalyst.run_id": run_id,
            "catalyst.event_schema_version": event.get("event_schema_version", "1.0"),
            "catalyst.redaction_policy_version": event.get(
                "redaction_policy_version", "sha256-content-fields-v1"
            ),
            "catalyst.span.name": event.get("span_name", "catalyst.operation"),
            "openinference.span.kind": event.get("openinference.span.kind", kind),
        }
        for field in (
            "request_id",
            "invocation_id",
            "request_kind",
            "model_call_id",
            "tool_call_id",
            "execution_id",
            "capability_internal_id",
            "capability_id",
            "capability_version",
            "binding_digest",
            "side_effect",
            "implementation_class",
            "component_id",
            "component_version",
            "manifest_sha256",
            "source_sha256",
            "package_sha256",
            "provider_id",
            "model",
        ):
            if event.get(field) is not None:
                attributes[f"catalyst.{field}"] = _attributes(event[field])
        for key, value in event.get("attributes", {}).items():
            converted = _attributes(value)
            if converted is not None:
                attributes[key] = converted
        attributes["catalyst.end_observed"] = event["span_id"] in ends
        span = tracer.start_span(
            str(event.get("span_name", "catalyst.operation")),
            context=parent_context if parent_id is not None else None,
            kind=span_kind,
            attributes=attributes,
            start_time=_time_ns(event["timestamp"]),
        )
        spans[event["span_id"]] = span

    event_span_id: dict[str, str] = {}
    for event in events:
        if event.get("event_type", "").startswith("span."):
            continue
        direct_span = event.get("span_id")
        parent_span = event.get("parent_span_id")
        event_span_id[event["event_id"]] = (
            direct_span
            if direct_span in spans
            else parent_span
            if parent_span in spans
            else root_span_id
        )
        target = spans[event_span_id[event["event_id"]]]
        attributes = {}
        for key, value in event.items():
            if key in {
                "event_id",
                "event_type",
                "timestamp",
                "event_schema_version",
                "run_id",
                "sequence",
                "request_id",
                "invocation_id",
                "trace_id",
                "span_id",
                "parent_span_id",
            }:
                continue
            converted = _attributes(value)
            if converted is not None:
                attributes[f"catalyst.{key}"] = converted
        target.add_event(
            str(event.get("event_type", "catalyst.event")),
            attributes=attributes,
            timestamp=_time_ns(event["timestamp"]),
        )

    for event in reversed(ordered_starts):
        span = spans[event["span_id"]]
        end = ends.get(event["span_id"])
        if end is None:
            span.set_attribute("catalyst.outcome", "incomplete")
            span.end(end_time=_time_ns(event["timestamp"]))
            continue
        status = end.get("status", "unknown")
        span.set_attribute("catalyst.outcome", status)
        if status == "success":
            span.set_status(Status(StatusCode.OK))
        elif status not in {"incomplete", "running"}:
            span.set_status(Status(StatusCode.ERROR, description=str(status)))
        span.end(end_time=_time_ns(end["timestamp"]))

    provider.force_flush()
    provider.shutdown()
    return {
        "run_id": run_id,
        "trace_id": trace_id,
        "spans_exported": len(spans),
        "terminal_status": inspected["terminal_status"],
        "observed_status": inspected["status"],
        "endpoint": endpoint,
        "protocol": "otlp-http-protobuf",
    }
