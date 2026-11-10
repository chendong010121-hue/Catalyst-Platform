"""An identity a person decided is folded into the graph, not asked again.

The queue names a pair and merges nothing: a deck draws its current chart and its proposal
with the same words, so only a person can say that 水利集团 and 天津市水利工程集团有限公司
are one company. Once they do, the answer arrives with the next reading and the two keys
become one, taking the branch's second edge with them.
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
from catalyst_platform.understand_wiki import (
    UnderstandWikiError,
    admission_plan,
    apply_admission_decisions,
)


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_identity_decision",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_identity_decision",
        requested_depth="semantic",
        budget_steps=16,
    )


class _Rows:
    model = "stub-identity-decision-model"
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


def _entity(key, meaning, evidence_id, scope_state=None):
    row = {"kind": "entity", "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
           "evidence_refs": [evidence_id]}
    if scope_state is not None:
        row["scope_state"] = scope_state
    return row


def _relation(key, subject, target, meaning, ends, source="LAYOUT"):
    row = {"kind": "relation", "key": key, "meaning": meaning, "subject": subject, "object": target,
           "predicate": "隶属", "relation_source": source, "evidence_class": "INFERRED",
           "evidence_refs": list(ends)}
    if source == "LAYOUT":
        row["layout_ref"] = "org.md 版面：名称上下排布"
    return row


LINES = ["天津市水利工程集团有限公司", "水利集团", "一分公司"]
FULL = "tianjin_shuili_gongcheng_jituan_youxian_gongsi"
SHORT = "shuili_jituan"


def _two_keys_for_one_company(evidence, *, scope_states=(None, None)):
    ids = _ids(evidence)
    return [
        _entity(FULL, "天津市水利工程集团有限公司", ids["天津市水利工程集团有限公司"],
                scope_state=scope_states[0]),
        _entity(SHORT, "水利集团", ids["水利集团"], scope_state=scope_states[1]),
        _entity("yifengongsi", "一分公司", ids["一分公司"]),
        _relation("yi_li_quancheng", "yifengongsi", FULL,
                  "「一分公司」列于「天津市水利工程集团有限公司」之下",
                  [ids["一分公司"], ids["天津市水利工程集团有限公司"]]),
        _relation("yi_li_jiancheng", "yifengongsi", SHORT, "「一分公司」隶属「水利集团」",
                  [ids["一分公司"], ids["水利集团"]]),
    ]


def _run(tmp_path, build, decisions=None):
    source = tmp_path / "org.md"
    source.write_text("\n".join(LINES), encoding="utf-8")
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(build),
                                       identity_decisions=decisions)


ANSWER = [{"keys": [SHORT, FULL], "keep": FULL}]


def test_a_decided_pair_becomes_one_entity_with_one_edge(tmp_path):
    result = _run(tmp_path, _two_keys_for_one_company, ANSWER)
    items = result.semantic_candidate.items
    keys = {item.key for item in items if item.kind == "entity"}
    assert keys == {FULL, "yifengongsi"}
    [edge] = [item for item in items if item.kind == "relation"]
    assert (edge.subject, edge.object) == ("yifengongsi", FULL)
    attribution = result.producer_attribution
    [merge] = attribution["identity_merges"]
    assert merge["kept_key"] == FULL
    assert merge["alias_keys"] == [SHORT]
    # Both keys cited the company, so the surviving row keeps both passages.
    assert merge["evidence_count"] == 2
    assert attribution["dropped_invalid_items"]["relation_duplicated_by_identity_decision"] == 1
    assert "declared_identity_merge" in attribution["catalyst_transforms"]


def test_the_queue_does_not_ask_again(tmp_path):
    result = _run(tmp_path, _two_keys_for_one_company, ANSWER)
    assert result.producer_attribution["identity_candidates"] == []


def test_an_edge_between_the_two_names_becomes_a_self_loop_and_goes(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [
            _entity(FULL, "天津市水利工程集团有限公司", ids["天津市水利工程集团有限公司"]),
            _entity(SHORT, "水利集团", ids["水利集团"]),
            _relation("jituan_shu_jituan", SHORT, FULL, "「水利集团」列于「天津市水利工程集团有限公司」之下",
                      [ids["水利集团"], ids["天津市水利工程集团有限公司"]]),
        ]

    result = _run(tmp_path, build, ANSWER)
    assert [item for item in result.semantic_candidate.items if item.kind == "relation"] == []
    assert result.producer_attribution["dropped_invalid_items"]["relation_endpoints_are_the_same_item"] == 1


def test_a_decision_naming_a_key_that_is_not_here_is_reported(tmp_path):
    result = _run(tmp_path, _two_keys_for_one_company,
                  [{"keys": ["shuilijituan", FULL], "keep": FULL}])
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    assert keys == {FULL, SHORT, "yifengongsi"}
    [unapplied] = result.producer_attribution["identity_decisions_unapplied"]
    assert unapplied["rule"] == "identity_decision_unknown_key"
    assert unapplied["missing"] == ["shuilijituan"]
    # The pair is still open, so the queue still names it.
    assert result.producer_attribution["identity_candidate_count"] == 1


def test_two_decisions_that_point_at_each_other_merge_nothing(tmp_path):
    result = _run(tmp_path, _two_keys_for_one_company,
                  [{"keys": [SHORT, FULL], "keep": FULL}, {"keys": [SHORT, FULL], "keep": SHORT}])
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    assert keys == {FULL, SHORT, "yifengongsi"}
    assert result.producer_attribution["identity_merges"] == []
    rules = {row["rule"] for row in result.producer_attribution["identity_decisions_unapplied"]}
    assert "identity_decision_cycle" in rules


def test_the_current_chart_and_the_proposal_are_not_folded(tmp_path):
    def build(evidence):
        return _two_keys_for_one_company(evidence, scope_states=("current", "proposed"))

    result = _run(tmp_path, build, ANSWER)
    keys = {item.key for item in result.semantic_candidate.items if item.kind == "entity"}
    assert keys == {FULL, SHORT, "yifengongsi"}
    [unapplied] = result.producer_attribution["identity_decisions_unapplied"]
    assert unapplied["rule"] == "identity_decision_spans_two_states"


def test_a_fold_of_twenty_two_edges_is_counted_as_twenty_two(tmp_path):
    branches = [f"第{index}分公司" for index in range(1, 23)]

    def build(evidence):
        ids = _ids(evidence)
        rows = [_entity(FULL, "天津市水利工程集团有限公司", ids["天津市水利工程集团有限公司"]),
                _entity(SHORT, "水利集团", ids["水利集团"])]
        for index, name in enumerate(branches, start=1):
            rows.append(_entity(f"branch_{index}", name, ids[name]))
            rows.append(_relation(f"branch_{index}_quancheng", f"branch_{index}", FULL,
                                  f"「{name}」列于「天津市水利工程集团有限公司」之下",
                                  [ids[name], ids["天津市水利工程集团有限公司"]]))
            rows.append(_relation(f"branch_{index}_jiancheng", f"branch_{index}", SHORT,
                                  f"「{name}」隶属「水利集团」", [ids[name], ids["水利集团"]]))
        return rows

    source = tmp_path / "org.md"
    source.write_text("\n".join(LINES + branches), encoding="utf-8")
    result = UnderstandPort().understand(_request(source), source_root=tmp_path,
                                         semantic_provider=_Rows(build),
                                         identity_decisions=ANSWER)
    attribution = result.producer_attribution
    assert len([item for item in result.semantic_candidate.items
                if item.kind == "relation"]) == 22
    # The record keeps every row now, and the count still keeps all twenty-two.
    assert len(attribution["item_contract_drops"]) == 22
    assert attribution["item_contract_drops_omitted"] == 0
    assert attribution["dropped_invalid_items"]["relation_duplicated_by_identity_decision"] == 22


def test_the_review_says_the_answer_was_applied(tmp_path):
    from catalyst_platform.understand_verify import verification_integrity, verification_local_checks

    result = _run(tmp_path, _two_keys_for_one_company, ANSWER)
    attribution = result.producer_attribution
    checks = verification_local_checks(attribution, verification_integrity(attribution))
    [applied] = [row for row in checks if row["rule"] == "identity_decision_applied"]
    assert applied["merges"][0] == {"kept_key": FULL, "alias_keys": [SHORT], "evidence_count": 2}
    # The queue is settled, so the check that asks for an answer is gone.
    assert [row for row in checks if row["rule"] == "identity_decision_required"] == []

    unread = _run(tmp_path, _two_keys_for_one_company, [{"keys": ["nope", FULL], "keep": FULL}])
    checks = verification_local_checks(unread.producer_attribution,
                                       verification_integrity(unread.producer_attribution))
    [unapplied] = [row for row in checks if row["rule"] == "identity_decision_unapplied"]
    assert unapplied["decisions"][0]["rule"] == "identity_decision_unknown_key"


def test_the_plan_records_the_answer_for_the_next_reading(tmp_path):
    first = _run(tmp_path, _two_keys_for_one_company)
    plan = admission_plan(first)
    assert plan["identity_candidates"][0]["keys"] == [SHORT, FULL]
    plan = apply_admission_decisions(
        plan, [{"item_key": SHORT, "action": "same_identity", "after": FULL,
                "by": "owner", "time": "2026-10-30T14:00:00Z"}])
    [decision] = plan["identity_decisions"]
    assert decision["keys"] == [SHORT, FULL]
    assert decision["keep"] == FULL

    second = _run(tmp_path, _two_keys_for_one_company, plan["identity_decisions"])
    keys = {item.key for item in second.semantic_candidate.items if item.kind == "entity"}
    assert keys == {FULL, "yifengongsi"}
    assert second.producer_attribution["identity_candidates"] == []


def test_an_identity_answer_needs_a_key_this_plan_holds(tmp_path):
    first = _run(tmp_path, _two_keys_for_one_company)
    plan = admission_plan(first)
    try:
        apply_admission_decisions(plan, [{"item_key": SHORT, "action": "same_identity",
                                          "after": "shuilijituan", "by": "owner",
                                          "time": "2026-10-30T14:00:00Z"}])
    except UnderstandWikiError as error:
        assert error.code == "unknown_admission_item"
    else:
        raise AssertionError("a kept key this plan does not hold must be refused")


def test_an_identity_answer_is_between_two_entities(tmp_path):
    def build(evidence):
        ids = _ids(evidence)
        return [_entity(FULL, "天津市水利工程集团有限公司", ids["天津市水利工程集团有限公司"]),
                _entity(SHORT, "水利集团", ids["水利集团"]),
                {"kind": "claim", "key": "duty_finance", "meaning": "财务由集团统一管理",
                 "evidence_class": "SOURCE_DIRECT",
                 "evidence_refs": [ids["天津市水利工程集团有限公司"]]}]

    first = _run(tmp_path, build)
    plan = admission_plan(first)
    try:
        apply_admission_decisions(plan, [{"item_key": SHORT, "action": "same_identity",
                                          "after": "duty_finance", "by": "owner",
                                          "time": "2026-10-30T14:00:00Z"}])
    except UnderstandWikiError as error:
        assert error.code == "identity_needs_two_entities"
    else:
        raise AssertionError("a claim is not an identity another entity can stand on")
