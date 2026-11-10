"""A name the card calls a label is not a node; an open relation is not a refused name.

One deck listed the kinds of customer it serves, the documents it produces and the working
modes it compares. The reading opened an entity for each name and, on the same page, an
UNKNOWN about it. The first rule treated any UNKNOWN as a refusal and took three governing
bodies off the card with it - 组织升级小组, 变革委员会 and 三定方案, names the deck places and acts
through. Only a denial written in the UNKNOWN refuses a node: a name the answer cannot place
stays, with the relation that is unwritten left open - the two facts can hold at once.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_label_entities",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_label_entities",
        requested_depth="semantic",
        budget_steps=16,
    )


class _Rows:
    model = "stub-label-model"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, build):
        self._build = build

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        return ModelResponse(content=json.dumps({"items": self._build(payload["evidence"])},
                                                ensure_ascii=False),
                             finish_reason="stop")


def _ids(evidence):
    return {row["quote"]: row["evidence_id"] for row in evidence}


def _entity(key, meaning, evidence_id):
    return {"kind": "entity", "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id]}


def _unknown(key, meaning, evidence_id):
    return {"kind": "unknown", "key": key, "meaning": meaning, "evidence_class": "UNKNOWN",
            "uncertainty": "本页未说明其性质或关系", "evidence_refs": [evidence_id]}


def _run(tmp_path, build, lines):
    source = tmp_path / "org.md"
    source.write_text("\n".join(lines), encoding="utf-8")
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(build))


def test_a_name_the_unknown_calls_a_collective_term_is_not_a_node(tmp_path):
    lines = ["各部门", "监事会"]

    def build(evidence):
        ids = _ids(evidence)
        return [
            _entity("bumen", "各部门", ids["各部门"]),
            _entity("jianshihui", "监事会", ids["监事会"]),
            _unknown("bumen_tongcheng", "「各部门」在本页为统称，未被逐一列名", ids["各部门"]),
        ]

    result = _run(tmp_path, build, lines)
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    # The page never placed 各部门 as a body; the UNKNOWN says what it is instead. 监事会 is
    # named by no UNKNOWN and stays.
    assert keys == {"jianshihui"}
    attribution = result.producer_attribution
    assert attribution["dropped_invalid_items"]["label_reported_as_unresolved"] == 1
    assert [row["item_key"] for row in attribution["item_contract_drops"]
            if row["rule"] == "label_reported_as_unresolved"] == ["bumen"]
    # The UNKNOWN that named it is kept whole, in run evidence: it says what 各部门 means
    # here, which is a statement about the reading and not a fact a Wiki may cite.
    assert [item.key for item in result.semantic_candidate.items if item.kind == "unknown"] == []
    diagnostics = {row["key"]: row for row in result.run_diagnostics}
    assert diagnostics["bumen_tongcheng"]["reason"] == "absence_without_scope"
    assert diagnostics["bumen_tongcheng"]["destination"] == "run_evidence"


def test_a_name_only_an_unknown_touches_is_not_a_reason_to_drop_it(tmp_path):
    lines = ["组织升级小组研讨确定各部门职责与岗位设置", "向变革委员会汇报决策", "水务局"]

    def build(evidence):
        ids = _ids(evidence)
        return [
            _entity("zuzhi_shengji_xiaozu", "组织升级小组", ids[lines[0]]),
            _entity("biange_weiyuanhui", "变革委员会", ids[lines[1]]),
            _entity("shuiwuju", "水务局", ids[lines[2]]),
            {"kind": "claim", "key": "xiaozu_ding_bumen_zhize",
             "meaning": "「组织升级小组研讨确定各部门职责与岗位设置」",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [ids[lines[0]]]},
            {"kind": "claim", "key": "xiang_weiyuanhui_huibao",
             "meaning": "「向变革委员会汇报决策」",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [ids[lines[1]]]},
            _unknown("zuzhi_shengji_xiaozu_zucheng",
                     "「组织升级小组」的组成、负责人及与各部门的关系未在本页说明。", ids[lines[0]]),
            _unknown("biange_weiyuanhui_zucheng",
                     "「变革委员会」在本页只作为汇报决策的对象出现，其组成、性质与职权未说明。",
                     ids[lines[1]]),
            _unknown("shuiwuju_guanxi", "「水务局」与集团之间的关系性质未说明", ids[lines[2]]),
        ]

    result = _run(tmp_path, build, lines)
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    # An UNKNOWN says what is unknown about these names, not that they are not things. 水务局
    # is named by no claim, and that is not a refusal either: its box is on the page.
    assert keys == {"zuzhi_shengji_xiaozu", "biange_weiyuanhui", "shuiwuju"}
    attribution = result.producer_attribution
    assert "label_reported_as_unresolved" not in attribution["dropped_invalid_items"]


def test_a_two_character_name_matches_only_inside_quotes(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [
            _entity("kehu", "客户", ids["客户与水务局"]),
            _unknown("kehu_bianjie", "客户 作为 客户 的边界未在本页说明", ids["客户与水务局"]),
        ]

    result = _run(tmp_path, build, ["客户与水务局"])
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    # Written bare inside a sentence, 客户 is a word the UNKNOWN happens to use, not the name
    # it reports; only a quoted name is that name.
    assert keys == {"kehu"}
    assert "label_reported_as_unresolved" not in result.producer_attribution["dropped_invalid_items"]


def test_a_name_the_card_places_is_never_dropped_as_a_label(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [
            _entity("dangweihui", "党委会", ids["党委会"]),
            _entity("yifengongsi", "一分公司", ids["一分公司"]),
            {"kind": "relation", "key": "yi_li_jituan", "meaning": "「一分公司」列于「党委会」之下",
             "subject": "yifengongsi", "object": "dangweihui", "predicate": "隶属",
             "relation_source": "LAYOUT", "layout_ref": "org.md 版面",
             "evidence_class": "INFERRED",
             "evidence_refs": [ids["一分公司"], ids["党委会"]]},
            _unknown("bumen_dingyi", "「党委会」「一分公司」在本页为统称，未被逐一列名", ids["党委会"]),
        ]

    result = _run(tmp_path, build, ["党委会", "一分公司"])
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    # Both names are joined by the layout line, so neither is a label however the UNKNOWN
    # is worded.
    assert keys == {"dangweihui", "yifengongsi"}
    assert "label_reported_as_unresolved" not in result.producer_attribution["dropped_invalid_items"]


def test_the_contract_states_the_rule_to_the_reader():
    from catalyst_platform.understand_semantic import semantic_extraction_rules

    rules = semantic_extraction_rules(None)
    assert "open no entity for each name" in rules
    assert "never an entity on its own" in rules


def test_the_contract_states_the_label_boundary_to_the_reader():
    from catalyst_platform.understand_semantic import semantic_extraction_rules

    rules = semantic_extraction_rules(None)
    # 只有名字的格子是实体，不是陈述
    assert "names that thing and nothing more" in rules
    # 括号人数是关于岗位的一条 claim，证据是写数字的那一格，不是粘在名字上
    assert "is that post's own establishment" in rules
    assert "its evidence is the cell that writes the number" in rules
    # 同形态的格子落同一类（P12）
    assert "Two cells written the same" in rules
