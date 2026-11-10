"""Loss-preserving Understand handoff and candidate graph over ProjectWiki.

The adapter keeps UnderstandingResult producer identity and evidence references
in the existing ProjectWiki semantic candidate ledger. It does not evaluate,
accept, activate, or infer enterprise identity.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

try:
    from pypdf.errors import PyPdfError as _PdfParseError
except ImportError:
    class _PdfParseError(Exception):
        pass

from .semantic_wiki import (MAX_CANDIDATE_ITEMS, MAX_NATIVE_CANDIDATE_ITEMS, SemanticTransitionError,
                             SemanticWiki, _SAFE_CODE)
from .understand_only import _locator_unit, stored_evidence_class
from .understand_semantic import states_its_relation
from .object_view import from_item
from .wiki import ProjectWiki, WikiError


_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_BUSINESS_OBJECT_KINDS = ("entity", "duty", "event", "condition")
_KIND_NOUN = {"duty": "职责", "event": "事件", "condition": "条件"}
# Objects first: a budget never lets evidence or free text push a saved duty off the graph.
_NODE_PRIORITY = ("entity", "duty", "event", "condition", "relation", "alias",
                  "exception", "claim", "negative_claim", "unknown")


def _business_roles(row: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """The keys a hand-off row saved, in the role it saved them in; nothing looked up."""
    kind = row.get("kind")
    if kind == "duty":
        sides = (("holder", row.get("subject")),)
    elif kind == "event":
        sides = tuple(("from", key) for key in (row.get("from") or []))
        sides += tuple(("to", key) for key in (row.get("to") or []))
    elif kind == "condition":
        sides = tuple(("applies_to", key) for key in (row.get("applies_to") or []))
    elif kind == "relation":
        sides = (("subject", row.get("subject")), ("object", row.get("object")))
    else:
        sides = ()
    return tuple((name, key) for name, key in sides if isinstance(key, str) and key)



_LINE_LOCATOR = re.compile(r"^line:(\d+)(?:-(\d+))?$")
_SAFE_ORIGIN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SAFE_REFERENCE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,256}$")
_MAX_RESULT_BYTES = 8 * 1024 * 1024
_MAX_SOURCES = 100
_MAX_EVIDENCE = 2000
_MAX_ITEMS = 1000
# One projection line holds the item and every passage it cites, and the store keeps one
# passage per line: the anchor is that line, so its size is the size the store bounds. A
# name spelled on six pages of a deck, or an unknown that searched twelve passages,
# legitimately exceeds the two thousand characters this used to be - the live card had
# 33 such rows and every one was a real answer whose evidence had been gathered, not
# thinned. The ceiling stays as a stop for a runaway line, not as a cap on evidence.
_MAX_PROJECTION_ANCHOR = 8000


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_origin(value: Any) -> str:
    return value if isinstance(value, str) and _SAFE_ORIGIN.fullmatch(value) else "unverified"


def _relative_path(value: Any) -> PurePosixPath | None:
    if not isinstance(value, str) or not value or len(value) > 1024:
        return None
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    if ":" in path.parts[0] or "\x00" in normalized:
        return None
    return path


def _identity_text(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _entry_identity_key(entry: Mapping) -> Any:
    """The name a defect is reported under, whatever shape the entry arrived in.

    A relation carries no key of its own: its identity is the three endpoints it joins,
    which is how the store names it too, so two relations are never one entry.
    """
    for name in ("key", "canonical_key", "item_key"):
        value = entry.get(name)
        if isinstance(value, str) and value.strip():
            return _identity_text(value)
    parts = [entry.get(name) for name in ("subject", "predicate", "object")]
    if all(isinstance(part, str) and part.strip() for part in parts):
        return "|".join(_identity_text(part) for part in parts)
    return None


def _relation_end_key(value, entity_keys):
    """The store key one relation end names, looked up by the producer's own spelling."""
    raw = str(value or "").lstrip("@")
    return entity_keys.get(raw) or _store_key("entity", raw)


def _store_key(kind, raw):
    """The store's identifier for a producer key: lower-case, safe and stable.

    A producer names things the way its own prompt asked: `entity:shuili_jituan`, a whole
    sentence as a key, or a Chinese phrase. The store keeps identifiers of its own shape,
    so the name is translated once, here - and a relation that addressed the producer's
    spelling is translated the same way, rather than dropped for being spelled differently.
    The human wording travels beside the key as the row's meaning.
    """
    text = str(raw or "").strip().lstrip("@")
    lowered = text.casefold()
    for prefix in (kind + ":", kind + ".", kind + "/", kind + "-"):
        if lowered.startswith(prefix):
            text = text[len(prefix):]
            break
    key = re.sub(r"_+", "_", re.sub(r"[^a-z0-9_.-]+", "_", text.casefold())).strip("._-")
    if not key:
        return "k_" + _sha(f"{kind}\0{text}".encode("utf-8"))[:12]
    if not key[0].isalpha():
        key = "k_" + key
    if len(key) > 63:
        # The suffix is derived from the producer's own spelling, so the same long name
        # always shortens to the same key, and two different long names stay apart.
        key = key[:40].rstrip("._-") + "_" + _sha(f"{kind}\0{text}".encode("utf-8"))[:12]
    return key


def _entry_wording(entry: Mapping) -> str:
    """The wording a row stands for, in either shape the entry arrives in.

    A submitted entity carries a display name, a stored one keeps the same text as its
    meaning, and a relation is worded by the three endpoints it joins - which is how
    the store words it - so no shape reads as a meaning that is missing.
    """
    for name in ("display_name", "meaning"):
        value = entry.get(name)
        if isinstance(value, str) and value.strip():
            return value
    parts = [entry.get(name) for name in ("subject", "predicate", "object")]
    if all(isinstance(part, str) and part.strip() for part in parts):
        return " ".join(parts)
    return ""


def entry_errors(entries) -> list:
    """Every deterministic defect in a set of stored entries, as (item_key, field, code, message).

    No model and no network: the same checks a publish runs, so a set can be compared
    with the set already stored before anything is written. A row read back from the
    ledger keeps its passage by digest rather than by text, and such an anchor counts
    as evidence: the store checked the text when it wrote the row, and re-hashing a
    quote it no longer keeps would invent evidence instead of checking it.
    """
    errors = []
    seen: set = set()
    for entry in entries or ():
        if not isinstance(entry, Mapping):
            errors.append({"item_key": None, "field": None, "code": "entry_not_an_object",
                           "message": "a stored entry must be an object"})
            continue
        key = _entry_identity_key(entry)
        kind = entry.get("kind")
        if kind not in {"entity", "claim", "relation", "condition", "exception", "unknown",
                        "duty", "event"}:
            errors.append({"item_key": key, "field": "kind", "code": "unsupported_kind",
                           "message": f"{kind!r} is not a storeable kind"})
            continue
        if (kind, key) in seen:
            errors.append({"item_key": key, "field": "key", "code": "duplicate_key",
                           "message": "the same kind and key appear twice in one publish"})
        seen.add((kind, key))
        if not _entry_wording(entry).strip():
            wording_of = ("an entity or relation needs the wording it stands for"
                          if kind in {"entity", "relation"} else "a claim or unknown needs the wording it stands for")
            errors.append({"item_key": key, "field": "meaning", "code": "empty_meaning",
                           "message": wording_of})
        evidence = entry.get("evidence")
        quote = str(evidence.get("quote") or "") if isinstance(evidence, Mapping) else ""
        span = evidence.get("span_sha256") if isinstance(evidence, Mapping) else None
        if kind != "unknown":
            ledged = not quote and isinstance(span, str) and _SHA256.fullmatch(span) is not None
            if not ledged and not quote.strip():
                errors.append({"item_key": key, "field": "evidence.quote", "code": "evidence_missing",
                               "message": "a non-unknown entry must carry the passage it came from"})
            elif quote and _sha(quote.encode("utf-8")) != span:
                errors.append({"item_key": key, "field": "evidence.span_sha256",
                               "code": "span_sha256_mismatch",
                               "message": "the stored quote does not hash to the span it claims"})
    return errors


def introduced_errors(previous, current) -> dict:
    """The defects this publish would add, with the ones already stored carried separately.

    An older set that is already imperfect must not block today's publish: only what
    this publish introduces does. What carries over is reported, never hidden, so the
    difference is visible in the wiki report instead of being inherited in silence.
    """
    def identity(row):
        return (row.get("item_key"), row.get("field"), row.get("code"))

    before = {identity(row): row for row in entry_errors(previous)}
    after = entry_errors(current)
    introduced = [row for row in after if identity(row) not in before]
    carried = [row for row in after if identity(row) in before]
    return {"introduced": introduced, "carried_over": carried,
            "blocked": bool(introduced),
            "counts": {"introduced": len(introduced), "carried_over": len(carried)}}


def ensure_publishable(previous, current) -> dict:
    """Return the report, or refuse the publish with the rows that would degrade the wiki."""
    report = introduced_errors(previous, current)
    if report["blocked"]:
        codes = sorted({row["code"] for row in report["introduced"]})
        error = UnderstandWikiError(
            "introduced_errors",
            f"this publish would introduce {len(report['introduced'])} defect(s): {', '.join(codes)}")
        error.report = report
        raise error
    return report


def stored_publish_entries(state) -> list:
    """One comparable row per candidate key the ledger of this scope already holds.

    A stored row keeps its passage by line and digest, so the row is rebuilt with that
    digest as its anchor. Keys are taken once across candidates: two publishes that
    share a key are not a duplicate of each other, and folding them together would
    hide the duplicate a later publish would introduce.
    """
    rows: dict = {}
    for candidate in (state.get("candidates") or {}).values():
        if not isinstance(candidate, Mapping):
            continue
        for entry in candidate.get("entries") or ():
            if not isinstance(entry, Mapping):
                continue
            row = {"kind": entry.get("kind"), "key": entry.get("key"),
                   "meaning": entry.get("meaning"),
                   "evidence": {"line_start": entry.get("line_start"),
                                "line_end": entry.get("line_end"),
                                "span_sha256": entry.get("span_sha256")}}
            if entry.get("kind") == "entity":
                row["canonical_key"] = entry.get("canonical_key")
                row["display_name"] = entry.get("meaning")
            elif entry.get("kind") == "relation":
                row.update(subject=entry.get("subject"), predicate=entry.get("predicate"),
                           object=entry.get("object"))
            rows.setdefault((row["kind"], _entry_identity_key(row)), row)
    return list(rows.values())


ADMISSION_ACTIONS = ("adopt", "unadopt", "rename", "describe", "identity",
                     "same_identity", "restore")
# The kinds a card carries a handful of, and the ones a page spread would starve: a
# relation or a condition sits late in its page, so taking only the page's opening
# items drops exactly the connective material a person wants most.
_SCARCE_KINDS = {"relation", "condition", "exception"}
"""The things a person may do to a candidate between review and harvest.

`same_identity` answers the identity queue: the item and the key in `after` are one
thing, and `after` is the key that stands for both.
"""

_HARVESTABLE_KINDS = {"entity", "claim", "relation", "condition", "exception", "unknown",
                      "duty", "event"}


def _plan_row(item) -> dict:
    return {"item_key": item.key, "item_id": item.item_id, "kind": item.kind,
            "meaning": item.meaning, "evidence_class": item.evidence_class,
            "evidence_refs": list(item.evidence_refs),
            "uncertainty": item.uncertainty,
            # What the run decided this row is, so a plan a person reads can tell a
            # statement from a question about the reading.
            "degradation": getattr(item, "degradation", None),
            # Which step wrote it, so the store keeps the row's own provenance and a
            # reader can say whether it is a claim about the material at all.
            "source_origin": dict(getattr(item, "source_origin", None) or {})}


def projection_anchor(item: Mapping, evidence_refs) -> str:
    """The one canonical line a projection stores for an item and the evidence it cites."""
    return _canonical({"item": item, "evidence": list(evidence_refs)}).decode("utf-8")


def _anchor_sizes(result) -> dict:
    """Projection anchor size per item, for a result that can render itself.

    A caller that cannot render its result (a test double, an older producer) gets no
    size check rather than a guess: the publish still refuses an oversized line.
    """
    render = getattr(result, "to_dict", None)
    if not callable(render):
        return {}
    raw = render()
    refs = {ref["evidence_id"]: ref for ref in raw.get("evidence_refs") or ()
            if isinstance(ref, Mapping) and isinstance(ref.get("evidence_id"), str)}
    sizes = {}
    for item in (raw.get("semantic_candidate") or {}).get("items") or ():
        if not isinstance(item, Mapping):
            continue
        cited = [refs[ref] for ref in item.get("evidence_refs") or () if ref in refs]
        sizes[item.get("item_id")] = len(projection_anchor(item, cited))
    return sizes



def _evidence_units(result, items) -> dict:
    """The source unit each item's first passage sits in, for a result that renders itself."""
    render = getattr(result, "to_dict", None)
    if not callable(render):
        return {}
    raw = render()
    refs = {ref["evidence_id"]: ref for ref in raw.get("evidence_refs") or ()
            if isinstance(ref, Mapping) and isinstance(ref.get("evidence_id"), str)}
    units = {}
    for item in items:
        for ref_id in item.evidence_refs:
            ref = refs.get(ref_id)
            if isinstance(ref, Mapping):
                units[item.item_id] = (str(ref.get("source_id") or ""), _locator_unit(str(ref.get("locator") or "")))
                break
    return units


def _spread_over_units(items, units) -> list:
    """Order items by giving every source unit one turn before any unit takes a second.

    Reading order is one chain, and a long deck spends the whole harvest budget on its
    first pages: two hundred items taken in document order covered eight of fourteen
    slides. Each unit keeps its own order - the order a person reads that page in -
    while the round-robin lets every unit be heard before the next round begins.
    """
    buckets: dict = {}
    order: list = []
    for item in items:
        key = units.get(item.item_id) or ("", "")
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(item)
    widest = max((len(bucket) for bucket in buckets.values()), default=0)
    spread = []
    for turn in range(widest):
        for key in order:
            if turn < len(buckets[key]):
                spread.append(buckets[key][turn])
    return spread


def _with_relation_endpoints(chosen, ordered, max_items) -> list:
    """Keep the two ends of every relation the plan adopts, inside the budget.

    A relation is a statement about two things; publish drops one whose endpoint was
    not selected, which is how a card that adopted ten edges delivered four. The ends
    come in from behind the cutoff, and the items that are neither an edge nor the end
    of an edge give way - the tail of the spread, which every unit has already had a
    turn at by then.

    An edge costs its two ends as well as itself, and one deck can hold more edges than
    the port takes: 144 relations over 99 entities is 243 items whatever the spread
    gives up, which the publish gate refuses whole as an invalid selection. So when the
    adopted edges and their ends alone outgrow the budget, the edges from the tail of
    the order wait with them and are named over_port_budget, each in the plan a person
    reads. The budget is what the port takes; nothing is handed on that it cannot carry.
    """
    entity_by_key = {item.key: item for item in ordered if item.kind == "entity"}
    ends_of = {item.item_id: {entity_by_key[key].item_id
                             for key in (item.subject, item.object) if key in entity_by_key}
               for item in ordered if item.kind == "relation"}
    edges = [item.item_id for item in chosen if item.kind == "relation"]
    others = [item.item_id for item in chosen if item.kind != "relation"]

    def ends(edges):
        return set().union(*(ends_of.get(edge, set()) for edge in edges)) if edges else set()

    while True:
        needed = ends(edges)
        spare = [item_id for item_id in others if item_id not in needed]
        if len(needed) + len(edges) + len(spare) <= max_items:
            break
        if spare:
            others.remove(spare[-1])
            continue
        if edges:
            edges.pop()
            continue
        break
    needed = ends(edges)
    keep = needed | set(edges) | {item_id for item_id in others if item_id not in needed}
    return [item for item in ordered if item.item_id in keep]


def _stated_relations(result) -> dict:
    """Per relation item, whether a cited passage states it in the relation's own words.

    A plan that counts 隶属 edges drawn from 分为 and 整合 sentences as confirmed is counting
    the two changes as standing structure. The answer comes from the same passage the store
    will hold, so the plan and the published card cannot disagree. A result that
    cannot render itself (a test double, an older producer) answers None: the plan
    then keeps the reading it can take from the relation source alone rather than
    refusing every edge.
    """
    render = getattr(result, "to_dict", None)
    if not callable(render):
        return None
    raw = render()
    refs = {ref["evidence_id"]: ref for ref in raw.get("evidence_refs") or ()
            if isinstance(ref, Mapping) and isinstance(ref.get("evidence_id"), str)}
    items = [row for row in (raw.get("semantic_candidate") or {}).get("items") or ()
             if isinstance(row, Mapping)]
    names = {row.get("key"): row.get("meaning") or row.get("key")
             for row in items if row.get("kind") == "entity"}
    stated = {}
    for row in items:
        if row.get("kind") != "relation":
            continue
        passage = "\n".join(str(refs[ref].get("quote") or "")
                            for ref in row.get("evidence_refs") or () if ref in refs)
        if not passage.strip() or not str(row.get("predicate") or "").strip():
            # No passage to read, or no predicate to look for: a row from a producer that
            # renders neither, or a test double. Nothing is judged here, and the caller
            # keeps the source's own word rather than refusing an edge it cannot read.
            continue
        ends = tuple(str(names.get(str(row.get(side)).lstrip("@")) or "") for side in ("subject", "object"))
        stated[row.get("item_id")] = (row.get("relation_source") != "LAYOUT"
                                      and states_its_relation(str(row.get("predicate") or ""),
                                                              passage, ends))
    return stated


def admission_plan(result, *, max_items: int = MAX_CANDIDATE_ITEMS) -> dict:
    """Sort a candidate into default adopt, pending and excluded, without a model call.

    `default_adopt` is what the port would hand to Wiki as it stands: an item whose
    class is read off the source or explicitly inferred, which cites evidence, whose
    key is not shared with a version that says something else, and whose kind Wiki can
    store. `pending` is everything a person should look at, each row naming why -
    including a key the store cannot name, which a person can rename before harvest.
    `excluded` is what cannot be harvested under today's contract at all.

    When more items qualify than the port takes, the scarce kinds - a relation, a
    condition, an exception - are taken first, and the rest is spent across source
    units in turn rather than down the document, so a long deck is not represented
    only by its opening pages and a page's late items are not always the ones lost.

    A relation is adopted together with the two things it joins, because publish drops
    an edge whose endpoint was not selected; a relation with an end that cannot be
    harvested at all is named with that reason instead of being adopted and lost.

    A relation nobody stated is not adopted. An org chart is a picture: on one deck 56 of
    59 edges were read off where two names sit, or off a sentence that says the two
    changed rather than that one sits under the other. Second-tier admission takes only
    what the material says, so those edges wait for a person, named with that reason,
    and the card holds the three edges the page states in words.
    """
    attribution = result.producer_attribution if isinstance(result.producer_attribution, Mapping) else {}
    conflicts = {str(row.get("item_key")) for row in attribution.get("duplicate_items_conflicting_meaning") or ()
                 if isinstance(row, Mapping)}
    items = list(result.semantic_candidate.items) if result.semantic_candidate else []
    anchors = _anchor_sizes(result)
    stated = _stated_relations(result)
    seen: dict = {}
    rows: dict = {}
    adoptable, pending, excluded, unstated = [], [], [], []

    def is_confirmed(item) -> bool:
        verdict = None if stated is None else stated.get(item.item_id)
        if verdict is None:
            # No verdict was formed - a producer that renders no quotes, a test double -
            # so the plan keeps the reading the row itself carries.
            return getattr(item, "relation_source", "TEXT") != "LAYOUT"
        return bool(verdict)
    for item in items:
        row = rows[item.item_id] = _plan_row(item)
        degradation = getattr(item, "degradation", None)
        if isinstance(degradation, Mapping) and degradation.get("class") == "run_diagnostic":
            # A diagnostic row is evidence about the reading. It cannot be saved as a
            # candidate by any selection, so the plan names it instead of adopting it.
            excluded.append({**row, "reason": "run_diagnostic_not_a_candidate"})
            continue
        if item.kind not in _HARVESTABLE_KINDS:
            excluded.append({**row, "reason": "harvest_unresolved_kind"})
            continue
        if item.evidence_class == "conflict":
            excluded.append({**row, "reason": "conflict_requires_review"})
            continue
        identity = (item.kind, item.key)
        seen[identity] = seen.get(identity, 0) + 1
        if item.kind != "relation" and not _SAFE_CODE.fullmatch(item.key):
            pending.append({**row, "reason": "key_not_storable"})
        elif seen[identity] > 1:
            pending.append({**row, "reason": "duplicate_key_in_candidate"})
        elif item.key in conflicts:
            pending.append({**row, "reason": "duplicate_key_conflict"})
        elif item.evidence_class == "unresolved" and item.kind != "unknown":
            pending.append({**row, "reason": "harvest_unresolved_item"})
        elif anchors.get(item.item_id, 0) > _MAX_PROJECTION_ANCHOR:
            pending.append({**row, "reason": "projection_anchor_too_large"})
        elif item.kind != "unknown" and not item.evidence_refs:
            pending.append({**row, "reason": "no_evidence"})
        elif item.kind == "unknown" and not (item.scope_refs and item.observed_absence):
            # An absence needs both halves: the places it searched and the phrasing it did
            # not find. A row missing either is a question about the reading, and the store
            # would refuse it, so the plan waits instead of handing it on.
            pending.append({**row, "reason": "absence_without_scope"})
        elif item.kind == "relation" and not is_confirmed(item):
            # Not a defect in the row: a diagram places two names near each other and a
            # sentence may describe a change. Neither is the material saying this, so the
            # edge waits for a person instead of being admitted as a fact. The endpoint
            # reasons are checked first, so a row that could not come along at all keeps
            # the reason that matters more.
            unstated.append(item)
        else:
            adoptable.append(item)
    # A relation can only be harvested if both of its ends can be: publish drops an
    # edge whose endpoint was not selected, so a plan that adopts the edge and leaves
    # its ends behind spends three slots to lose a row. The ends that cannot come along
    # are named here instead, and the relation goes to a person with that reason.
    end_keys = {item.key for item in adoptable if item.kind == "entity"}

    def named(item) -> set:
        """The entities this row addresses and cannot be stored without."""
        if item.kind == "relation":
            return {item.subject, item.object}
        if item.kind == "duty":
            return {item.subject}
        if item.kind == "event":
            return set(item.event_from) | set(item.event_to)
        return set()

    paired, orphaned = [], []
    for item in adoptable:
        if item.kind in {"relation", "duty", "event"} and not named(item) <= end_keys:
            orphaned.append(item)
        else:
            paired.append(item)
    adoptable = paired
    for item in orphaned:
        pending.append({**rows[item.item_id], "reason": {
            "relation": "relation_endpoint_not_harvestable",
            "duty": "duty_holder_not_harvestable",
            "event": "event_participant_not_harvestable",
        }[item.kind]})
    for item in unstated:
        pending.append({**rows[item.item_id], "reason": "relation_not_confirmed"})
    scarce = [item for item in adoptable if item.kind in _SCARCE_KINDS]
    bulk = [item for item in adoptable if item.kind not in _SCARCE_KINDS]
    ordered = scarce + _spread_over_units(bulk, _evidence_units(result, items))
    chosen = _with_relation_endpoints(ordered[:max_items], ordered, max_items)
    kept_ids = {item.item_id for item in chosen}
    for item in ordered:
        if item.item_id not in kept_ids:
            pending.append({**rows[item.item_id], "reason": "over_port_budget"})
    default_adopt = [rows[item.item_id] for item in chosen]
    integrity = attribution.get("integrity") or {}
    gaps = {
        "refused_units": [row.get("unit") for row in attribution.get("refused_units") or ()
                          if isinstance(row, Mapping)],
        # A unit whose answer was cut short is read only up to the cut, so the
        # candidate is incomplete in a way a reader has to be told about.
        "truncated_units": [row.get("unit") for row in attribution.get("truncated_units") or ()
                            if isinstance(row, Mapping)],
        "dropped_rows": dict(attribution.get("dropped_invalid_items") or {}),
        "dropped_relations": len(attribution.get("dropped_relations") or ()),
    }
    # Names a reader would call one thing wait for a decision instead of being merged
    # inside the plan: the same words belong to a current org chart and to a proposed
    # one, and only the Owner can say which of the two a key stands for.
    identity = [{"keys": list(row.get("keys") or ()), "names": list(row.get("names") or ()),
                 "basis": row.get("basis"), "score": row.get("score")}
                for row in list(attribution.get("identity_candidates") or ())
                if isinstance(row, Mapping)]
    return {"default_adopt": default_adopt, "pending": pending, "excluded": excluded,
            "counts": {"default_adopt": len(default_adopt), "pending": len(pending),
                       "excluded": len(excluded)},
            "identity_candidates": identity,
            # The identity answers this card already applied: the plan and the review
            # read the folded graph, and a pair settled here is not offered again.
            "identity_merges": [dict(row) for row in list(attribution.get("identity_merges") or ())
                                if isinstance(row, Mapping)],
            # How much of what is adopted comes from a page drawn as it stands and how
            # much from one drawn as proposed, so the two charts stay tellable apart.
            "scope_states": {name: sum(1 for item in chosen
                                       if item.kind in {"entity", "relation"}
                                       and getattr(item, "scope_state", None) == name)
                             for name in ("current", "proposed")},
            # How much of what this plan adopts rests on a sentence and how much on
            # the layout of a page: the second is stored unconfirmed.
            "relation_verification": {
                "confirmed": sum(1 for item in items
                                 if item.kind == "relation" and is_confirmed(item)),
                "unconfirmed": sum(1 for item in items
                                   if item.kind == "relation" and not is_confirmed(item))},
            "coverage_gap": any(gaps.values()), "gaps": gaps, "integrity": integrity}


def _decision(action: str, item_key: str, *, before=None, after=None, by: str, time: str) -> dict:
    if action not in ADMISSION_ACTIONS:
        raise UnderstandWikiError("unknown_admission_action", f"{action!r} is not one of {ADMISSION_ACTIONS}")
    if not isinstance(item_key, str) or not item_key.strip():
        raise UnderstandWikiError("invalid_admission_decision", "a decision must name the item it acts on")
    if not isinstance(by, str) or not by.strip() or not isinstance(time, str) or not time.strip():
        raise UnderstandWikiError("invalid_admission_decision", "a decision must record who made it and when")
    return {"item_key": item_key, "action": action, "before": before, "after": after,
            "by": by, "time": time}


def apply_admission_decisions(plan: dict, decisions, *, existing=(), discard_decisions: bool = False) -> dict:
    """Apply Owner actions to a plan and return the selection harvest may use.

    A decision that is already recorded is kept. A run that would lose earlier
    decisions refuses instead of silently rewriting them: dropping a person's work
    takes an explicit `discard_decisions=True`, the way a draft with decisions cannot
    be re-drafted without saying so.
    """
    kept = [row for row in existing or () if isinstance(row, Mapping)]
    incoming = [row for row in decisions or () if isinstance(row, Mapping)]
    lost = [row for row in kept if row not in incoming]
    if lost and not discard_decisions:
        raise UnderstandWikiError(
            "discard_decisions",
            f"{len(lost)} recorded decision(s) would be lost; pass discard_decisions to discard them")
    adopt = {row["item_key"]: dict(row) for row in plan.get("default_adopt") or ()}
    pending = {row["item_key"]: dict(row) for row in plan.get("pending") or ()}
    excluded = {row["item_key"]: dict(row) for row in plan.get("excluded") or ()}
    log = []
    identities: list[dict] = []
    for row in incoming:
        key = str(row.get("item_key") or "")
        action = str(row.get("action") or "")
        if action not in ADMISSION_ACTIONS:
            raise UnderstandWikiError("unknown_admission_action",
                                      f"{action!r} is not one of {ADMISSION_ACTIONS}")
        if action == "adopt":
            if key in excluded:
                raise UnderstandWikiError("excluded_item_needs_restore",
                                          "an excluded item enters by restore, not by adopt")
            if key in pending:
                adopt[key] = {**pending.pop(key), "adopted_by": row.get("by")}
            elif key not in adopt:
                raise UnderstandWikiError("unknown_admission_item", f"no candidate item is keyed {key!r}")
            log.append(_decision(action, key, before="pending", after="adopt",
                                 by=row.get("by"), time=row.get("time")))
        elif action == "unadopt":
            if key not in adopt:
                raise UnderstandWikiError("unknown_admission_item", f"no adopted item is keyed {key!r}")
            pending[key] = {**adopt.pop(key), "reason": "owner_unadopted"}
            log.append(_decision(action, key, before="adopt", after="pending",
                                 by=row.get("by"), time=row.get("time")))
        elif action in {"rename", "describe", "identity", "same_identity"}:
            target = adopt.get(key) or pending.get(key) or excluded.get(key)
            if target is None:
                raise UnderstandWikiError("unknown_admission_item", f"no candidate item is keyed {key!r}")
            field = {"rename": "item_key", "describe": "meaning", "identity": "identity",
                     "same_identity": "same_identity"}[action]
            before, after = target.get(field), row.get("after")
            if not isinstance(after, str) or not after.strip():
                raise UnderstandWikiError("invalid_admission_decision", f"{action} needs the value it sets")
            if action == "same_identity":
                # The answer says this item and `after` are one thing, and names the key
                # that stands for both. It is kept in the plan for the next reading to
                # fold into the graph: recorded here alone, the branch would still hang
                # under two keys.
                kept = adopt.get(after) or pending.get(after) or excluded.get(after)
                if kept is None or after == key:
                    raise UnderstandWikiError("unknown_admission_item",
                                              f"no other candidate item is keyed {after!r}")
                if target.get("kind") != "entity" or kept.get("kind") != "entity":
                    raise UnderstandWikiError("identity_needs_two_entities",
                                              "only two entities can be one identity")
                identities.append({"keys": [key, after], "keep": after,
                                  "by": row.get("by"), "time": row.get("time")})
            target[field] = after
            if action == "rename" and key in adopt:
                adopt[after] = adopt.pop(key)
            log.append(_decision(action, key, before=before, after=after,
                                 by=row.get("by"), time=row.get("time")))
        else:  # restore
            if key not in excluded:
                raise UnderstandWikiError("unknown_admission_item", f"no excluded item is keyed {key!r}")
            pending[key] = {**excluded.pop(key), "reason": "owner_restored", "restored_by": row.get("by")}
            log.append(_decision(action, key, before="excluded", after="pending",
                                 by=row.get("by"), time=row.get("time")))
    return {"selection": sorted(adopt), "default_adopt": list(adopt.values()),
            "pending": list(pending.values()), "excluded": list(excluded.values()),
            "decisions": log,
            # The answers to the identity queue, as the next reading takes them.
            "identity_decisions": identities,
            "counts": {"adopted": len(adopt), "pending": len(pending),
                                          "excluded": len(excluded)}}


class UnderstandWikiError(SemanticTransitionError):
    """A bounded, machine-readable Understand-to-Wiki contract error."""


class UnderstandWikiAdapter:
    """Submit a bounded Understand result as a candidate-only handoff to existing Wiki owners."""

    def __init__(self, wiki: ProjectWiki, semantic: SemanticWiki, source_root: Path | str):
        self.wiki = wiki
        self.semantic = semantic
        self.source_root = Path(source_root).expanduser().resolve()

    def harvest_entries(self, items, refs, selected, *, lines, strict, verified=None):
        """Turn selected items into typed entries, and name what could not become one.

        A passage becomes one line of the derived package and the entry anchors to that
        line, so every producer keeps one anchor shape. What cannot be anchored is named
        in the report instead of deciding the whole publish: the product path degrades one
        row at a time, while the TEST-SCOPE harvest keeps its all-or-nothing behaviour.
        """
        entries = []
        report = {"dropped": [], "dropped_relations": [], "unconfirmed_relations": []}
        selected_entities = {items[item_id]["key"] for item_id in selected
                             if items[item_id]["kind"] == "entity"}
        names_by_key = {row.get("key"): row.get("meaning") or row.get("key")
                        for row in items.values() if row.get("kind") == "entity"}
        # The producer's spelling and the store's identifier, so a relation that
        # addressed `entity:alpha` still points at the entity stored as `alpha`.
        entity_keys = {str(row.get("key")): _store_key("entity", row.get("key"))
                       for row in items.values() if row.get("kind") == "entity"}

        def defer(item_key, rule, code, message):
            if strict and code is not None:
                raise UnderstandWikiError(code, message)
            report["dropped"].append({"item_key": item_key, "rule": rule})

        for key in selected:
            item = items[key]
            if item["kind"] not in {"entity", "claim", "relation", "condition", "exception",
                                    "unknown", "duty", "event"}:
                defer(key, "unsupported_kind", "harvest_unresolved_kind",
                      "conflicts and unsupported kinds require separate review")
                continue
            if item["evidence_class"] == "conflict":
                # A conflict is the material disagreeing with itself: evidence of a decision
                # waiting for a person. It is named, never silently dropped, and it never
                # decides the rows that are not in conflict.
                defer(key, "conflict_requires_decision", "harvest_unresolved_kind",
                      "conflicts and unsupported kinds require separate review")
                continue
            if item["kind"] == "duty" and str(item.get("subject") or "").lstrip("@") not in selected_entities:
                # A holder the store cannot address is not a field: the duty is saved only
                # with the entity that holds it, and this row is named instead of guessed.
                defer(key, "duty_holder_not_selected", "harvest_duty_holder_not_selected",
                      "a duty must be harvested with the entity that holds it")
                continue
            if item["kind"] == "event" and not {
                str(end).lstrip("@") for end in (*(item.get("from") or ()),
                                                 *(item.get("to") or ()))
            } <= selected_entities:
                defer(key, "event_participant_not_selected", "harvest_event_participant_not_selected",
                      "an event must be harvested with the units on both of its sides")
                continue
            if item["kind"] == "relation" and not {
                str(item["subject"]).lstrip("@"), str(item["object"]).lstrip("@"),
            } <= selected_entities:
                # A relation whose two ends are not both in this harvest would point at
                # nothing: the relation is dropped and counted, never the whole publish.
                # The usual cause is an end whose key the store cannot name, which the
                # admission plan already holds back for a person to rename.
                report["dropped_relations"].append({"item_key": item["key"],
                                                    "rule": "relation_endpoint_not_selected"})
                continue
            cited = list(item["evidence_refs"] or ())
            if any(ref not in refs for ref in cited):
                defer(key, "evidence_reference_unknown", "harvest_unresolved_item",
                      "evidence does not match re-read original")
                continue
            if item["kind"] in {"duty", "event"}:
                # Two gates, not one. A complete duty or event may be saved while it is
                # still pending - 246 names one unit on both sides of a change and that is
                # exactly what a reviewer has to see. What it cannot do is arrive with no
                # passage at all: the row is stored against its own evidence or not at all,
                # and the consumption gate is where pending is refused as a fact.
                if not cited:
                    defer(key, "evidence_unresolved", "harvest_unresolved_item",
                          "a duty or an event is stored against the passage it cites")
                    continue
            elif item["kind"] != "unknown" and (not cited or item["evidence_class"] == "unresolved"):
                defer(key, "evidence_unresolved", "harvest_unresolved_item",
                      "unsupported or pending meanings cannot be harvested as facts")
                continue
            if item["kind"] == "unknown" and not (item.get("observed_absence") and item.get("scope_refs")):
                # The same rule the store enforces, checked before anything is anchored: an
                # absence that cannot say what it looked for and where is not a candidate.
                defer(key, "absence_without_scope", "harvest_absence_without_scope",
                      "an absence must say what it looked for and where it searched")
                continue
            if verified is not None and cited and not any(ref in verified for ref in cited):
                # The handoff already re-read the original and compared every span; a row
                # whose every citation failed that check has no passage to stand on.
                defer(key, "evidence_not_verified", None, "")
                continue
            quote = projection_anchor(item, [refs[r] for r in cited])
            if len(quote) > _MAX_PROJECTION_ANCHOR:
                defer(key, "projection_anchor_too_large", "projection_anchor_too_large",
                      "select a smaller evidence-bound candidate")
                continue
            lines.append(quote)
            entry = {"kind": item["kind"], "evidence_class": stored_evidence_class(item["kind"]),
                     "evidence": {"line_start": len(lines), "line_end": len(lines),
                                  "quote": quote, "span_sha256": _sha(quote.encode("utf-8"))}}
            # Saved with the row it belongs to: which step wrote it, in which call, for
            # which row. Only a claim about the material is stored as one; a row with
            # no verifiable step is stored without a tag and reads back as unverified.
            origin = item.get("source_origin")
            if isinstance(origin, Mapping) and origin.get("category") == "source_claim":
                entry["source_origin"] = dict(origin)
            if item["kind"] == "entity":
                entry.update(canonical_key=_store_key(item["kind"], item["key"]),
                             display_name=item["meaning"])
                if item.get("business_type"):
                    entry["business_type"] = item["business_type"]
            elif item["kind"] == "relation":
                entry.update(subject="@" + _relation_end_key(item["subject"], entity_keys),
                             predicate=item["predicate"],
                             object="@" + _relation_end_key(item["object"], entity_keys))
                # A sentence names both ends only when it says this relation in its own
                # words: 分为 and 整合 describe a change, and read as a standing edge they
                # invert it. A diagram only places two names near each other. Both stay
                # unconfirmed, and each downgrade is named in the publish report.
                ends = tuple(str(names_by_key.get(str(item.get(side)).lstrip("@")) or "")
                             for side in ("subject", "object"))
                # The passage the claim rests on is the cited evidence itself, not the
                # projection line: that line carries this row's own wording, and a row
                # that says 隶属 about a 分为 sentence would then confirm itself.
                passage = "\n".join(str(refs[ref].get("quote") or "")
                                    for ref in cited if ref in refs)
                stated = (item.get("relation_source") != "LAYOUT"
                          and states_its_relation(str(item.get("predicate") or ""), passage, ends))
                entry["verification"] = "confirmed" if stated else "unconfirmed"
                if not stated:
                    report["unconfirmed_relations"].append({
                        "item_key": item["key"],
                        "rule": ("relation_reads_a_change"
                                 if item.get("relation_source") != "LAYOUT"
                                 else "relation_read_off_a_layout")})
            elif item["kind"] in {"duty", "event"}:
                # The rows this contract is about: a duty keeps the entity that holds it
                # as a field, and an event keeps the two sides of one change. Neither is
                # pressed into a sentence, which is where the holder used to be lost.
                entry.update(key=_store_key(item["kind"], item["key"]),
                             meaning=item["meaning"])
                if item.get("predicate"):
                    entry["predicate"] = item["predicate"]
                if item["kind"] == "duty":
                    entry["holder"] = "@" + _relation_end_key(item.get("subject"), entity_keys)
                else:
                    entry["from"] = ["@" + _relation_end_key(end, entity_keys)
                                     for end in (item.get("from") or ())]
                    entry["to"] = ["@" + _relation_end_key(end, entity_keys)
                                   for end in (item.get("to") or ())]
                    # The producer row names the shape of its own two sides; the store
                    # keeps it so a reader can say whether a change was read as two
                    # lists or as one pair split out of a sentence.
                    if item.get("ends_source") in {"lists", "pair"}:
                        entry["ends_source"] = item["ends_source"]
                    entry["keeps_legal_entity"] = item.get("keeps_legal_entity")
                    if item.get("keeps_legal_entity_scope") is not None:
                        entry["keeps_legal_entity_scope"] = item["keeps_legal_entity_scope"]
                # A pending row is stored as `unresolved`; everything else the store
                # re-reads from the passage this entry cites.
                entry["evidence_class"] = (
                    "unresolved" if item["evidence_class"] == "unresolved"
                    else stored_evidence_class(item["kind"]))
            else:
                entry.update(key=_store_key(item["kind"], item["key"]),
                             meaning=item["meaning"])
                if item["kind"] == "unknown":
                    # The absence and the places it was searched in travel together: a card
                    # that keeps only 未在本页说明 hands a reader a statement about the whole
                    # material that was only ever checked against one page.
                    if item.get("observed_absence"):
                        entry["absence"] = item["observed_absence"]
                    searched = sorted({str(refs[ref].get("locator") or "")
                                       for ref in item.get("scope_refs") or () if ref in refs})
                    if searched:
                        entry["searched"] = searched
                    # How much of its source this row was read over, as the layer wrote it
                    # on the item. A consumer that has to open the raw quote to learn the
                    # limit has no limit: the eligibility travels with the typed row.
                    unread = [str(scope) for scope in (item.get("unread_scopes") or ())
                              if str(scope)]
                    if unread:
                        entry["unread_scopes"] = list(dict.fromkeys(unread))
            # The page's own word for which chart the row came from, carried to the
            # store so a proposed organisation is not read as the current one.
            if item.get("scope_state") in {"current", "proposed"}:
                entry["scope_state"] = item["scope_state"]
            if item["kind"] in {"condition", "exception"}:
                # A restriction travels with what it restricts; one that cannot say what
                # it restricts is stored unattached rather than pinned to the nearest row.
                entry["applies_to"] = ["@" + _relation_end_key(target, entity_keys)
                                       for target in (item.get("applies_to") or ())]
            entries.append(entry)
        return entries, report

    def publish_handoff(self, frozen, bindings, mappings, candidate_id):
        """Publish the typed reading a verified handoff already stands on.

        The handoff re-read every original and compared every span, so a row whose
        citations all verified has a passage to stand on. The rows that do not are counted
        here instead of deciding the publish, and the package this writes carries the
        passages only - never the document a second time.
        """
        items = {row["item_id"]: row for row in frozen["semantic_candidate"]["items"]}
        refs = {ref["evidence_id"]: ref for ref in frozen["evidence_refs"]}
        verified = {row["evidence_id"] for row in mappings if row["mapping_status"] == "MAPPED"}
        staged = [row for row in bindings
                  if row["status"] == "STAGED" and isinstance(row.get("wiki_source_id"), str)]
        if not staged or not items:
            return {"status": "skipped", "reason": "no staged source or no item to place"}
        selected = list(items)
        lines = ["# Derived passages of a verified handoff - inferred, not original facts",
                 _canonical({"handoff_candidate_id": candidate_id,
                             "originals": [{"path": row["relative_path"],
                                            "sha256": row["source_sha256"]} for row in staged],
                             "selected_item_ids": selected}).decode("utf-8")]
        entries, report = self.harvest_entries(items, refs, selected, lines=lines,
                                               strict=False, verified=verified)
        kept = []
        seen = set()
        dropped = list(report["dropped"])
        for entry in entries:
            item_key = _entry_identity_key(entry)
            identity = (entry.get("kind"), item_key)
            if identity in seen:
                # Two rows standing for the same thing in one publish: the first keeps its
                # own passage, the second is named so the duplicate stays countable.
                dropped.append({"item_key": item_key, "rule": "duplicate_key"})
                continue
            defects = entry_errors([entry])
            if defects:
                dropped.append({"item_key": item_key, "rule": defects[0]["code"]})
                continue
            seen.add(identity)
            kept.append(entry)
        if not kept:
            return {"status": "skipped", "reason": "no item could be anchored",
                    "dropped": dropped,
                    "dropped_relations": report["dropped_relations"],
                    "unconfirmed_relations": report["unconfirmed_relations"]}
        publish_report = ensure_publishable(stored_publish_entries(self.wiki.semantic_state()), kept)
        content = ("\n".join(lines) + "\n").encode("utf-8")
        if len(content) > 2 * 1024 * 1024:
            raise UnderstandWikiError("projection_too_large",
                                      "derived passage package exceeds Wiki source bound")
        folder = self.source_root / ".catalyst-proposals"
        folder.mkdir(exist_ok=True)
        if not folder.resolve().is_relative_to(self.source_root):
            raise UnderstandWikiError("source_scope_denied", "projection directory escaped root")
        path = folder / (_sha(content) + ".md")
        if path.is_symlink() or not path.resolve().is_relative_to(self.source_root):
            raise UnderstandWikiError("source_scope_denied", "projection path escaped root")
        try:
            with path.open("xb") as stream:
                stream.write(content)
        except FileExistsError:
            if path.read_bytes() != content:
                raise UnderstandWikiError("projection_collision", "immutable projection differs")
        staged_package = self.semantic.stage_source(path, actor_origin="catalyst_model")
        proposal = self.semantic._propose_native_projection({
            "schema_version": "catalyst.native_projection.v1", "producer_origin": "catalyst_model",
            "scope_id": self.wiki.scope_id, "source_id": staged_package["source_id"],
            "source_revision": staged_package["revision"],
            "origin_document_sha256": staged_package["revision"], "items": kept,
        }, readable_places={ref["locator"] for evidence_id, ref in refs.items()
                            if isinstance(ref.get("locator"), str)
                            and (not verified or evidence_id in verified)})
        return {"status": "proposed", "candidate_id": proposal["candidate_id"],
                "meaning_count": proposal["meaning_count"], "package_path": str(path),
                "package_source_id": staged_package["source_id"],
                "package_bytes": len(content),
                "dropped": dropped, "dropped_count": len(dropped),
                "dropped_relations": report["dropped_relations"],
                "unconfirmed_relations": report["unconfirmed_relations"],
                "publish_report": publish_report, "authority": "CANDIDATE_ONLY"}

    def propose_native(self, result, *, selected_item_ids, actor_context):
        """TEST-SCOPE native document proposal; no evaluation, decision or activation.

        The Markdown projection is a derived evidence package, not the original
        document. It binds original bytes, locators, all producer output, omitted
        items and uncertainty. Every submitted meaning is inferred or unresolved.
        Existing Wiki typed validation and authority receipts remain mandatory.
        """
        import base64
        from .understand_only import UnderstandPort, _extract

        if not isinstance(actor_context, Mapping) or actor_context.get("verified") is not True or actor_context.get("simulation") is not True:
            raise UnderstandWikiError("trusted_test_actor_required", "native document handoff currently requires trusted TEST-SCOPE context")
        if "knowledge.propose" not in actor_context.get("permissions", ()) or self.wiki.scope_id not in actor_context.get("readable_scope_ids", ()):
            raise UnderstandWikiError("scope_or_permission_denied", "knowledge.propose and the exact readable scope are required")
        raw, _, _ = self._validate_result(result.to_dict(), self.wiki.scope_id)
        if raw["semantic_candidate"].get("producer_origin") != "catalyst_native_model":
            raise UnderstandWikiError("native_producer_required", "native projection requires a native provider result")
        if UnderstandPort().verify_freshness(result, source_root=self.source_root) != "FRESH":
            raise UnderstandWikiError("source_revision_changed", "original source changed before harvest")
        if not any(self.source_root == root or self.source_root.is_relative_to(root) for root in self.wiki.roots):
            raise UnderstandWikiError("scope_mismatch", "source root is outside Wiki source roots")
        items = {row["item_id"]: row for row in raw["semantic_candidate"]["items"]}
        selected = list(selected_item_ids)
        if not selected or len(selected) > MAX_NATIVE_CANDIDATE_ITEMS or len(set(selected)) != len(selected) or any(key not in items for key in selected):
            raise UnderstandWikiError("invalid_harvest_selection", "harvest must explicitly select unique existing candidate items")
        refs = {ref["evidence_id"]: ref for ref in raw["evidence_refs"]}
        originals = []
        valid_spans = set()
        for source in result.source_inventory:
            path = (self.source_root / source.relative_path).resolve(strict=True)
            if not path.is_relative_to(self.source_root):
                raise UnderstandWikiError("source_scope_denied", "original source escaped root")
            data = path.read_bytes()
            if _sha(data) != source.source_sha256:
                raise UnderstandWikiError("source_revision_changed", "original source changed during harvest")
            units, _ = _extract(path, source.relative_path, source.source_id, source.source_revision, raw=data,
                locator_scope=tuple(ref["locator"] for ref in refs.values() if ref["source_id"] == source.source_id))
            valid_spans.update((unit.source_id, unit.locator, unit.quote) for unit in units)
            originals.append({"path": source.relative_path, "sha256": _sha(data), "bytes_base64": base64.b64encode(data).decode("ascii")})
        for ref in refs.values():
            if (ref["source_id"], ref["locator"], ref["quote"]) not in valid_spans or _sha(ref["quote"].encode("utf-8")) != ref["span_sha256"]:
                raise UnderstandWikiError("evidence_anchor_mismatch", "evidence does not match re-read original")
        lines = ["# Derived native semantic proposal — TEST-SCOPE, not original facts",
                 _canonical({"understanding": raw, "originals": originals, "selected_item_ids": selected}).decode("utf-8")]
        entries, harvest_report = self.harvest_entries(items, refs, selected, lines=lines, strict=True)
        dropped_relations = harvest_report["dropped_relations"]
        unconfirmed_relations = harvest_report["unconfirmed_relations"]
        publish_report = ensure_publishable(stored_publish_entries(self.wiki.semantic_state()), entries)
        content = ("\n".join(lines) + "\n").encode("utf-8")
        if len(content) > 2 * 1024 * 1024:
            raise UnderstandWikiError("projection_too_large", "derived evidence package exceeds Wiki source bound")
        folder = self.source_root / ".catalyst-proposals"
        folder.mkdir(exist_ok=True)
        if not folder.resolve().is_relative_to(self.source_root):
            raise UnderstandWikiError("source_scope_denied", "projection directory escaped root")
        path = folder / (_sha(content) + ".md")
        if path.is_symlink() or not path.resolve().is_relative_to(self.source_root):
            raise UnderstandWikiError("source_scope_denied", "projection path escaped root")
        try:
            with path.open("xb") as stream:
                stream.write(content)
        except FileExistsError:
            if path.read_bytes() != content:
                raise UnderstandWikiError("projection_collision", "immutable projection differs")
        staged = self.semantic.stage_source(path, actor_origin="catalyst_model")
        proposal = self.semantic._propose_native_projection({
            "schema_version": "catalyst.native_projection.v1", "producer_origin": "catalyst_model",
            "scope_id": self.wiki.scope_id, "source_id": staged["source_id"],
            "source_revision": staged["revision"], "origin_document_sha256": staged["revision"], "items": entries,
        }, readable_places={ref["locator"] for ref in refs.values() if isinstance(ref.get("locator"), str)})
        returned_understanding = {**raw, "wiki_handoff": "CANDIDATE_PROPOSED_ONLY", "handoff_receipt": proposal}
        return {"proposal": proposal, "projection_path": str(path), "understanding": returned_understanding,
                "publish_report": publish_report,
                "dropped_relations": dropped_relations,
                "unconfirmed_relations": unconfirmed_relations,
                "selected_item_ids": selected, "omitted_item_ids": sorted(set(items) - set(selected)),
                "authority": "CANDIDATE_ONLY", "source_role": "DERIVED_PROJECTION_WITH_ORIGINAL_BYTES"}

    def _emit(self, event_type: str, **fields: Any) -> None:
        self.semantic._emit(event_type, **fields)

    def _active_summary(self) -> dict[str, Any]:
        state = self.wiki.semantic_state()
        version_id = state.get("active_version_id")
        version = state.get("accepted_versions", {}).get(version_id, {}) if version_id else {}
        authority_class = version.get("authority_class") if isinstance(version, dict) else None
        if not version_id:
            status = "NO_ACTIVE_VERSION"
        elif authority_class == "test_only":
            status = "TEST_ONLY_ACTIVE"
        elif authority_class == "organization_owner":
            status = "ACTIVE"
        else:
            status = "ACTIVE_AUTHORITY_UNVERIFIED"
        return {
            "active_version_id": version_id,
            "active_authority_class": authority_class,
            "active_semantics_status": status,
        }

    def _source_manifest_digests(self, result: Mapping[str, Any]) -> tuple[str, str]:
        source_manifest = sorted(
            (
                row.get("source_id"),
                row.get("source_revision"),
                row.get("source_sha256"),
            )
            for row in result.get("source_inventory", [])
            if isinstance(row, dict)
        )
        evidence_manifest = sorted(
            (
                row.get("evidence_id"),
                row.get("source_id"),
                row.get("source_revision"),
                row.get("locator"),
                row.get("span_sha256"),
            )
            for row in result.get("evidence_refs", [])
            if isinstance(row, dict)
        )
        return _sha(_canonical(source_manifest)), _sha(_canonical(evidence_manifest))

    def _validate_result(self, result: Mapping[str, Any], declared_scope_id: str) -> tuple[dict[str, Any], bytes, str]:
        try:
            raw = json.loads(_canonical(result).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise UnderstandWikiError("invalid_understanding_result", "Understand result must be finite JSON") from exc
        payload = _canonical(raw)
        if len(payload) > _MAX_RESULT_BYTES:
            raise UnderstandWikiError("understanding_result_too_large", "Understand result exceeds the local handoff size limit")
        required = {
            "version", "request_id", "intent", "result_type", "status",
            "source_inventory", "evidence_refs", "semantic_candidate",
        }
        if not isinstance(raw, dict) or not required.issubset(raw):
            raise UnderstandWikiError("invalid_understanding_result", "Understand result is missing required contract fields")
        if not isinstance(raw.get("version"), str) or not isinstance(raw.get("request_id"), str):
            raise UnderstandWikiError("invalid_understanding_result", "Understand producer version and request identity are required")
        candidate = raw.get("semantic_candidate")
        if not isinstance(candidate, dict) or not isinstance(candidate.get("items"), list):
            raise UnderstandWikiError("invalid_semantic_candidate", "Understand result has no typed semantic candidate")
        if declared_scope_id != self.wiki.scope_id or candidate.get("scope_id") != self.wiki.scope_id:
            raise UnderstandWikiError("scope_mismatch", "Understand result scope does not match this ProjectWiki")
        inventory = raw.get("source_inventory")
        evidence = raw.get("evidence_refs")
        if not isinstance(inventory, list) or len(inventory) > _MAX_SOURCES:
            raise UnderstandWikiError("invalid_source_inventory", "Understand source inventory is invalid or exceeds its bound")
        if not isinstance(evidence, list) or len(evidence) > _MAX_EVIDENCE:
            raise UnderstandWikiError("invalid_evidence_refs", "Understand evidence references are invalid or exceed their bound")
        items = candidate["items"]
        if len(items) > _MAX_ITEMS or any(not isinstance(item, dict) for item in items):
            raise UnderstandWikiError("invalid_candidate_items", "Understand semantic candidate items are invalid or exceed their bound")
        # U0.1: item IDs are graph identities, not just optional display labels.
        # Reject ambiguous candidates before staging any source or candidate state.
        item_ids: set[str] = set()
        for item in items:
            item_id = item.get("item_id")
            if not isinstance(item_id, str) or not _SAFE_REFERENCE_ID.fullmatch(item_id):
                raise UnderstandWikiError("invalid_candidate_item_identity", "candidate item_id must be a nonempty safe reference ID")
            if item_id in item_ids:
                raise UnderstandWikiError("duplicate_candidate_item_id", "candidate item_id must be unique across all item kinds")
            item_ids.add(item_id)
        source_ids: set[str] = set()
        for source in inventory:
            if not isinstance(source, dict):
                raise UnderstandWikiError("invalid_source_inventory", "each source record must be an object")
            source_id = source.get("source_id")
            if not isinstance(source_id, str) or not _SAFE_REFERENCE_ID.fullmatch(source_id) or source_id in source_ids:
                raise UnderstandWikiError("invalid_source_identity", "producer source IDs must be present and unique")
            if _relative_path(source.get("relative_path")) is None:
                raise UnderstandWikiError("invalid_source_locator", "producer source paths must be safe relative paths")
            if not isinstance(source.get("source_revision"), str) or not _SAFE_REFERENCE_ID.fullmatch(source["source_revision"]) or not _SHA256.fullmatch(str(source.get("source_sha256", ""))):
                raise UnderstandWikiError("invalid_source_revision", "producer source revision must be a safe version reference and content digest must be SHA-256")
            source_ids.add(source_id)
        evidence_ids: set[str] = set()
        for ref in evidence:
            if not isinstance(ref, dict):
                raise UnderstandWikiError("invalid_evidence_ref", "each evidence reference must be an object")
            evidence_id = ref.get("evidence_id")
            if not isinstance(evidence_id, str) or not _SAFE_REFERENCE_ID.fullmatch(evidence_id) or evidence_id in evidence_ids:
                raise UnderstandWikiError("invalid_evidence_identity", "producer evidence IDs must be present and unique")
            if not isinstance(ref.get("locator"), str) or not isinstance(ref.get("quote"), str):
                raise UnderstandWikiError("invalid_evidence_locator", "evidence locator and source span must be preserved as strings")
            if not isinstance(ref.get("source_revision"), str) or not _SAFE_REFERENCE_ID.fullmatch(ref["source_revision"]):
                raise UnderstandWikiError("invalid_evidence_revision", "evidence source revision must be a safe version reference")
            if not _SHA256.fullmatch(str(ref.get("source_sha256", ""))) or not _SHA256.fullmatch(str(ref.get("span_sha256", ""))):
                raise UnderstandWikiError("invalid_evidence_digest", "evidence span digest must be a SHA-256 value")
            evidence_ids.add(evidence_id)
        return raw, payload, _sha(payload)

    def _source_files(self, result: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        try:
            root = self.source_root.resolve(strict=True)
        except OSError:
            root = self.source_root
        bindings: list[dict[str, Any]] = []
        content_by_source: dict[str, dict[str, Any]] = {}
        for source in result["source_inventory"]:
            relative = _relative_path(source.get("relative_path"))
            assert relative is not None
            path = root.joinpath(*relative.parts)
            binding: dict[str, Any] = {
                "producer_source_id": source["source_id"],
                "relative_path": relative.as_posix(),
                "source_revision": source["source_revision"],
                "source_sha256": source["source_sha256"],
                "wiki_source_id": None,
                "current_revision": None,
                "status": "SOURCE_UNAVAILABLE",
            }
            try:
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    raise OSError("source is outside configured root")
                raw = resolved.read_bytes()
            except OSError:
                bindings.append(binding)
                continue
            current_revision = _sha(raw)
            binding["current_revision"] = current_revision
            binding["current_source_sha256"] = current_revision
            if resolved.suffix.casefold() in {".docx", ".pptx", ".pdf"}:
                if path.is_symlink() or resolved.relative_to(root).as_posix() != relative.as_posix():
                    binding["status"] = "SOURCE_IDENTITY_MISMATCH"
                    bindings.append(binding)
                    continue
                if current_revision != source["source_sha256"]:
                    binding["status"] = "SOURCE_REVISION_MISMATCH"
                    bindings.append(binding)
                    continue
                try:
                    from .understand_only import _extract

                    locators = [
                        ref["locator"]
                        for ref in result["evidence_refs"]
                        if ref.get("source_id") == source["source_id"]
                    ]
                    units, warnings = _extract(
                        resolved,
                        relative.as_posix(),
                        source["source_id"],
                        current_revision,
                        raw=raw,
                        locator_scope=locators,
                    )
                    if any(warning.startswith(("UNSUPPORTED", "PARTIAL")) for warning in warnings):
                        raise ValueError("incomplete native extraction")
                    unit_map = {unit.locator: unit.quote for unit in units}
                    if len(unit_map) != len(units):
                        raise ValueError("ambiguous native locator")
                    staged = self.semantic.stage_native_source(
                        resolved, actor_origin="catalyst_deterministic"
                    )
                except (
                    OSError,
                    ValueError,
                    WikiError,
                    SemanticTransitionError,
                    ET.ParseError,
                    zipfile.BadZipFile,
                    _PdfParseError,
                ):
                    binding["status"] = "SOURCE_NOT_STAGEABLE"
                    bindings.append(binding)
                    continue
                binding["wiki_source_id"] = staged["source_id"]
                binding["wiki_source_revision"] = staged.get("revision")
                binding["status"] = (
                    "STAGED"
                    if staged.get("revision") == source["source_sha256"]
                    else "SOURCE_REVISION_MISMATCH"
                )
                content_by_source[source["source_id"]] = {
                    "native_locators": unit_map,
                    "binding": binding,
                }
                bindings.append(binding)
                continue
            if resolved.suffix.casefold() != ".md":
                binding["status"] = "UNSUPPORTED_SOURCE_TYPE"
                bindings.append(binding)
                continue
            if current_revision != source["source_sha256"]:
                binding["status"] = "SOURCE_REVISION_MISMATCH"
                bindings.append(binding)
                continue
            try:
                raw.decode("utf-8-sig")
                staged = self.semantic.stage_source(resolved, actor_origin="catalyst_deterministic")
            except (UnicodeDecodeError, WikiError, SemanticTransitionError):
                binding["status"] = "SOURCE_NOT_STAGEABLE"
                bindings.append(binding)
                continue
            binding["wiki_source_id"] = staged["source_id"]
            binding["wiki_source_revision"] = staged.get("revision")
            binding["status"] = "STAGED" if staged.get("revision") == source["source_sha256"] else "SOURCE_REVISION_MISMATCH"
            content_by_source[source["source_id"]] = {
                "bytes": raw,
                "text": raw.decode("utf-8-sig"),
                "binding": binding,
            }
            bindings.append(binding)
        return bindings, content_by_source

    @staticmethod
    def _map_evidence(result: Mapping[str, Any], bindings: list[dict[str, Any]], content_by_source: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
        source_rows = {row["source_id"]: row for row in result["source_inventory"]}
        binding_rows = {row["producer_source_id"]: row for row in bindings}
        mapped: list[dict[str, Any]] = []
        for ref in result["evidence_refs"]:
            source_id = ref.get("source_id")
            source = source_rows.get(source_id)
            binding = binding_rows.get(source_id)
            status = "NEEDS_MAPPING"
            locator_status = "UNSUPPORTED_LOCATOR"
            if not source or not binding:
                status = "UNKNOWN_SOURCE_REFERENCE"
            elif (
                ref.get("source_revision") != source.get("source_revision")
                or ref.get("source_sha256") != source.get("source_sha256")
                or ref.get("relative_path") != source.get("relative_path")
            ):
                status = "SOURCE_IDENTITY_MISMATCH"
            elif binding.get("status") != "STAGED":
                status = binding.get("status", "NEEDS_MAPPING")
            elif _sha(ref["quote"].encode("utf-8")) != ref["span_sha256"]:
                status = "SPAN_DIGEST_MISMATCH"
                locator_status = "ANCHOR_MISMATCH"
            else:
                content = content_by_source.get(source_id, {})
                native = content.get("native_locators")
                match = _LINE_LOCATOR.fullmatch(ref["locator"])
                if isinstance(native, dict):
                    source_span = native.get(ref["locator"])
                    if source_span == ref["quote"] and _sha(source_span.encode("utf-8")) == ref["span_sha256"]:
                        status = "MAPPED"
                        locator_status = "VERIFIED_NATIVE_SPAN"
                    else:
                        status = "ANCHOR_MISMATCH"
                        locator_status = "ANCHOR_MISMATCH"
                elif match is not None:
                    start = int(match.group(1))
                    end = int(match.group(2) or match.group(1))
                    lines = content_by_source[source_id]["text"].splitlines()
                    if 1 <= start <= end <= len(lines):
                        source_span = "\n".join(lines[start - 1:end])
                        if source_span == ref["quote"] and _sha(source_span.encode("utf-8")) == ref["span_sha256"]:
                            status = "MAPPED"
                            locator_status = "VERIFIED_LINE_SPAN"
                        else:
                            status = "ANCHOR_MISMATCH"
                            locator_status = "ANCHOR_MISMATCH"
                    else:
                        status = "ANCHOR_MISMATCH"
                        locator_status = "ANCHOR_MISMATCH"
                else:
                    status = "NEEDS_MAPPING"
            mapped.append({
                "evidence_id": ref["evidence_id"],
                "producer_source_id": source_id if isinstance(source_id, str) else None,
                "wiki_source_id": binding.get("wiki_source_id") if binding else None,
                "source_revision": ref.get("source_revision"),
                "locator": ref["locator"],
                "span_sha256": ref["span_sha256"],
                "mapping_status": status,
                "locator_status": locator_status,
            })
        return mapped

    def submit(self, result: Mapping[str, Any], *, declared_scope_id: str) -> dict[str, Any]:
        input_digest = None
        try:
            _, raw_payload, input_digest = self._validate_result(result, declared_scope_id)
            frozen = json.loads(raw_payload.decode("utf-8"))
            candidate_id = "understand_" + _sha(f"{self.wiki.scope_id}\0{input_digest}".encode("utf-8"))[:24]
            state = self.wiki.semantic_state()
            previous = state["candidates"].get(candidate_id)
            if previous is not None:
                if previous.get("candidate_type") != "understand_handoff.v1" or previous.get("understanding_result_sha256") != input_digest:
                    raise UnderstandWikiError("candidate_identity_conflict", "existing candidate identity is bound to different content")
                source_manifest_sha256, evidence_manifest_sha256 = self._source_manifest_digests(frozen)
                active = self._active_summary()
                self._emit(
                    "understand.candidate.received",
                    candidate_id=candidate_id,
                    submission_sha256=input_digest,
                    producer_origin=_safe_origin(previous.get("producer_origin")),
                    producer_version=previous.get("producer_version"),
                    producer_identity_status=previous.get("producer_identity_status"),
                    source_manifest_sha256=source_manifest_sha256,
                    evidence_manifest_sha256=evidence_manifest_sha256,
                    parent_active_version_id=previous.get("parent_active_version_id"),
                    source_count=len(previous.get("source_bindings", [])),
                    evidence_count=len(previous.get("evidence_mappings", [])),
                    item_count=len(previous.get("understanding_result", {}).get("semantic_candidate", {}).get("items", [])),
                    mapping_status=previous.get("mapping_status"),
                    **active,
                    status="no_op",
                )
                return {"status": "no_op", "authority": "CANDIDATE_ONLY", "candidate_id": candidate_id, "submission_sha256": input_digest}

            source_bindings, content_by_source = self._source_files(frozen)
            evidence_mappings = self._map_evidence(frozen, source_bindings, content_by_source)
            mapping_status = "COMPLETE"
            if any(row["status"] != "STAGED" for row in source_bindings) or any(row["mapping_status"] != "MAPPED" for row in evidence_mappings):
                mapping_status = "NEEDS_MAPPING"
            producer = frozen.get("semantic_candidate", {}).get("producer_origin")
            item_count = len(frozen["semantic_candidate"]["items"])
            source_manifest_sha256, evidence_manifest_sha256 = self._source_manifest_digests(frozen)
            active = self._active_summary()
            typed = None
            try:
                typed = self.publish_handoff(frozen, source_bindings, evidence_mappings, candidate_id)
            except (UnderstandWikiError, SemanticTransitionError, WikiError, OSError) as exc:
                # The handoff is already worth keeping: the frozen result, its bindings and its
                # verified spans stay in the ledger even when no typed candidate could be made,
                # and the refusal is named in the report instead of being swallowed.
                typed = {"status": "refused", "error": getattr(exc, "code", type(exc).__name__)}
            candidate = {
                "candidate_type": "understand_handoff.v1",
                "candidate_id": candidate_id,
                "scope_id": self.wiki.scope_id,
                "authority": "CANDIDATE_ONLY",
                "status": "PROPOSED" if mapping_status == "COMPLETE" else "PROPOSED_NEEDS_MAPPING",
                "mapping_status": mapping_status,
                "producer_origin": producer if isinstance(producer, str) else "unknown",
                "producer_identity_status": "DECLARED_UNVERIFIED",
                "producer_version": frozen["version"],
                "request_id": frozen["request_id"],
                "understanding_result_sha256": input_digest,
                "understanding_result": frozen,
                "source_bindings": source_bindings,
                "evidence_mappings": evidence_mappings,
                "mapping_error_codes": sorted({row["mapping_status"] for row in evidence_mappings if row["mapping_status"] != "MAPPED"} | {row["status"] for row in source_bindings if row["status"] != "STAGED"}),
                "parent_active_version_id": state.get("active_version_id"),
                "created_run_id": getattr(self.semantic.recorder, "run_id", None),
                "latest_evaluation_id": None,
                "latest_decision_id": None,
                "typed_candidate_id": (typed or {}).get("candidate_id"),
            }
            self.wiki.update_semantic_state(lambda mutable: mutable["candidates"].__setitem__(candidate_id, candidate))
            self._emit(
                "understand.candidate.received",
                candidate_id=candidate_id,
                submission_sha256=input_digest,
                producer_origin=_safe_origin(producer),
                producer_version=frozen["version"],
                producer_identity_status="DECLARED_UNVERIFIED",
                source_manifest_sha256=source_manifest_sha256,
                evidence_manifest_sha256=evidence_manifest_sha256,
                parent_active_version_id=state.get("active_version_id"),
                source_count=len(source_bindings),
                evidence_count=len(evidence_mappings),
                item_count=item_count,
                mapping_status=mapping_status,
                **active,
                status="proposed" if mapping_status == "COMPLETE" else "proposed_needs_mapping",
            )
            return {
                "status": "proposed" if mapping_status == "COMPLETE" else "proposed_needs_mapping",
                "authority": "CANDIDATE_ONLY",
                "candidate_id": candidate_id,
                "submission_sha256": input_digest,
                "mapping_status": mapping_status,
                "typed": typed,
                "source_count": len(source_bindings),
                "evidence_count": len(evidence_mappings),
                "mapped_evidence_count": sum(row["mapping_status"] == "MAPPED" for row in evidence_mappings),
                "item_count": item_count,
            }
        except UnderstandWikiError as exc:
            self._emit(
                "understand.candidate.received",
                submission_sha256=input_digest,
                producer_origin="unverified",
                mapping_status="REJECTED",
                **self._active_summary(),
                status="rejected",
                error_code=exc.code,
            )
            raise

    def _candidate(self, candidate_id: str) -> dict[str, Any]:
        if not isinstance(candidate_id, str):
            raise UnderstandWikiError("candidate_not_found", "Understand candidate is unavailable")
        row = self.wiki.semantic_state()["candidates"].get(candidate_id)
        if not isinstance(row, dict) or row.get("candidate_type") != "understand_handoff.v1" or row.get("scope_id") != self.wiki.scope_id:
            raise UnderstandWikiError("candidate_not_found", "Understand candidate is unavailable in this ProjectWiki scope")
        # Fail closed for old/malformed persisted rows as well as new submissions:
        # no consumer may return a graph containing colliding candidate node IDs.
        seen: set[str] = set()
        for item in row.get("understanding_result", {}).get("semantic_candidate", {}).get("items", []):
            item_id = item.get("item_id") if isinstance(item, dict) else None
            if not isinstance(item_id, str) or not _SAFE_REFERENCE_ID.fullmatch(item_id) or item_id in seen:
                raise UnderstandWikiError("candidate_item_identity_conflict", "stored candidate item IDs cannot be resolved unambiguously")
            seen.add(item_id)
        return row

    def _current_source_path(self, binding: Mapping[str, Any]) -> tuple[str, Path | None]:
        """Resolve one contained source path; consumers retain their error contracts.

        This establishes a unique filesystem match, not enterprise identity or
        content-read authority. Do not deduplicate roots or pick a first match.
        """
        relative = PurePosixPath(str(binding.get("relative_path", "")))
        matches = []
        for root_path in self.wiki.roots:
            try:
                root = root_path.resolve(strict=True)
                resolved = root.joinpath(*relative.parts).resolve(strict=True)
                if resolved.is_relative_to(root) and resolved.is_file():
                    matches.append(resolved)
            except OSError:
                continue
        if len(matches) != 1:
            return ("SOURCE_UNAVAILABLE" if not matches else "SOURCE_IDENTITY_AMBIGUOUS", None)
        return "AVAILABLE", matches[0]

    def _current_revision(self, binding: Mapping[str, Any]) -> tuple[str, str | None]:
        status, source_path = self._current_source_path(binding)
        if source_path is None:
            return status, None
        try:
            return "AVAILABLE", _sha(source_path.read_bytes())
        except OSError:
            return "SOURCE_UNAVAILABLE", None

    def candidate_graph(self, candidate_id: str, *, limit: int = 500) -> dict[str, Any]:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise UnderstandWikiError("invalid_graph_limit", "candidate graph limit must be between 1 and 500")
        return self._project_candidate_graph(candidate_id, limit=limit, emit=True)


    # ------------------------------------------------------------------ business view
    #
    # The provenance view above is kept exactly as it was: sources, every evidence node, then
    # whatever fits. Read as a business picture it fails the other way round - evidence is
    # drawn first, the 500-node cap fills with it, and a saved duty has no node type at all.
    # This view draws the saved objects first, hides evidence until asked, and says in the
    # answer what was filtered, focused and cut.
    def business_graph(self, candidate_id: str, *, limit: int = 500,
                       focus: str | None = None, evidence: bool = False) -> dict[str, Any]:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise UnderstandWikiError("invalid_graph_limit", "candidate graph limit must be between 1 and 500")
        if focus is not None and not isinstance(focus, str):
            raise UnderstandWikiError("invalid_graph_focus", "candidate graph focus must be a node id")
        candidate = self._candidate(candidate_id)
        result = candidate["understanding_result"]
        items = [row for row in result["semantic_candidate"]["items"] if isinstance(row, dict)]
        evidence_rows = {row["evidence_id"]: row for row in (result.get("evidence_refs") or [])
                         if isinstance(row, dict) and isinstance(row.get("evidence_id"), str)}
        evidence_map = {row["evidence_id"]: row for row in candidate["evidence_mappings"]}
        titles = {binding["producer_source_id"]: binding["relative_path"]
                  for binding in candidate["source_bindings"]}
        entity_by_key: dict[str, dict[str, Any]] = {}
        object_by_key: dict[str, dict[str, Any]] = {}
        for row in items:
            key = row.get("key")
            if not isinstance(key, str) or not key:
                continue
            if row.get("kind") == "entity":
                entity_by_key.setdefault(key, row)
            elif row.get("kind") in _KIND_NOUN:
                object_by_key.setdefault(key, row)
        entities = {key: (str(row.get("meaning") or key), None)
                    for key, row in entity_by_key.items()}

        def name_of(key: Any) -> str | None:
            """The name the store saved for a key, or nothing; a key is never dressed as a name."""
            if not isinstance(key, str) or not key:
                return None
            row = entity_by_key.get(key) or object_by_key.get(key)
            if row is None:
                return None
            text = row.get("meaning")
            if isinstance(text, str) and text.strip():
                return text.strip()
            return key

        def joined(keys: Any) -> str:
            return "、".join(item for item in (name_of(key) for key in (keys or [])) if item)

        nodes: list[dict[str, Any]] = []
        index: list[dict[str, Any]] = []
        unattached: list[dict[str, Any]] = []
        totals: dict[str, int] = {}
        for row in items:
            item_id = row.get("item_id")
            if not isinstance(item_id, str):
                continue
            raw_kind = row.get("kind") if isinstance(row.get("kind"), str) else "unknown_type"
            kind = raw_kind if raw_kind in _NODE_PRIORITY else "semantic_candidate"
            totals[kind] = totals.get(kind, 0) + 1
            evidence_ids = [ref for ref in (row.get("evidence_refs") or []) if isinstance(ref, str)]
            unresolved_refs = [ref for ref in evidence_ids
                               if evidence_map.get(ref, {}).get("mapping_status") != "MAPPED"]
            node: dict[str, Any] = {
                "id": f"understand-item:{item_id}",
                "type": kind,
                "producer_item_id": item_id,
                "raw_type": raw_kind,
                "key": row.get("key"),
                "label": row.get("meaning"),
                # Copied as saved. A hand-off item that recorded no qualification says so by
                # staying None; this view never fills one in.
                "qualification": row.get("qualification"),
                "qualification_basis": row.get("qualification_basis"),
                "verification": row.get("verification"),
                "scope_state": row.get("scope_state"),
                "evidence_class": row.get("evidence_class", "unknown"),
                "status": "UNRESOLVED" if raw_kind == "unknown" or unresolved_refs else "CANDIDATE_ONLY",
                "evidence_ids": evidence_ids,
            }
            if kind == "entity":
                node["business_type"] = row.get("business_type")
            elif kind == "duty":
                node["holder"] = row.get("subject")
            elif kind == "event":
                node["from"] = [key for key in (row.get("from") or []) if isinstance(key, str)]
                node["to"] = [key for key in (row.get("to") or []) if isinstance(key, str)]
            elif kind == "condition":
                node["applies_to"] = [key for key in (row.get("applies_to") or []) if isinstance(key, str)]
            elif kind == "relation":
                node.update({"subject": row.get("subject"), "predicate": row.get("predicate"),
                             "object": row.get("object"), "relation_source": row.get("relation_source"),
                             "layout_ref": row.get("layout_ref")})
            # What a reader recognises: the saved words, the predicate of a relation, and the
            # role line that says which object this one hangs from. The key stays `key`.
            saved = row.get("meaning")
            saved = saved.strip() if isinstance(saved, str) else ""
            if kind == "relation":
                display = (row.get("predicate") or saved or row.get("key") or item_id)
                sub_label = " → ".join(part for part in (name_of(row.get("subject")),
                                                        name_of(row.get("object"))) if part) or None
            elif kind == "duty":
                holder = name_of(row.get("subject"))
                display = saved or row.get("key") or item_id
                sub_label = f"持有者 · {holder}" if holder else None
            elif kind == "event":
                left = joined(row.get("from"))
                right = joined(row.get("to"))
                display = saved or row.get("key") or item_id
                sub_label = f"{left} → {right}".strip(" →") or None
            elif kind == "condition":
                targets = joined(row.get("applies_to"))
                display = saved or row.get("key") or item_id
                sub_label = f"适用 · {targets}" if targets else None
            elif kind == "entity":
                display = saved or row.get("key") or item_id
                sub_label = row.get("business_type") or None
            else:
                display = saved or row.get("key") or item_id
                sub_label = None
            node["display_name"] = str(display)
            node["sub_label"] = sub_label
            roles = _business_roles(row)
            if kind == "condition":
                # A condition is saved against a duty or an event, not only against an entity.
                resolved = [(name, key) for name, key in roles
                            if key in object_by_key or key in entity_by_key]
            else:
                resolved = [(name, key) for name, key in roles if key in entity_by_key]
            if kind in _KIND_NOUN:
                node["unattached"] = not resolved
                if not resolved:
                    missing = [key for _, key in roles if key not in object_by_key and key not in entity_by_key]
                    if not missing:
                        reason = f"{_KIND_NOUN[kind]} · " + {"duty": "没有记录持有者",
                                                             "event": "没有记录起点或终点",
                                                             "condition": "没有记录适用对象"}[kind]
                    else:
                        reason = f"{_KIND_NOUN[kind]} · 这些键在本体里没有对应实体：{'、'.join(missing)}"
                    node["unattached_reason"] = reason
                    unattached.append({"id": node["id"], "kind": kind, "key": node.get("key"),
                                       "reason": reason})
            if kind in {"duty", "event", "condition", "relation"}:
                normalized = dict(row)
                if kind == "duty" and not normalized.get("holder"):
                    # The hand-off saves a duty's holder in `subject`; the card reads `holder`.
                    normalized["holder"] = row.get("subject")
                normalized["evidence"] = [evidence_rows[ref] for ref in evidence_ids if ref in evidence_rows]
                card = from_item(normalized, scope_id=self.wiki.scope_id, candidate_id=candidate_id,
                                 entities=entities, titles=titles)
                node["object"] = card.to_dict()
            nodes.append(node)
            if kind in _BUSINESS_OBJECT_KINDS:
                index.append({"id": node["id"], "kind": kind, "key": row.get("key"),
                              "label": row.get("meaning"), "display_name": node["display_name"],
                              "sub_label": node["sub_label"], "holder": node.get("holder"),
                              "qualification": node.get("qualification"),
                              "scope_state": node.get("scope_state"),
                              "unattached": node.get("unattached", False)})

        edges: list[dict[str, Any]] = []
        seen_edges: set[str] = set()

        def add_edge(edge_type: str, source: Mapping[str, Any], target: Mapping[str, Any],
                     label: str, **extra: Any) -> None:
            edge_id = f"{edge_type}:{source.get('item_id')}:{target.get('item_id')}"
            if edge_id in seen_edges:
                return
            seen_edges.add(edge_id)
            edges.append({"id": edge_id, "type": edge_type,
                          "source": f"understand-item:{source.get('item_id')}",
                          "target": f"understand-item:{target.get('item_id')}",
                          "label": label, "direction": "source_to_target",
                          "status": "CANDIDATE_ONLY", **extra})

        for row in items:
            kind = row.get("kind")
            if kind == "relation":
                for edge_type, field in (("subject_entity", "subject"), ("object_entity", "object")):
                    target = entity_by_key.get(row.get(field))
                    if target is not None:
                        add_edge(edge_type, row, target, str(row.get("predicate") or "关系"),
                                 relation_source=row.get("relation_source"))
            elif kind == "duty":
                target = entity_by_key.get(row.get("subject"))
                if target is not None:
                    add_edge("held_by", row, target, "持有者")
            elif kind == "event":
                for edge_type, field, label in (("event_from", "from", "起点"),
                                                ("event_to", "to", "终点")):
                    for key in row.get(field) or []:
                        target = entity_by_key.get(key)
                        if target is not None:
                            add_edge(edge_type, row, target, label)
            elif kind == "condition":
                for key in row.get("applies_to") or []:
                    target = object_by_key.get(key)
                    if target is not None and target is not row:
                        add_edge("applies_to", row, target, "适用")
        edge_totals: dict[str, int] = {}
        for edge in edges:
            edge_totals[edge["type"]] = edge_totals.get(edge["type"], 0) + 1

        # One event saved with two endpoints is one event; where it is shown twice, that is a
        # placement, not a second event. The two numbers are reported apart.
        placements = {kind: count for kind, count in totals.items()}
        event_nodes = [node for node in nodes if node["type"] == "event"]
        placements["event"] = sum(
            max(1, len({key for key in (node.get("from") or []) + (node.get("to") or [])
                        if key in entity_by_key}))
            for node in event_nodes)
        counts = {
            "items": {kind: {"items": totals.get(kind, 0), "placements": placements.get(kind, 0)}
                      for kind in sorted(set(totals) | {"event"})},
            "edges": dict(sorted(edge_totals.items())),
            "note": "同一事件涉及两端时只算一条，页面或图上两端各展示一次，计入 placements。",
        }

        focus_state = None
        explain_focus = None
        if focus:
            present = {node["id"] for node in nodes}
            if focus not in present:
                # Named, not filled: a missing focus must not quietly become a center.
                nodes, edges = [], []
                focus_state = {"node_id": focus, "depth": 1, "found": False}
                explain_focus = f"聚焦对象不在本候选：{focus}；没有改选别的对象，也没有画中心。"
            else:
                near = {focus}
                for edge in edges:
                    if edge["source"] == focus:
                        near.add(edge["target"])
                    elif edge["target"] == focus:
                        near.add(edge["source"])
                nodes = [node for node in nodes if node["id"] in near]
                edges = [edge for edge in edges if edge["source"] in near and edge["target"] in near]
                focus_state = {"node_id": focus, "depth": 1, "found": True}
                explain_focus = f"聚焦 {focus}，只给一跳邻居：{len(nodes)} 个节点。"

        evidence_total = len(evidence_rows)
        if evidence:
            wanted = set()
            if focus and focus_state and focus_state["found"]:
                for node in nodes:
                    wanted.update(ref for ref in node["evidence_ids"] if ref in evidence_rows)
            else:
                wanted = set(evidence_rows)
            sources: dict[str, dict[str, Any]] = {}
            for ref in sorted(wanted):
                row = evidence_rows[ref]
                source_id = str(row.get("source_id") or "")
                binding = next((item for item in candidate["source_bindings"]
                                if item["producer_source_id"] == source_id), None)
                nodes.append({
                    "id": f"evidence:{ref}",
                    "type": "evidence",
                    "evidence_id": ref,
                    "producer_source_id": source_id,
                    "source_revision": row.get("source_revision"),
                    "relative_path": binding.get("relative_path") if binding else row.get("relative_path"),
                    "locator": row.get("locator"),
                    "span_sha256": row.get("span_sha256"),
                    "evidence_class": row.get("evidence_class"),
                })
                for node in nodes:
                    if node["type"] in {"evidence", "source_revision"}:
                        continue
                    if ref in node["evidence_ids"]:
                        edges.append({"id": f"supports:{node['producer_item_id']}:{ref}",
                                      "type": "supported_by", "source": node["id"],
                                      "target": f"evidence:{ref}", "label": "依据",
                                      "direction": "source_to_target", "status": "CANDIDATE_ONLY"})
                if binding:
                    source_node_id = f"source:{source_id}@{row.get('source_revision')}"
                    sources[source_node_id] = {
                        "id": source_node_id, "type": "source_revision",
                        "producer_source_id": source_id,
                        "relative_path": binding.get("relative_path"),
                        "source_revision": row.get("source_revision"),
                        "wiki_source_id": binding.get("wiki_source_id"),
                        "wiki_source_revision": binding.get("wiki_source_revision"),
                        "mapping_status": binding.get("status"),
                    }
                    edges.append({"id": f"locates_in:{ref}", "type": "locates_in",
                                  "source": f"evidence:{ref}", "target": source_node_id,
                                  "label": "所在来源", "direction": "source_to_target",
                                  "status": "CANDIDATE_ONLY"})
            nodes.extend(sources.values())

        order = {kind: rank for rank, kind in enumerate(_NODE_PRIORITY)}
        ranked = sorted(enumerate(nodes),
                        key=lambda pair: (order.get(pair[1]["type"], len(_NODE_PRIORITY)), pair[0]))
        truncated = len(ranked) > limit
        retained = ranked[:limit]
        kept_ids = {node["id"] for _, node in retained}
        nodes = sorted((node for _, node in retained), key=lambda node: (node["type"], node["id"]))
        edges = sorted((edge for edge in edges if edge["source"] in kept_ids and edge["target"] in kept_ids),
                       key=lambda edge: (edge["type"], edge["id"]))
        shown: dict[str, int] = {}
        for node in nodes:
            shown[node["type"]] = shown.get(node["type"], 0) + 1
        totals["evidence"] = evidence_total
        by_type = {kind: {"shown": shown.get(kind, 0), "total": total}
                   for kind, total in sorted(totals.items())}
        for kind, count in shown.items():
            by_type.setdefault(kind, {"shown": count, "total": count})
        cut = [f"{kind} {row['shown']}/{row['total']}"
               for kind, row in by_type.items() if row["shown"] < row["total"]]
        explain_truncation = None
        if truncated:
            explain_truncation = (f"预算 {limit} 个节点：先保留业务对象，再保留关系与自由文本；"
                                  f"未画出的：{'、'.join(cut)}。")
        explain_evidence = ("已展开证据节点；它们只增加依据，不改变资格、状态或条目摘要。"
                            if evidence else
                            "默认不画证据节点；带 evidence=1 时追加，且在预算里排在业务对象之后。")

        warnings: set[str] = set(candidate.get("mapping_error_codes", []))
        source_freshness: dict[str, str] = {}
        for binding in candidate["source_bindings"]:
            current_status, current_revision = self._current_revision(binding)
            freshness = ("fresh" if current_status == "AVAILABLE" and current_revision == binding["source_sha256"]
                         else "stale" if current_status == "AVAILABLE" else "unknown")
            source_freshness[binding["producer_source_id"]] = freshness
            if freshness != "fresh":
                warnings.add("source_revision_changed" if freshness == "stale" else "source_unavailable")
        if any(node["type"] == "condition" and node.get("unattached") for node in nodes):
            warnings.add("condition_exception_linkage_unavailable")
        active = self._active_summary()
        graph = {
            "schema": "catalyst.understand_business_graph.v1",
            "view": "business",
            "scope_id": self.wiki.scope_id,
            "candidate_id": candidate_id,
            "candidate_status": candidate["status"],
            "authority": "EXTERNAL_CANDIDATE_NOT_ACTIVE",
            "producer_origin": _safe_origin(candidate.get("producer_origin")),
            "producer_identity_status": candidate["producer_identity_status"],
            "producer_version": candidate["producer_version"],
            "parent_active_version_id": candidate.get("parent_active_version_id"),
            **active,
            "freshness_status": ("STALE" if "stale" in source_freshness.values()
                                 else "UNKNOWN" if any(value != "fresh" for value in source_freshness.values())
                                 else "FRESH"),
            "evidence_expanded": bool(evidence),
            "focus": focus_state,
            "counts": counts,
            "budget": {"node_limit": limit, "node_count": len(nodes), "truncated": truncated,
                       "by_type": by_type},
            "explain": {"evidence": explain_evidence, "focus": explain_focus,
                        "truncation": explain_truncation},
            "index": index,
            "unattached": unattached,
            "nodes": nodes,
            "edges": edges,
            "source_index": [
                {"producer_source_id": row["producer_source_id"], "wiki_source_id": row.get("wiki_source_id"),
                 "source_revision": row["source_revision"], "relative_path": row["relative_path"],
                 "mapping_status": row["status"]}
                for row in candidate["source_bindings"]
            ],
            "warnings": sorted(warnings),
            "errors": [],
        }
        self._emit(
            "understand.graph.projected",
            candidate_id=candidate_id,
            graph_sha256=_sha(_canonical(graph)),
            view="business",
            **active,
            node_count=len(nodes),
            edge_count=len(edges),
            source_count=len(candidate["source_bindings"]),
            warning_count=len(warnings),
            status="success",
        )
        return graph

    def _project_candidate_graph(self, candidate_id: str, *, limit: int | None, emit: bool) -> dict[str, Any]:
        """Build graph once; None is allowed only for bounded internal item pagination.

        Public graph reads retain the 500-node cap. Candidate items have a
        separate 1000-item cap at intake and must not inherit graph truncation.
        """
        candidate = self._candidate(candidate_id)
        result = candidate["understanding_result"]
        source_rows = {row["producer_source_id"]: row for row in candidate["source_bindings"]}
        evidence_map = {row["evidence_id"]: row for row in candidate["evidence_mappings"]}
        evidence_refs = {row["evidence_id"]: row for row in result["evidence_refs"]}
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        warnings: set[str] = set(candidate.get("mapping_error_codes", []))
        source_freshness: dict[str, str] = {}
        for binding in candidate["source_bindings"]:
            source_node_id = f"source:{binding['producer_source_id']}@{binding['source_revision']}"
            current_status, current_revision = self._current_revision(binding)
            freshness = "fresh" if current_status == "AVAILABLE" and current_revision == binding["source_sha256"] else "stale" if current_status == "AVAILABLE" else "unknown"
            source_freshness[binding["producer_source_id"]] = freshness
            if freshness != "fresh":
                warnings.add("source_revision_changed" if freshness == "stale" else "source_unavailable")
            nodes.append({
                "id": source_node_id,
                "type": "source_revision",
                "producer_source_id": binding["producer_source_id"],
                "wiki_source_id": binding.get("wiki_source_id"),
                "source_revision": binding["source_revision"],
                "source_sha256": binding["source_sha256"],
                "wiki_source_revision": binding.get("wiki_source_revision"),
                "relative_path": binding["relative_path"],
                "mapping_status": binding["status"],
                "current_revision": current_revision,
                "freshness_status": freshness,
            })
        for evidence_id, ref in evidence_refs.items():
            mapping = evidence_map.get(evidence_id, {})
            producer_source_id = ref.get("source_id")
            binding = source_rows.get(producer_source_id)
            evidence_status = mapping.get("mapping_status", "UNKNOWN_SOURCE_REFERENCE")
            if source_freshness.get(producer_source_id) == "stale":
                evidence_status = "STALE_SOURCE_REVISION"
            elif source_freshness.get(producer_source_id) == "unknown" and binding is not None:
                evidence_status = "SOURCE_UNAVAILABLE"
            evidence_node_id = f"evidence:{evidence_id}"
            nodes.append({
                "id": evidence_node_id,
                "type": "evidence",
                "evidence_id": evidence_id,
                "producer_source_id": producer_source_id,
                "wiki_source_id": mapping.get("wiki_source_id"),
                "source_revision": ref.get("source_revision"),
                "wiki_source_revision": binding.get("wiki_source_revision") if binding else None,
                "relative_path": binding.get("relative_path") if binding else None,
                "locator": ref.get("locator"),
                "span_sha256": ref.get("span_sha256"),
                "mapping_status": evidence_status,
                "locator_status": mapping.get("locator_status", "UNSUPPORTED_LOCATOR"),
            })
            if binding:
                source_node_id = f"source:{producer_source_id}@{ref.get('source_revision')}"
                edges.append({"id": f"evidence-source:{evidence_id}", "type": "locates_in", "source": evidence_node_id, "target": source_node_id})
            if evidence_status != "MAPPED":
                warnings.add(str(evidence_status))

        items = result["semantic_candidate"]["items"]
        item_by_id = {row.get("item_id"): row for row in items if isinstance(row.get("item_id"), str)}
        entity_ids = {item_id for item_id, row in item_by_id.items() if row.get("kind") == "entity"}
        relation_ids = {item_id for item_id, row in item_by_id.items() if row.get("kind") == "relation"}
        for row in items:
            item_id = row.get("item_id")
            if not isinstance(item_id, str):
                warnings.add("candidate_item_id_missing")
                continue
            kind = row.get("kind") if isinstance(row.get("kind"), str) else "unknown_type"
            node_type = kind if kind in {"claim", "unknown", "condition", "exception", "entity", "alias", "relation", "negative_claim"} else "semantic_candidate"
            evidence_ids_for_item = row.get("evidence_refs", []) if isinstance(row.get("evidence_refs"), list) else []
            unresolved_refs = [evidence_id for evidence_id in evidence_ids_for_item if evidence_map.get(evidence_id, {}).get("mapping_status") != "MAPPED"]
            node: dict[str, Any] = {
                "id": f"understand-item:{item_id}",
                "type": node_type,
                "producer_item_id": item_id,
                "raw_type": kind,
                "key": row.get("key"),
                "label": row.get("meaning"),
                "evidence_ids": list(evidence_ids_for_item),
                "evidence_class": row.get("evidence_class", "unknown"),
                "status": "UNRESOLVED" if kind == "unknown" or unresolved_refs else "CANDIDATE_ONLY",
                "mapping_status": "NEEDS_MAPPING" if unresolved_refs else "MAPPED",
            }
            if kind == "relation":
                node.update({
                    "subject": row.get("subject"),
                    "predicate": row.get("predicate"),
                    "object": row.get("object"),
                    "endpoint_identity_status": "UNRESOLVED",
                })
                subject_item_id = row.get("subject_entity_item_id")
                object_item_id = row.get("object_entity_item_id")
                if isinstance(subject_item_id, str) and subject_item_id in entity_ids and isinstance(object_item_id, str) and object_item_id in entity_ids:
                    node["endpoint_identity_status"] = "EXPLICIT_ITEM_ID_BINDING"
                    edges.extend([
                        {"id": f"relation-subject:{item_id}", "type": "subject_entity", "source": f"understand-item:{item_id}", "target": f"understand-item:{subject_item_id}"},
                        {"id": f"relation-object:{item_id}", "type": "object_entity", "source": f"understand-item:{item_id}", "target": f"understand-item:{object_item_id}"},
                    ])
                elif not all(isinstance(row.get(field), str) and row.get(field).strip() for field in ("subject", "predicate", "object")):
                    node["endpoint_identity_status"] = "MISSING_TRIPLE_FIELD"
                    warnings.add("relation_triple_incomplete")
                else:
                    warnings.add("relation_endpoint_identity_unresolved")
            nodes.append(node)
            for evidence_id in evidence_ids_for_item:
                if evidence_id in evidence_refs:
                    edges.append({"id": f"supports:{item_id}:{evidence_id}", "type": "supported_by", "source": f"understand-item:{item_id}", "target": f"evidence:{evidence_id}"})
                else:
                    warnings.add("candidate_evidence_reference_missing")
            if kind in {"condition", "exception"}:
                relation_ref = next((row.get(name) for name in ("relation_item_id", "applies_to_relation_item_id", "related_relation_id") if isinstance(row.get(name), str)), None)
                if relation_ref in relation_ids:
                    edges.append({"id": f"applies-to:{item_id}", "type": "applies_to_relation", "source": f"understand-item:{item_id}", "target": f"understand-item:{relation_ref}"})
                else:
                    warnings.add("condition_exception_linkage_unavailable")
            if kind == "alias":
                entity_ref = next((row.get(name) for name in ("entity_item_id", "target_entity_item_id", "canonical_entity_item_id") if isinstance(row.get(name), str)), None)
                if entity_ref in entity_ids:
                    edges.append({"id": f"alias-of:{item_id}", "type": "alias_of", "source": f"understand-item:{item_id}", "target": f"understand-item:{entity_ref}"})
                else:
                    warnings.add("alias_target_identity_unresolved")

        truncated = limit is not None and len(nodes) > limit
        if truncated:
            retained = {node["id"] for node in nodes[:limit]}
            nodes = nodes[:limit]
            edges = [edge for edge in edges if edge["source"] in retained and edge["target"] in retained]
            warnings.add("graph_truncated")
        nodes.sort(key=lambda row: (row["type"], row["id"]))
        edges.sort(key=lambda row: (row["type"], row["id"]))
        active = self._active_summary()
        graph = {
            "schema": "catalyst.understand_candidate_graph.v1",
            "view": "candidate",
            "scope_id": self.wiki.scope_id,
            "candidate_id": candidate_id,
            "candidate_status": candidate["status"],
            "authority": "EXTERNAL_CANDIDATE_NOT_ACTIVE",
            "producer_origin": _safe_origin(candidate.get("producer_origin")),
            "producer_identity_status": candidate["producer_identity_status"],
            "producer_version": candidate["producer_version"],
            "parent_active_version_id": candidate.get("parent_active_version_id"),
            **active,
            "freshness_status": "STALE" if "stale" in source_freshness.values() else "UNKNOWN" if any(value != "fresh" for value in source_freshness.values()) else "FRESH",
            "nodes": nodes,
            "edges": edges,
            "source_index": [
                {"producer_source_id": row["producer_source_id"], "wiki_source_id": row.get("wiki_source_id"), "source_revision": row["source_revision"], "relative_path": row["relative_path"], "mapping_status": row["status"]}
                for row in candidate["source_bindings"]
            ],
            "warnings": sorted(warnings),
            "errors": [],
            "truncated": truncated,
        }
        if emit:
            self._emit(
                "understand.graph.projected",
                candidate_id=candidate_id,
                graph_sha256=_sha(_canonical(graph)),
                view="candidate",
                **active,
                node_count=len(nodes),
                edge_count=len(edges),
                source_count=len(candidate["source_bindings"]),
                warning_count=len(warnings),
                status="success",
            )
        return graph

    def _active_graph(self, *, limit: int = 100) -> dict[str, Any]:
        active = self._active_summary()
        if active.get("active_version_id") is None:
            return {
                "schema": "catalyst.ontology_graph.v0.1",
                "scope_id": self.wiki.scope_id,
                "authority": "NO_ACTIVE_VERSION",
                "version_id": None,
                "active_version_id": None,
                "knowledge_status": "no_active_version",
                "freshness_status": "UNKNOWN",
                "nodes": [],
                "edges": [],
                "source_index": [],
                "warnings": ["active_version_unknown"],
                "truncated": False,
                "candidate_meanings_included": False,
                "causal_influence_proven": False,
            }
        projector = getattr(self.semantic, "ontology_graph", None)
        if not callable(projector):
            raise UnderstandWikiError("active_graph_projection_unavailable", "this D2 Wiki snapshot has no active graph projection")
        return projector(actor_origin="catalyst_deterministic", limit=limit)

    def active_graph(self, *, limit: int = 100) -> dict[str, Any]:
        graph = self._active_graph(limit=limit)
        active = self._active_summary()
        graph["view"] = "active"
        # This labels the read boundary (active-version-only), while the
        # separate active_semantics_status reports whether a version exists.
        graph["authority"] = "ACTIVE_VERSION_ONLY"
        graph.update(active)
        self._emit(
            "understand.graph.projected",
            candidate_id=None,
            graph_sha256=_sha(_canonical(graph)),
            view="active",
            **active,
            node_count=len(graph.get("nodes", [])),
            edge_count=len(graph.get("edges", [])),
            source_count=len(graph.get("source_index", [])),
            warning_count=len(graph.get("warnings", [])),
            status="success",
        )
        return graph

    def relations(self, candidate_id: str, entity_ref: str) -> dict[str, Any]:
        candidate = self._candidate(candidate_id)
        items = candidate["understanding_result"]["semantic_candidate"]["items"]
        entities = [row for row in items if row.get("kind") == "entity"]
        exact = [row for row in entities if row.get("item_id") == entity_ref or row.get("key") == entity_ref]
        if not exact:
            result = {"status": "UNKNOWN_ENTITY", "scope_id": self.wiki.scope_id, "candidate_id": candidate_id, "entity_identity_established": False, "relations": []}
        else:
            labels = {row.get("meaning") for row in exact}
            same_label = [row for row in entities if row.get("meaning") in labels]
            if len(same_label) > 1:
                result = {"status": "AMBIGUOUS_ENTITY_LABEL", "scope_id": self.wiki.scope_id, "candidate_id": candidate_id, "entity_identity_established": False, "relations": []}
            else:
                label = exact[0].get("meaning")
                relation_rows = []
                for row in items:
                    if row.get("kind") == "relation" and (row.get("subject") == label or row.get("object") == label):
                        relation_rows.append({
                            "producer_item_id": row.get("item_id"),
                            "subject": row.get("subject"),
                            "predicate": row.get("predicate"),
                            "object": row.get("object"),
                            "evidence_ids": list(row.get("evidence_refs", [])),
                            "identity_match": "LITERAL_ENDPOINT_MATCH_UNVERIFIED",
                        })
                result = {
                    "status": "FOUND" if relation_rows else "NO_RELATIONS",
                    "scope_id": self.wiki.scope_id,
                    "candidate_id": candidate_id,
                    "entity_item_id": exact[0].get("item_id"),
                    "entity_label": label,
                    "entity_identity_established": False,
                    "relation_identity_status": "LITERAL_ENDPOINT_MATCH_UNVERIFIED",
                    "relations": relation_rows,
                }
        self._emit(
            "understand.consumer.queried",
            candidate_id=candidate_id,
            query_kind="relations",
            query_sha256=_sha(str(entity_ref).encode("utf-8")),
            result_count=len(result["relations"]),
            result_ids_sha256=_sha(_canonical([row.get("producer_item_id") for row in result["relations"]])),
            identity_status=result.get("relation_identity_status", result["status"]),
            **self._active_summary(),
            status="success",
        )
        return result

    def items(self, candidate_id: str, *, kind: str = "all", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        allowed = {"all", "entity", "alias", "relation", "condition", "exception", "claim", "unknown", "negative_claim"}
        if kind not in allowed or type(limit) is not int or not 1 <= limit <= 500 or type(offset) is not int or not 0 <= offset <= _MAX_ITEMS:
            raise UnderstandWikiError("invalid_candidate_query", "candidate item kind, limit or offset is invalid")
        # Don't page a 500-node graph: it also contains Sources and Evidence,
        # so a valid 1000-item candidate could otherwise be silently omitted.
        graph = self._project_candidate_graph(candidate_id, limit=None, emit=False)
        selected = [node for node in graph["nodes"] if node["type"] in allowed - {"all"} and (kind == "all" or node["type"] == kind)]
        total_count = len(selected)
        if offset > total_count:
            raise UnderstandWikiError("invalid_candidate_query", "candidate item offset exceeds result count")
        page = selected[offset:offset + limit]
        next_offset = offset + len(page) if offset + len(page) < total_count else None
        result = {
            "schema": "catalyst.understand_candidate_items.v1",
            "scope_id": self.wiki.scope_id,
            "candidate_id": candidate_id,
            "authority": "EXTERNAL_CANDIDATE_NOT_ACTIVE",
            "kind": kind,
            "items": page,
            "total_count": total_count,
            "offset": offset,
            "next_offset": next_offset,
            "item_count": len(page),
            "has_more": next_offset is not None,
            "truncated": offset > 0 or next_offset is not None,
            "warnings": graph["warnings"],
        }
        self._emit(
            "understand.consumer.queried",
            candidate_id=candidate_id,
            query_kind=f"items:{kind}",
            query_sha256=_sha(_canonical({"kind": kind, "limit": limit, "offset": offset})),
            result_count=len(page),
            result_ids_sha256=_sha(_canonical([row["producer_item_id"] for row in page if row.get("producer_item_id")])),
            identity_status="CANDIDATE_ONLY",
            **self._active_summary(),
            status="success",
        )
        return result

    def result(self, candidate_id: str) -> dict[str, Any]:
        """Unprivileged result read: metadata only, never the frozen private payload.

        The complete UnderstandingResult remains untouched in the scoped
        ProjectWiki ledger for future *trusted* internal consumption. No public
        or CLI full-result read is authorized by a caller-provided scope, actor
        label, or Boolean flag. That permission must come from an authenticated
        host principal and an independently checked content-read policy.
        """
        candidate = self._candidate(candidate_id)
        frozen = candidate["understanding_result"]
        digest = candidate["understanding_result_sha256"]
        semantic = frozen.get("semantic_candidate", {})
        # No source excerpts, semantic meanings, questions, uncertainty text,
        # evidence quotes, raw result objects or paths may enter this view.
        item_types: dict[str, int] = {}
        for item in semantic.get("items", []):
            kind = item.get("kind") if isinstance(item, dict) else None
            # Aggregate only explicitly recognized categories; custom free-form
            # producer labels may contain sensitive names or user content.
            safe = kind if kind in {
                "claim", "negative_claim", "entity", "alias", "relation",
                "condition", "exception", "unknown",
            } else "other"
            item_types[safe] = item_types.get(safe, 0) + 1
        coverage = frozen.get("coverage_receipt", [])
        if isinstance(coverage, dict):
            coverage = coverage.get("items", [])
        # Never return raw CoverageReceipt fields: they may contain source text.
        summary = {
            "schema": "catalyst.understand_candidate_result_summary.v1",
            "scope_id": self.wiki.scope_id,
            "candidate_id": candidate_id,
            "authority": "CANDIDATE_ONLY",
            "candidate_status": candidate["status"],
            "producer_identity_status": candidate.get("producer_identity_status", "DECLARED_UNVERIFIED"),
            "understanding_result_sha256": digest,
            "source_count": len(frozen.get("source_inventory", [])),
            "evidence_count": len(frozen.get("evidence_refs", [])),
            "item_count": len(semantic.get("items", [])),
            "item_type_counts": dict(sorted(item_types.items())),
            "coverage_receipt_count": len(coverage) if isinstance(coverage, list) else None,
            "raw_result_included": False,
            "source_text_included": False,
            "full_result_access": "DENIED_UNTIL_TRUSTED_CONTENT_AUTHORIZATION",
        }
        self._emit(
            "understand.consumer.queried",
            candidate_id=candidate_id,
            query_kind="result",
            query_sha256=_sha(b"understand_candidate_result_summary.v1"),
            result_count=1,
            result_ids_sha256=_sha(_canonical([digest])),
            identity_status="CANDIDATE_ONLY",
            **self._active_summary(),
            status="success",
        )
        return summary

    def evidence(self, candidate_id: str, evidence_id: str) -> dict[str, Any]:
        candidate = self._candidate(candidate_id)
        result = candidate["understanding_result"]
        ref = next((row for row in result["evidence_refs"] if row.get("evidence_id") == evidence_id), None)
        mapping = next((row for row in candidate["evidence_mappings"] if row.get("evidence_id") == evidence_id), None)
        if ref is None or mapping is None:
            raise UnderstandWikiError("evidence_not_found", "evidence reference is unavailable in this candidate")
        source = next((row for row in candidate["source_bindings"] if row.get("producer_source_id") == ref.get("source_id")), None)
        status = mapping["mapping_status"]
        current_revision = None
        if source is not None:
            # Keep the legacy evidence status and read-error behavior; share
            # path selection with graph freshness, not its output policy.
            _, source_path = self._current_source_path(
                {"relative_path": PurePosixPath(source["relative_path"])}
            )
            if source_path is not None:
                current_revision = _sha(source_path.read_bytes())
                if current_revision != source.get("source_sha256"):
                    status = "STALE_SOURCE_REVISION"
            else:
                status = "SOURCE_UNAVAILABLE"
        locator_match = _LINE_LOCATOR.fullmatch(str(ref.get("locator", "")))
        if locator_match:
            locator_kind = "line"
        elif mapping.get("locator_status") == "VERIFIED_NATIVE_SPAN":
            locator_kind = "native"
        else:
            locator_kind = "unsupported"
        result_row = {
            "status": "RESOLVED" if status == "MAPPED" else status,
            "scope_id": self.wiki.scope_id,
            "candidate_id": candidate_id,
            "evidence_id": evidence_id,
            "producer_source_id": ref.get("source_id"),
            "wiki_source_id": mapping.get("wiki_source_id"),
            "wiki_source_revision": source.get("wiki_source_revision") if source else None,
            "source_revision": ref.get("source_revision"),
            "current_revision": current_revision,
            "relative_path": source.get("relative_path") if source else None,
            "locator": ref.get("locator"),
            "locator_status": mapping.get("locator_status"),
            "span_sha256": ref.get("span_sha256"),
            "line_range": [int(locator_match.group(1)), int(locator_match.group(2) or locator_match.group(1))] if locator_match else None,
            "quote_included": False,
        }
        self._emit(
            "understand.evidence.resolved",
            candidate_id=candidate_id,
            evidence_id=evidence_id,
            source_id=ref.get("source_id") if isinstance(ref.get("source_id"), str) else None,
            source_revision=ref.get("source_revision"),
            locator_kind=locator_kind,
            span_sha256=ref.get("span_sha256"),
            resolution_status=result_row["status"],
            **self._active_summary(),
        )
        return result_row

    def compare_active(self, candidate_id: str) -> dict[str, Any]:
        candidate = self._candidate(candidate_id)
        active = self._active_graph()
        active_summary = self._active_summary()
        result = {
            "scope_id": self.wiki.scope_id,
            "candidate_id": candidate_id,
            "candidate_authority": "EXTERNAL_CANDIDATE_NOT_ACTIVE",
            "candidate_status": candidate["status"],
            "active_version_id": active.get("active_version_id"),
            "active_graph_authority": active.get("authority"),
            "active_authority_class": active_summary["active_authority_class"],
            "active_semantics_status": active_summary["active_semantics_status"],
            "candidate_item_count": len(candidate["understanding_result"]["semantic_candidate"]["items"]),
            "active_meaning_count": len([row for row in active.get("nodes", []) if row.get("type") == "meaning"]),
            "crosswalk_status": "NOT_COMPARABLE_WITHOUT_EXPLICIT_CANONICAL_MAPPING",
            "shared_ids": [],
        }
        self._emit(
            "understand.consumer.queried",
            candidate_id=candidate_id,
            query_kind="candidate_vs_active",
            query_sha256=_sha(candidate_id.encode("utf-8")),
            result_count=1,
            result_ids_sha256=_sha(_canonical([candidate_id, active.get("active_version_id")])),
            identity_status=result["crosswalk_status"],
            **active_summary,
            status="success",
        )
        return result

