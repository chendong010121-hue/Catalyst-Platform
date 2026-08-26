"""Catalyst Platform Integration V0.1 — deterministic cross-component proof.

This is a proof, not a new framework. It reuses existing Platform/Adapter/Runtime
surfaces and validates the repository-native visibility + construction-decision
handoff without changing their ownership.
"""
from __future__ import annotations

import json
from pathlib import Path

from examples.platform_standard_reference import make_report_invocation, make_stack
from platform_standard.models import CapabilityDescriptor, Invocation

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json"
DECISION = ROOT / "CATALYST_CONSTRUCTION_DECISION_PROOF_COMPOSE_REPORT_V0.1.json"
CASE01_DRY_RUN = ROOT / "CATALYST_CASE01_CONSTRUCTION_DECISION_DRY_RUN_V0.1.json"
SKILL = ROOT / "platform-harness" / "skills" / "agent-construction" / "SKILL.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    index = _load(INDEX)
    decision = _load(DECISION)
    case01 = _load(CASE01_DRY_RUN)
    skill = SKILL.read_text(encoding="utf-8")

    entries = index["entries"]
    formal = next(e for e in entries if e.get("capability_ref", {}).get("id") == "compose_report")
    assert formal["capability_ref"] == {"id": "compose_report", "version": "1.0.0"}
    assert not ({"input_schema", "output_schema", "execution", "health", "score", "status"} & set(formal))
    harvested = next(e for e in entries if "Retrieval-gated memory" in e["summary"])
    assert "capability_ref" not in harvested
    safety = next(e for e in entries if "fail-closed numeric safety" in e["summary"])
    assert "capability_ref" not in safety and "asset_refs" not in safety

    reused = decision["capability_search"]["reused_capability_refs"]
    assert {"id": "compose_report", "version": "1.0.0"} in reused
    assert decision["solution"]["selected_solution_form"] == "Deterministic implementation"
    assert decision["capability_search"]["missing_or_unproven_capability_needs"] == []

    assert case01["solution"]["selected_solution_form"] == "UNDECIDED_PENDING_MISSING_CAPABILITY_PROOF"
    assert case01["capability_search"]["missing_or_unproven_capability_needs"]
    assert "vector database without retrieval evidence" in case01["proof"]["not_required_now"]

    for marker in (
        "Capability Search before construction",
        "REUSE\n→ ADAPT\n→ COMPOSE\n→ RECONSTRUCT\n→ BUILD NEW ONLY FOR THE REMAINING GAP",
        "Select the simplest justified solution form",
        "Emit Runtime requirements, do not absorb Runtime",
        "Emit Evaluation evidence requirements, do not absorb Evaluation",
        "Construction Decision output",
        "Stop rule",
    ):
        assert marker in skill, marker

    registry, adapter = make_stack()
    descriptor = registry.get("compose_report", "1.0.0")
    assert descriptor is not None
    assert descriptor.id == formal["capability_ref"]["id"]
    assert descriptor.capability_version == formal["capability_ref"]["version"]

    invocation = make_report_invocation(
        {"title": "Catalyst Integration", "sections": ["existing capability reuse"]},
        invocation_id="inv_catalyst_integration_v01",
        trace_id="trace_catalyst_integration_v01",
    )
    result = adapter.execute(invocation)
    assert result.status == "success"
    assert result.output["report_text"].startswith("# Catalyst Integration")
    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.producer.capability_id == "compose_report"
    assert artifact.producer.invocation_id == invocation.id

    event_types = [e.event_type for e in adapter.trace_events() if e.trace_id == invocation.trace_id]
    assert "invocation.started" in event_types
    assert "invocation.completed" in event_types
    assert "artifact.created" in event_types

    missing = adapter.execute(
        Invocation(
            id="inv_catalyst_missing_v01",
            capability_id="not_registered",
            capability_version="1.0.0",
            input={},
            context={"extensions": {}},
            trace_id="trace_catalyst_missing_v01",
        )
    )
    assert missing.status == "failure"
    assert missing.error["code"] == "capability_not_found"

    assert tuple(CapabilityDescriptor.__dataclass_fields__) == (
        "standard_version", "kind", "id", "extensions", "name", "description",
        "capability_version", "input_schema", "output_schema", "execution",
    )

    print("PASS: Catalyst Platform Integration V0.1 cross-component proof")


if __name__ == "__main__":
    main()
