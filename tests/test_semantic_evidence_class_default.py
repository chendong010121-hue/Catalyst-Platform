"""一条忘了写 evidence_class 的行，不该让整张卡作废。

真卡 m5a 就是这样死的：模型在 slide7 写了一条「两个合并事件的生效时间在证据中未出现」的
UNKNOWN，带了 uncertainty、scope_refs、observed_absence，唯独漏了 evidence_class。
抽取层当时把它当硬违规抛出，于是 15 次付费请求和旁边三百多条行一起作废。

这条行本身是有内容的（有陈述、有检索范围、有说明），所以现在的处置是：保下来、
降成 unresolved、把规则名写在归因里。不完整是合法的，作废不是。
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


class _Answer:
    model = "stub-evidence-class"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _run(tmp_path, build):
    source = tmp_path / "deck.md"
    source.write_text("一分公司合并到智信。\n", encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("evidence-class", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE, scope_id="scope_class",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _unknown_without_class(evidence):
    return {"kind": "unknown", "key": "hebing_shengxiao_shijian",
            "meaning": "两个合并事件的生效时间在证据中未出现",
            "uncertainty": "证据只陈述合并内容，未给出生效日期",
            "scope_refs": [evidence[0]["evidence_id"]],
            "observed_absence": "未见生效日期"}


def test_a_row_that_forgets_its_evidence_class_does_not_cost_the_card(tmp_path):
    def build(evidence):
        return [
            {"kind": "entity", "key": "yi_fengongsi", "meaning": "一分公司",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence[0]["evidence_id"]]},
            _unknown_without_class(evidence),
        ]

    result = _run(tmp_path, build)
    rows = {item.key: item for item in result.semantic_candidate.items}
    assert rows["yi_fengongsi"].evidence_class == "observed_from_source"
    kept = rows["hebing_shengxiao_shijian"]
    assert kept.kind == "unknown"
    assert kept.evidence_class == "unresolved"
    attribution = result.producer_attribution
    assert attribution["evidence_class_defaulted_count"] == 1
    assert attribution["evidence_class_defaulted"] == [
        {"item_key": "hebing_shengxiao_shijian", "rule": "evidence_class_missing", "as": "unknown"}]


def test_a_class_the_contract_never_defined_is_named_and_kept(tmp_path):
    def build(evidence):
        row = _unknown_without_class(evidence)
        return [{**row, "evidence_class": "PENDING_REVIEW"}]

    result = _run(tmp_path, build)
    kept = {item.key: item for item in result.semantic_candidate.items}["hebing_shengxiao_shijian"]
    assert kept.evidence_class == "unresolved"
    assert result.producer_attribution["evidence_class_defaulted"] == [
        {"item_key": "hebing_shengxiao_shijian", "rule": "evidence_class_unsupported",
         "as": "unknown", "named": "PENDING_REVIEW"}]
