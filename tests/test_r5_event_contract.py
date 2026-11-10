"""R5: extension-facing run events are allowlisted before every export surface."""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

from catalyst_platform.monitor import create_monitor_server
from catalyst_platform.observability import RunRecorder
from catalyst_platform.otel_export import export_run_otlp
from catalyst_platform.trace_log import JsonlTraceStore


def test_unknown_fields_and_nested_custom_data_are_absent_from_jsonl_sse_and_otlp(tmp_path):
    pytest.importorskip("opentelemetry.sdk.trace")
    workspace = tmp_path / "workspace"
    store = JsonlTraceStore(workspace)
    recorder = RunRecorder(
        store,
        run_id="run_r5_redaction",
        request_id="req_r5_redaction",
        invocation_id="inv_r5_redaction",
        trace_id="5" * 32,
    )
    marker = "sk-r5-must-never-escape"
    recorder.start(request_kind="component_execution")
    span_id = recorder.start_span(
        "component.execute",
        kind="TOOL",
        component_id="local_text_stats",
        component_version="1.0.0",
        manifest_sha256="c" * 64,
        source_sha256="d" * 64,
        package_sha256="e" * 64,
        attributes={
            "openinference.span.kind": "TOOL",
            "tool.name": "local_text_stats",
            "custom.extension.payload": marker,
            "password": marker,
        },
    )
    recorder.event(
        "tool.call.requested",
        tool_name="local_text_stats",
        arguments_sha256="a" * 64,
        api_key=marker,
        custom_extension_payload=marker,
        sensitive_parameters={"path": marker, "secret": marker},
    )
    recorder.event(
        "agent.decision",
        model_call_present=True,
        tool_calls=[
            {
                "tool_call_id": "call-safe",
                "tool_name": "local_text_stats",
                "arguments_sha256": "b" * 64,
                "arguments": marker,
                "provider_secret": marker,
            }
        ],
    )
    recorder.event(
        "component.lifecycle.failed",
        action="admit",
        error_code="component_operation_failed",
        error_type="ComponentError",
        error_message=f"provider rejected api_key={marker}; path=C:\\private\\input.txt",
    )
    with pytest.raises(ValueError, match="unsupported run event type"):
        recorder.event("component.custom.unreviewed", access_token=marker)
    recorder.end_span(span_id, status="success", attributes={"custom.output": marker})
    recorder.finish("success")

    raw_jsonl = store.path.read_text(encoding="utf-8")
    replay = store.inspect_run("run_r5_redaction")
    assert replay is not None
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "run_event_v1_4.schema.json").read_text(
            encoding="utf-8"
        )
    )
    for event in replay["events"]:
        validate(event, schema)
    with pytest.raises(ValidationError):
        validate({**replay["events"][0], "custom_extension_payload": marker}, schema)
    assert marker not in raw_jsonl
    assert all("custom_extension_payload" not in event for event in replay["events"])
    assert all("sensitive_parameters" not in event for event in replay["events"])
    lifecycle_failure = next(
        event for event in replay["events"]
        if event["event_type"] == "component.lifecycle.failed"
    )
    assert "error_message" not in lifecycle_failure
    span_start = next(
        event
        for event in replay["events"]
        if event["event_type"] == "span.started" and event.get("span_name") == "component.execute"
    )
    assert span_start["attributes"] == {
        "openinference.span.kind": "TOOL",
        "tool.name": "local_text_stats",
    }
    decision = next(event for event in replay["events"] if event["event_type"] == "agent.decision")
    assert decision["tool_calls"] == [
        {
            "tool_call_id": "call-safe",
            "tool_name": "local_text_stats",
            "arguments_sha256": "b" * 64,
        }
    ]

    monitor = create_monitor_server(workspace, lambda *_args: None, port=0)
    monitor_thread = threading.Thread(target=monitor.serve_forever, daemon=True)
    monitor_thread.start()
    try:
        monitor_url = f"http://127.0.0.1:{monitor.server_address[1]}"
        page = urllib.request.urlopen(monitor_url + "/", timeout=5).read()
        assert "组件生命周期变更".encode("utf-8") in page
        assert b"event.component_id" in page
        streamed = urllib.request.urlopen(
            monitor_url + "/api/runs/run_r5_redaction/stream?after=-1", timeout=5
        ).read()
    finally:
        monitor.shutdown()
        monitor.server_close()
        monitor_thread.join(timeout=5)
    assert marker.encode("utf-8") not in streamed
    assert b"component.custom.unreviewed" not in streamed
    assert b"component.lifecycle.failed" in streamed

    received: list[bytes] = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            received.append(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, _format, *_args):
            return

    receiver = HTTPServer(("127.0.0.1", 0), Receiver)
    receiver_thread = threading.Thread(target=receiver.serve_forever, daemon=True)
    receiver_thread.start()
    try:
        endpoint = f"http://127.0.0.1:{receiver.server_address[1]}/v1/traces"
        exported = export_run_otlp(workspace, "run_r5_redaction", endpoint)
    finally:
        receiver.shutdown()
        receiver.server_close()
        receiver_thread.join(timeout=5)
    assert exported["spans_exported"] == 2
    assert received
    assert all(marker.encode("utf-8") not in body for body in received)
    assert any(b"local_text_stats" in body and b"manifest_sha256" in body for body in received)
