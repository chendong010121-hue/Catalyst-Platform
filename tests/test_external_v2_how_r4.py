from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.semantic_wiki import _entry_rows, _meaning_id
from catalyst_platform.wiki import ProjectWiki
from p0_test_authority import trusted_test_operation


REPO = Path(__file__).resolve().parents[1]


def _cli(*args: str) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    payload = json.loads(result.stdout) if result.stdout.strip() else {}
    return result.returncode, payload


def _wiki_args(workspace: Path, roots: Path, backend: str, enterprise: str = "synthetic-enterprise") -> list[str]:
    return [
        "--workspace", str(workspace), "--wiki-root", str(roots),
        "--enterprise-id", enterprise, "--project-id", "external-v2",
        "--wiki-backend", backend,
    ]


def _evidence(quote: str, line: int) -> dict:
    return {
        "line_start": line,
        "line_end": line,
        "quote": quote,
        "span_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
    }


def _v2_submission(source: dict, lines: list[str]) -> dict:
    return {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [
            {"kind": "entity", "canonical_key": "qa_lead", "display_name": "质量评审负责人", "evidence_class": "observed_from_source", "evidence": _evidence(lines[1], 2)},
            {"kind": "entity", "canonical_key": "release_gate", "display_name": "发布放行门", "evidence_class": "observed_from_source", "evidence": _evidence(lines[2], 3)},
            {"kind": "alias", "canonical_key": "qa_lead", "display_name": "质量审核负责人", "evidence_class": "observed_from_source", "evidence": _evidence(lines[3], 4)},
            {"kind": "relation", "subject": "@qa_lead", "predicate": "approves", "object": "@release_gate", "evidence_class": "observed_from_source", "evidence": _evidence(lines[4], 5)},
            {"kind": "claim", "key": "release-duty", "meaning": "质量评审负责人负责发布放行", "evidence_class": "observed_from_source", "evidence": _evidence(lines[5], 6)},
            # An absence carries both halves or it is not an absence: what was looked for
            # and where it searched. The store checks the places against the source.
            {"kind": "unknown", "key": "supplier-review-unknown", "meaning": "供应商复核职责尚未确认", "evidence_class": "unresolved", "evidence": _evidence(lines[6], 7),
             "absence": "供应商复核职责", "searched": ["line:7"]},
            {"kind": "condition", "key": "qualified-supplier", "meaning": "供应商完成备案后适用", "evidence_class": "observed_from_source", "evidence": _evidence(lines[7], 8)},
            {"kind": "exception", "key": "emergency-review", "meaning": "重大安全事故进入应急评审", "evidence_class": "observed_from_source", "evidence": _evidence(lines[8], 9)},
        ],
    }


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_external_v2_seven_types_share_existing_wiki_lifecycle_and_cold_read(tmp_path: Path, backend: str):
    workspace = tmp_path / backend / "workspace"
    roots = tmp_path / backend / "sources"
    roots.mkdir(parents=True)
    source_path = roots / "quality_policy.md"
    lines = [
        "# 合成质量制度",
        "Entity: qa_lead | 质量评审负责人",
        "Entity: release_gate | 发布放行门",
        "Alias: qa_lead | 质量审核负责人",
        "Relation: @qa_lead | approves | @release_gate",
        "Claim: release-duty | 质量评审负责人负责发布放行",
        "Unknown: supplier-review-unknown | 供应商复核职责尚未确认",
        "Condition: qualified-supplier | 供应商完成备案后适用",
        "Exception: emergency-review | 重大安全事故进入应急评审",
    ]
    source_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    common = _wiki_args(workspace, roots, backend)

    code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
    assert code == 0 and staged["status"] == "success", staged
    source = staged["result"]
    submission = _v2_submission(source, lines)
    schema = Draft202012Validator(json.loads((REPO / "schemas/external_candidate_submission_v2.schema.json").read_text(encoding="utf-8")))
    assert not list(schema.iter_errors(submission))
    submission_path = tmp_path / f"{backend}-candidate-v2.json"
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")

    code, proposed = _cli(
        "ontology", "external", "submit-v2", *common,
        "--correlation-id", f"external-v2-{backend}", "--submission", str(submission_path),
    )
    assert code == 0 and proposed["status"] == "success", proposed
    candidate_id = proposed["result"]["candidate_id"]
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic-enterprise", project_id="external-v2", backend=backend)
    candidate = wiki.semantic_state()["candidates"][candidate_id]
    assert {entry["kind"] for entry in candidate["entries"]} == {
        "claim", "unknown", "entity", "alias", "relation", "condition", "exception",
    }
    assert all(entry["source_id"] == source["source_id"] for entry in candidate["entries"])
    assert all(entry["source_revision"] == source["revision"] for entry in candidate["entries"])
    assert all(entry["evidence_class"] in {"observed_from_source", "unresolved", "inferred"} for entry in candidate["entries"])
    source_snapshot = wiki.source_snapshot(source["source_id"])
    marker_rows = _entry_rows(
        source_snapshot["content"], source_snapshot["source"], wiki.claim_history(source["source_id"])
    )
    marker_identity_pairs = {(row["kind"], row["meaning_id"]) for row in marker_rows}
    assert all((entry["kind"], entry["meaning_id"]) in marker_identity_pairs for entry in candidate["entries"] if entry["kind"] != "unknown"), [
        (entry["kind"], entry["meaning_id"]) for entry in candidate["entries"]
        if entry["kind"] != "unknown" and (entry["kind"], entry["meaning_id"]) not in marker_identity_pairs
    ]
    typed_unknown = next(entry for entry in candidate["entries"] if entry["kind"] == "unknown")
    assert typed_unknown["meaning_id"] == _meaning_id(source["scope_id"], "unknown", "supplier-review-unknown")

    code, evaluation = _cli("ontology", "candidate", "evaluate", *common, "--candidate-id", candidate_id)
    assert code == 0 and evaluation["result"]["status"] == "pass", evaluation
    code, denied_decision = _cli(
        "ontology", "candidate", "decide", *common,
        "--candidate-id", candidate_id, "--decision", "ACCEPTED", "--reason-code", "synthetic-manager-review",
    )
    assert code == 1 and denied_decision["error"]["code"] == "external_semantic_evaluation_required", denied_decision
    decision = trusted_test_operation(
        workspace, wiki, f"{backend}_test_only_accept", "decide", candidate_id,
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="synthetic-manager-review",
    )
    version_id = decision["result"]["version_id"]
    code, denied_activation = _cli("ontology", "version", "activate", *common, "--version-id", version_id)
    assert code == 1 and denied_activation["error"]["code"] == "authority_receipt_required", denied_activation
    activation = trusted_test_operation(
        workspace, wiki, f"{backend}_test_only_activate", "activate", version_id,
        actor_origin="manager_acceptance", expected_head_version_id=None,
    )
    assert activation["result"]["active_version_id"] == version_id
    code, query = _cli("ontology", "query", *common, "--query", "质量评审发布职责")
    assert code == 0 and query["result"]["active_version_id"] == version_id, query

    fresh = subprocess.run(
        [sys.executable, "-c", "from catalyst_platform.wiki import ProjectWiki; import sys; w=ProjectWiki(sys.argv[1],[sys.argv[2]],enterprise_id='synthetic-enterprise',project_id='external-v2',backend=sys.argv[3]); s=w.semantic_state(); print(s['active_version_id'])", str(workspace), str(roots), backend],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert fresh.stdout.strip() == version_id
    assert JsonlTraceStore(workspace).inspect_run(proposed["run_id"])["terminal_status"] == "success"


def test_external_v2_wrong_original_quote_fails_closed_with_trace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_path = roots / "policy.md"
    source_path.write_text("# 合成制度\n制度规定质量负责人复核。\n", encoding="utf-8")
    common = _wiki_args(workspace, roots, "json")
    code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
    assert code == 0
    source = staged["result"]
    submission = {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [{
            "kind": "claim", "key": "review-duty", "meaning": "质量负责人复核",
            "evidence_class": "inferred",
            "evidence": {"line_start": 2, "line_end": 2, "quote": "伪造的原文", "span_sha256": "0" * 64},
        }],
    }
    submission_path = tmp_path / "candidate.json"
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")
    code, rejected = _cli(
        "ontology", "external", "submit-v2", *common,
        "--correlation-id", "external-v2-negative", "--submission", str(submission_path),
    )
    assert code == 1 and rejected["error"]["code"] == "evidence_anchor_mismatch", rejected
    trace = JsonlTraceStore(workspace).inspect_run(rejected["run_id"])
    assert trace is not None and trace["terminal_status"] == "failure"
    assert not ProjectWiki(workspace, [roots], enterprise_id="synthetic-enterprise", project_id="external-v2").semantic_state()["candidates"]
    raw_trace = JsonlTraceStore(workspace).path.read_text(encoding="utf-8")
    assert "伪造的原文" not in raw_trace and str(submission_path) not in raw_trace


def test_external_v2_relation_evidence_requires_token_boundaries(tmp_path: Path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_path = roots / "policy.md"
    quote = "@quality-assurance approves @release-gate"
    source_path.write_text(f"# Synthetic policy\n{quote}\n", encoding="utf-8")
    common = _wiki_args(workspace, roots, "json")
    code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
    assert code == 0, staged
    source = staged["result"]
    submission = {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [{
            "kind": "relation", "subject": "@qual", "predicate": "approves", "object": "@release-gate",
            "evidence_class": "observed_from_source", "evidence": _evidence(quote, 2),
        }],
    }
    submission_path = tmp_path / "candidate.json"
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")
    code, rejected = _cli(
        "ontology", "external", "submit-v2", *common,
        "--correlation-id", "external-v2-relation-boundary", "--submission", str(submission_path),
    )
    assert code == 1 and rejected["error"]["code"] == "observed_text_mismatch", rejected
    assert not ProjectWiki(workspace, [roots], enterprise_id="synthetic-enterprise", project_id="external-v2").semantic_state()["candidates"]


def test_semantic_gateway_redacts_untrusted_error_codes_from_result_and_trace(tmp_path: Path):
    gateway = CatalystGateway(tmp_path)
    private_value = r"E:\private\customer\token=not-for-trace"

    class UnsafeError(RuntimeError):
        code = private_value

    def fail(_recorder):
        raise UnsafeError("synthetic failure")

    result = gateway.semantic_operation(
        operation="candidate.submit",
        scope_id="scope_synthetic",
        actor_origin="codex_external",
        input_value={},
        action=fail,
    )
    assert result["status"] == "failure"
    assert result["error"]["code"] == "semantic_operation_failed"
    trace = gateway.inspect_run(result["run_id"])
    assert trace is not None and trace["terminal_status"] == "failure"
    trace_text = gateway.traces.path.read_text(encoding="utf-8")
    assert private_value not in trace_text
    assert private_value not in json.dumps(result, ensure_ascii=False)


def test_how_evolution_and_rollback_emit_v15_r4_runs_and_cold_replay(tmp_path: Path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "wiki"
    roots.mkdir()
    source = roots / "operating-model.md"
    expected = "Domain and Enterprise are parallel semantic dimensions."
    source.write_text(
        f"# Reference index\nOpening summary unrelated to the search term.\n"
        f"Another short introductory line.\nA third brief overview line.\n{expected}\n",
        encoding="utf-8",
    )
    benchmark = [{
        "query": expected,
        "expected_source": str(source.resolve()),
        "expected_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "expected_text": expected,
    }]
    benchmark_path = tmp_path / "benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
    args = ["--workspace", str(workspace), "--wiki-root", str(roots)]
    code, acquired = _cli("acquire-ripgrep", *args)
    assert code == 0, acquired

    code, evolved = _cli("evolve-understand", *args, "--benchmark", str(benchmark_path), "--activate")
    assert code == 0 and evolved["evaluation"]["status"] == "pass", evolved
    evolve_run_id = evolved["run_id"]
    cold = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", "inspect", "--workspace", str(workspace), "--run-id", evolve_run_id],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    replay = json.loads(cold.stdout)
    assert replay["terminal_status"] == "success"
    evaluation_event = next(row for row in replay["events"] if row["event_type"] == "how.evaluation.completed")
    assert evaluation_event["change_domain"] == "implementation/how"
    assert evaluation_event["activation_decision"] == "activated"
    assert evaluation_event["active_after"] == "ripgrep_search@1.0.0"
    assert all(row["event_schema_version"] == "1.5" for row in replay["events"])
    schema_document = json.loads((REPO / "schemas/run_event_v1_5.schema.json").read_text(encoding="utf-8"))
    assert schema_document["$id"].endswith("run-event-v1.5.schema.json")
    schema = Draft202012Validator(schema_document)
    assert all(not list(schema.iter_errors(row)) for row in replay["events"])
    trace_text = Path(replay["trace_path"]).read_text(encoding="utf-8")
    assert str(source.resolve()) not in trace_text and expected not in trace_text

    code, rolled_back = _cli(
        "rollback-understand", *args, "--implementation", "wiki_index_v1",
    )
    assert code == 0 and rolled_back["status"] == "rolled_back", rolled_back
    rollback = JsonlTraceStore(workspace).inspect_run(rolled_back["run_id"])
    assert rollback is not None and rollback["terminal_status"] == "success"
    rollback_event = next(row for row in rollback["events"] if row["event_type"] == "how.rollback.completed")
    assert rollback_event["active_before"] == "ripgrep_search@1.0.0"
    assert rollback_event["active_after"] == "wiki_index_v1"


def test_how_tie_and_evaluation_failure_are_observed_without_switching(tmp_path: Path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "wiki"
    roots.mkdir()
    source = roots / "policy.md"
    expected = "Audit control requires preserved evidence."
    source.write_text(
        f"# Document introduction\nOpening summary unrelated to the query.\n"
        f"A second introductory line.\nA third introductory line.\n{expected}\n",
        encoding="utf-8",
    )
    benchmark = [{
        "query": expected,
        "expected_source": str(source.resolve()),
        "expected_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "expected_text": expected,
    }]
    benchmark_path = tmp_path / "benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
    args = ["--workspace", str(workspace), "--wiki-root", str(roots)]
    assert _cli("acquire-ripgrep", *args)[0] == 0
    first_code, first = _cli("evolve-understand", *args, "--benchmark", str(benchmark_path), "--activate")
    assert first_code == 0 and first["active_implementation"] == "ripgrep_search@1.0.0", first
    active_before = first["active_implementation"]

    tie_code, tie = _cli("evolve-understand", *args, "--benchmark", str(benchmark_path), "--activate")
    assert tie_code == 0 and tie["active_implementation"] == active_before, tie
    tie_trace = JsonlTraceStore(workspace).inspect_run(tie["run_id"])
    assert tie_trace is not None and tie_trace["terminal_status"] == "success"
    tie_event = next(row for row in tie_trace["events"] if row["event_type"] == "how.evaluation.completed")
    assert tie_event["activation_decision"] == "candidate_not_better"
    assert tie_event["active_before"] == tie_event["active_after"] == active_before

    bad_benchmark = [dict(benchmark[0], expected_text="text absent from the source")]
    bad_path = tmp_path / "bad-benchmark.json"
    bad_path.write_text(json.dumps(bad_benchmark), encoding="utf-8")
    fail_code, failed = _cli("evolve-understand", *args, "--benchmark", str(bad_path), "--activate")
    assert fail_code == 1 and failed["evaluation"]["status"] == "fail", failed
    failure_trace = JsonlTraceStore(workspace).inspect_run(failed["run_id"])
    assert failure_trace is not None and failure_trace["terminal_status"] == "failure"
    failed_event = next(row for row in failure_trace["events"] if row["event_type"] == "how.evaluation.completed")
    assert failed_event["evaluation_status"] == "fail"
    assert failed_event["active_before"] == failed_event["active_after"] == active_before

    invalid_code, invalid_rollback = _cli(
        "rollback-understand", *args, "--implementation", "unregistered@9.9.9",
    )
    assert invalid_code == 2 and invalid_rollback["status"] == "failure", invalid_rollback
    invalid_trace = JsonlTraceStore(workspace).inspect_run(invalid_rollback["run_id"])
    assert invalid_trace is not None and invalid_trace["terminal_status"] == "failure"
    assert any(row["event_type"] == "how.operation.failed" for row in invalid_trace["events"])
    assert app_active(workspace) == active_before


def test_how_failure_redacts_untrusted_exception_code_from_trace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    gateway = CatalystGateway(workspace)

    class UnsafeFailure(RuntimeError):
        code = r"E:\private\token=not-for-trace"

    observed = gateway.workbench_how_operation(
        operation="rollback_understand",
        action=lambda: (_ for _ in ()).throw(UnsafeFailure("private details")),
        active_before="wiki_index_v1",
        active_reader=lambda: "wiki_index_v1",
    )
    assert observed["status"] == "failure"
    assert observed["error"]["code"] == "how_operation_failed"
    trace_text = JsonlTraceStore(workspace).path.read_text(encoding="utf-8")
    assert "E:\\private\\token" not in trace_text
    assert "not-for-trace" not in trace_text
    assert "private details" not in trace_text


def test_how_active_state_read_failure_still_closes_the_run(tmp_path: Path):
    workspace = tmp_path / "workspace"
    gateway = CatalystGateway(workspace)

    def unavailable_active_reader() -> str:
        raise OSError("private state path")

    observed = gateway.workbench_how_operation(
        operation="rollback_understand",
        action=lambda: {"status": "rolled_back"},
        active_before="ripgrep_search@1.0.0",
        active_reader=unavailable_active_reader,
    )
    assert observed["status"] == "failure"
    assert observed["error"]["code"] == "active_state_read_failed"
    replay = JsonlTraceStore(workspace).inspect_run(observed["run_id"])
    assert replay is not None and replay["terminal_status"] == "failure"
    failure = next(row for row in replay["events"] if row["event_type"] == "how.operation.failed")
    assert failure["active_after"] is None
    assert "private state path" not in JsonlTraceStore(workspace).path.read_text(encoding="utf-8")


def app_active(workspace: Path) -> str:
    value = json.loads((workspace / ".catalyst" / "active-understand.json").read_text(encoding="utf-8"))
    return value["active_implementation"]


def test_external_v2_keeps_same_entity_key_separate_across_enterprise_scopes(tmp_path: Path):
    roots = tmp_path / "shared-source-fixtures"
    roots.mkdir()
    source_path = roots / "org-policy.md"
    source_path.write_text(
        "# Synthetic policy\nEntity: review_owner | 质量评审负责人\n",
        encoding="utf-8",
    )
    identities = []
    for enterprise in ("enterprise-a", "enterprise-b"):
        workspace = tmp_path / enterprise
        common = _wiki_args(workspace, roots, "json", enterprise)
        code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
        assert code == 0 and staged["status"] == "success", staged
        source = staged["result"]
        quote = "Entity: review_owner | 质量评审负责人"
        submission = {
            "schema_version": "catalyst.external_candidate.v2",
            "producer_origin": "codex_external",
            "scope_id": source["scope_id"],
            "source_id": source["source_id"],
            "source_revision": source["revision"],
            "origin_document_sha256": source["revision"],
            "items": [{
                "kind": "entity", "canonical_key": "review_owner", "display_name": "质量评审负责人",
                "evidence_class": "observed_from_source", "evidence": _evidence(quote, 2),
            }],
        }
        submission_path = tmp_path / f"{enterprise}.json"
        submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")
        code, proposed = _cli(
            "ontology", "external", "submit-v2", *common,
            "--correlation-id", f"external-v2-{enterprise}", "--submission", str(submission_path),
        )
        assert code == 0 and proposed["status"] == "success", proposed
        candidate = ProjectWiki(workspace, [roots], enterprise_id=enterprise, project_id="external-v2").semantic_state()["candidates"][proposed["result"]["candidate_id"]]
        identities.append((candidate["entries"][0]["meaning_id"], candidate["entries"][0]["canonical_id"]))
    assert identities[0][0] != identities[1][0]
    assert identities[0][1] != identities[1][1]


def test_external_v2_unresolved_relation_stays_unaccepted_and_needs_review(tmp_path: Path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source_path = roots / "relation.md"
    quote = "Relation: @unknown_owner | approves | quality_gate"
    source_path.write_text(f"# Synthetic relation\n{quote}\n", encoding="utf-8")
    common = _wiki_args(workspace, roots, "json")
    code, staged = _cli("ontology", "source", "stage", *common, "--file", str(source_path))
    assert code == 0
    source = staged["result"]
    submission = {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": source["scope_id"],
        "source_id": source["source_id"],
        "source_revision": source["revision"],
        "origin_document_sha256": source["revision"],
        "items": [{
            "kind": "relation", "subject": "@unknown_owner", "predicate": "approves", "object": "quality_gate",
            "evidence_class": "inferred", "evidence": _evidence(quote, 2),
        }],
    }
    submission_path = tmp_path / "relation.json"
    submission_path.write_text(json.dumps(submission, ensure_ascii=False), encoding="utf-8")
    code, proposed = _cli(
        "ontology", "external", "submit-v2", *common,
        "--correlation-id", "external-v2-unresolved-relation", "--submission", str(submission_path),
    )
    assert code == 0, proposed
    candidate_id = proposed["result"]["candidate_id"]
    code, evaluation = _cli("ontology", "candidate", "evaluate", *common, "--candidate-id", candidate_id)
    assert code == 0 and evaluation["result"]["status"] == "needs_review", evaluation
    code, rejected = _cli(
        "ontology", "candidate", "decide", *common,
        "--candidate-id", candidate_id, "--decision", "ACCEPTED", "--reason-code", "synthetic-manager-review",
    )
    assert code == 1 and rejected["error"]["code"] == "reviewed_material_change_required", rejected
    state = ProjectWiki(workspace, [roots], enterprise_id="synthetic-enterprise", project_id="external-v2").semantic_state()
    assert state["candidates"][candidate_id]["status"] == "NEEDS_REVIEW"
    assert state["accepted_versions"] == {}
