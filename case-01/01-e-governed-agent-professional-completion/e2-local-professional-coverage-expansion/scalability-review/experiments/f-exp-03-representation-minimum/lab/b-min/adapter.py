from __future__ import annotations

from typing import Any, Iterable

from shared.model import GROUPS, source_for


def adapt(
    case: dict[str, Any],
    registry: dict[str, Any],
    omit_groups: Iterable[str] = (),
) -> dict[str, Any]:
    omitted = set(omit_groups)
    source = source_for(case, registry) if "G-BASE" not in omitted else None
    typed = case["b_min"]
    return {
        "track": "B_MIN",
        "groups": [group for group in GROUPS if group not in omitted],
        "base": source,
        "scope": None if "G-SCOPE" in omitted else typed["G-SCOPE"],
        "conditions": None if "G-CONDITION" in omitted else typed["G-CONDITION"],
        "numeric": None if "G-NUMERIC" in omitted else typed["G-NUMERIC"],
        "semantic_fields": {
            group: typed[group]
            for group in ("G-SCOPE", "G-CONDITION", "G-NUMERIC")
            if group not in omitted
        },
    }
