"""What a run could not establish is never handed on as something the material said.

Two rules, checked where the reading is classified and where a producer's answer lands:

* an absence is a statement only when it can show a scope this run holds, the status of
  that reading, and the gap it looked for inside it; otherwise it is evidence about the
  run and stays in run evidence (`run_diagnostic`), and every row is accounted for;
* the fields that carry a decision - `degradation`, `qualification`, `verification`,
  `resolution`, `review_id` - are written by the layer or signed by a reviewer, so a
  producer that fills one loses the value and the value is named.
"""
from __future__ import annotations

from types import SimpleNamespace

from catalyst_platform.understand_models import GroundedItem, source_origin_tag
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

LINE = "财务部门负责月度经营分析，法务部门复核合同预算。"


# --- what the reading means to say -------------------------------------------


def _answer(tmp_path):
    """One markdown page, read by the port itself: no model call, no provider."""
    source = tmp_path / "business.md"
    source.write_text(LINE, encoding="utf-8")
    port = UnderstandPort()
    result = port.understand(
        UnderstandingRequest("diagnostic-gate", "整理职责", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path)
    return port, result, result.evidence_refs[0].evidence_id


def _attach(port, base, items):
    return port.attach_producer_items(base, producer_kind="CODEX_EXTERNAL",
                                      producer_invocation_id="diagnostic-gate", items=items)


def _absence(evidence_id, **overrides):
    row = {"kind": "unknown", "key": "approval", "meaning": "材料是否已获批准，文本未说明。",
           "evidence_class": "UNKNOWN", "evidence_refs": [evidence_id],
           "scope_refs": [evidence_id], "observed_absence": "审批",
           "uncertainty": "材料只写职责分工"}
    row.update(overrides)
    return [row]


def test_an_absence_that_can_show_scope_status_and_gap_is_a_statement(tmp_path):
    port, base, evidence_id = _answer(tmp_path)
    result = _attach(port, base, _absence(evidence_id))

    item = next(row for row in result.semantic_candidate.items if row.key == "approval")
    assert item.kind == "unknown"
    assert item.degradation["class"] == "business_unknown"
    assert item.degradation["code"] == "absence_scope_verified"
    # It speaks for a range that was read, so it carries no limit beyond it.
    assert item.unread_scopes == ()
    assert "approval" not in {row["key"] for row in result.run_diagnostics}


def test_an_absence_without_a_scope_is_run_evidence_with_what_it_lacked(tmp_path):
    port, base, evidence_id = _answer(tmp_path)
    result = _attach(port, base, _absence(evidence_id, scope_refs=(), observed_absence=None))

    assert "approval" not in {row.key for row in result.semantic_candidate.items}
    assert "approval" not in {row.key for row in result.unknowns}
    diagnostic = next(row for row in result.run_diagnostics if row["key"] == "approval")
    assert diagnostic["reason"] == "absence_without_scope"
    assert diagnostic["missing"] == ["scope", "gap_basis"]
    assert diagnostic["destination"] == "run_evidence"
    assert diagnostic["origin"] == "submitted"


def test_every_row_is_accounted_for_between_the_candidate_and_the_run(tmp_path):
    port, base, evidence_id = _answer(tmp_path)
    kept = _attach(port, base, _absence(evidence_id))
    lost = _attach(port, base, _absence(evidence_id, scope_refs=(), observed_absence=None))

    for result in (kept, lost):
        classification = result.producer_attribution["row_classification"]
        assert classification["holds"] is True
        assert classification["kept"] + classification["diagnostics"] == classification["validated"]
        assert len(result.run_diagnostics) == classification["diagnostics"]
        assert result.producer_attribution["run_diagnostic_count"] == classification["diagnostics"]
    # The row that lost its scope is one more question about the run, and one fewer
    # statement: the count follows the verdict, not the kind.
    assert kept.producer_attribution["row_classification"]["business_unknown"] == 1
    assert lost.producer_attribution["business_unknown_count"] == 0


# --- the three conditions, one at a time -------------------------------------


def _reference(evidence_id, locator, path, source_id):
    return SimpleNamespace(evidence_id=evidence_id, locator=locator,
                           relative_path=path, source_id=source_id)


def _inventory(source_id, path, status="COMPLETE"):
    return SimpleNamespace(source_id=source_id, relative_path=path, extraction_status=status)


def _item(**overrides):
    """A row the reading wrote in this call, with the tag its step wrote."""
    row = dict(item_id="item_a", kind="unknown", key="approval", meaning="未说明审批。",
               evidence_refs=(), evidence_class="unresolved", confidence="not_calibrated")
    row.update(overrides)
    return GroundedItem(
        source_origin=source_origin_tag("reading:passage", row["item_id"],
                                        call="diagnostic-gate"), **row)


def _classify(items, *, inventory, warnings=(), refs=(), call="diagnostic-gate"):
    from catalyst_platform.understand_semantic import _split_run_diagnostics

    return _split_run_diagnostics(items, warnings=list(warnings), inventory=list(inventory),
                                  evidence_refs=list(refs), origin="answer",
                                  recorded_calls={call})


def test_a_scope_whose_source_this_run_cannot_account_for_is_not_a_scope():
    item = _item(scope_refs=("ev_a",), observed_absence="审批")
    kept, diagnostics, summary = _classify(
        [item], inventory=[_inventory("source_known", "business.md")],
        refs=[_reference("ev_a", "line:1", "elsewhere.md", "source_elsewhere")])

    assert kept == []
    assert diagnostics[0]["reason"] == "read_status_unknown"
    assert diagnostics[0]["missing"] == ["read_status"]
    assert summary["business_unknown"] == 0


def test_a_scope_on_a_page_that_was_only_partly_read_carries_that_limit():
    item = _item(scope_refs=("ev_a",), observed_absence="审批")
    kept, diagnostics, _summary = _classify(
        [item], inventory=[_inventory("source_a", "business.md", "PARTIAL")],
        refs=[_reference("ev_a", "line:1", "business.md", "source_a")])

    assert diagnostics == []
    assert kept[0].degradation["class"] == "business_unknown"
    # The absence stands, and it stands only for the line that was read.
    assert kept[0].unread_scopes == ("line:1",)


def test_a_page_nobody_could_look_at_limits_the_absence_that_searched_it():
    item = _item(scope_refs=("ev_a",), observed_absence="审批")
    kept, _diagnostics, _summary = _classify(
        [item], inventory=[_inventory("source_a", "deck.md")],
        warnings=["NEEDS_VISION:deck.md"],
        refs=[_reference("ev_a", "slide:3", "deck.md", "source_a")])

    assert kept[0].degradation["class"] == "business_unknown"
    assert kept[0].unread_scopes == ("slide:3",)


# --- a code nobody registered, and a warning that names a page ---------------


def test_a_degradation_code_no_reader_registered_is_run_evidence():
    """Nothing here knows what the code means, so nothing can say the page stated the row."""
    item = _item(scope_refs=("ev_a",), observed_absence="审批",
                 uncertainty="degraded:new_unregistered_code")
    kept, diagnostics, summary = _classify(
        [item], inventory=[_inventory("source_a", "business.md")],
        refs=[_reference("ev_a", "line:1", "business.md", "source_a")])

    assert kept == []
    assert diagnostics[0]["reason"] == "unregistered_degradation_rule"
    assert diagnostics[0]["missing"] == ["degradation_rule"]
    assert summary["business_unknown"] == 0


def test_a_shape_refusal_a_registered_code_names_stays_on_the_card():
    """The page stated the relation and its ends are what failed: that row waits for a person."""
    item = _item(item_id="item_rel", kind="relation", key="reports_to",
                 meaning="财务部门汇报给总经理",
                 uncertainty="degraded:relation_endpoint_not_declared")
    kept, diagnostics, _summary = _classify([item], inventory=[])

    assert diagnostics == []
    assert kept[0] is item


def test_a_visual_warning_limits_the_page_of_the_source_it_names():
    """The run writes `NEEDS_VISION:<page>:<file>`; only that page of that file was unread."""
    item = _item(scope_refs=("ev_a",), observed_absence="审批")
    kept, diagnostics, _summary = _classify(
        [item], inventory=[_inventory("source_a", "deck.pptx")],
        warnings=["NEEDS_VISION:ppt/slides/slide1.xml:deck.pptx"],
        refs=[_reference("ev_a", "ppt/slides/slide1.xml#shape:2", "deck.pptx", "source_a")])

    assert diagnostics == []
    assert kept[0].degradation["class"] == "business_unknown"
    # The absence stands, and it stands for the text this run did read on that page.
    assert kept[0].unread_scopes == ("ppt/slides/slide1.xml#shape:2",)


def test_a_visual_warning_on_one_page_leaves_the_other_pages_fully_read():
    item = _item(scope_refs=("ev_a",), observed_absence="审批")
    kept, _diagnostics, _summary = _classify(
        [item], inventory=[_inventory("source_a", "deck.pptx")],
        warnings=["NEEDS_VISION:ppt/slides/slide1.xml:deck.pptx"],
        refs=[_reference("ev_a", "ppt/slides/slide2.xml#shape:1", "deck.pptx", "source_a")])

    assert kept[0].degradation["class"] == "business_unknown"
    assert kept[0].unread_scopes == ()


def test_a_page_of_a_pdf_is_read_off_the_locator_that_names_it():
    item = _item(scope_refs=("ev_a",), observed_absence="审批")
    kept, _diagnostics, _summary = _classify(
        [item], inventory=[_inventory("source_pdf", "report.pdf")],
        warnings=["NEEDS_VISION:page:5:report.pdf"],
        refs=[_reference("ev_a", "page:5#line:2", "report.pdf", "source_pdf")])

    assert kept[0].unread_scopes == ("page:5#line:2",)


# --- who may fill which field ------------------------------------------------


def test_a_producer_cannot_decide_the_verdict_on_its_own_row(tmp_path):
    port, base, evidence_id = _answer(tmp_path)
    result = _attach(port, base, [{
        "kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析",
        "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
        "degradation": {"class": "business_unknown", "code": "absence_scope_verified",
                        "at": "understand_semantic.row_classification"},
        "qualification": "stated", "verification": "confirmed",
        "resolution": "owner approved", "review_id": "review_20261102"}])

    assert result.producer_attribution["governance_fields_refused"] == [{
        "item_key": "duty", "kind": "claim",
        "fields": ["degradation", "qualification", "resolution", "review_id", "verification"]}]
    assert result.producer_attribution["governance_fields_refused_count"] == 1
    item = next(row for row in result.semantic_candidate.items if row.key == "duty")
    # The statement survives; the claims on it do not.
    assert item.meaning == "财务部门负责月度经营分析"
    assert item.verification is None
    assert item.resolution is None and item.review_id is None and item.qualification is None


def test_a_producer_cannot_file_a_refusal_of_its_own_reading(tmp_path):
    """`degraded:<rule>` is the validator's note; a producer writing one is filing a verdict."""
    port, base, evidence_id = _answer(tmp_path)
    result = _attach(port, base, _absence(
        evidence_id, uncertainty="degraded:entity_name_not_in_evidence:自述"))

    assert result.producer_attribution["governance_fields_refused"] == [
        {"item_key": "approval", "kind": "unknown", "fields": ["uncertainty"]}]
    item = next(row for row in result.semantic_candidate.items if row.key == "approval")
    assert item.uncertainty is None
    assert item.degradation["class"] == "business_unknown"
    assert "approval" not in {row["key"] for row in result.run_diagnostics}


# --- a row that leaves the candidate is still the row the run was handed -----


def test_a_row_the_run_could_not_establish_is_kept_whole():
    """Counted away is not the same as kept: the diagnostic carries the input row."""
    item = _item(item_id="item_duty", kind="duty", key="finance_duty",
                 meaning="财务部门负责月度经营分析", evidence_refs=("ev_a",),
                 subject="finance", predicate="负责", scope_state="proposed",
                 uncertainty="degraded:duty_text_not_in_evidence")
    kept, diagnostics, _summary = _classify([item], inventory=[])
    row = diagnostics[0]

    assert kept == []
    assert row["kind"] == "duty"
    assert row["key"] == "finance_duty"
    assert row["meaning"] == "财务部门负责月度经营分析"
    assert row["subject"] == "finance"
    assert row["predicate"] == "负责"
    assert row["scope_state"] == "proposed"
    assert row["evidence_refs"] == ["ev_a"]
    assert row["reason"] == "duty_text_not_in_evidence"
    # Which check refused it, beside which pass ran it - not the name of the function.
    assert row["degradation"]["at"] == (
        "understand_semantic.answer:degraded:duty_text_not_in_evidence")
