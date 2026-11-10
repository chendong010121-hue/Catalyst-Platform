"""A row that must name an entity keeps a name that resolves, or says it cannot.

A duty's holder, a relation's two ends and a change's participants are entity keys by
contract. An entity could leave the candidate after the row was validated - the label rule
drops a name the same card reports as unresolved, a same-name fold keeps one key - and only
relations were cleaned up afterwards. A duty whose holder went kept a bare key and read as
bound; the record of what was dropped kept its first twenty rows, so the label rule's rows
were counted but never named.
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_models import GroundedItem
from catalyst_platform.understand_semantic import _finalize_entity_references
from catalyst_platform.understand_verify import verification_integrity

LINES = [
    "市场部",
    "「市场部」在本页为统称，未被逐一列名",
    "市场部：负责区域市场开发",
    "分公司经理",
    "分公司经理全面负责分公司经营",
]


class _Answer:
    model = "stub-reference-integrity"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _eid(evidence, quote):
    return next(row["evidence_id"] for row in evidence if row["quote"].startswith(quote))


def _run(tmp_path, build):
    source = tmp_path / "page.md"
    source.write_text("\n".join(LINES), encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("reference", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_reference",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def _entity(key, meaning, evidence_id):
    return {"kind": "entity", "key": key, "meaning": meaning,
            "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}


def test_a_duty_whose_holder_was_dropped_is_kept_unresolved_and_named(tmp_path):
    def build(evidence):
        return [
            _entity("shichangbu", "市场部", _eid(evidence, "市场部")),
            {"kind": "unknown", "key": "shichangbu_tongcheng",
             "meaning": "「市场部」在本页为统称，未被逐一列名",
             "evidence_class": "UNKNOWN", "uncertainty": "本页未逐一列名",
             "evidence_refs": [_eid(evidence, "「市场部」")]},
            {"kind": "duty", "key": "duty_shichangbu_quyu", "subject": "shichangbu",
             "meaning": "市场部：负责区域市场开发", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_eid(evidence, "市场部：")]},
        ]

    result = _run(tmp_path, build)
    items = _by_key(result)
    # The label rule still drops the name: the page calls it a collective term.
    assert "shichangbu" not in items
    duty = items["duty_shichangbu_quyu"]
    assert duty.evidence_class == "unresolved"
    assert duty.subject == "shichangbu"
    assert duty.meaning == "市场部：负责区域市场开发"
    assert duty.evidence_refs
    assert duty.uncertainty.startswith("degraded:reference_not_declared:subject=shichangbu")
    attribution = result.producer_attribution
    assert attribution["reference_not_declared_count"] == 1
    assert attribution["reference_not_declared"][0]["item_key"] == "duty_shichangbu_quyu"
    # And the per-key record now names the label drop itself, not only its count.
    named = {(row["item_key"], row["rule"]) for row in attribution["item_contract_drops"]}
    assert ("shichangbu", "label_reported_as_unresolved") in named


def test_a_row_already_refused_keeps_its_own_reason(tmp_path):
    def build(evidence):
        return [
            _entity("fengongsi_jingli", "分公司经理", _eid(evidence, "分公司经理")),
            # `gongsi` is declared nowhere: the duty is degraded at validation, and the
            # reference check must not restate it under a second rule.
            {"kind": "duty", "key": "bz_ganbu_jinggang", "subject": "gongsi",
             "meaning": "分公司经理全面负责分公司经营", "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_eid(evidence, "分公司经理全面")]},
        ]

    result = _run(tmp_path, build)
    duty = _by_key(result)["bz_ganbu_jinggang"]
    assert duty.evidence_class == "unresolved"
    assert duty.uncertainty == "degraded:duty_holder_not_declared:gongsi"
    attribution = result.producer_attribution
    assert attribution["reference_not_declared_count"] == 0
    kept = attribution["reference_not_declared_already_unresolved"]
    assert [row["item_key"] for row in kept] == ["bz_ganbu_jinggang"]
    assert kept[0]["kept_uncertainty"] == "degraded:duty_holder_not_declared:gongsi"


def test_a_drop_that_happens_after_the_old_twenty_row_record_is_still_named(tmp_path):
    def build(evidence):
        rows = [_entity("shichangbu", "市场部", _eid(evidence, "市场部")),
                {"kind": "unknown", "key": "shichangbu_tongcheng",
                 "meaning": "「市场部」在本页为统称，未被逐一列名",
                 "evidence_class": "UNKNOWN", "uncertainty": "本页未逐一列名",
                 "evidence_refs": [_eid(evidence, "「市场部」")]}]
        # Twenty-one rows refused earlier in the row loop: a scope state on a claim.
        for index in range(21):
            rows.append({"kind": "claim", "key": f"claim_scope_{index:02d}",
                         "meaning": "分公司经理全面负责分公司经营",
                         "scope_state": "current",
                         "evidence_class": "SOURCE_DIRECT",
                         "evidence_refs": [_eid(evidence, "分公司经理全面")]})
        return rows

    result = _run(tmp_path, build)
    attribution = result.producer_attribution
    assert attribution["item_contract_drop_counts"]["scope_state_not_applicable"] == 21
    named = [row["item_key"] for row in attribution["item_contract_drops"]
             if row["rule"] == "label_reported_as_unresolved"]
    assert named == ["shichangbu"]
    assert attribution["item_contract_drops_omitted"] == 0


def test_a_missing_reference_on_an_already_refused_row_is_still_counted(tmp_path):
    def build(evidence):
        return [
            # Its evidence cannot be bound, so the entity leaves the candidate.
            _entity("shichangbu", "市场部", "ev_not_supplied"),
            _entity("fengongsi_jingli", "分公司经理", _eid(evidence, "分公司经理")),
            # Already kept unresolved for another reason: a layout reading was not marked
            # inferred. Its subject will not resolve once the entity above is gone.
            {"kind": "relation", "key": "rel_shichangbu_jingli",
             "meaning": "市场部：负责区域市场开发", "subject": "shichangbu",
             "predicate": "负责", "object": "fengongsi_jingli",
             "relation_source": "LAYOUT", "layout_ref": "page.md 版面",
             "evidence_class": "SOURCE_DIRECT",
             "evidence_refs": [_eid(evidence, "市场部：")]},
        ]

    result = _run(tmp_path, build)
    attribution = result.producer_attribution
    # The row keeps its own reason and is not restated under the reference rule...
    assert attribution["reference_not_declared_count"] == 0
    [already] = attribution["reference_not_declared_already_unresolved"]
    assert already["item_key"] == "rel_shichangbu_jingli"
    assert already["kind"] == "relation"
    assert already["kept_uncertainty"].startswith("degraded:layout_relation_must_be_inferred")
    # ...but the review path still sees the missing end: a row refused once must not hide
    # a second, different defect.
    integrity = verification_integrity(attribution)
    assert integrity["unresolved_reference_relations"] == 1


def _item(kind, key, **fields):
    return GroundedItem(item_id="item_" + key, kind=kind, key=key,
                        meaning=fields.pop("meaning", key),
                        evidence_refs=("ev_1",),
                        evidence_class=fields.pop("evidence_class", "observed_from_source"),
                        confidence="source_anchored_not_truth", **fields)


def test_relation_ends_and_event_participants_are_reference_fields():
    entity = _item("entity", "a", meaning="甲")
    relation = _item("relation", "rel_a_missing", subject="a", object="missing",
                     predicate="隶属")
    event = _item("event", "evt", event_from=("a",), event_to=("missing",),
                  predicate="整合")
    kept, degraded, already = _finalize_entity_references([entity, relation, event])
    assert [row["item_key"] for row in degraded] == ["rel_a_missing", "evt"]
    by_key = {item.key: item for item in kept}
    assert by_key["rel_a_missing"].evidence_class == "unresolved"
    assert by_key["rel_a_missing"].subject == "a"
    assert "object=missing" in by_key["rel_a_missing"].uncertainty
    assert by_key["evt"].evidence_class == "unresolved"
    assert "event_to=missing" in by_key["evt"].uncertainty
    assert already == []


def test_a_field_outside_the_contract_is_not_read_as_a_reference():
    entity = _item("entity", "a", meaning="甲")
    # A claim has no entity-reference field; `subject` on it is not one by this contract.
    claim = _item("claim", "claim_x", subject="missing", meaning="甲属于乙")
    kept, degraded, already = _finalize_entity_references([entity, claim])
    assert degraded == [] and already == []
    assert {item.key for item in kept} == {"a", "claim_x"}
    assert next(item for item in kept if item.key == "claim_x").evidence_class == "observed_from_source"
