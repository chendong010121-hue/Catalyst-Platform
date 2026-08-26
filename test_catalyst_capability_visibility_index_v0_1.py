from __future__ import annotations

import json
from pathlib import Path

INDEX_PATH = Path(__file__).with_name("CATALYST_CAPABILITY_VISIBILITY_INDEX_V0.1.json")


def _load_index() -> dict:
    with INDEX_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _assert_ref(ref: dict) -> None:
    assert isinstance(ref.get("repository"), str) and ref["repository"]
    assert isinstance(ref.get("ref"), str) and ref["ref"]
    if "path" in ref:
        assert isinstance(ref["path"], str) and ref["path"]


def main() -> None:
    index = _load_index()
    assert index["index_version"] == "0.1"
    entries = index["entries"]
    assert isinstance(entries, list) and len(entries) == 3

    summaries = [entry["summary"] for entry in entries]
    assert all(isinstance(summary, str) and summary.strip() for summary in summaries)

    for entry in entries:
        assert set(entry).issubset(
            {
                "summary",
                "authority_ref",
                "capability_ref",
                "asset_refs",
                "evidence_refs",
                "lineage_refs",
                "realization_or_binding_refs",
                "known_limits_ref",
                "domain_or_enterprise_binding_refs",
            }
        )
        _assert_ref(entry["authority_ref"])
        for key in (
            "asset_refs",
            "evidence_refs",
            "lineage_refs",
            "realization_or_binding_refs",
            "domain_or_enterprise_binding_refs",
        ):
            for ref in entry.get(key, []):
                _assert_ref(ref)
        if "known_limits_ref" in entry:
            _assert_ref(entry["known_limits_ref"])

    formal = next(e for e in entries if e.get("capability_ref", {}).get("id") == "compose_report")
    assert formal["capability_ref"] == {"id": "compose_report", "version": "1.0.0"}
    assert "input_schema" not in formal and "output_schema" not in formal and "execution" not in formal

    harvested = next(e for e in entries if "Retrieval-gated memory" in e["summary"])
    assert "capability_ref" not in harvested
    assert "status" not in harvested and "health" not in harvested and "score" not in harvested

    safety = next(e for e in entries if "fail-closed numeric safety" in e["summary"])
    assert "capability_ref" not in safety
    assert "asset_refs" not in safety
    assert "evidence_refs" in safety
    assert "status" not in safety and "health" not in safety and "score" not in safety

    print("PASS: Catalyst Capability Visibility Index V0.1 rediscovery proof")


if __name__ == "__main__":
    main()
