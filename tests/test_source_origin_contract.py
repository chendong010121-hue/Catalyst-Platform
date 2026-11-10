"""Who wrote a row is part of what the row may be.

The source contract (Owner, 2026-11-02) is one field, written where the row is made and
verified where it is classified: a claim about the material, a note about the run, or a
source nobody can verify. It is not a label a producer or a model may fill, it does not
change because a scope was attached or a wording revised, and a row read back out of the
store is the same kind of row it was saved as.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from catalyst_platform.gateway import CatalystGateway
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.understand_models import (
    SOURCE_STEPS,
    GroundedItem,
    source_origin_tag,
)
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)
from catalyst_platform.understand_semantic import _recorded_calls, _split_run_diagnostics
from catalyst_platform.understand_wiki import UnderstandWikiAdapter, apply_admission_decisions
from catalyst_platform.wiki import ProjectWiki

LINE = "财务部门负责月度经营分析，法务部门复核合同预算。"


def _base(tmp_path):
    source = tmp_path / "business.md"
    source.write_text(LINE, encoding="utf-8")
    result = UnderstandPort().understand(
        UnderstandingRequest("source-origin", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path)
    return result, result.evidence_refs[0].evidence_id


def _classify(items, *, result, origin="answer", calls=()):
    # The calls are read from the run's own record, never from the rows under test.
    return _split_run_diagnostics(list(items), warnings=list(result.source_warnings),
                                  inventory=list(result.source_inventory),
                                  evidence_refs=list(result.evidence_refs),
                                  origin=origin,
                                  recorded_calls=_recorded_calls(result) | set(calls))


def _attach(base, items, invocation="call_attach"):
    return UnderstandPort().attach_producer_items(
        base, producer_kind="CODEX_EXTERNAL", producer_invocation_id=invocation, items=items)


# --- 1. the reading's own guard rails, however they are armed -------------------


def test_a_guard_sentence_is_run_evidence_however_it_is_armed(tmp_path):
    result, evidence_id = _base(tmp_path)
    guards = [row for row in result.unknowns if row.key in {"approval", "binding"}]
    assert {row.source_origin["step"] for row in guards} == {"reading:guard"}
    armed = [replace(row, scope_refs=(evidence_id,), observed_absence="审批")
             for row in guards]

    kept, diagnostics, _summary = _classify(armed, result=result)

    # Complete as an absence, and still not something the material said: the step that
    # wrote the row never writes claims about the material.
    assert kept == []
    assert {row["reason"] for row in diagnostics} == {"source_origin_run_diagnostic"}
    assert {row["destination"] for row in diagnostics} == {"run_evidence"}
    assert {row["source_origin"]["category"] for row in diagnostics} == {"run_diagnostic"}
    assert {row["source_origin"]["step"] for row in diagnostics} == {"reading:guard"}


# --- 2. a real absence in the material is still a statement ---------------------


def test_a_real_absence_in_the_material_is_still_a_business_unknown(tmp_path):
    base, evidence_id = _base(tmp_path)
    attached = _attach(base, [{
        "kind": "unknown", "key": "approval", "meaning": "材料是否已获批准，文本未说明。",
        "evidence_class": "UNKNOWN", "evidence_refs": [evidence_id],
        "scope_refs": [evidence_id], "observed_absence": "审批",
        "uncertainty": "材料只写职责分工"}])
    item = next(row for row in attached.unknowns if row.key == "approval")

    kept, diagnostics, summary = _classify([item], result=attached)

    assert diagnostics == []
    assert summary["business_unknown"] == 1
    # The same key the guard rail uses, and a different row: this one a producer wrote
    # about a passage, with the scope and the gap the read could show.
    assert kept[0].degradation["class"] == "business_unknown"
    assert kept[0].source_origin["category"] == "source_claim"
    assert kept[0].source_origin["step"] == "submission:producer"


# --- 3. neither a producer nor a model may write the tag ------------------------


def test_a_producer_cannot_name_the_step_that_made_its_row(tmp_path):
    base, evidence_id = _base(tmp_path)
    attached = _attach(base, [{
        "kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析",
        "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
        # Filed as if the reading's own guard step had written this claim.
        "source_origin": {"category": "run_diagnostic", "step": "reading:guard",
                          "call": "call_attach", "item_id": "item_forged"}}], invocation="call_attach")

    # The field is this layer's: the value is taken off and named beside the row.
    assert attached.producer_attribution["governance_fields_refused"] == [
        {"item_key": "duty", "kind": "claim", "fields": ["source_origin"]}]
    item = next(row for row in attached.semantic_candidate.items if row.key == "duty")
    # And the layer writes its own answer: the producer step is what wrote this row.
    assert item.source_origin["step"] == "submission:producer"
    assert item.source_origin["category"] == "source_claim"
    assert item.source_origin["item_id"] == item.item_id


# --- 4. a row that cannot show its step is not source knowledge -----------------


def test_a_row_that_cannot_show_its_step_is_not_source_knowledge(tmp_path):
    result, evidence_id = _base(tmp_path)
    tag = source_origin_tag("reading:passage", "item_a")
    untagged = GroundedItem(
        item_id="item_a", kind="claim", key="duty", meaning="财务部门负责月度经营分析",
        evidence_refs=(evidence_id,), evidence_class="observed_from_source",
        confidence="source_anchored_not_truth")
    # Three ways a tag fails to say who wrote the row: it names another row, its step is
    # not one this layer runs, or its category is not the one that step writes.
    other_row = replace(untagged, source_origin={**tag, "item_id": "item_b"})
    unregistered = replace(untagged, source_origin={**tag, "step": "made:up"})
    laundered = replace(untagged, source_origin={**tag, "category": "source_claim",
                                                 "step": "reading:guard"})

    for row in (untagged, other_row, unregistered, laundered):
        kept, diagnostics, _summary = _classify([row], result=result)
        assert kept == [], row
        assert {entry["reason"] for entry in diagnostics} == {"source_origin_unverifiable"}
        # The row keeps its content in run evidence; it is not admitted as knowledge.
        assert diagnostics[0]["meaning"] == row.meaning


# --- 5. what is saved is what is read back --------------------------------------


def test_a_saved_row_is_read_back_as_the_kind_of_row_it_was_saved_as(tmp_path):
    from tests import test_understand_only as fixtures

    root = tmp_path / "sources"
    root.mkdir()
    source = root / "evidence.docx"
    fixtures._docx(source, text="Claim: dept_duty | 部门承担经营分析")
    wiki = ProjectWiki(tmp_path / "workspace", [root], enterprise_id="synthetic",
                       project_id="typed", backend="json")
    gateway = CatalystGateway(wiki.workspace)
    result = UnderstandPort().understand(
        UnderstandingRequest("saved-origin", "read document", source_refs=(source,),
                             intent="KNOWLEDGE_PROPOSE", scope_id=wiki.scope_id,
                             requested_depth="semantic", budget_steps=16),
        source_root=root).to_dict()

    def submit(recorder):
        return UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), root).submit(
            result, declared_scope_id=wiki.scope_id)

    receipt = gateway.semantic_operation(
        operation="understand.candidate.submit", scope_id=wiki.scope_id,
        actor_origin="offline_fixture",
        input_value={"contract_version": "catalyst.understand.handoff.v1"},
        action=submit)["result"]
    typed_id = receipt["typed"]["candidate_id"]
    entries = wiki.semantic_state()["candidates"][typed_id]["entries"]
    assert entries

    # Saved with the step that wrote it, the call it was written in, and its own id.
    for entry in entries:
        assert entry["source_origin"]["category"] == "source_claim"
        assert entry["source_origin"]["step"] in SOURCE_STEPS
        assert entry["source_origin"]["call"]
        assert entry["source_origin"]["item_id"]

    # A cold read of the same workspace - a store opened again - is the same rows.
    reopened = ProjectWiki(wiki.workspace, [root], enterprise_id="synthetic",
                           project_id="typed", backend="json")
    again = reopened.semantic_state()["candidates"][typed_id]["entries"]
    assert [entry["source_origin"] for entry in again] == [
        entry["source_origin"] for entry in entries]


def test_a_row_saved_before_this_contract_reads_as_unverified(tmp_path):
    from tests import test_duty_event_storage as storage

    workspace, _roots, wiki, staged = storage._wiki(tmp_path)
    storage._accepted(workspace, wiki, staged, [*storage._entities(), storage._duty()], "run_old_row")

    # Nothing on disk says where the row came from, and nothing on disk is rewritten to
    # pretend it does.
    candidate_id = wiki.semantic_state()["active_version_id"]
    version = wiki.semantic_state()["accepted_versions"][candidate_id]
    assert all("source_origin" not in entry for entry in version["meanings"])

    read = wiki.read_knowledge("负责", mode="accepted_enterprise_semantics", limit=100)
    duty = next(row for row in read["meanings"] if row["kind"] == "duty")
    assert duty["source_origin"] == {"category": "unverifiable", "step": None,
                                     "call": None, "item_id": None}


# --- 6. a revision keeps the chain ----------------------------------------------


def test_a_revision_keeps_the_source_chain_and_the_original_wording():
    plan = {"default_adopt": [{"item_key": "duty", "item_id": "item_a", "kind": "claim",
                               "meaning": "财务部门负责月度经营分析",
                               "evidence_class": "observed_from_source",
                               "source_origin": source_origin_tag("reading:passage", "item_a")}],
            "pending": [], "excluded": []}

    revised = apply_admission_decisions(plan, [{
        "item_key": "duty", "action": "describe", "after": "财务部门负责月度经营分析（修订）",
        "by": "owner", "time": "2026-11-02T00:00:00Z"}], existing=[])

    row = revised["default_adopt"][0]
    assert row["meaning"] == "财务部门负责月度经营分析（修订）"
    # Rewording says what the row means; it does not say who wrote it.
    assert row["source_origin"] == source_origin_tag("reading:passage", "item_a")
    # And the wording it replaced is in the decision record, not lost.
    assert revised["decisions"][0]["before"] == "财务部门负责月度经营分析"


# --- 7. the call a row names is checked against the run's own records ------------


def _tagged_claim(evidence_id, *, call=None, item_id="item_a"):
    return GroundedItem(
        item_id=item_id, kind="claim", key="duty",
        meaning="财务部门负责月度经营分析", evidence_refs=(evidence_id,),
        evidence_class="observed_from_source", confidence="source_anchored_not_truth",
        source_origin=source_origin_tag("reading:passage", item_id, call))


def test_a_row_naming_the_call_that_wrote_it_is_still_knowledge(tmp_path):
    result, evidence_id = _base(tmp_path)

    kept, diagnostics, _summary = _classify(
        [_tagged_claim(evidence_id, call=result.request_id)], result=result)

    assert diagnostics == []
    assert kept[0].source_origin["call"] == result.request_id


def test_a_row_that_names_no_call_is_not_knowledge(tmp_path):
    result, evidence_id = _base(tmp_path)

    kept, diagnostics, _summary = _classify([_tagged_claim(evidence_id)], result=result)

    assert kept == []
    # Nothing on disk or in the row says where it was written, and the pass does not
    # give it the call it happens to be running under.
    assert diagnostics[0]["reason"] == "source_origin_call_missing"
    assert diagnostics[0]["missing"] == ["call"]


def test_a_row_naming_a_call_this_run_never_made_is_not_knowledge(tmp_path):
    result, evidence_id = _base(tmp_path)

    kept, diagnostics, _summary = _classify(
        [_tagged_claim(evidence_id, call="not-a-recorded-call")], result=result)

    assert kept == []
    # The tag is internally coherent; only the record can say the call never ran.
    assert diagnostics[0]["source_origin"]["call"] == "not-a-recorded-call"
    assert diagnostics[0]["reason"] == "source_origin_call_unrecorded"
    assert diagnostics[0]["missing"] == ["call_record"]


def test_a_row_written_in_an_earlier_call_is_verified_against_that_record(tmp_path):
    result, evidence_id = _base(tmp_path)
    historical = _tagged_claim(evidence_id, call="run_20261101")

    kept, diagnostics, _summary = _classify([historical], result=result)
    assert kept == []
    assert diagnostics[0]["reason"] == "source_origin_call_unrecorded"

    # Told which call wrote it, the pass verifies the row and keeps the call it names:
    # a row read back out of a store came from the call that read it then.
    kept, diagnostics, _summary = _classify([historical], result=result,
                                            calls={"run_20261101"})
    assert diagnostics == []
    assert kept[0].source_origin["call"] == "run_20261101"


# --- 8. a degraded row keeps the step that wrote it, not the one that refused it --


def _degraded(producer_kind, invocation, evidence_id, base):
    # A relation whose ends the row never declares: the contract refuses the shape and
    # keeps the row as an unresolved one, written by whichever step is submitting.
    attached = UnderstandPort().attach_producer_items(
        base, producer_kind=producer_kind, producer_invocation_id=invocation,
        items=[{"kind": "relation", "key": "reports_to",
                "meaning": "财务部门汇报给总经理", "evidence_refs": [evidence_id]}])
    return attached, attached.semantic_candidate.items[0]


def test_a_degraded_row_keeps_the_step_that_wrote_it(tmp_path):
    base, evidence_id = _base(tmp_path)

    _external, external = _degraded("CODEX_EXTERNAL", "call_external", evidence_id, base)
    _native, native = _degraded("CATALYST_NATIVE_MODEL", "call_native", evidence_id, base)

    # Both rows were degraded by the same rule, and the reason is on the row.
    assert external.uncertainty.startswith("degraded:relation_fields_required")
    assert native.uncertainty.startswith("degraded:relation_fields_required")
    # The step is the one that submitted, never the one that refused.
    assert external.source_origin["step"] == "submission:producer"
    assert native.source_origin["step"] == "answer:model"
    assert external.source_origin["step"] != "answer:model"
    assert native.source_origin["step"] != "submission:producer"
    # And the call is the submission's, not the reading's.
    assert external.source_origin["call"] == "call_external"
    assert native.source_origin["call"] == "call_native"


def test_a_degraded_rows_tag_says_who_wrote_it_and_nothing_else(tmp_path):
    base, evidence_id = _base(tmp_path)
    attached, row = _degraded("CATALYST_NATIVE_MODEL", "call_native", evidence_id, base)

    # A shape refusal stays on the card for a reviewer, and the row is handed on whole.
    kept, diagnostics, _summary = _classify([row], result=attached)
    assert diagnostics == []
    assert kept[0] is row
    # The tag says who wrote the row and nothing else: the refusal is the row's
    # uncertainty, and it is where a reader finds it.
    assert set(row.source_origin) == {"category", "step", "call", "item_id"}
    assert row.source_origin["category"] == "source_claim"
    assert row.source_origin["item_id"] == row.item_id

