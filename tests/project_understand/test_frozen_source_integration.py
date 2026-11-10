"""Real fixed source bytes -> original Harness/P0/R4 -> original Evaluation.

The transport is a labeled deterministic control. No target code is imported,
no model is contacted, and absent transitive behavior remains unresolved.
"""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import socket
import uuid

import pytest

from catalyst_platform.model_qualification import DEFAULT_QUALIFICATION, load_qualification
from catalyst_platform.observability import RunRecorder
from catalyst_platform.project_understand import ProjectUnderstandingRequest, digest, run_project_analysis, source_manifest
from catalyst_platform.project_understand_evaluation import project_grader, run_project_evaluation
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from tests.test_workspace_model_settings import configuration, packet

FROZEN = Path(__file__).resolve().parents[3] / "sources"
SAMPLES = {
    "skill": ("penguin", ["plugins/agent-development/skills/agent-initialization/SKILL.md",
                            "plugins/agent-development/skills/agent-initialization/reference/hooks.md"]),
    "plugin": ("product", ["catalyst_platform/harness_plugins.py", "catalyst_platform/plugin_composition.py"]),
    "agent": ("openhands", ["examples/01_standalone_sdk/02_custom_tools.py",
                            "openhands-sdk/openhands/sdk/tool/__init__.py"]),
}


@pytest.fixture(autouse=True)
def offline_and_original_qualification_clock(monkeypatch):
    import catalyst_platform.workspace_settings as settings
    instant = load_qualification(DEFAULT_QUALIFICATION).verified_at + timedelta(seconds=1)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr(settings, "datetime", Clock)
    def deny(*args, **kwargs):
        raise AssertionError("FROZEN_SOURCE_EXTERNAL_NETWORK_DENIED")
    monkeypatch.setattr(socket.socket, "connect", deny)


def _tool_packet(request, action, arguments, count):
    name = next(t["function"]["name"] for t in request["tools"]
                if t["function"]["description"].startswith(action + ":"))
    value = packet()
    value["choices"][0].update(finish_reason="tool_calls", message={"role": "assistant", "content": None,
        "tool_calls": [{"id": "frozen-control-" + str(count), "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments)}}]})
    return 200, value


def _find_observed(value):
    if isinstance(value, dict):
        if "evidence" in value and "source_reads" in value:
            return value
        values = value.values()
    elif isinstance(value, list):
        values = value
    else:
        return None
    for child in values:
        found = _find_observed(child)
        if found:
            return found


def _transport(object_type, objective, selected_ids):
    calls = []
    def send(url, headers, body):
        request = json.loads(body)
        calls.append(request)
        if len(calls) == 1:
            assert not any(m["role"] == "tool" for m in request["messages"])
            return _tool_packet(request, "project_inspect", {"query": "entry", "source_ids": selected_ids[:1]}, 1)
        if len(calls) == 2:
            return _tool_packet(request, "project_expand_evidence", {"query": "import dependency", "source_ids": selected_ids[1:]}, 2)
        if len(calls) == 3:
            actual = _find_observed(json.loads(next(m["content"] for m in reversed(request["messages"]) if m["role"] == "tool")))
            assert actual and actual["evidence"]
            evidence = min(actual["evidence"], key=lambda row: len(row["quote"]))
            value = dict(schema_version="project-understanding.v1", objective=objective, object_type=object_type,
                requested_depth=2, achieved_depth=1, analysis_finished=True, decision_readiness="NEEDS_EVIDENCE",
                questions=[dict(question_id="entry", critical=True, status="SUPPORTED", claim_ids=["quoted-entry"]),
                           dict(question_id="dynamic", critical=True, status="EXPLICITLY_UNRESOLVED", claim_ids=[])],
                claims=[dict(claim_id="quoted-entry", text=evidence["quote"], evidence_ids=[evidence["evidence_id"]],
                             conditions=[], exceptions=[], support_mode="SOURCE_DIRECT")],
                dependencies=[], reuse_suggestions=[], unknowns=["Transitive implementation and actual runtime behavior not established"],
                coverage=dict(read_source_ids=[r["source_id"] for r in actual["source_reads"]],
                              unread_source_ids=actual["unread_source_ids"]))
            return _tool_packet(request, "project_submit_analysis", {"query": json.dumps(value)}, 3)
        assert len(calls) == 4
        return 200, packet("OFFLINE CONTROL: static analysis submitted; independent semantic review absent")
    return calls, send


def _reference(path, role):
    return {"path": str(path), "role": role, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def frozen_runtime_entry(public, workspace):
    """Public-only original entry. It never receives private gold or assertions."""
    object_type = public["object_type"]
    name, selected_paths = SAMPLES[object_type]
    root = FROZEN / name
    session = WorkspaceUserSession(workspace / "workspace")
    session.app._project_source_roots = (root.resolve(),)
    package = Path(__file__).resolve().parents[2] / "examples/project_methods/project-understand/0.1.0"
    candidate = session.app.components.discover(package)
    session.app.components.admit(package, candidate["package_sha256"])
    session.app.components.activate("project-understand", "0.1.0")
    inventory = source_manifest(root)
    selected = [next(row["source_id"] for row in inventory if row["relative_path"] == p) for p in selected_paths]
    calls, transport = _transport(object_type, public["objective"], selected)
    session.settings = WorkspaceSettings(session.app, transport=transport)
    config = configuration()
    config["max_requests"] = 4
    session.settings.configure(config)
    recorder = RunRecorder(JsonlTraceStore(session.workspace), run_id="frozen-" + uuid.uuid4().hex,
        request_id="frozen-request-" + uuid.uuid4().hex, invocation_id="inv-" + uuid.uuid4().hex)
    recorder.start(request_kind="project.frozen_source.offline_control")
    try:
        request = ProjectUnderstandingRequest(recorder.request_id, public["objective"], object_type, 2, ("entry", "dynamic"))
        observation = run_project_analysis(session.session, request, root, provider=session.settings.provider, recorder=recorder)
        recorder.finish("success")
        assert len(calls) == 4
        rows = session.settings.ledger.read()
        assert sum(row["event"] == "RESERVED_BEFORE_SEND" for row in rows) == 4
        assert sum(row["event"] == "METERED" for row in rows) == 4
        assert session.settings.ledger.is_settled()
        events = JsonlTraceStore(session.workspace).inspect_run(recorder.run_id)["events"]
        trace = workspace / "r4.jsonl"
        trace.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events), encoding="utf-8")
        result = workspace / "project-result.json"
        result.write_text(json.dumps(observation, ensure_ascii=False), encoding="utf-8")
        runtime_state = session.app.session_dir / (observation["session_id"] + ".json")
        assert runtime_state.is_file()
        observation.update(execution_kind="PRODUCT_RUNTIME", capability_id="project_submit_analysis",
                           evidence_refs=[_reference(trace, "r4"), _reference(result, "project_result"),
                                          _reference(runtime_state, "runtime_state")],
                           fixture_transport="EXPLICIT_OFFLINE_CONTROL", model_quality="NOT_PROVEN")
        return observation
    except Exception as exc:
        # Preserve the true stopping boundary instead of hiding model/P0 limits
        # behind the adapter's intentionally content-free infrastructure class.
        (workspace / "entry-stop.json").write_text(json.dumps({"error_type": type(exc).__name__,
            "error": str(exc), "transport_calls": len(calls), "input_limit": session.settings.task.input_token_limit,
            "run_id": recorder.run_id, "session_id": getattr(exc, "session_id", None)}, ensure_ascii=False), encoding="utf-8")
        raise
    finally:
        if not recorder.is_finished:
            recorder.finish("failure")
        session.app.components.close_loaded()
        session.app.plugins.close()


@pytest.mark.parametrize("object_type", SAMPLES)
def test_fixed_source_runtime_evaluation(tmp_path, object_type):
    if not FROZEN.is_dir():
        pytest.skip("External frozen source corpus absent; no substitute source or downloaded code is executed")
    name, selected_paths = SAMPLES[object_type]
    frozen_manifest = json.loads((FROZEN / "manifest.json").read_text(encoding="utf-8"))
    original = {row["relative_path"]: (FROZEN / row["relative_path"]).read_bytes()
                for row in frozen_manifest["sources"]}
    for row in frozen_manifest["sources"]:
        data = original[row["relative_path"]]
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == row["git_blob_sha1"]
    inventory = source_manifest(FROZEN / name)
    objective = "Inspect " + object_type
    public = {"object_type": object_type, "objective": objective}
    gold = {"basis": "INDEPENDENT_SOURCE_IDENTITY_ONLY", "objective": objective, "object_type": object_type,
            "requested_depth": 2, "critical_question_ids": ["entry", "dynamic"],
            "source_manifest_sha256": digest(inventory),
            "read_source_ids": [row["source_id"] for row in inventory if row["relative_path"] in selected_paths],
            "sources": [{"source_id": row["source_id"], "sha256": row["sha256"],
                         "text": (FROZEN / name / row["relative_path"]).read_bytes().decode("utf-8-sig")} for row in inventory]}
    case = {"id": "fixed_" + object_type, "split": "val", "critical": True, "public": public, "gold": gold}
    evaluated = run_project_evaluation([case], frozen_runtime_entry, tmp_path / "evaluation", target_identity="FROZEN_SOURCE_OFFLINE_CONTROL")
    row = evaluated["rows"][0]
    assert row["status"] == "valid", row
    assert row["dimensions"]["SOURCE_IDENTITY"]["status"] == "PASS", row
    assert row["dimensions"]["COVERAGE_INTEGRITY"]["status"] == "PASS", row
    assert row["dimensions"]["SOURCE_SUPPORT"]["status"] == "NOT_EVALUATED"
    assert row["dimensions"]["SEMANTIC_QUALITY"]["status"] == "NOT_EVALUATED"
    assert row["task_success"] is False and "UNRESOLVED_CRITICAL_QUESTION" in row["critical_faults"]
    observation = json.loads((tmp_path / "evaluation/cases" / case["id"] / "observation.json").read_text(encoding="utf-8"))
    assert observation["analysis"]["decision_readiness"] == "NEEDS_EVIDENCE"
    assert observation["tool_executions"] == {"project_inspect": 1, "project_expand_evidence": 1, "project_submit_analysis": 1}
    assert observation["lifecycle"]["handle_released"] is True
    assert all((FROZEN / path).read_bytes() == data for path, data in original.items())
    # A direct grade has the same deliberate limitations; wrapper success does
    # not overwrite the unresolved business/objective result.
    assert project_grader(observation, gold)["semantic_status"] == "NOT_EVALUATED"
