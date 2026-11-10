from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticTransitionError, SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki
from jsonschema import Draft202012Validator
from p0_test_authority import authorize_test_operation, trusted_test_operation, verify_test_receipt


def _recorder(workspace: Path, run_id: str, *, event_schema_version="1.4") -> RunRecorder:
    recorder = RunRecorder(
        JsonlTraceStore(workspace),
        run_id=run_id,
        request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        event_schema_version=event_schema_version,
    )
    recorder.start(request_kind="phase2_test", actor="local_cli_user", component="CatalystGateway")
    return recorder


def _operation(workspace: Path, run_id: str, wiki: ProjectWiki, method: str, *args, **kwargs):
    needs_test_authority = method in {"activate", "rollback"} or (
        method == "decide" and kwargs.get("decision") == "ACCEPTED"
    )
    recorder = _recorder(workspace, run_id, event_schema_version="1.5" if needs_test_authority else "1.4")
    service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verify_test_receipt)
    try:
        authorized_kwargs = authorize_test_operation(service, method, args, kwargs)
        result = getattr(service, method)(*args, **authorized_kwargs)
        recorder.finish("success", model_calls=0)
        service.finalize_run(run_id, "success")
        return result
    except BaseException:
        if not recorder.is_finished:
            recorder.finish("failure", model_calls=0, error_owner="phase2_test")
            service.finalize_run(run_id, "failure")
        raise


def _accept(workspace: Path, wiki: ProjectWiki, source: Path, prefix: str, *, reason="reviewed_fixture"):
    proposal = _operation(workspace, f"{prefix}_propose", wiki, "propose", source, actor_origin="codex_fixture")
    evaluation = _operation(
        workspace, f"{prefix}_evaluate", wiki, "evaluate", proposal["candidate_id"], actor_origin="independent_evaluator"
    )
    decision = _operation(
        workspace,
        f"{prefix}_decide",
        wiki,
        "decide",
        proposal["candidate_id"],
        decision="ACCEPTED",
        actor_origin="manager_acceptance",
        reason_code=reason,
    )
    return proposal, evaluation, decision


def _cold_cli(repo: Path, args: list[str]) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return completed.returncode, json.loads(completed.stdout)


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_one_projectwiki_contract_keeps_source_document_claim_and_canonical_identity_distinct(tmp_path, backend):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    first_source = roots / "quality_policy.md"
    second_source = roots / "review_addendum.md"
    first_source.write_text(
        "# 质量评审管理办法\n"
        "Entity: quality_review_owner | 质量评审负责人\n"
        "Entity: release_gate | 发布放行门\n"
        "Alias: quality_review_owner | 质量审核负责人\n"
        "Relation: @quality_review_owner | approves | @release_gate\n"
        "Claim: release-duty | 质量评审负责人负责发布放行\n"
        "Claim: stable-duty | 档案管理员负责保留审批记录\n"
        "Condition: qualified_supplier | 供应商完成备案后适用\n"
        "Exception: emergency_review | 重大安全事故须进入应急评审\n",
        encoding="utf-8",
    )
    second_source.write_text(
        "# 质量评审补充说明\n"
        "Alias: quality_review_owner | 质量把关人\n"
        "Claim: release-duty | 质量评审负责人负责发布放行\n",
        encoding="utf-8",
    )
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj", backend=backend)

    first, first_eval, first_version = _accept(workspace, wiki, first_source, f"{backend}_first")
    assert first_eval["status"] == "pass"
    _operation(
        workspace,
        f"{backend}_activate_first",
        wiki,
        "activate",
        first_version["version_id"],
        actor_origin="manager_acceptance",
        expected_head_version_id=None,
    )
    second, second_eval, second_version = _accept(workspace, wiki, second_source, f"{backend}_second")
    assert second_eval["status"] == "pass"
    _operation(
        workspace,
        f"{backend}_activate_second",
        wiki,
        "activate",
        second_version["version_id"],
        actor_origin="manager_acceptance",
        expected_head_version_id=first_version["version_id"],
    )

    semantic = wiki.semantic_state()
    active = semantic["accepted_versions"][semantic["active_version_id"]]
    release = next(row for row in active["meanings"].values() if row["key"] == "release-duty")
    assert release["meaning_id"] == first["meaning_ids"][first["meaning_ids"].index(release["meaning_id"])]
    assert {evidence["source_id"] for evidence in release["evidence"]} == {
        first["source_id"], second["source_id"]
    }
    canonical_ids = {
        row["canonical_id"]
        for row in active["meanings"].values()
        if row.get("kind") in {"entity", "alias"} and row.get("canonical_key") == "quality_review_owner"
    }
    assert len(canonical_ids) == 1
    assert {row["kind"] for row in active["meanings"].values()} >= {
        "entity", "alias", "relation", "claim", "condition", "exception"
    }
    relation = next(row for row in active["meanings"].values() if row["kind"] == "relation")
    assert relation["canonical_subject_id"] in canonical_ids
    assert relation["canonical_object_id"] is not None

    source_view = _operation(
        workspace, f"{backend}_source_read", wiki, "read_knowledge", "质量评审", mode="source_discovery", actor_origin="catalyst_deterministic"
    )
    claim_view = _operation(
        workspace, f"{backend}_claim_read", wiki, "read_knowledge", "发布放行", mode="grounded_claims", actor_origin="catalyst_deterministic"
    )
    semantic_view = _operation(
        workspace, f"{backend}_semantic_read", wiki, "read_knowledge", "质量把关人 发布放行", mode="accepted_enterprise_semantics", actor_origin="catalyst_deterministic"
    )
    assert source_view["read_mode"] == "source_discovery"
    assert source_view["documents"][0]["document_id"] != source_view["documents"][0]["source_id"]
    assert claim_view["read_mode"] == "grounded_claims"
    assert all(row["authority"] == "SOURCE_GROUNDED_CANDIDATE" for row in claim_view["claims"])
    assert semantic_view["read_mode"] == "accepted_enterprise_semantics"
    assert semantic_view["version_id"] == second_version["version_id"]
    assert any(row["meaning_id"] == release["meaning_id"] for row in semantic_view["meanings"])

    other = ProjectWiki(workspace, [roots], enterprise_id="other_ent", project_id="proj", backend=backend)
    other_version_source = roots / "other_enterprise.md"
    other_version_source.write_text("# 同名主体\nEntity: quality_review_owner | 质量评审负责人\n", encoding="utf-8")
    other_proposal, _, other_accepted = _accept(workspace, other, other_version_source, f"{backend}_other")
    _operation(
        workspace,
        f"{backend}_activate_other",
        other,
        "activate",
        other_accepted["version_id"],
        actor_origin="manager_acceptance",
        expected_head_version_id=None,
    )
    other_entity = next(
        row for row in other.semantic_state()["accepted_versions"][other_accepted["version_id"]]["meanings"].values()
        if row.get("kind") == "entity"
    )
    assert other_entity["canonical_id"] not in canonical_ids


def test_source_revision_freshness_is_dependency_scoped_and_survives_history(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    first_source = roots / "primary.md"
    second_source = roots / "support.md"
    first_source.write_text(
        "# 质量制度\nEntity: reviewer | 质量评审人\nRule: 评审人负责发布审批\nClaim: release-duty | 评审人负责发布审批\nRule: 档案员负责留存记录\nClaim: archive-duty | 档案员负责留存记录\n",
        encoding="utf-8",
    )
    second_source.write_text(
        "# 补充制度\nAlias: reviewer | 质量审核人\nRule: 评审人负责发布审批\nClaim: release-duty | 评审人负责发布审批\n",
        encoding="utf-8",
    )
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    first, _, v1 = _accept(workspace, wiki, first_source, "fresh_first")
    _operation(workspace, "fresh_activate1", wiki, "activate", v1["version_id"], actor_origin="manager_acceptance", expected_head_version_id=None)
    second, _, v2 = _accept(workspace, wiki, second_source, "fresh_second")
    _operation(workspace, "fresh_activate2", wiki, "activate", v2["version_id"], actor_origin="manager_acceptance", expected_head_version_id=v1["version_id"])

    second_source.write_text(second_source.read_text(encoding="utf-8") + "\n新条款：发布审批流程待重新核定\n", encoding="utf-8")
    docs = _operation(
        workspace, "fresh_docs", wiki, "read_knowledge", "补充制度", mode="source_discovery", actor_origin="catalyst_deterministic"
    )
    assert any(row["source_id"] == second["source_id"] and row["freshness_status"] == "changed_unstaged" for row in docs["documents"])

    release = _operation(
        workspace, "fresh_release", wiki, "read_knowledge", "发布审批", mode="accepted_enterprise_semantics", actor_origin="catalyst_deterministic"
    )
    release_row = next(row for row in release["meanings"] if row["key"] == "release-duty")
    assert release_row["freshness_status"] == "partial"
    assert release["knowledge_status"] == "needs_reconciliation"
    assert {item["freshness_status"] for item in release_row["evidence"]} == {"fresh", "stale"}

    archive = _operation(
        workspace, "fresh_archive", wiki, "read_knowledge", "档案员 留存", mode="accepted_enterprise_semantics", actor_origin="catalyst_deterministic"
    )
    archive_row = next(row for row in archive["meanings"] if row["key"] == "archive-duty")
    assert archive_row["freshness_status"] == "fresh"
    assert archive["knowledge_status"] == "current"

    grounded = _operation(
        workspace, "fresh_grounded", wiki, "read_knowledge", "发布审批", mode="grounded_claims", actor_origin="catalyst_deterministic"
    )
    assert all(row["source_id"] != second["source_id"] for row in grounded["claims"])
    assert any(row["source_id"] == second["source_id"] for row in grounded["stale_claims"])


def test_reviewed_same_source_policy_change_and_sibling_head_protection(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    policy = roots / "policy.md"
    sibling = roots / "sibling.md"
    policy.write_text("# 质量抽查制度\nClaim: sample-rate | 抽查比例为百分之十\n", encoding="utf-8")
    sibling.write_text("# 配套制度\nClaim: retention | 审批记录保存五年\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")

    first, _, v1 = _accept(workspace, wiki, policy, "policy_v1")
    _operation(workspace, "policy_activate_v1", wiki, "activate", v1["version_id"], actor_origin="manager_acceptance", expected_head_version_id=None)
    policy.write_text("# 质量抽查制度 2026 修订\nClaim: sample-rate | 抽查比例为百分之十五\n", encoding="utf-8")
    revised = _operation(workspace, "policy_propose_v2", wiki, "propose", policy, actor_origin="codex_fixture")
    evaluation = _operation(workspace, "policy_eval_v2", wiki, "evaluate", revised["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "needs_review"
    assert {finding["code"] for finding in evaluation["findings"]} == {"active_meaning_conflict"}
    with pytest.raises(SemanticTransitionError, match="reviewed material change"):
        _operation(
            workspace, "policy_accept_v2_unreviewed", wiki, "decide", revised["candidate_id"],
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_fixture",
        )
    v2 = _operation(
        workspace, "policy_accept_v2", wiki, "decide", revised["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_material_change",
    )
    _operation(workspace, "sibling_stage", wiki, "stage_source", sibling, actor_origin="codex_fixture")
    sibling_proposal, _, sibling_version = _accept(workspace, wiki, sibling, "policy_sibling")
    _operation(
        workspace, "policy_activate_v2", wiki, "activate", v2["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=v1["version_id"],
    )
    with pytest.raises(SemanticTransitionError, match="expected head"):
        _operation(
            workspace, "stale_head_activation", wiki, "activate", sibling_version["version_id"],
            actor_origin="manager_acceptance", expected_head_version_id=v1["version_id"],
        )
    assert wiki.semantic_state()["active_version_id"] == v2["version_id"]
    branch = _operation(
        workspace, "explicit_branch_switch", wiki, "activate", sibling_version["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=v2["version_id"], allow_branch_switch=True,
    )
    assert branch["active_version_id"] == sibling_version["version_id"]

    rollback = _operation(
        workspace, "policy_rollback", wiki, "rollback", v1["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=sibling_version["version_id"],
    )
    assert rollback["active_version_id"] == v1["version_id"]
    trace = JsonlTraceStore(workspace).inspect_run("explicit_branch_switch")
    assert trace is not None
    activated = next(event for event in trace["events"] if event["event_type"] == "semantic.version.activated")
    assert activated["branch_switch"] is True
    assert activated["expected_head_version_id"] == v2["version_id"]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_keyed_conditions_and_exceptions_change_only_after_review_and_rollback(tmp_path, backend):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    policy = roots / "quality_policy.md"
    policy.write_text(
        "# 质量评审制度 2025\n"
        "Condition: qualified_supplier | 供应商完成备案后适用\n"
        "Exception: emergency_review | 重大安全事故需要复核\n",
        encoding="utf-8",
    )
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj", backend=backend)

    initial, initial_eval, v1 = _accept(workspace, wiki, policy, f"{backend}_condition_exception_v1")
    assert initial_eval["status"] == "pass"
    _operation(
        workspace, f"{backend}_condition_exception_activate_v1", wiki, "activate", v1["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=None,
    )

    policy.write_text(
        "# 质量评审制度 2026 修订\n"
        "Condition: qualified_supplier | 供应商通过年度复核后适用\n"
        "Exception: emergency_review | 重大安全事故可先行处置并在二十四小时内复核\n",
        encoding="utf-8",
    )
    revised = _operation(
        workspace, f"{backend}_condition_exception_propose_v2", wiki, "propose", policy,
        actor_origin="codex_fixture",
    )
    evaluation = _operation(
        workspace, f"{backend}_condition_exception_evaluate_v2", wiki, "evaluate", revised["candidate_id"],
        actor_origin="independent_evaluator",
    )
    conflicts = [finding for finding in evaluation["findings"] if finding["code"] == "active_meaning_conflict"]
    assert evaluation["status"] == "needs_review"
    expected_changed_ids = {
        row["meaning_id"] for row in wiki.semantic_state()["accepted_versions"][v1["version_id"]]["meanings"].values()
        if row["kind"] in {"condition", "exception"}
    }
    assert {finding["meaning_id"] for finding in conflicts} == expected_changed_ids
    assert len(conflicts) == 2
    assert all(finding["reviewable_material_change"] is True for finding in conflicts)
    trace = JsonlTraceStore(workspace).inspect_run(f"{backend}_condition_exception_evaluate_v2")
    assert trace is not None
    event = next(row for row in trace["events"] if row["event_type"] == "semantic.candidate.evaluated")
    assert event["finding_codes"] == "active_meaning_conflict"

    with pytest.raises(SemanticTransitionError, match="reviewed material change"):
        _operation(
            workspace, f"{backend}_condition_exception_accept_unreviewed", wiki, "decide", revised["candidate_id"],
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_fixture",
        )
    accepted = _operation(
        workspace, f"{backend}_condition_exception_accept_v2", wiki, "decide", revised["candidate_id"],
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_material_change",
    )
    activated = _operation(
        workspace, f"{backend}_condition_exception_activate_v2", wiki, "activate", accepted["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=v1["version_id"],
    )
    assert activated["active_version_id"] == accepted["version_id"]

    current = _operation(
        workspace, f"{backend}_condition_exception_query_v2", wiki, "query",
        "qualified_supplier emergency_review", actor_origin="catalyst_deterministic",
    )
    current_by_kind = {row["kind"]: row["meaning"] for row in current["meanings"]}
    assert current_by_kind["condition"] == "供应商通过年度复核后适用"
    assert current_by_kind["exception"] == "重大安全事故可先行处置并在二十四小时内复核"

    rolled_back = _operation(
        workspace, f"{backend}_condition_exception_rollback_v1", wiki, "rollback", v1["version_id"],
        actor_origin="manager_acceptance", expected_head_version_id=accepted["version_id"],
    )
    assert rolled_back["active_version_id"] == v1["version_id"]
    restored = _operation(
        workspace, f"{backend}_condition_exception_query_v1", wiki, "query",
        "qualified_supplier emergency_review", actor_origin="catalyst_deterministic",
    )
    restored_by_kind = {row["kind"]: row["meaning"] for row in restored["meanings"]}
    assert restored_by_kind["condition"] == "供应商完成备案后适用"
    assert restored_by_kind["exception"] == "重大安全事故需要复核"


def test_conflicting_cross_document_responsibility_is_never_reviewed_as_same_source_revision(tmp_path):
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    first_source = roots / "role_a.md"
    second_source = roots / "role_b.md"
    first_source.write_text("# 职责规范 A\nClaim: inspector-duty | 检查员负责最终验收\n", encoding="utf-8")
    second_source.write_text("# 职责规范 B\nClaim: inspector-duty | 质量负责人负责最终验收\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj")
    _, _, v1 = _accept(workspace, wiki, first_source, "role_a")
    _operation(workspace, "role_activate_a", wiki, "activate", v1["version_id"], actor_origin="manager_acceptance", expected_head_version_id=None)
    conflict = _operation(workspace, "role_propose_b", wiki, "propose", second_source, actor_origin="codex_fixture")
    evaluation = _operation(workspace, "role_eval_b", wiki, "evaluate", conflict["candidate_id"], actor_origin="independent_evaluator")
    assert evaluation["status"] == "needs_review"
    assert "active_meaning_conflict" in {finding["code"] for finding in evaluation["findings"]}
    with pytest.raises(SemanticTransitionError, match="reviewed material change"):
        _operation(
            workspace, "role_accept_b", wiki, "decide", conflict["candidate_id"],
            decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_material_change",
        )
    trace = JsonlTraceStore(workspace).inspect_run("role_eval_b")
    assert trace is not None
    conflict_event = next(event for event in trace["events"] if event["event_type"] == "semantic.candidate.evaluated")
    assert conflict_event["status"] == "needs_review"
    assert "active_meaning_conflict" in conflict_event["finding_codes"]
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "run_event_v1_4.schema.json").read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(schema).iter_errors(conflict_event))
    rejected = _operation(
        workspace, "role_reject_b", wiki, "decide", conflict["candidate_id"],
        decision="REJECTED", actor_origin="manager_acceptance", reason_code="cross_source_conflict",
    )
    assert rejected["status"] == "rejected"
    reject_trace = JsonlTraceStore(workspace).inspect_run("role_reject_b")
    assert reject_trace is not None
    assert any(
        event["event_type"] == "semantic.candidate.decided" and event["decision"] == "REJECTED"
        for event in reject_trace["events"]
    )
    current = _operation(
        workspace,
        "role_current_after_reject",
        wiki,
        "read_knowledge",
        "最终验收",
        mode="accepted_enterprise_semantics",
        actor_origin="catalyst_deterministic",
    )
    assert current["pending_conflicts"] == []
    assert current["knowledge_status"] == "current"


def test_document_read_receipt_drops_uncontracted_source_content_and_paths(tmp_path):
    workspace = tmp_path / "workspace"
    recorder = _recorder(workspace, "run_safe_document_receipt")
    recorder.event(
        "knowledge.document.discovered",
        scope_id="enterprise:ent/project:proj",
        read_mode="source_discovery",
        document_id="document_example",
        source_id="source_example",
        source_revision="a" * 64,
        current_revision="a" * 64,
        revision_status="current",
        freshness_status="fresh",
        status="current",
        actor_origin="catalyst_deterministic",
        raw_text="synthetic secret must not persist",
        absolute_path="C:/private/customer.md",
        arbitrary_extension={"prompt": "never persist"},
    )
    recorder.finish("success", model_calls=0)
    trace = JsonlTraceStore(workspace).inspect_run("run_safe_document_receipt")
    assert trace is not None
    event = next(row for row in trace["events"] if row["event_type"] == "knowledge.document.discovered")
    assert {"raw_text", "absolute_path", "arbitrary_extension"}.isdisjoint(event)
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "run_event_v1_4.schema.json").read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(schema).iter_errors(event))


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_fresh_cli_processes_share_read_contract_ask_trace_and_safe_event_schema(tmp_path, backend):
    repo = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "workspace"
    roots = tmp_path / "sources"
    roots.mkdir()
    source = roots / "quality.md"
    source.write_text(
        "# 质量评审职责\n"
        "Entity: reviewer | 质量评审负责人\n"
        "Alias: reviewer | 质量审核经理\n"
        "Rule: 质量评审负责人负责最终放行\n"
        "Claim: release-duty | 质量评审负责人负责最终放行\n"
        "Condition: qualified_supplier | 供应商完成备案后适用\n"
        "Exception: emergency_review | 重大安全事故须进入应急评审\n",
        encoding="utf-8",
    )
    common = [
        "--workspace", str(workspace), "--wiki-root", str(roots),
        "--enterprise-id", "ent", "--project-id", "proj", "--wiki-backend", backend,
    ]
    runs = []

    code, staged = _cold_cli(repo, ["ontology", "source", "stage", *common, "--file", str(source)])
    assert code == 0 and staged["status"] == "success", staged
    runs.append(staged)
    code, source_view = _cold_cli(repo, ["ontology", "query", *common, "--query", "质量评审", "--mode", "source_discovery"])
    assert code == 0 and source_view["result"]["documents"], source_view
    source_id = source_view["result"]["documents"][0]["source_id"]
    document_id = source_view["result"]["documents"][0]["document_id"]
    assert source_id != document_id
    runs.append(source_view)
    code, grounded = _cold_cli(repo, ["ontology", "query", *common, "--query", "最终放行", "--mode", "grounded_claims"])
    assert code == 0 and grounded["result"]["claims"], grounded
    assert grounded["result"]["claims"][0]["source_id"] == source_id
    rule_line = "Rule: 质量评审负责人负责最终放行"
    expected_span = hashlib.sha256(rule_line.encode("utf-8")).hexdigest()
    assert grounded["result"]["claims"][0]["span_sha256"] == expected_span
    assert grounded["result"]["claims"][0]["evidence_refs"][0]["span_sha256"] == expected_span
    runs.append(grounded)

    code, proposal = _cold_cli(repo, ["ontology", "candidate", "propose", *common, "--file", str(source)])
    assert code == 0 and proposal["result"]["status"] == "proposed", proposal
    runs.append(proposal)
    candidate_id = proposal["result"]["candidate_id"]
    code, evaluation = _cold_cli(repo, ["ontology", "candidate", "evaluate", *common, "--candidate-id", candidate_id])
    assert code == 0 and evaluation["result"]["status"] == "pass", evaluation
    runs.append(evaluation)
    code, denied_accept = _cold_cli(repo, [
        "ontology", "candidate", "decide", *common,
        "--candidate-id", candidate_id, "--decision", "ACCEPTED", "--reason-code", "reviewed_synthetic",
    ])
    assert code == 1 and denied_accept["error"]["code"] == "external_semantic_evaluation_required", denied_accept
    wiki = ProjectWiki(workspace, [roots], enterprise_id="ent", project_id="proj", backend=backend)
    authorized_accept = trusted_test_operation(
        workspace, wiki, f"{backend}_test_only_accept", "decide", candidate_id,
        decision="ACCEPTED", actor_origin="manager_acceptance", reason_code="reviewed_synthetic",
    )
    accepted = {"run_id": authorized_accept["run_id"], "result": authorized_accept["result"]}
    runs.append(accepted)
    version_id = accepted["result"]["version_id"]
    code, denied_activation = _cold_cli(repo, [
        "ontology", "version", "activate", *common,
        "--version-id", version_id, "--expected-head", "none",
    ])
    assert code == 1 and denied_activation["error"]["code"] == "authority_receipt_required", denied_activation
    authorized_activation = trusted_test_operation(
        workspace, wiki, f"{backend}_test_only_activate", "activate", version_id,
        actor_origin="manager_acceptance", expected_head_version_id=None,
    )
    activated = {"run_id": authorized_activation["run_id"], "result": authorized_activation["result"]}
    assert activated["result"]["active_version_id"] == version_id
    runs.append(activated)

    query = "质量审核经理 最终放行"
    code, ontology = _cold_cli(repo, ["ontology", "query", *common, "--query", query])
    assert code == 0 and ontology["result"]["version_id"] == version_id, ontology
    assert ontology["result"]["freshness_status"] == "fresh"
    runs.append(ontology)
    code, wiki_view = _cold_cli(repo, ["ontology", "wiki", *common, "--query", query])
    assert code == 0 and wiki_view["result"]["meaning_ids"] == ontology["result"]["meaning_ids"], wiki_view
    assert f"{version_id}" in wiki_view["result"]["wiki_markdown"]
    runs.append(wiki_view)

    code, ask = _cold_cli(repo, [
        "ask", "--workspace", str(workspace), "--wiki-root", str(roots),
        "--enterprise-id", "ent", "--project-id", "proj", "--wiki-backend", backend,
        "--message", query, "--offline-deterministic",
    ])
    assert code == 0 and ask["status"] == "success", ask
    assert ask["wiki"]["read_contract"]["active_version_id"] == version_id
    assert ask["wiki"]["read_contract"]["accepted_semantic_status"] == "current"
    runs.append(ask)

    validators = {}
    for version in ("1.4", "1.5"):
        schema_name = f"run_event_v{version.replace('.', '_')}.schema.json"
        schema = json.loads((repo / "schemas" / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validators[version] = Draft202012Validator(schema)
    trace_store = JsonlTraceStore(workspace)
    for run in runs:
        code, replay = _cold_cli(repo, ["inspect", "--workspace", str(workspace), "--run-id", run["run_id"]])
        assert code == 0 and replay["run_id"] == run["run_id"], replay
        trace = trace_store.inspect_run(run["run_id"])
        assert trace is not None and trace["terminal_status"] == "success"
        for event in trace["events"]:
            validator = validators[event["event_schema_version"]]
            assert not list(validator.iter_errors(event)), (run["run_id"], event)
    ask_trace = trace_store.inspect_run(ask["run_id"])
    assert ask_trace is not None
    read_modes = {
        event.get("read_mode")
        for event in ask_trace["events"]
        if event["event_type"] == "semantic.consumer.queried"
    }
    assert read_modes == {"grounded_claims", "accepted_enterprise_semantics"}
    assert any(
        event["event_type"] == "semantic.consumer.meaning_consumed"
        and event.get("source_id") == source_id
        and event.get("freshness_status") == "fresh"
        for event in ask_trace["events"]
    )


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_frozen_r6_r7_identity_pins_load_through_the_unified_reader(tmp_path, backend):
    repo = Path(__file__).resolve().parents[1]
    fixture_root = repo / "tests" / "fixtures" / "phase2_knowledge"
    pins = json.loads((fixture_root / "legacy_identity_pins.json").read_text(encoding="utf-8"))

    r6_workspace = tmp_path / "r6_workspace"
    r6_roots = tmp_path / "r6_sources"
    r6_roots.mkdir()
    r6_file = r6_roots / "alpha.md"
    r6_file.write_bytes((fixture_root / "r6_alpha.md").read_bytes())
    r6_wiki = ProjectWiki(
        r6_workspace,
        [r6_roots],
        enterprise_id="enterprise-local",
        project_id="project-alpha",
        backend=backend,
    )
    r6_stage = r6_wiki.stage_markdown(r6_file)
    assert r6_stage["scope_id"] == pins["r6"]["scope_id"]
    assert r6_stage["source_id"] == pins["r6"]["source_id"]
    assert r6_stage["revision"] == pins["r6"]["source_revision"]
    assert r6_stage["claim_ids"] == pins["r6"]["claim_ids"]

    workspace = tmp_path / "r7_workspace"
    roots = tmp_path / "r7_sources"
    roots.mkdir()
    source = roots / "guide.md"
    source.write_bytes((fixture_root / "quality_review_v1.md").read_bytes())
    old = pins["r7"]
    wiki = ProjectWiki(
        workspace,
        [roots],
        enterprise_id="review",
        project_id="phase2",
        backend=backend,
    )
    staged = wiki.stage_markdown(source)
    assert staged["source_id"] == old["source_id"]
    assert staged["revision"] == old["source_revision"]
    assert staged["claim_ids"] == old["claim_ids"]

    # The frozen R7 acceptance output did not archive its store file. Seed a
    # minimal schema-valid record from its recorded IDs and exact synthetic
    # evidence rows, then verify the current cold CLI can read those old IDs.
    decision_id = old["decision_id"]
    evaluation_id = "evaluation_legacy_identity_fixture"
    meanings = {row["meaning_id"]: row for row in old["meanings"]}
    candidate = {
        "candidate_id": old["candidate_id"],
        "scope_id": old["scope_id"],
        "source_id": old["source_id"],
        "source_revision": old["source_revision"],
        "entries": list(meanings.values()),
        "latest_evaluation_id": evaluation_id,
        "latest_decision_id": decision_id,
    }
    evaluation = {
        "evaluation_id": evaluation_id,
        "candidate_id": old["candidate_id"],
        "status": "pass",
    }
    decision = {
        "decision_id": decision_id,
        "candidate_id": old["candidate_id"],
        "evaluation_id": evaluation_id,
        "decision": "ACCEPTED",
        "version_id": old["accepted_version_id"],
    }
    accepted_version = {
        "version_id": old["accepted_version_id"],
        "scope_id": old["scope_id"],
        "candidate_id": old["candidate_id"],
        "decision_id": decision_id,
        "parent_version_id": None,
        "meanings": meanings,
    }

    def seed_legacy(state):
        state["candidates"][old["candidate_id"]] = candidate
        state["evaluations"][evaluation_id] = evaluation
        state["decisions"][decision_id] = decision
        state["accepted_versions"][old["accepted_version_id"]] = accepted_version
        state["active_version_id"] = old["accepted_version_id"]

    wiki.update_semantic_state(seed_legacy)
    common = [
        "--workspace", str(workspace), "--wiki-root", str(roots),
        "--enterprise-id", "review", "--project-id", "phase2", "--wiki-backend", backend,
    ]
    code, queried = _cold_cli(repo, [
        "ontology", "query", *common, "--query", "Reviewer source link",
        "--mode", "accepted_enterprise_semantics",
    ])
    assert code == 0 and queried["status"] == "success", queried
    result = queried["result"]
    assert result["version_id"] == old["accepted_version_id"]
    assert set(result["meaning_ids"]) == set(old["consumer_meaning_ids"])
    assert {row["source_id"] for row in result["meanings"]} == {old["source_id"]}
    assert {
        evidence["claim_id"]
        for row in result["meanings"]
        for evidence in row["evidence"]
    } <= set(old["claim_ids"])

    code, inspected = _cold_cli(repo, ["ontology", "inspect", *common])
    assert code == 0 and inspected["status"] == "success", inspected
    inspect_result = inspected["result"]
    assert old["candidate_id"] in inspect_result["candidate_ids"]
    assert old["accepted_version_id"] in inspect_result["accepted_version_ids"]
    assert inspect_result["active_version_id"] == old["accepted_version_id"]
    assert set(inspect_result["active_meaning_ids"]) == set(old["consumer_meaning_ids"])
