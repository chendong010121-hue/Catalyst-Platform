"""一次变更是「一组单位变成另一组单位」，不是一对边。

「整合投资管理中心、市场营销中心，设置为市场营销中心」这句话里，市场营销中心在变更前后
都在。旧的成对形状只能写「投资管理中心 → 市场营销中心」，读者会以为市场营销中心是这次变更
的产物；模型想把两边都写出来，就只好再写一行「市场营销中心 → 市场营销中心」，而那一行正是
契约拒绝的「两端是同一个条目」。所以事件按 `types.v0.2` 的 `from` / `to` 列表落：

    from [投资管理中心, 市场营销中心]  to [市场营销中心]

一次动作一行，两个列表各是一个单位集合。旧卡上的成对行按它写的那一对读，一行不改地继续成立。
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

TEXT = ("投资管理中心与市场营销中心整合为市场营销中心。\n"
        "一分公司合并到天水智信，不再保留一分公司法人主体。\n")


class _Answer:
    model = "stub-event-lists"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _evidence(evidence, name):
    return next(item["evidence_id"] for item in evidence if name in item["quote"])


def _entity(key, name, evidence):
    return {"kind": "entity", "key": key, "meaning": name, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [_evidence(evidence, name)]}


def _run(tmp_path, build):
    source = tmp_path / "deck.md"
    source.write_text(TEXT, encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("event-lists", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_event_lists",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def _units(evidence):
    return [_entity("touzi", "投资管理中心", evidence),
            _entity("shichang", "市场营销中心", evidence),
            _entity("yi_fen", "一分公司", evidence),
            _entity("zhi_xin", "天水智信", evidence)]


def test_one_change_keeps_the_unit_that_was_already_there_on_both_sides(tmp_path):
    """The sentence's whole point: 市场营销中心 is an input and the result."""
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "zhenghe", "predicate": "整合",
             "meaning": "「投资管理中心」与「市场营销中心」整合，设置为「市场营销中心」",
             "from": ["touzi", "shichang"], "to": ["shichang"],
             "evidence_class": "SOURCE_DIRECT", "scope_state": "proposed",
             "evidence_refs": [_evidence(evidence, "投资管理中心")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["zhenghe"]
    assert (event.event_from, event.event_to) == (("touzi", "shichang"), ("shichang",))
    assert event.evidence_class == "observed_from_source"
    assert result.producer_attribution["item_contract_degraded_count"] == 0


def test_the_card_writes_the_lists_under_the_names_the_type_gave_them(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "zhenghe", "predicate": "整合",
             "meaning": "整合为「市场营销中心」",
             "from": ["touzi", "shichang"], "to": ["shichang"],
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "市场营销中心")]},
        ]

    card = _run(tmp_path, build).to_dict()
    row = next(item for item in card["semantic_candidate"]["items"] if item["kind"] == "event")
    assert row["from"] == ["touzi", "shichang"] and row["to"] == ["shichang"]
    assert "event_from" not in row and "event_to" not in row


def test_a_change_that_gives_one_side_only_is_unresolved_and_named(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "zhenghe", "predicate": "整合",
             "meaning": "整合为一处", "from": ["touzi"],
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "投资管理中心")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["zhenghe"]
    assert event.evidence_class == "unresolved"
    assert event.uncertainty == "degraded:event_fields_required"


def test_ends_that_are_not_names_are_refused_as_a_shape_not_as_content(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "zhenghe", "predicate": "整合",
             "meaning": "整合为一处", "from": [{"key": "touzi"}], "to": ["shichang"],
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "投资管理中心")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["zhenghe"]
    assert event.evidence_class == "unresolved"
    assert event.uncertainty == "degraded:event_ends_must_be_lists"


def test_an_old_pair_shaped_row_still_stands_as_the_pair_it_names(tmp_path):
    """Every card taken before the list shape keeps exactly the meaning it had."""
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "hebing", "predicate": "合并",
             "meaning": "「一分公司」合并到「天水智信」",
             "subject": "yi_fen", "object": "zhi_xin",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "一分公司")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["hebing"]
    assert (event.event_from, event.event_to) == (("yi_fen",), ("zhi_xin",))
    assert event.uncertainty is None


def test_whether_the_legal_person_survives_is_kept_when_the_page_says_so(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "hebing", "predicate": "合并",
             "meaning": "「一分公司」合并到「天水智信」，不再保留一分公司法人主体",
             "from": ["yi_fen"], "to": ["zhi_xin"], "keeps_legal_entity": False,
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "一分公司")]},
        ]

    result = _run(tmp_path, build)
    assert _by_key(result)["hebing"].keeps_legal_entity is False


def test_a_legal_person_answer_that_is_not_yes_or_no_is_dropped_and_named(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "hebing", "predicate": "合并",
             "meaning": "「一分公司」合并到「天水智信」",
             "from": ["yi_fen"], "to": ["zhi_xin"], "keeps_legal_entity": "可能",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "一分公司")]},
        ]

    result = _run(tmp_path, build)
    assert _by_key(result)["hebing"].keeps_legal_entity is None
    assert [row["rule"] for row in result.producer_attribution["item_contract_drops"]] == [
        "keeps_legal_entity_not_boolean"]
