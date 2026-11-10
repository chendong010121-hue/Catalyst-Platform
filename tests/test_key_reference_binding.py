"""A reference may bind by letter case; it may not become a name of its own.

Owner's contract, 2026-11-02: a technical key may be referenced with ASCII case
differences, but only when exactly one declaration in what this run allowed can own that
spelling; business entities are never merged over it. Four consequences are checked here
beside the six cases the contract named:

* an exact match takes the path it always took, and nothing is recorded as rewritten;
* a case-only match points the reference at the declaration and records both spellings;
* two declarations that share a spelling leave neither available - nothing picks one;
* a spelling no declaration carries, or one outside what this run allowed, stays
  unresolved and is named by the rule that refused it;
* a bound endpoint says nothing about the row's standing: a duty whose holder resolved
  is still pending when the passage does not carry its claim;
* no key, item id, display name or alias is decided here.
"""
from __future__ import annotations

from pathlib import Path

from catalyst_platform.semantic_wiki import _reading_qualification
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

LINE = "投资管理中心与市场营销中心整合为市场营销中心，投资管理中心负责月度经营分析。"


def _base(tmp_path, text=LINE):
    source = tmp_path / "org.md"
    source.write_text(text, encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("case-binding", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path)
    return result, result.evidence_refs[0].evidence_id


def _entities(evidence_id):
    return [
        {"kind": "entity", "key": "touzi_guanli_zhongxin", "meaning": "「投资管理中心」",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
        {"kind": "entity", "key": "shichang_yingxiao_zhongxin", "meaning": "「市场营销中心」",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
    ]


def _event(evidence_id, **overrides):
    row = {"kind": "event", "key": "zhenghe_shichang", "predicate": "整合",
           "meaning": "「投资管理中心」与「市场营销中心」整合为市场营销中心",
           "subject": "touzi_guanli_zhongxin", "object": "shichang_yingxiao_zhongxin",
           "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
           "from": ["touzi_guanli_zhongxin"], "to": ["shichang_yingxiao_zhongxin"]}
    row.update(overrides)
    return row


def _duty(evidence_id, **overrides):
    row = {"kind": "duty", "key": "yuedu_jingying", "predicate": "负责",
           "meaning": "负责月度经营分析", "subject": "touzi_guanli_zhongxin",
           "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}
    row.update(overrides)
    return row


def _attach(base, items, *, endpoint_keys=None):
    return UnderstandPort().attach_producer_items(
        base, producer_kind="CODEX_EXTERNAL", producer_invocation_id="call_case",
        items=items, endpoint_keys=endpoint_keys)


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def _bound(result):
    return result.producer_attribution["key_references_bound"]


# --- 1. exact ----------------------------------------------------------------


def test_a_reference_spelled_as_declared_is_not_rewritten(tmp_path):
    base, evidence_id = _base(tmp_path)

    result = _attach(base, [*_entities(evidence_id), _event(evidence_id)])

    item = _by_key(result)["zhenghe_shichang"]
    assert item.uncertainty is None
    assert item.event_from == ("touzi_guanli_zhongxin",)
    assert item.event_to == ("shichang_yingxiao_zhongxin",)
    assert _bound(result) == []
    assert result.producer_attribution["key_references_bound_count"] == 0


# --- 2. one declaration, letter case the only difference ----------------------


def test_a_reference_that_differs_only_in_case_binds_to_the_declaration(tmp_path):
    base, evidence_id = _base(tmp_path)

    result = _attach(base, [*_entities(evidence_id), _event(
        evidence_id, **{"from": ["touzi_guanli_zhongxin", "Shichang_Yingxiao_Zhongxin"],
                        "to": ["shichang_yingxiao_zhongxin"]})])

    item = _by_key(result)["zhenghe_shichang"]
    assert item.uncertainty is None
    # The row carries the declaration; the spelling it arrived with is in the record.
    assert item.event_from == ("touzi_guanli_zhongxin", "shichang_yingxiao_zhongxin")
    assert item.event_to == ("shichang_yingxiao_zhongxin",)
    assert _bound(result) == [{"item_key": "zhenghe_shichang", "field": "from",
                               "as_written": "Shichang_Yingxiao_Zhongxin",
                               "bound_to": "shichang_yingxiao_zhongxin"}]


def test_a_relation_and_a_duty_bind_the_same_way(tmp_path):
    base, evidence_id = _base(tmp_path)
    relation = {"kind": "relation", "key": "touzi_shichang", "predicate": "汇报",
                "meaning": "「投资管理中心」汇报给「市场营销中心」",
                "subject": "Touzi_Guanli_Zhongxin", "object": "shichang_yingxiao_zhongxin",
                "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}

    result = _attach(base, [*_entities(evidence_id), relation,
                            _duty(evidence_id, subject="Touzi_Guanli_Zhongxin")])

    rows = _by_key(result)
    assert (rows["touzi_shichang"].subject, rows["touzi_shichang"].object) == (
        "touzi_guanli_zhongxin", "shichang_yingxiao_zhongxin")
    assert rows["yuedu_jingying"].subject == "touzi_guanli_zhongxin"
    assert {row["field"] for row in _bound(result)} == {"subject"}


# --- 3. two declarations, one spelling ---------------------------------------


def test_two_declarations_that_share_a_spelling_leave_neither_available(tmp_path):
    base, evidence_id = _base(tmp_path)
    twins = [
        {"kind": "entity", "key": "zhongxin", "meaning": "「投资管理中心」",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
        {"kind": "entity", "key": "Zhongxin", "meaning": "「市场营销中心」",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
    ]

    result = _attach(base, [*twins, _event(
        evidence_id, **{"from": ["ZHONGXIN"], "to": ["zhongxin"]})])

    item = _by_key(result)["zhenghe_shichang"]
    # Neither twin is chosen: the row is kept, refused, and names the spelling.
    assert item.uncertainty == "degraded:event_endpoint_not_declared:ZHONGXIN"
    assert item.event_from == () and item.event_to == ()
    assert _bound(result) == []
    # And the two declarations are still two rows, each with the key it wrote.
    assert {row.key for row in result.semantic_candidate.items
            if row.kind == "entity"} == {"zhongxin", "Zhongxin"}


# --- 4. nothing declares it --------------------------------------------------


def test_a_reference_no_declaration_carries_stays_unresolved_and_is_named(tmp_path):
    base, evidence_id = _base(tmp_path)

    result = _attach(base, [*_entities(evidence_id), _event(
        evidence_id, **{"from": ["weixuan_danwei"], "to": ["shichang_yingxiao_zhongxin"]})])

    item = _by_key(result)["zhenghe_shichang"]
    assert item.uncertainty == "degraded:event_endpoint_not_declared:weixuan_danwei"
    assert item.event_from == () and item.event_to == ()
    assert _bound(result) == []


# --- 5. outside what this run allowed ---------------------------------------


def test_a_reference_outside_the_allowed_endpoints_is_not_bound(tmp_path):
    base, evidence_id = _base(tmp_path)
    # The candidate holds both units; this run allowed only one of them as an endpoint.
    allowed = ["touzi_guanli_zhongxin"]

    result = _attach(base, [*_entities(evidence_id), _event(
        evidence_id, **{"from": ["Touzi_Guanli_Zhongxin"],
                        "to": ["Shichang_Yingxiao_Zhongxin"]})], endpoint_keys=allowed)

    item = _by_key(result)["zhenghe_shichang"]
    assert item.uncertainty == "degraded:event_endpoint_not_declared:Shichang_Yingxiao_Zhongxin"
    assert item.event_from == () and item.event_to == ()
    # The one reference inside the allowed range still binds, and only it is recorded.
    assert _bound(result) == [{"item_key": "zhenghe_shichang", "field": "from",
                               "as_written": "Touzi_Guanli_Zhongxin",
                               "bound_to": "touzi_guanli_zhongxin"}]


# --- 6. bound is not confirmed ----------------------------------------------


def test_a_bound_holder_does_not_confirm_the_duty_it_joins(tmp_path):
    # Two units, two duties: a claim that stitches the two clauses belongs to neither.
    base, evidence_id = _base(
        tmp_path, "投资管理中心负责月度经营分析，市场营销中心负责预算复核。")
    stitched = _duty(evidence_id, subject="Touzi_Guanli_Zhongxin",
                     meaning="负责月度经营分析，负责预算复核")

    result = _attach(base, [*_entities(evidence_id), stitched])

    item = _by_key(result)["yuedu_jingying"]
    assert item.subject == "touzi_guanli_zhongxin"
    # Binding an endpoint decides no standing: the candidate hands on no qualification.
    assert item.qualification is None and item.verification is None
    # The gate the store runs says the same thing about the row the holder resolved for.
    qualification, verification, basis = _reading_qualification(
        "duty", quote="投资管理中心负责月度经营分析，市场营销中心负责预算复核。",
        names={"touzi_guanli_zhongxin": "投资管理中心",
               "shichang_yingxiao_zhongxin": "市场营销中心"},
        holder=item.subject, evidence_class="observed_from_source",
        meaning=item.meaning)
    assert (qualification, verification) == ("pending", "unconfirmed")
    assert basis == "duty_attached_to_another_unit"


# --- 7. no identity is decided here -----------------------------------------


def test_binding_a_reference_leaves_every_declaration_as_it_was(tmp_path):
    base, evidence_id = _base(tmp_path)
    declared = _entities(evidence_id)

    plain = _attach(base, [*declared, _event(evidence_id)])
    bound = _attach(base, [*declared, _event(
        evidence_id, **{"from": ["Shichang_Yingxiao_Zhongxin"]})])

    def identities(result):
        return [(row.item_id, row.kind, row.key, row.meaning)
                for row in result.semantic_candidate.items if row.kind == "entity"]

    # The same declaration, the same item id, the same name: a reference moved, nothing
    # else did.
    assert identities(plain) == identities(bound)
    # The entity rows are not the ones the record says were rewritten.
    assert _bound(plain) == []
    assert {row["item_key"] for row in _bound(bound)} == {"zhenghe_shichang"}


# --- 8. the record keeps both spellings ----------------------------------------


def test_the_runs_record_keeps_the_spelling_and_the_declaration(tmp_path):
    import json

    from catalyst_platform.semantic_method import producer_items, write_record

    base, evidence_id = _base(tmp_path)
    result = _attach(base, [*_entities(evidence_id), _event(
        evidence_id, **{"from": ["Shichang_Yingxiao_Zhongxin"]})])

    written = write_record(
        tmp_path / "record", original=result, repaired=producer_items(result),
        submitted=producer_items(result), stored=result,
        identity={"method": {}, "repairs": {}, "builtin_skills": {}},
        validation={}, segment_budget={"entities": 8, "other_items": 16})
    record = json.loads(Path(written["path"]).read_text(encoding="utf-8"))

    # The stored row names the declaration; the record still holds what it was called.
    mapping = record["validator"]["producer_attribution"]["key_references_bound"]
    assert mapping == [{"item_key": "zhenghe_shichang", "field": "from",
                        "as_written": "Shichang_Yingxiao_Zhongxin",
                        "bound_to": "shichang_yingxiao_zhongxin"}]


# --- 9. every rewrite is in the record -----------------------------------------


def test_every_rewritten_reference_is_in_the_record_not_just_the_first_twenty(tmp_path):
    base, evidence_id = _base(tmp_path)
    events = [{"kind": "event", "key": f"zhenghe_{index:02d}", "predicate": "整合",
               "meaning": "「投资管理中心」与「市场营销中心」整合为市场营销中心",
               "subject": "touzi_guanli_zhongxin",
               "object": "shichang_yingxiao_zhongxin",
               "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
               "from": ["Touzi_Guanli_Zhongxin"],
               "to": ["shichang_yingxiao_zhongxin"]}
              for index in range(25)]

    result = _attach(base, [*_entities(evidence_id), *events])

    attribution = result.producer_attribution
    bound = attribution["key_references_bound"]
    # The list is the record, not a sample of it: the count and the rows agree at a size
    # no sample list would reach, so any one rewrite can be looked up by its row.
    assert attribution["key_references_bound_count"] == 25
    assert len(bound) == 25
    assert {row["item_key"] for row in bound} == {f"zhenghe_{index:02d}" for index in range(25)}
    assert {(row["as_written"], row["bound_to"]) for row in bound} == {
        ("Touzi_Guanli_Zhongxin", "touzi_guanli_zhongxin")}
