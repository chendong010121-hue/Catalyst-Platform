"""一份定岗定编方案里，变更不只五个词。

holdout 那三页上有一句「融资岗融入出纳岗」——页面**决定**的事，是这次变更的全部内容。
旧词表只收 拆分 / 整合 / 合并 / 撤销 / 新设，于是这句话落成了一条 claim：把决定降级成
说法。宽词表收 融入 / 并入 / 划入 / 承接，方向与合并一致（失去原位的进 from，接住的进 to），
并且仍然只收这九个词：词表之外的说法照样降级、照样点名，不许拿一个没人定义过的谓词进事实集。
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

TEXT = ("融资岗融入出纳岗，出纳岗编制维持不变。\n"
        "招投标部并入投资管理部。\n"
        "办公室划入综合管理部。\n"
        "质检岗承接原材料检验职责。\n")

NAMES = {"rongzi": "融资岗", "chuna": "出纳岗", "zhaobiao": "招投标部",
         "touzi": "投资管理部", "bangong": "办公室", "zonghe": "综合管理部",
         "zhijian": "质检岗"}


class _Answer:
    model = "stub-event-vocabulary"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _evidence(evidence, name):
    return next(item["evidence_id"] for item in evidence if name in item["quote"])


def _entity(key, evidence):
    name = NAMES[key]
    return {"kind": "entity", "key": key, "meaning": name, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [_evidence(evidence, name)]}


def _units(evidence):
    return [_entity(key, evidence) for key in NAMES]


def _run(tmp_path, build):
    source = tmp_path / "deck.md"
    source.write_text(TEXT, encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("event-vocabulary", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_event_vocabulary",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def _event(key, predicate, before, after, evidence):
    """One change: `before` / `after` are lists of keys; the meaning names the units."""
    names = "、".join(NAMES.get(k, k) for k in before) + " → " + "、".join(NAMES.get(k, k) for k in after)
    return {"kind": "event", "key": key, "predicate": predicate,
            "meaning": "「" + predicate + "」：" + names,
            "from": list(before), "to": list(after), "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [_evidence(evidence, NAMES[before[0]])]}


def test_a_merger_worded_as_融入_is_a_change_and_not_a_claim(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            _event("rongru", "融入", ["rongzi"], ["chuna"], evidence)]

    result = _run(tmp_path, build)
    event = _by_key(result)["rongru"]
    assert event.kind == "event"
    assert (event.event_from, event.event_to) == (("rongzi",), ("chuna",))
    assert event.evidence_class == "observed_from_source"
    assert result.producer_attribution["item_contract_degraded_count"] == 0


def test_every_word_that_names_a_change_takes_both_sides(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            _event("rongru", "融入", ["rongzi"], ["chuna"], evidence),
            _event("bingru", "并入", ["zhaobiao"], ["touzi"], evidence),
            _event("huaru", "划入", ["bangong"], ["zonghe"], evidence),
            _event("chengjie", "承接", ["zhijian"], ["chuna"], evidence)]

    result = _run(tmp_path, build)
    by_key = _by_key(result)
    assert {k: v.uncertainty for k, v in by_key.items() if v.kind == "event"} == {
        "rongru": None, "bingru": None, "huaru": None, "chengjie": None}
    assert (by_key["bingru"].event_from, by_key["bingru"].event_to) == (("zhaobiao",), ("touzi",))
    assert (by_key["huaru"].event_from, by_key["huaru"].event_to) == (("bangong",), ("zonghe",))
    assert (by_key["chengjie"].event_from, by_key["chengjie"].event_to) == (("zhijian",), ("chuna",))


def test_a_takeover_whose_receiver_is_not_named_here_stays_unresolved_and_named(tmp_path):
    """承接 names what is taken over and who takes it; a missing receiver is not a fact."""
    def build(evidence):
        return _units(evidence) + [
            _event("chengjie", "承接", ["zhijian"], ["qiye"], evidence)]

    result = _run(tmp_path, build)
    event = _by_key(result)["chengjie"]
    assert event.evidence_class == "unresolved"
    assert event.uncertainty.startswith("degraded:event_endpoint_not_declared")


def test_one_side_only_is_refused_the_same_way_as_a_merge(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            {"kind": "event", "key": "rongru", "predicate": "融入",
             "meaning": "「融资岗」融入一处", "from": ["rongzi"],
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "融资岗")]}]

    result = _run(tmp_path, build)
    event = _by_key(result)["rongru"]
    assert event.uncertainty == "degraded:event_fields_required"


def test_a_verb_outside_the_nine_is_still_refused_and_named(tmp_path):
    """A wider vocabulary is not an open one: 转让 is not a change this contract defines."""
    def build(evidence):
        return _units(evidence) + [
            _event("zhuanrang", "转让", ["bangong"], ["zonghe"], evidence)]

    result = _run(tmp_path, build)
    event = _by_key(result)["zhuanrang"]
    assert event.kind == "event"
    assert event.evidence_class == "unresolved"
    assert event.uncertainty.startswith("degraded:event_predicate_unsupported")


def test_the_contract_names_the_nine_words_to_the_reader():
    from catalyst_platform.understand_semantic import semantic_extraction_rules

    rules = semantic_extraction_rules(None)
    for word in ("融入", "并入", "划入", "承接"):
        assert word in rules
    # 方向也写给模型：那一句是这次扩展最容易被读反的地方
    assert "is from [融资岗], to [出纳岗]" in rules
