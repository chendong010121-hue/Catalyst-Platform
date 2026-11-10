"""A page that prints a post beside what it does has stated a duty.

The contract has carried `kind=duty` with a holder from the start, but the semantic
prompt's list of kinds never offered it and said in as many words "claim for duties",
so no card ever held one duty: 2d read 0 while the duties sat on the card as claims,
word for word. This closes that gap on the method side - the rubric's 2d already reads
`kind=duty`, so nothing about the scale moves - and keeps the two guards a duty needs
to be a fact: the holder is a name this answer declares, and the work item is written
in the page's own words rather than the reader's.
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

TEXT = ("分公司经理全面负责分公司经营，主抓市场营销。\n"
        "市场副经理专注分公司区域市场开发。\n"
        "各部门负责技术质量管理工作。\n")

NAMES = {"fengongsi_jingli": "分公司经理", "shichang_fujingli": "市场副经理"}


class _Answer:
    model = "stub-duties"
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
        UnderstandingRequest("duties", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_duties",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def _duty(key, holder, meaning, evidence, quote_name="分公司经理"):
    return {"kind": "duty", "key": key, "subject": holder, "meaning": meaning,
            "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [_evidence(evidence, quote_name)]}


def test_a_work_item_a_named_post_owns_is_a_duty_row(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            _duty("duty_jingli", "fengongsi_jingli", "全面负责分公司经营，主抓市场营销", evidence)]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_jingli"]
    assert duty.kind == "duty"
    assert duty.subject == "fengongsi_jingli"
    assert duty.meaning == "全面负责分公司经营，主抓市场营销"
    assert duty.evidence_class == "observed_from_source"
    assert duty.uncertainty is None
    assert result.producer_attribution["item_contract_degraded_count"] == 0


def test_a_duty_hung_on_a_name_nothing_declared_is_kept_and_named(tmp_path):
    """「各部门负责…」 says somebody; it does not name who, so it cannot be a fact."""
    def build(evidence):
        return _units(evidence) + [
            _duty("duty_quanbu", "gebumen", "负责技术质量管理工作", evidence,
                  quote_name="各部门")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_quanbu"]
    assert duty.kind == "duty"
    assert duty.evidence_class == "unresolved"
    assert duty.uncertainty == "degraded:duty_holder_not_declared:gebumen"


def test_a_duty_written_in_the_readers_own_words_is_refused(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            _duty("duty_zongchou", "fengongsi_jingli", "统筹一切事务", evidence)]

    result = _run(tmp_path, build)
    # The holder resolves, but the work item is in the reader's words rather than the page's,
    # so nothing about this duty was established: it is run evidence, not a candidate.
    assert "duty_zongchou" not in _by_key(result)
    diagnostic = {row["key"]: row for row in result.run_diagnostics}["duty_zongchou"]
    assert diagnostic["reason"] == "duty_text_not_in_evidence"
    assert diagnostic["destination"] == "run_evidence"


def test_a_work_item_with_no_holder_is_not_yet_a_duty(tmp_path):
    def build(evidence):
        return _units(evidence) + [
            {"kind": "duty", "key": "duty_nobody", "meaning": "负责技术质量管理工作",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_evidence(evidence, "各部门")]}]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_nobody"]
    assert duty.kind == "duty"
    assert duty.evidence_class == "unresolved"
    assert duty.uncertainty == "degraded:duty_holder_required:kind=duty"


def test_a_duty_is_not_turned_into_a_claim_by_the_sentence_screen(tmp_path):
    """The prose screen moves a *name* that reads like a sentence into a claim.

    It must not move a duty there: a duty row's meaning is a sentence by design, and
    the row that says who owns the work item would otherwise disappear into prose.
    """
    def build(evidence):
        return _units(evidence) + [
            _duty("duty_shichang", "shichang_fujingli", "专注分公司区域市场开发", evidence,
                  quote_name="市场副经理")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_shichang"]
    assert duty.kind == "duty"
    assert duty.evidence_class == "observed_from_source"


def test_a_duty_carries_the_state_of_the_page_it_came_from(tmp_path):
    """The work a post owns on the proposed chart is proposed work.

    The label is the page's, not a category of row: leaving it off a duty put a duty-only
    cell in a position where the owner's answer about which arrangement it draws had no
    row to sit on.
    """
    def build(evidence):
        row = _duty("duty_jingli", "fengongsi_jingli", "全面负责分公司经营，主抓市场营销", evidence)
        row["scope_state"] = "proposed"
        return _units(evidence) + [row]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_jingli"]
    assert duty.scope_state == "proposed"
    assert {"item_key": "duty_jingli", "rule": "scope_state_not_applicable"} not in         result.producer_attribution["item_contract_drops"]


def test_a_duty_still_refuses_a_state_word_the_contract_never_defined(tmp_path):
    def build(evidence):
        row = _duty("duty_jingli", "fengongsi_jingli", "全面负责分公司经营，主抓市场营销", evidence)
        row["scope_state"] = "maybe"
        return _units(evidence) + [row]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_jingli"]
    assert duty.scope_state is None
    assert {"item_key": "duty_jingli", "rule": "scope_state_unsupported"} in         result.producer_attribution["item_contract_drops"]


def test_the_contract_names_duty_and_its_two_guards_to_the_reader():
    from catalyst_platform.understand_semantic import semantic_extraction_rules

    rules = semantic_extraction_rules(None)
    assert "duty for a work item a named thing owns" in rules
    assert "holder's entity key in subject" in rules
    # 一句话一条 duty；同一句不再另出 claim——这是「条目膨胀」和「同段写两遍」的唯一闸门
    assert "One sentence is one duty" in rules
    assert "not also written as a claim" in rules
    # 原文措辞的门槛写给模型，与 T1.10 的 6 字对齐
    assert "at least six characters" in rules
    # 状态是页面的词：duty 与它旁边的单位同一个词，不再是「不许带」
    assert "A duty carries the state of the page it came from" in rules
    assert "A duty row carries no scope_state" not in rules
