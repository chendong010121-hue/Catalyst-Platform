"""A page that only lists names is still a page that says who sits under what."""

from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


class _ListPage:
    """A heading and one name under it, with or without the edge that joins them."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, join=True):
        self.join = join
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"]
        heading, listed = evidence[0]["evidence_id"], evidence[1]["evidence_id"]
        items = [
            {"kind": "entity", "key": "water_group", "meaning": "水利集团",
             "business_type": "BusinessUnit", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [heading]},
            {"kind": "entity", "key": "finance_dept", "meaning": "财务部",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [listed]},
        ]
        if self.join:
            items.append({"kind": "relation", "key": "finance_dept|belongs|water_group",
                          "subject": "finance_dept", "predicate": "隶属", "object": "water_group",
                          "meaning": "财务部 隶属 水利集团",
                          "relation_source": "LAYOUT", "layout_ref": "slide1: 组织结构 heading over 财务部",
                          "evidence_class": "INFERRED", "evidence_refs": [listed, heading],
                          "uncertainty": "名字列在同一标题下的版式里，按版式读作隶属"})
        return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False),
                             finish_reason="stop")


def _run(tmp_path, provider):
    source = tmp_path / "org.md"
    source.write_text("水利集团组织结构：\n财务部\n", encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("list-page", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)


def test_a_listed_name_no_relation_joins_is_counted(tmp_path):
    result = _run(tmp_path, _ListPage(join=False))
    attribution = result.producer_attribution

    assert attribution["entities_without_relation_count"] == 2
    assert attribution["entities_without_relation"] == ["water_group", "finance_dept"]


def test_a_layout_edge_places_the_listed_name_and_clears_the_count(tmp_path):
    result = _run(tmp_path, _ListPage(join=True))
    attribution = result.producer_attribution
    relations = [item for item in result.semantic_candidate.items if item.kind == "relation"]

    assert attribution["entities_without_relation_count"] == 0
    assert attribution["entities_without_relation"] == []
    assert [(item.subject, item.predicate, item.object) for item in relations] == [
        ("finance_dept", "隶属", "water_group")]
    assert relations[0].relation_source == "LAYOUT"
