"""A key the store cannot name costs its unit at most, never the card."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_semantic import _repaired_key


class _PerUnit:
    """One saved answer per extraction unit, in the order the units arrive."""

    model = "generator-fixture"
    structured_output_token_limit = 4096

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        payload = json.loads(request.messages[-1].content)
        evidence = payload["evidence"][0]["evidence_id"]
        rows = self.answers[min(len(self.requests), len(self.answers)) - 1]
        items = [{**row, "evidence_refs": [evidence]} if isinstance(row, dict) else row for row in rows]
        return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False),
                             finish_reason="stop")


def _source(tmp_path, sentence: str = "复核负责人负责单据复核。", lines: int = 100) -> Path:
    source = tmp_path / "org.md"
    source.write_text("\n".join(f"第 {index} 行：{sentence}" for index in range(lines)) + "\n",
                      encoding="utf-8")
    return source


def _entity(key: str, meaning: str) -> dict:
    return {"kind": "entity", "key": key, "meaning": meaning, "business_type": "Position",
            "evidence_class": "SOURCE_DIRECT"}


def _run(tmp_path, provider, sentence: str = "复核负责人负责单据复核。"):
    return UnderstandPort().understand(
        UnderstandingRequest("unit-keys", "整理组织", source_refs=(_source(tmp_path, sentence),),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path, semantic_provider=provider)


def test_a_key_written_with_spaces_is_repaired_rather_than_refused(tmp_path):
    result = _run(tmp_path, _PerUnit([[_entity("guan kong guanxi", "复核负责人")]]))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]

    assert [item.key for item in entities] == ["guan_kong_guanxi"]
    assert result.producer_attribution["refused_units"] == []


def test_a_relation_whose_ends_were_repaired_still_joins_them(tmp_path):
    result = _run(tmp_path, _PerUnit([[
        _entity("tech dept", "技术部"),
        _entity("tech lead", "技术主管"),
        {"kind": "relation", "key": "tech lead|belongs|tech dept", "subject": "tech lead",
         "predicate": "隶属", "object": "tech dept", "meaning": "技术主管 隶属 技术部",
         "evidence_class": "SOURCE_DIRECT"},
    ]]), sentence="技术部：技术主管 隶属 技术部。")
    relations = [item for item in result.semantic_candidate.items if item.kind == "relation"]

    assert [(item.subject, item.object) for item in relations] == [("tech_lead", "tech_dept")]


def test_a_key_with_nothing_storable_refuses_its_unit_and_keeps_the_others(tmp_path):
    result = _run(tmp_path, _PerUnit([
        [_entity("组 织", "复核负责人")],
        [_entity("review_lead", "复核负责人")],
    ]))
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]
    attribution = result.producer_attribution

    # Two units of the deck landed; the one that could not be named went alone.
    assert [item.key for item in entities] == ["review_lead"]
    assert [row["code"] for row in attribution["refused_units"]] == ["semantic_item_contract_violation"]


def test_repair_leaves_a_storable_key_alone():
    for key in ("review_lead", "dept.a-2", "k9"):
        assert _repaired_key(key) == key


def test_repair_keeps_a_chinese_key_for_the_refusal_to_name():
    assert _repaired_key("组织升级小组") == "组织升级小组"
    assert _repaired_key("guan kong") == "guan_kong"
    assert _repaired_key("9 lives") == "k_9_lives"
