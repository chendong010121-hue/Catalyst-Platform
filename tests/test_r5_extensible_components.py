"""R5: explicit, version-pinned local component integration through the existing Harness."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace
from pathlib import Path

from agent_runtime.contracts import Failure, ModelResponse, ModelToolCall, Success

import catalyst_platform.__main__ as cli
from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.observability import RunRecorder
from catalyst_platform.workbench import CapabilityCatalog, CatalystWorkbench


PRODUCT_ROOT = Path(__file__).resolve().parents[1]


class ScriptedProvider:
    provider_id = "scripted-r5-test-provider"
    model = "deterministic-r5"
    mode = "offline"
    external_calls = 0

    def __init__(self, handler):
        self.handler = handler
        self.requests = []

    @property
    def request_count(self):
        return len(self.requests)

    def request(self, request):
        self.requests.append(request)
        return self.handler(request, len(self.requests))


def _payload(text: str) -> dict:
    return json.loads(text)


def _cli(monkeypatch, capsys, provider, workspace: Path, message: str, file_path=None, extra_args=()):
    monkeypatch.setattr(
        cli,
        "configured_model_provider_from_environment",
        lambda: provider,
        raising=False,
    )
    args = ["ask", "--workspace", str(workspace), "--message", message]
    if file_path is not None:
        args.extend(["--file", str(file_path)])
    args.extend(extra_args)
    code = cli.main(args)
    return code, _payload(capsys.readouterr().out)


def _component_command(capsys, workspace: Path, *args):
    code = cli.main(["component", *args, "--workspace", str(workspace)])
    output = capsys.readouterr()
    return code, _payload(output.out) if output.out.strip() else {"stderr": output.err}


def _cold_inspect(workspace: Path, run_id: str) -> dict:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "catalyst_platform",
            "inspect",
            "--workspace",
            str(workspace),
            "--run-id",
            run_id,
        ],
        cwd=PRODUCT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert process.returncode == 0, process.stderr
    return _payload(process.stdout)


def _tool_call(request, capability_id: str, version: str, arguments: dict, call_id: str):
    key = CapabilityCatalog.internal_key(capability_id, version)
    assert [tool.name for tool in request.tools] == [key]
    return ModelResponse(
        tool_calls=(
            ModelToolCall(
                id=call_id,
                name=key,
                arguments=json.dumps(arguments, ensure_ascii=False),
            ),
        ),
        finish_reason="tool_calls",
    )


def _last_tool_result(request) -> dict:
    tool_message = next(message for message in reversed(request.messages) if message.role == "tool")
    return json.loads(tool_message.content)


def _write_external_text_stats_package(directory: Path, version: str, *, unicode_words: bool) -> Path:
    del unicode_words  # The example version pins its actual implementation and word policy.
    source = PRODUCT_ROOT / "examples" / "local_components" / "local_text_stats" / version
    return shutil.copytree(source, directory)


def test_harness_can_expose_existing_wiki_search_binding_on_request(
    tmp_path: Path, monkeypatch, capsys
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    source = wiki / "r5-catalyst.md"
    source_bytes = "# Catalyst R5 Search\n\nCatalyst component growth evidence.\n".encode("utf-8")
    source.write_bytes(source_bytes)

    def reply(request, index):
        if index == 1:
            return _tool_call(
                request,
                "wiki_search",
                "1.0.0",
                {"query": "Catalyst component growth"},
                "call-wiki-r5",
            )
        result = _last_tool_result(request)
        assert result["evidence"][0]["source_sha256"] == hashlib.sha256(source_bytes).hexdigest()
        return ModelResponse(content="The local Wiki found the R5 source.", finish_reason="stop")

    provider = ScriptedProvider(reply)
    code, response = _cli(
        monkeypatch,
        capsys,
        provider,
        workspace,
        "Find the Catalyst component growth source.",
        extra_args=("--wiki-root", str(wiki), "--capability", "wiki_search@1.0.0"),
    )

    assert code == 0, response
    assert response["result"]["output"]["answer"] == "The local Wiki found the R5 source."
    assert len(provider.requests) == 2
    inspected = _cold_inspect(workspace, response["run_id"])
    call = next(event for event in inspected["events"] if event["event_type"] == "tool.call.requested")
    result = next(event for event in inspected["events"] if event["event_type"] == "tool.result")
    assert call["capability_id"] == result["capability_id"] == "wiki_search"
    assert call["capability_version"] == result["capability_version"] == "1.0.0"
    assert call["binding_digest"] == result["binding_digest"]
    started = next(event for event in inspected["events"] if event["event_type"] == "llm.request.started")
    assert [item["capability_id"] for item in started["exposed_tools"]] == ["wiki_search"]


def test_external_readonly_component_admission_replacement_deactivation_and_restore(
    tmp_path: Path, monkeypatch, capsys
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "sources"
    wiki.mkdir()
    source = wiki / "mixed-language.txt"
    source_bytes = "Hello \u4e16\u754c\nSecond line\n".encode("utf-8")
    source.write_bytes(source_bytes)
    package_v1 = _write_external_text_stats_package(
        tmp_path / "source-v1", "1.0.0", unicode_words=False
    )
    package_v2 = _write_external_text_stats_package(
        tmp_path / "source-v2", "2.0.0", unicode_words=True
    )

    code, discovered_v1 = _component_command(
        capsys, workspace, "discover", "--source", str(package_v1)
    )
    assert code == 0, discovered_v1
    code, discovered_v2 = _component_command(
        capsys, workspace, "discover", "--source", str(package_v2)
    )
    assert code == 0, discovered_v2
    assert discovered_v1["status"] == discovered_v2["status"] == "success"
    assert discovered_v1["phase"] == "validated"
    assert discovered_v1["component"]["resource_type"] == "tool"
    assert discovered_v1["component"]["llm_visibility"] == "explicit"
    assert discovered_v1["package_sha256"] != discovered_v2["package_sha256"]

    code, admitted_v1 = _component_command(
        capsys,
        workspace,
        "admit",
        "--source",
        str(package_v1),
        "--expected-sha256",
        discovered_v1["package_sha256"],
    )
    assert code == 0, admitted_v1
    code, admitted_v2 = _component_command(
        capsys,
        workspace,
        "admit",
        "--source",
        str(package_v2),
        "--expected-sha256",
        discovered_v2["package_sha256"],
    )
    assert code == 0, admitted_v2
    assert admitted_v1["status"] == admitted_v2["status"] == "success"
    assert admitted_v1["component"]["admitted"] is True
    assert admitted_v1["component"]["active_version"] is None

    code, active_v1 = _component_command(
        capsys, workspace, "activate", "--component-id", "local_text_stats", "--version", "1.0.0"
    )
    assert code == 0, active_v1
    assert active_v1["component"]["active_version"] == "1.0.0"

    def ask_version(version: str, call_number: str):
        def reply(request, index):
            if index == 1:
                return _tool_call(
                    request,
                    "local_text_stats",
                    version,
                    {"path": str(source.resolve())},
                    call_number,
                )
            observed = _last_tool_result(request)
            assert observed["source_sha256"] == hashlib.sha256(source_bytes).hexdigest()
            return ModelResponse(
                content=f"The file has {observed['word_count']} words.",
                finish_reason="stop",
            )

        provider = ScriptedProvider(reply)
        code, response = _cli(
            monkeypatch,
            capsys,
            provider,
            workspace,
            "Count words in this selected file.",
            source,
            (
                "--wiki-root",
                str(wiki),
                "--capability",
                f"local_text_stats@{version}",
            ),
        )
        return code, response, provider

    code_v1, run_v1, provider_v1 = ask_version("1.0.0", "call-component-v1")
    assert code_v1 == 0
    assert run_v1["result"]["output"]["tool_results"][0]["output"]["word_count"] == 3
    assert provider_v1.request_count == 2
    trace_v1 = _cold_inspect(workspace, run_v1["run_id"])
    tool_v1 = next(event for event in trace_v1["events"] if event["event_type"] == "tool.result")
    assert tool_v1["capability_version"] == "1.0.0"
    assert tool_v1["binding_digest"]
    assert tool_v1["component_id"] == "local_text_stats"
    assert tool_v1["component_version"] == "1.0.0"
    assert tool_v1["source_sha256"] == admitted_v1["source_sha256"]
    assert f"_catalyst_component_{admitted_v1['source_sha256']}" not in sys.modules

    missing_source = wiki / "missing.txt"
    missing_provider = ScriptedProvider(
        lambda request, index: (
            _tool_call(
                request,
                "local_text_stats",
                "1.0.0",
                {"path": str(missing_source.resolve())},
                "call-external-missing",
            )
            if index == 1
            else pytest.fail("a failed external Tool must stop before a final model answer")
        )
    )
    missing_code, missing_run = _cli(
        monkeypatch,
        capsys,
        missing_provider,
        workspace,
        "Count words in this selected file.",
        missing_source,
        ("--wiki-root", str(wiki), "--capability", "local_text_stats@1.0.0"),
    )
    assert missing_code == 1
    assert missing_run["result"]["error"]["code"] == "capability_failed"
    missing_trace = _cold_inspect(workspace, missing_run["run_id"])
    failed_tool = next(event for event in missing_trace["events"] if event["event_type"] == "tool.result")
    assert failed_tool["status"] == "failure"
    assert failed_tool["capability_version"] == "1.0.0"
    assert "assistant.final_answer" not in [event["event_type"] for event in missing_trace["events"]]

    inactive_provider = ScriptedProvider(lambda _request, _index: pytest.fail("inactive binding was called"))
    code_inactive, inactive_run = _cli(
        monkeypatch,
        capsys,
        inactive_provider,
        workspace,
        "Use the selected component.",
        source,
        ("--wiki-root", str(wiki), "--capability", "local_text_stats@2.0.0"),
    )
    assert code_inactive == 1
    assert inactive_provider.request_count == 0
    assert inactive_run["result"]["error"]["code"] == "capability_not_found"

    _, replaced = _component_command(
        capsys, workspace, "activate", "--component-id", "local_text_stats", "--version", "2.0.0"
    )
    assert replaced["transition"] == "replaced"
    code_v2, run_v2, _ = ask_version("2.0.0", "call-component-v2")
    assert code_v2 == 0
    assert run_v2["result"]["output"]["tool_results"][0]["output"]["word_count"] == 4
    trace_v2 = _cold_inspect(workspace, run_v2["run_id"])
    tool_v2 = next(event for event in trace_v2["events"] if event["event_type"] == "tool.result")
    assert tool_v2["capability_version"] == "2.0.0"
    assert tool_v2["binding_digest"] != tool_v1["binding_digest"]

    _, deactivated = _component_command(
        capsys, workspace, "deactivate", "--component-id", "local_text_stats"
    )
    assert deactivated["transition"] == "deactivated"
    code_stopped, stopped = _cli(
        monkeypatch,
        capsys,
        inactive_provider,
        workspace,
        "Use the selected component.",
        source,
        ("--wiki-root", str(wiki), "--capability", "local_text_stats@2.0.0"),
    )
    assert code_stopped == 1
    assert stopped["result"]["error"]["code"] == "capability_not_found"

    _, restored = _component_command(
        capsys, workspace, "activate", "--component-id", "local_text_stats", "--version", "1.0.0"
    )
    assert restored["transition"] == "restored"
    code_restored, run_restored, _ = ask_version("1.0.0", "call-component-restored")
    assert code_restored == 0
    assert run_restored["result"]["output"]["tool_results"][0]["output"]["word_count"] == 3

    manifest = json.loads((workspace / ".catalyst" / "capabilities.json").read_text(encoding="utf-8"))
    assert manifest["components"]["local_text_stats"]["active_version"] == "1.0.0"
    lifecycle_events = [
        event
        for output in (active_v1, replaced, deactivated, restored)
        for event in _cold_inspect(workspace, output["run_id"])["events"]
        if event["event_type"] == "component.lifecycle.changed"
    ]
    assert [event["transition"] for event in lifecycle_events] == [
        "activated",
        "replaced",
        "deactivated",
        "restored",
    ]
    assert lifecycle_events[1]["previous_version"] == "1.0.0"
    assert lifecycle_events[1]["component_version"] == "2.0.0"
    assert lifecycle_events[2]["component_version"] == "2.0.0"
    assert lifecycle_events[2]["source_sha256"] == admitted_v2["source_sha256"]
    assert lifecycle_events[2]["manifest_sha256"] == discovered_v2["manifest_sha256"]
    assert lifecycle_events[2]["package_sha256"] == admitted_v2["package_sha256"]
    for event, version, admitted, discovered in (
        (lifecycle_events[0], "1.0.0", admitted_v1, discovered_v1),
        (lifecycle_events[1], "2.0.0", admitted_v2, discovered_v2),
        (lifecycle_events[2], "2.0.0", admitted_v2, discovered_v2),
        (lifecycle_events[3], "1.0.0", admitted_v1, discovered_v1),
    ):
        assert event["component_version"] == version
        assert event["source_sha256"] == admitted["source_sha256"]
        assert event["manifest_sha256"] == discovered["manifest_sha256"]
        assert event["package_sha256"] == admitted["package_sha256"]


def test_external_tool_visibility_does_not_authorize_a_different_selected_file(
    tmp_path: Path, monkeypatch, capsys
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "sources"
    wiki.mkdir()
    selected = wiki / "selected.txt"
    other = wiki / "other.txt"
    selected.write_text("Selected file.\n", encoding="utf-8")
    other.write_text("A different file the user did not select.\n", encoding="utf-8")
    package = _write_external_text_stats_package(
        tmp_path / "candidate", "1.0.0", unicode_words=False
    )
    _, discovery = _component_command(capsys, workspace, "discover", "--source", str(package))
    _, admission = _component_command(
        capsys,
        workspace,
        "admit",
        "--source",
        str(package),
        "--expected-sha256",
        discovery["package_sha256"],
    )
    assert admission["status"] == "success"
    _, activation = _component_command(
        capsys,
        workspace,
        "activate",
        "--component-id",
        "local_text_stats",
        "--version",
        "1.0.0",
    )
    assert activation["status"] == "success"

    provider = ScriptedProvider(
        lambda request, index: _tool_call(
            request,
            "local_text_stats",
            "1.0.0",
            {"path": str(other.resolve())},
            "call-unselected-file",
        )
    )
    code, response = _cli(
        monkeypatch,
        capsys,
        provider,
        workspace,
        "Count the words in the selected file.",
        selected,
        ("--wiki-root", str(wiki), "--capability", "local_text_stats@1.0.0"),
    )
    assert code == 1
    assert provider.request_count == 1
    assert response["result"]["error"]["code"] == "permission_denied"
    inspected = _cold_inspect(workspace, response["run_id"])
    decision = next(event for event in inspected["events"] if event["event_type"] == "authorization.decided")
    result = next(event for event in inspected["events"] if event["event_type"] == "tool.result")
    assert decision["decision"] == "deny"
    assert result["status"] == "denied"
    assert "assistant.final_answer" not in [event["event_type"] for event in inspected["events"]]


def test_component_admission_pins_source_and_does_not_load_before_activation(
    tmp_path: Path, capsys
):
    workspace = tmp_path / "workspace"
    package = _write_external_text_stats_package(
        tmp_path / "candidate", "1.0.0", unicode_words=False
    )
    import_marker = tmp_path / "entrypoint-imported.txt"
    source_path = package / "tool.py"
    source_path.write_text(
        source_path.read_text(encoding="utf-8")
        + f"\nfrom pathlib import Path\nPath({str(import_marker)!r}).write_text('loaded', encoding='utf-8')\n",
        encoding="utf-8",
    )
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _, discovery = _component_command(capsys, workspace, "discover", "--source", str(package))
    assert not import_marker.exists()
    _, admitted = _component_command(
        capsys,
        workspace,
        "admit",
        "--source",
        str(package),
        "--expected-sha256",
        discovery["package_sha256"],
    )
    assert admitted["status"] == "success"
    assert not import_marker.exists()
    source_path.write_text(source_path.read_text(encoding="utf-8") + "\n# changed after admission\n", encoding="utf-8")
    code, rejected = _component_command(
        capsys,
        workspace,
        "admit",
        "--source",
        str(package),
        "--expected-sha256",
        discovery["package_sha256"],
    )
    assert code == 1
    assert rejected["status"] == "failure"
    state = json.loads((workspace / ".catalyst" / "capabilities.json").read_text(encoding="utf-8"))
    assert state["components"]["local_text_stats"]["active_version"] is None
    assert "1.0.0" in state["components"]["local_text_stats"]["versions"]


def test_tampered_admitted_source_cannot_activate_or_be_called(
    tmp_path: Path, monkeypatch, capsys
):
    workspace = tmp_path / "workspace"
    package = _write_external_text_stats_package(
        tmp_path / "candidate", "1.0.0", unicode_words=False
    )
    _, discovery = _component_command(capsys, workspace, "discover", "--source", str(package))
    _, admission = _component_command(
        capsys,
        workspace,
        "admit",
        "--source",
        str(package),
        "--expected-sha256",
        discovery["package_sha256"],
    )
    assert admission["status"] == "success"

    installed = workspace / ".catalyst" / "components" / "local_text_stats" / "1.0.0"
    marker = tmp_path / "tampered-component-imported.txt"
    source_path = installed / "tool.py"
    source_path.write_text(
        source_path.read_text(encoding="utf-8")
        + f"\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('loaded', encoding='utf-8')\n",
        encoding="utf-8",
    )

    code, activation = _component_command(
        capsys,
        workspace,
        "activate",
        "--component-id",
        "local_text_stats",
        "--version",
        "1.0.0",
    )
    assert code == 1
    assert activation["status"] == "failure"
    assert activation["error"]["code"] == "component_operation_failed"
    assert not marker.exists()
    state = json.loads((workspace / ".catalyst" / "capabilities.json").read_text(encoding="utf-8"))
    assert state["components"]["local_text_stats"]["active_version"] is None
    failed_trace = _cold_inspect(workspace, activation["run_id"])
    failure = next(
        event for event in failed_trace["events"]
        if event["event_type"] == "component.lifecycle.failed"
    )
    assert failure["error_type"] == "ComponentError"

    provider = ScriptedProvider(lambda *_args: pytest.fail("tampered source must never reach the Provider"))
    code, run = _cli(
        monkeypatch,
        capsys,
        provider,
        workspace,
        "Count words in this file.",
        tmp_path / "does-not-exist.txt",
        ("--capability", "local_text_stats@1.0.0"),
    )
    assert code == 1
    assert provider.request_count == 0
    assert run["result"]["error"]["code"] == "capability_not_found"


def test_deactivation_withdraws_new_bindings_and_drains_an_existing_run_before_cleanup(
    tmp_path: Path, capsys
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    source = wiki / "leased.txt"
    raw = "Lease remains valid until this read finishes.\n".encode("utf-8")
    source.write_bytes(raw)
    package = _write_external_text_stats_package(
        tmp_path / "candidate", "1.0.0", unicode_words=False
    )
    _, discovery = _component_command(capsys, workspace, "discover", "--source", str(package))
    _, admission = _component_command(
        capsys,
        workspace,
        "admit",
        "--source",
        str(package),
        "--expected-sha256",
        discovery["package_sha256"],
    )
    assert admission["status"] == "success"
    _, activation = _component_command(
        capsys,
        workspace,
        "activate",
        "--component-id",
        "local_text_stats",
        "--version",
        "1.0.0",
    )
    assert activation["status"] == "success"

    app = CatalystWorkbench(workspace=workspace, wiki_roots=[wiki])
    registration = app._catalog.get("local_text_stats", "1.0.0")
    assert registration is not None
    implementation = registration.implementation
    module_name = f"_catalyst_component_{registration.metadata['source_sha256']}"
    assert module_name in sys.modules
    assert implementation.closed is False
    leases = app._catalog.runtime_bindings(
        lambda _capability_id: None,
        allowed_source_roots=[wiki],
    )
    key = CapabilityCatalog.internal_key("local_text_stats", "1.0.0")
    binding = leases[key]

    deactivation = app.components.deactivate("local_text_stats")
    assert deactivation["cleanup_status"] == "deferred"
    assert app._catalog.is_active("local_text_stats", "1.0.0") is False
    assert key not in app._catalog.runtime_bindings(lambda _capability_id: None)

    result = binding.invoke({"path": str(source)}, SimpleNamespace())
    assert isinstance(result, Success)
    assert result.data["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert implementation.closed is False

    binding.release()
    assert implementation.closed is True
    assert module_name not in sys.modules


def test_deactivation_during_model_wait_drains_the_captured_binding_and_records_transition(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    source = wiki / "in-flight.txt"
    raw = "The captured component version remains usable for this run.\n".encode("utf-8")
    source.write_bytes(raw)
    package = _write_external_text_stats_package(
        tmp_path / "candidate", "1.0.0", unicode_words=False
    )
    app = CatalystWorkbench(workspace=workspace, wiki_roots=[wiki])
    candidate = app.components.discover(package)
    app.components.admit(package, candidate["package_sha256"])
    app.components.activate("local_text_stats", "1.0.0")
    registration = app._catalog.get("local_text_stats", "1.0.0")
    assert registration is not None
    implementation = registration.implementation
    module_name = f"_catalyst_component_{registration.metadata['source_sha256']}"

    entered = threading.Event()
    release = threading.Event()

    class BlockingProvider:
        provider_id = "scripted-r5-inflight"
        model = "deterministic-r5"
        mode = "offline"

        def __init__(self):
            self.request_count = 0

        def request(self, request):
            self.request_count += 1
            if self.request_count == 1:
                entered.set()
                assert release.wait(5)
                return _tool_call(
                    request,
                    "local_text_stats",
                    "1.0.0",
                    {"path": str(source.resolve())},
                    "call-during-deactivation",
                )
            result = _last_tool_result(request)
            assert result["source_sha256"] == hashlib.sha256(raw).hexdigest()
            return ModelResponse(content="The captured component completed the read.", finish_reason="stop")

    provider = BlockingProvider()
    session = app.new_session(domain={"id": "local"}, enterprise={"id": "local"})
    gateway = CatalystGateway(workspace)
    recorder = RunRecorder(
        gateway.traces,
        run_id="run_r5_inflight",
        request_id="req_r5_inflight",
        invocation_id="inv_r5_inflight",
        trace_id="5" * 32,
    )
    output = []

    def execute():
        output.append(
            gateway.ask_natural_language(
                message="Count words in the selected file.",
                selected_file=source,
                recorder=recorder,
                ask=lambda invocation_id, trace_id, active_recorder: session.ask(
                    "Count words in the selected file.",
                    provider=provider,
                    selected_file=source,
                    visible_capabilities=(("local_text_stats", "1.0.0"),),
                    invocation_id=invocation_id,
                    trace_id=trace_id,
                    recorder=active_recorder,
                ),
            )
        )

    thread = threading.Thread(target=execute)
    thread.start()
    assert entered.wait(5)
    assert module_name in sys.modules
    transition = gateway.component_lifecycle(
        operation="deactivate",
        action=lambda: app.components.deactivate("local_text_stats"),
    )
    assert transition["status"] == "success"
    assert transition["cleanup_status"] == "deferred"
    release.set()
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert output[0]["status"] == "success"
    assert provider.request_count == 2
    assert implementation.closed is True
    assert module_name not in sys.modules

    run_trace = gateway.inspect_run("run_r5_inflight")
    assert run_trace is not None and run_trace["status"] == "success"
    result_event = next(event for event in run_trace["events"] if event["event_type"] == "tool.result")
    assert result_event["component_version"] == "1.0.0"
    assert result_event["status"] == "success"
    transition_trace = gateway.inspect_run(transition["run_id"])
    assert transition_trace is not None
    lifecycle = next(
        event for event in transition_trace["events"]
        if event["event_type"] == "component.lifecycle.changed"
    )
    assert lifecycle["in_flight_policy"] == "existing_runs_drain"
    assert lifecycle["cleanup_status"] == "deferred"
