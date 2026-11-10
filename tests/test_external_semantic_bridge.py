from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki
from p0_test_authority import trusted_test_operation


def _cli(repo: Path, *args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload


def _common(workspace: Path, roots: Path, backend: str) -> list[str]:
    return [
        "--workspace", str(workspace),
        "--wiki-root", str(roots),
        "--enterprise-id", "synthetic-enterprise",
        "--project-id", "external-bridge-test",
        "--wiki-backend", backend,
    ]


def _submission(source: dict, quote: str, key: str, meaning: str) -> dict:
    return {
        "schema_version": "catalyst.external_candidate.v1",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [
            {
                "kind": "claim",
                "key": key,
                "meaning": meaning,
                "evidence_class": "inferred",
                "evidence": {
                    "line_start": 2,
                    "line_end": 2,
                    "quote": quote,
                    "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                },
            }
        ],
    }


def _write_submission(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _schema(repo: Path, filename: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((repo / "schemas" / filename).read_text(encoding="utf-8")))


def test_external_submission_anchors_original_source_and_carries_campaign_correlation(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    roots = tmp_path / "approved_sources"
    roots.mkdir()
    original = roots / "policy.md"
    original.write_text(
        "# 合成质量制度\n"
        "制度规定，质量评审负责人负责记录复核。\n",
        encoding="utf-8",
    )
    common = _common(workspace, roots, "json")
    campaign = "2-9-test-original-source"

    code, staged = _cli(
        repo,
        "ontology", "source", "stage", *common,
        "--correlation-id", campaign,
        "--file", str(original),
    )
    assert code == 0 and staged["status"] == "success", staged
    source = staged["result"]
    quote = "制度规定，质量评审负责人负责记录复核。"
    submission = {
        "schema_version": "catalyst.external_candidate.v1",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [
            {
                "kind": "claim",
                "key": "quality-review-duty",
                "meaning": "质量评审负责人负责记录复核。",
                "evidence_class": "inferred",
                "evidence": {
                    "line_start": 2,
                    "line_end": 2,
                    "quote": quote,
                    "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                },
            }
        ],
    }
    generated_candidate = tmp_path / "generated_candidate.json"
    generated_candidate.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")

    code, proposed = _cli(
        repo,
        "ontology", "external", "submit", *common,
        "--correlation-id", campaign,
        "--submission", str(generated_candidate),
    )
    assert code == 0 and proposed["status"] == "success", json.dumps(proposed, ensure_ascii=False)
    assert proposed["result"]["source_id"] == source["source_id"]
    assert proposed["result"]["source_revision"] == source["revision"]
    assert proposed["result"]["candidate_id"].startswith("candidate_")

    trace = JsonlTraceStore(workspace).inspect_run(proposed["run_id"])
    assert trace is not None and trace["terminal_status"] == "success"
    assert all(event.get("correlation_id") == campaign for event in trace["events"])
    action = next(event for event in trace["events"] if event["event_type"] == "semantic.external.action")
    assert action["action"] == "candidate_submitted"
    assert action["status"] == "submitted"
    assert action["evidence_level"] == "DIRECTLY_OBSERVED"
    assert action["source_id"] == source["source_id"]
    assert action["source_revision"] == source["revision"]
    assert action["candidate_id"] == proposed["result"]["candidate_id"]
    assert action["internal_reasoning_status"] == "NOT_OBSERVABLE"
    assert action["producer_usage_status"] == "unknown"
    raw_trace = Path(trace["trace_path"]).read_text(encoding="utf-8")
    assert str(generated_candidate) not in raw_trace
    assert quote not in raw_trace
    assert "input_tokens" not in raw_trace and "output_tokens" not in raw_trace


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_external_campaign_reuses_one_wiki_and_cold_correlates_evaluate_consume_and_rollback(tmp_path, backend):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    roots = tmp_path / "approved_sources"
    roots.mkdir()
    source_a_path = roots / "policy_a.md"
    source_b_path = roots / "policy_b.md"
    quote_a = "制度规定，质量评审负责人负责记录复核。"
    quote_b = "补充说明，档案管理员负责保留审批记录。"
    source_a_path.write_text(f"# 合成制度甲\n{quote_a}\n", encoding="utf-8")
    source_b_path.write_text(f"# 合成制度乙\n{quote_b}\n", encoding="utf-8")
    common = _common(workspace, roots, backend)
    campaign = f"2-9-{backend}-synthetic-bridge"
    outputs: list[dict] = []

    def call(*args: str) -> dict:
        code, value = _cli(repo, "ontology", *args, *common, "--correlation-id", campaign)
        assert code == 0 and value.get("status") == "success", json.dumps(value, ensure_ascii=False)
        outputs.append(value)
        return value

    wiki = ProjectWiki(
        workspace,
        [roots],
        enterprise_id="synthetic-enterprise",
        project_id="external-bridge-test",
        backend=backend,
    )

    def denied_without_authority(*args: str, expected_code: str) -> dict:
        code, value = _cli(repo, "ontology", *args, *common, "--correlation-id", campaign)
        assert code == 1 and value.get("error", {}).get("code") == expected_code, value
        trace = JsonlTraceStore(workspace).inspect_run(value["run_id"])
        assert trace is not None and trace["terminal_status"] == "failure"
        return value

    def test_authorized(method: str, run_id: str, *args, **kwargs) -> dict:
        outcome = trusted_test_operation(
            workspace, wiki, run_id, method, *args, correlation_id=campaign, **kwargs
        )
        value = {"run_id": outcome["run_id"], "status": "success", "result": outcome["result"]}
        outputs.append(value)
        return value

    source_a = call("source", "stage", "--file", str(source_a_path))["result"]
    read_a = call("external", "read-receipt", "--source-id", source_a["source_id"], "--source-revision", source_a["revision"])
    candidate_a_file = tmp_path / "candidate_a.json"
    submission_a = _submission(source_a, quote_a, "quality-review-duty", quote_a)
    errors = list(_schema(repo, "external_candidate_submission_v1.schema.json").iter_errors(submission_a))
    assert not errors
    _write_submission(candidate_a_file, submission_a)
    candidate_a = call("external", "submit", "--submission", str(candidate_a_file))["result"]
    evaluation_a = call("candidate", "evaluate", "--candidate-id", candidate_a["candidate_id"])["result"]
    assert evaluation_a["status"] == "pass"
    denied_without_authority(
        "candidate", "decide", "--candidate-id", candidate_a["candidate_id"],
        "--decision", "ACCEPTED", "--reason-code", "synthetic-test-manager-review",
        expected_code="external_semantic_evaluation_required",
    )
    decision_a = test_authorized(
        "decide", "test_only_accept_a", candidate_a["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="synthetic-test-manager-review",
    )["result"]
    version_a = decision_a["version_id"]
    denied_without_authority(
        "version", "activate", "--version-id", version_a, "--expected-head", "none",
        expected_code="authority_receipt_required",
    )
    test_authorized(
        "activate", "test_only_activate_a", version_a,
        actor_origin="manager_acceptance", expected_head_version_id=None,
    )
    query_a = call("query", "--query", "质量评审负责人记录复核")["result"]
    assert query_a["active_version_id"] == version_a
    assert any(row["key"] == "quality-review-duty" for row in query_a["meanings"])

    source_b = call("source", "stage", "--file", str(source_b_path))["result"]
    call("external", "read-receipt", "--source-id", source_b["source_id"], "--source-revision", source_b["revision"])
    candidate_b_file = tmp_path / "candidate_b.json"
    _write_submission(candidate_b_file, _submission(source_b, quote_b, "record-retention-duty", quote_b))
    candidate_b = call("external", "submit", "--submission", str(candidate_b_file))["result"]
    evaluation_b = call("candidate", "evaluate", "--candidate-id", candidate_b["candidate_id"])["result"]
    assert evaluation_b["status"] == "pass"
    denied_without_authority(
        "candidate", "decide", "--candidate-id", candidate_b["candidate_id"],
        "--decision", "ACCEPTED", "--reason-code", "synthetic-test-manager-review",
        expected_code="external_semantic_evaluation_required",
    )
    decision_b = test_authorized(
        "decide", "test_only_accept_b", candidate_b["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="synthetic-test-manager-review",
    )["result"]
    version_b = decision_b["version_id"]
    denied_without_authority(
        "version", "activate", "--version-id", version_b, "--expected-head", version_a,
        expected_code="authority_receipt_required",
    )
    test_authorized(
        "activate", "test_only_activate_b", version_b,
        actor_origin="manager_acceptance", expected_head_version_id=version_a,
    )
    both = call("wiki", "--query", "质量评审负责人 档案管理员")["result"]
    assert both["active_version_id"] == version_b
    denied_without_authority(
        "version", "rollback", "--version-id", version_a, "--expected-head", version_b,
        expected_code="authority_receipt_required",
    )
    rollback = test_authorized(
        "rollback", "test_only_rollback_a", version_a,
        actor_origin="manager_acceptance", expected_head_version_id=version_b,
    )
    assert rollback["result"]["status"] == "active"
    assert rollback["result"]["active_version_id"] == version_a
    cold_after_rollback = call("query", "--query", "质量评审负责人记录复核")["result"]
    assert cold_after_rollback["active_version_id"] == version_a
    assert {row["key"] for row in cold_after_rollback["meanings"]} == {"quality-review-duty"}

    assert set(wiki._store.load()["sources"]) == {source_a["source_id"], source_b["source_id"]}
    assert wiki.semantic_state()["active_version_id"] == version_a

    store = JsonlTraceStore(workspace)
    event_validators = {
        version: Draft202012Validator(_schema(repo, f"run_event_v{version.replace('.', '_')}.schema.json").schema)
        for version in ("1.4", "1.5")
    }
    for output in outputs:
        trace = store.inspect_run(output["run_id"])
        assert trace is not None and trace["terminal_status"] == "success"
        assert all(row.get("correlation_id") == campaign for row in trace["events"])
        invalid = [
            (row["event_type"], [error.message for error in event_validators[row["event_schema_version"]].iter_errors(row)])
            for row in trace["events"]
            if list(event_validators[row["event_schema_version"]].iter_errors(row))
        ]
        assert not invalid, invalid
    assert read_a["result"]["evidence_level"] == "EXTERNAL_SELF_REPORTED"
    all_trace_text = store.path.read_text(encoding="utf-8")
    for secretish in (str(candidate_a_file), str(candidate_b_file), quote_a, quote_b, "input_tokens", "output_tokens"):
        assert secretish not in all_trace_text
    external_events = [
        row for output in outputs for row in store.inspect_run(output["run_id"])["events"]
        if row["event_type"] == "semantic.external.action"
    ]
    assert {row["action"] for row in external_events} == {"source_read_receipt", "candidate_submitted"}
    assert {row["evidence_level"] for row in external_events} == {"EXTERNAL_SELF_REPORTED", "DIRECTLY_OBSERVED"}
    assert all(row["producer_usage_status"] == "unknown" for row in external_events)
    assert all(row["internal_reasoning_status"] == "NOT_OBSERVABLE" for row in external_events)


@pytest.mark.parametrize("mutation,expected_code", [
    ("stale_revision", "source_revision_changed"),
    ("wrong_quote", "evidence_anchor_mismatch"),
    ("unknown_secret_field", "invalid_submission_fields"),
])
def test_invalid_external_submission_is_rejected_without_persisting_payload(tmp_path, mutation, expected_code):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    roots = tmp_path / "approved_sources"
    roots.mkdir()
    original = roots / "policy.md"
    quote = "制度规定，质量评审负责人负责记录复核。"
    original.write_text(f"# 合成制度\n{quote}\n", encoding="utf-8")
    common = _common(workspace, roots, "json")
    campaign = "2-9-invalid-submission-test"
    code, staged = _cli(repo, "ontology", "source", "stage", *common, "--correlation-id", campaign, "--file", str(original))
    assert code == 0
    source = staged["result"]
    submission = _submission(source, quote, "quality-review-duty", quote)
    if mutation == "stale_revision":
        submission["source_revision"] = "a" * 64
        submission["origin_document_sha256"] = "a" * 64
    elif mutation == "wrong_quote":
        submission["items"][0]["evidence"]["quote"] = "伪造的原文锚点"
    else:
        submission["api_key"] = "sk-EXTERNAL-SECRET-DO-NOT-LOG"
    submission_path = tmp_path / "external_candidate.json"
    _write_submission(submission_path, submission)
    code, failed = _cli(
        repo, "ontology", "external", "submit", *common,
        "--correlation-id", campaign,
        "--submission", str(submission_path),
    )
    assert code == 1
    assert failed["error"]["code"] == expected_code
    trace = JsonlTraceStore(workspace).inspect_run(failed["run_id"])
    assert trace is not None and trace["terminal_status"] == "failure"
    action = next(row for row in trace["events"] if row["event_type"] == "semantic.external.action")
    assert action["status"] == "rejected" and action["error_code"] == expected_code
    assert all(row.get("correlation_id") == campaign for row in trace["events"])
    trace_text = JsonlTraceStore(workspace).path.read_text(encoding="utf-8")
    assert str(submission_path) not in trace_text
    assert "sk-EXTERNAL-SECRET-DO-NOT-LOG" not in trace_text
    assert "伪造的原文锚点" not in trace_text
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic-enterprise", project_id="external-bridge-test")
    assert wiki.semantic_state()["candidates"] == {}


def test_codex_external_candidate_origin_cannot_self_approve(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_path = roots / "source.md"
    quote = "制度规定，负责人应复核记录。"
    source_path.write_text(f"# 合成制度\n{quote}\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic-enterprise", project_id="external-bridge-test")
    staged = wiki.stage_markdown(source_path)
    submission = _submission(staged, quote, "record-review-duty", quote)
    store = JsonlTraceStore(workspace)
    producer = RunRecorder(
        store,
        run_id="run_external_candidate_origin",
        request_id="req_external_candidate_origin",
        invocation_id="inv_external_candidate_origin",
        correlation_id="2-9-self-approval-test",
    )
    producer.start(request_kind="external_candidate_test")
    producer_service = SemanticWiki(wiki, recorder=producer)
    candidate = producer_service.propose_external_submission(submission)
    producer.finish("success", model_calls=0)
    producer_service.finalize_run(producer.run_id, "success")

    attempted = RunRecorder(
        store,
        run_id="run_external_self_approval_attempt",
        request_id="req_external_self_approval_attempt",
        invocation_id="inv_external_self_approval_attempt",
        correlation_id="2-9-self-approval-test",
    )
    attempted.start(request_kind="external_self_approval_test")
    service = SemanticWiki(wiki, recorder=attempted)
    with pytest.raises(SemanticTransitionError) as raised:
        service.decide(
            candidate["candidate_id"],
            decision="ACCEPTED",
            actor_origin="codex_external",
            reason_code="attempted_self_approval",
        )
    assert raised.value.code == "self_approval_denied"
    attempted.finish("failure", model_calls=0, error_owner="semantic_wiki")
    assert wiki.semantic_state()["candidates"][candidate["candidate_id"]]["status"] == "PROPOSED"


def test_external_consumer_read_can_be_labeled_and_correlated_as_codex(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    campaign = "2-9-external-consumer-read"

    code, result = _cli(
        repo,
        "ontology", "query",
        "--workspace", str(workspace),
        "--wiki-root", str(roots),
        "--enterprise-id", "synthetic-enterprise",
        "--project-id", "external-bridge-test",
        "--wiki-backend", "json",
        "--query", "质量审核",
        "--actor-origin", "codex_external",
        "--correlation-id", campaign,
    )

    assert code == 0, result
    trace = JsonlTraceStore(workspace).inspect_run(result["run_id"])
    assert trace is not None and trace["terminal_status"] == "success"
    consumer = next(row for row in trace["events"] if row["event_type"] == "semantic.consumer.queried")
    assert consumer["actor_origin"] == "codex_external"
    assert all(row.get("correlation_id") == campaign for row in trace["events"])


def test_external_event_allowlist_drops_unknown_credentials_and_usage_fields(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    store = JsonlTraceStore(workspace)
    recorder = RunRecorder(
        store,
        run_id="run_external_event_allowlist",
        request_id="req_external_event_allowlist",
        invocation_id="inv_external_event_allowlist",
        correlation_id="2-9-event-allowlist-test",
    )
    recorder.start(request_kind="external_event_allowlist_test")
    event = recorder.event(
        "semantic.external.action",
        action="candidate_submitted",
        producer_origin="codex_external",
        evidence_level="DIRECTLY_OBSERVED",
        internal_reasoning_status="NOT_OBSERVABLE",
        producer_usage_status="unknown",
        status="recorded",
        api_key="sk-EXTERNAL-SECRET-DO-NOT-LOG",
        prompt="sensitive prompt must not be stored",
        input_tokens=999,
        custom_payload={"secret": "hidden"},
    )
    recorder.finish("success", model_calls=0)
    trace = store.inspect_run(recorder.run_id)
    assert trace is not None
    assert all(row.get("correlation_id") == "2-9-event-allowlist-test" for row in trace["events"])
    assert "api_key" not in event and "prompt" not in event and "input_tokens" not in event and "custom_payload" not in event
    raw_trace = store.path.read_text(encoding="utf-8")
    assert "sk-EXTERNAL-SECRET-DO-NOT-LOG" not in raw_trace
    assert "sensitive prompt must not be stored" not in raw_trace
    event_schema = _schema(repo, "run_event_v1_4.schema.json")
    assert all(not list(event_schema.iter_errors(row)) for row in trace["events"])


def test_v13_trace_and_schema_remain_readable_after_v14_addition(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    source_store = JsonlTraceStore(tmp_path / "v14_source")
    recorder = RunRecorder(
        source_store,
        run_id="run_v13_compat_source",
        request_id="req_v13_compat_source",
        invocation_id="inv_v13_compat_source",
        trace_id="a" * 32,
    )
    recorder.start(request_kind="v13_compatibility")
    recorder.event("result.emitted", status="success", result_sha256="b" * 64)
    recorder.finish("success", model_calls=0)
    current = source_store.inspect_run(recorder.run_id)
    assert current is not None

    legacy_events = []
    for event in current["events"]:
        legacy = dict(event)
        legacy["event_schema_version"] = "1.3"
        legacy.pop("correlation_id", None)
        legacy_events.append(legacy)
    legacy_workspace = tmp_path / "v13_legacy"
    legacy_store = JsonlTraceStore(legacy_workspace)
    legacy_store.path.parent.mkdir(parents=True, exist_ok=True)
    legacy_store.path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in legacy_events),
        encoding="utf-8",
    )
    replay = legacy_store.inspect_run(recorder.run_id)
    assert replay is not None and replay["terminal_status"] == "success"
    validator = _schema(repo, "run_event_v1_3.schema.json")
    assert all(not list(validator.iter_errors(row)) for row in legacy_events)
