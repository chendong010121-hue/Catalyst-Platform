"""The concept set of one scope: which types it uses, versioned, and readable back.

The upper kinds of :mod:`catalyst_platform.ontology_types` are the same in every scope; the
concepts are not. This module holds the scope's own concept ledger, in the same Wiki document
as its claims and its semantic state, and it is where OpenBKN's two habits land without a
database behind them:

* **A version per decision.** Every define, deprecate or adoption publishes a new version with
  its parent, its actor, its reason and its time, so "why does this card have Ward" is answered
  by the scope rather than by a commit message.
* **Retirement, not deletion.** A deprecated concept keeps its spellings in ``retired``, with
  the concept that replaced it. A card read under the old set is still readable, and its
  ``病区`` still resolves - to whatever the scope now calls that thing.

An empty ledger is not an error: it means the scope never declared anything, and reads the
starter pack of the standard. Declaring the first concept starts from that same pack, so a
scope never has to restate eleven types to add a twelfth.
"""

from __future__ import annotations

import copy
import time

from dataclasses import replace
from typing import Any, Mapping, Sequence

from .ontology_types import (
    Concept,
    ConceptError,
    ConceptSet,
    META_KINDS,
    STARTER_PACK,
    declared_counts,
)


SCHEMA_VERSION = 1

# A scope's own types: enough for a hospital or a bank, few enough that the prompt stays one
# screen. The pack of the standard is eleven, so this leaves room for fifty-three decisions.
MAX_CONCEPTS = 64


def empty_concept_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "active_version_id": None,
        "versions": {},
        "history": [],
        "retired": {},
    }


def _now() -> int:
    return int(time.time())


def concept_state_is_valid(state: object) -> bool:
    """True only for a ledger this module could have written or could read."""
    if not isinstance(state, Mapping) or state.get("schema_version") != SCHEMA_VERSION:
        return False
    versions = state.get("versions")
    history = state.get("history")
    retired = state.get("retired", {})
    if not isinstance(versions, Mapping) or not isinstance(history, list) or not isinstance(retired, Mapping):
        return False
    if any(not isinstance(key, str) or not isinstance(row, Mapping) for key, row in versions.items()):
        return False
    for key, row in versions.items():
        if row.get("version_id") != key:
            return False
        parent = row.get("parent_version_id")
        if parent is not None and parent not in versions:
            return False
        if not isinstance(row.get("concepts"), Sequence) or isinstance(row.get("concepts"), (str, bytes)):
            return False
        try:
            ConceptSet.from_dict({"concepts": list(row["concepts"])})
        except ConceptError:
            return False
    active = state.get("active_version_id")
    if active is not None and active not in versions:
        return False
    for row in history:
        if not isinstance(row, Mapping) or row.get("event") not in {"adopt", "define", "deprecate"}:
            return False
        if row.get("version_id") not in versions:
            return False
    for key, row in retired.items():
        if not isinstance(key, str) or not isinstance(row, Mapping):
            return False
        try:
            Concept.from_dict(row.get("concept"))
        except ConceptError:
            return False
        replacement = row.get("replacement")
        if replacement is not None and not isinstance(replacement, str):
            return False
    return True


def _active_version(state: Mapping[str, Any]) -> Mapping[str, Any] | None:
    active = state.get("active_version_id")
    if active is None:
        return None
    return state["versions"][active]


def _row_concepts(version: Mapping[str, Any]) -> tuple[Concept, ...] | None:
    rows = version.get("concepts")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return None
    origin = str(version.get("origin") or "declared")
    return tuple(Concept.from_dict(row, origin=row.get("origin") or origin)
                 for row in rows if isinstance(row, Mapping))


def concept_set_of(state: Mapping[str, Any]) -> ConceptSet:
    """The set this scope extracts with: its own version, or the starter pack of the standard."""
    version = _active_version(state)
    if version is None:
        return STARTER_PACK
    concepts = _row_concepts(version)
    if concepts is None:
        raise ConceptError("concept_state_invalid", "the active concept version holds no readable concepts")
    return ConceptSet(concepts, str(version["version_id"]), str(version.get("origin") or "declared"))


def _retired_spellings(state: Mapping[str, Any]) -> dict[str, Concept | None]:
    """What a retired spelling now means: the concept that replaced it, when there is one."""
    current = concept_set_of(state)
    index: dict[str, Concept | None] = {}
    for retired in (state.get("retired") or {}).values():
        concept_row = retired.get("concept") if isinstance(retired, Mapping) else None
        if not isinstance(concept_row, Mapping):
            continue
        replacement = retired.get("replacement")
        target = current.by_id(replacement) if isinstance(replacement, str) else None
        for spelling in (concept_row.get("concept_id"), concept_row.get("name"), *(concept_row.get("aliases") or ())):
            if isinstance(spelling, str) and spelling.strip():
                index.setdefault(spelling.strip().casefold(), target)
    return index


def resolve_concept_in(state: Mapping[str, Any], value: object) -> Concept | None:
    """The concept this scope means by a spelling, including one it has already retired.

    A card read under an old concept set still names ``Ward``; a scope that deprecated Ward in
    favour of ``CareUnit`` resolves that name to CareUnit instead of losing the type.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    return concept_set_of(state).resolve(value) or _retired_spellings(state).get(value.strip().casefold())


def _publish(state: dict[str, Any], concepts: Sequence[Concept], *, origin: str, actor: str,
             reason: str, event: str, concept_id: str | None = None) -> dict[str, Any]:
    version_id = f"concepts-{len(state['versions']) + 1}"
    parent = state.get("active_version_id")
    state["versions"][version_id] = {
        "version_id": version_id,
        "parent_version_id": parent,
        "origin": origin,
        "actor": actor,
        "reason": reason,
        "defined_at": _now(),
        "concepts": [concept.to_dict() for concept in concepts],
    }
    state["active_version_id"] = version_id
    state["history"].append({
        "event": event,
        "version_id": version_id,
        "concept_id": concept_id,
        "actor": actor,
        "reason": reason,
        "at": state["versions"][version_id]["defined_at"],
        # A first decision started from the pack, and the version says so: the scope declared
        # one type, it did not invent eleven.
        "started_from": "starter_pack" if parent is None else None,
    })
    return {"version_id": version_id, "parent_version_id": parent,
            "concept_count": len(concepts), "active_version_id": version_id}


def _checked_reason(reason: object) -> str:
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 400:
        raise ConceptError("concept_reason_required", "every concept decision records one line saying why")
    return reason.strip()


def _checked_actor(actor: object) -> str:
    if not isinstance(actor, str) or not actor.strip():
        raise ConceptError("concept_actor_required", "every concept decision records who made it")
    return actor.strip()


def define_concept(state: dict[str, Any], concept: Concept, *, actor: str, reason: str) -> dict[str, Any]:
    """Add one concept to the scope's set and publish the version that holds it."""
    reason, actor = _checked_reason(reason), _checked_actor(actor)
    # The declared row is validated the way a stored one is read back, so a concept that
    # reaches the ledger is one this module can also load.
    declared = replace(Concept.from_dict(concept.to_dict() if isinstance(concept, Concept) else concept),
                       origin=actor)
    current = concept_set_of(state)
    if current.by_id(concept.concept_id) is not None:
        raise ConceptError("concept_already_defined",
                           f"{concept.concept_id} is already in this scope; deprecate it before defining its replacement")
    if len(current.concepts) >= MAX_CONCEPTS:
        raise ConceptError("concept_set_full", f"a scope holds at most {MAX_CONCEPTS} concepts")
    published = _publish(state, (*current.concepts, declared), origin="declared", actor=actor,
                         reason=reason, event="define", concept_id=declared.concept_id)
    return {**published, "concept": declared.to_dict()}


def deprecate_concept(state: dict[str, Any], concept_id: str, *, actor: str, reason: str,
                      replacement: str | None = None) -> dict[str, Any]:
    """Retire one concept, keeping its spellings and saying what now stands for it."""
    reason, actor = _checked_reason(reason), _checked_actor(actor)
    current = concept_set_of(state)
    retired = current.by_id(concept_id)
    if retired is None:
        raise ConceptError("concept_not_found", f"{concept_id} is not in this scope's concept set")
    remaining = tuple(concept for concept in current.concepts if concept.concept_id != concept_id)
    if not remaining:
        # A scope with no concept cannot read anything, so the last one stays.
        raise ConceptError("concept_set_empty", "a scope keeps at least one concept")
    if replacement is not None and not any(concept.concept_id == replacement for concept in remaining):
        raise ConceptError("concept_replacement_not_found",
                           f"{replacement} is not a concept of this scope, so nothing replaces {concept_id}")
    state.setdefault("retired", {})[concept_id] = {
        "concept": retired.to_dict(), "replacement": replacement, "at": _now(),
    }
    published = _publish(state, remaining, origin="declared", actor=actor, reason=reason,
                         event="deprecate", concept_id=concept_id)
    return {**published, "concept_id": concept_id, "replacement": replacement}


def adopt_concept_pack(state: dict[str, Any], *, actor: str, reason: str,
                       pack: ConceptSet | None = None) -> dict[str, Any]:
    """Write the starting pack into the scope, so its concepts are its own data from now on."""
    reason, actor = _checked_reason(reason), _checked_actor(actor)
    chosen = pack or STARTER_PACK
    # ``replace`` keeps every declaration the concept already carries; rebuilding the dataclass
    # field by field would silently drop whatever a later release adds.
    concepts = tuple(replace(concept, origin=str(actor)) for concept in chosen.concepts)
    return _publish(state, concepts, origin=chosen.origin, actor=actor, reason=reason, event="adopt")


def _unresolved_relation_targets(concepts: ConceptSet) -> list[dict[str, str]]:
    """Declared relations whose target is neither a concept of this set nor an upper kind."""
    held = set(concepts.ids())
    return [
        {"concept_id": concept.concept_id, "predicate": relation.predicate, "target": relation.target}
        for concept in concepts.concepts
        for relation in concept.relations
        if relation.target not in held and relation.target not in META_KINDS
    ]


def concept_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    """The ledger as a reader sees it: the active set, its versions and what is retired."""
    current = concept_set_of(state)
    return {
        "schema_version": SCHEMA_VERSION,
        "scope_concept_set": current.to_dict(),
        "declarations": declared_counts(current.concepts),
        "unresolved_relation_targets": _unresolved_relation_targets(current),
        "declared": _active_version(state) is not None,
        "versions": [
            {"version_id": row["version_id"], "parent_version_id": row.get("parent_version_id"),
             "origin": row.get("origin"), "actor": row.get("actor"), "reason": row.get("reason"),
             "defined_at": row.get("defined_at"), "concept_count": len(row.get("concepts") or ())}
            for row in state.get("versions", {}).values()
        ],
        "history": copy.deepcopy(state.get("history", [])),
        "retired": [
            {"concept_id": key, "name": (row.get("concept") or {}).get("name"),
             "replacement": row.get("replacement"), "at": row.get("at")}
            for key, row in (state.get("retired") or {}).items()
        ],
        "meta_kinds": {key: {"name": meta.name, "criteria": meta.criteria, "grounding": meta.grounding}
                       for key, meta in META_KINDS.items()},
    }
