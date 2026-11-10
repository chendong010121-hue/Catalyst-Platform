from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.understand_wiki import UnderstandWikiAdapter, UnderstandWikiError


FIXTURE = Path(__file__).parent / "fixtures" / "u0_understand_handoff"


def _load_result() -> dict:
    return json.loads((FIXTURE / "SemanticCandidate.json").read_text(encoding="utf-8-sig"))


def _workspace(tmp_path: Path, backend: str = "json", enterprise_id: str = "synthetic"):
    root = tmp_path / "sources"
    shutil.copytree(FIXTURE / "inputs", root)
    wiki = ProjectWiki(
        tmp_path / "workspace",
        [root],
        enterprise_id=enterprise_id,
        project_id="monthly",
        backend=backend,
    )
    gateway = CatalystGateway(tmp_path / "workspace")
    return root, wiki, gateway


def _submit(root: Path, wiki: ProjectWiki, gateway: CatalystGateway, result=None):
    frozen = result if result is not None else _load_result()
    return gateway.semantic_operation(
        operation="understand.candidate.submit",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"contract_version": "catalyst.understand_handoff.v1"},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).submit(frozen, declared_scope_id=wiki.scope_id),
    )


def test_frozen_understanding_handoff_preserves_all_producer_data_and_source_identity(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    original = _load_result()

    receipt = _submit(root, wiki, gateway, original)

    assert receipt["status"] == "success"
    candidate_id = receipt["result"]["candidate_id"]
    state = wiki.semantic_state()
    candidate = state["candidates"][candidate_id]
    assert candidate["candidate_type"] == "understand_handoff.v1"
    assert candidate["understanding_result"] == original
    assert candidate["authority"] == "CANDIDATE_ONLY"
    assert candidate["producer_identity_status"] == "DECLARED_UNVERIFIED"
    assert candidate["producer_origin"] == original["semantic_candidate"]["producer_origin"]
    assert candidate["producer_origin"] != "codex_external"
    assert len(candidate["source_bindings"]) == 2
    assert len(candidate["understanding_result"]["evidence_refs"]) == 7
    assert state["active_version_id"] is None
    assert candidate.get("latest_decision_id") is None
    handoff_schema = json.loads((Path(__file__).parents[1] / "schemas" / "understand_handoff_v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(handoff_schema).validate(candidate)


def test_candidate_result_query_returns_safe_summary_and_preserves_full_frozen_payload(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    original = _load_result()
    candidate_id = _submit(root, wiki, gateway, original)["result"]["candidate_id"]

    outcome = gateway.semantic_operation(
        operation="understand.consumer.result",
        scope_id=wiki.scope_id,
        actor_origin="manager_acceptance",  # A label is not content-read authority.
        input_value={"candidate_id": candidate_id},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).result(candidate_id),
    )

    projection = outcome["result"]
    stored = wiki.semantic_state()["candidates"][candidate_id]
    assert projection["schema"] == "catalyst.understand_candidate_result_summary.v1"
    assert projection["authority"] == "CANDIDATE_ONLY"
    assert projection["raw_result_included"] is False
    assert projection["source_text_included"] is False
    assert projection["full_result_access"] == "DENIED_UNTIL_TRUSTED_CONTENT_AUTHORIZATION"
    assert "understanding_result" not in projection
    assert stored["understanding_result"] == original  # Storage remains lossless.
    assert projection["understanding_result_sha256"] == stored["understanding_result_sha256"]
    events = gateway.inspect_run(outcome["run_id"])["events"]
    assert any(event.get("event_type") == "understand.consumer.queried" and event.get("query_kind") == "result" for event in events)
    public_text = json.dumps({"result": projection, "events": events}, ensure_ascii=False)
    assert str(root.resolve()) not in public_text
    assert all(ref["quote"] not in public_text for ref in original["evidence_refs"])

    cli = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", "ontology", "understand", "result",
         "--workspace", str(tmp_path / "workspace"), "--wiki-root", str(root),
         "--enterprise-id", "synthetic", "--project-id", "monthly", "--wiki-backend", "json",
         "--actor-origin", "manager_acceptance", "--candidate-id", candidate_id],
        cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True, encoding="utf-8",
    )
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["result"]["raw_result_included"] is False
    assert all(ref["quote"] not in cli.stdout for ref in original["evidence_refs"])
    cold_inspect = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", "inspect", "--workspace", str(tmp_path / "workspace"),
         "--run-id", cli_payload["run_id"]],
        cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True, encoding="utf-8",
    )
    trace_text = cold_inspect.stdout
    assert all(ref["quote"] not in trace_text for ref in original["evidence_refs"])
    assert str(root.resolve()) not in trace_text

def test_candidate_graph_is_explicit_non_authoritative_and_never_invents_links(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    receipt = _submit(root, wiki, gateway)
    candidate_id = receipt["result"]["candidate_id"]
    graph_receipt = gateway.semantic_operation(
        operation="understand.graph.candidate",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"candidate_id": candidate_id},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).candidate_graph(candidate_id),
    )

    graph = graph_receipt["result"]
    assert graph["view"] == "candidate"
    assert graph["authority"] == "EXTERNAL_CANDIDATE_NOT_ACTIVE"
    assert graph["candidate_status"] == "PROPOSED"
    assert len([n for n in graph["nodes"] if n["type"] == "source_revision"]) == 2
    assert len([n for n in graph["nodes"] if n["type"] == "evidence"]) == 7
    relation_nodes = [n for n in graph["nodes"] if n["type"] == "relation"]
    assert relation_nodes
    assert all({"subject", "predicate", "object"} <= set(n) for n in relation_nodes)
    assert all(n["endpoint_identity_status"] == "UNRESOLVED" for n in relation_nodes)
    assert not [e for e in graph["edges"] if e["type"] in {"subject_entity", "object_entity"}]
    assert not [e for e in graph["edges"] if e["type"] == "applies_to_relation"]
    assert "condition_exception_linkage_unavailable" in graph["warnings"]
    assert len([n for n in graph["nodes"] if n["type"] == "unknown"]) == 3
    serialized = json.dumps(graph, ensure_ascii=False)
    assert str(root.resolve()) not in serialized
    assert '"quote"' not in serialized


def test_candidate_with_multiple_relation_objects_and_evidence_refs_is_lossless(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    relation = next(row for row in result["semantic_candidate"]["items"] if row["kind"] == "relation")
    second = dict(relation)
    second.update({"item_id": "item_relation_second_object", "object": "预算部", "key": "经营分析部:requests_data_from:预算部"})
    result["semantic_candidate"]["items"].append(second)
    unknown = next(row for row in result["semantic_candidate"]["items"] if row["kind"] == "unknown")
    unknown["evidence_refs"] = [
        result["evidence_refs"][1]["evidence_id"],
        result["evidence_refs"][3]["evidence_id"],
    ]

    candidate_id = _submit(root, wiki, gateway, result)["result"]["candidate_id"]
    candidate = wiki.semantic_state()["candidates"][candidate_id]
    relation_items = [row for row in candidate["understanding_result"]["semantic_candidate"]["items"] if row["kind"] == "relation"]
    assert len(relation_items) == 2
    assert {row["object"] for row in relation_items} == {"财务部", "预算部"}
    assert len(unknown["evidence_refs"]) == 2


def test_explicit_condition_relation_binding_is_used_without_inference(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    relation = next(row for row in result["semantic_candidate"]["items"] if row["kind"] == "relation")
    condition = next(row for row in result["semantic_candidate"]["items"] if row["kind"] == "condition")
    condition["relation_item_id"] = relation["item_id"]
    candidate_id = _submit(root, wiki, gateway, result)["result"]["candidate_id"]
    graph = gateway.semantic_operation(
        operation="understand.graph.candidate",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"candidate_id": candidate_id},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).candidate_graph(candidate_id),
    )["result"]
    assert any(edge["type"] == "applies_to_relation" and edge["target"] == f"understand-item:{relation['item_id']}" for edge in graph["edges"])


def test_line_range_locator_resolves_against_exact_source_bytes(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    ref = result["evidence_refs"][0]
    lines = (root / "monthly_rules.md").read_text(encoding="utf-8-sig").splitlines()
    ref["locator"] = "line:1-2"
    ref["quote"] = "\n".join(lines[:2])
    ref["span_sha256"] = hashlib.sha256(ref["quote"].encode("utf-8")).hexdigest()
    candidate_id = _submit(root, wiki, gateway, result)["result"]["candidate_id"]
    evidence_id = ref["evidence_id"]
    resolved = gateway.semantic_operation(
        operation="understand.evidence.lookup",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"candidate_id": candidate_id, "evidence_id": evidence_id},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).evidence(candidate_id, evidence_id),
    )["result"]
    assert resolved["status"] == "RESOLVED"
    assert resolved["line_range"] == [1, 2]


def test_opaque_producer_revision_is_preserved_separately_from_wiki_content_revision(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    for source in result["source_inventory"]:
        source["source_revision"] = "rev-2026-10-18-a"
    for evidence in result["evidence_refs"]:
        evidence["source_revision"] = "rev-2026-10-18-a" if evidence["source_id"] == result["source_inventory"][0]["source_id"] else "rev-2026-10-18-b"
    result["source_inventory"][1]["source_revision"] = "rev-2026-10-18-b"

    receipt = _submit(root, wiki, gateway, result)
    candidate = wiki.semantic_state()["candidates"][receipt["result"]["candidate_id"]]
    assert candidate["mapping_status"] == "COMPLETE"
    assert candidate["source_bindings"][0]["source_revision"] == "rev-2026-10-18-a"
    assert candidate["source_bindings"][0]["wiki_source_revision"] == candidate["source_bindings"][0]["source_sha256"]


def test_evidence_source_path_mismatch_is_retained_but_needs_mapping(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    result["evidence_refs"][0]["relative_path"] = "org_policy.md"
    receipt = _submit(root, wiki, gateway, result)
    candidate = wiki.semantic_state()["candidates"][receipt["result"]["candidate_id"]]
    mapping = candidate["evidence_mappings"][0]
    assert mapping["evidence_id"] == result["evidence_refs"][0]["evidence_id"]
    assert mapping["mapping_status"] == "SOURCE_IDENTITY_MISMATCH"
    assert result["evidence_refs"][0]["relative_path"] == "org_policy.md"


def test_exact_entity_query_reports_literal_endpoint_without_claiming_identity(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
    candidate = wiki.semantic_state()["candidates"][candidate_id]
    entity = next(
        row for row in candidate["understanding_result"]["semantic_candidate"]["items"]
        if row["kind"] == "entity" and row["meaning"] == "经营分析部"
    )
    result = gateway.semantic_operation(
        operation="understand.consumer.relations",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"candidate_id": candidate_id, "entity_ref": entity["item_id"]},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).relations(candidate_id, entity["item_id"]),
    )["result"]

    assert result["status"] == "FOUND"
    assert result["entity_identity_established"] is False
    assert result["relation_identity_status"] == "LITERAL_ENDPOINT_MATCH_UNVERIFIED"
    assert result["relations"]
    assert all(row["subject"] == entity["meaning"] or row["object"] == entity["meaning"] for row in result["relations"])


def test_same_name_entities_are_reported_ambiguous_without_relation_attachment(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    entity = next(row for row in result["semantic_candidate"]["items"] if row["kind"] == "entity")
    second = dict(entity)
    second.update({"item_id": "item_same_name_other_org", "key": "other_org:department:经营分析部"})
    result["semantic_candidate"]["items"].append(second)
    candidate_id = _submit(root, wiki, gateway, result)["result"]["candidate_id"]
    outcome = gateway.semantic_operation(
        operation="understand.consumer.relations",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"candidate_id": candidate_id, "entity_ref": entity["item_id"]},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).relations(candidate_id, entity["item_id"]),
    )["result"]
    assert outcome["status"] == "AMBIGUOUS_ENTITY_LABEL"
    assert outcome["relations"] == []


def test_changed_source_revision_is_stored_as_unmapped_and_never_fresh(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    (root / "monthly_rules.md").write_text("different revision\n", encoding="utf-8")
    receipt = _submit(root, wiki, gateway)
    candidate = wiki.semantic_state()["candidates"][receipt["result"]["candidate_id"]]
    assert receipt["result"]["mapping_status"] == "NEEDS_MAPPING"
    assert candidate["status"] == "PROPOSED_NEEDS_MAPPING"
    assert candidate["source_bindings"][0]["status"] == "SOURCE_REVISION_MISMATCH"
    assert wiki.semantic_state()["active_version_id"] is None


def test_candidate_item_query_exposes_conditions_exceptions_and_unknown_as_candidates(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
    for kind in ("condition", "exception", "unknown"):
        result = gateway.semantic_operation(
            operation="understand.consumer.items",
            scope_id=wiki.scope_id,
            actor_origin="codex_fixture",
            input_value={"candidate_id": candidate_id, "kind": kind},
            action=lambda recorder, kind=kind: UnderstandWikiAdapter(
                wiki, SemanticWiki(wiki, recorder=recorder), root
            ).items(candidate_id, kind=kind),
        )["result"]
        assert result["authority"] == "EXTERNAL_CANDIDATE_NOT_ACTIVE"
        assert result["items"]
        assert all(item["type"] == kind for item in result["items"])
        if kind in {"condition", "exception"}:
            assert all(item["producer_item_id"] for item in result["items"])


def test_evidence_lookup_returns_safe_original_locator_and_detects_revision_change(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
    evidence_id = _load_result()["evidence_refs"][1]["evidence_id"]
    def resolve():
        return gateway.semantic_operation(
            operation="understand.evidence.lookup",
            scope_id=wiki.scope_id,
            actor_origin="codex_fixture",
            input_value={"candidate_id": candidate_id, "evidence_id": evidence_id},
            action=lambda recorder: UnderstandWikiAdapter(
                wiki, SemanticWiki(wiki, recorder=recorder), root
            ).evidence(candidate_id, evidence_id),
        )["result"]

    resolved = resolve()
    assert resolved["status"] == "RESOLVED"
    assert resolved["locator"] == "line:2"
    assert resolved["relative_path"] == "monthly_rules.md"
    assert resolved["source_revision"] == _load_result()["source_inventory"][0]["source_revision"]
    assert "quote" not in resolved
    assert str(root.resolve()) not in json.dumps(resolved, ensure_ascii=False)

    (root / "monthly_rules.md").write_text("revised source\n", encoding="utf-8")
    stale = resolve()
    assert stale["status"] == "STALE_SOURCE_REVISION"
    graph = gateway.semantic_operation(
        operation="understand.graph.candidate",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"candidate_id": candidate_id},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).candidate_graph(candidate_id),
    )["result"]
    assert graph["freshness_status"] == "STALE"
    assert "source_revision_changed" in graph["warnings"]


def test_unsupported_locator_is_preserved_as_needs_mapping_not_dropped(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    result["evidence_refs"][0]["locator"] = "ppt/slides/slide1.xml#text:1"

    receipt = _submit(root, wiki, gateway, result)
    assert receipt["status"] == "success"
    candidate = wiki.semantic_state()["candidates"][receipt["result"]["candidate_id"]]
    evidence = candidate["understanding_result"]["evidence_refs"][0]
    assert evidence["locator"] == "ppt/slides/slide1.xml#text:1"
    assert candidate["mapping_status"] == "NEEDS_MAPPING"


def test_duplicate_submission_is_idempotent_and_test_scope_never_becomes_active(tmp_path):
    root, wiki, gateway = _workspace(tmp_path, enterprise_id="synthetic_test")
    result = _load_result()
    result["semantic_candidate"]["scope_id"] = wiki.scope_id
    first = _submit(root, wiki, gateway, result)
    second = _submit(root, wiki, gateway, result)
    assert first["result"]["candidate_id"] == second["result"]["candidate_id"]
    assert second["result"]["status"] == "no_op"
    state = wiki.semantic_state()
    row = state["candidates"][first["result"]["candidate_id"]]
    # One document keeps its frozen handoff and, beside it, the typed reading made from
    # the same spans - one candidate each, never more.
    typed = [cid for cid, cand in state["candidates"].items()
             if cand.get("candidate_type") != "understand_handoff.v1"]
    assert len(typed) <= 1
    assert set(state["candidates"]) == {first["result"]["candidate_id"], *typed}
    if typed:
        assert first["result"]["typed"]["candidate_id"] == typed[0]
    # The same bytes submitted again add neither a handoff nor a typed candidate.
    third = _submit(root, wiki, gateway, result)
    assert third["result"]["status"] == "no_op"
    assert set(wiki.semantic_state()["candidates"]) == set(state["candidates"])
    assert row["authority"] == "CANDIDATE_ONLY"
    assert row["producer_identity_status"] == "DECLARED_UNVERIFIED"
    assert state["active_version_id"] is None
    assert not state["accepted_versions"]


def test_understand_handoff_cannot_enter_legacy_evaluate_or_accept_lifecycle(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
    outcome = gateway.semantic_operation(
        operation="candidate.evaluate",
        scope_id=wiki.scope_id,
        actor_origin="independent_evaluator",
        input_value={"candidate_id": candidate_id, "evaluator_id": "structural-evaluator-v1"},
        action=lambda recorder: SemanticWiki(wiki, recorder=recorder).evaluate(
            candidate_id, actor_origin="independent_evaluator"
        ),
    )
    assert outcome["status"] == "failure"
    assert outcome["error"]["code"] == "candidate_requires_mapping"
    state = wiki.semantic_state()
    assert state["evaluations"] == {}
    assert state["decisions"] == {}
    assert state["active_version_id"] is None


def test_candidate_and_active_graphs_are_distinct_and_comparison_refuses_name_guessing(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
    active = gateway.semantic_operation(
        operation="understand.graph.active",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"query": "ontology_graph"},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).active_graph(),
    )["result"]
    compare = gateway.semantic_operation(
        operation="understand.consumer.compare",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"candidate_id": candidate_id},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).compare_active(candidate_id),
    )["result"]
    assert active["view"] == "active"
    assert active["active_version_id"] is None
    assert active["authority"] == "ACTIVE_VERSION_ONLY"
    assert active["active_semantics_status"] == "NO_ACTIVE_VERSION"
    assert active["candidate_meanings_included"] is False
    assert compare["candidate_authority"] == "EXTERNAL_CANDIDATE_NOT_ACTIVE"
    assert compare["crosswalk_status"] == "NOT_COMPARABLE_WITHOUT_EXPLICIT_CANONICAL_MAPPING"


def test_active_graph_exposes_test_only_authority_and_r4_version_scope(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    def action(recorder):
        semantic = SemanticWiki(wiki, recorder=recorder)
        semantic.ontology_graph = lambda **_kwargs: {
            "active_version_id": "version_test_only",
            "version_id": "version_test_only",
            "authority": "MANAGER_ACCEPTED_SCOPED_SEMANTICS",
            "knowledge_status": "known",
            "freshness_status": "fresh",
            "nodes": [{"id": "meaning:test", "type": "meaning"}],
            "edges": [],
            "source_index": [],
            "warnings": [],
            "truncated": False,
            "candidate_meanings_included": False,
            "causal_influence_proven": False,
        }
        wiki.semantic_state = lambda: {
            "active_version_id": "version_test_only",
            "accepted_versions": {"version_test_only": {"authority_class": "test_only"}},
        }
        return UnderstandWikiAdapter(wiki, semantic, root).active_graph()

    result = gateway.semantic_operation(
        operation="understand.graph.active",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"query": "ontology_graph"},
        action=action,
    )

    assert result["status"] == "success"
    assert result["result"]["active_semantics_status"] == "TEST_ONLY_ACTIVE"
    assert result["result"]["active_authority_class"] == "test_only"
    assert result["result"]["candidate_meanings_included"] is False
    events = JsonlTraceStore(tmp_path / "workspace").inspect_run(result["run_id"])["events"]
    graph_event = next(event for event in events if event["event_type"] == "understand.graph.projected")
    assert graph_event["scope_id"] == wiki.scope_id
    assert graph_event["active_version_id"] == "version_test_only"
    assert graph_event["active_authority_class"] == "test_only"
    assert graph_event["view"] == "active"


def test_invalid_scope_is_rejected_without_writing_a_candidate(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    result = _load_result()
    result["semantic_candidate"]["scope_id"] = "enterprise:other/project:monthly"

    receipt = _submit(root, wiki, gateway, result)
    assert receipt["status"] == "failure"
    assert receipt["error"]["code"] == "scope_mismatch"
    assert wiki.semantic_state()["candidates"] == {}
    inspect = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", "inspect", "--workspace", str(tmp_path / "workspace"), "--run-id", receipt["run_id"]],
        cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True,
    )
    events = json.loads(inspect.stdout)["events"]
    assert events[-1]["event_type"] == "request.terminal"
    assert events[-1]["terminal_status"] == "failure"
    assert any(event["event_type"] == "understand.candidate.received" and event["status"] == "rejected" for event in events)
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "run_event_v1_6.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    assert not [error.message for event in events for error in validator.iter_errors(event)]


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_candidate_state_round_trips_across_cold_processes(tmp_path, backend):
    root, wiki, gateway = _workspace(tmp_path, backend)
    receipt = _submit(root, wiki, gateway)
    candidate_id = receipt["result"]["candidate_id"]
    args = [
        sys.executable,
        "-c",
        "import json,sys; from catalyst_platform.wiki import ProjectWiki; "
        "w=ProjectWiki(sys.argv[1],[sys.argv[2]],enterprise_id='synthetic',project_id='monthly',backend=sys.argv[3]); "
        "s=w.semantic_state(); c=s['candidates'][sys.argv[4]]; "
        "print(json.dumps({'candidate_id':c['candidate_id'],'active':s['active_version_id'],'items':len(c['understanding_result']['semantic_candidate']['items'])},sort_keys=True))",
        str(tmp_path / "workspace"),
        str(root),
        backend,
        candidate_id,
    ]
    replay = subprocess.run(args, check=True, capture_output=True, text=True)
    assert json.loads(replay.stdout) == {"active": None, "candidate_id": candidate_id, "items": 12}


def test_json_and_sqlite_candidate_graph_outputs_are_equivalent(tmp_path):
    outputs = []
    for backend in ("json", "sqlite"):
        root, wiki, gateway = _workspace(tmp_path / backend, backend)
        candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
        graph = gateway.semantic_operation(
            operation="understand.graph.candidate",
            scope_id=wiki.scope_id,
            actor_origin="codex_fixture",
            input_value={"candidate_id": candidate_id},
            action=lambda recorder, wiki=wiki, root=root, candidate_id=candidate_id: UnderstandWikiAdapter(
                wiki, SemanticWiki(wiki, recorder=recorder), root
            ).candidate_graph(candidate_id),
        )["result"]
        outputs.append(graph)
    assert outputs[0] == outputs[1]


def test_r4_v16_events_validate_and_cold_process_trace_replay(tmp_path):
    root, wiki, gateway = _workspace(tmp_path)
    receipt = _submit(root, wiki, gateway)
    run_id = receipt["run_id"]
    inspect = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", "inspect", "--workspace", str(tmp_path / "workspace"), "--run-id", run_id],
        cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True,
    )
    cold = json.loads(inspect.stdout)
    assert cold["run_id"] == run_id
    events = cold["events"]
    assert {event["event_schema_version"] for event in events} == {"1.6"}
    assert any(event["event_type"] == "understand.candidate.received" for event in events)
    assert events[-1]["event_type"] == "request.terminal"
    assert events[-1]["terminal_status"] == "success"
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "run_event_v1_6.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    def leaf_errors(error):
        if error.context:
            return [message for nested in error.context for message in leaf_errors(nested)]
        return [f"{list(error.path)}: {error.message}"]

    schema_errors = []
    for event in events:
        for error in validator.iter_errors(event):
            schema_errors.extend((event["event_type"], message) for message in leaf_errors(error))
    assert not schema_errors, schema_errors
    trace_text = json.dumps(events, ensure_ascii=False)
    assert str(root.resolve()) not in trace_text
    assert all(ref["quote"] not in trace_text for ref in _load_result()["evidence_refs"])


@pytest.mark.parametrize("backend", ["json", "sqlite"])
@pytest.mark.parametrize("identity_problem", ["duplicate", "missing", "unsafe"])
def test_u01_invalid_or_duplicate_item_id_is_rejected_before_candidate_write(tmp_path, backend, identity_problem):
    """No two candidate graph nodes may share an ID, even across different kinds."""
    root, wiki, gateway = _workspace(tmp_path, backend=backend)
    result = _load_result()
    items = result["semantic_candidate"]["items"]
    if identity_problem == "duplicate":
        items[-1]["item_id"] = items[0]["item_id"]  # unknown vs exception
        error_code = "duplicate_candidate_item_id"
    elif identity_problem == "missing":
        items[0].pop("item_id")
        error_code = "invalid_candidate_item_identity"
    else:
        items[0]["item_id"] = "unsafe/item:id"
        error_code = "invalid_candidate_item_identity"

    receipt = _submit(root, wiki, gateway, result)
    assert receipt["status"] == "failure"
    assert receipt["error"]["code"] == error_code
    state = wiki.semantic_state()
    assert not state["candidates"]
    assert state["active_version_id"] is None
    assert not state["accepted_versions"]
    # The failed handoff is still observable through the existing R4 recorder.
    run_id = receipt["run_id"]
    inspected = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", "inspect", "--workspace", str(tmp_path / "workspace"), "--run-id", run_id],
        cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True,
    )
    events = json.loads(inspected.stdout)["events"]
    assert events[-1]["event_type"] == "request.terminal"
    assert events[-1]["terminal_status"] == "failure"
    assert any(event["event_type"] == "understand.candidate.received" and event["status"] == "rejected" and event["error_code"] == error_code for event in events)


@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_u01_unknown_items_are_paginated_from_complete_candidate_not_truncated_graph(tmp_path, backend):
    """The 500-node graph cap must never silently hide candidate-only UNKNOWNs."""
    root, wiki, gateway = _workspace(tmp_path, backend=backend)
    result = _load_result()
    items = result["semantic_candidate"]["items"]
    unknown = next(row for row in items if row["kind"] == "unknown")
    for i in range(600):
        item = dict(unknown)
        item["item_id"] = f"item_u01_unknown_{i:04d}"
        item["key"] = f"u01_critical_unknown_{i:04d}"
        items.append(item)
    candidate_id = _submit(root, wiki, gateway, result)["result"]["candidate_id"]
    class _NullRecorder:
        def event(self, *args, **kwargs):
            return {}

    adapter = UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=_NullRecorder(), recover_pending=False), root)

    graph = adapter.candidate_graph(candidate_id)
    assert graph["truncated"] is True
    assert "graph_truncated" in graph["warnings"]
    original_ids = {row["item_id"] for row in items if row["kind"] == "unknown"}
    assert len(original_ids) == 603
    assert len({node["id"] for node in graph["nodes"]}) == len(graph["nodes"])

    first = adapter.items(candidate_id, kind="unknown", limit=500)
    second = adapter.items(candidate_id, kind="unknown", limit=500, offset=first["next_offset"])
    assert first["total_count"] == second["total_count"] == len(original_ids)
    assert first["item_count"] == 500
    assert first["has_more"] is True and first["truncated"] is True
    assert first["next_offset"] == 500
    assert second["item_count"] == 103
    assert second["has_more"] is False
    assert second["next_offset"] is None
    assert second["offset"] == 500 and second["truncated"] is True  # page 2 is not the whole set
    all_rows = first["items"] + second["items"]
    assert {row["producer_item_id"] for row in all_rows} == original_ids
    assert len({row["producer_item_id"] for row in all_rows}) == len(all_rows)
    assert all(row["status"] == "UNRESOLVED" for row in all_rows)
    assert "graph_truncated" not in first["warnings"]  # items use an uncapped internal projection
    assert adapter.items(candidate_id, kind="unknown", offset=603)["items"] == []
    with pytest.raises(UnderstandWikiError) as exc:
        adapter.items(candidate_id, kind="unknown", offset=604)
    assert exc.value.code == "invalid_candidate_query"

    # Same store, fresh process, public CLI pagination (no private in-memory test JSON).
    cli = [sys.executable, "-m", "catalyst_platform", "ontology", "understand", "items",
           "--workspace", str(tmp_path / "workspace"), "--wiki-root", str(root),
           "--enterprise-id", "synthetic", "--project-id", "monthly", "--wiki-backend", backend,
           "--candidate-id", candidate_id, "--kind", "unknown", "--limit", "500", "--offset", "500"]
    replay = subprocess.run(cli, cwd=Path(__file__).parents[1], check=True, capture_output=True, text=True)
    cold_page = json.loads(replay.stdout)["result"]
    assert cold_page["offset"] == 500
    assert cold_page["total_count"] == 603
    assert {row["producer_item_id"] for row in cold_page["items"]} == {row["producer_item_id"] for row in second["items"]}

@pytest.mark.parametrize("backend", ["json", "sqlite"])
def test_u01_previously_persisted_collision_cannot_be_projected_as_valid_graph(tmp_path, backend):
    root, wiki, gateway = _workspace(tmp_path, backend=backend)
    candidate_id = _submit(root, wiki, gateway)["result"]["candidate_id"]
    def emulate_legacy_corrupt_row(state):
        items = state["candidates"][candidate_id]["understanding_result"]["semantic_candidate"]["items"]
        items[-1]["item_id"] = items[0]["item_id"]
    wiki.update_semantic_state(emulate_legacy_corrupt_row)
    outcome = gateway.semantic_operation(
        operation="understand.graph.candidate", scope_id=wiki.scope_id,
        actor_origin="codex_fixture", input_value={"candidate_id": candidate_id},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).candidate_graph(candidate_id),
    )
    assert outcome["status"] == "failure"
    assert outcome["error"]["code"] == "candidate_item_identity_conflict"
