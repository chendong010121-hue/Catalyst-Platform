"""Capacity refusals and the producer endpoint contract, with no model call.

Three holes are closed here:

* an external producer could name a relation endpoint that its own items never
  declare, so a grounded-looking edge pointed at nothing;
* an over-capacity semantic answer is refused whole and counted instead of
  becoming "the envelope is invalid";
* the shipped Generator method text reaches the model call, while the envelope
  header that contradicts this Port stays out.

Every test drives the Port through a stub provider; no credential is read and no
network call is made.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime.contracts import ModelResponse
from catalyst_platform.understand_only import (
    SemanticCapacityError,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)


def _request(source: Path, *, intent=UnderstandIntent.KNOWLEDGE_PROPOSE, sources=None) -> UnderstandingRequest:
    refs = tuple(sources) if sources is not None else (source,)
    return UnderstandingRequest(
        request_id="req_capacity",
        message="请理解这些资料中的经营职责、规则和未知项",
        source_refs=refs,
        intent=intent,
        scope_id="scope_capacity",
        requested_depth="semantic",
        budget_steps=16,
    )


def _source(tmp_path: Path, text: str = "财务部门负责月度经营分析。") -> Path:
    source = tmp_path / "business.md"
    source.write_text(text, encoding="utf-8")
    return source


def _two_sources(tmp_path: Path, lines: int = 400) -> tuple[Path, Path]:
    """Each file stays under the per-file locator limit; together they pass the unit cap."""
    written = []
    for name in ("a.md", "b.md"):
        path = tmp_path / name
        path.write_text(
            "\n".join(f"{name}第{index}条经营事项记录" for index in range(lines)), encoding="utf-8")
        written.append(path)
    return written[0], written[1]


def _rows(count: int, evidence_id: str, *, numbered: bool = False) -> list[dict]:
    # One name is one entity, so a fixture that spelled one name sixty-four times would
    # now be folded into a single row and would measure the merge, not the ceiling. A
    # card that names sixty-four things names sixty-four things.
    return [
        {
            "kind": "entity",
            "key": f"dept_{index}",
            "meaning": f"财务部门{index}" if numbered else "财务部门",
            "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id],
        }
        for index in range(count)
    ]


def _named_source(tmp_path: Path, count: int = 64) -> Path:
    """A source that spells `count` departments, each with its own name."""
    return _source(tmp_path, "、".join(f"财务部门{index}" for index in range(count)) + "负责月度经营分析。")


def _claim_rows(count: int, evidence_id: str) -> list[dict]:
    return [
        {
            "kind": "claim",
            "key": f"duty_{index}",
            "meaning": "财务部门负责月度经营分析。",
            "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [evidence_id],
        }
        for index in range(count)
    ]


class _Provider:
    """Minimal semantic provider that records the request it was given."""

    def __init__(self, build):
        self._build = build
        self.requests: list = []

    def request(self, request):
        self.requests.append(request)
        payload = json.loads(request.messages[-1].content)
        evidence_id = payload["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence_id)}, ensure_ascii=False),
                             finish_reason="stop")


def test_over_capacity_semantic_output_is_refused_whole_and_counted(tmp_path: Path):
    source = _source(tmp_path)
    # The total is the two segment ceilings together: 64 entities + 128 statements.
    provider = _Provider(lambda evidence_id: _rows(65, evidence_id) + _claim_rows(128, evidence_id))
    with pytest.raises(SemanticCapacityError) as excinfo:
        UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    assert excinfo.value.limit == 192
    assert excinfo.value.received == 193
    assert excinfo.value.refused_item_count == 1
    assert "refused, not truncated" in str(excinfo.value)
    assert excinfo.value.public_code == "semantic_capacity_exceeded"
    # The model is told the envelope it is judged against, so the refusal is its own.
    assert "at most 192 items" in provider.requests[0].messages[0].content


def test_an_answer_at_the_limit_is_still_accepted(tmp_path: Path):
    source = _named_source(tmp_path)
    # 64 entities and 128 statements fill both segments and the total exactly.
    provider = _Provider(lambda evidence_id: _rows(64, evidence_id, numbered=True) + _claim_rows(128, evidence_id))
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    assert result.semantic_candidate is not None
    # The Port may add its own unresolved rows on top of the producer answer; what
    # matters here is that an answer at the limit is accepted and asked for once.
    assert len(result.semantic_candidate.items) >= 192
    assert len(provider.requests) == 1


def test_the_statement_segment_holds_the_shape_a_real_deck_produced(tmp_path: Path):
    """55 entities and 69 statements fit: that is what one 14-page deck actually emitted."""
    source = _named_source(tmp_path, 55)
    provider = _Provider(lambda evidence_id: _rows(55, evidence_id, numbered=True) + _claim_rows(69, evidence_id))
    result = UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    assert result.semantic_candidate is not None
    assert len(provider.requests) == 1
    # The model is told the new segment bound, not the old one.
    system = provider.requests[0].messages[0].content
    assert "at most 128 items of every other kind" in system
    assert "at most 64 items of every other kind" not in system


def test_the_statement_segment_still_refuses_its_own_overflow(tmp_path: Path):
    source = _source(tmp_path)
    provider = _Provider(lambda evidence_id: _rows(30, evidence_id) + _claim_rows(129, evidence_id))
    with pytest.raises(SemanticCapacityError) as excinfo:
        UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    assert (excinfo.value.segment, excinfo.value.limit, excinfo.value.received) == ('other_items', 128, 129)


def test_the_entity_segment_keeps_its_own_ceiling(tmp_path: Path):
    source = _source(tmp_path)
    provider = _Provider(lambda evidence_id: _rows(65, evidence_id) + _claim_rows(10, evidence_id))
    with pytest.raises(SemanticCapacityError) as excinfo:
        UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    assert (excinfo.value.segment, excinfo.value.limit, excinfo.value.received) == ('entities', 64, 65)


def test_generator_method_reaches_the_model_call_without_the_foreign_envelope(tmp_path: Path):
    source = _source(tmp_path)
    provider = _Provider(lambda evidence_id: _rows(1, evidence_id))
    UnderstandPort().understand(_request(source), source_root=tmp_path, semantic_provider=provider)
    system = provider.requests[0].messages[0].content
    # The method body ships in the package and must be in front of the model.
    assert "# Method B" in system
    assert "scene-first" in system.casefold()
    # The package head declares {scheme,items}, which this Port never accepts.
    assert "{scheme,items}" not in system.replace(" ", "")
    # The Port still states its own envelope after the method.
    assert "only top-level key is items" in system


def test_producer_relation_may_only_join_entities_its_items_declare(tmp_path: Path):
    source = _source(tmp_path, "财务部门与法务部门共同复核合同。")
    port = UnderstandPort()
    base = port.understand(_request(source), source_root=tmp_path)
    evidence_id = base.evidence_refs[0].evidence_id
    common = dict(kind="entity", meaning="财务部门", evidence_class="SOURCE_DIRECT", evidence_refs=[evidence_id])

    undeclared = port.attach_producer_items(
        base,
        producer_kind="CODEX_EXTERNAL",
        producer_invocation_id="codex-endpoint-test",
        items=[
            {**common, "key": "finance"},
            {"kind": "relation", "key": "approves", "meaning": "财务部门与法务部门共同复核合同",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
             "subject": "finance", "predicate": "approves", "object": "legal"},
        ],
    )
    # The endpoint stays unresolved and is never created: the relation keeps its row as
    # an unresolved one, so the sentence is still there for a reviewer to finish.
    assert undeclared.producer_attribution["item_contract_drops"] == [
        {"item_key": "approves", "rule": "relation_endpoint_not_declared"}]
    kept = undeclared.semantic_candidate.items
    assert [item.kind for item in kept] == ["entity", "relation"]
    assert kept[-1].evidence_class == "unresolved"
    assert kept[-1].uncertainty.startswith("degraded:relation_endpoint_not_declared")

    accepted = port.attach_producer_items(
        base,
        producer_kind="CODEX_EXTERNAL",
        producer_invocation_id="codex-endpoint-test",
        items=[
            {**common, "key": "finance"},
            {**common, "key": "legal", "meaning": "法务部门"},
            {"kind": "relation", "key": "approves", "meaning": "财务部门与法务部门共同复核合同",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
             "subject": "finance", "predicate": "approves", "object": "legal"},
        ],
    )
    assert any(item.kind == "relation" and item.object == "legal" for item in accepted.semantic_candidate.items)


def test_producer_relation_cannot_use_a_declared_claim_as_endpoint(tmp_path: Path):
    source = _source(tmp_path)
    port = UnderstandPort()
    base = port.understand(_request(source), source_root=tmp_path)
    evidence_id = base.evidence_refs[0].evidence_id
    result = port.attach_producer_items(
        base,
        producer_kind="CODEX_EXTERNAL",
        producer_invocation_id="codex-claim-endpoint",
        items=[
            {"kind": "claim", "key": "duty", "meaning": "财务部门承担经营分析。",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]},
            {"kind": "relation", "key": "links", "meaning": "财务部门负责月度经营分析",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id],
             "subject": "duty", "predicate": "owned_by", "object": "duty"},
        ],
    )
    # A claim is not an endpoint: the relation is refused that standing and kept
    # unresolved with the rule named, the claim stands untouched.
    assert result.producer_attribution["item_contract_drops"] == [
        {"item_key": "links", "rule": "relation_endpoint_not_declared"}]
    kept = result.semantic_candidate.items
    assert [item.key for item in kept] == ["duty", "links"]
    assert kept[-1].evidence_class == "unresolved"
    assert kept[-1].uncertainty.startswith("degraded:relation_endpoint_not_declared")


def test_inventory_truncation_stops_ontology_modeling_instead_of_trimming(tmp_path: Path):
    sources = _two_sources(tmp_path)
    provider = _Provider(lambda evidence_id: _rows(1, evidence_id))
    with pytest.raises(SemanticCapacityError) as excinfo:
        UnderstandPort().understand(_request(sources[0], sources=sources), source_root=tmp_path, semantic_provider=provider)
    assert excinfo.value.limit == 500
    assert excinfo.value.received > 500
    assert "source units" in str(excinfo.value)
    assert provider.requests == []


def test_inventory_truncation_stays_a_warning_for_other_intents(tmp_path: Path):
    sources = _two_sources(tmp_path)
    result = UnderstandPort().understand(_request(sources[0], intent=UnderstandIntent.TASK_USE, sources=sources), source_root=tmp_path)
    assert any(warning.startswith("UNITS_TRUNCATED:") for warning in result.source_warnings)
