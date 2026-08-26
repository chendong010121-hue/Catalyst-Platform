"""Catalyst Minimum Operational V1 — small current-state proof.

This test deliberately proves only the current operational seams. Historical Stage and
Case proofs remain available through frozen Git refs and are not required by active main.
"""
from __future__ import annotations

import json
from pathlib import Path

from examples.platform_standard_reference import make_report_invocation, make_stack
from platform_standard.models import CapabilityDescriptor, Invocation

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json"
BASELINE = ROOT / "CATALYST_OPERATIONAL_BASELINE_V1.md"
ASSETS = ROOT / "assets" / "knowledge"
SKILLS = ROOT / "platform-harness" / "skills"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    baseline = BASELINE.read_text(encoding="utf-8")
    assert "CATALYST MINIMUM OPERATIONAL V1" in baseline
    assert "STOP PLANNED PLATFORM PRE-DEVELOPMENT" in baseline

    index = _load(INDEX)
    assert index["index_version"] == "0.1"
    assert len(index["entries"]) == 3
    allowed = {
        "summary", "authority_ref", "capability_ref", "asset_refs", "evidence_refs",
        "lineage_refs", "realization_or_binding_refs", "known_limits_ref",
        "domain_or_enterprise_binding_refs",
    }
    for entry in index["entries"]:
        assert set(entry).issubset(allowed)
        assert entry["summary"]
        assert entry["authority_ref"]
        assert not ({"status", "health", "score", "input_schema", "output_schema", "execution"} & set(entry))

    formal = next(e for e in index["entries"] if e.get("capability_ref", {}).get("id") == "compose_report")
    assert formal["capability_ref"] == {"id": "compose_report", "version": "1.0.0"}

    waku = next(e for e in index["entries"] if "Retrieval-gated memory" in e["summary"])
    assert "capability_ref" not in waku
    assert waku["authority_ref"]["path"] == "assets/knowledge/WAKU_RETRIEVAL_GATED_MEMORY_V0.1.json"
    waku_asset = _load(ASSETS / "WAKU_RETRIEVAL_GATED_MEMORY_V0.1.json")
    assert waku_asset["asset_type"] == "governed_mechanism_knowledge"
    assert waku_asset["lineage"]

    safety = next(e for e in index["entries"] if "fail-closed numeric safety" in e["summary"])
    assert "capability_ref" not in safety
    assert safety["authority_ref"]["path"] == "assets/knowledge/FAIL_CLOSED_NUMERIC_SAFETY_V0.1.json"
    safety_asset = _load(ASSETS / "FAIL_CLOSED_NUMERIC_SAFETY_V0.1.json")
    assert safety_asset["accepted_evidence"]["professional_result"]["unsupported_regulatory_numeric_claims"] == 0
    assert safety_asset["accepted_evidence"]["professional_result"]["case_C_fail_closed"] == "PASS"

    skill_markers = {
        "agent-construction": "Capability Search before construction",
        "capability-benchmark-design": "Test what a user actually needs the system to do",
        "capability-evaluation": "A capability is proven by observable user-task evidence",
        "capability-optimization": "Repair is not the default",
    }
    for skill, marker in skill_markers.items():
        text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        assert marker in text, (skill, marker)

    # The active root is a current product surface, not a historical Stage archive.
    for historical in (
        "HANDOFF.md",
        "CATALYST_PLATFORM_INTEGRATION_V0.1_STAGE_SPEC.md",
        "CATALYST_CASE01_CONSTRUCTION_DECISION_DRY_RUN_V0.1.json",
        "CATALYST_TEST_DECISION_WAKU_REUSE_V0.1.json",
        "IMPLEMENTATION_NOTES.md",
        "TEST_MANIFEST.md",
    ):
        assert not (ROOT / historical).exists(), historical
    assert not (ROOT / "case-01").exists()
    assert not (ROOT / "case-02").exists()

    registry, adapter = make_stack()
    descriptor = registry.get("compose_report", "1.0.0")
    assert descriptor is not None
    assert descriptor.id == formal["capability_ref"]["id"]
    assert descriptor.capability_version == formal["capability_ref"]["version"]

    result = adapter.execute(
        make_report_invocation(
            {"title": "Operational V1", "sections": ["existing capability reuse"]},
            invocation_id="inv_operational_v1",
            trace_id="trace_operational_v1",
        )
    )
    assert result.status == "success"
    assert result.output["report_text"].startswith("# Operational V1")
    assert result.artifacts[0].producer.capability_id == "compose_report"
    assert result.artifacts[0].producer.invocation_id == "inv_operational_v1"

    missing = adapter.execute(
        Invocation(
            id="inv_operational_missing",
            capability_id="not_registered",
            capability_version="1.0.0",
            input={},
            context={"extensions": {}},
            trace_id="trace_operational_missing",
        )
    )
    assert missing.status == "failure"
    assert missing.error["code"] == "capability_not_found"

    assert tuple(CapabilityDescriptor.__dataclass_fields__) == (
        "standard_version", "kind", "id", "extensions", "name", "description",
        "capability_version", "input_schema", "output_schema", "execution",
    )

    print("PASS: Catalyst Minimum Operational V1")


if __name__ == "__main__":
    main()
