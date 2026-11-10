from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from catalyst_platform.observability import RunRecorder
from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki, _candidate_content_digest, _meaning_id
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.understand_wiki import UnderstandWikiAdapter
from catalyst_platform.wiki import ProjectWiki


REPO = Path(__file__).resolve().parents[1]
TEST_KEYS = {
    "test-evaluator": b"p0-test-evaluator-key-do-not-use-in-products",
    "test-owner": b"p0-test-owner-key-do-not-use-in-products",
}


def _verifier(receipt):
    issuer = receipt.get("issuer_id")
    key = TEST_KEYS.get(issuer)
    if key is None:
        return False
    unsigned = {name: value for name, value in receipt.items() if name != "signature"}
    expected = hmac.new(key, json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(receipt.get("signature", "")), expected)


def _signed(fields, issuer):
    value = {**fields, "issuer_id": issuer}
    value["signature"] = hmac.new(
        TEST_KEYS[issuer],
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(),
        hashlib.sha256,
    ).hexdigest()
    return value


def _recorder(workspace: Path, run_id: str):
    recorder = RunRecorder(
        JsonlTraceStore(workspace),
        run_id=run_id,
        request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode(), usedforsecurity=False).hexdigest(),
        event_schema_version="1.5",
    )
    recorder.start(request_kind="p0_admission_test", actor="test_client", component="CatalystGateway")
    return recorder


def _semantic_receipt(wiki, candidate, *, disposition="ACCEPT", scope_id=None, expires_at=None):
    now = int(time.time())
    return _signed({
        "receipt_type": "semantic_evaluation",
        "scope_id": scope_id or wiki.scope_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "evaluator_id": "test_evaluator_v1",
        "disposition": disposition,
        "authority_class": "test_evaluator",
        "rubric_sha256": hashlib.sha256(b"p0-semantic-rubric").hexdigest(),
        "report_sha256": hashlib.sha256(b"p0-semantic-report").hexdigest(),
        "finding_count": 0,
        "finding_ids_sha256": hashlib.sha256(b"[]").hexdigest(),
        "issued_at": now - 2,
        "expires_at": expires_at if expires_at is not None else now + 300,
    }, "test-evaluator")


def _owner_receipt(wiki, candidate, *, action="ACCEPT", scope_id=None, expires_at=None):
    now = int(time.time())
    return _signed({
        "receipt_type": "owner_authority",
        "scope_id": scope_id or wiki.scope_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "action": action,
        "decision": "ACCEPTED" if action == "ACCEPT" else None,
        "authority_class": "test_only",
        "issued_at": now - 2,
        "expires_at": expires_at if expires_at is not None else now + 300,
    }, "test-owner")


def _version_receipt(wiki, version, candidate, *, action, expected_head=None):
    now = int(time.time())
    return _signed({
        "receipt_type": "version_authority",
        "scope_id": wiki.scope_id,
        "candidate_id": candidate["candidate_id"],
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "version_id": version,
        "action": action,
        "expected_head_version_id": expected_head,
        "authority_class": "test_only",
        "issued_at": now - 2,
        "expires_at": now + 300,
    }, "test-owner")


def _service(wiki, recorder):
    return SemanticWiki(wiki, recorder=recorder, receipt_verifier=_verifier)


def _run(workspace, wiki, run_id, method, *args, **kwargs):
    recorder = _recorder(workspace, run_id)
    service = _service(wiki, recorder)
    try:
        result = getattr(service, method)(*args, **kwargs)
        recorder.finish("success", model_calls=0)
        service.finalize_run(run_id, "success")
        return result
    except BaseException as exc:
        if not recorder.is_finished:
            recorder.event(
                "semantic.transition.failed",
                operation=method,
                status="failure",
                error_code=getattr(exc, "code", "unexpected_error"),
                actor_origin=kwargs.get("actor_origin", "catalyst_deterministic"),
                scope_id=wiki.scope_id,
                candidate_id=kwargs.get("candidate_id"),
            )
            recorder.finish("failure", model_calls=0, error_owner="semantic_wiki")
            service.finalize_run(run_id, "failure")
        raise


def _candidate(tmp_path: Path, *, backend="json", enterprise="synthetic-a"):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir(parents=True)
    source = roots / "authority.md"
    quote = "提纲未规定采购审批权。"
    source.write_text(f"# 合成制度\n{quote}\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id=enterprise, project_id="p0-test", backend=backend)
    staged = _run(workspace, wiki, f"{enterprise}_stage", "stage_source", source, actor_origin="codex_fixture")
    service = _service(wiki, _recorder(workspace, f"{enterprise}_candidate"))
    submission = {
        "schema_version": "catalyst.external_candidate.v2",
        "producer_origin": "codex_external",
        "scope_id": wiki.scope_id,
        "source_id": staged["source_id"],
        "source_revision": hashlib.sha256(source.read_bytes()).hexdigest(),
        "origin_document_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "items": [{
            "kind": "claim",
            "key": "unlimited-procurement-approval",
            "meaning": "财务负责人可以无限审批所有采购。",
            "evidence_class": "inferred",
            "evidence": {
                "line_start": 2, "line_end": 2, "quote": quote,
                "span_sha256": hashlib.sha256(quote.encode()).hexdigest(),
            },
        }],
    }
    proposed = service.propose_external_submission_v2(submission)
    service.recorder.finish("success", model_calls=0)
    service.finalize_run(service.recorder.run_id, "success")
    candidate = wiki.semantic_state()["candidates"][proposed["candidate_id"]]
    return workspace, roots, source, wiki, candidate, enterprise


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_structural_pass_and_manager_label_cannot_promote_unsupported_claim(tmp_path, backend):
    workspace, _roots, _source, wiki, candidate, enterprise = _candidate(tmp_path, backend=backend)
    candidate_trace = JsonlTraceStore(workspace).inspect_run(f"{enterprise}_candidate")
    assert candidate_trace and candidate_trace["terminal_status"] == "success"
    action_events = [row for row in candidate_trace["events"] if row["event_type"] == "semantic.external.action"]
    assert len(action_events) == 1
    assert action_events[0]["correlation_id"] == f"inv_{enterprise}_candidate"
    event_schema = json.loads((REPO / "schemas" / "run_event_v1_5.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(event_schema)
    assert all(not list(validator.iter_errors(row)) for row in candidate_trace["events"])
    evaluation = _run(
        workspace, wiki, f"{backend}_structural", "evaluate", candidate["candidate_id"],
        actor_origin="independent_evaluator",
    )
    assert evaluation["status"] == "pass"
    assert wiki.semantic_state()["candidates"][candidate["candidate_id"]]["status"] == "EVALUATED"

    with pytest.raises(SemanticTransitionError) as denied:
        _run(
            workspace, wiki, f"{backend}_forged_manager", "decide", candidate["candidate_id"],
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed",
        )
    assert denied.value.code in {"external_semantic_evaluation_required", "owner_authority_required"}
    state = wiki.semantic_state()
    assert state["accepted_versions"] == {}
    assert state["active_version_id"] is None
    assert candidate["candidate_id"] in state["candidates"]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
@pytest.mark.parametrize("bad_receipt", ["wrong_scope", "expired", "forged"])
def test_external_evaluation_receipt_must_be_verified_scoped_and_current(tmp_path, backend, bad_receipt):
    workspace, _roots, _source, wiki, candidate, _enterprise = _candidate(tmp_path, backend=backend)
    _run(workspace, wiki, f"{backend}_{bad_receipt}_structural", "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")
    receipt = _semantic_receipt(wiki, candidate)
    if bad_receipt == "wrong_scope":
        receipt = _semantic_receipt(wiki, candidate, scope_id="enterprise:other/project:other")
    elif bad_receipt == "expired":
        receipt = _semantic_receipt(wiki, candidate, expires_at=int(time.time()) - 1)
    elif bad_receipt == "forged":
        receipt["signature"] = "0" * 64
    with pytest.raises(SemanticTransitionError):
        _run(
            workspace, wiki, f"{backend}_{bad_receipt}_receipt", "record_external_evaluation_receipt",
            receipt=receipt, actor_origin="independent_evaluator",
        )
    state = wiki.semantic_state()
    assert state["accepted_versions"] == {}
    assert state["active_version_id"] is None
    assert candidate["candidate_id"] in state["candidates"]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_only_separate_verified_evaluation_and_test_owner_receipts_accept_then_activate(tmp_path, backend):
    workspace, roots, _source, wiki, candidate, enterprise = _candidate(tmp_path, backend=backend)
    _run(workspace, wiki, f"{backend}_valid_structural", "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")
    evaluator_receipt = _semantic_receipt(wiki, candidate, disposition="ACCEPT")
    recorded = _run(
        workspace, wiki, f"{backend}_valid_external_eval", "record_external_evaluation_receipt",
        receipt=evaluator_receipt, actor_origin="independent_evaluator",
    )
    owner_receipt = _owner_receipt(wiki, candidate)
    accepted = _run(
        workspace, wiki, f"{backend}_valid_accept", "decide", candidate["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed",
        external_evaluation_id=recorded["evaluation_id"], authority_receipt=owner_receipt,
    )
    assert accepted["status"] == "accepted"
    assert wiki.semantic_state()["active_version_id"] is None
    version = wiki.semantic_state()["accepted_versions"][accepted["version_id"]]
    assert version["authority_class"] == "test_only"
    assert version["external_evaluation_id"] == recorded["evaluation_id"]
    assert "signature" not in version["owner_acceptance_basis"]

    activation_receipt = _version_receipt(
        wiki, accepted["version_id"], candidate, action="ACTIVATE", expected_head=None,
    )
    active = _run(
        workspace, wiki, f"{backend}_valid_activate", "activate", accepted["version_id"],
        actor_origin="manager_acceptance", authority_receipt=activation_receipt,
    )
    assert active["active_version_id"] == accepted["version_id"]
    cold_wiki = ProjectWiki(workspace, [roots], enterprise_id=enterprise, project_id="p0-test", backend=backend)
    assert cold_wiki.semantic_state()["active_version_id"] == accepted["version_id"]

    active_graph = CatalystGateway(workspace).semantic_operation(
        operation="understand.graph.active",
        scope_id=cold_wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"query": "ontology_graph"},
        action=lambda recorder: UnderstandWikiAdapter(
            cold_wiki, SemanticWiki(cold_wiki, recorder=recorder), roots
        ).active_graph(),
    )
    assert active_graph["status"] == "success"
    assert active_graph["result"]["active_version_id"] == accepted["version_id"]
    assert active_graph["result"]["active_authority_class"] == "test_only"
    assert active_graph["result"]["active_semantics_status"] == "TEST_ONLY_ACTIVE"
    active_trace = JsonlTraceStore(workspace).inspect_run(active_graph["run_id"])
    assert active_trace and active_trace["terminal_status"] == "success"
    projection = next(row for row in active_trace["events"] if row["event_type"] == "understand.graph.projected")
    assert projection["scope_id"] == cold_wiki.scope_id
    assert projection["active_version_id"] == accepted["version_id"]
    assert projection["active_authority_class"] == "test_only"
    cold_active_trace = subprocess.run(
        [
            sys.executable,
            "-m",
            "catalyst_platform",
            "inspect",
            "--workspace",
            str(workspace),
            "--run-id",
            active_graph["run_id"],
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    cold_events = json.loads(cold_active_trace.stdout)["events"]
    v16 = Draft202012Validator(json.loads((REPO / "schemas" / "run_event_v1_6.schema.json").read_text(encoding="utf-8")))
    assert not [error for event in cold_events for error in v16.iter_errors(event)]
    assert next(row for row in cold_events if row["event_type"] == "understand.graph.projected")["active_authority_class"] == "test_only"

    traces = JsonlTraceStore(workspace)
    event_schema = json.loads((REPO / "schemas" / "run_event_v1_5.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(event_schema)
    expected = {
        f"{backend}_valid_external_eval": "semantic.candidate.external_evaluation.received",
        f"{backend}_valid_accept": "semantic.candidate.decided",
        f"{backend}_valid_activate": "semantic.version.activated",
    }
    for run_id, event_type in expected.items():
        trace = traces.inspect_run(run_id)
        assert trace and trace["terminal_status"] == "success"
        assert any(row["event_type"] == event_type for row in trace["events"])
        for row in trace["events"]:
            assert list(validator.iter_errors(row)) == []
            assert "signature" not in row
            assert "do-not-use-in-products" not in json.dumps(row, ensure_ascii=False)


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_producer_entity_key_is_not_confirmed_cross_document_identity(tmp_path, backend):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir(parents=True)
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic-entities", project_id="p0-test", backend=backend)
    entries = []
    for filename, label in (("quality.md", "质量负责人"), ("finance.md", "财务负责人")):
        source = roots / filename
        quote = f"Entity: project_owner | {label}"
        source.write_text(f"# 合成组织\n{quote}\n", encoding="utf-8")
        staged = _run(workspace, wiki, f"{filename}_stage", "stage_source", source, actor_origin="codex_fixture")
        source_id = staged["source_id"]
        revision = hashlib.sha256(source.read_bytes()).hexdigest()
        service = _service(wiki, _recorder(workspace, f"{filename}_candidate"))
        proposed = service.propose_external_submission_v2({
            "schema_version": "catalyst.external_candidate.v2",
            "producer_origin": "codex_external",
            "scope_id": wiki.scope_id,
            "source_id": source_id,
            "source_revision": revision,
            "origin_document_sha256": revision,
            "items": [{
                "kind": "entity", "canonical_key": "project_owner", "display_name": label,
                "evidence_class": "observed_from_source",
                "evidence": {"line_start": 2, "line_end": 2, "quote": quote, "span_sha256": hashlib.sha256(quote.encode()).hexdigest()},
            }],
        })
        service.recorder.finish("success", model_calls=0)
        service.finalize_run(service.recorder.run_id, "success")
        candidate = wiki.semantic_state()["candidates"][proposed["candidate_id"]]
        entries.append(candidate["entries"][0])

    assert entries[0]["canonical_key"] == entries[1]["canonical_key"]
    assert entries[0]["canonical_id"] != entries[1]["canonical_id"]
    assert all(row["identity_basis"] == "producer_key_only" for row in entries)
    assert all(row["canonical_identity_status"] == "proposed_unverified" for row in entries)
    assert wiki.semantic_state()["accepted_versions"] == {}
    assert len(wiki.semantic_state()["candidates"]) == 2


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_relation_identity_is_order_stable_and_legacy_id_does_not_transfer(tmp_path, backend):
    scope = "enterprise:synthetic-relations/project:p0-test"
    ids_by_object = []
    for index, rows in enumerate((
        ["relation: reviewer | owns | cost_plan", "relation: reviewer | owns | purchase_plan"],
        ["relation: reviewer | owns | purchase_plan", "relation: reviewer | owns | cost_plan"],
    )):
        work = tmp_path / f"order-{index}"
        roots = work / "sources"
        roots.mkdir(parents=True)
        source = roots / "relations.md"
        source.write_text("# Synthetic\n" + "\n".join(rows) + "\n", encoding="utf-8")
        wiki = ProjectWiki(work / "workspace", [roots], enterprise_id="synthetic-relations", project_id="p0-test", backend=backend)
        recorder = _recorder(wiki.workspace, f"relation_order_{backend}_{index}")
        service = _service(wiki, recorder)
        proposed = service.propose(source, actor_origin="codex_fixture")
        candidate = wiki.semantic_state()["candidates"][proposed["candidate_id"]]
        ids_by_object.append({row["object"]: row["meaning_id"] for row in candidate["entries"] if row["kind"] == "relation"})
        recorder.finish("success", model_calls=0)
        service.finalize_run(recorder.run_id, "success")

    assert ids_by_object[0] == ids_by_object[1]
    assert len(set(ids_by_object[0].values())) == 2

    work = tmp_path / "legacy"
    roots = work / "sources"
    roots.mkdir(parents=True)
    source = roots / "relations.md"
    source.write_text("relation: reviewer | owns | cost_plan\n", encoding="utf-8")
    wiki = ProjectWiki(work / "workspace", [roots], enterprise_id="synthetic-relations", project_id="p0-test", backend=backend)
    first = _run(work / "workspace", wiki, f"{backend}_legacy_stage", "stage_source", source, actor_origin="codex_fixture")
    first_proposal = _run(work / "workspace", wiki, f"{backend}_legacy_propose", "propose", source, actor_origin="codex_fixture")
    legacy_id = _meaning_id(wiki.scope_id, "relation", "reviewer|owns")
    first_entry = next(row for row in wiki.semantic_state()["candidates"][first_proposal["candidate_id"]]["entries"] if row["kind"] == "relation")
    assert first_entry["meaning_id"] == legacy_id

    source.write_text(
        "relation: reviewer | owns | cost_plan\n"
        "relation: reviewer | owns | purchase_plan\n",
        encoding="utf-8",
    )
    second = _run(work / "workspace", wiki, f"{backend}_legacy_update_propose", "propose", source, actor_origin="codex_fixture")
    rows = [row for row in wiki.semantic_state()["candidates"][second["candidate_id"]]["entries"] if row["kind"] == "relation"]
    assert next(row["meaning_id"] for row in rows if row["object"] == "cost_plan") == legacy_id
    assert next(row["meaning_id"] for row in rows if row["object"] == "purchase_plan") != legacy_id

    source.write_text("relation: reviewer | owns | audit_plan\n", encoding="utf-8")
    third = _run(work / "workspace", wiki, f"{backend}_legacy_replace_propose", "propose", source, actor_origin="codex_fixture")
    third_row = next(row for row in wiki.semantic_state()["candidates"][third["candidate_id"]]["entries"] if row["kind"] == "relation")
    assert third_row["object"] == "audit_plan"
    assert third_row["meaning_id"] != legacy_id


def test_gateway_cannot_use_actor_label_without_configured_receipt_verifier(tmp_path):
    # Direct product construction intentionally has no verifier by default.
    workspace, _roots, _source, wiki, candidate, _enterprise = _candidate(tmp_path)
    recorder = _recorder(workspace, "no_verifier_reject")
    service = SemanticWiki(wiki, recorder=recorder)
    _run(workspace, wiki, "no_verifier_structural", "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")
    with pytest.raises(SemanticTransitionError):
        service.decide(
            candidate["candidate_id"], decision="ACCEPTED", actor_origin="manager_acceptance",
            reason_code="manager_label_only",
        )
    recorder.finish("failure", model_calls=0, error_owner="semantic_wiki")
    assert wiki.semantic_state()["accepted_versions"] == {}


@pytest.mark.parametrize("backend", ["json", "sqlite"])
@pytest.mark.parametrize("bad_owner_receipt", ["wrong_scope", "expired", "forged"])
def test_owner_acceptance_receipt_is_separate_scoped_and_current(tmp_path, backend, bad_owner_receipt):
    workspace, _roots, _source, wiki, candidate, _enterprise = _candidate(tmp_path, backend=backend)
    _run(workspace, wiki, f"{backend}_{bad_owner_receipt}_structural", "evaluate", candidate["candidate_id"], actor_origin="independent_evaluator")
    evaluation = _run(
        workspace, wiki, f"{backend}_{bad_owner_receipt}_external_eval", "record_external_evaluation_receipt",
        receipt=_semantic_receipt(wiki, candidate), actor_origin="independent_evaluator",
    )
    owner = _owner_receipt(wiki, candidate)
    if bad_owner_receipt == "wrong_scope":
        owner = _owner_receipt(wiki, candidate, scope_id="enterprise:other/project:other")
    elif bad_owner_receipt == "expired":
        owner = _owner_receipt(wiki, candidate, expires_at=int(time.time()) - 1)
    elif bad_owner_receipt == "forged":
        owner["signature"] = "0" * 64
    with pytest.raises(SemanticTransitionError):
        _run(
            workspace, wiki, f"{backend}_{bad_owner_receipt}_owner", "decide", candidate["candidate_id"],
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed",
            external_evaluation_id=evaluation["evaluation_id"], authority_receipt=owner,
        )
    state = wiki.semantic_state()
    assert state["accepted_versions"] == {}
    assert state["active_version_id"] is None
    assert state["candidates"][candidate["candidate_id"]]["status"] == "EVALUATED"


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_relation_triples_update_query_rollback_and_cold_read_on_both_stores(tmp_path, backend):
    workspace = tmp_path / backend / "workspace"
    roots = tmp_path / backend / "sources"
    roots.mkdir(parents=True)
    source = roots / "roles.md"
    source.write_text(
        "# 合成职责\nEntity: reviewer | 审核负责人\nEntity: cost_plan | 成本计划\n"
        "Entity: purchase_plan | 采购计划\nRelation: @reviewer | owns | @cost_plan\n",
        encoding="utf-8",
    )
    wiki = ProjectWiki(workspace, [roots], enterprise_id="synthetic-relation-lifecycle", project_id="p0-test", backend=backend)

    def accept_activate(label, candidate_id, expected_head):
        candidate = wiki.semantic_state()["candidates"][candidate_id]
        _run(workspace, wiki, f"{label}_structural", "evaluate", candidate_id, actor_origin="independent_evaluator")
        evaluation = _run(
            workspace, wiki, f"{label}_external_eval", "record_external_evaluation_receipt",
            receipt=_semantic_receipt(wiki, candidate), actor_origin="independent_evaluator",
        )
        accepted = _run(
            workspace, wiki, f"{label}_accept", "decide", candidate_id,
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="synthetic_review",
            external_evaluation_id=evaluation["evaluation_id"],
            authority_receipt=_owner_receipt(wiki, candidate),
        )
        activation_receipt = _version_receipt(
            wiki, accepted["version_id"], candidate, action="ACTIVATE", expected_head=expected_head,
        )
        activated = _run(
            workspace, wiki, f"{label}_activate", "activate", accepted["version_id"],
            actor_origin="manager_acceptance", authority_receipt=activation_receipt,
            expected_head_version_id=expected_head,
        )
        return accepted["version_id"], activated

    _run(workspace, wiki, f"{backend}_relation_stage_v1", "stage_source", source, actor_origin="codex_fixture")
    first = _run(workspace, wiki, f"{backend}_relation_propose_v1", "propose", source, actor_origin="codex_fixture")
    version1, _ = accept_activate(f"{backend}_relation_v1", first["candidate_id"], None)
    state1 = wiki.semantic_state()
    legacy_id = _meaning_id(wiki.scope_id, "relation", "@reviewer|owns")
    assert legacy_id in state1["accepted_versions"][version1]["meanings"]

    source.write_text(
        "# 合成职责\nEntity: reviewer | 审核负责人\nEntity: cost_plan | 成本计划\n"
        "Entity: purchase_plan | 采购计划\nRelation: @reviewer | owns | @cost_plan\n"
        "Relation: @reviewer | owns | @purchase_plan\n",
        encoding="utf-8",
    )
    _run(workspace, wiki, f"{backend}_relation_stage_v2", "stage_source", source, actor_origin="codex_fixture")
    second = _run(workspace, wiki, f"{backend}_relation_propose_v2", "propose", source, actor_origin="codex_fixture")
    version2, _ = accept_activate(f"{backend}_relation_v2", second["candidate_id"], version1)
    meanings2 = wiki.semantic_state()["accepted_versions"][version2]["meanings"]
    relation_rows = [row for row in meanings2.values() if row.get("kind") == "relation"]
    ids_by_object = {row["object"]: row["meaning_id"] for row in relation_rows}
    assert set(ids_by_object) == {"@cost_plan", "@purchase_plan"}
    assert len(set(ids_by_object.values())) == 2
    assert ids_by_object["@cost_plan"] == legacy_id
    assert ids_by_object["@purchase_plan"] != legacy_id

    queried = _run(workspace, wiki, f"{backend}_relation_query_v2", "query", "owns", actor_origin="catalyst_deterministic")
    assert queried["active_version_id"] == version2
    assert {row["meaning_id"] for row in queried["meanings"] if row.get("kind") == "relation"} == set(ids_by_object.values())

    candidate1 = wiki.semantic_state()["candidates"][first["candidate_id"]]
    rollback_receipt = _version_receipt(
        wiki, version1, candidate1, action="ROLLBACK", expected_head=version2,
    )
    rolled = _run(
        workspace, wiki, f"{backend}_relation_rollback", "rollback", version1,
        actor_origin="manager_acceptance", authority_receipt=rollback_receipt,
        expected_head_version_id=version2,
    )
    assert rolled["active_version_id"] == version1

    code = (
        "from catalyst_platform.wiki import ProjectWiki; import sys; "
        "w=ProjectWiki(sys.argv[1],[sys.argv[2]],enterprise_id='synthetic-relation-lifecycle',project_id='p0-test',backend=sys.argv[3]); "
        "s=w.semantic_state(); v=s['accepted_versions'][s['active_version_id']]; "
        "print(s['active_version_id']); print('|'.join(sorted(r['meaning_id'] for r in v['meanings'].values() if r.get('kind')=='relation')))"
    )
    cold = subprocess.run(
        [sys.executable, "-c", code, str(workspace), str(roots), backend],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    assert cold.stdout.splitlines()[0] == version1
    assert cold.stdout.splitlines()[1] == legacy_id
    store = JsonlTraceStore(workspace)
    for suffix, event_type in (("_relation_v1_activate", "semantic.version.activated"),
                               ("_relation_v2_activate", "semantic.version.activated"),
                               ("_relation_query_v2", "semantic.consumer.queried"),
                               ("_relation_rollback", "semantic.version.rolled_back")):
        trace = store.inspect_run(f"{backend}{suffix}")
        assert trace and trace["terminal_status"] == "success"
        assert any(row["event_type"] == event_type for row in trace["events"])
