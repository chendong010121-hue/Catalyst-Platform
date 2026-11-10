"""One lifecycle vocabulary projected over the three existing state owners.

Read-only by construction: this module reads plain mappings that the existing
owners already persist (component lifecycle records, Wiki semantic state and
local maintenance reviews) and never writes, imports or executes anything.

The owners keep their own vocabularies.  This module answers one question the
product could not answer before: "what state is this capability in, and what
evidence says so?"  A value that cannot be mapped is reported as UNKNOWN with a
reason; it is never defaulted to ACTIVE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

# --- canonical lifecycle -------------------------------------------------

PROPOSED = "PROPOSED"
UNDERSTOOD = "UNDERSTOOD"
EVALUATED = "EVALUATED"
ADMITTED = "ADMITTED"
ACTIVE = "ACTIVE"
DEPRECATED = "DEPRECATED"
RETIRED = "RETIRED"
NEEDS_REVIEW = "NEEDS_REVIEW"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"

CANONICAL_STATES = (
    PROPOSED,
    UNDERSTOOD,
    EVALUATED,
    ADMITTED,
    ACTIVE,
    DEPRECATED,
    RETIRED,
    NEEDS_REVIEW,
    REJECTED,
)

TERMINAL_STATES = (RETIRED, REJECTED)

# Every allowed forward or corrective move.  Anything absent is refused.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    PROPOSED: (UNDERSTOOD, REJECTED),
    UNDERSTOOD: (EVALUATED, NEEDS_REVIEW, REJECTED),
    EVALUATED: (ADMITTED, NEEDS_REVIEW, REJECTED),
    ADMITTED: (ACTIVE, REJECTED),
    ACTIVE: (DEPRECATED, RETIRED),
    DEPRECATED: (ACTIVE, RETIRED),
    NEEDS_REVIEW: (EVALUATED, REJECTED),
    RETIRED: (),
    REJECTED: (),
}

# Evidence an operator must be able to point at before a move is credible.
TRANSITION_EVIDENCE: dict[tuple[str, str], tuple[str, ...]] = {
    (PROPOSED, UNDERSTOOD): ("source_evidence",),
    (UNDERSTOOD, EVALUATED): ("evaluation_record",),
    (EVALUATED, ADMITTED): ("admission_record",),
    (ADMITTED, ACTIVE): ("activation_record",),
    (ACTIVE, DEPRECATED): ("supersession_record",),
    (DEPRECATED, ACTIVE): ("activation_record",),
    (ACTIVE, RETIRED): ("retirement_decision",),
    (DEPRECATED, RETIRED): ("retirement_decision",),
}

# --- comparison vocabulary (contract for Harvest; not computed here) ------

SAME = "SAME"
SUPERSEDES = "SUPERSEDES"
SIMILAR = "SIMILAR"
COMPLEMENTARY = "COMPLEMENTARY"
DISTINCT = "DISTINCT"
COMPARISON_UNKNOWN = "UNKNOWN"

COMPARISON_RELATIONS = (SAME, SUPERSEDES, SIMILAR, COMPLEMENTARY, DISTINCT, COMPARISON_UNKNOWN)

REPLACE = "REPLACE"
EVALUATE_IN_DEVELOPMENT = "EVALUATE_IN_DEVELOPMENT"
KEEP_BOTH = "KEEP_BOTH"
NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
IGNORE_DUPLICATE = "IGNORE_DUPLICATE"

ACTION_BY_RELATION: dict[str, str] = {
    SAME: REPLACE,
    SUPERSEDES: REPLACE,
    SIMILAR: EVALUATE_IN_DEVELOPMENT,
    COMPLEMENTARY: KEEP_BOTH,
    DISTINCT: KEEP_BOTH,
    COMPARISON_UNKNOWN: NEEDS_HUMAN_REVIEW,
}


def compare_action(relation: str) -> str:
    """Map a comparison verdict to the review action a user may be offered."""
    if relation not in ACTION_BY_RELATION:
        raise ValueError("unknown comparison relation")
    return ACTION_BY_RELATION[relation]


def can_transition(before: str, after: str) -> bool:
    """Return whether the canonical vocabulary allows this move."""
    return after in TRANSITIONS.get(before, ())


def missing_evidence(before: str, after: str) -> tuple[str, ...]:
    """Evidence kinds a credible move between two states must reference."""
    if not can_transition(before, after):
        raise ValueError("transition is not allowed")
    return TRANSITION_EVIDENCE.get((before, after), ())


# --- projection ----------------------------------------------------------

@dataclass(frozen=True)
class Evidence:
    kind: str
    ref: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "ref": self.ref}


@dataclass(frozen=True)
class Projection:
    """One capability, one canonical state, and why."""

    subject: str
    state: str
    origin: str
    raw_state: str | None = None
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "state": self.state,
            "origin": self.origin,
            "raw_state": self.raw_state,
            "evidence": [item.to_dict() for item in self.evidence],
            "reason": self.reason,
        }


def _unknown(subject: str, origin: str, raw: Any, reason: str) -> Projection:
    return Projection(
        subject=subject,
        state=UNKNOWN,
        origin=origin,
        raw_state=None if raw is None else str(raw),
        reason=reason,
    )


_COMPONENT_TOKEN = {True: ACTIVE, False: ADMITTED}


def project_component_version(
    component_id: str,
    version: str,
    record: Mapping[str, Any],
    *,
    active: bool,
    load_error_type: str | None = None,
) -> Projection:
    """Project one admitted component version from the lifecycle records."""
    if not isinstance(record, Mapping):
        return _unknown(f"{component_id}@{version}", "component_lifecycle", record, "version record is not an object")
    if "admitted" in record and record["admitted"] is not True:
        return _unknown(f"{component_id}@{version}", "component_lifecycle", record.get("admitted"), "version is not admitted")

    evidence = [Evidence("component_version", f"{component_id}@{version}")]
    for key in ("package_sha256", "manifest_sha256", "source_sha256"):
        value = record.get(key)
        if isinstance(value, str) and value:
            evidence.append(Evidence(key, value))

    if load_error_type:
        return Projection(
            subject=f"{component_id}@{version}",
            state=ADMITTED,
            origin="component_lifecycle",
            raw_state="admitted",
            evidence=tuple(evidence),
            reason=f"module_load_failed:{load_error_type}",
        )
    state = ACTIVE if active is True else ADMITTED
    return Projection(
        subject=f"{component_id}@{version}",
        state=state,
        origin="component_lifecycle",
        raw_state="admitted+active" if active else "admitted",
        evidence=tuple(evidence),
    )


def project_components(rows: Sequence[Mapping[str, Any]]) -> tuple[Projection, ...]:
    """Project the output of ``LocalComponentLifecycle.list_components``."""
    out: list[Projection] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        component_id = row.get("component_id")
        if not isinstance(component_id, str):
            continue
        versions = row.get("versions")
        if not isinstance(versions, Sequence) or isinstance(versions, (str, bytes)):
            continue
        for item in versions:
            if not isinstance(item, Mapping):
                continue
            version = item.get("version")
            if not isinstance(version, str):
                continue
            flagged = item.get("active")
            if isinstance(flagged, bool):
                active = flagged
            else:
                pointer = row.get("active_version")
                active = isinstance(pointer, str) and pointer == version
            out.append(
                project_component_version(
                    component_id,
                    version,
                    {**item, "admitted": item.get("admitted")},
                    active=active,
                    load_error_type=item.get("load_error_type") if isinstance(item.get("load_error_type"), str) else None,
                )
            )
    return tuple(out)


_CANDIDATE_STATES = {
    "PROPOSED": PROPOSED,
    "EVALUATED": EVALUATED,
    "NEEDS_REVIEW": NEEDS_REVIEW,
    "ACCEPTED": ADMITTED,
    "REJECTED": REJECTED,
    "DEFERRED": NEEDS_REVIEW,
}


def project_semantic_candidate(candidate_id: str, candidate: Mapping[str, Any]) -> Projection:
    """Project one Wiki semantic candidate (proposal, never activation)."""
    if not isinstance(candidate, Mapping):
        return _unknown(candidate_id, "semantic_wiki", candidate, "candidate record is not an object")
    status = candidate.get("status")
    state = _CANDIDATE_STATES.get(status) if isinstance(status, str) else None
    if state is None:
        return _unknown(candidate_id, "semantic_wiki", status, "candidate status is outside the known vocabulary")
    evidence = [Evidence("candidate", candidate_id)]
    for key in ("source_id", "source_revision"):
        value = candidate.get(key)
        if isinstance(value, str) and value:
            evidence.append(Evidence(key, value))
    decision = candidate.get("latest_decision_id")
    if isinstance(decision, str) and decision:
        evidence.append(Evidence("decision", decision))
    return Projection(
        subject=candidate_id,
        state=state,
        origin="semantic_wiki",
        raw_state=status,
        evidence=tuple(evidence),
        reason=None if state != NEEDS_REVIEW else f"candidate_status:{status}",
    )


def project_semantic_version(version_id: str, state: Mapping[str, Any]) -> Projection:
    """Project one accepted semantic version, including the active pointer."""
    accepted = state.get("accepted_versions") if isinstance(state, Mapping) else None
    if not isinstance(accepted, Mapping):
        return _unknown(version_id, "semantic_wiki", None, "semantic state has no accepted versions")
    version = accepted.get(version_id)
    if not isinstance(version, Mapping):
        return _unknown(version_id, "semantic_wiki", None, "version is not an accepted semantic version")
    active_id = state.get("active_version_id")
    evidence = [Evidence("accepted_version", version_id)]
    for key in ("decision_id", "source_id", "source_revision"):
        value = version.get(key)
        if isinstance(value, str) and value:
            evidence.append(Evidence(key, value))
    is_active = active_id == version_id
    return Projection(
        subject=version_id,
        state=ACTIVE if is_active else ADMITTED,
        origin="semantic_wiki",
        raw_state="accepted+active" if is_active else "accepted",
        evidence=tuple(evidence),
        reason=None if is_active else "accepted_but_not_active",
    )


_MAINTENANCE_STATES = {
    "VALIDATED": EVALUATED,
    "PENDING_RESTART": ADMITTED,
    "APPLYING": ADMITTED,
    "ROLLBACK_PENDING": ACTIVE,
    "APPLIED": ACTIVE,
    "ROLLED_BACK": DEPRECATED,
    "VALIDATION_FAILED": REJECTED,
    "REJECTED": REJECTED,
    "FAILED": REJECTED,
    "FAILED_ROLLED_BACK": REJECTED,
    "RECOVERY_REQUIRED": NEEDS_REVIEW,
}


def project_maintenance(row: Mapping[str, Any]) -> Projection:
    """Project one local maintenance review onto the same vocabulary."""
    review_id = row.get("review_id") if isinstance(row, Mapping) else None
    subject = review_id if isinstance(review_id, str) else "maintenance:unknown"
    if not isinstance(row, Mapping):
        return _unknown(subject, "maintenance", row, "maintenance record is not an object")
    status = row.get("status")
    state = _MAINTENANCE_STATES.get(status) if isinstance(status, str) else None
    if state is None:
        return _unknown(subject, "maintenance", status, "maintenance status is outside the known vocabulary")
    evidence = [Evidence("maintenance_review", subject)]
    confirmed = row.get("confirmed_by")
    if isinstance(confirmed, str) and confirmed:
        evidence.append(Evidence("confirmed_by", confirmed))
    return Projection(
        subject=subject,
        state=state,
        origin="maintenance",
        raw_state=status,
        evidence=tuple(evidence),
        reason=f"maintenance_status:{status}" if state in (NEEDS_REVIEW,) else None,
    )


def project_snapshot(
    *,
    components: Iterable[Mapping[str, Any]] = (),
    semantic_state: Mapping[str, Any] | None = None,
    maintenance: Iterable[Mapping[str, Any]] = (),
) -> tuple[Projection, ...]:
    """Project every readable capability record through one vocabulary."""
    out: list[Projection] = list(project_components(tuple(components)))
    if isinstance(semantic_state, Mapping):
        candidates = semantic_state.get("candidates")
        if isinstance(candidates, Mapping):
            for candidate_id, candidate in sorted(candidates.items()):
                if isinstance(candidate_id, str):
                    out.append(project_semantic_candidate(candidate_id, candidate))
        accepted = semantic_state.get("accepted_versions")
        if isinstance(accepted, Mapping):
            for version_id in sorted(accepted):
                if isinstance(version_id, str):
                    out.append(project_semantic_version(version_id, semantic_state))
    for row in maintenance:
        out.append(project_maintenance(row))
    return tuple(out)


def state_counts(projections: Iterable[Projection]) -> dict[str, int]:
    """Count projections per canonical state; UNKNOWN is counted, not hidden."""
    counts = {state: 0 for state in CANONICAL_STATES}
    counts[UNKNOWN] = 0
    for item in projections:
        counts[item.state] = counts.get(item.state, 0) + 1
    return counts
