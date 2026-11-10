"""Extraction runs one call per unit of evidence, and the units are merged under one contract.

A whole deck in one answer is what made every mechanical rule refuse cards whole
(run-7..run-17). These tests pin the replacement: a small source stays one call, a
source with page, slide or row boundaries is called one unit at a time, and the merged
candidate is validated once — so a relation may join entities two units declare, and a
fact two units both quote keeps one row.

Every test drives the Port through a stub provider; no credential is read and no
network call is made.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    _evidence_units,
)


def _request(source: Path) -> UnderstandingRequest:
    return UnderstandingRequest(
        request_id="req_units",
        message="请理解这些资料中的经营职责、规则和未知项",
        source_refs=(source,),
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
        scope_id="scope_units",
        requested_depth="semantic",
        budget_steps=16,
    )


def _lines(tmp_path: Path, count: int) -> Path:
    source = tmp_path / "business.md"
    source.write_text(
        "\n".join(f"第{index}条：财务部门{index}向法务部门报送第{index}项月度经营分析" for index in range(count)),
        encoding="utf-8")
    return source


class _UnitProvider:
    """Answers each request with items derived from the evidence rows it was given."""

    model = "stub-unit-model"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def __init__(self, build):
        self._build = build
        self.payloads = []

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        self.payloads.append(payload)
        rows = payload["evidence"]
        items = self._build(len(self.payloads) - 1, rows)
        return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False),
                             finish_reason="stop")


def _named(rows) -> str:
    """The department a unit's first row names, e.g. 第39条：财务部门39向法务部门报送…."""
    return rows[0]["quote"].split("：", 1)[1].split("向", 1)[0]


def _row(kind, key, meaning, evidence_id, **extra):
    return {"kind": kind, "key": key, "meaning": meaning, "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id], **extra}


def test_a_long_source_is_extracted_one_unit_at_a_time(tmp_path):
    source = _lines(tmp_path, 90)
    provider = _UnitProvider(lambda index, rows: [
        _row("entity", f"dept_{index}", _named(rows), rows[0]["evidence_id"])])
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)

    units = _evidence_units(result.evidence_refs)
    assert len(units) == 3
    # One call per unit, and each call carries only its own rows.
    assert len(provider.payloads) == 3
    sent = [row["evidence_id"] for payload in provider.payloads for row in payload["evidence"]]
    assert sent == [ref.evidence_id for ref in result.evidence_refs]
    for payload, (_, refs) in zip(provider.payloads, units):
        assert [row["evidence_id"] for row in payload["evidence"]] == [ref.evidence_id for ref in refs]
    # The merged candidate carries what every unit answered.
    assert len([item for item in result.semantic_candidate.items if item.kind == "entity"]) == 3
    assert result.producer_attribution["extraction_units"] == 3
    assert result.producer_attribution["unit_item_counts"] == [1, 1, 1]


def test_a_relation_may_join_entities_two_units_declare(tmp_path):
    source = _lines(tmp_path, 90)

    def build(index, rows):
        first = rows[0]["evidence_id"]
        if index == 0:
            return [_row("entity", "alpha", "财务部门", first)]
        if index == 1:
            return [_row("entity", "beta", "法务部门", first),
                    _row("relation", "reports", "财务部门向法务部门报送", first,
                         subject="alpha", predicate="报送", object="beta", relation_source="TEXT")]
        return []

    result = UnderstandPort().understand(_request(source), source_root=tmp_path,
                                         semantic_provider=_UnitProvider(build))
    relations = [item for item in result.semantic_candidate.items if item.kind == "relation"]
    assert [item.key for item in relations] == ["reports"]
    assert result.producer_attribution["dropped_relation_count"] == 0


def test_a_key_two_units_both_declare_is_merged_once(tmp_path):
    source = _lines(tmp_path, 90)
    provider = _UnitProvider(lambda index, rows: [
        _row("entity", "finance", "财务部门", rows[0]["evidence_id"])])
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    entities = [item for item in result.semantic_candidate.items if item.kind == "entity"]
    assert [item.key for item in entities] == ["finance"]
    assert result.producer_attribution["extraction_units"] == 3
    assert result.producer_attribution["duplicate_items_dropped"] == 2


def test_a_small_source_still_costs_one_call(tmp_path):
    source = tmp_path / "business.md"
    source.write_text("财务部门负责月度经营分析。", encoding="utf-8")
    provider = _UnitProvider(lambda index, rows: [
        _row("entity", "finance", "财务部门", rows[0]["evidence_id"])])
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    assert len(provider.payloads) == 1
    assert result.producer_attribution["extraction_units"] == 1
    assert result.producer_attribution["duplicate_items_dropped"] == 0


class _EnvelopeProvider(_UnitProvider):
    """Answers each unit with a shape the caller chooses, to pin how a bad envelope lands."""

    def __init__(self, build, wrap):
        super().__init__(build)
        self._wrap = wrap

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        self.payloads.append(payload)
        items = self._build(len(self.payloads) - 1, payload["evidence"])
        return ModelResponse(content=json.dumps(self._wrap(items), ensure_ascii=False),
                             finish_reason="stop")


def test_an_extra_top_level_key_is_named_and_dropped(tmp_path):
    source = _lines(tmp_path, 90)
    provider = _EnvelopeProvider(
        lambda index, rows: [_row("entity", f"dept_{index}", _named(rows), rows[0]["evidence_id"])],
        lambda items: {"type": "json_object", "items": items})
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    # The answer is used, and the key the contract does not allow is reported.
    assert len([item for item in result.semantic_candidate.items if item.kind == "entity"]) == 3
    assert result.producer_attribution["envelope_keys_dropped"] == ["type"]
    assert result.producer_attribution["refused_units"] == []


def test_one_unreadable_unit_costs_only_that_unit(tmp_path):
    source = _lines(tmp_path, 90)
    # The key names the unit, not the call: the middle unit answers the same unreadable
    # envelope when it is asked again, exactly as a real page would.
    def unit_index(rows):
        return int(rows[0]["locator"].split(":", 1)[1]) // 40

    provider = _EnvelopeProvider(
        lambda index, rows: [_row("entity", f"dept_{unit_index(rows)}", _named(rows),
                                  rows[0]["evidence_id"])],
        lambda items: {"items": items} if items[0]["key"] != "dept_1" else {"rows": []})
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    # Two units answered, the middle one did not, and the refusal names the unit.
    assert [item.key for item in result.semantic_candidate.items if item.kind == "entity"] == [
        "dept_0", "dept_2"]
    assert result.producer_attribution["unit_item_counts"] == [1, 0, 1]
    # Three units, four calls: the unreadable unit was asked for once more and refused.
    assert len(provider.payloads) == 4
    [refused] = result.producer_attribution["refused_units"]
    # The refusal names what was wrong with that answer, not just that it failed.
    assert refused["code"] == "envelope_invalid"
    assert refused["detail"] == "invalid semantic output envelope"
    assert refused["unit"].startswith("lines:")


def test_a_truncated_unit_names_that_reason(tmp_path):
    source = _lines(tmp_path, 90)

    class Truncating(_UnitProvider):
        def request(self, request):
            payload = json.loads(request.messages[-1].content)
            self.payloads.append(payload)
            if len(self.payloads) == 2:
                return ModelResponse(content='{"items": [', finish_reason="length")
            items = self._build(len(self.payloads) - 1, payload["evidence"])
            return ModelResponse(content=json.dumps({"items": items}, ensure_ascii=False),
                                 finish_reason="stop")

    provider = Truncating(lambda index, rows: [_row("entity", f"dept_{index}", _named(rows), rows[0]["evidence_id"])])
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    [refused] = result.producer_attribution["refused_units"]
    assert refused["code"] == "truncated"
    assert [item.key for item in result.semantic_candidate.items if item.kind == "entity"] == ["dept_0", "dept_2"]


def test_every_unit_refused_still_fails_the_card(tmp_path):
    source = _lines(tmp_path, 90)
    provider = _EnvelopeProvider(lambda index, rows: [], lambda items: {"rows": []})
    try:
        UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    except ValueError as exc:
        assert str(exc) == "all 3 extraction units were refused"
    else:
        raise AssertionError("a card with no readable unit must fail")


def test_a_merged_candidate_may_outgrow_one_answers_envelope(tmp_path):
    source = _lines(tmp_path, 130)
    # Four units answer sixty claims each: 240 items, past the 192 a single answer may
    # carry, and no one answer ever carried them.
    provider = _UnitProvider(lambda index, rows: [
        _row("claim", f"claim_{index}_{position}", f"第{index}页第{position}条职责",
             rows[position % len(rows)]["evidence_id"]) for position in range(60)])
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    # The merged candidate carries the 240 claims; the reader unknowns ride beside them.
    claims = [item for item in result.semantic_candidate.items if item.kind == "claim"]
    assert len(claims) == 240
    assert result.producer_attribution["unit_item_counts"] == [60, 60, 60, 60]
