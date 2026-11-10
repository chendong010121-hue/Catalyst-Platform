"""一个契约没定义的字段带着值，不该让整张卡作废——字段走，行走。

真卡 live-m5b 就是这么死的：模型把 relation 才有的 `relation_source` / `layout_ref`
写在了一条 claim 上（「这句职责按版面位置归属常务副经理」），抽取层把它当硬违规抛出，
一张卡连同 300 多条行一起作废。这句话本身是有内容的、有证据的，只是形状不对。

现在的处置：丢字段、留行、把字段名和它所在的行记进归因。发明的字段永远进不了卡，
也不该因此把卡作废。
"""
from __future__ import annotations

import json

import pytest

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

TEXT = "分公司常务副经理统筹管理分公司日常运营工作，主抓生产。\n"


class _Answer:
    model = "stub-valued-field"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _run(tmp_path, build):
    source = tmp_path / "deck.md"
    source.write_text(TEXT, encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("valued-field", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_valued",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def test_a_relation_field_written_on_a_claim_costs_the_field_and_not_the_card(tmp_path):
    def build(evidence):
        ref = [evidence[0]["evidence_id"]]
        return [
            {"kind": "entity", "key": "changwu_fujingli", "meaning": "分公司常务副经理",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ref},
            {"kind": "claim", "key": "changwu_fujingli_zhize",
             "meaning": "「统筹管理分公司日常运营工作，主抓生产」",
             "evidence_class": "INFERRED", "evidence_refs": ref,
             "uncertainty": "该职责句紧接岗位名且未另写主语，按相邻顺序推断",
             "relation_source": "LAYOUT", "layout_ref": "slide12: 岗位名与其后职责描述相邻"},
        ]

    result = _run(tmp_path, build)
    rows = {item.key: item for item in result.semantic_candidate.items}
    claim = rows["changwu_fujingli_zhize"]
    assert claim.kind == "claim"
    assert claim.evidence_class == "inferred"
    assert claim.relation_source is None and claim.layout_ref is None
    assert "统筹管理分公司日常运营工作" in claim.meaning
    attribution = result.producer_attribution
    assert attribution["dropped_valued_field_count"] == 1
    assert attribution["dropped_valued_fields"] == [
        {"item_key": "changwu_fujingli_zhize", "kind": "claim",
         "fields": ["layout_ref", "relation_source"]}]
    assert attribution["dropped_item_fields"] == {"layout_ref": 1, "relation_source": 1}


def test_an_absence_field_on_a_claim_still_takes_the_row(tmp_path):
    """The absence fields are different: a claim carrying them is a row in the wrong shape."""
    def build(evidence):
        ref = [evidence[0]["evidence_id"]]
        return [
            {"kind": "entity", "key": "changwu_fujingli", "meaning": "分公司常务副经理",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ref},
            {"kind": "claim", "key": "odd_row", "meaning": "「主抓生产」",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ref,
             "observed_absence": "审批权限"},
        ]

    result = _run(tmp_path, build)
    assert "odd_row" not in {item.key for item in result.semantic_candidate.items}
    assert result.producer_attribution["dropped_invalid_items"] == {
        "absence_scope_not_applicable": 1}


def test_a_field_that_claims_authority_is_refused_not_dropped(tmp_path):
    """字段能丢，决定权不能丢：activation/approval 这类字段是模型在替业主拍板。

    其他没定义的字段一律「丢字段、留行」；这一条是唯一的例外，整张答案作废，
    因为「确认」这件事只能由业主做（回执，契约第五节）。
    """
    def build(evidence):
        ref = [evidence[0]["evidence_id"]]
        return [
            {"kind": "entity", "key": "changwu_fujingli", "meaning": "分公司常务副经理",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ref,
             "activation_authorized": True},
        ]

    with pytest.raises(ValueError) as refused:
        _run(tmp_path, build)
    assert "item_claims_authority" in str(refused.value)


def test_a_field_that_only_mentions_a_decision_verb_in_a_word_is_still_dropped(tmp_path):
    """`design_ref` 里的 design 不是签名：按 snake_case 词元比对，不按子串。"""
    def build(evidence):
        ref = [evidence[0]["evidence_id"]]
        return [
            {"kind": "entity", "key": "changwu_fujingli", "meaning": "分公司常务副经理",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": ref,
             "design_ref": "slide12"},
        ]

    result = _run(tmp_path, build)
    assert "changwu_fujingli" in {item.key for item in result.semantic_candidate.items}
    assert result.producer_attribution["dropped_item_fields"] == {"design_ref": 1}
