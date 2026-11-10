"""R0: inspect a real local text file through the Catalyst product CLI."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


PRODUCT_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(workspace: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "catalyst_platform",
            *arguments,
            "--workspace",
            str(workspace),
        ],
        cwd=PRODUCT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _payload(process: subprocess.CompletedProcess[str]) -> dict:
    assert process.stdout, process.stderr
    return json.loads(process.stdout)


def test_two_real_files_return_their_own_title_and_verifiable_source(tmp_path: Path):
    workspace = tmp_path / "workspace"
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first_bytes = "# 第一份真实资料\n\n第一份正文。\n".encode("utf-8")
    second_bytes = "开头说明\n\n# 第二份真实资料\n\n第二份正文。\n".encode("utf-8")
    first.write_bytes(first_bytes)
    second.write_bytes(second_bytes)

    first_process = _run_cli(workspace, "inspect-file", "--file", str(first))
    second_process = _run_cli(workspace, "inspect-file", "--file", str(second))

    assert first_process.returncode == 0, first_process.stderr
    assert second_process.returncode == 0, second_process.stderr
    first_run = _payload(first_process)
    second_run = _payload(second_process)

    assert first_run["status"] == second_run["status"] == "success"
    assert first_run["result"]["output"]["title"] == "第一份真实资料"
    assert second_run["result"]["output"]["title"] == "第二份真实资料"
    assert first_run["result"]["output"]["source"]["path"] == str(first.resolve())
    assert second_run["result"]["output"]["source"]["path"] == str(second.resolve())
    assert first_run["result"]["output"]["source"]["sha256"] == hashlib.sha256(first_bytes).hexdigest()
    assert second_run["result"]["output"]["source"]["sha256"] == hashlib.sha256(second_bytes).hexdigest()
    assert first_run["result"]["output"]["source"]["line"] == 1
    assert second_run["result"]["output"]["source"]["line"] == 3
    assert first_run["run_id"] != second_run["run_id"]


def test_run_trace_can_be_inspected_by_a_fresh_product_process(tmp_path: Path):
    workspace = tmp_path / "workspace"
    source = tmp_path / "readback.md"
    source.write_text("# Readback source\n\nBody text.\n", encoding="utf-8")

    run_process = _run_cli(workspace, "inspect-file", "--file", str(source))
    assert run_process.returncode == 0, run_process.stderr
    run = _payload(run_process)

    inspect_process = _run_cli(workspace, "inspect", "--run-id", run["run_id"])

    assert inspect_process.returncode == 0, inspect_process.stderr
    inspected = _payload(inspect_process)
    event_types = [event["event_type"] for event in inspected["events"]]
    assert inspected["run_id"] == run["run_id"]
    assert inspected["terminal_status"] == "success"
    assert "request.started" in event_types
    assert "span.started" in event_types
    assert "tool.execution.started" in event_types
    assert "source.read.started" in event_types
    assert "source.read.completed" in event_types
    assert "tool.result" in event_types
    assert "result.emitted" in event_types
    assert event_types[-1] == "request.terminal"
    tool_start = next(event for event in inspected["events"] if event["event_type"] == "source.read.started")
    assert tool_start["tool_id"] == "read_file_title"
    assert tool_start["tool_version"] == "1.0.0"
    assert Path(run["trace_path"]).is_file()


def test_missing_file_is_a_real_failure_with_a_persisted_terminal_trace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    missing = tmp_path / "absent.md"

    process = _run_cli(workspace, "inspect-file", "--file", str(missing))

    assert process.returncode == 1
    run = _payload(process)
    assert run["status"] == "failure"
    assert run["result"]["status"] == "failure"
    assert run["error"]["code"] == "file_not_found"
    assert str(missing.resolve()) in run["error"]["message"]
    assert Path(run["trace_path"]).is_file()

    inspect_process = _run_cli(workspace, "inspect", "--run-id", run["run_id"])
    assert inspect_process.returncode == 0, inspect_process.stderr
    inspected = _payload(inspect_process)
    assert inspected["terminal_status"] == "failure"
    assert any(
        event["event_type"] == "source.read.failed"
        and event.get("error_code") == "file_not_found"
        for event in inspected["events"]
    )


def test_markdown_without_an_explicit_h1_does_not_guess_a_title(tmp_path: Path):
    workspace = tmp_path / "workspace"
    source = tmp_path / "untitled.md"
    source.write_text("Paragraph only.\n", encoding="utf-8")

    process = _run_cli(workspace, "inspect-file", "--file", str(source))

    assert process.returncode == 1
    run = _payload(process)
    assert run["status"] == "failure"
    assert run["error"]["code"] == "title_not_found"
    assert run["result"]["output"] is None


@pytest.mark.parametrize(
    ("heading", "expected_title"),
    [("# C#", "C#"), ("# Release#", "Release#"), ("# C ##", "C")],
)
def test_markdown_preserves_literal_hashes_and_only_strips_valid_closing_hashes(
    tmp_path: Path, heading: str, expected_title: str
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "hashes.md"
    source.write_text(f"{heading}\n", encoding="utf-8")

    process = _run_cli(workspace, "inspect-file", "--file", str(source))

    assert process.returncode == 0, process.stderr
    run = _payload(process)
    assert run["result"]["output"]["title"] == expected_title


@pytest.mark.parametrize(
    ("content", "expected_status", "expected_title", "expected_line"),
    [
        ("```text\n# Example\n```\n", "failure", None, None),
        ("```text\n# Example\n```\n# Actual title\n", "success", "Actual title", 4),
        ("~~~markdown\n# Example\n~~~\n# Actual title\n", "success", "Actual title", 4),
    ],
)
def test_markdown_does_not_extract_headings_from_fenced_code(
    tmp_path: Path,
    content: str,
    expected_status: str,
    expected_title: str | None,
    expected_line: int | None,
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "fence.md"
    source.write_text(content, encoding="utf-8")

    process = _run_cli(workspace, "inspect-file", "--file", str(source))

    assert process.returncode == (0 if expected_status == "success" else 1)
    run = _payload(process)
    assert run["status"] == expected_status
    if expected_status == "success":
        assert run["result"]["output"]["title"] == expected_title
        assert run["result"]["output"]["source"]["line"] == expected_line
    else:
        assert run["error"]["code"] == "title_not_found"


@pytest.mark.parametrize(
    ("content", "expected_status", "expected_title", "expected_line"),
    [
        ("# ###\n", "failure", None, None),
        ("# ###   \n", "failure", None, None),
        ("# ###\n# Actual title\n", "success", "Actual title", 2),
    ],
)
def test_markdown_empty_atx_headings_are_not_returned_as_titles(
    tmp_path: Path,
    content: str,
    expected_status: str,
    expected_title: str | None,
    expected_line: int | None,
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "empty-heading.md"
    source.write_text(content, encoding="utf-8")

    process = _run_cli(workspace, "inspect-file", "--file", str(source))

    assert process.returncode == (0 if expected_status == "success" else 1)
    run = _payload(process)
    assert run["status"] == expected_status
    if expected_status == "success":
        assert run["result"]["output"]["title"] == expected_title
        assert run["result"]["output"]["source"]["line"] == expected_line
    else:
        assert run["error"]["code"] == "title_not_found"


@pytest.mark.parametrize(
    "record",
    [
        "null",
        "[]",
        '{"run_id":"run-corrupt","event_type":"request.terminal","terminal_status":"success"}',
    ],
)
def test_trace_inspection_returns_structured_failure_for_invalid_record_shape(
    tmp_path: Path, record: str
):
    workspace = tmp_path / "workspace"
    trace_path = workspace / ".catalyst" / "traces" / "runs.jsonl"
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text(record + "\n", encoding="utf-8")

    process = _run_cli(workspace, "inspect", "--run-id", "run-corrupt")

    assert process.returncode == 2
    assert process.stderr == ""
    result = _payload(process)
    assert result["status"] == "failure"
    assert result["error"]["type"] == "TraceStoreError"


def test_plain_text_uses_first_nonempty_line_as_a_declared_deterministic_rule(tmp_path: Path):
    workspace = tmp_path / "workspace"
    source = tmp_path / "notes.txt"
    source.write_text("\nPlain text title\nBody text\n", encoding="utf-8")

    process = _run_cli(workspace, "inspect-file", "--file", str(source))

    assert process.returncode == 0, process.stderr
    run = _payload(process)
    output = run["result"]["output"]
    assert output["title"] == "Plain text title"
    assert output["source"]["line"] == 2
    assert output["source"]["extraction_method"] == "text_first_nonempty_line"


def test_request_start_is_observed_before_runtime_execution(tmp_path: Path, monkeypatch):
    from catalyst_platform import gateway as gateway_module

    workspace = tmp_path / "workspace"
    source = tmp_path / "ordered.md"
    source.write_text("# Ordered trace\n", encoding="utf-8")
    timeline: list[str] = []
    original_execute = gateway_module.RuntimeAdapter.execute
    original_append = gateway_module.JsonlTraceStore.append_event

    def observed_append(store, run_id, sequence, event):
        if event.get("event_type") == "request.started":
            timeline.append("request.started.persisted")
        return original_append(store, run_id, sequence, event)

    def observed_execute(adapter, invocation):
        timeline.append("runtime.execute")
        return original_execute(adapter, invocation)

    monkeypatch.setattr(gateway_module.JsonlTraceStore, "append_event", observed_append)
    monkeypatch.setattr(gateway_module.RuntimeAdapter, "execute", observed_execute)

    gateway_module.CatalystGateway(workspace).inspect_file(source)

    assert timeline.index("request.started.persisted") < timeline.index("runtime.execute")
