"""Read-only capability review: what an incoming claim would meet in the library.

Discovers capability claims, validates them, and compares every pair that shares
a responsibility key.  It reads files and returns a projection; it never writes,
never activates, never calls a model, and never decides which capability is
better.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .capability_claim import validate_claim
from .capability_compare import compare_claims

MAX_CLAIMS = 50
MAX_PAIRS = 200
EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "capability_claims"
CLAIMS_SUBDIR = Path(".catalyst") / "capability-claims"


def _claim_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.claim.json") if path.is_file() and not path.is_symlink())


def _load(files: Iterable[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claims: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for path in files:
        try:
            claim = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append({"file": path.name, "violation": f"unreadable:{type(exc).__name__}"})
            continue
        violations = validate_claim(claim)
        if violations:
            errors.append({"file": path.name, "violation": violations[0]})
            continue
        claims.append(claim)
    return claims, errors


def _summary(claim: dict[str, Any]) -> dict[str, Any]:
    capability = claim["capability"]
    return {
        "id": capability["id"],
        "version": capability["version"],
        "kind": capability["kind"],
        "responsibility_key": capability["responsibility_key"],
        "statement": capability["statement"],
    }


def _coverage(result: dict[str, Any]) -> dict[str, int]:
    row = next((item for item in result["fields"] if item["field"] == "what.obligations"), {})
    return {
        "matched": len(row.get("matched", [])),
        "left_only": len(row.get("left_only", [])),
        "right_only": len(row.get("right_only", [])),
    }


def review(workspace: str | Path, *, examples_root: str | Path = EXAMPLES) -> dict[str, Any]:
    """Return every comparison the library would surface for these claims."""
    root = Path(workspace)
    claims_dir = root / CLAIMS_SUBDIR
    files = _claim_files(claims_dir)
    source = "workspace"
    if not files:
        claims_dir = Path(examples_root)
        files = _claim_files(claims_dir)
        source = "examples"

    claims, errors = _load(files[:MAX_CLAIMS])
    claims.sort(key=lambda claim: (claim["capability"]["id"], claim["capability"]["version"]))

    items: list[dict[str, Any]] = []
    truncated = False
    for index, left in enumerate(claims):
        for right in claims[index + 1:]:
            if left["capability"]["responsibility_key"] != right["capability"]["responsibility_key"]:
                continue
            if len(items) >= MAX_PAIRS:
                truncated = True
                break
            result = compare_claims(left, right)
            items.append({
                "relation": result["relation"],
                "action": result["action"],
                "reason": result["reason"],
                "requires_owner_confirmation": result["requires_owner_confirmation"],
                "evaluation_questions": result["evaluation_questions"],
                "input_digest": result["input_digest"],
                "coverage": _coverage(result),
                "left": _summary(left),
                "right": _summary(right),
            })
    order = {"SAME": 0, "SIMILAR": 1, "COMPLEMENTARY": 2, "UNKNOWN": 3, "DISTINCT": 4}
    items.sort(key=lambda item: (order.get(item["relation"], 9), item["input_digest"]))

    return {
        "items": items,
        "claims": [_summary(claim) for claim in claims],
        "source": source,
        "claims_dir": str(claims_dir),
        "errors": errors,
        "truncated": truncated,
        "write_enabled": False,
        "scope": "READ_ONLY_COMPARISON_NO_WIKI_WRITE",
    }
