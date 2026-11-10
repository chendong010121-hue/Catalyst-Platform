"""Bounded software capture, not semantic quality or live authorization."""
import json
from pathlib import Path
from dataclasses import replace

import pytest

from catalyst_platform.llm_provider import configured_model_provider
from catalyst_platform.workbench import CapabilityCatalog
from tests.test_agent_understand_binding import setup_case
from tests.test_api_infrastructure_p0 import response, task


def capture_case(tmp_path, backend="json", fault=None):
    app, session, _, proposal, recorder, wiki = setup_case(tmp_path, backend)
    calls = []

    def send(url, headers, body):
        packet = json.loads(body)
        calls.append(packet)
        assert len(calls) <= 2, "capture must not send a final-answer request"
        if packet.get("response_format"):
            if fault == "timeout":
                raise TimeoutError("offline timeout")
            payload = json.loads(packet["messages"][-1]["content"])
            row = dict(kind="entity", key="team", meaning="服务组", evidence_class="SOURCE_DIRECT",
                       evidence_refs=[payload["evidence"][0]["evidence_id"]])
            if fault == "typed":
                row["kind"] = "inference"
            content = "{broken" if fault == "json" else json.dumps({"items": [row]}, ensure_ascii=False)
            return 200, response(content=content, usage=fault != "usage")
        if fault == "no_tool":
            return 200, response(content="No tool selected")
        result = response()
        result["choices"][0] = {"message": {"role": "assistant", "content": None,
            "tool_calls": [{"id": "capture-tool", "type": "function", "function": {
                "name": CapabilityCatalog.internal_key("understand", "1.0.0"),
                "arguments": json.dumps({"source_ids": ["unknown" if fault == "unknown_ids" else "document"]})}}]}, "finish_reason": "tool_calls"}
        return 200, result

    provider = configured_model_provider(provider_id="deepseek", api_key="OFFLINE-NON-CREDENTIAL",
        model="deepseek-flash", base_url="https://api.deepseek.com", transport=send,
        task=task(input_token_limit=100000, max_output_tokens=1024))
    provider.mode = "offline"
    proposal = replace(proposal, provider=provider,
                       harvest=lambda _: pytest.fail("capture may not call Harvest"))
    return session, provider, proposal, recorder, wiki, calls


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_real_agent_capture_stops_normally_before_harvest(tmp_path, backend):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path, backend)
    result = session.capture_enterprise_semantics("形成候选", provider=provider,
        proposal_context=proposal, recorder=recorder, artifact_dir=wiki.workspace / ".catalyst/captures/run")
    receipt = result.summary()
    assert receipt["status"] == "CAPTURED" and receipt["typed_capture"] is True
    assert receipt["runtime_terminal"] == "success"
    assert receipt["boundary"] == "BEFORE_HARVEST" and receipt["candidate_id"] is None
    assert receipt["trace"]["run_id"] == recorder.run_id and receipt["trace"]["session_id"]
    assert len(calls) == provider.budget_snapshot["attempts"] == 2
    assert len(result.observation()["items"]) == 1
    assert receipt["artifacts"]["understanding"]["sha256"]
    assert "服务组" not in json.dumps(receipt, ensure_ascii=False)
    assert wiki.semantic_state()["candidates"] == {} and wiki.semantic_state()["active_version_id"] is None


@pytest.mark.parametrize("fault,status", [("typed", "OUTPUT_REJECTED"), ("json", "OUTPUT_REJECTED"),
                                          ("usage", "MODEL_FAILURE"), ("timeout", "MODEL_FAILURE")])
def test_failure_preserves_raw_and_never_sends_third_call(tmp_path, fault, status):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path, fault=fault)
    result = session.capture_enterprise_semantics("形成候选", provider=provider,
        proposal_context=proposal, recorder=recorder, artifact_dir=wiki.workspace / ".catalyst/captures/run")
    receipt = result.summary()
    assert receipt["status"] == status and receipt["typed_capture"] is False
    assert len(calls) == 2
    assert bool(receipt["artifacts"].get("raw_response")) is (fault != "timeout")
    if fault == "typed":
        assert result.observation()["items"][0]["kind"] == "inference"
    if fault in ("usage", "timeout"):
        assert provider.budget_snapshot["uncertain"] is True
    assert wiki.semantic_state()["candidates"] == {} and wiki.semantic_state()["active_version_id"] is None


def test_no_tool_selected_is_not_capture_success(tmp_path):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path, fault="no_tool")
    result = session.capture_enterprise_semantics("形成候选", provider=provider,
        proposal_context=proposal, recorder=recorder, artifact_dir=wiki.workspace / ".catalyst/captures/run")
    assert result.summary()["status"] == "NOT_EXECUTED" and len(calls) == 1
    with pytest.raises(ValueError, match="observation"):
        result.observation()


@pytest.mark.parametrize("fault", ["scope", "changed", "outside_artifacts", "reused_artifacts",
                                   "readable_artifacts", "source_overlap"])
def test_capture_preflight_zero_dispatch(tmp_path, fault):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path)
    folder = wiki.workspace / ".catalyst/captures/run"
    if fault == "scope":
        proposal = replace(proposal, actor_context={**proposal.actor_context, "readable_scope_ids": []})
    elif fault == "changed":
        next(iter(proposal.sources.values())).path.write_text("changed", encoding="utf-8")
    elif fault == "outside_artifacts":
        folder = tmp_path / "outside"
    elif fault == "readable_artifacts":
        folder = wiki.workspace / "private/capture"
    elif fault == "source_overlap":
        session.app.wiki_roots = (tmp_path,)
        proposal = replace(proposal, source_root=tmp_path)
    else:
        folder.mkdir(parents=True)
    with pytest.raises((ValueError, OSError)):
        session.capture_enterprise_semantics("形成候选", provider=provider, proposal_context=proposal,
            recorder=recorder, artifact_dir=folder)
    assert not calls and not provider.budget_snapshot["attempts"]


def test_unknown_source_id_stops_without_extraction(tmp_path):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path, fault="unknown_ids")
    result = session.capture_enterprise_semantics("形成候选", provider=provider,
        proposal_context=proposal, recorder=recorder, artifact_dir=wiki.workspace / ".catalyst/captures/run")
    assert len(calls) == 1 and result.summary()["typed_capture"] is False
    assert result.summary()["runtime_terminal"] == "failure"


def test_capture_observation_tamper_is_not_consumed(tmp_path):
    session, provider, proposal, recorder, wiki, _ = capture_case(tmp_path)
    folder = wiki.workspace / ".catalyst/captures/run"
    result = session.capture_enterprise_semantics("形成候选", provider=provider,
        proposal_context=proposal, recorder=recorder, artifact_dir=folder)
    (folder / result.summary()["artifacts"]["observation"]["path"]).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        result.observation()


def test_interrupted_product_preserves_raw_without_reporting_completion(tmp_path, monkeypatch):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path)
    original = session.ask

    def interrupt(*args, **kwargs):
        original(*args, **kwargs)
        raise KeyboardInterrupt("offline interruption")

    monkeypatch.setattr(session, "ask", interrupt)
    folder = wiki.workspace / ".catalyst/captures/run"
    with pytest.raises(KeyboardInterrupt):
        session.capture_enterprise_semantics("形成候选", provider=provider,
            proposal_context=proposal, recorder=recorder, artifact_dir=folder)
    receipt = json.loads((folder / "CAPTURE_RECEIPT.json").read_bytes())
    assert receipt["status"] == "INTERRUPTED" and receipt["runtime_terminal"] == "not_completed"
    assert receipt["artifacts"]["raw_response"] and len(calls) == 2


def test_capture_write_failure_leaves_partial_scope_and_never_retries(tmp_path, monkeypatch):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path)
    original = Path.open

    def denied(path, *args, **kwargs):
        if path.name == "001_request.json":
            raise PermissionError("offline artifact write denial")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    folder = wiki.workspace / ".catalyst/captures/run"
    with pytest.raises(PermissionError):
        session.capture_enterprise_semantics("形成候选", provider=provider,
            proposal_context=proposal, recorder=recorder, artifact_dir=folder)
    assert len(calls) == 2 and folder.exists()
    with pytest.raises(FileExistsError):
        session.capture_enterprise_semantics("形成候选", provider=provider,
            proposal_context=proposal, recorder=recorder, artifact_dir=folder)
    assert len(calls) == 2


def test_typed_output_does_not_override_failed_execution(tmp_path, monkeypatch):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path)
    original = session.ask

    def failed_result(*args, **kwargs):
        run = original(*args, **kwargs)
        return replace(run, result=replace(run.result, status="failure",
                                          error={"code": "synthetic_execution_failure", "message": "Offline fault"}))

    monkeypatch.setattr(session, "ask", failed_result)
    result = session.capture_enterprise_semantics("形成候选", provider=provider,
        proposal_context=proposal, recorder=recorder, artifact_dir=wiki.workspace / ".catalyst/captures/run")
    assert result.summary()["status"] == "EXECUTION_FAILURE"
    assert result.summary()["typed_capture"] is True and len(calls) == 2


def test_future_readable_descendant_cannot_become_capture_output(tmp_path):
    session, provider, proposal, recorder, wiki, calls = capture_case(tmp_path)
    folder = wiki.workspace / ".catalyst/captures/run"
    session.app.enterprise_source_allowlist = {session.enterprise["id"]: (
        proposal.source_root, folder / "calls")}
    with pytest.raises(ValueError, match="overlap"):
        session.capture_enterprise_semantics("形成候选", provider=provider,
            proposal_context=proposal, recorder=recorder, artifact_dir=folder)
    assert calls == [] and not folder.exists()
