"""A relation whose far end was never harvested cannot be published, and is counted."""

from __future__ import annotations

import hashlib
import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.observability import RunRecorder
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_wiki import UnderstandWikiAdapter, admission_plan
from catalyst_platform.wiki import ProjectWiki


class _PairWithAnUnnamableEnd:
    """Two things, one key the store cannot hold, and the relation that joins them."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "finance_dept", "meaning": "财务部门",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [evidence]},
            {"kind": "entity", "key": "各部门", "meaning": "各部门",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [evidence]},
            {"kind": "relation", "key": "finance_belongs_all",
             "subject": "finance_dept", "predicate": "隶属", "object": "各部门",
             "meaning": "财务部门 隶属 各部门",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]},
        ]}, ensure_ascii=False), finish_reason="stop")


def test_the_far_end_of_a_relation_is_dropped_not_fatal(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    source = sources / "org.md"
    source.write_text("财务部门 隶属 各部门。\n", encoding="utf-8")
    wiki = ProjectWiki(tmp_path / "workspace", [sources], enterprise_id="synthetic",
                       project_id="publish-relations")
    result = UnderstandPort().understand(
        UnderstandingRequest("far-end", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id=wiki.scope_id,
                             requested_depth="semantic", budget_steps=4),
        source_root=sources, semantic_provider=_PairWithAnUnnamableEnd())
    plan = admission_plan(result)
    # The plan names the pair it cannot deliver rather than adopting an edge it must drop.
    assert {row["item_key"]: row["reason"] for row in plan["pending"]} == {
        "各部门": "key_not_storable", "finance_belongs_all": "relation_endpoint_not_harvestable"}
    selected = [row["item_id"] for row in plan["default_adopt"]]
    # The owner may still select the edge by hand; publish stays the last guard.
    selected += [item.item_id for item in result.semantic_candidate.items
                 if item.key == "finance_belongs_all"]

    recorder = RunRecorder(JsonlTraceStore(wiki.workspace), run_id="run_far_end",
                           request_id="req_far_end", invocation_id="inv_far_end",
                           trace_id=hashlib.md5(b"far-end").hexdigest())
    recorder.start(request_kind="publish_test", actor="local_cli_user", component="CatalystGateway")
    actor = {"verified": True, "simulation": True, "permissions": ("knowledge.propose",),
             "readable_scope_ids": (wiki.scope_id,)}
    published = UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), sources).propose_native(
        result, selected_item_ids=selected, actor_context=actor)

    assert published["dropped_relations"] == [
        {"item_key": "finance_belongs_all", "rule": "relation_endpoint_not_selected"},
    ]
    entries = wiki.semantic_state()["candidates"][published["proposal"]["candidate_id"]]["entries"]
    kinds = [entry["kind"] for entry in entries]
    assert "entity" in kinds
    assert "relation" not in kinds
