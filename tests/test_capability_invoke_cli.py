"""R2: invoke a discovered exact binding and inspect its correlated outcome."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


PRODUCT_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(
    workspace: Path,
    wiki: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "catalyst_platform",
        *arguments,
        "--workspace",
        str(workspace),
    ]
    if arguments[0] != "inspect":
        command.extend(["--wiki-root", str(wiki)])
    return subprocess.run(
        command,
        cwd=PRODUCT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _payload(process: subprocess.CompletedProcess[str]) -> dict:
    assert process.stdout, process.stderr
    return json.loads(process.stdout)


def _invoke(
    workspace: Path,
    wiki: Path,
    *,
    capability_id: str = "read_file_title",
    version: str = "1.0.0",
    path: str = "inputs/r2-source.md",
) -> subprocess.CompletedProcess[str]:
    return _run_cli(
        workspace,
        wiki,
        "invoke",
        "--capability-id",
        capability_id,
        "--version",
        version,
        "--input-json",
        json.dumps({"path": path}, ensure_ascii=False),
        "--domain-id",
        "local",
        "--enterprise-id",
        "test-enterprise",
    )


def test_discovered_file_title_binding_runs_through_generic_invoke_and_cold_trace(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    source = workspace / "inputs" / "r2-source.md"
    wiki.mkdir()
    source.parent.mkdir(parents=True)
    source_bytes = "# R2 Real Source\n\nThis is a new input.\n".encode("utf-8")
    source.write_bytes(source_bytes)

    discovery_process = _run_cli(workspace, wiki, "discover")

    assert discovery_process.returncode == 0, discovery_process.stderr
    discovery = _payload(discovery_process)
    file_title_route = next(
        route
        for route in discovery["invocation_routes"]
        if route["capability_id"] == "read_file_title"
    )
    assert file_title_route == {
        "capability_id": "read_file_title",
        "capability_version": "1.0.0",
        "command": "invoke",
    }

    invocation_process = _invoke(workspace, wiki)

    assert invocation_process.returncode == 0, invocation_process.stderr
    invocation = _payload(invocation_process)
    result_output = invocation["result"]["output"]
    assert invocation["status"] == "success"
    assert invocation["run_id"].startswith("run_")
    assert result_output["title"] == "R2 Real Source"
    assert result_output["source"]["path"] == str(source.resolve())
    assert result_output["source"]["sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert Path(invocation["trace_path"]).name == "runs.jsonl"

    # A new CLI process reads the JSONL observation and the Workbench execution trace.
    inspect_process = _run_cli(
        workspace,
        wiki,
        "inspect",
        "--run-id",
        invocation["run_id"],
    )
    assert inspect_process.returncode == 0, inspect_process.stderr
    inspected = _payload(inspect_process)
    assert inspected["terminal_status"] == "success"
    event_types = [event["event_type"] for event in inspected["events"]]
    assert event_types[0] == "request.started"
    assert event_types[-1] == "request.terminal"
    assert "capability.invoke.requested" in event_types
    assert "binding.resolved" in event_types
    assert "authorization.decided" in event_types
    assert "tool.execution.started" in event_types
    assert "tool.result" in event_types
    assert "source.read.completed" in event_types
    invoked_event = next(
        event for event in inspected["events"] if event["event_type"] == "binding.resolved"
    )
    assert invoked_event["capability_id"] == "read_file_title"
    assert invoked_event["capability_version"] == "1.0.0"
    assert invoked_event["side_effect"] == "none"
    capability_call = next(
        event for event in inspected["events"] if event["event_type"] == "tool.execution.started"
    )
    capability_result = next(
        event for event in inspected["events"] if event["event_type"] == "tool.result"
    )
    assert capability_call["execution_id"]
    assert capability_call["execution_id"] == capability_result["execution_id"]
    assert capability_result["status"] == "success"
    emitted = next(
        event for event in inspected["events"] if event["event_type"] == "result.emitted"
    )
    assert emitted["source_sha256"] == hashlib.sha256(source_bytes).hexdigest()
    assert emitted["source_line"] == 1
    terminal = inspected["events"][-1]
    assert terminal["terminal_status"] == "success"
    assert terminal["model_calls"] == 0
    assert terminal["external_calls"] == 0
    assert terminal["provider_requests"] > 0

    native_trace = json.loads(Path(invocation["execution_trace_path"]).read_text(encoding="utf-8"))
    assert native_trace["trace_id"] == inspected["events"][0]["trace_id"]
    assert any(
        item["execution_id"] == capability_call["execution_id"]
        for item in native_trace["capability_calls"]
    )


@pytest.mark.parametrize(
    ("capability_id", "version"),
    [("unknown_capability", "1.0.0"), ("read_file_title", "9.9.9")],
)
def test_unbound_exact_binding_fails_and_is_visible_after_cold_inspect(
    tmp_path: Path,
    capability_id: str,
    version: str,
):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    wiki.mkdir()

    invoke_process = _invoke(
        workspace,
        wiki,
        capability_id=capability_id,
        version=version,
    )

    assert invoke_process.returncode == 1, invoke_process.stderr
    invocation = _payload(invoke_process)
    assert invocation["status"] == "failure"
    assert invocation["result"]["error"]["code"] == "capability_not_found"
    assert f"{capability_id}@{version}" in invocation["result"]["error"]["message"]
    inspected = _payload(
        _run_cli(workspace, wiki, "inspect", "--run-id", invocation["run_id"])
    )
    assert inspected["terminal_status"] == "failure"
    assert not any(event["event_type"] == "binding.resolved" for event in inspected["events"])
    emitted = next(event for event in inspected["events"] if event["event_type"] == "result.emitted")
    assert emitted["error_code"] == "capability_not_found"


def test_registered_binding_failure_records_source_error_and_terminal_trace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    wiki = tmp_path / "wiki"
    wiki.mkdir()

    invoke_process = _invoke(workspace, wiki, path="inputs/absent.md")

    assert invoke_process.returncode == 1, invoke_process.stderr
    invocation = _payload(invoke_process)
    assert invocation["status"] == "failure"
    assert invocation["result"]["error"]["code"] == "capability_failed"
    assert "file_not_found" in invocation["result"]["error"]["message"]
    inspected = _payload(
        _run_cli(workspace, wiki, "inspect", "--run-id", invocation["run_id"])
    )
    assert inspected["terminal_status"] == "failure"
    tool_result = next(event for event in inspected["events"] if event["event_type"] == "tool.result")
    assert tool_result["status"] == "failure"
    assert any(event["event_type"] == "source.read.failed" and event["error_code"] == "file_not_found" for event in inspected["events"])
