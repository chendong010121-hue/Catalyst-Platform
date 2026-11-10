"""R4: live, durable, redacted execution observations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from agent_runtime.contracts import (
    Action,
    Act,
    CapabilityDescriptor,
    Complete,
    Goal,
    Message,
    ModelCallRecord,
    ModelResponse,
    ModelToolCall,
    ModelUsage,
    ReasoningResult,
    Success,
)
from agent_runtime.policies import StepLimitPolicy
from agent_runtime.runtime import Runtime
from catalyst_platform.observability import ObservedModelProvider, RunRecorder
from catalyst_platform.file_title import CAPABILITY_VERSION, FileTitleCapability
from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.monitor import create_monitor_server
from catalyst_platform.otel_export import export_run_otlp
from catalyst_platform.storage import JsonFileStateStore
from catalyst_platform.workbench import CatalystWorkbench
from catalyst_platform.trace_log import JsonlTraceStore


def test_run_events_are_durable_before_terminal_and_replay_as_incomplete(tmp_path):
    store = JsonlTraceStore(tmp_path / "workspace")
    recorder = RunRecorder(
        store,
        run_id="run_live",
        request_id="req_live",
        invocation_id="inv_live",
        trace_id="a" * 32,
    )

    recorder.start(request_kind="natural_language_ask", input_sha256="b" * 64)
    llm_span = recorder.start_span(
        "llm.request",
        kind="LLM",
        parent_span_id=recorder.root_span_id,
        attributes={"llm.system": "scripted", "llm.model_name": "deterministic"},
    )

    replay = store.inspect_run("run_live")

    assert replay is not None
    assert replay["status"] == "running"
    assert replay["terminal_status"] is None
    source_revision = replay["events"][0]["source_revision_ref"]
    source_dirty = replay["events"][0]["source_worktree_dirty"]
    assert source_revision is None or source_revision.startswith("git:")
    assert source_dirty is None or isinstance(source_dirty, bool)
    assert [event["event_type"] for event in replay["events"]] == [
        "request.started",
        "span.started",
        "span.started",
    ]

    recorder.end_span(llm_span, status="success", attributes={"usage.input_tokens": 4})
    recorder.finish("success")

    completed = store.inspect_run("run_live")
    assert completed is not None
    assert completed["status"] == "success"
    assert completed["events"][-1]["event_type"] == "request.terminal"


def test_v1_events_validate_against_the_published_contract(tmp_path):
    from jsonschema import Draft202012Validator, FormatChecker

    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "run_event_v1_4.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    store = JsonlTraceStore(tmp_path / "workspace")
    recorder = RunRecorder(
        store,
        run_id="run_schema",
        request_id="req_schema",
        invocation_id="inv_schema",
        trace_id="2" * 32,
    )
    recorder.start(request_kind="schema_contract")
    recorder.event("result.emitted", status="success", result_sha256="a" * 64)
    recorder.finish("success")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    replay = store.inspect_run("run_schema")
    assert replay is not None
    assert all(not list(validator.iter_errors(event)) for event in replay["events"])


def test_actual_run_exports_as_otlp_to_a_local_receiver(tmp_path):
    pytest.importorskip("opentelemetry.sdk.trace")
    proto = pytest.importorskip(
        "opentelemetry.proto.collector.trace.v1.trace_service_pb2"
    )
    received = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            received.append(
                proto.ExportTraceServiceRequest.FromString(self.rfile.read(length))
            )
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, _format, *_args):
            return

    receiver = HTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=receiver.serve_forever, daemon=True)
    thread.start()
    try:
        workspace = tmp_path / "workspace"
        source = tmp_path / "export.md"
        source.write_text("# OTLP Source\n", encoding="utf-8")
        run = CatalystGateway(workspace).inspect_file(source)
        endpoint = f"http://127.0.0.1:{receiver.server_address[1]}/v1/traces"
        exported = export_run_otlp(workspace, run["run_id"], endpoint)
    finally:
        receiver.shutdown()
        receiver.server_close()
        thread.join(timeout=5)

    assert exported["protocol"] == "otlp-http-protobuf"
    assert exported["spans_exported"] == 2
    spans = [
        span
        for request in received
        for resource in request.resource_spans
        for scope in resource.scope_spans
        for span in scope.spans
    ]
    assert len(spans) == 2
    root = next(span for span in spans if span.name == "catalyst.run")
    tool = next(span for span in spans if span.name == "capability.execute")
    assert root.trace_id.hex() == exported["trace_id"]
    assert tool.parent_span_id.hex() == root.span_id.hex()
    attributes = {item.key: item.value for item in tool.attributes}
    assert attributes["openinference.span.kind"].string_value == "TOOL"
    assert attributes["catalyst.capability_id"].string_value == "read_file_title"
    assert attributes["catalyst.end_observed"].bool_value is True

    with pytest.raises(ValueError, match="must not contain embedded credentials") as rejected:
        export_run_otlp(workspace, run["run_id"], "http://user:private-value@127.0.0.1/v1/traces")
    assert "private-value" not in str(rejected.value)


def test_run_recorder_redacts_content_and_secret_fields_before_persisting(tmp_path):
    store = JsonlTraceStore(tmp_path / "workspace")
    recorder = RunRecorder(
        store,
        run_id="run_private",
        request_id="req_private",
        invocation_id="inv_private",
        trace_id="c" * 32,
    )
    recorder.start(request_kind="natural_language_ask", input_sha256="d" * 64)

    recorder.event(
        "assistant.final_answer",
        answer="private answer",
        source_path=r"C:\private\report.md",
        api_key="sk-live-should-never-persist",
        result_sha256="e" * 64,
    )

    raw = store.path.read_text(encoding="utf-8")
    replay = store.inspect_run("run_private")
    assert replay is not None
    assert "private answer" not in raw
    assert r"C:\private\report.md" not in raw
    assert "sk-live-should-never-persist" not in raw
    final = replay["events"][-1]
    assert final["answer_sha256"]
    assert "source_path_sha256" not in final
    assert "result_sha256" not in final


def test_provider_start_is_visible_while_provider_is_still_running(tmp_path):
    store = JsonlTraceStore(tmp_path / "workspace")
    recorder = RunRecorder(
        store,
        run_id="run_provider_live",
        request_id="req_provider_live",
        invocation_id="inv_provider_live",
        trace_id="1" * 32,
    )
    recorder.start(request_kind="natural_language_ask")
    entered = threading.Event()
    release = threading.Event()

    class BlockingProvider:
        provider_id = "scripted"
        model = "deterministic"
        mode = "offline"

        def request(self, _request):
            entered.set()
            assert release.wait(5)
            return ModelResponse(content="real deterministic answer", usage=ModelUsage(3, 2))

    provider = ObservedModelProvider(
        BlockingProvider(), recorder, invocation_id="inv_provider_live"
    )
    worker = threading.Thread(target=lambda: provider.request(object()), daemon=True)
    worker.start()
    try:
        assert entered.wait(5)
        during_request = store.inspect_run("run_provider_live")
        assert during_request is not None
        types = [event["event_type"] for event in during_request["events"]]
        assert "llm.request.started" in types
        assert "llm.response.received" not in types
        assert any(
            event["event_type"] == "span.started"
            and event.get("span_kind") == "LLM"
            for event in during_request["events"]
        )
    finally:
        release.set()
        worker.join(timeout=5)
    completed = store.inspect_run("run_provider_live")
    assert completed is not None
    started = next(
        event for event in completed["events"] if event["event_type"] == "llm.request.started"
    )
    assert started["exposed_tools"] == []
    assert started["exposed_tool_count"] == 0
    response = next(
        event for event in completed["events"] if event["event_type"] == "llm.response.received"
    )
    assert response["input_tokens"] == 3
    assert response["output_tokens"] == 2
    assert "real deterministic answer" not in store.path.read_text(encoding="utf-8")


def test_runtime_observer_links_native_tool_call_to_exact_execution(tmp_path):
    observations = []

    class ReadOnlyCapability:
        def describe(self):
            return CapabilityDescriptor(
                id="read_title",
                name="Read title",
                description="Return one title",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                output_schema={"type": "object", "properties": {}, "additionalProperties": True},
            )

        def invoke(self, _parameters, _context):
            return Success({"title": "Verified"})

    class Reasoner:
        calls = 0

        def decide(self, *_args):
            self.calls += 1
            if self.calls == 1:
                action = Action("read_title", {})
                call = ModelToolCall("call-exact-7", "read_title", "{}")
                return ReasoningResult(
                    Act(action),
                    ModelCallRecord(
                        tool_calls=(call,),
                        assistant_message=Message("assistant", tool_calls=(call,)),
                    ),
                )
            return ReasoningResult(
                Complete("The verified title is available."),
                ModelCallRecord(assistant_message=Message("assistant", "The verified title is available.")),
            )

    runtime = Runtime(
        Reasoner(),
        {"read_title": ReadOnlyCapability()},
        StepLimitPolicy(max_steps=3),
        JsonFileStateStore(tmp_path / "runtime"),
        observation_sink=observations.append,
    )
    runtime.start(Goal("Read the title"))

    requested = next(event for event in observations if event["event_type"] == "tool.requested")
    started = next(
        event for event in observations if event["event_type"] == "capability.execution.started"
    )
    completed = next(
        event for event in observations if event["event_type"] == "capability.execution.completed"
    )
    assert requested["tool_call_id"] == "call-exact-7"
    assert started["tool_call_id"] == "call-exact-7"
    assert started["execution_id"]
    assert started["execution_id"] == completed["execution_id"]
    assert completed["status"] == "success"
    assert next(event for event in observations if event["event_type"] == "reasoning.completed")["step_index"] == 0


def test_local_monitor_streams_real_workbench_events_and_replays_result(tmp_path):
    workspace = tmp_path / "workspace"
    source = workspace / "inputs" / "live.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Live Monitor Title\n", encoding="utf-8")
    entered = threading.Event()
    release = threading.Event()

    class BlockingProvider:
        provider_id = "scripted-r4"
        model = "deterministic-r4"
        mode = "offline"
        request_count = 0
        external_calls = 0

        def request(self, request):
            self.request_count += 1
            if self.request_count == 1:
                entered.set()
                assert release.wait(8)
                tool = request.tools[0]
                call = ModelToolCall(
                    "call-monitor-1",
                    tool.name,
                    json.dumps({"path": str(source.resolve())}),
                )
                return ModelResponse(
                    tool_calls=(call,), finish_reason="tool_calls", usage=ModelUsage(5, 3)
                )
            tool_message = next(
                item for item in reversed(request.messages) if item.role == "tool"
            )
            assert "Live Monitor Title" in tool_message.content
            return ModelResponse(
                content="The file title is Live Monitor Title.",
                finish_reason="stop",
                usage=ModelUsage(8, 6),
            )

    provider = BlockingProvider()

    def run_request(message, selected_file, recorder):
        app = CatalystWorkbench(workspace=workspace, wiki_roots=[workspace])
        capability = FileTitleCapability(workspace=workspace, event_sink=lambda _event: None)
        app.register_capability(
            capability.describe(),
            capability_version=CAPABILITY_VERSION,
            execution={"side_effect": "none"},
            implementation=capability,
            metadata={
                "model_policy": {
                    "mode": "selected_file_path",
                    "path_parameter": "path",
                    "max_calls": 1,
                },
                "llm_visibility": "explicit",
            },
        )
        session = app.new_session(domain={"id": "local"}, enterprise={"id": "local"})
        gateway = CatalystGateway(workspace)
        result = gateway.ask_natural_language(
            message=message,
            selected_file=selected_file,
            recorder=recorder,
            ask=lambda invocation_id, trace_id, active_recorder: session.ask(
                message,
                provider=provider,
                selected_file=selected_file,
                invocation_id=invocation_id,
                trace_id=trace_id,
                recorder=active_recorder,
            ),
        )
        # The terminal event reaches SSE before the worker publishes its
        # in-memory response; the browser must tolerate this short gap.
        time.sleep(0.3)
        return result

    server = create_monitor_server(workspace, run_request, port=0)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        page = urllib.request.urlopen(base_url + "/", timeout=5).read().decode("utf-8")
        assert "Catalyst Run Monitor" in page
        assert "EventSource" in page
        assert "data.result?.output" in page

        request = urllib.request.Request(
            base_url + "/api/ask",
            data=json.dumps(
                {"message": "Read the title of this selected file.", "selected_file": str(source)}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = json.loads(urllib.request.urlopen(request, timeout=5).read())
        run_id = started["run_id"]
        assert started["status"] == "running"
        assert entered.wait(5)

        during = json.loads(
            urllib.request.urlopen(base_url + f"/api/runs/{run_id}", timeout=5).read()
        )
        during_types = [event["event_type"] for event in during["events"]]
        assert during["status"] == "running"
        assert "llm.request.started" in during_types
        assert "llm.response.received" not in during_types
        provider_started = next(
            event for event in during["events"] if event["event_type"] == "llm.request.started"
        )
        assert [item["capability_id"] for item in provider_started["exposed_tools"]] == [
            "read_file_title"
        ]
        assert provider_started["exposed_tools"][0]["tool_name"].startswith("cap_")
        assert provider_started["exposed_tools"][0]["capability_version"] == "1.0.0"

        # Observe the SSE feed while the actual scripted Provider is still blocked.
        live_stream = urllib.request.urlopen(
            base_url + f"/api/runs/{run_id}/stream?after=0", timeout=5
        )
        live_lines = []
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            line = live_stream.readline().decode("utf-8").strip()
            if line:
                live_lines.append(line)
            if any(
                line.startswith("data: ") and '"event_type":"llm.request.started"' in line
                for line in live_lines
            ):
                break
        assert any(
            line.startswith("data: ") and '"event_type":"llm.request.started"' in line
            for line in live_lines
        )
        assert not any(
            line.startswith("data: ") and '"event_type":"llm.response.received"' in line
            for line in live_lines
        )
    finally:
        release.set()

    try:
        streamed = live_stream.read().decode("utf-8")
        assert "event: run.event" in streamed
        assert '"event_type":"tool.result"' in streamed
        assert '"event_type":"request.terminal"' in streamed
        attempts = 0
        deadline = time.monotonic() + 3
        result = None
        while time.monotonic() < deadline:
            attempts += 1
            try:
                result = json.loads(
                    urllib.request.urlopen(
                        base_url + f"/api/runs/{run_id}/result", timeout=5
                    ).read()
                )
                break
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
                time.sleep(0.05)
        assert attempts >= 2
        assert result is not None
        assert result["status"] == "success"
        assert result["result"]["output"]["answer"] == "The file title is Live Monitor Title."
        runs = json.loads(urllib.request.urlopen(base_url + "/api/runs", timeout=5).read())
        assert any(item["run_id"] == run_id and item["status"] == "success" for item in runs)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def test_abruptly_interrupted_run_is_cold_read_as_incomplete(tmp_path):
    workspace = tmp_path / "workspace"
    marker = tmp_path / "ready"
    script = (
        "from pathlib import Path; import os,time; "
        "from catalyst_platform.observability import RunRecorder; "
        "from catalyst_platform.trace_log import JsonlTraceStore; "
        "s=JsonlTraceStore(Path(os.environ['CATALYST_TEST_WORKSPACE'])); "
        "r=RunRecorder(s,run_id='run_cut',request_id='req_cut',invocation_id='inv_cut',trace_id='f'*32); "
        "r.start(request_kind='natural_language_ask',input_sha256='0'*64); "
        "r.start_span('llm.request',kind='LLM'); "
        "Path(os.environ['CATALYST_TEST_READY']).write_text('ready'); time.sleep(30)"
    )
    env = dict(
        os.environ,
        CATALYST_TEST_WORKSPACE=str(workspace),
        CATALYST_TEST_READY=str(marker),
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        deadline = time.monotonic() + 8
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists(), "child did not durably start the run"
    finally:
        process.terminate()
        process.wait(timeout=8)

    replay = JsonlTraceStore(workspace).inspect_run("run_cut")
    assert replay is not None
    assert replay["status"] == "incomplete"
    assert replay["terminal_status"] is None
    assert [event["event_type"] for event in replay["events"]] == [
        "request.started",
        "span.started",
        "span.started",
    ]


def test_a_failed_request_without_a_public_code_still_names_an_error_code(tmp_path):
    """The event contract carries a string code, so an unclassified failure still says one."""
    store = JsonlTraceStore(tmp_path / "workspace")
    recorder = RunRecorder(
        store,
        run_id="run_provider_failed",
        request_id="req_provider_failed",
        invocation_id="inv_provider_failed",
        trace_id="2" * 32,
    )
    recorder.start(request_kind="natural_language_ask")

    class RefusingProvider:
        provider_id = "scripted"
        model = "deterministic"

        def request(self, _request):
            raise ValueError("this failure carries no public code")

    provider = ObservedModelProvider(
        RefusingProvider(), recorder, invocation_id="inv_provider_failed"
    )
    with pytest.raises(ValueError):
        provider.request(object())
    recorder.finish(status="failure", model_calls=1)

    events = store.inspect_run("run_provider_failed")["events"]
    failed = next(event for event in events if event["event_type"] == "llm.request.failed")
    assert failed["error_type"] == "ValueError"
    assert failed["error_code"] == "PROVIDER_REQUEST_FAILED"
    ended = next(
        event
        for event in events
        if event["event_type"] == "span.ended" and "catalyst.error.code" in event.get("attributes", {})
    )
    assert ended["attributes"]["catalyst.error.code"] == "PROVIDER_REQUEST_FAILED"
