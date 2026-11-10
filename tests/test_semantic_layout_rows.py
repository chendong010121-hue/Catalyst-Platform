"""A page that reads its layout states where it read it; a page that limits a rule says so.

Two rows were lost by the field they were written in, not by what they said. One page
put a layout relation's reading step in layout_ref and left uncertainty empty, and
thirty-seven true relations went with it; the extraction contract asks for conditions
and exceptions as rows of their own, which one card then answered with none of.
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
from catalyst_platform.understand_semantic import semantic_extraction_rules


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_layout_rows",
        message="请理解这份组织架构资料",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_layout_rows",
        requested_depth="semantic",
        budget_steps=16,
    )


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "org.md"
    source.write_text("水利集团\n党委会\n工程管理中心", encoding="utf-8")
    return source


class _Rows:
    """One answer, built from the evidence ids the request carried."""

    model = "stub-layout-model"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, build):
        self._build = build
        self.payloads = []

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        self.payloads.append(payload)
        return ModelResponse(content=json.dumps({"items": self._build(payload["evidence"])},
                                                ensure_ascii=False),
                             finish_reason="stop")


def _entity(key, meaning, evidence_id):
    return {"kind": "entity", "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id]}


def _layout_relation(**extra):
    row = {"kind": "relation", "key": "dangweihui_xiashe", "meaning": "「党委会」在版式中列于「水利集团」之下",
           "subject": "dangweihui", "object": "shuili_jituan", "predicate": "隶属",
           "relation_source": "LAYOUT", "layout_ref": "org.md 版面：党委会置于集团名称之下",
           "evidence_class": "INFERRED"}
    row.update(extra)
    return row


def _run(tmp_path, rows_from):
    source = _source(tmp_path)
    return UnderstandPort().understand(_request(source), source_root=tmp_path,
                                       semantic_provider=_Rows(rows_from))


def test_a_layout_relation_states_its_reading_step_in_the_layout_ref(tmp_path):
    def build(evidence):
        # Each name is quoted by the line that spells it.
        by_quote = {row["quote"]: row["evidence_id"] for row in evidence}
        group, committee = by_quote["水利集团"], by_quote["党委会"]
        return [_entity("shuili_jituan", "水利集团", group),
                _entity("dangweihui", "党委会", committee),
                _layout_relation(evidence_refs=[group, committee])]

    result = _run(tmp_path, build)
    [relation] = [item for item in result.semantic_candidate.items if item.kind == "relation"]
    # The place the two names sit is the reading step, so it is copied over and counted
    # rather than the row being dropped for an empty field.
    assert relation.uncertainty == "org.md 版面：党委会置于集团名称之下"
    assert result.producer_attribution["uncertainty_from_layout"] == 1
    assert result.producer_attribution["dropped_invalid_items"].get("uncertainty_required") is None


def test_an_inferred_row_with_neither_a_reading_step_nor_a_layout_ref_is_dropped(tmp_path):
    def build(evidence):
        first = evidence[0]["evidence_id"]
        return [_entity("shuili_jituan", "水利集团", first),
                _entity("dangweihui", "党委会", first),
                {"kind": "claim", "key": "dangweihui_role", "meaning": "党委会把关定向",
                 "evidence_class": "INFERRED", "evidence_refs": [first]}]

    result = _run(tmp_path, build)
    assert [item.key for item in result.semantic_candidate.items if item.kind == "claim"] == []
    assert result.producer_attribution["dropped_invalid_items"]["uncertainty_required"] == 1


def test_a_row_with_no_statement_is_dropped_without_taking_the_card_with_it(tmp_path):
    # One paid run died on this: a single row with a key and no statement aborted the whole
    # card, and every sound row beside it went with it. A row that holds nothing a reader
    # can check is counted and named like every other row the contract cannot keep.
    def build(evidence):
        first = evidence[0]["evidence_id"]
        return [_entity("shuili_jituan", "水利集团", first),
                _entity("dangweihui", "党委会", first),
                {"kind": "claim", "key": "buzhou_san_baogao_zhuti", "meaning": "   ",
                 "evidence_class": "SOURCE_DIRECT", "evidence_refs": [first]}]

    result = _run(tmp_path, build)
    keys = {item.key for item in result.semantic_candidate.items}
    assert "buzhou_san_baogao_zhuti" not in keys
    # 党委会's name is not spelled by the passage it cites, so that row is run evidence
    # and the sound row beside it still reaches the card on its own.
    assert keys == {"shuili_jituan"}
    assert [row["key"] for row in result.run_diagnostics if row["kind"] == "unknown"
            and row["key"] == "dangweihui"] == ["dangweihui"]
    assert result.producer_attribution["dropped_invalid_items"]["meaning_required"] == 1
    assert result.producer_attribution["dropped_invalid_item_keys"] != []


def test_the_contract_asks_for_a_condition_and_an_exception_of_their_own():
    rules = semantic_extraction_rules()
    assert "is a condition row of its own" in rules
    assert "is an exception row" in rules
    # A condition is an extra row, never a substitute for what the sentence states.
    assert "yields the claim and the condition" in rules
    assert "a condition folded into a claim's meaning is not a condition row" in rules
