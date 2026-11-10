"""Admission over a candidate: three groups, six actions, no model call."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from catalyst_platform.semantic_wiki import MAX_CANDIDATE_ITEMS
from catalyst_platform.understand_wiki import (
    ADMISSION_ACTIONS,
    UnderstandWikiError,
    admission_plan,
    apply_admission_decisions,
)


def _item(key, *, kind="claim", meaning="职责说明", evidence_class="observed_from_source",
          refs=("ev_1",), uncertainty=None, scope_refs=(), observed_absence=None, item_id=None,
          subject=None, object=None):
    return SimpleNamespace(item_id=item_id or f"item_{key}", key=key, kind=kind, meaning=meaning,
                           evidence_class=evidence_class, evidence_refs=tuple(refs),
                           uncertainty=uncertainty, scope_refs=tuple(scope_refs),
                           observed_absence=observed_absence, subject=subject, object=object)


def _result(items, attribution=None):
    return SimpleNamespace(semantic_candidate=SimpleNamespace(items=tuple(items)),
                           producer_attribution=attribution or {})


def test_a_clean_candidate_is_adopted_by_default():
    plan = admission_plan(_result([
        _item("duty"), _item("team", kind="entity", meaning="财务部门"),
        _item("approval", kind="unknown", evidence_class="unresolved", refs=(),
              scope_refs=("ev_1",), observed_absence="审批")]))
    assert plan["counts"] == {"default_adopt": 3, "pending": 0, "excluded": 0}
    assert set(plan["default_adopt"][0]) >= {"item_key", "kind", "meaning", "evidence_refs"}


def test_every_group_carries_a_reason_a_person_can_act_on():
    plan = admission_plan(_result([
        _item("duty"),
        _item("conflicted", meaning="同一键的另一种说法"),
        _item("loose", refs=()),
        _item("vague", kind="unknown", evidence_class="unresolved", refs=()),
        _item("odd", kind="slogan"),
        _item("clash", evidence_class="conflict"),
    ], {"duplicate_items_conflicting_meaning": [{"item_key": "conflicted"}]}))
    assert plan["counts"] == {"default_adopt": 1, "pending": 3, "excluded": 2}
    assert {row["item_key"]: row["reason"] for row in plan["pending"]} == {
        "conflicted": "duplicate_key_conflict", "loose": "no_evidence",
        "vague": "absence_without_scope"}
    assert {row["item_key"]: row["reason"] for row in plan["excluded"]} == {
        "odd": "harvest_unresolved_kind", "clash": "conflict_requires_review"}


def test_the_port_budget_sends_the_overage_to_pending_not_to_the_bin():
    plan = admission_plan(_result([_item(f"duty_{n}") for n in range(MAX_CANDIDATE_ITEMS + 20)]))
    assert plan["counts"]["default_adopt"] == MAX_CANDIDATE_ITEMS
    assert plan["counts"]["pending"] == 20
    assert {row["reason"] for row in plan["pending"]} == {"over_port_budget"}


def test_the_schemas_and_the_port_carry_the_same_number_of_items():
    for name in ("external_candidate_submission_v1.schema.json",
                 "external_candidate_submission_v2.schema.json"):
        schema = json.loads((Path(__file__).parents[1] / "schemas" / name).read_text(encoding="utf-8"))
        assert schema["properties"]["items"]["maxItems"] == MAX_CANDIDATE_ITEMS == 200


def test_an_edge_that_cannot_bring_its_ends_waits_instead_of_overflowing():
    # 150 edges over 150 separate pairs is 300 items: more than the port takes, and
    # publish refuses a selection wider than the budget whole. The edges from the tail
    # wait with the rows they cannot bring, so the plan never hands on what it cannot.
    items = []
    for index in range(150):
        items.append(_item(f"left_{index}", kind="entity", meaning=f"甲部门{index}"))
        items.append(_item(f"right_{index}", kind="entity", meaning=f"乙部门{index}"))
        items.append(_item(f"edge_{index}", kind="relation", meaning=f"甲部门{index}隶属乙部门{index}",
                           subject=f"left_{index}", object=f"right_{index}"))
    plan = admission_plan(_result(items))
    # An edge gives way together with the two ends only it needed, so the last one to
    # go can free three slots at once: the plan fills the budget or comes short of it,
    # never over.
    assert MAX_CANDIDATE_ITEMS - 2 <= plan["counts"]["default_adopt"] <= MAX_CANDIDATE_ITEMS
    adopted = {row["item_key"] for row in plan["default_adopt"]}
    ends = {row["item_key"].removeprefix("edge_") for row in plan["default_adopt"]
            if row["kind"] == "relation"}
    # Every adopted edge still has both of its ends; the edges that did not fit are
    # named for a person, not silently dropped.
    assert all(f"left_{index}" in adopted and f"right_{index}" in adopted for index in ends)
    waiting = {row["item_key"] for row in plan["pending"] if row["reason"] == "over_port_budget"}
    assert {"edge_149", "left_149", "right_149"} <= waiting


def test_the_plan_says_when_the_run_itself_lost_rows():
    plan = admission_plan(_result([_item("duty")], {
        "refused_units": [{"unit": "slide:3", "code": "invalid_json"}],
        "dropped_invalid_items": {"entity_name_not_in_evidence": 4}}))
    assert plan["coverage_gap"] is True
    assert plan["gaps"]["dropped_rows"] == {"entity_name_not_in_evidence": 4}
    assert plan["gaps"]["refused_units"] == ["slide:3"]


def test_the_six_actions_are_the_six_actions():
    # `same_identity` answers the identity queue: this item and the key in `after` are one
    # thing. `identity` still records which key an item stands on in the store.
    assert ADMISSION_ACTIONS == ("adopt", "unadopt", "rename", "describe", "identity",
                                 "same_identity", "restore")


def _paged(items, locators):
    """A result whose items cite evidence on named pages, so the plan can spread them."""
    result = _result(items)
    result.to_dict = lambda: {
        "evidence_refs": [
            {"evidence_id": f"ev_{index}", "locator": locator, "quote": "原文",
             "source_id": "source_1", "source_revision": "rev_1",
             "source_sha256": "0" * 64, "span_sha256": "1" * 64}
            for index, locator in enumerate(locators)],
        "semantic_candidate": {"items": [
            {"item_id": item.item_id, "kind": item.kind, "key": item.key, "meaning": item.meaning,
             "evidence_class": item.evidence_class, "evidence_refs": list(item.evidence_refs)}
            for item in items]},
    }
    return result


def test_a_long_first_page_does_not_take_the_whole_budget():
    items = ([_item(f"first_{n}", refs=("ev_0",)) for n in range(5)]
             + [_item(f"second_{n}", refs=("ev_1",)) for n in range(5)])
    plan = admission_plan(_paged(items, ["ppt/slides/slide1.xml#text:1",
                                         "ppt/slides/slide2.xml#text:1"]), max_items=4)
    assert [row["item_key"] for row in plan["default_adopt"]] == [
        "first_0", "second_0", "first_1", "second_1"]
    assert plan["counts"] == {"default_adopt": 4, "pending": 6, "excluded": 0}
    assert {row["reason"] for row in plan["pending"]} == {"over_port_budget"}


def test_every_page_is_heard_before_a_page_is_heard_twice_and_the_plan_repeats():
    items = ([_item(f"p1_{n}", refs=("ev_0",)) for n in range(2)]
             + [_item(f"p2_{n}", refs=("ev_1",)) for n in range(2)]
             + [_item(f"p3_{n}", refs=("ev_2",)) for n in range(3)])
    locators = ["ppt/slides/slide1.xml#text:1", "ppt/slides/slide2.xml#text:1",
                "ppt/slides/slide3.xml#text:1"]
    first = admission_plan(_paged(items, locators), max_items=5)
    again = admission_plan(_paged(items, locators), max_items=5)
    assert [row["item_key"] for row in first["default_adopt"]] == [
        "p1_0", "p2_0", "p3_0", "p1_1", "p2_1"]
    assert first == again


def test_a_result_that_cannot_name_its_pages_keeps_document_order():
    plan = admission_plan(_result([_item(f"duty_{n}") for n in range(6)]), max_items=3)
    assert [row["item_key"] for row in plan["default_adopt"]] == ["duty_0", "duty_1", "duty_2"]


def test_a_relation_late_in_its_page_survives_a_tight_budget():
    items = ([_item("dep_a", kind="entity", meaning="财务部"),
              _item("dep_b", kind="entity", meaning="法务部"),
              _item("joins", kind="relation", refs=("ev_0",), subject="dep_a", object="dep_b")]
             + [_item(f"duty_{n}") for n in range(8)])
    plan = admission_plan(_paged(items, ["ppt/slides/slide1.xml#text:1"]), max_items=3)
    assert [row["item_key"] for row in plan["default_adopt"]] == ["joins", "dep_a", "dep_b"]


def test_a_relation_brings_the_two_ends_it_joins_into_the_budget():
    # The ends sit behind the cutoff: adopting the edge without them would only lose it
    # again at publish, which drops a relation whose endpoint was not selected.
    items = ([_item("dep_a", kind="entity", meaning="财务部", refs=("ev_0",)),
              _item("dep_b", kind="entity", meaning="法务部", refs=("ev_1",))]
             + [_item(f"duty_{n}", refs=("ev_2",)) for n in range(6)]
             + [_item("joins", kind="relation", refs=("ev_2",), subject="dep_a", object="dep_b")])
    plan = admission_plan(_paged(items, ["ppt/slides/slide1.xml#text:1",
                                         "ppt/slides/slide2.xml#text:1",
                                         "ppt/slides/slide3.xml#text:1"]), max_items=3)
    assert [row["item_key"] for row in plan["default_adopt"]] == ["joins", "dep_a", "dep_b"]
    assert plan["counts"] == {"default_adopt": 3, "pending": 6, "excluded": 0}


def test_a_relation_whose_end_cannot_be_harvested_is_named_not_adopted():
    items = [_item("dep_a", kind="entity", meaning="财务部"),
             _item("组织升级小组", kind="entity", meaning="组织升级小组"),   # a key the store cannot hold
             _item("joins", kind="relation", subject="dep_a", object="组织升级小组")]
    plan = admission_plan(_result(items))
    assert [row["item_key"] for row in plan["default_adopt"]] == ["dep_a"]
    assert {row["item_key"]: row["reason"] for row in plan["pending"]} == {
        "组织升级小组": "key_not_storable", "joins": "relation_endpoint_not_harvestable"}


def test_a_key_the_candidate_already_uses_goes_to_pending_not_to_the_publish():
    repeated = dict(kind="unknown", evidence_class="unresolved", refs=("ev_1",),
                    scope_refs=("ev_1",), observed_absence="审批")
    plan = admission_plan(_result([_item("approval_scope", item_id="item_a", **repeated),
                                   _item("approval_scope", item_id="item_b", **repeated)]))
    assert plan["counts"] == {"default_adopt": 1, "pending": 1, "excluded": 0}
    assert [row["reason"] for row in plan["pending"]] == ["duplicate_key_in_candidate"]


def test_an_absence_without_its_scope_is_never_adopted():
    # The two rows a deck produces when a page could not be read: an absence with no scope
    # and no phrasing looked for. Neither is a candidate, so neither is adopted. The first
    # row is named for what it lacks; the second repeats its key, so it is named as the
    # duplicate it is - a row that never gets as far as being asked what it lacks.
    repeated = dict(kind="unknown", evidence_class="unresolved", refs=("ev_1",), uncertainty="未读取")
    plan = admission_plan(_result([_item("visual_content", item_id="item_a", **repeated),
                                   _item("visual_content", item_id="item_b", **repeated)]))
    assert plan["counts"] == {"default_adopt": 0, "pending": 2, "excluded": 0}
    assert {row["reason"] for row in plan["pending"]} == {"absence_without_scope",
                                                         "duplicate_key_in_candidate"}


def test_a_key_the_store_cannot_name_goes_to_pending_where_a_person_can_rename_it():
    plan = admission_plan(_result([_item("shichang_yIngxiao_zhongxin", kind="entity",
                                         meaning="市场营销中心")]))
    assert plan["counts"] == {"default_adopt": 0, "pending": 1, "excluded": 0}
    assert [row["reason"] for row in plan["pending"]] == ["key_not_storable"]


def _renderable(items, quotes):
    """A result that can render itself, so the plan can size each projection line."""
    result = _result(items)
    result.to_dict = lambda: {
        "evidence_refs": [{"evidence_id": "ev_1", "locator": "line:1", "quote": quote,
                           "source_revision": "rev_1", "source_sha256": "0" * 64,
                           "span_sha256": "1" * 64} for quote in quotes],
        "semantic_candidate": {"items": [
            {"item_id": item.item_id, "kind": item.kind, "key": item.key, "meaning": item.meaning,
             "evidence_class": item.evidence_class, "evidence_refs": list(item.evidence_refs)}
            for item in items]},
    }
    return result


def test_a_passage_the_projection_could_not_store_is_pending_not_adopted():
    plan = admission_plan(_renderable([_item("huge")], ["长" * 9000]))
    assert plan["counts"] == {"default_adopt": 0, "pending": 1, "excluded": 0}
    assert [row["reason"] for row in plan["pending"]] == ["projection_anchor_too_large"]


def test_a_name_that_cites_many_passages_is_not_too_large():
    # One name may be spelled on a dozen pages: the row that records it is longer than any
    # one of the passages, and it is the passages the store bounds, not the count of them.
    quotes = [f"财务部门在第{index}项里报送经营分析" for index in range(12)]
    plan = admission_plan(_renderable([_item("finance", kind="entity", meaning="财务部门")], quotes))
    assert plan["counts"] == {"default_adopt": 1, "pending": 0, "excluded": 0}


def test_a_line_the_projection_can_store_is_adopted_without_a_size_remark():
    plan = admission_plan(_renderable([_item("duty")], ["财务部门负责月度经营分析。"]))
    assert plan["counts"] == {"default_adopt": 1, "pending": 0, "excluded": 0}


def _decide(key, action, after=None, by="owner", time="2026-10-29T02:00:00Z"):
    return {"item_key": key, "action": action, "after": after, "by": by, "time": time}


def test_unadopt_takes_an_adopted_item_out_of_the_selection():
    plan = admission_plan(_result([_item("duty"), _item("team", kind="entity")]))
    result = apply_admission_decisions(plan, [_decide("team", "unadopt")])
    assert result["selection"] == ["duty"]
    assert [row["item_key"] for row in result["pending"]] == ["team"]
    assert result["pending"][0]["reason"] == "owner_unadopted"
    [row] = result["decisions"]
    assert (row["action"], row["before"], row["after"], row["by"]) == ("unadopt", "adopt", "pending", "owner")


def test_adopt_promotes_a_pending_row_and_names_who_did_it():
    plan = admission_plan(_result([_item("loose", refs=())]))
    assert plan["counts"]["pending"] == 1
    result = apply_admission_decisions(plan, [_decide("loose", "adopt")])
    assert result["selection"] == ["loose"]
    assert result["default_adopt"][0]["adopted_by"] == "owner"


def test_rename_and_describe_keep_the_value_that_was_there_before():
    plan = admission_plan(_result([_item("duty", meaning="财务部门负责月度经营分析")]))
    result = apply_admission_decisions(plan, [
        _decide("duty", "rename", "monthly_analysis_duty"),
        _decide("monthly_analysis_duty", "describe", "财务部门负责月度经营分析，含复核"),
    ])
    assert result["selection"] == ["monthly_analysis_duty"]
    rename, describe = result["decisions"]
    assert (rename["before"], rename["after"]) == ("duty", "monthly_analysis_duty")
    assert describe["before"] == "财务部门负责月度经营分析"
    assert result["default_adopt"][0]["meaning"] == "财务部门负责月度经营分析，含复核"


def test_identity_records_which_key_the_item_stands_on():
    plan = admission_plan(_result([_item("duty")]))
    result = apply_admission_decisions(plan, [_decide("duty", "identity", "duty@finance")])
    [row] = result["decisions"]
    assert (row["action"], row["after"]) == ("identity", "duty@finance")


def test_an_excluded_item_enters_by_restore_and_not_by_adopt():
    plan = admission_plan(_result([_item("clash", evidence_class="conflict")]))
    with pytest.raises(UnderstandWikiError) as raised:
        apply_admission_decisions(plan, [_decide("clash", "adopt")])
    assert raised.value.code == "excluded_item_needs_restore"
    result = apply_admission_decisions(plan, [_decide("clash", "restore")])
    assert result["excluded"] == [] and [row["item_key"] for row in result["pending"]] == ["clash"]


def test_a_run_that_would_lose_earlier_decisions_refuses_first():
    plan = admission_plan(_result([_item("duty"), _item("team", kind="entity")]))
    first = apply_admission_decisions(plan, [_decide("team", "unadopt")])
    plan_after_rerun = admission_plan(_result([_item("duty"), _item("team", kind="entity"),
                                               _item("extra")]))
    with pytest.raises(UnderstandWikiError) as raised:
        apply_admission_decisions(plan_after_rerun, [_decide("extra", "adopt")],
                                  existing=first["decisions"])
    assert raised.value.code == "discard_decisions"
    kept = apply_admission_decisions(plan_after_rerun, [*first["decisions"], _decide("extra", "adopt")],
                                     existing=first["decisions"])
    assert set(kept["selection"]) == {"duty", "extra"}


def test_an_unknown_action_or_item_is_refused_by_name():
    plan = admission_plan(_result([_item("duty")]))
    with pytest.raises(UnderstandWikiError) as raised:
        apply_admission_decisions(plan, [_decide("duty", "bless")])
    assert raised.value.code == "unknown_admission_action"
    with pytest.raises(UnderstandWikiError) as raised:
        apply_admission_decisions(plan, [_decide("ghost", "adopt")])
    assert raised.value.code == "unknown_admission_item"
