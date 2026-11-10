"""组织的一次变更是一条 event，不是一条长期成立的关系。

一张方案页说「综合办公室拆分为行政服务办公室、党委办公室、纪检室」，说的是它决定做什么；
这句话读成「行政服务办公室 隶属 综合办公室」就把一次拆分写成了一种现状，方向刚好相反。
所以变更走 event：subject 是被变更的单位，object 是它变成的单位，predicate 是拆分/整合/合并/撤销/新设。

写得不对的 event 不许进事实：谓词不在词表里、缺一个端点、端点不是本题声明过的实体，
都保成 unresolved 的 event 并把规则写在它脸上，既不丢行也不冒充事实。
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

TEXT = ("综合办公室拆分为行政服务办公室、党委办公室、纪检室。\n"
        "投资管理中心与市场营销中心整合为一个中心。\n")


class _Answer:
    model = "stub-change-events"
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
        UnderstandingRequest("change-events", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_events",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def test_a_split_the_page_decides_is_one_event_per_unit_it_creates(tmp_path):
    def build(evidence):
        return [
            _entity("zonghe_bangongshi", "综合办公室", evidence),
            _entity("xingzheng_bangongshi", "行政服务办公室", evidence),
            _entity("dangwei_bangongshi", "党委办公室", evidence),
            {"kind": "event", "key": "chai_fen_xingzheng", "predicate": "拆分",
             "meaning": "「综合办公室」拆分为「行政服务办公室」",
             "subject": "zonghe_bangongshi", "object": "xingzheng_bangongshi",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "综合办公室")], "scope_state": "proposed"},
            {"kind": "event", "key": "chai_fen_dangwei", "predicate": "拆分",
             "meaning": "「综合办公室」拆分为「党委办公室」",
             "subject": "zonghe_bangongshi", "object": "dangwei_bangongshi",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "综合办公室")], "scope_state": "proposed"},
        ]

    result = _run(tmp_path, build)
    items = _by_key(result)
    split = items["chai_fen_xingzheng"]
    assert (split.kind, split.subject, split.predicate, split.object) == (
        "event", "zonghe_bangongshi", "拆分", "xingzheng_bangongshi")
    assert split.scope_state == "proposed"
    assert result.producer_attribution["item_contract_degraded_count"] == 0


def test_a_change_naming_a_unit_this_answer_never_declared_stays_unresolved(tmp_path):
    def build(evidence):
        return [
            _entity("zonghe_bangongshi", "综合办公室", evidence),
            {"kind": "event", "key": "chai_fen_jiwei", "predicate": "拆分",
             "meaning": "「综合办公室」拆分为「纪检室」",
             "subject": "zonghe_bangongshi", "object": "jijian_shi",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "综合办公室")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["chai_fen_jiwei"]
    # Kept, not dropped: the page did decide it, and a reviewer can still finish the end.
    assert event.kind == "event"
    assert event.evidence_class == "unresolved"
    assert event.uncertainty == "degraded:event_endpoint_not_declared:jijian_shi"
    assert [row["rule"] for row in result.producer_attribution["item_contract_degraded"]] == [
        "event_endpoint_not_declared"]


def test_a_change_word_outside_the_vocabulary_is_named_not_guessed(tmp_path):
    def build(evidence):
        return [
            _entity("touzi_guanli_zhongxin", "投资管理中心", evidence),
            _entity("shichang_yingsiao_zhongxin", "市场营销中心", evidence),
            {"kind": "event", "key": "zhenghe_yingsiao", "predicate": "调整",
             "meaning": "「投资管理中心」与「市场营销中心」整合为一个中心",
             "subject": "touzi_guanli_zhongxin", "object": "shichang_yingsiao_zhongxin",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "投资管理中心")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["zhenghe_yingsiao"]
    assert event.evidence_class == "unresolved"
    assert event.uncertainty == "degraded:event_predicate_unsupported:调整"


def test_a_change_joining_an_item_to_itself_changes_nothing_and_is_named(tmp_path):
    """Live card m4e wrote 「整合 市场营销中心 -> 市场营销中心」 beside the true pair.

    Both ends are the same unit, so the row states no change; it is kept unresolved
    rather than published as a fact, and the rule that refused it is on its face.
    """
    def build(evidence):
        return [
            _entity("shichang_yingsiao_zhongxin", "市场营销中心", evidence),
            {"kind": "event", "key": "zhenghe_zishen", "predicate": "整合",
             "meaning": "「市场营销中心」整合为「市场营销中心」",
             "subject": "shichang_yingsiao_zhongxin", "object": "shichang_yingsiao_zhongxin",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "市场营销中心")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["zhenghe_zishen"]
    assert event.evidence_class == "unresolved"
    assert event.uncertainty == "degraded:event_endpoints_are_the_same_item"


def test_abolishing_one_unit_needs_only_the_unit_it_acts_on(tmp_path):
    def build(evidence):
        return [
            _entity("zonghe_bangongshi", "综合办公室", evidence),
            {"kind": "event", "key": "chexiao_jijian", "predicate": "撤销",
             "meaning": "「纪检室」不再单独设置",
             "subject": "zonghe_bangongshi",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "综合办公室")]},
        ]

    result = _run(tmp_path, build)
    event = _by_key(result)["chexiao_jijian"]
    assert (event.kind, event.predicate, event.object) == ("event", "撤销", None)
    assert event.evidence_class != "unresolved"
