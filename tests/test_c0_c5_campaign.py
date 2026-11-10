from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki
from p0_test_authority import authorize_test_operation, verify_test_receipt


SYNTHETIC_SOURCE = (
    "# 合成质量评审流程\n"
    "Entity: quality_owner | 质量评审负责人\n"
    "Entity: release_board | 发布审查委员会\n"
    "Entity: safety_board | 安全评审委员会\n"
    "Alias: quality_owner | 质量把关人\n"
    "Relation: @quality_owner | approves | @release_board\n"
    "Relation: @quality_owner | escalates_to | @safety_board\n"
    "Condition: package_ready | 资料齐全并完成校验后适用\n"
    "Exception: emergency_case | 紧急事故转应急评审\n"
)


def _operation(workspace: Path, run_id: str, wiki: ProjectWiki, method: str, *args, **kwargs):
    recorder = RunRecorder(
        JsonlTraceStore(workspace),
        run_id=run_id,
        request_id=f"req_{run_id}",
        invocation_id=f"inv_{run_id}",
        trace_id=hashlib.md5(run_id.encode("utf-8"), usedforsecurity=False).hexdigest(),
        correlation_id="c0-c5-synthetic-campaign",
        event_schema_version="1.5",
    )
    recorder.start(request_kind=f"campaign_{method}", actor="test_client", component="CatalystGateway")
    service = SemanticWiki(wiki, recorder=recorder, receipt_verifier=verify_test_receipt)
    authorized = authorize_test_operation(service, method, args, kwargs)
    result = getattr(service, method)(*args, **authorized)
    recorder.finish("success", model_calls=0)
    service.finalize_run(run_id, "success")
    return result


def _accepted_version(workspace: Path, wiki: ProjectWiki, source: Path, prefix: str, expected_head=None):
    proposal = _operation(workspace, f"{prefix}_propose", wiki, "propose", source, actor_origin="codex_fixture")
    evaluation = _operation(
        workspace,
        f"{prefix}_evaluate",
        wiki,
        "evaluate",
        proposal["candidate_id"],
        actor_origin="independent_evaluator",
    )
    assert evaluation["status"] == "pass"
    decision = _operation(
        workspace,
        f"{prefix}_decide",
        wiki,
        "decide",
        proposal["candidate_id"],
        decision="ACCEPTED",
        actor_origin="manager_acceptance",
        reason_code="isolated_synthetic_test",
    )
    activated = _operation(
        workspace,
        f"{prefix}_activate",
        wiki,
        "activate",
        decision["version_id"],
        actor_origin="manager_acceptance",
        expected_head_version_id=expected_head,
    )
    return proposal, decision, activated


def _seed_workspace(tmp_path: Path, backend: str, source_text: str = SYNTHETIC_SOURCE):
    workspace = tmp_path / backend / "workspace"
    source_root = tmp_path / backend / "sources"
    source_root.mkdir(parents=True)
    source = source_root / "synthetic_quality.md"
    source.write_text(source_text, encoding="utf-8")
    wiki = ProjectWiki(workspace, [source_root], enterprise_id="synthetic", project_id="quality", backend=backend)
    _proposal, accepted, activated = _accepted_version(workspace, wiki, source, f"{backend}_v1")
    return workspace, source_root, source, wiki, accepted["version_id"], activated["active_version_id"]


def _cli(repo: Path, args: list[str]) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if not completed.stdout.strip():
        return completed.returncode, {"stderr": completed.stderr}
    return completed.returncode, json.loads(completed.stdout)


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_relation_expansion_uses_exact_entity_ids_and_leaves_unlinked_applicability_unknown(tmp_path, backend):
    workspace, _source_root, _source, wiki, version_id, _active = _seed_workspace(tmp_path, backend)
    result = _operation(workspace, f"{backend}_relations", wiki, "resolve_relations", "质量把关人", actor_origin="catalyst_deterministic")

    assert result["status"] == "resolved"
    assert result["version_id"] == version_id
    assert len(result["entities"]) == 1
    assert {row["predicate"] for row in result["relations"]} == {"approves", "escalates_to"}
    assert len({row["object_id"] for row in result["relations"]}) == 2
    assert all(row["evidence"] and row["freshness_status"] == "fresh" for row in result["relations"])
    assert {row["kind"] for row in result["unlinked_applicability"]} == {"condition", "exception"}
    assert result["applicability_status"] == "unknown"
    assert "condition_exception_linkage_unavailable" in result["warnings"]
    relation_trace = JsonlTraceStore(workspace).inspect_run(f"{backend}_relations")
    assert relation_trace and relation_trace["terminal_status"] == "success"
    assert any(
        event["event_type"] == "semantic.consumer.queried" and event["read_mode"] == "relation_expansion"
        for event in relation_trace["events"]
    )

    unknown = _operation(workspace, f"{backend}_unknown", wiki, "resolve_relations", "不存在的主体", actor_origin="catalyst_deterministic")
    assert unknown["status"] == "unknown"
    assert unknown["relations"] == []


def test_graph_is_deterministic_across_json_and_sqlite_and_candidate_is_not_exposed(tmp_path):
    outputs = []
    for backend in ("json", "sqlite"):
        workspace, _roots, source, wiki, version_id, _active = _seed_workspace(tmp_path, backend)
        graph = _operation(workspace, f"{backend}_graph", wiki, "ontology_graph", actor_origin="catalyst_deterministic")
        assert graph["schema"] == "catalyst.ontology_graph.v0.1"
        assert graph["version_id"] == version_id
        assert graph["candidate_meanings_included"] is False
        assert graph["source_index"]
        assert any(edge["type"] == "relation" for edge in graph["edges"])
        assert any(edge["type"] == "supported_by" for edge in graph["edges"])
        assert "condition_exception_linkage_unavailable" in graph["warnings"]

        source.write_text(SYNTHETIC_SOURCE + "Relation: @quality_owner | audits | @release_board\n", encoding="utf-8")
        proposal = _operation(workspace, f"{backend}_pending_proposal", wiki, "propose", source, actor_origin="codex_fixture")
        pending_graph = _operation(workspace, f"{backend}_pending_graph", wiki, "ontology_graph", actor_origin="catalyst_deterministic")
        assert pending_graph["version_id"] == version_id
        assert len([edge for edge in pending_graph["edges"] if edge["type"] == "relation"]) == 2
        assert proposal["candidate_id"] not in json.dumps(pending_graph, ensure_ascii=False)
        outputs.append(graph)

    assert outputs[0] == outputs[1]


def test_relation_expansion_returns_ambiguous_for_same_label_with_distinct_ids(tmp_path):
    duplicate_label_source = (
        "# 合成同名实体\n"
        "Entity: owner_alpha | 同名角色\n"
        "Entity: owner_beta | 同名角色\n"
        "Relation: @owner_alpha | escalates_to | @owner_beta\n"
    )
    workspace, _source_root, _source, wiki, _version_id, _active = _seed_workspace(
        tmp_path, "json", duplicate_label_source,
    )
    result = _operation(
        workspace,
        "ambiguous_entity_read",
        wiki,
        "resolve_relations",
        "同名角色",
        actor_origin="catalyst_deterministic",
    )
    assert result["status"] == "ambiguous"
    assert result["relations"] == []
    assert result["warnings"] == ["entity_identity_ambiguous"]


def test_graph_reports_limit_truncation(tmp_path):
    workspace, _source_root, _source, wiki, version_id, _active = _seed_workspace(tmp_path, "json")
    result = _operation(
        workspace,
        "bounded_graph_read",
        wiki,
        "ontology_graph",
        actor_origin="catalyst_deterministic",
        limit=1,
    )
    assert result["version_id"] == version_id
    assert result["truncated"] is True
    assert "graph_truncated" in result["warnings"]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_graph_cli_cold_replay_pins_versions_and_traces_only_safe_evidence(tmp_path, backend):
    repo = Path(__file__).resolve().parents[1]
    workspace, source_root, source, wiki, v1, _active = _seed_workspace(tmp_path, backend)
    source.write_text(SYNTHETIC_SOURCE + "Relation: @quality_owner | audits | @release_board\n", encoding="utf-8")
    _proposal, accepted_v2, activated_v2 = _accepted_version(workspace, wiki, source, f"{backend}_v2", expected_head=v1)

    args = [
        "ontology", "graph", "--workspace", str(workspace), "--wiki-root", str(source_root),
        "--enterprise-id", "synthetic", "--project-id", "quality", "--wiki-backend", backend,
        "--actor-origin", "catalyst_deterministic", "--correlation-id", "c0-c5-synthetic-campaign",
    ]
    code, latest = _cli(repo, args)
    assert code == 0
    assert latest["result"]["version_id"] == accepted_v2["version_id"]
    assert len([edge for edge in latest["result"]["edges"] if edge["type"] == "relation"]) == 3

    pinned_code, pinned = _cli(repo, [*args, "--version-id", v1])
    assert pinned_code == 0
    assert pinned["result"]["version_id"] == v1
    assert len([edge for edge in pinned["result"]["edges"] if edge["type"] == "relation"]) == 2
    pinned_inspect_code, pinned_inspected = _cli(
        repo,
        ["inspect", "--workspace", str(workspace), "--run-id", pinned["run_id"]],
    )
    assert pinned_inspect_code == 0
    pinned_query = next(
        event for event in pinned_inspected["events"] if event["event_type"] == "semantic.consumer.queried"
    )
    assert pinned_query["version_id"] == v1
    assert pinned_query["active_version_id"] == accepted_v2["version_id"]

    inspect_code, inspected = _cli(repo, ["inspect", "--workspace", str(workspace), "--run-id", latest["run_id"]])
    assert inspect_code == 0
    assert inspected and inspected["terminal_status"] == "success"
    semantic_events = [event for event in inspected["events"] if event["event_type"].startswith("semantic.consumer")]
    assert semantic_events
    assert {event["event_schema_version"] for event in inspected["events"]} == {"1.5"}
    assert all(event.get("correlation_id") == "c0-c5-synthetic-campaign" for event in inspected["events"])
    assert all(str(source_root) not in json.dumps(event, ensure_ascii=False) for event in inspected["events"])
    schema = json.loads((repo / "schemas" / "run_event_v1_5.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for event in inspected["events"]:
        assert not list(validator.iter_errors(event))

    rolled = _operation(
        workspace,
        f"{backend}_rollback_v1",
        wiki,
        "rollback",
        v1,
        actor_origin="manager_acceptance",
        expected_head_version_id=activated_v2["active_version_id"],
    )
    assert rolled["active_version_id"] == v1
    cold_code, cold = _cli(repo, args)
    assert cold_code == 0
    assert cold["result"]["version_id"] == v1
    assert cold["result"]["freshness_status"] == "stale"
    assert "stale_source_evidence" in cold["result"]["warnings"]


def test_relations_cli_resolves_exact_alias_and_cold_trace_is_valid(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    workspace, source_root, _source, wiki, version_id, _active = _seed_workspace(tmp_path, "json")
    args = [
        "ontology", "relations", "--entity", "质量把关人", "--workspace", str(workspace),
        "--wiki-root", str(source_root), "--enterprise-id", "synthetic", "--project-id", "quality",
        "--wiki-backend", "json", "--actor-origin", "catalyst_deterministic",
        "--correlation-id", "c0-c5-synthetic-campaign",
    ]
    code, response = _cli(repo, args)
    assert code == 0
    assert response["result"]["status"] == "resolved"
    assert response["result"]["version_id"] == version_id
    assert len(response["result"]["relations"]) == 2
    assert {row["predicate"] for row in response["result"]["relations"]} == {"approves", "escalates_to"}
    assert {row["kind"] for row in response["result"]["unlinked_applicability"]} == {"condition", "exception"}
    assert response["result"]["applicability_status"] == "unknown"

    inspect_code, inspected = _cli(repo, ["inspect", "--workspace", str(workspace), "--run-id", response["run_id"]])
    assert inspect_code == 0
    assert inspected["terminal_status"] == "success"
    assert any(
        event["event_type"] == "semantic.consumer.queried" and event["read_mode"] == "relation_expansion"
        for event in inspected["events"]
    )
    assert {event["event_schema_version"] for event in inspected["events"]} == {"1.5"}
    schema = json.loads((repo / "schemas" / "run_event_v1_5.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for event in inspected["events"]:
        assert not list(validator.iter_errors(event))
        assert str(source_root) not in json.dumps(event, ensure_ascii=False)
