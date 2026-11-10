"""A candidate says the class storage will carry, and names the budget it overflowed.

Two alignments, both mechanical:

* the candidate view reports `stored_evidence_class`, the class harvest will give
  the entry (`inferred`, or `unresolved` for an unknown), not only the class the
  producer declared;
* the two segment budgets — 64 entities and 64 other items — are checked before
  anything is attached, and a refusal names the segment in its public code.
"""
from types import SimpleNamespace

import pytest

from agent_runtime.contracts import Failure
from catalyst_platform.semantic_tool import UnderstandCapabilityAdapter, candidate_summary
from catalyst_platform.understand_only import (
    SemanticCapacityError,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    stored_evidence_class,
)


def _names(count):
    return [f"部门{index}" for index in range(count)]


def _base(tmp_path, names=("财务部门",)):
    source = tmp_path / "business.md"
    source.write_text("、".join(names) + "。", encoding="utf-8")
    port = UnderstandPort()
    result = port.understand(
        UnderstandingRequest("budget", "整理职责", source_refs=(source,), intent=UnderstandIntent.KNOWLEDGE_PROPOSE),
        source_root=tmp_path)
    return port, result, result.evidence_refs[0].evidence_id


def _entities(names, evidence_id):
    return [{"kind": "entity", "key": f"e{index}", "meaning": name,
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]}
            for index, name in enumerate(names)]


def _attach(port, base, rows):
    return port.attach_producer_items(base, producer_kind="CODEX_EXTERNAL",
                                      producer_invocation_id="budget", items=rows)


def test_the_entity_segment_accepts_sixty_four_and_refuses_sixty_five(tmp_path):
    names = _names(65)
    port, base, evidence_id = _base(tmp_path, names)
    accepted = _attach(port, base, _entities(names[:64], evidence_id))
    assert len([row for row in accepted.semantic_candidate.items if row.kind == "entity"]) == 64
    with pytest.raises(SemanticCapacityError) as raised:
        _attach(port, base, _entities(names, evidence_id))
    assert (raised.value.limit, raised.value.received, raised.value.segment) == (64, 65, "entities")
    assert raised.value.refused_item_count == 1


def test_the_other_segment_counts_claims_relations_and_the_rest(tmp_path):
    # One segment for every non-entity kind; the ceiling is 128 and the total 192.
    port, base, evidence_id = _base(tmp_path)
    rows = _entities(["财务部门"], evidence_id) + [
        {"kind": "claim", "key": f"c{index}", "meaning": f"财务部门负责事项{index}",
         "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence_id]} for index in range(129)]
    with pytest.raises(SemanticCapacityError) as raised:
        _attach(port, base, rows)
    assert (raised.value.limit, raised.value.received, raised.value.segment) == (128, 129, "other_items")


def test_the_refusal_reaches_the_agent_with_the_segment():
    def refuse(source_ids):
        raise SemanticCapacityError(64, 65, what="entity segment", segment="entities")

    context = SimpleNamespace(plugin_services={"understand.execute": refuse}, raise_if_cancelled=lambda: None)
    observation = UnderstandCapabilityAdapter().invoke({"source_ids": ["s1"]}, context)
    assert isinstance(observation, Failure)
    assert observation.error == "understand_proposal_failed:semantic_capacity_exceeded items=65 limit=64 segment=entities"


def test_a_candidate_reports_the_class_harvest_will_store():
    assert stored_evidence_class("claim") == "inferred"
    assert stored_evidence_class("relation") == "inferred"
    assert stored_evidence_class("unknown") == "unresolved"


def test_the_candidate_view_states_the_stored_class_beside_the_declared_one():
    output = {
        "understanding": {"semantic_candidate": {"items": [
            {"item_id": "i1", "kind": "claim", "key": "duty", "meaning": "财务部门负责月度经营分析",
             "evidence_class": "observed_from_source"},
            {"item_id": "i2", "kind": "unknown", "key": "approval", "meaning": "是否批准未说明",
             "evidence_class": "unresolved"},
        ]}, "evidence_refs": []},
        "proposal": {"candidate_id": "c1"}, "selected_item_ids": [], "omitted_item_ids": [],
    }
    preview = candidate_summary(output)["preview"]
    assert [(row["evidence_class"], row["stored_evidence_class"]) for row in preview] == [
        ("observed_from_source", "inferred"), ("unresolved", "unresolved")]
