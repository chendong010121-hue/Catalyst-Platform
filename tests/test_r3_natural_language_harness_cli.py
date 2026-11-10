"""R3: natural-language asks use the current read-only Workbench binding."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent_runtime.contracts import ModelResponse, ModelToolCall

import catalyst_platform.__main__ as cli
from catalyst_platform.workbench import CapabilityCatalog


PRODUCT_ROOT = Path(__file__).resolve().parents[1]


def test_r3_ask_is_available_from_the_shared_cli():
    subparsers = next(
        action
        for action in cli._build_parser()._actions
        if action.dest == "command"
    )
    assert "ask" in subparsers.choices


def test_cli_exposes_a_configurable_model_provider_factory():
    assert callable(getattr(cli, "configured_model_provider_from_environment", None))


def test_model_provider_factory_configures_supported_providers_without_calling_them(monkeypatch):
    monkeypatch.setenv("CATALYST_LLM_API_KEY", "test-secret-never-emitted")
    monkeypatch.setenv("CATALYST_LLM_TIMEOUT_SECONDS", "2.5")

    monkeypatch.setenv("CATALYST_LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("CATALYST_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("CATALYST_LLM_MODEL", "deepseek-test-model")
    deepseek = cli.configured_model_provider_from_environment()
    assert deepseek.provider_id == "deepseek"
    assert deepseek.model == "deepseek-test-model"
    assert deepseek.mode == "live"
    assert deepseek.request_count == 0
    assert deepseek.external_calls == 0

    monkeypatch.setenv("CATALYST_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("CATALYST_LLM_BASE_URL", "https://models.example.test/v1")
    monkeypatch.setenv("CATALYST_LLM_MODEL", "compatible-test-model")
    compatible = cli.configured_model_provider_from_environment()
    assert compatible.provider_id == "openai-compatible"
    assert compatible.model == "compatible-test-model"
    assert compatible.mode == "live"
    assert compatible.request_count == 0
    assert compatible.external_calls == 0


def test_model_provider_factory_fails_closed_without_a_key_or_required_base_url(monkeypatch):
    module = importlib.import_module("catalyst_platform.llm_provider")
    monkeypatch.setenv("CATALYST_LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("CATALYST_LLM_API_KEY", raising=False)
    with pytest.raises(module.ModelProviderConfigurationError) as missing_key:
        cli.configured_model_provider_from_environment()
    assert "CATALYST_LLM_API_KEY" in str(missing_key.value)
    assert "test-secret" not in str(missing_key.value)

    monkeypatch.setenv("CATALYST_LLM_API_KEY", "test-secret-never-emitted")
    monkeypatch.setenv("CATALYST_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("CATALYST_LLM_MODEL", "compatible-test-model")
    monkeypatch.delenv("CATALYST_LLM_BASE_URL", raising=False)
    with pytest.raises(module.ModelProviderConfigurationError) as missing_url:
        cli.configured_model_provider_from_environment()
    assert "CATALYST_LLM_BASE_URL" in str(missing_url.value)
    assert "test-secret" not in str(missing_url.value)


def test_cli_persists_a_failure_when_live_provider_configuration_is_missing(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.delenv("CATALYST_LLM_API_KEY", raising=False)
    code = cli.main(
        [
            "ask",
            "--workspace",
            str(tmp_path / "workspace"),
            "--message",
            "Answer a simple question.",
        ]
    )
    response = _payload(capsys.readouterr().out)

    assert code == 1
    assert response["status"] == "failure"
    assert response["result"]["error"]["code"] == "llm_provider_not_configured"
    assert response["result"]["output"] is None
    inspected = _cold_inspect(tmp_path / "workspace", response["run_id"])
    assert inspected["terminal_status"] == "failure"
    assert any(event["event_type"] == "llm.request.failed" for event in inspected["events"])
    terminal = inspected["events"][-1]
    assert terminal["model_calls"] == 0
    assert terminal["provider_requests"] == 1
    assert terminal["external_calls"] == 0


def test_invalid_tool_parameters_are_rejected_before_file_access(
    tmp_path: Path, monkeypatch, capsys
):
    source = tmp_path / "selected.md"
    source.write_text("# Schema Guard\n", encoding="utf-8")

    def invalid_call(request, _index):
        tool = request.tools[0]
        return ModelResponse(
            tool_calls=(
                ModelToolCall(
                    id="call-invalid-parameters",
                    name=tool.name,
                    arguments=json.dumps({"path": str(source.resolve()), "unexpected": True}),
                ),
            ),
            finish_reason="tool_calls",
        )

    provider = ScriptedProvider(invalid_call)
    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        tmp_path / "workspace",
        "Read the title of my selected file.",
        source,
    )

    assert code == 1
    assert response["status"] == "failure"
    assert response["result"]["output"] is None
    inspected = _cold_inspect(tmp_path / "workspace", response["run_id"])
    event_types = [event["event_type"] for event in inspected["events"]]
    assert "source.read.started" not in event_types
    assert any(
        event["event_type"] == "tool.result"
        and event["status"] == "failure"
        for event in inspected["events"]
    )
    assert "assistant.final_answer" not in event_types


class ScriptedProvider:
    provider_id = "scripted-r3-test-provider"
    model = "scripted-test-model"
    mode = "offline"
    external_calls = 0

    def __init__(self, handler):
        self.handler = handler
        self.request_count = 0
        self.requests = []

    def request(self, request):
        self.request_count += 1
        self.requests.append(request)
        return self.handler(request, self.request_count)


def _payload(text: str) -> dict:
    return json.loads(text)


def _ask(
    monkeypatch,
    capsys,
    provider: ScriptedProvider,
    workspace: Path,
    message: str,
    file_path: Path | None = None,
    extra_args: tuple[str, ...] = (),
) -> tuple[int, dict]:
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


def _read_file_call(request, call_id: str, path: Path) -> ModelResponse:
    assert len(request.tools) == 1
    tool = request.tools[0]
    return ModelResponse(
        tool_calls=(
            ModelToolCall(
                id=call_id,
                name=tool.name,
                arguments=json.dumps({"path": str(path.resolve())}),
            ),
        ),
        finish_reason="tool_calls",
    )


def _success_result_from_tool_message(request) -> dict:
    message = next(message for message in reversed(request.messages) if message.role == "tool")
    return json.loads(message.content)


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


def test_natural_language_read_uses_exact_readonly_binding_and_cold_trace(
    tmp_path: Path, monkeypatch, capsys
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "inputs" / "r3-source.md"
    source.parent.mkdir()
    source_bytes = "# R3 Bound Source\n\nA real source for the harness.\n".encode()
    source.write_bytes(source_bytes)

    def reply(request, index):
        if index == 1:
            assert [tool.name for tool in request.tools] == [request.tools[0].name]
            return _read_file_call(request, "call-r3-read", source)
        observed = _success_result_from_tool_message(request)
        assert observed["source"]["sha256"] == hashlib.sha256(source_bytes).hexdigest()
        return ModelResponse(
            content=f'The file title is "{observed["title"]}".',
            finish_reason="stop",
        )

    provider = ScriptedProvider(reply)
    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        workspace,
        "Please read the title of my selected file and tell me the source.",
        source,
    )

    assert code == 0
    assert response["status"] == "success"
    assert response["run_id"].startswith("run_")
    assert response["result"]["output"]["answer"] == 'The file title is "R3 Bound Source".'
    assert response["result"]["output"]["tool_results"][0]["output"]["title"] == "R3 Bound Source"
    assert len(provider.requests) == 2
    expected_tool_name = CapabilityCatalog.internal_key("read_file_title", "1.0.0")
    assert [tool.name for tool in provider.requests[0].tools] == [expected_tool_name]
    assert provider.requests[0].tools[0].parameters["properties"] == {
        "path": {"type": "string"}
    }
    assert provider.requests[1].messages[-1].role == "tool"

    inspected = _cold_inspect(workspace, response["run_id"])
    assert inspected["terminal_status"] == "success"
    events = inspected["events"]
    event_types = [event["event_type"] for event in events]
    assert "llm.response.received" in event_types
    assert "agent.decision" in event_types
    assert "tool.call.requested" in event_types
    assert "tool.execution.started" in event_types
    assert "source.read.started" in event_types
    assert "source.read.completed" in event_types
    assert "tool.result" in event_types
    assert "assistant.final_answer" in event_types
    call_event = next(event for event in events if event["event_type"] == "tool.call.requested")
    result_event = next(event for event in events if event["event_type"] == "tool.result")
    assert call_event["tool_call_id"] == "call-r3-read"
    assert call_event["capability_id"] == "read_file_title"
    assert call_event["capability_version"] == "1.0.0"
    assert call_event["side_effect"] == "none"
    tool_start = next(event for event in events if event["event_type"] == "tool.execution.started")
    assert tool_start["execution_id"]
    assert tool_start["tool_call_id"] == call_event["tool_call_id"]
    assert result_event["tool_call_id"] == call_event["tool_call_id"]
    assert result_event["execution_id"] == tool_start["execution_id"]
    assert result_event["result_sha256"]
    assert events[-1]["event_type"] == "request.terminal"
    assert events[-1]["model_calls"] == 2
    assert events[-1]["external_calls"] == 0
    assert events[0]["event_type"] == "request.started"
    assert events[-1]["event_type"] == "request.terminal"
    assert events.index(call_event) < events.index(result_event)
    assert all(event["request_id"] == events[0]["request_id"] for event in events)


def test_plain_question_can_finish_without_a_tool(tmp_path: Path, monkeypatch, capsys):
    provider = ScriptedProvider(
        lambda request, _index: ModelResponse(
            content="A direct answer from the configured model.", finish_reason="stop"
        )
    )
    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        tmp_path / "workspace",
        "What does R3 stand for?",
    )

    assert code == 0
    assert response["status"] == "success"
    assert response["result"]["output"]["answer"] == "A direct answer from the configured model."
    assert response["result"]["output"]["tool_results"] == []
    assert provider.request_count == 1
    assert provider.requests[0].tools == ()
    inspected = _cold_inspect(tmp_path / "workspace", response["run_id"])
    provider_start = next(
        event for event in inspected["events"] if event["event_type"] == "llm.request.started"
    )
    assert provider_start["exposed_tools"] == []
    assert provider_start["exposed_tool_count"] == 0


def test_missing_file_stops_without_a_fabricated_final_answer(tmp_path: Path, monkeypatch, capsys):
    missing = tmp_path / "missing.md"
    provider = ScriptedProvider(
        lambda request, _index: _read_file_call(request, "call-missing", missing)
    )
    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        tmp_path / "workspace",
        "Read the title of my selected file.",
        missing,
    )

    assert code == 1
    assert response["status"] == "failure"
    assert response["result"]["error"]["code"] == "capability_failed"
    assert "file_not_found" in response["result"]["error"]["message"]
    assert response["result"]["output"] is None
    assert provider.request_count == 1
    inspected = _cold_inspect(tmp_path / "workspace", response["run_id"])
    event_types = [event["event_type"] for event in inspected["events"]]
    assert "source.read.failed" in event_types
    assert any(
        event["event_type"] == "tool.result" and event["status"] == "failure"
        for event in inspected["events"]
    )
    assert "assistant.final_answer" not in event_types
    assert inspected["terminal_status"] == "failure"


def test_model_cannot_redirect_read_to_a_different_local_file(tmp_path: Path, monkeypatch, capsys):
    selected = tmp_path / "selected.md"
    other = tmp_path / "other.md"
    selected.write_text("# Selected\n", encoding="utf-8")
    other.write_text("# Not selected\n", encoding="utf-8")
    provider = ScriptedProvider(
        lambda request, _index: _read_file_call(request, "call-path-mismatch", other)
    )

    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        tmp_path / "workspace",
        "Read my selected file.",
        selected,
    )

    assert code == 1
    assert response["status"] == "failure"
    assert response["result"]["output"] is None
    assert provider.request_count == 1
    inspected = _cold_inspect(tmp_path / "workspace", response["run_id"])
    event_types = [event["event_type"] for event in inspected["events"]]
    assert "tool.execution.started" not in event_types
    assert any(
        event["event_type"] == "tool.result" and event["status"] == "denied"
        for event in inspected["events"]
    )
    assert "assistant.final_answer" not in event_types


def test_ask_respects_the_existing_enterprise_source_allowlist(tmp_path: Path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    selected = workspace / "unapproved.md"
    selected.parent.mkdir()
    selected.write_text("# Must not be read\n", encoding="utf-8")
    allowed_root = workspace / "approved"
    allowed_root.mkdir()
    allow_map = tmp_path / "enterprise-access.json"
    allow_map.write_text(
        json.dumps({"local": [str(allowed_root.resolve())]}), encoding="utf-8"
    )
    provider = ScriptedProvider(
        lambda request, _index: _read_file_call(request, "call-not-authorized", selected)
    )

    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        workspace,
        "Read the title of my selected file.",
        selected,
        ("--enterprise-access-map", str(allow_map)),
    )

    assert code == 1
    inspected = _cold_inspect(workspace, response["run_id"])
    event_types = [event["event_type"] for event in inspected["events"]]
    assert "tool.execution.started" not in event_types
    assert any(
        event["event_type"] == "tool.result"
        and event["status"] == "denied"
        for event in inspected["events"]
    )
    assert "assistant.final_answer" not in event_types


def test_one_read_only_tool_call_is_the_per_request_limit(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "once.md"
    source.write_text("# One call\n", encoding="utf-8")

    def reply(request, index):
        if index == 1:
            return _read_file_call(request, "call-first", source)
        return _read_file_call(request, "call-second", source)

    provider = ScriptedProvider(reply)
    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        tmp_path / "workspace",
        "Read the title of my selected file.",
        source,
    )

    assert code == 1
    assert response["status"] == "failure"
    assert provider.request_count == 2
    inspected = _cold_inspect(tmp_path / "workspace", response["run_id"])
    successful_calls = [
        event
        for event in inspected["events"]
        if event["event_type"] == "tool.result" and event["status"] == "success"
    ]
    denied_calls = [
        event
        for event in inspected["events"]
        if event["event_type"] == "tool.result" and event["status"] == "denied"
    ]
    assert len(successful_calls) == 1
    assert len(denied_calls) == 1
    assert "assistant.final_answer" not in [event["event_type"] for event in inspected["events"]]


def test_provider_error_is_traceable_without_echoing_error_text(
    tmp_path: Path, monkeypatch, capsys
):
    class BrokenProvider(ScriptedProvider):
        def request(self, request):
            self.request_count += 1
            raise RuntimeError("private-provider-detail-must-not-be-echoed")

    provider = BrokenProvider(lambda _request, _index: None)
    code, response = _ask(
        monkeypatch,
        capsys,
        provider,
        tmp_path / "workspace",
        "Answer this simple question.",
    )

    assert code == 1
    assert response["status"] == "failure"
    assert response["result"]["output"] is None
    assert "private-provider-detail-must-not-be-echoed" not in json.dumps(response)
    inspected = _cold_inspect(tmp_path / "workspace", response["run_id"])
    assert inspected["terminal_status"] == "failure"
    assert any(event["event_type"] == "llm.request.failed" for event in inspected["events"])
    terminal = inspected["events"][-1]
    assert terminal["model_calls"] == 0
    assert terminal["provider_requests"] == 1
