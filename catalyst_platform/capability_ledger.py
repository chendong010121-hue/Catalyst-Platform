"""Obligation ownership and coverage, derived rather than written.

A claim says what must hold.  A binding says who is accountable for each of those
obligations and which evidence speaks to it.  A ledger merges the bindings of one
group, workflow or agent and reports what is closed and what is still missing.

Nothing here decides a level by hand: `level`, `coverage`, `status` and `depth`
are pure functions of the rows.  A ledger that stores them is only accepted when
the stored value equals the recomputed one, so a green ledger cannot be written —
it can only be produced.

The ladder is fixed and may be climbed one rung at a time:

    QUOTED < STRUCTURAL < EXECUTED < MEASURED

A raising revision must add an evidence record or a receipt.  A lowering revision
must name a receipt that justifies it.  Raising an existing record's strength is
refused outright: see `capability_claim.evidence_carryover_violations`.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from .capability_claim import (
    AUTHORITY_ORDER,
    DEFAULT_REQUIRED_AUTHORITY,
    authority_of,
    authority_rank,
    canonical,
    claim_digest,
)

LEVELS = ("MISSING", "DECLARED", "BOUND", "VERIFIED")
DEPTHS = ("L0", "L1", "L2", "L3", "L4")
STATUSES = ("CLOSED", "PARTIAL", "CONTRADICTED")
ROLES = ("SUPPLIER", "CONSUMER", "STANDALONE")
DERIVED_FIELDS = ("level", "coverage", "status", "depth")

_HEX64 = re.compile(r"^[a-f0-9]{64}$")


class LedgerError(ValueError):
    """A binding or ledger cannot be built from the inputs it was given."""


def _row_authorities(row: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for authority in row.get("evidence_authority") or []:
        if authority:
            values.append(authority)
    for proof in row.get("proofs") or []:
        if isinstance(proof, Mapping) and proof.get("authority"):
            values.append(proof["authority"])
    return values


def derive_level(row: Mapping[str, Any]) -> str:
    """The one place a level is decided. Missing owner or missing evidence wins."""
    owner = row.get("owner") or {}
    if owner.get("kind") in (None, "none") or not owner.get("ref"):
        return "MISSING"
    ranks = [authority_rank(value) for value in _row_authorities(row)]
    best = max(ranks, default=-1)
    if best < 0:
        return "MISSING"
    required = authority_rank(row.get("required_authority") or DEFAULT_REQUIRED_AUTHORITY)
    if best == authority_rank("QUOTED"):
        return "DECLARED"
    if best == authority_rank("STRUCTURAL"):
        return "BOUND"
    # EXECUTED or MEASURED. Enough to verify only when it meets this obligation's bar.
    return "VERIFIED" if best >= max(required, authority_rank("EXECUTED")) else "BOUND"


def derive_coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in ("declared", "bound", "verified", "missing", "unowned")}
    for row in rows:
        level = derive_level(row)
        counts[level.lower()] += 1
        if (row.get("owner") or {}).get("kind") in (None, "none", "unowned"):
            counts["unowned"] += 1
    return counts


def derive_status(rows: Sequence[Mapping[str, Any]], contradictions: Iterable[str] = ()) -> str:
    if list(contradictions):
        return "CONTRADICTED"
    if any(derive_level(row) == "MISSING" for row in rows):
        return "PARTIAL"
    return "CLOSED"


def derive_depth(claim: Mapping[str, Any], receipts: Iterable[Mapping[str, Any]] = ()) -> str:
    """How explicit this part is: identity, obligations, graph, executed, measured.

    L2 needs the task sub-graph, L3 a run receipt (or an EXECUTED record), L4 a
    measurement on a shared benchmark.  A claim with obligations stops at L1.
    """
    strengths = {
        row.get("strength")
        for row in (claim.get("why") or {}).get("evidence") or []
        if isinstance(row, Mapping)
    }
    if "MEASURED" in strengths:
        return "L4"
    executed = "EXECUTED" in strengths or any(
        isinstance(receipt, Mapping) and receipt.get("status") in {"DONE", "FALLBACK_DONE"}
        for receipt in receipts
    )
    if executed:
        return "L3"
    if claim.get("graph"):
        return "L2"
    if (claim.get("what") or {}).get("obligations"):
        return "L1"
    return "L0"


def _owner(value: Any, default: str) -> dict[str, str]:
    if value is None:
        return {"kind": "self", "ref": default} if default else {"kind": "none", "ref": ""}
    if isinstance(value, str):
        return {"kind": "member", "ref": value}
    kind = str(value.get("kind") or "none")
    if kind not in {"self", "member", "external", "none"}:
        raise LedgerError(f"unsupported owner kind: {kind}")
    return {"kind": kind, "ref": str(value.get("ref") or "")}


def build_binding(
    claim: Mapping[str, Any],
    *,
    role: str = "STANDALONE",
    owners: Mapping[str, Any] | None = None,
    owner_digest: str | None = None,
) -> dict[str, Any]:
    """Read one claim and write who owns each obligation.

    No level is produced: `derive_level` decides it from the evidence recorded
    here, so a binding cannot claim to be verified.
    """
    if role not in ROLES:
        raise LedgerError(f"unsupported binding role: {role}")
    capability = claim.get("capability") or {}
    identity = str(capability.get("id") or "")
    strengths = {
        row["id"]: row.get("strength")
        for row in (claim.get("why") or {}).get("evidence") or []
        if isinstance(row, Mapping) and row.get("id")
    }
    obligations = (claim.get("what") or {}).get("obligations") or []
    owners = owners or {}
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(obligations):
        if not isinstance(item, Mapping):
            continue
        obligation_id = str(item.get("id") or f"ob-{index + 1}")
        evidence = [value for value in item.get("evidence") or [] if isinstance(value, str)]
        rows.append(
            {
                "id": obligation_id,
                "statement": item.get("statement"),
                "owner": _owner(owners.get(obligation_id), identity),
                "evidence": evidence,
                "evidence_authority": sorted(
                    {authority_of(strengths.get(value)) for value in evidence if authority_of(strengths.get(value))},
                    key=authority_rank,
                ),
                "proofs": [],
                "required_authority": item.get("required_authority") or DEFAULT_REQUIRED_AUTHORITY,
                "next_evidence": item.get("next_evidence"),
                "missing": None,
            }
        )
    return {
        "binding_version": 1,
        "subject": {
            "id": identity,
            "version": str(capability.get("version") or ""),
            "claim_digest": claim_digest(claim),
            "owner_digest": owner_digest or "",
        },
        "role": role,
        "obligations": rows,
    }


def validate_binding(binding: Mapping[str, Any], claim: Mapping[str, Any] | None = None) -> list[str]:
    violations: list[str] = []
    subject = binding.get("subject") or {}
    if not subject.get("owner_digest") or not _HEX64.match(str(subject.get("owner_digest"))):
        violations.append("binding:owner_digest_missing")
    if binding.get("role") not in ROLES:
        violations.append(f"binding:role:{binding.get('role')}")
    if claim is not None:
        if subject.get("claim_digest") != claim_digest(claim):
            violations.append("binding:claim_digest_mismatch")
        statements = {
            str(item.get("id") or f"ob-{index + 1}"): item.get("statement")
            for index, item in enumerate((claim.get("what") or {}).get("obligations") or [])
            if isinstance(item, Mapping)
        }
        for row in binding.get("obligations") or []:
            if not isinstance(row, Mapping):
                continue
            obligation_id = str(row.get("id"))
            if row.get("statement") != statements.get(obligation_id):
                violations.append(f"binding:statement_drift:{obligation_id}")
    for index, row in enumerate(binding.get("obligations") or []):
        if not isinstance(row, Mapping):
            continue
        for field in DERIVED_FIELDS:
            if field in row:
                violations.append(f"binding:derived_field_stored:obligations[{index}].{field}")
    for field in DERIVED_FIELDS:
        if field in binding:
            violations.append(f"binding:derived_field_stored:{field}")
    return violations


def build_ledger(
    subject: Mapping[str, Any],
    members: Iterable[tuple[Mapping[str, Any], Mapping[str, Any]]],
    *,
    contradictions: Iterable[str] = (),
) -> dict[str, Any]:
    """Merge bindings into one ledger and attach the derived block."""
    rows: list[dict[str, Any]] = []
    member_rows: list[dict[str, Any]] = []
    for claim, binding in members:
        subject_row = binding.get("subject") or {}
        member_rows.append(
            {
                "id": subject_row.get("id"),
                "version": subject_row.get("version"),
                "claim_digest": subject_row.get("claim_digest") or claim_digest(claim),
                "owner_digest": subject_row.get("owner_digest") or "",
                "binding_digest": hashlib.sha256(canonical(binding)).hexdigest(),
            }
        )
        for row in binding.get("obligations") or []:
            if isinstance(row, Mapping):
                rows.append({**row, "member": subject_row.get("id")})
    ledger = {
        "ledger_version": 1,
        "subject": dict(subject),
        "members": member_rows,
        "obligations": rows,
        "contradictions": list(contradictions),
    }
    ledger["derived"] = _derived_block(ledger)
    return ledger


def _derived_block(ledger: Mapping[str, Any]) -> dict[str, Any]:
    rows = [row for row in ledger.get("obligations") or [] if isinstance(row, Mapping)]
    return {
        "obligations": [
            {"id": row.get("id"), "member": row.get("member"), "level": derive_level(row)} for row in rows
        ],
        "coverage": derive_coverage(rows),
        "status": derive_status(rows, ledger.get("contradictions") or ()),
    }


def validate_ledger(
    ledger: Mapping[str, Any],
    claims: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[str]:
    """Every stored derived value must equal the recomputed one."""
    violations: list[str] = []
    derived = ledger.get("derived")
    if not isinstance(derived, Mapping):
        return ["ledger:derived_missing"]

    recomputed = _derived_block(ledger)
    stored_rows = derived.get("obligations") or []
    for index, row in enumerate(ledger.get("obligations") or []):
        if not isinstance(row, Mapping):
            continue
        expected = recomputed["obligations"][index]
        actual = stored_rows[index] if index < len(stored_rows) else {}
        if not isinstance(actual, Mapping) or actual.get("level") != expected["level"]:
            violations.append(f"ledger:derived_mismatch:obligations[{index}].level")

    for key, value in recomputed["coverage"].items():
        if (derived.get("coverage") or {}).get(key) != value:
            violations.append(f"ledger:derived_mismatch:coverage.{key}")
    if derived.get("status") != recomputed["status"]:
        violations.append("ledger:derived_mismatch:status")

    if claims is not None:
        violations.extend(_drift_violations(ledger, claims))
    return violations


def _drift_violations(
    ledger: Mapping[str, Any], claims: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Re-read the member claims and refuse a row that overstates its evidence."""
    violations: list[str] = []
    for member in ledger.get("members") or []:
        claim = claims.get(str(member.get("id")))
        if claim is None:
            violations.append(f"ledger:member_claim_missing:{member.get('id')}")
            continue
        if member.get("claim_digest") != claim_digest(claim):
            violations.append(f"ledger:member_claim_drift:{member.get('id')}")
    known = {
        str(row.get("id"))
        for claim in claims.values()
        for row in (claim.get("what") or {}).get("obligations") or []
        if isinstance(row, Mapping)
    }
    for index, row in enumerate(ledger.get("obligations") or []):
        if not isinstance(row, Mapping):
            continue
        next_evidence = row.get("next_evidence")
        if isinstance(next_evidence, Mapping):
            subject = next_evidence.get("subject_id")
            if subject and subject not in known:
                violations.append(f"ledger:next_evidence_unknown_subject:{row.get('id')}:{subject}")
    return violations


def revise_ledger(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[str]:
    """A revision may only move a level with the record that justifies it."""
    violations: list[str] = []
    before = {
        str(row.get("id")): row for row in previous.get("obligations") or [] if isinstance(row, Mapping)
    }
    demotions = {
        str(entry.get("id"))
        for entry in current.get("demotions") or []
        if isinstance(entry, Mapping) and entry.get("receipt")
    }
    for row in current.get("obligations") or []:
        if not isinstance(row, Mapping):
            continue
        obligation_id = str(row.get("id"))
        old = before.get(obligation_id)
        if old is None:
            continue
        was, now = derive_level(old), derive_level(row)
        if LEVELS.index(now) > LEVELS.index(was):
            added = (set(row.get("evidence") or []) - set(old.get("evidence") or [])) or (
                len(row.get("proofs") or []) > len(old.get("proofs") or [])
            )
            if not added:
                violations.append(f"level:raised_without_evidence:{obligation_id}")
        elif LEVELS.index(now) < LEVELS.index(was) and obligation_id not in demotions:
            violations.append(f"level:lowered_without_receipt:{obligation_id}")
    return violations


def ledger_digest(ledger: Mapping[str, Any]) -> str:
    """Digest over the facts only; the derived block is not part of the identity."""
    body = {key: value for key, value in ledger.items() if key != "derived"}
    return hashlib.sha256(canonical(body)).hexdigest()


def load_ledger(path: str | Any) -> dict[str, Any]:
    from pathlib import Path

    return json.loads(Path(path).read_text(encoding="utf-8"))
