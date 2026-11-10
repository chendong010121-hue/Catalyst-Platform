"""The business view: objects first, evidence on request, and counts that say what they count.

The shipped candidate graph draws every evidence node before the first item and has no
duty/event/condition node at all (see evidence/batch3-before). These tests pin the new
business view, and keep the old provenance view's contract intact.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.understand_wiki import UnderstandWikiAdapter

FIXTURE = Path(__file__).parent / "fixtures" / "u0_understand_handoff"
HOLDER = "经营分析部"
FINANCE = "财务部"
EVIDENCE = "ev_1df4b99626359028bceea0c4"


def _result_with_objects(scope_id: str = "enterprise:synthetic/project:monthly") -> dict:
    result = json.loads((FIXTURE / "SemanticCandidate.json").read_text(encoding="utf-8-sig"))
    result["semantic_candidate"]["scope_id"] = scope_id
    items = result["semantic_candidate"]["items"]
    items.extend([
        {
            "item_id": "item_duty_monthly", "kind": "duty", "key": "duty_monthly",
            "meaning": "负责月度经营分析", "subject": HOLDER, "scope_state": "current",
            "evidence_class": "observed_from_source", "evidence_refs": [EVIDENCE],
        },
        {
            "item_id": "item_duty_lost", "kind": "duty", "key": "duty_lost",
            "meaning": "负责无人认领的工作", "subject": "不存在单位", "scope_state": "proposed",
            "evidence_class": "inferred", "evidence_refs": [],
        },
        {
            "item_id": "item_event_report", "kind": "event", "key": "event_report",
            "meaning": "运营管理部向财务报送月报", "predicate": "报送",
            "from": [HOLDER], "to": [FINANCE], "scope_state": "proposed",
            "evidence_class": "inferred", "evidence_refs": [EVIDENCE],
        },
        {
            "item_id": "item_condition_closed", "kind": "condition", "key": "cond_closed",
            "meaning": "仅在关账后报送", "applies_to": ["duty_monthly"],
            "evidence_class": "inferred", "evidence_refs": [EVIDENCE],
        },
    ])
    return result


def _candidate_in(tmp_path, project_id: str, extra_items=None):
    root = tmp_path / "sources"
    shutil.copytree(FIXTURE / "inputs", root)
    wiki = ProjectWiki(tmp_path / "workspace", [root], enterprise_id="synthetic",
                       project_id=project_id, backend="json")
    gateway = CatalystGateway(tmp_path / "workspace")
    result = _result_with_objects(wiki.scope_id)
    result["semantic_candidate"]["items"].extend(extra_items or [])
    receipt = gateway.semantic_operation(
        operation="understand.candidate.submit",
        scope_id=wiki.scope_id,
        actor_origin="codex_fixture",
        input_value={"contract_version": "catalyst.understand_handoff.v1"},
        action=lambda recorder: UnderstandWikiAdapter(
            wiki, SemanticWiki(wiki, recorder=recorder), root
        ).submit(result, declared_scope_id=wiki.scope_id),
    )
    class _NullRecorder:
        def event(self, *args, **kwargs):
            return {}

    adapter = UnderstandWikiAdapter(
        wiki, SemanticWiki(wiki, recorder=_NullRecorder(), recover_pending=False), root)
    return adapter, receipt["result"]["candidate_id"], wiki


@pytest.fixture()
def candidate(tmp_path):
    return _candidate_in(tmp_path, "monthly")


@pytest.fixture()
def local_candidate(tmp_path):
    return _candidate_in(tmp_path, "local-ui-demo")


def types_of(graph):
    return [node["type"] for node in graph["nodes"]]


def node(graph, item_id):
    return next(node for node in graph["nodes"] if node["id"] == f"understand-item:{item_id}")


# ---------------------------------------------------------------- the business view
def test_the_business_view_draws_objects_and_not_evidence(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id)

    assert graph["schema"] == "catalyst.understand_business_graph.v1"
    assert graph["view"] == "business"
    assert graph["authority"] == "EXTERNAL_CANDIDATE_NOT_ACTIVE"
    assert graph["evidence_expanded"] is False
    assert "evidence" not in types_of(graph)
    assert "source_revision" not in types_of(graph)
    counts = {}
    for kind in types_of(graph):
        counts[kind] = counts.get(kind, 0) + 1
    assert counts["duty"] == 2
    assert counts["event"] == 1
    assert counts["condition"] == 2
    assert counts["entity"] == 3


def test_the_provenance_view_keeps_its_old_contract(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.candidate_graph(candidate_id)
    assert graph["schema"] == "catalyst.understand_candidate_graph.v1"
    assert graph["view"] == "candidate"
    assert len([node for node in graph["nodes"] if node["type"] == "evidence"]) == 7
    assert len([node for node in graph["nodes"] if node["type"] == "source_revision"]) == 2
    small = adapter.candidate_graph(candidate_id, limit=3)
    assert small["truncated"] is True
    assert "graph_truncated" in small["warnings"]


def test_an_event_with_two_endpoints_counts_once(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id)
    assert graph["counts"]["items"]["event"]["items"] == 1
    assert graph["counts"]["items"]["event"]["placements"] == 2
    assert graph["budget"]["by_type"]["event"] == {"shown": 1, "total": 1}
    assert "一次" in graph["counts"]["note"]


def test_the_budget_keeps_objects_before_claims_and_says_why(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id, limit=6)

    assert graph["budget"]["truncated"] is True
    retained = types_of(graph)
    assert set(retained) <= {"entity", "duty", "event", "condition"}
    assert graph["budget"]["by_type"]["claim"] == {"shown": 0, "total": 2}
    assert graph["budget"]["by_type"]["unknown"] == {"shown": 0, "total": 3}
    assert graph["budget"]["by_type"]["entity"] == {"shown": 3, "total": 3}
    assert "预算" in graph["explain"]["truncation"]


def test_focus_returns_the_object_and_one_hop_only(candidate):
    adapter, candidate_id, _wiki = candidate
    focus_id = "understand-item:" + next(
        item["item_id"] for item in _result_with_objects()["semantic_candidate"]["items"]
        if item["kind"] == "entity" and item["key"] == HOLDER)
    graph = adapter.business_graph(candidate_id, focus=focus_id)

    assert graph["focus"]["node_id"] == focus_id
    assert graph["focus"]["found"] is True
    ids = [node["id"] for node in graph["nodes"]]
    assert focus_id in ids
    assert "understand-item:item_duty_monthly" in ids  # held by the focus
    assert "understand-item:item_event_report" in ids  # starts at the focus
    assert "understand-item:item_condition_closed" not in ids  # two hops: entity -> duty -> condition
    assert "understand-item:item_duty_lost" not in ids  # unrelated
    assert graph["budget"]["by_type"]["claim"]["total"] == 2
    assert graph["budget"]["by_type"]["claim"]["shown"] == 0
    assert "聚焦" in graph["explain"]["focus"]


def test_focus_on_an_unknown_node_is_named_not_filled(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id, focus="understand-item:item_missing")
    assert graph["focus"]["found"] is False
    assert graph["nodes"] == []
    assert "item_missing" in graph["explain"]["focus"]


def test_without_a_focus_no_center_is_chosen(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id)
    assert graph["focus"] is None
    assert "center" not in graph
    assert len(graph["index"]) == 8  # 3 entities + 2 duties + 1 event + 2 conditions
    assert {row["kind"] for row in graph["index"]} == {"entity", "duty", "event", "condition"}


def test_unattached_objects_are_listed_with_a_reason(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id)
    lost = {row["id"] for row in graph["unattached"]}
    assert "understand-item:item_duty_lost" in lost
    assert "understand-item:item_condition_closed" not in lost  # applies to a duty
    reasons = {row["id"]: row["reason"] for row in graph["unattached"]}
    assert "不存在单位" in reasons["understand-item:item_duty_lost"]
    assert "没有记录适用对象" in reasons.get("understand-item:" + next(
        item["item_id"] for item in _result_with_objects()["semantic_candidate"]["items"]
        if item["kind"] == "condition" and item["key"] == "closed_period"), "")


def test_expanding_evidence_adds_information_and_changes_no_judgement(candidate):
    adapter, candidate_id, _wiki = candidate
    base = adapter.business_graph(candidate_id)
    expanded = adapter.business_graph(candidate_id, evidence=True)

    assert expanded["evidence_expanded"] is True
    assert "evidence" in types_of(expanded)
    base_items = {node["id"]: node for node in base["nodes"]}
    expanded_items = {node["id"]: node for node in expanded["nodes"] if node["type"] not in {"evidence", "source_revision"}}
    assert set(base_items) == set(expanded_items)
    for node_id, before in base_items.items():
        after = expanded_items[node_id]
        assert after["qualification"] == before["qualification"]
        assert after["status"] == before["status"]
        assert after["evidence_ids"] == before["evidence_ids"]
    assert expanded["authority"] == base["authority"]
    assert expanded["candidate_status"] == base["candidate_status"]


def test_business_nodes_carry_the_shared_object_card(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id)
    duty = node(graph, "item_duty_monthly")
    card = duty["object"]
    assert card["kind"] == "duty"
    assert card["roles"][0]["name"] == "holder"
    assert card["roles"][0]["key"] == HOLDER
    # The entity's own saved label, caveat included; the key stays next to it.
    assert card["roles"][0]["title"].startswith(HOLDER)
    assert card["roles"][0]["resolved"] is True
    assert card["citations"] and "来源属性未记录" in card["citations"][0]["line"]
    assert card["advanced"]["identity"]["candidate_id"] == candidate_id
    assert card["unattached"] is False


def test_each_node_is_named_the_way_the_store_named_it(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id)

    entity = next(row for row in graph["nodes"] if row["type"] == "entity" and row["key"] == HOLDER)
    assert entity["display_name"].startswith(HOLDER)
    assert entity["display_name"] != entity["key"]
    # The context line is whatever the row saved: a business type, or nothing at all.
    assert entity["sub_label"] == entity["business_type"]

    duty = node(graph, "item_duty_monthly")
    assert duty["display_name"] == "负责月度经营分析"
    assert duty["display_name"] != duty["key"]
    assert HOLDER in duty["sub_label"]  # the holder, by name

    relation = next(row for row in graph["nodes"] if row["type"] == "relation")
    assert relation["display_name"] == relation["predicate"]
    assert relation["display_name"] != relation["key"]

    # The list a reader picks from carries the same name, with the key beside it.
    row = next(item for item in graph["index"] if item["id"] == duty["id"])
    assert row["display_name"] == duty["display_name"]
    assert row["key"] == duty["key"]
    for item in graph["index"]:
        assert item["display_name"]


def test_a_node_without_a_saved_name_keeps_its_key(tmp_path):
    adapter, candidate_id, _wiki = _candidate_in(tmp_path, "monthly-nameless", extra_items=[
        {
            "item_id": "item_duty_nameless", "kind": "duty", "key": "duty_nameless",
            "meaning": "", "subject": HOLDER, "evidence_class": "inferred", "evidence_refs": [],
        },
    ])
    graph = adapter.business_graph(candidate_id)
    row = node(graph, "item_duty_nameless")
    assert row["display_name"] == "duty_nameless"
    assert row["display_name"] == row["key"]


def test_edges_carry_their_name_and_direction(candidate):
    adapter, candidate_id, _wiki = candidate
    graph = adapter.business_graph(candidate_id)
    held = next(edge for edge in graph["edges"] if edge["type"] == "held_by")
    assert held["source"] == "understand-item:item_duty_monthly"
    assert held["target"].startswith("understand-item:")
    assert held["label"] == "持有者"
    assert held["direction"] == "source_to_target"
    relation = next(edge for edge in graph["edges"] if edge["type"] == "subject_entity")
    assert relation["label"] == "requests_data_from"
    assert relation["direction"] == "source_to_target"
    event_from = next(edge for edge in graph["edges"] if edge["type"] == "event_from")
    assert event_from["label"] == "起点"
    applies = [edge for edge in graph["edges"] if edge["type"] == "applies_to"]
    assert [edge["target"] for edge in applies] == ["understand-item:item_duty_monthly"]


def test_the_http_read_defaults_to_the_business_view(local_candidate):
    import threading
    from urllib.error import HTTPError
    from urllib.request import urlopen

    from catalyst_platform.workspace_ui import create_workspace_server

    adapter, candidate_id, wiki = local_candidate
    workspace = wiki.workspace
    server = create_workspace_server(workspace, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    scope = wiki.scope_id
    try:
        from urllib.parse import quote

        def get(path):
            with urlopen(base + path, timeout=30) as response:
                return response.status, json.load(response)

        # The server's daily scope is this workspace's own scope, so no scope query is needed.
        q = quote(scope, safe="")
        status, graph = get(f"/api/ontology?candidate_id={candidate_id}")
        assert status == 200
        assert graph["view_tier"] == "candidate"
        assert graph["schema"] == "catalyst.understand_business_graph.v1"
        assert graph["evidence_expanded"] is False

        _status, provenance = get(f"/api/ontology?candidate_id={candidate_id}&view=all")
        assert provenance["schema"] == "catalyst.understand_candidate_graph.v1"
        assert "evidence" in [node["type"] for node in provenance["nodes"]]

        _status, small = get(f"/api/ontology?candidate_id={candidate_id}&limit=6")
        assert small["budget"]["truncated"] is True

        _status, focused = get(
            f"/api/ontology?candidate_id={candidate_id}"
            "&focus=understand-item:item_duty_monthly")
        assert focused["focus"]["found"] is True
        ids = [node["id"] for node in focused["nodes"]]
        assert "understand-item:item_duty_monthly" in ids
        assert "understand-item:item_condition_closed" in ids  # applies to this duty
        assert len(ids) == 3  # the duty, its holder, and that condition

        with pytest.raises(HTTPError) as raised:
            get(f"/api/ontology?candidate_id={candidate_id}&view=bogus")
        assert raised.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
