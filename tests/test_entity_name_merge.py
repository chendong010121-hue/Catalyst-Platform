"""One name is one entity, however many pages of the source spell it."""

from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


class _SameNameTwice:
    """The same department named on two pages under two keys, with a relation to each."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, second_key="tech_dept_v2", same_meaning=True):
        self.second_key = second_key
        self.same_meaning = same_meaning
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        evidence = json.loads(request.messages[-1].content)["evidence"]
        # Two different passages: the second page that repeats the name when it is one
        # name, and a page that merely looks like it when it is two.
        first = evidence[1]["evidence_id"]
        second = evidence[2]["evidence_id"] if self.same_meaning else evidence[3]["evidence_id"]
        second_meaning = "技术部" if self.same_meaning else "技术中心"
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "tech_dept", "meaning": "技术部",
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [first]},
            {"kind": "entity", "key": self.second_key, "meaning": second_meaning,
             "business_type": "Department", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [second]},
            {"kind": "entity", "key": "tech_lead", "meaning": "技术主管",
             "business_type": "Position", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [first]},
            {"kind": "relation", "key": "tech_lead|belongs|tech_dept",
             "subject": "tech_lead", "predicate": "隶属", "object": "tech_dept",
             "meaning": "技术主管 隶属 技术部",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [second]},
            {"kind": "relation", "key": "tech_lead|belongs|tech_dept_v2",
             "subject": "tech_lead", "predicate": "隶属", "object": self.second_key,
             "meaning": "技术主管 隶属 技术部",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [second]},
        ]}, ensure_ascii=False), finish_reason="stop")


def _run(tmp_path, provider):
    source = tmp_path / "org.md"
    source.write_text("# 组织\n技术部：技术主管隶属技术部。\n技术部负责技术管理。\n技术中心负责技术交流。\n",
                      encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("name-merge", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)


def test_two_keys_for_one_name_become_one_entity(tmp_path):
    result = _run(tmp_path, _SameNameTwice())
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]

    assert sorted(item.key for item in entities) == ["tech_dept", "tech_lead"]
    kept = next(item for item in entities if item.key == "tech_dept")
    # Both passages now stand behind the one row.
    assert len(kept.evidence_refs) == 2


def test_a_relation_to_the_merged_key_is_rewritten_to_the_survivor(tmp_path):
    result = _run(tmp_path, _SameNameTwice())
    relations = [item for item in result.semantic_candidate.items if item.kind == "relation"]

    # The two edges said the same thing about the same two things; one edge remains.
    assert [(item.subject, item.predicate, item.object) for item in relations] == [
        ("tech_lead", "隶属", "tech_dept")]


def test_the_merge_is_named_in_the_attribution(tmp_path):
    result = _run(tmp_path, _SameNameTwice())
    attribution = result.producer_attribution

    # The chart the fold happened in is named with it: a name folds inside one chart only.
    assert attribution["merged_duplicate_entities"] == [
        {"name": "技术部", "kept_key": "tech_dept", "scope_state": None,
         "merged_keys": ["tech_dept_v2"], "evidence_count": 2}]
    assert "same_name_entity_merge" in attribution["catalyst_transforms"]
    assert attribution["dropped_invalid_items"].get("relation_duplicated_by_entity_merge") == 1


def test_two_names_that_only_look_alike_stay_two_entities(tmp_path):
    result = _run(tmp_path, _SameNameTwice(same_meaning=False))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]

    assert sorted(item.key for item in entities) == ["tech_dept", "tech_dept_v2", "tech_lead"]
    assert result.producer_attribution["merged_duplicate_entities"] == []
