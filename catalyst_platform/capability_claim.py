"""Validate a capability claim and prove each field is backed or declared unknown.

A claim is compared with other claims, so it must not contain a field that is
blank, invented or unsupported.  The rules here are the ones the JSON Schema
cannot express on its own:

* every evidence id a claim refers to exists;
* every evidence record points at a path that exists in the same claim;
* every claim-bearing item carries evidence, or the claim declares that path as
  unknown with a reason;
* a path cannot be both backed and declared unknown;
* an unobservable quick start must say why;
* an obligation whose verifier is "none" cannot demand more than a quote;
* an input or an output whose form is unknown says so in why.unknowns, and an
  unknown invocation mode does the same;
* a requirement never carries a secret value, only its key name;
* next_evidence names an obligation or an unknown that exists in this claim.

A second entry point, evidence_carryover_violations, compares two revisions of
one claim: an evidence record that both carry must not change its strength, its
quote, its source or who asserted it. Raising a level means adding a receipt,
never editing the record that is already there.

Nothing is written and no owner is imported.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "capability_claim_v1.schema.json"

# The authority ladder.  A strength maps to one rung; a level may only be raised
# one rung at a time, and only by evidence that is actually on record.
AUTHORITY_ORDER = ("QUOTED", "STRUCTURAL", "EXECUTED", "MEASURED")
STRENGTH_AUTHORITY = {
    "DIRECT_QUOTE": "QUOTED",
    "EXTERNAL_DOC": "QUOTED",  # another product's document never outranks our own artifact
    "STRUCTURAL": "STRUCTURAL",
    "EXECUTED": "EXECUTED",
    "MEASURED": "MEASURED",
}
DEFAULT_REQUIRED_AUTHORITY = "STRUCTURAL"


def authority_rank(authority: str | None) -> int:
    """0 for QUOTED .. 3 for MEASURED; -1 for anything not on the ladder."""
    try:
        return AUTHORITY_ORDER.index(authority)
    except ValueError:
        return -1


def authority_of(strength: str | None) -> str | None:
    return STRENGTH_AUTHORITY.get(strength or "")


# A secret is stored as a key name.  These patterns catch a value that was pasted
# in instead, so it is refused before it reaches disk.
_SECRET_PREFIXES = ("sk-", "ghp_", "gho_", "ghu_", "xoxb-", "xoxp-", "AKIA", "glpat-")
_SECRET_LIKE = re.compile(r"^(?:" + "|".join(re.escape(prefix) for prefix in _SECRET_PREFIXES) + r")[A-Za-z0-9_\-]{8,}$")


def looks_like_secret(value: Any) -> bool:
    """True when a string looks like a pasted credential rather than a key name."""
    if not isinstance(value, str) or not value:
        return False
    if _SECRET_LIKE.match(value):
        return True
    # A long opaque run with no spaces and no path punctuation is treated the same way.
    return len(value) > 60 and " " not in value and "/" not in value and "\\" not in value


# Fields that fix what an evidence record means.  Changing any of them rewrites
# history instead of adding to it.
EVIDENCE_IMMUTABLE_FIELDS = (
    "strength",
    "quote",
    "span_sha256",
    "source_id",
    "revision",
    "locator",
    "field",
    "asserted_by",
    "asserted_at",
)

# How two claims may be compared, per field family.  Behavioural properties are
# named explicitly and always win over their parent: quality cannot be asserted
# from text, only measured.
BEHAVIOURAL = "behavioral"

COMPARABILITY = {
    "capability.id": "exact",
    "capability.responsibility_key": "exact",
    "capability.version": "exact",
    "capability.kind": "exact",
    "capability.statement": "normalized",
    "what.performance": BEHAVIOURAL,
    "what.cost": BEHAVIOURAL,
    "what.quality": BEHAVIOURAL,
    "what.robustness": BEHAVIOURAL,
    "what": "normalized",
    "how.interface": "exact",
    "how.entry": "exact",
    "how.side_effects": "normalized",
    "how.permissions": "normalized",
    "quick_start": "exact",
}


def comparability_for(path: str) -> str:
    """Return exact / normalized / behavioral for a claim field path."""
    for prefix in sorted(COMPARABILITY, key=len, reverse=True):
        if path == prefix or path.startswith(prefix + ".") or path.startswith(prefix + "["):
            return COMPARABILITY[prefix]
    return BEHAVIOURAL


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def claim_digest(claim: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(claim)).hexdigest()


_SEGMENT = re.compile(r"\[([0-9]+)\]|([A-Za-z_][A-Za-z0-9_]*)")


def resolve_path(document: Any, path: str) -> tuple[bool, Any]:
    """Resolve ``a.b[0].c`` inside a claim; return (found, value)."""
    if not isinstance(path, str) or not path:
        return False, None
    current = document
    for match in _SEGMENT.finditer(path):
        index, key = match.groups()
        if index is not None:
            if not isinstance(current, list) or int(index) >= len(current):
                return False, None
            current = current[int(index)]
            continue
        if not isinstance(current, Mapping) or key not in current:
            return False, None
        current = current[key]
    return True, current


def _claim_items(claim: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, Any]]]:
    """Yield every evidence-bearing item with its path."""
    capability = claim.get("capability") or {}
    what = claim.get("what") or {}
    how = claim.get("how") or {}
    groups = (
        ("capability.anchors", capability.get("anchors")),
        ("what.obligations", what.get("obligations")),
        ("what.inputs", what.get("inputs")),
        ("what.outputs", what.get("outputs")),
        ("what.applicability.include", (what.get("applicability") or {}).get("include")),
        ("what.applicability.exclude", (what.get("applicability") or {}).get("exclude")),
        ("what.known_limits", what.get("known_limits")),
        ("what.failure_modes", what.get("failure_modes")),
        ("how.side_effects", how.get("side_effects")),
        ("how.permissions", how.get("permissions")),
    )
    for prefix, values in groups:
        if not isinstance(values, list):
            continue
        for index, item in enumerate(values):
            if isinstance(item, Mapping):
                yield f"{prefix}[{index}]", item


def validate_claim(claim: Mapping[str, Any], *, schema: Mapping[str, Any] | None = None) -> list[str]:
    """Return every violation; an empty list means the claim may be compared."""
    from jsonschema import Draft202012Validator

    schema = schema or _load_schema()
    violations: list[str] = []
    for error in sorted(Draft202012Validator(schema).iter_errors(claim), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        violations.append(f"schema:{location}:{error.validator}")
    if violations:
        # Structural problems make referential checks meaningless.
        return violations

    evidence = claim["why"]["evidence"]
    ids = [row["id"] for row in evidence]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    for value in duplicates:
        violations.append(f"evidence:duplicate_id:{value}")

    known_ids = set(ids)
    referenced: list[tuple[str, str]] = []
    for value in claim["capability"]["evidence"]:
        referenced.append(("capability.evidence", value))
    for path, item in _claim_items(claim):
        for value in item.get("evidence", []):
            referenced.append((f"{path}.evidence", value))
    for path, value in referenced:
        if value not in known_ids:
            violations.append(f"evidence:dangling:{path}:{value}")

    unknown_paths = []
    for row in claim["why"]["unknowns"]:
        field = row["field"]
        found, value = resolve_path(claim, field)
        if found:
            unknown_paths.append(field)
            continue
        # An absent sub-field is a legitimate unknown; a missing parent is a typo.
        parent = field.rsplit(".", 1)[0] if "." in field else ""
        parent_found = bool(parent) and resolve_path(claim, parent)[0]
        if not parent_found:
            violations.append(f"unknown:parent_not_found:{field}")
        unknown_paths.append(field)
    unknown_set = set(unknown_paths)

    for path, item in _claim_items(claim):
        if not item.get("evidence") and path not in unknown_set:
            violations.append(f"claim:unbacked:{path}")
        if item.get("evidence") and path in unknown_set:
            violations.append(f"unknown:contradicts_evidence:{path}")

    for row in evidence:
        field = row["field"]
        found, _ = resolve_path(claim, field)
        if not found:
            violations.append(f"evidence:field_not_in_claim:{field}")

    quick_start = claim["quick_start"]
    if quick_start["observable"] is False and not quick_start.get("limitation"):
        violations.append("quick_start:unobservable_without_limitation")

    violations.extend(_obligation_violations(claim, unknown_set))
    violations.extend(_contract_violations(claim, unknown_set))
    return violations


def _obligation_violations(claim: Mapping[str, Any], unknown_set: set[str]) -> list[str]:
    """Rules that only make sense once an obligation carries the v2 fields."""
    violations: list[str] = []
    obligations = (claim.get("what") or {}).get("obligations") or []
    obligation_ids = {item["id"] for item in obligations if isinstance(item, Mapping) and item.get("id")}
    unknown_ids = {row["field"] for row in (claim.get("why") or {}).get("unknowns") or [] if isinstance(row, Mapping)}

    for index, item in enumerate(obligations):
        if not isinstance(item, Mapping):
            continue
        path = f"what.obligations[{index}]"
        verifier = item.get("verifier") or {}
        required = item.get("required_authority") or DEFAULT_REQUIRED_AUTHORITY
        if verifier.get("kind") == "none" and required != "QUOTED":
            # Nothing can ever close it, so it must not demand more than a quote.
            violations.append(f"obligation:verifier_none_above_quoted:{path}")
        next_evidence = item.get("next_evidence")
        if isinstance(next_evidence, Mapping):
            subject = next_evidence.get("subject_id")
            if subject and subject not in obligation_ids and subject not in unknown_ids:
                violations.append(f"next_evidence:unknown_subject:{path}:{subject}")
            requires = next_evidence.get("requires_authority")
            if requires and authority_rank(requires) < 0:
                violations.append(f"next_evidence:authority_not_on_ladder:{path}")
    return violations


def _contract_violations(claim: Mapping[str, Any], unknown_set: set[str]) -> list[str]:
    """Unknown forms and unknown invocation modes must be declared, not implied."""
    violations: list[str] = []
    what = claim.get("what") or {}
    for group in ("inputs", "outputs"):
        for index, item in enumerate(what.get(group) or []):
            if not isinstance(item, Mapping):
                continue
            if item.get("form") != "unknown":
                continue
            path = f"what.{group}[{index}].form"
            if path not in unknown_set:
                violations.append(f"claim:form_unknown_not_declared:{path}")

    invocation = (claim.get("how") or {}).get("invocation") or {}
    if invocation.get("mode") == "unknown" and not ({"how.invocation", "how.invocation.mode"} & unknown_set):
        violations.append("claim:invocation_unknown_not_declared:how.invocation.mode")

    for path, value in _requirement_strings(claim):
        if looks_like_secret(value):
            violations.append(f"secret:literal_value:{path}")
    return violations


def _requirement_strings(claim: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    """Yield every string a requirement names, so a pasted value is caught."""
    requirements = (claim.get("how") or {}).get("requirements") or {}
    if not isinstance(requirements, Mapping):
        return
    for key in ("tools", "writes"):
        for index, value in enumerate(requirements.get(key) or []):
            yield f"how.requirements.{key}[{index}]", value
    for index, row in enumerate(requirements.get("secrets") or []):
        if isinstance(row, Mapping):
            for field in ("key", "purpose"):
                yield f"how.requirements.secrets[{index}].{field}", row.get(field)
    for index, row in enumerate(requirements.get("mcp_servers") or []):
        if isinstance(row, Mapping):
            yield f"how.requirements.mcp_servers[{index}].name", row.get("name")


def evidence_carryover_violations(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """Refuse a revision that rewrites an evidence record both revisions carry.

    A level is raised by adding a receipt, not by editing the strength of the
    record that is already on file.  Deleting a record is allowed: that is how a
    claim withdraws something it can no longer support.
    """
    before = {row["id"]: row for row in (previous.get("why") or {}).get("evidence") or [] if isinstance(row, Mapping)}
    after = {row["id"]: row for row in (current.get("why") or {}).get("evidence") or [] if isinstance(row, Mapping)}
    violations: list[str] = []
    for evidence_id in sorted(before):
        old, new = before[evidence_id], after.get(evidence_id)
        if new is None:
            continue
        for field in EVIDENCE_IMMUTABLE_FIELDS:
            if old.get(field) != new.get(field):
                violations.append(f"evidence:rewritten:{evidence_id}:{field}")
    return violations


def load_claim(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
