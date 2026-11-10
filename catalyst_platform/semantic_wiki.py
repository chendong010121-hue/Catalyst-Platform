"""Bounded, source-grounded semantic candidates on the existing ProjectWiki store."""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import uuid
from typing import Any, Callable, Iterable, Mapping, Sequence

from .consumption import record as record_consumption
from .ontology_concepts import resolve_concept_in
from .understand_models import SOURCE_CATEGORIES, SOURCE_STEPS
from .wiki import ProjectWiki, WikiError, WikiUnavailable, _tokens as _wiki_tokens
from .wiki_relocation import line_index


_ACTORS = {
    "codex_fixture",
    "codex_external",
    "catalyst_deterministic",
    "catalyst_model",
    "manager_acceptance",
    "independent_evaluator",
}
_ENTRY = re.compile(r"^\s*(claim|relation|condition|exception|unknown|entity|alias)\s*:\s*(.*?)\s*$", re.IGNORECASE)
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_ID = re.compile(r"^source_[a-f0-9]{24}$")
MAX_CANDIDATE_ITEMS = 200
"""How many items one candidate submission may carry; the port and the schemas agree.

A graph-heavy deck wants more: 144 relations over 99 entities is 243 items whatever
the spread gives way, and the admission plan now keeps that card inside the budget
by letting the edges from the tail wait. The budget itself cannot grow yet, because
publish writes a derived evidence package that carries the whole understanding and
the original document as base64: 320 items made that package 2,133,125 bytes against
the 2,097,152 the Wiki accepts, and 200 items make 1,939,996. Raising this waits for
the package to stop carrying the same quotes twice.
"""

MAX_NATIVE_CANDIDATE_ITEMS = 1000
"""The ceiling for the native projection only, which does not carry the document twice.

Every measured card of one real deck held 277 to 350 items, so the bound above refused
each of them before anything else could. This path writes a package of passages, one
line per anchored item, and every anchor is re-read from the original by the caller; it
is bounded by the adapter's own document bound instead, and the external submission
keeps the 200 that keeps a model's JSON reviewable.
"""
_UNSET = object()


class SemanticTransitionError(ValueError):
    """A semantic lifecycle action cannot be accepted safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _identity(prefix: str, value: Any) -> str:
    return f"{prefix}_" + _digest(_canonical(value))[:24]


def _norm(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _contains_text_token(text: str, value: str) -> bool:
    """Require a whole normalized token/phrase, not an incidental substring."""
    token = value[1:] if value.startswith("@") else value
    if not token:
        return False
    normalized_text = _norm(text)
    normalized_token = _norm(token)
    return re.search(rf"(?<!\w){re.escape(normalized_token)}(?!\w)", normalized_text, re.UNICODE) is not None


def _meaning_id(scope_id: str, kind: str, key: str) -> str:
    return _identity("meaning", [scope_id, kind, _norm(key)])


def _candidate_content_digest(candidate: Mapping[str, Any]) -> str:
    return _digest(_canonical({
        "scope_id": candidate.get("scope_id"),
        "source_id": candidate.get("source_id"),
        "source_revision": candidate.get("source_revision"),
        "entries": candidate.get("entries", []),
    }))


def _canonical_id(scope_id: str, canonical_key: str) -> str:
    return _identity("canonical", [scope_id, _norm(canonical_key)])


def _proposed_canonical_id(scope_id: str, source_id: str, producer_key: str) -> str:
    """Keep producer keys source-scoped until an explicit mapping is accepted."""
    return _identity("canonical", ["source-proposal", scope_id, source_id, _norm(producer_key)])


def _relation_tuple(entry: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        _norm(str(entry.get("subject", ""))),
        _norm(str(entry.get("predicate", ""))),
        _norm(str(entry.get("object", ""))),
    )


def _assign_relation_identities(
    entries: list[dict[str, Any]],
    *,
    scope_id: str,
    parent_meanings: Mapping[str, Mapping[str, Any]],
) -> None:
    """Reuse legacy subject/predicate IDs only for their original triple."""
    prior_by_tuple: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    prior_id_owner: dict[str, tuple[str, str, str]] = {}
    for prior in parent_meanings.values():
        if prior.get("kind") == "relation" and all(_relation_tuple(prior)):
            triple = _relation_tuple(prior)
            prior_by_tuple.setdefault(triple, prior)
            prior_id_owner.setdefault(str(prior.get("meaning_id", "")), triple)

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in entries:
        if entry.get("kind") == "relation":
            subject, predicate, _object = _relation_tuple(entry)
            groups.setdefault((subject, predicate), []).append(entry)

    for pair, group in groups.items():
        assigned: set[tuple[str, str, str]] = set()
        for entry in group:
            triple = _relation_tuple(entry)
            prior = prior_by_tuple.get(triple)
            if prior is not None and prior_id_owner.get(str(prior.get("meaning_id", ""))) == triple:
                entry["meaning_id"] = str(prior["meaning_id"])
                entry["key"] = str(prior.get("key", f"{pair[0]}|{pair[1]}"))
                assigned.add(triple)

        unassigned = {_relation_tuple(entry) for entry in group} - assigned
        legacy_key = f"{pair[0]}|{pair[1]}"
        legacy_id = _meaning_id(scope_id, "relation", legacy_key)
        legacy_prior = parent_meanings.get(legacy_id) or next(
            (row for row in parent_meanings.values() if row.get("meaning_id") == legacy_id),
            None,
        )
        # A pre-existing legacy ID is tied to the triple that originally used it.
        # Never transfer it to a changed Object when a source revision replaces a relation.
        legacy_triple = _relation_tuple(legacy_prior) if isinstance(legacy_prior, Mapping) else ("", "", "")
        legacy_is_represented = any(
            _relation_tuple(entry) == legacy_triple and str(entry.get("meaning_id")) == legacy_id
            for entry in group
        ) if all(legacy_triple) else False
        if legacy_prior is None and unassigned:
            # Deterministic lexical selection makes IDs independent of row order.
            legacy_triple = min(unassigned)
            for entry in group:
                if _relation_tuple(entry) == legacy_triple:
                    entry["meaning_id"] = legacy_id
                    entry["key"] = legacy_key
            assigned.add(legacy_triple)
        elif legacy_is_represented:
            assigned.add(legacy_triple)

        for entry in group:
            triple = _relation_tuple(entry)
            if triple in assigned and entry.get("meaning_id"):
                continue
            triple_key = _canonical(list(triple)).decode("utf-8")
            entry["meaning_id"] = _meaning_id(scope_id, "relation", f"triple:{triple_key}")
            entry["key"] = f"{triple[0]}|{triple[1]}|{triple[2]}"


def _relation_identity_history(
    state: Mapping[str, Any], active_meanings: Mapping[str, Mapping[str, Any]]
) -> dict[str, Mapping[str, Any]]:
    history: dict[str, Mapping[str, Any]] = dict(active_meanings)
    for version_id in sorted(state.get("accepted_versions", {})):
        version = state["accepted_versions"].get(version_id, {})
        meanings = version.get("meanings", {}) if isinstance(version, Mapping) else {}
        if isinstance(meanings, Mapping):
            for meaning_id, row in meanings.items():
                history.setdefault(str(meaning_id), row)
    for candidate_id in sorted(state.get("candidates", {})):
        candidate = state["candidates"].get(candidate_id, {})
        entries = candidate.get("entries", []) if isinstance(candidate, Mapping) else []
        prior_relations = sorted(
            (item for item in entries if isinstance(item, Mapping) and item.get("kind") == "relation"),
            key=lambda item: _relation_tuple(item),
        )
        for index, row in enumerate(prior_relations):
            history[f"candidate:{candidate_id}:{index}"] = row
    return history


def _apply_explicit_alias_mappings(
    entries: list[dict[str, Any]],
    *,
    source_content: str,
    active_meanings: Mapping[str, Mapping[str, Any]],
    scope_id: str,
    source_id: str,
) -> None:
    """Treat a literal Alias declaration as mapping evidence, not the key alone."""
    lines = source_content.splitlines()
    candidate_entities: dict[str, list[dict[str, Any]]] = {}
    active_entities: dict[str, list[Mapping[str, Any]]] = {}
    for row in entries:
        if row.get("kind") == "entity" and isinstance(row.get("canonical_key"), str):
            candidate_entities.setdefault(str(row["canonical_key"]), []).append(row)
    for row in active_meanings.values():
        if row.get("kind") in {"entity", "alias"} and isinstance(row.get("canonical_key"), str):
            active_entities.setdefault(str(row["canonical_key"]), []).append(row)

    for alias in (row for row in entries if row.get("kind") == "alias"):
        line_start = alias.get("line_start")
        explicit = (
            type(line_start) is int
            and 1 <= line_start <= len(lines)
            and lines[line_start - 1].lstrip().casefold().startswith("alias:")
        )
        key = str(alias.get("canonical_key", ""))
        if not explicit:
            alias["canonical_id"] = _proposed_canonical_id(scope_id, source_id, key)
            alias["identity_basis"] = "producer_key_only"
            alias["canonical_identity_status"] = "proposed_unverified"
            continue
        local_targets = candidate_entities.get(key, [])
        external_targets = active_entities.get(key, [])
        targets = local_targets if local_targets else external_targets
        unique_ids = {str(row.get("canonical_id")) for row in targets if isinstance(row.get("canonical_id"), str)}
        if len(unique_ids) == 1:
            alias["canonical_id"] = next(iter(unique_ids))
            alias["identity_basis"] = "explicit_source_alias_declaration"
            alias["canonical_identity_status"] = (
                "mapped_to_candidate_entity" if local_targets else "proposed_mapping_to_active_entity"
            )
        else:
            alias["canonical_id"] = _proposed_canonical_id(scope_id, source_id, key)
            alias["identity_basis"] = "explicit_source_alias_declaration"
            alias["canonical_identity_status"] = "mapping_target_unresolved"


# Fields the execution layer writes or a reviewer signs, and the field the validator writes
# its refusal into (`uncertainty` is where a `degraded:<rule>` verdict travels). A submission
# that carries one is not describing the organisation: it is deciding a reading, a review or
# an archive, and this store only takes those through the records that own them.
_GOVERNANCE_FIELDS = frozenset({
    "degradation", "qualification", "item_id",
    "resolution", "resolves", "remaining", "resolved_by", "review_id",
    "archived", "archived_by", "archived_basis", "uncertainty",
})
# `verification` and `unread_scopes` are fields with a home on the row itself, and only the
# execution layer may fill them: the native adapter hands over the value it derived from the
# original passage and from the run's own extraction status, while an external producer's
# own verdict on its own sentence is not a verification of anything, and its own word for
# how much it read is not a reading. Both are refused from an external submission.
_EXECUTION_ONLY_FROM_EXTERNAL = frozenset({"verification", "unread_scopes",
                                           "ends_source", "keeps_legal_entity_scope",
                                           # Which step wrote the row is the run's own
                                           # knowledge of itself: a producer submitting
                                           # one is naming a step it did not run.
                                           "source_origin"})

# The locator shapes this platform reads a source into: a line, a page and its line, a
# slide's text or table cell, a document paragraph, a sheet row. A place an absence
# searched has to be one of these.
_PLACE_LOCATOR = re.compile(
    r"(?:line:\d+"
    r"|page:\d+(?:#line:\d+)?"
    r"|[^\s#]+#(?:shape:\d+|state|paragraph:\d+|line:\d+|cxn:\d+"
    r"|sheet:\d+:(?:metadata|row:\d+)|table:\d+:r\d+:c\d+))")


def _place_verdict(place: str, lines: Sequence[str], *,
                   re_read: frozenset[str] | None = None) -> str:
    """Whether a place an absence searched is a place at all, and one this source has.

    A scope nobody can point at is not a scope: an absence that names it says nothing
    about the material, and a word that happens to occur in the source is not a place it
    was searched in - it is the thing that was looked for. Every place is therefore read
    as a locator, never as text. `line:N` is resolved against this source's own length.
    A derived package hands over the places its run re-read from the originals, and only
    one of those resolves there: its own lines are the package, not the source.
    """
    if _PLACE_LOCATOR.fullmatch(place) is None:
        return "not_a_locator"
    if re_read is not None:
        return "resolved" if place in re_read else "not_in_source"
    match = re.fullmatch(r"line:(\d+)", place)
    if match:
        return "resolved" if 1 <= int(match.group(1)) <= len(lines) else "not_in_source"
    # A page or a slide is not something a Markdown source can place: the locator is real
    # and this source cannot show it, which is a refusal and not a resolution.
    return "not_in_source"


# The marks that cut one sentence, the marks that cut one clause, and - for the reason a
# reading is refused - the words that name a negation and a condition. The two word lists
# only ever *label* a refusal; no reading of a duty is granted because a list matched, so a
# condition word outside the list cannot be taken as "the passage has no condition".
_DUTY_SENTENCE = re.compile(r"[。；;！!？?\n]+")
_DUTY_CLAUSE = re.compile(r"[，、]")
_DUTY_NEGATION = ("不", "未", "没有", "并非", "禁止")
_DUTY_CONDITION = ("若", "如果", "倘若", "一旦", "假如", "如需")
# A negation is glued to the predicate in Chinese (不负责, 未授权, 没有设置, 禁止使用), so
# the window read for one is the run of characters immediately before the work item.
_DUTY_CONTEXT = 8
# What may stand between a claim and its sentence without being said by the claim: the
# holder's own name is the subject, and punctuation is not a statement.
_DUTY_NOISE = " \t\r\n，、；;：:。."


def _duty_owner(sentence: str, names: Sequence[str], at: int) -> str:
    """The nearest unit named before `at`, or "" when the sentence names none there."""
    owner, found = "", -1
    for name in names:
        position = sentence.rfind(name, 0, at)
        if position > found or (position >= 0 and position == found and len(name) > len(owner)):
            owner, found = name, position
    return owner


def _duty_spans(sentence: str, content: str, clauses: Sequence[str]) -> list[tuple[int, int]] | None:
    """Where each clause of the claim sits in this sentence, or None if the claim is not here.

    The claim is looked for whole first. When it is not found, its clauses are looked for in
    order and at increasing positions: a reader's shorthand may drop the words between two
    clauses, but it may not reorder them or invent a clause.
    """
    spans: list[tuple[int, int]] = []
    at = sentence.find(content) if content else -1
    if at < 0:
        at = 0
    for clause in clauses:
        position = sentence.find(clause, at)
        if position < 0:
            return None
        spans.append((position, position + len(clause)))
        at = position + len(clause)
    return spans


def _duty_dropped(sentence: str, spans: Sequence[tuple[int, int]], holder_name: str,
                  content: str) -> str:
    """The sentence outside the claim that the claim does not itself say, or "".

    Every interval the claim does not cover is read - before its first clause, between any
    two of them, after its last. Words between two matched fragments are not a safe omission:
    「…专业能力建设，仅在审批通过后负责资源统筹」 states the second clause under a condition,
    and a claim that reads only the clauses has dropped it.

    Only the holder's name and punctuation may stand in those intervals: everything else is
    wording the row left out, and whether that wording restricts the claim or is more of the
    same claim is exactly what a text rule cannot tell. So it is named, not judged.
    """
    edges = [0, *(edge for span in spans for edge in span), len(sentence)]
    for at in range(0, len(edges), 2):
        part = sentence[edges[at]:edges[at + 1]].replace(holder_name, "").strip(_DUTY_NOISE)
        if part and part not in content:
            return part
    return ""


def _duty_support(quote: str, meaning: str | None, holder_name: str,
                  other_names: Sequence[str]) -> tuple[bool, str]:
    """Whether one sentence of the passage carries this duty, and if not, what is missing.

    This is a guard over the text of one sentence, not a reading of it. It can show three
    things: that the claim was cut out of the passage and stitched to another unit's half,
    that the sentence says more than the claim (so the claim silently dropped wording, and
    whether that wording was a condition is not something this function can establish), and
    that the polarity of the work differs. It cannot show that different wording means the
    same thing, it does not look at exceptions, and it has no idea which arrangement a page
    draws. So `confirmed` here says *the sentence says this, and nothing in the sentence is
    missing from it* - not that the claim is true of the organisation.

    This is frozen as a bounded gate: what it checks is listed below and nothing more is to be
    added to it. A row this refuses is a question for a reader or a decision, not a reason to
    grow another pattern here - and the way past it is that decision, never a longer list.

    A duty is one entity and one work item in one sentence. The passage carries the row when
    a single sentence says all of it: the work in the row's own words, every clause of that
    claim belonging to the holder (a clause inherited from the unit named before it is that
    unit's), the same polarity, and no wording before or after the claim that the claim drops.
    Everything else stays unconfirmed with the fragment that is missing named.
    """
    if not holder_name or holder_name not in quote:
        return False, "holder_not_in_evidence"
    content = (meaning or "").strip()
    if content.startswith(holder_name):
        # The row may quote the whole line, holder included: what has to be carried is the
        # work after it, and the name in front of that work is then the holder by itself.
        content = content[len(holder_name):].lstrip("：:，、 ")
    # The sentence this is compared against was cut at these marks, so a row that quotes
    # the sentence whole ends in one of them and carries it nowhere.
    content = content.rstrip("。；;！!？?").strip()
    clauses = [part for part in _DUTY_CLAUSE.split(content) if part]
    if not clauses:
        return False, "duty_text_not_in_evidence"
    names = [name for name in (*other_names, holder_name) if name]
    reasons: list[str] = []
    for sentence in _DUTY_SENTENCE.split(quote):
        if not sentence:
            continue
        spans = _duty_spans(sentence, content, clauses)
        if spans is None:
            continue
        start, end = spans[0][0], spans[-1][1]
        owners = [_duty_owner(sentence, names, at) for at, _ in spans]
        if any(owner and owner != holder_name for owner in owners):
            # A clause of the claim belongs to the unit named before it. Joining that half to
            # the holder's half is a claim neither unit made: the sentence made both, apart.
            reasons.append("duty_attached_to_another_unit")
            continue
        if holder_name not in owners:
            # No clause is the holder's: the sentence says the work and names nobody, and the
            # holder is elsewhere in the passage - the two-cell gap - or named but not here.
            reasons.append("holder_and_duty_not_in_one_sentence" if holder_name not in sentence
                           else "duty_not_attached_to_holder")
            continue
        if any(not any(mark in sentence[at:clause_end] for mark in _DUTY_CONDITION)
               for (at, clause_end), owner in zip(spans, owners) if not owner):
            # A leading fragment with no unit in front of it stands for the work that follows
            # only when it is a condition this reader can see. Otherwise it may be a predicate
            # whose subject is somewhere else, and the holder cannot inherit it.
            reasons.append("duty_not_attached_to_holder")
            continue
        carrier = sentence[max(0, start - _DUTY_CONTEXT):end]
        if (any(mark in content for mark in _DUTY_NEGATION)
                != any(mark in carrier for mark in _DUTY_NEGATION)):
            # Denied here, asserted there - or the other way round. Both are the passage
            # saying something other than the row does.
            reasons.append("polarity_not_carried")
            continue
        dropped = _duty_dropped(sentence, spans, holder_name, content)
        if dropped:
            # 若…负责… is work that waits for a condition, and 仅在…后 is a limit this reader
            # has no word for: either way the claim states less than the sentence. Named by
            # what is visible - a condition word, or wording the claim does not carry.
            reasons.append("condition_not_carried"
                           if any(mark in dropped for mark in _DUTY_CONDITION)
                           else "restriction_not_carried")
            continue
        return True, "duty_carried_by_its_sentence"
    return False, (reasons[0] if reasons else "duty_text_not_in_evidence")


def _reading_qualification(kind: str, *, quote: str, names: Mapping[str, str],
                           holder: str | None = None,
                           ends: Mapping[str, Sequence[str]] | None = None,
                           predicate: str | None = None,
                           evidence_class: str | None = None,
                           meaning: str | None = None) -> tuple[str, str, str]:
    """How far the passage this row cites carries it, and what the reader is left with.

    A row has two separate standings, and this computes the second one. It may be saved
    and reviewed whatever the answer here; it may be read as a fact only when the passage
    it cites carries what the row says *and* the row was read as stated or inferred. So
    `verification` answers "does its own evidence carry it", `qualification` answers "how
    was it read", and the basis is the one thing that was missing when it is pending.

    A duty is carried when one sentence of its passage says it: the work in the row's own
    words, attached to its holder rather than to a unit named beside it, with the same
    polarity and the same condition. The holder's name appearing somewhere in the passage
    is not that - a holder in one cell and the work in another are two fragments, and a
    holder that no cited cell names at all is the row's own gap, not the material's
    silence. An event is carried when its passage names both sides and its predicate, and
    when its two sides are not the same unit: 整合中心、市场营销中心，设置为市场营销中心
    names one unit before and after, and which of the two is terminating and which
    survives is what the row cannot say.
    """
    if not quote:
        return "pending", "unconfirmed", "content_not_established"

    def named(key: str) -> bool:
        name = str(names.get(key) or "")
        return bool(name) and name in quote

    def read_as(evidence_class: str | None) -> str:
        # A native harvest stores every meaning as `inferred`, and an external submission
        # that re-read its own passage can declare `observed_from_source`; the word a
        # reader sees says which of the two it was.
        return "stated" if evidence_class == "observed_from_source" else "inferred"

    if kind == "duty":
        if evidence_class == "unresolved":
            return "pending", "unconfirmed", "content_not_established"
        holder_name = str(names.get(holder) or "") if holder else ""
        if holder_name and holder_name in quote:
            # The passage does name the holder, so what its sentence says about the work
            # decides the row: the weaker reading below is for a passage that never names
            # the holder, and cannot stand in for a sentence that says something else.
            carried, basis = _duty_support(
                quote, meaning, holder_name,
                [name for key, name in names.items() if key != holder])
            if carried:
                return read_as(evidence_class), "confirmed", basis
            return "pending", "unconfirmed", basis
        if evidence_class == "inferred" and meaning and meaning in quote:
            return "inferred", "confirmed", "content_read_by_inference"
        return "pending", "unconfirmed", "holder_not_in_evidence"

    sides = ends or {}
    before = list(sides.get("from") or ())
    after = list(sides.get("to") or ())
    if set(before) & set(after):
        # One unit named on both sides of one change: which of the two comes out is what
        # the row cannot say. That is a fact about the row's own shape, so it is named
        # before the reading's standing is consulted - 246 is `unresolved` because its
        # sides overlap, not for want of a passage, and the reader is owed the reason.
        return "pending", "unconfirmed", "roles_or_endpoints_unsettled"
    if evidence_class == "unresolved":
        return "pending", "unconfirmed", "content_not_established"
    says_what_it_is = not predicate or predicate in quote
    if not before or not after:
        # One side is the whole shape of 撤销 and 新设; a two-sided change that lost a
        # side is `unresolved` and has already returned above, so this is not a gap.
        if all(named(key) for key in (*before, *after)) and says_what_it_is:
            return read_as(evidence_class), "confirmed", "its_side_named_in_evidence"
    elif all(named(key) for key in (*before, *after)) and says_what_it_is:
        return read_as(evidence_class), "confirmed", "both_sides_named_in_evidence"
    if evidence_class == "inferred":
        return "inferred", "confirmed", "content_read_by_inference"
    return "pending", "unconfirmed", "endpoints_not_in_evidence"


def _actor(value: str) -> str:
    if value not in _ACTORS:
        raise SemanticTransitionError("invalid_actor_origin", "actor origin is outside the R7 test contract")
    return value


def _entry_rows(content: str, source: Mapping[str, Any], r6_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scope_id = str(source["scope_id"])
    source_id = str(source["source_id"])
    revision = str(source["revision"])
    entries: list[dict[str, Any]] = []
    for claim in r6_claims:
        line = int(claim["line_start"])
        lines = content.splitlines()
        if not 1 <= line <= len(lines):
            continue
        kind = "claim" if claim["kind"] == "rule" else str(claim["kind"])
        meaning = str(claim["meaning"])
        key = meaning
        if kind in {"condition", "exception"} and "|" in meaning:
            candidate_key, candidate_meaning = (part.strip() for part in meaning.split("|", 1))
            if not candidate_key or not candidate_meaning:
                raise SemanticTransitionError("invalid_marker", f"{kind} marker requires a non-empty key and meaning")
            key = candidate_key
            meaning = candidate_meaning
        entries.append(
            {
                "meaning_id": _meaning_id(scope_id, kind, key),
                "kind": kind,
                "key": _norm(key),
                "meaning": meaning,
                "heading": claim.get("heading"),
                "claim_id": claim["claim_id"],
                "source_id": source_id,
                "source_revision": revision,
                "line_start": line,
                "line_end": line,
                "span_sha256": _digest(lines[line - 1].encode("utf-8")),
                "evidence_class": "observed_from_source",
            }
        )

    fence_character: str | None = None
    fence_length = 0
    lines = content.splitlines()
    for line_number, line in enumerate(lines, 1):
        if fence_character is not None:
            closing = _FENCE_CLOSE.match(line)
            if closing and closing.group(1)[0] == fence_character and len(closing.group(1)) >= fence_length:
                fence_character = None
                fence_length = 0
            continue
        opening = _FENCE_OPEN.match(line)
        if opening and (opening.group(1)[0] != "`" or "`" not in opening.group(2)):
            fence_character = opening.group(1)[0]
            fence_length = len(opening.group(1))
            continue
        match = _ENTRY.match(line)
        if not match:
            continue
        entry_kind = match.group(1).casefold()
        if entry_kind == "claim":
            claim_text = match.group(2).strip()
            if not claim_text:
                raise SemanticTransitionError("invalid_marker", "claim marker requires non-empty meaning")
            claim_key = claim_text
            if "|" in claim_text:
                candidate_key, candidate_meaning = (part.strip() for part in claim_text.split("|", 1))
                if not candidate_key or not candidate_meaning:
                    raise SemanticTransitionError("invalid_marker", "claim marker requires a non-empty key and meaning")
                claim_key = candidate_key
                claim_text = candidate_meaning
            entries.append(
                {
                    "meaning_id": _meaning_id(scope_id, "claim", claim_key),
                    "kind": "claim",
                    "key": _norm(claim_key),
                    "meaning": claim_text,
                    "heading": None,
                    "claim_id": None,
                    "source_id": source_id,
                    "source_revision": revision,
                    "line_start": line_number,
                    "line_end": line_number,
                    "span_sha256": _digest(line.encode("utf-8")),
                    "evidence_class": "observed_from_source",
                }
            )
            continue
        if entry_kind in {"entity", "alias"}:
            parts = [part.strip() for part in match.group(2).split("|", 1)]
            if len(parts) != 2 or not all(parts):
                raise SemanticTransitionError(
                    "invalid_marker",
                    f"{entry_kind} marker requires a stable canonical key and a non-empty display name",
                )
            canonical_key, display_name = parts
            if not _SAFE_CODE.fullmatch(canonical_key):
                raise SemanticTransitionError("invalid_marker", "canonical entity keys must be stable lower-case identifiers")
            canonical = _proposed_canonical_id(scope_id, source_id, canonical_key)
            row_kind = "entity" if entry_kind == "entity" else "alias"
            entry_key = canonical_key if row_kind == "entity" else _norm(display_name)
            entries.append(
                {
                    "meaning_id": _meaning_id(scope_id, row_kind, entry_key),
                    "kind": row_kind,
                    "key": _norm(entry_key),
                    "meaning": display_name,
                    "canonical_key": _norm(canonical_key),
                    "canonical_id": canonical,
                    "identity_basis": "producer_key_only",
                    "canonical_identity_status": "proposed_unverified",
                    "heading": None,
                    "claim_id": None,
                    "source_id": source_id,
                    "source_revision": revision,
                    "line_start": line_number,
                    "line_end": line_number,
                    "span_sha256": _digest(line.encode("utf-8")),
                    "evidence_class": "observed_from_source",
                }
            )
            continue
        if entry_kind != "relation":
            continue
        parts = [part.strip() for part in match.group(2).split("|")]
        if len(parts) != 3 or not all(parts):
            raise SemanticTransitionError(
                "invalid_marker",
                "relation marker requires non-empty subject, predicate, and object fields",
            )
        subject, predicate, object_ = parts
        key = f"{_norm(subject)}|{_norm(predicate)}|{_norm(object_)}"
        subject_key = subject[1:] if subject.startswith("@") else None
        object_key = object_[1:] if object_.startswith("@") else None
        if subject_key is not None and not _SAFE_CODE.fullmatch(subject_key):
            raise SemanticTransitionError("invalid_marker", "canonical relation references must use stable lower-case identifiers")
        if object_key is not None and not _SAFE_CODE.fullmatch(object_key):
            raise SemanticTransitionError("invalid_marker", "canonical relation references must use stable lower-case identifiers")
        entries.append(
            {
                "meaning_id": _meaning_id(scope_id, "relation", key),
                "kind": "relation",
                "key": key,
                "subject": subject,
                "predicate": predicate,
                "object": object_,
                "meaning": f"{subject} {predicate} {object_}",
                "canonical_subject_id": _proposed_canonical_id(scope_id, source_id, subject_key) if subject_key else None,
                "canonical_object_id": _proposed_canonical_id(scope_id, source_id, object_key) if object_key else None,
                "claim_id": None,
                "source_id": source_id,
                "source_revision": revision,
                "line_start": line_number,
                "line_end": line_number,
                "span_sha256": _digest(line.encode("utf-8")),
                "evidence_class": "observed_from_source",
            }
        )
    _assign_relation_identities(entries, scope_id=scope_id, parent_meanings={})
    return sorted(entries, key=lambda row: (row["line_start"], row["kind"], row["meaning_id"]))


_EVIDENCE_FIELDS = (
    "source_id", "source_revision", "claim_id", "line_start", "line_end", "span_sha256", "evidence_class",
)


def _evidence_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: row.get(field) for field in _EVIDENCE_FIELDS}


def _meaning_evidence(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence = row.get("evidence")
    if isinstance(evidence, list) and evidence:
        return [dict(item) for item in evidence if isinstance(item, Mapping)]
    return [_evidence_ref(row)]


def _with_evidence(row: Mapping[str, Any], evidence: list[Mapping[str, Any]]) -> dict[str, Any]:
    result = dict(row)
    unique = {
        _canonical(_evidence_ref(item)): _evidence_ref(item)
        for item in evidence
    }
    ordered = sorted(
        unique.values(),
        key=lambda item: (
            str(item.get("source_id", "")), str(item.get("source_revision", "")),
            int(item.get("line_start", 0) or 0), str(item.get("span_sha256", "")),
        ),
    )
    if not ordered:
        return result
    result["evidence"] = ordered
    for field in _EVIDENCE_FIELDS:
        result[field] = ordered[0].get(field)
    return result


def _merge_candidate_meanings(
    parent_meanings: Mapping[str, Mapping[str, Any]], candidate: Mapping[str, Any],
    *, carried: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Replace only this source's evidence and preserve same-meaning evidence from other sources.

    ``carried`` holds the meanings this source still states but which the candidate did not
    mention (sparse reconciliation). They are the ones whose own text is still in the accepted
    revision, so keeping them is the document's claim rather than the model's silence.
    """
    carried = carried or {}
    source_id = str(candidate["source_id"])
    meanings: dict[str, dict[str, Any]] = {}
    for meaning_id, prior in parent_meanings.items():
        remaining = [row for row in _meaning_evidence(prior) if row.get("source_id") != source_id]
        if remaining:
            meanings[meaning_id] = _with_evidence(prior, remaining)
        elif meaning_id in carried:
            meanings[meaning_id] = carried[meaning_id]
    for entry in candidate["entries"]:
        meaning_id = str(entry["meaning_id"])
        current = meanings.get(meaning_id)
        evidence = [*_meaning_evidence(current), _evidence_ref(entry)] if current else [_evidence_ref(entry)]
        # A conflicting value is rejected by evaluation; retaining the proposal here lets diff show it.
        meanings[meaning_id] = _with_evidence(entry, evidence)
    return meanings


def _meaning_diff(
    old: Mapping[str, Mapping[str, Any]], projected: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[str]]:
    """What one accepted version changes about the version it descends from."""
    return {
        "added_meaning_ids": sorted(set(projected) - set(old)),
        "changed_meaning_ids": sorted(
            key for key in set(projected) & set(old)
            if projected[key].get("meaning") != old[key].get("meaning")),
        "removed_meaning_ids": sorted(set(old) - set(projected)),
        "evidence_added_meaning_ids": sorted(
            key for key in set(projected) & set(old)
            if {_canonical(item) for item in _meaning_evidence(projected[key])}
            - {_canonical(item) for item in _meaning_evidence(old[key])}),
        "evidence_removed_meaning_ids": sorted(
            key for key in set(projected) & set(old)
            if {_canonical(item) for item in _meaning_evidence(old[key])}
            - {_canonical(item) for item in _meaning_evidence(projected[key])}),
        "carried_meaning_ids": sorted(
            key for key in projected if projected[key].get("confirmed_by_absence")),
    }


class SemanticWiki:
    """Manage scoped Enterprise Ontology candidates and versions on the existing ProjectWiki store."""

    def __init__(
        self,
        wiki: ProjectWiki,
        *,
        recorder,
        receipt_verifier: Callable[[Mapping[str, Any]], bool] | None = None,
        recover_pending: bool = True,
    ) -> None:
        self.wiki = wiki
        self.recorder = recorder
        # The host owns trust anchors. The Wiki never treats actor_origin as proof.
        self.receipt_verifier = receipt_verifier
        if recover_pending:
            self._recover_pending()

    def _emit(self, event_type: str, **fields: Any) -> dict[str, Any]:
        if event_type == "semantic.external.action":
            fields.setdefault(
                "correlation_id",
                getattr(self.recorder, "correlation_id", None) or self.recorder.invocation_id,
            )
        return self.recorder.event(event_type, scope_id=self.wiki.scope_id, **fields)

    def _v15_fields(self, **fields: Any) -> dict[str, Any]:
        return fields if getattr(self.recorder, "event_schema_version", "1.4") == "1.5" else {}

    def _verified_receipt(
        self,
        receipt: Mapping[str, Any] | None,
        *,
        receipt_type: str,
        candidate: Mapping[str, Any],
        allowed_authority_classes: set[str],
        expected: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(receipt, Mapping):
            raise SemanticTransitionError("authority_receipt_required", "a separately verifiable authority receipt is required")
        required = (
            "receipt_type", "scope_id", "candidate_id", "candidate_sha256", "source_id",
            "source_revision", "issuer_id", "authority_class", "issued_at", "expires_at", "signature",
        )
        if any(name not in receipt for name in required):
            raise SemanticTransitionError("authority_receipt_incomplete", "authority receipt is missing required bound fields")
        if receipt.get("receipt_type") != receipt_type:
            raise SemanticTransitionError("authority_receipt_type_mismatch", "authority receipt type does not match this transition")
        if receipt.get("scope_id") != self.wiki.scope_id or receipt.get("scope_id") != candidate.get("scope_id"):
            raise SemanticTransitionError("authority_receipt_scope_mismatch", "authority receipt is bound to another Wiki scope")
        candidate_digest = _candidate_content_digest(candidate)
        if (
            receipt.get("candidate_id") != candidate.get("candidate_id")
            or receipt.get("candidate_sha256") != candidate_digest
            or receipt.get("source_id") != candidate.get("source_id")
            or receipt.get("source_revision") != candidate.get("source_revision")
        ):
            raise SemanticTransitionError("authority_receipt_binding_mismatch", "authority receipt does not bind the current candidate and source revision")
        issuer_id = receipt.get("issuer_id")
        authority_class = receipt.get("authority_class")
        signature = receipt.get("signature")
        if not isinstance(issuer_id, str) or not _SAFE_CODE.fullmatch(issuer_id):
            raise SemanticTransitionError("authority_receipt_issuer_invalid", "authority receipt issuer must be a stable identifier")
        if authority_class not in allowed_authority_classes:
            raise SemanticTransitionError("authority_receipt_class_invalid", "authority receipt is not from an allowed authority class")
        if not isinstance(signature, str) or not re.fullmatch(r"[a-f0-9]{64}", signature):
            raise SemanticTransitionError("authority_receipt_signature_invalid", "authority receipt signature is missing or malformed")
        issued_at, expires_at = receipt.get("issued_at"), receipt.get("expires_at")
        now = int(time.time())
        if type(issued_at) is not int or type(expires_at) is not int or issued_at > now + 30 or expires_at <= issued_at:
            raise SemanticTransitionError("authority_receipt_time_invalid", "authority receipt validity interval is invalid")
        if expires_at <= now:
            raise SemanticTransitionError("authority_receipt_expired", "authority receipt has expired")
        if expected and any(receipt.get(name) != value for name, value in expected.items()):
            raise SemanticTransitionError("authority_receipt_action_mismatch", "authority receipt does not authorize this exact action")
        if self.receipt_verifier is None:
            raise SemanticTransitionError("receipt_verifier_unavailable", "no trusted receipt verifier is configured for this Wiki host")
        try:
            verified = self.receipt_verifier(receipt)
        except Exception as exc:
            raise SemanticTransitionError("authority_receipt_verification_failed", "trusted receipt verification failed") from exc
        if verified is not True:
            raise SemanticTransitionError("authority_receipt_signature_invalid", "authority receipt signature is not trusted")
        signature_sha256 = _digest(signature.encode("ascii"))
        unsigned = {key: value for key, value in receipt.items() if key != "signature"}
        receipt_id = _identity("receipt", [unsigned, signature_sha256])
        return {
            "receipt_id": receipt_id,
            "receipt_type": receipt_type,
            "scope_id": self.wiki.scope_id,
            "candidate_id": str(candidate["candidate_id"]),
            "candidate_sha256": candidate_digest,
            "source_id": str(candidate["source_id"]),
            "source_revision": str(candidate["source_revision"]),
            "issuer_id": issuer_id,
            "authority_class": authority_class,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "receipt_sha256": _digest(_canonical({"unsigned": unsigned, "signature_sha256": signature_sha256})),
            # Optional bindings an external review carries; they are signed like every other field.
            **{name: receipt[name] for name in ("review_package_sha256", "evaluator_context")
               if name in receipt},
        }

    def _begin(self, operation: str, actor_origin: str, undo: Mapping[str, Any] | None = None) -> dict[str, Any]:
        actor_origin = _actor(actor_origin)
        transition_id = _identity("transition", [self.recorder.run_id, operation, uuid.uuid4().hex])
        event = self._emit(
            "semantic.transition.started",
            transition_id=transition_id,
            operation=operation,
            status="started",
            actor_origin=actor_origin,
        )
        self.wiki.update_semantic_state(
            lambda state: state["transitions"].append(
                {
                    "transition_id": transition_id,
                    "run_id": self.recorder.run_id,
                    "operation": operation,
                    "actor_origin": actor_origin,
                    "status": "started",
                    "started_event_id": event["event_id"],
                    "undo": dict(undo or {}),
                }
            )
        )
        return {"transition_id": transition_id, "actor_origin": actor_origin}

    def _complete(self, transition: Mapping[str, Any], event_type: str, *, changes=None, **fields: Any) -> dict[str, Any]:
        transition_id = str(transition["transition_id"])
        self.wiki.update_semantic_state(
            lambda state: self._mutate_completion(state, transition_id, event_type, changes)
        )
        event = self._emit(event_type, transition_id=transition_id, **fields)

        def mark(state):
            row = self._transition(state, transition_id)
            row["completion_event_id"] = event["event_id"]
            row["completion_event_type"] = event_type
            row["status"] = "awaiting_terminal"

        self.wiki.update_semantic_state(mark)
        return event

    @staticmethod
    def _transition(state: dict[str, Any], transition_id: str) -> dict[str, Any]:
        row = next((item for item in state["transitions"] if item.get("transition_id") == transition_id), None)
        if row is None:
            raise SemanticTransitionError("transition_receipt_missing", "semantic transition receipt is missing")
        return row

    def _mutate_completion(self, state: dict[str, Any], transition_id: str, event_type: str, changes) -> None:
        row = self._transition(state, transition_id)
        row["status"] = "pending_completion"
        row["completion_event_type"] = event_type
        if changes is not None:
            changes(state)

    def _recover_pending(self) -> None:
        state = self.wiki.semantic_state()
        pending = [row for row in state["transitions"] if row.get("status") in {"started", "pending_completion", "awaiting_terminal"}]
        if not pending:
            return
        for transition in pending:
            try:
                run = self.recorder.store.inspect_run(str(transition["run_id"]))
            except Exception as exc:
                raise SemanticTransitionError("transition_trace_unavailable", "a pending semantic transition trace cannot be read") from exc
            events = run.get("events", []) if isinstance(run, dict) else []
            terminal_ok = bool(run and run.get("terminal_status") == "success")
            completion = next(
                (event for event in events if event.get("event_id") == transition.get("completion_event_id")),
                None,
            )
            if completion is None and transition.get("completion_event_type"):
                completion = next(
                    (
                        event for event in events
                        if event.get("event_type") == transition.get("completion_event_type")
                        and event.get("transition_id") == transition.get("transition_id")
                    ),
                    None,
                )
            if terminal_ok and completion is not None:
                def commit(state, transition_id=transition["transition_id"], event=completion):
                    row = self._transition(state, transition_id)
                    row["completion_event_id"] = event["event_id"]
                    row["status"] = "committed"
                self.wiki.update_semantic_state(commit)
                continue

            recovery_status = self.wiki.update_semantic_state(
                lambda mutable, row=transition: self._undo_transition(mutable, row)
            )
            self._emit(
                "semantic.transition.recovered",
                transition_id=transition["transition_id"],
                operation=transition.get("operation"),
                status=recovery_status,
                actor_origin="catalyst_deterministic",
                from_version_id=transition.get("undo", {}).get("previous_version_id"),
                to_version_id=transition.get("undo", {}).get("target_version_id"),
            )

    @staticmethod
    def _undo_transition(state: dict[str, Any], transition: Mapping[str, Any]) -> str:
        undo = transition.get("undo", {})
        operation = transition.get("operation")
        status = "incomplete"
        if operation in {"version.activate", "version.rollback"}:
            target = undo.get("target_version_id")
            if state.get("active_version_id") == target:
                state["active_version_id"] = undo.get("previous_version_id")
                status = "recovered_rollback"
        elif operation == "candidate.decide":
            if undo.get("created_decision", True) and undo.get("decision_id"):
                state["decisions"].pop(undo["decision_id"], None)
            if undo.get("created_version", True) and undo.get("version_id"):
                state["accepted_versions"].pop(undo["version_id"], None)
            candidate = state["candidates"].get(undo.get("candidate_id"))
            if candidate is not None:
                candidate["latest_decision_id"] = undo.get("previous_latest_decision_id")
                candidate["status"] = undo.get("previous_candidate_status", "EVALUATED")
        elif operation == "candidate.evaluate":
            if undo.get("created_evaluation", True) and undo.get("evaluation_id"):
                state["evaluations"].pop(undo["evaluation_id"], None)
            candidate = state["candidates"].get(undo.get("candidate_id"))
            if candidate is not None:
                candidate["latest_evaluation_id"] = undo.get("previous_evaluation_id")
                candidate["status"] = undo.get("previous_candidate_status", "PROPOSED")
        elif operation == "candidate.propose" and undo.get("candidate_id"):
            state["candidates"].pop(undo["candidate_id"], None)
        row = SemanticWiki._transition(state, str(transition["transition_id"]))
        row["status"] = status
        return status

    def finalize_run(self, run_id: str, terminal_status: str) -> None:
        """Close this run's semantic receipts after its R4 terminal event is durable."""
        state = self.wiki.semantic_state()
        pending = [row for row in state["transitions"] if row.get("run_id") == run_id and row.get("status") in {"started", "pending_completion", "awaiting_terminal"}]
        if not pending:
            return
        run = self.recorder.store.inspect_run(run_id)
        for transition in pending:
            completion = next(
                (
                    event for event in (run or {}).get("events", [])
                    if event.get("event_id") == transition.get("completion_event_id")
                    or (
                        transition.get("completion_event_type")
                        and event.get("event_type") == transition.get("completion_event_type")
                        and event.get("transition_id") == transition.get("transition_id")
                    )
                ),
                None,
            )
            if terminal_status == "success" and run and run.get("terminal_status") == "success" and completion:
                def close(mutable, transition_id=transition["transition_id"], event=completion):
                    row = self._transition(mutable, transition_id)
                    row["completion_event_id"] = event["event_id"]
                    row["status"] = "committed"
                self.wiki.update_semantic_state(close)
            else:
                self.wiki.update_semantic_state(lambda mutable, row=transition: self._undo_transition(mutable, row))

    def stage_source(self, path, *, actor_origin: str) -> dict[str, Any]:
        transition = self._begin("source.stage", actor_origin)
        receipt = self.wiki.stage_markdown(path)
        self._emit(
            "knowledge.source.staged",
            source_id=receipt["source_id"],
            source_revision=receipt["revision"],
            status=receipt["status"],
            claim_count=receipt["claim_count"],
        )
        self._complete(
            transition,
            "semantic.source.staged",
            source_id=receipt["source_id"],
            source_revision=receipt["revision"],
            status=receipt["status"],
            meaning_count=receipt["claim_count"],
            actor_origin=transition["actor_origin"],
        )
        return receipt

    def stage_native_source(self, path, *, actor_origin: str) -> dict[str, Any]:
        """Stage native document identity only; no implicit semantic claims or admission."""
        transition = self._begin("source.stage", actor_origin)
        receipt = self.wiki.stage_native_source(path)
        self._emit(
            "knowledge.source.staged",
            source_id=receipt["source_id"],
            source_revision=receipt["revision"],
            status=receipt["status"],
            claim_count=0,
        )
        self._complete(
            transition,
            "semantic.source.staged",
            source_id=receipt["source_id"],
            source_revision=receipt["revision"],
            status=receipt["status"],
            meaning_count=0,
            actor_origin=transition["actor_origin"],
        )
        return receipt

    def record_external_source_read(self, source_id: str, source_revision: str) -> dict[str, Any]:
        """Record a producer-reported source read after checking the staged revision still exists."""
        actor_origin = _actor("codex_external")
        if (
            not isinstance(source_id, str)
            or not _SOURCE_ID.fullmatch(source_id)
            or not isinstance(source_revision, str)
            or not _SHA256.fullmatch(source_revision)
        ):
            self._emit(
                "semantic.external.action",
                action="source_read_receipt",
                producer_origin=actor_origin,
                evidence_level="EXTERNAL_SELF_REPORTED",
                source_id=source_id if isinstance(source_id, str) and _SOURCE_ID.fullmatch(source_id) else None,
                source_revision=source_revision if isinstance(source_revision, str) and _SHA256.fullmatch(source_revision) else None,
                internal_reasoning_status="NOT_OBSERVABLE",
                producer_usage_status="unknown",
                status="rejected",
                error_code="invalid_source_identity",
            )
            raise SemanticTransitionError("invalid_source_identity", "the reported source identity is invalid")
        try:
            snapshot = self.wiki.source_snapshot(source_id)
        except WikiError as exc:
            self._emit(
                "semantic.external.action",
                action="source_read_receipt",
                producer_origin=actor_origin,
                evidence_level="EXTERNAL_SELF_REPORTED",
                source_id=source_id,
                source_revision=source_revision,
                internal_reasoning_status="NOT_OBSERVABLE",
                producer_usage_status="unknown",
                status="rejected",
                error_code="source_unavailable",
            )
            raise SemanticTransitionError("source_unavailable", "the reported source is not available in this Wiki scope") from exc
        if (
            snapshot["source"].get("revision") != source_revision
            or snapshot["current_revision"] != source_revision
        ):
            self._emit(
                "semantic.external.action",
                action="source_read_receipt",
                producer_origin=actor_origin,
                evidence_level="EXTERNAL_SELF_REPORTED",
                source_id=source_id,
                source_revision=source_revision,
                internal_reasoning_status="NOT_OBSERVABLE",
                producer_usage_status="unknown",
                status="rejected",
                error_code="source_revision_changed",
            )
            raise SemanticTransitionError("source_revision_changed", "the reported source revision is no longer current")
        self._emit(
            "semantic.external.action",
            action="source_read_receipt",
            producer_origin=actor_origin,
            evidence_level="EXTERNAL_SELF_REPORTED",
            source_id=source_id,
            source_revision=source_revision,
            internal_reasoning_status="NOT_OBSERVABLE",
            producer_usage_status="unknown",
            status="recorded",
        )
        return {
            "status": "recorded",
            "producer_origin": actor_origin,
            "evidence_level": "EXTERNAL_SELF_REPORTED",
            "source_id": source_id,
            "source_revision": source_revision,
        }

    def record_external_submission_error(
        self,
        *,
        error_code: str,
        submission_sha256: str | None = None,
    ) -> None:
        """Record an externally reported submission parse/read failure without retaining its contents."""
        self._emit(
            "semantic.external.action",
            action="candidate_submitted",
            producer_origin=_actor("codex_external"),
            evidence_level="DIRECTLY_OBSERVED",
            submission_sha256=submission_sha256 if isinstance(submission_sha256, str) and _SHA256.fullmatch(submission_sha256) else None,
            internal_reasoning_status="NOT_OBSERVABLE",
            producer_usage_status="unknown",
            status="rejected",
            error_code=error_code,
        )

    def propose_external_submission(
        self,
        submission: Mapping[str, Any],
        *,
        submission_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Validate a Codex-produced candidate against original source bytes, then use the existing ledger."""
        actor_origin = _actor("codex_external")
        if submission_sha256 is None:
            try:
                submission_digest = _digest(_canonical(submission))
            except (TypeError, ValueError):
                submission_digest = None
        else:
            submission_digest = submission_sha256 if isinstance(submission_sha256, str) and _SHA256.fullmatch(submission_sha256) else None
        source_id = submission.get("source_id") if isinstance(submission, Mapping) else None
        source_revision = submission.get("source_revision") if isinstance(submission, Mapping) else None
        items = submission.get("items") if isinstance(submission, Mapping) else None
        item_count = len(items) if isinstance(items, list) else None

        def reject(code: str, message: str):
            self._emit(
                "semantic.external.action",
                action="candidate_submitted",
                producer_origin=actor_origin,
                evidence_level="DIRECTLY_OBSERVED",
                source_id=source_id if isinstance(source_id, str) and _SOURCE_ID.fullmatch(source_id) else None,
                source_revision=source_revision if isinstance(source_revision, str) and _SHA256.fullmatch(source_revision) else None,
                submission_sha256=submission_digest,
                item_count=item_count,
                internal_reasoning_status="NOT_OBSERVABLE",
                producer_usage_status="unknown",
                status="rejected",
                error_code=code,
            )
            raise SemanticTransitionError(code, message)

        if not isinstance(submission, Mapping):
            reject("invalid_submission", "external candidate submission must be a JSON object")
        if set(submission) != {
            "schema_version", "producer_origin", "scope_id", "source_id",
            "source_revision", "origin_document_sha256", "items",
        }:
            reject("invalid_submission_fields", "external candidate submission contains missing or unknown fields")
        if submission.get("schema_version") != "catalyst.external_candidate.v1":
            reject("unsupported_submission_version", "external candidate submission schema version is unsupported")
        if submission.get("producer_origin") != "codex_external":
            reject("invalid_producer_origin", "external submission producer origin must be codex_external")
        if (
            not isinstance(submission.get("scope_id"), str)
            or len(submission["scope_id"]) > 256
            or submission.get("scope_id") != self.wiki.scope_id
        ):
            reject("scope_mismatch", "external candidate scope does not match this ProjectWiki")
        if (
            not isinstance(source_id, str)
            or not _SOURCE_ID.fullmatch(source_id)
            or not isinstance(source_revision, str)
            or not _SHA256.fullmatch(source_revision)
            or submission.get("origin_document_sha256") != source_revision
            or not isinstance(submission_digest, str)
            or not _SHA256.fullmatch(submission_digest)
        ):
            reject("invalid_source_identity", "external candidate must identify an exact original source revision")
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_CANDIDATE_ITEMS:
            # Over-capacity submissions are refused whole and the gap is reported:
            # trimming would let a partial candidate look complete.
            received = len(items) if isinstance(items, list) else 0
            reject("invalid_submission_items",
                   f"external candidate must contain between 1 and {MAX_CANDIDATE_ITEMS} items; "
                   f"{received} were submitted and "
                   f"{max(0, received - MAX_CANDIDATE_ITEMS)} refused, not truncated")
        try:
            snapshot = self.wiki.source_snapshot(source_id)
        except WikiError as exc:
            reject("source_unavailable", "the original source is unavailable in this Wiki scope")
        if (
            snapshot["source"].get("scope_id") != self.wiki.scope_id
            or snapshot["source"].get("revision") != source_revision
            or snapshot["current_revision"] != source_revision
        ):
            reject("source_revision_changed", "candidate source revision is not the current staged original")

        lines = snapshot["content"].splitlines()
        r6_claims = self.wiki.claim_history(source_id)
        entries: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for item in items:
            if not isinstance(item, Mapping) or set(item) != {
                "kind", "key", "meaning", "evidence_class", "evidence",
            }:
                reject("invalid_submission_item", "each external candidate item must match the strict contract")
            governed = sorted(set(item) & _GOVERNANCE_FIELDS)
            if governed:
                reject("producer_may_not_author_governance_fields",
                       f"a submission may not carry {', '.join(governed)}")
            kind = item.get("kind")
            key = item.get("key")
            meaning = item.get("meaning")
            evidence_class = item.get("evidence_class")
            evidence = item.get("evidence")
            if kind == "unknown":
                # This bridge version has no field for a scope, so it cannot carry an
                # absence at all: use v2, which asks what was looked for and where.
                reject("unknown_without_scope",
                       "this bridge version cannot carry an absence; submit it as v2 with "
                       "its absence and searched places")
            if not isinstance(kind, str) or kind not in {"claim", "unknown"}:
                reject("unsupported_candidate_kind", "this bridge version accepts only claim and unknown items")
            if not isinstance(key, str) or not _SAFE_CODE.fullmatch(key):
                reject("invalid_candidate_key", "external candidate keys must be stable lower-case identifiers")
            if not isinstance(meaning, str) or not meaning.strip() or meaning != meaning.strip() or len(meaning) > 1000 or "\n" in meaning or "\r" in meaning:
                reject("invalid_candidate_meaning", "external candidate meaning must be one non-empty line of at most 1000 characters")
            if not isinstance(evidence_class, str) or evidence_class not in {"observed_from_source", "inferred", "unresolved"}:
                reject("invalid_evidence_class", "external candidate evidence class is unsupported")
            if not isinstance(evidence, Mapping) or set(evidence) != {
                "line_start", "line_end", "quote", "span_sha256",
            }:
                reject("invalid_evidence_anchor", "external candidate evidence must include one exact source line")
            line_start = evidence.get("line_start")
            line_end = evidence.get("line_end")
            quote = evidence.get("quote")
            span_sha256 = evidence.get("span_sha256")
            if (
                type(line_start) is not int
                or line_start < 1
                or type(line_end) is not int
                or line_end != line_start
                or line_start > len(lines)
                or not isinstance(quote, str)
                or not quote
                or len(quote) > 8000
                or not isinstance(span_sha256, str)
                or not _SHA256.fullmatch(span_sha256)
            ):
                reject("invalid_evidence_anchor", "external candidate evidence line range is invalid")
            source_line = lines[line_start - 1]
            if quote != source_line or _digest(source_line.encode("utf-8")) != span_sha256:
                reject("evidence_anchor_mismatch", "external candidate quote or digest does not match the original source line")
            if evidence_class == "observed_from_source" and meaning != quote:
                reject("observed_text_mismatch", "observed_from_source items must preserve the exact quoted statement")
            normalized_key = _norm(key)
            duplicate_key = f"{kind}:{normalized_key}"
            if duplicate_key in seen_keys:
                reject("duplicate_candidate_key", "external candidate keys must be unique within one submission")
            seen_keys.add(duplicate_key)
            matched_claim = next(
                (
                    claim for claim in r6_claims
                    if claim.get("revision") == source_revision and claim.get("line_start") == line_start
                ),
                None,
            )
            entries.append(
                {
                    "meaning_id": _meaning_id(self.wiki.scope_id, kind, key),
                    "kind": kind,
                    "key": normalized_key,
                    "meaning": meaning,
                    "heading": None,
                    "claim_id": matched_claim.get("claim_id") if matched_claim else None,
                    "source_id": source_id,
                    "source_revision": source_revision,
                    "line_start": line_start,
                    "line_end": line_end,
                    "span_sha256": span_sha256,
                    "evidence_class": evidence_class,
                }
            )

        entries.sort(key=lambda row: (row["line_start"], row["kind"], row["meaning_id"]))
        state = self.wiki.semantic_state()
        parent_id = state["active_version_id"]
        parent = state["accepted_versions"].get(parent_id, {}) if parent_id else {}
        active_meanings = parent.get("meanings", {}) if isinstance(parent, dict) else {}
        parent_meanings = _relation_identity_history(state, active_meanings)
        _apply_explicit_alias_mappings(
            entries,
            source_content=snapshot["content"],
            active_meanings=active_meanings,
            scope_id=self.wiki.scope_id,
            source_id=source_id,
        )
        _assign_relation_identities(entries, scope_id=self.wiki.scope_id, parent_meanings=parent_meanings)
        candidate_id = _identity("candidate", [self.wiki.scope_id, source_id, source_revision, entries])
        existing = state["candidates"].get(candidate_id)
        transition = self._begin("candidate.external_submit", actor_origin, {"candidate_id": candidate_id})
        if existing is not None:
            self._complete(
                transition,
                "semantic.candidate.proposed",
                candidate_id=candidate_id,
                parent_version_id=existing.get("parent_version_id"),
                source_id=source_id,
                source_revision=source_revision,
                meaning_count=len(entries),
                meaning_ids_sha256=_digest(_canonical(sorted({row["meaning_id"] for row in entries}))),
                actor_origin=actor_origin,
                status="no_op",
            )
            status = "no_op"
        else:
            candidate = {
                "candidate_id": candidate_id,
                "scope_id": self.wiki.scope_id,
                "source_id": source_id,
                "source_revision": source_revision,
                "parent_version_id": parent_id,
                "proposer_origin": actor_origin,
                "entries": entries,
                "status": "PROPOSED",
                "created_run_id": self.recorder.run_id,
                "latest_evaluation_id": None,
            }
            self._complete(
                transition,
                "semantic.candidate.proposed",
                changes=lambda mutable: mutable["candidates"].__setitem__(candidate_id, candidate),
                candidate_id=candidate_id,
                parent_version_id=parent_id,
                source_id=source_id,
                source_revision=source_revision,
                meaning_count=len(entries),
                meaning_ids_sha256=_digest(_canonical(sorted({row["meaning_id"] for row in entries}))),
                actor_origin=actor_origin,
                status="proposed",
            )
            for entry in entries:
                self._emit(
                    "semantic.candidate.evidence",
                    candidate_id=candidate_id,
                    meaning_id=entry["meaning_id"],
                    source_id=source_id,
                    source_revision=source_revision,
                    line_start=entry["line_start"],
                    line_end=entry["line_end"],
                    span_sha256=entry["span_sha256"],
                    actor_origin=actor_origin,
                )
            status = "proposed"
        self._emit(
            "semantic.external.action",
            action="candidate_submitted",
            producer_origin=actor_origin,
            evidence_level="DIRECTLY_OBSERVED",
            source_id=source_id,
            source_revision=source_revision,
            submission_sha256=submission_digest,
            candidate_id=candidate_id,
            item_count=len(entries),
            internal_reasoning_status="NOT_OBSERVABLE",
            producer_usage_status="unknown",
            status="submitted" if status == "proposed" else "recorded",
        )
        return {
            "status": status,
            "producer_origin": actor_origin,
            "candidate_id": candidate_id,
            "source_id": source_id,
            "source_revision": source_revision,
            "meaning_ids": sorted({row["meaning_id"] for row in entries}),
            "meaning_count": len(entries),
        }

    def propose_external_submission_v2(
        self, submission: Mapping[str, Any], *, submission_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Preserve the external V2 envelope and exact source-line validation."""
        return self._propose_typed_submission(
            submission, submission_sha256=submission_sha256,
            actor_origin="codex_external", schema_version="catalyst.external_candidate.v2",
        )

    def _propose_native_projection(self, submission: Mapping[str, Any], *,
                                   readable_places: Iterable[str] | None = None) -> dict[str, Any]:
        """Internal native adapter: same candidate ledger, validation and admission gates.

        Evidence lines reference an explicitly derived, immutable projection, never
        masquerade as original business observations. Native entries are inferred.
        `readable_places` is what the hand-over re-read from the originals: the package
        it submits is a projection, so a place an absence searched resolves against the
        source the run actually read, not against the lines of the package.
        """
        if any(item.get("evidence_class") not in {"inferred", "unresolved"} for item in submission.get("items", [])):
            raise SemanticTransitionError("native_projection_not_observation", "native projections cannot assert source observations")
        return self._propose_typed_submission(
            submission, submission_sha256=None, actor_origin="catalyst_model",
            schema_version="catalyst.native_projection.v1",
            max_items=MAX_NATIVE_CANDIDATE_ITEMS, readable_places=readable_places,
        )

    def _propose_typed_submission(self, submission, *, submission_sha256, actor_origin, schema_version,
                                  max_items: int = MAX_CANDIDATE_ITEMS,
                                  readable_places: Iterable[str] | None = None):
        actor_origin = _actor(actor_origin)
        def emit_external(*args, **kwargs):
            if actor_origin == "codex_external":
                self._emit(*args, **kwargs)
        if submission_sha256 is None:
            try:
                submission_digest = _digest(_canonical(submission))
            except (TypeError, ValueError):
                submission_digest = None
        else:
            submission_digest = submission_sha256 if isinstance(submission_sha256, str) and _SHA256.fullmatch(submission_sha256) else None
        source_id = submission.get("source_id") if isinstance(submission, Mapping) else None
        source_revision = submission.get("source_revision") if isinstance(submission, Mapping) else None
        items = submission.get("items") if isinstance(submission, Mapping) else None
        item_count = len(items) if isinstance(items, list) else None

        def reject(code: str, message: str):
            emit_external(
                "semantic.external.action",
                action="candidate_submitted",
                producer_origin=actor_origin,
                evidence_level="DIRECTLY_OBSERVED",
                source_id=source_id if isinstance(source_id, str) and _SOURCE_ID.fullmatch(source_id) else None,
                source_revision=source_revision if isinstance(source_revision, str) and _SHA256.fullmatch(source_revision) else None,
                submission_sha256=submission_digest,
                item_count=item_count,
                internal_reasoning_status="NOT_OBSERVABLE",
                producer_usage_status="unknown",
                status="rejected",
                error_code=code,
            )
            raise SemanticTransitionError(code, message)

        envelope_fields = {
            "schema_version", "producer_origin", "scope_id", "source_id",
            "source_revision", "origin_document_sha256", "items",
        }
        if not isinstance(submission, Mapping):
            reject("invalid_submission", "external candidate submission must be a JSON object")
        if set(submission) != envelope_fields:
            reject("invalid_submission_fields", "external candidate submission contains missing or unknown fields")
        if submission.get("schema_version") != schema_version:
            reject("unsupported_submission_version", "external candidate submission schema version is unsupported")
        if submission.get("producer_origin") != actor_origin:
            reject("invalid_producer_origin", "external submission producer origin must be codex_external")
        if (
            not isinstance(submission.get("scope_id"), str)
            or len(submission["scope_id"]) > 256
            or submission.get("scope_id") != self.wiki.scope_id
        ):
            reject("scope_mismatch", "external candidate scope does not match this ProjectWiki")
        if (
            not isinstance(source_id, str)
            or not _SOURCE_ID.fullmatch(source_id)
            or not isinstance(source_revision, str)
            or not _SHA256.fullmatch(source_revision)
            or submission.get("origin_document_sha256") != source_revision
            or not isinstance(submission_digest, str)
            or not _SHA256.fullmatch(submission_digest)
        ):
            reject("invalid_source_identity", "external candidate must identify an exact original source revision")
        if not isinstance(items, list) or not 1 <= len(items) <= max_items:
            # Over-capacity submissions are refused whole and the gap is reported:
            # trimming would let a partial candidate look complete.
            received = len(items) if isinstance(items, list) else 0
            reject("invalid_submission_items",
                   f"candidate must contain between 1 and {max_items} items; "
                   f"{received} were submitted and "
                   f"{max(0, received - max_items)} refused, not truncated")
        try:
            snapshot = self.wiki.source_snapshot(source_id)
        except WikiError as exc:
            reject("source_unavailable", "the original source is unavailable in this Wiki scope")
        if (
            snapshot["source"].get("scope_id") != self.wiki.scope_id
            or snapshot["source"].get("revision") != source_revision
            or snapshot["current_revision"] != source_revision
        ):
            reject("source_revision_changed", "candidate source revision is not the current staged original")

        lines = snapshot["content"].splitlines()
        # A native projection cannot place a scope on its own lines: they are the package
        # this layer wrote, and the places it names are the ones the hand-over re-read.
        re_read = (frozenset(str(place) for place in readable_places)
                   if readable_places is not None and actor_origin != "codex_external" else None)
        r6_claims = self.wiki.claim_history(source_id)
        allowed_fields = {
            "claim": {"kind", "key", "meaning", "evidence_class", "evidence"},
            "unknown": {"kind", "key", "meaning", "evidence_class", "evidence",
                        "absence", "searched", "unread_scopes"},
            "condition": {"kind", "key", "meaning", "evidence_class", "evidence",
                          "applies_to"},
            "exception": {"kind", "key", "meaning", "evidence_class", "evidence",
                          "applies_to"},
            "duty": {"kind", "key", "meaning", "evidence_class", "evidence",
                     "holder", "predicate", "scope_state"},
            "event": {"kind", "key", "meaning", "evidence_class", "evidence",
                      "from", "to", "predicate", "keeps_legal_entity", "scope_state",
                      "ends_source", "keeps_legal_entity_scope"},
            "entity": {"kind", "canonical_key", "display_name", "business_type", "scope_state",
                       "evidence_class", "evidence"},
            "alias": {"kind", "canonical_key", "display_name", "evidence_class", "evidence"},
            "relation": {"kind", "subject", "predicate", "object", "scope_state",
                        "verification", "evidence_class", "evidence"},
        }
        # Who this candidate says its entities are, and what they are called: a duty's
        # holder and an event's side address these keys and no others, and a name is how
        # the cited passage is asked whether it says the row.
        names_by_key: dict[str, str] = {}
        for row in items:
            if isinstance(row, Mapping) and row.get("kind") in {"entity", "alias"}:
                raw_key = row.get("canonical_key")
                if isinstance(raw_key, str) and raw_key.strip():
                    names_by_key[_norm(raw_key)] = str(row.get("display_name") or "")
        # What a condition may limit: the duties and events this same candidate holds.
        limits_able = {_norm(str(row.get("key"))) for row in items
                       if isinstance(row, Mapping)
                       and row.get("kind") in {"duty", "event"}
                       and isinstance(row.get("key"), str)}

        def one_line(value, code):
            if value is None:
                return None
            if (not isinstance(value, str) or not value.strip() or value != value.strip()
                    or len(value) > 256 or "\n" in value or "\r" in value):
                reject(code, "the field is one line of at most 256 characters")
            return value

        entries: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        # The scope's own concept set decides what a type may be, including a concept
        # it has already retired: an old answer's type still means the thing that
        # replaced it, so re-submitting an old card is not refused for being old.
        concept_state = self.wiki.concept_state()
        for item in items:
            if not isinstance(item, Mapping) or not isinstance(item.get("kind"), str):
                reject("invalid_submission_item", "each external candidate item must have a supported kind")
            kind = item["kind"]
            governed = sorted(set(item) & _GOVERNANCE_FIELDS)
            if actor_origin == "codex_external":
                governed += sorted(set(item) & _EXECUTION_ONLY_FROM_EXTERNAL - set(governed))
            if governed:
                # The field is one this layer or a review record writes. Refusing the whole
                # item is the only safe answer: a candidate that arrives pre-verified or
                # pre-resolved is claiming a decision no submission is allowed to make.
                reject("producer_may_not_author_governance_fields",
                       f"a submission may not carry {', '.join(governed)}")
            if kind not in allowed_fields:
                reject("unsupported_candidate_kind", "external candidate kind is unsupported")
            allowed = allowed_fields[kind]
            # A type is optional on an entity so a producer that never heard of the
            # vocabulary still submits, and the score says what that costs.
            # Which chart a row came from is the page's own word, so a producer that
            # never reads one submits without it.
            optional = {"business_type", "scope_state"} if kind == "entity" else (
                {"scope_state", "verification"} if kind == "relation" else (
                    {"absence", "searched", "unread_scopes"} if kind == "unknown" else (
                        {"predicate", "scope_state"} if kind == "duty" else (
                            {"predicate", "scope_state", "ends_source",
                             "keeps_legal_entity_scope"} if kind == "event" else (
                                {"applies_to"} if kind in {"condition", "exception"} else set())))))
            # Which step wrote the row travels with every kind: it says what the row may be.
            allowed = set(allowed) | {"source_origin"}
            optional = set(optional) | {"source_origin"}
            if set(item) - allowed or allowed - set(item) - optional:
                reject("invalid_submission_item", "each typed item must match its exact V2 field contract")
            origin = item.get("source_origin")
            if origin is not None:
                # The tag is read, not believed: a category its step never writes, a step
                # this layer does not run, or a tag naming another row is refused with
                # the row, so a saved row is always one the layer can account for.
                if not isinstance(origin, Mapping):
                    reject("invalid_source_origin", "a row's source is one tag")
                category, step = origin.get("category"), origin.get("step")
                if category not in SOURCE_CATEGORIES or SOURCE_STEPS.get(step) != category:
                    reject("invalid_source_origin",
                           "the tag names a step that does not write that category")
                if not isinstance(origin.get("item_id"), str) or not origin["item_id"]:
                    reject("invalid_source_origin", "a tag names the row it belongs to")
                if origin.get("call") is not None and not isinstance(origin["call"], str):
                    reject("invalid_source_origin", "a tag names the call it was written in")
                origin = dict(origin)
            evidence_class = item.get("evidence_class")
            scope_state = item.get("scope_state")
            if scope_state is not None and scope_state not in {"current", "proposed"}:
                reject("invalid_scope_state", "scope_state is either current or proposed")
            verification = item.get("verification")
            if verification is not None and verification not in {"confirmed", "unconfirmed"}:
                reject("invalid_verification", "verification is either confirmed or unconfirmed")
            absence = item.get("absence")
            if absence is not None and (not isinstance(absence, str) or not absence.strip()
                                        or len(absence) > 200 or "\n" in absence):
                # An absence is the wording that was looked for and not found: one line,
                # short enough to hold in a review, never a passage of its own.
                reject("invalid_absence", "an absence is one line of the wording that was missing")
            absence = absence.strip() if isinstance(absence, str) else None
            searched = item.get("searched")
            if searched is not None:
                if (not isinstance(searched, list) or len(searched) > 256
                        or any(not isinstance(place, str) or not place.strip() or len(place) > 200
                               for place in searched)):
                    reject("invalid_searched", "the places an absence searched are exact locators")
                searched = list(dict.fromkeys(place.strip() for place in searched))
            unread_scopes = item.get("unread_scopes")
            if unread_scopes is not None:
                # What the run could not read, written by the layer that read it. It is a
                # list of locators like the places above, and never free text: a limit
                # nobody can point at would limit nothing.
                if (not isinstance(unread_scopes, list) or len(unread_scopes) > 256
                        or any(not isinstance(scope, str) or not _PLACE_LOCATOR.fullmatch(scope)
                               for scope in unread_scopes)):
                    reject("invalid_unread_scopes",
                           "the scopes a row was not read over are exact locators")
                unread_scopes = list(dict.fromkeys(unread_scopes))
            holder = None
            sides: dict[str, list[str]] = {"from": [], "to": []}
            keeps_legal_entity = None
            keeps_legal_entity_scope = None
            ends_source = None
            applies_to: list[str] = []
            predicate_field = None
            if kind == "duty":
                holder = item.get("holder")
                if not isinstance(holder, str) or not _SAFE_CODE.fullmatch(_norm(holder.lstrip("@"))):
                    reject("invalid_duty_holder", "a duty must name the entity that holds it")
                holder = _norm(holder.lstrip("@"))
                if holder not in names_by_key:
                    # The holder is a field that addresses an entity, not a sentence: a key
                    # this candidate does not hold names nobody a reader can reach.
                    reject("duty_holder_not_selected",
                           "a duty's holder must be an entity of the same candidate")
                predicate_field = one_line(item.get("predicate"), "invalid_duty_predicate")
            elif kind == "event":
                for side in ("from", "to"):
                    values = item.get(side)
                    if not isinstance(values, list) or len(values) > 32 or any(
                            not isinstance(value, str) or not value.strip() or len(value) > 64
                            for value in values):
                        reject("invalid_event_endpoints",
                               "an event's two sides are lists of entity keys")
                    sides[side] = [_norm(value.strip().lstrip("@")) for value in values]
                if not sides["from"] and not sides["to"]:
                    reject("event_endpoints_missing",
                           "an event must name at least one side it changes")
                outside = [key for side in ("from", "to") for key in sides[side]
                           if key not in names_by_key]
                if outside:
                    reject("event_participant_not_selected",
                           f"an event's sides must be entities of the same candidate: {outside[:3]}")
                keeps = item.get("keeps_legal_entity")
                if keeps is not None and not isinstance(keeps, bool):
                    reject("invalid_keeps_legal_entity",
                           "keeps_legal_entity answers true, false, or null when the page is silent")
                keeps_legal_entity = keeps
                ends_source = item.get("ends_source") or "lists"
                if ends_source not in {"lists", "pair"}:
                    reject("invalid_ends_source", "the two sides came from lists or from a pair")
                keeps_legal_entity_scope = item.get("keeps_legal_entity_scope")
                if keeps_legal_entity_scope is not None and keeps_legal_entity_scope != "unclear":
                    reject("invalid_keeps_legal_entity_scope",
                           "a legal-person answer whose scope is not the whole change says unclear")
                predicate_field = one_line(item.get("predicate"), "invalid_event_predicate")
            elif kind in {"condition", "exception"}:
                raw_applies = item.get("applies_to", [])
                if not isinstance(raw_applies, list) or len(raw_applies) > 16 or any(
                        not isinstance(value, str) or not value.strip() or len(value) > 64
                        for value in raw_applies):
                    reject("invalid_applies_to", "applies_to is a list of duty or event keys")
                applies_to = [_norm(value.strip().lstrip("@")) for value in raw_applies]
                outside = [key for key in applies_to if key not in limits_able]
                if outside:
                    # A restriction that cannot say what it restricts is not carried on
                    # the nearest sentence: it says it is unattached instead of guessing.
                    reject("condition_applies_to_unknown",
                           f"a condition must limit a duty or event of the same candidate: {outside[:3]}")
            if kind == "unknown":
                # An absence is a statement about what it searched, so it has to carry both
                # halves and the places it names have to exist: a row that says the material
                # was silent without saying where it looked is a question about the reading,
                # and this store holds statements, not readings.
                if not absence or not searched:
                    reject("unknown_without_scope",
                           "an absence must say what it looked for and where it searched")
                verdicts = {place: _place_verdict(place, lines, re_read=re_read)
                            for place in searched}
                words = [place for place, verdict in verdicts.items() if verdict == "not_a_locator"]
                if words:
                    reject("unknown_scope_not_a_locator",
                           f"the absence names words, not places of a source: {words[:3]}")
                missing = [place for place, verdict in verdicts.items()
                           if verdict == "not_in_source"]
                if missing:
                    reject("unknown_scope_not_in_source",
                           f"the absence names places this source does not have: {missing[:3]}")
            if evidence_class not in {"observed_from_source", "inferred", "unresolved"}:
                reject("invalid_evidence_class", "external candidate evidence class is unsupported")
            evidence = item.get("evidence")
            if not isinstance(evidence, Mapping) or set(evidence) != {
                "line_start", "line_end", "quote", "span_sha256",
            }:
                reject("invalid_evidence_anchor", "external candidate evidence must include one exact source line")
            line_start = evidence.get("line_start")
            line_end = evidence.get("line_end")
            quote = evidence.get("quote")
            span_sha256 = evidence.get("span_sha256")
            if (
                type(line_start) is not int or line_start < 1
                or type(line_end) is not int or line_end != line_start
                or line_start > len(lines)
                or not isinstance(quote, str) or not quote or len(quote) > 8000
                or not isinstance(span_sha256, str) or not _SHA256.fullmatch(span_sha256)
            ):
                reject("invalid_evidence_anchor", "external candidate evidence line range is invalid")
            source_line = lines[line_start - 1]
            if quote != source_line or _digest(source_line.encode("utf-8")) != span_sha256:
                reject("evidence_anchor_mismatch", "external candidate quote or digest does not match the original source line")

            canonical_key = None
            canonical = None
            business_type = None
            subject = predicate = object_ = None
            if kind in {"claim", "unknown", "condition", "exception", "duty", "event"}:
                key, meaning = item.get("key"), item.get("meaning")
                if not isinstance(key, str) or not _SAFE_CODE.fullmatch(key):
                    reject("invalid_candidate_key", "typed candidate keys must be stable lower-case identifiers")
                if not isinstance(meaning, str) or not meaning.strip() or meaning != meaning.strip() or len(meaning) > 1000 or "\n" in meaning or "\r" in meaning:
                    reject("invalid_candidate_meaning", "typed candidate meaning must be one non-empty line of at most 1000 characters")
                normalized_key = _norm(key)
                entry_key = normalized_key
                if evidence_class == "observed_from_source" and meaning not in quote:
                    reject("observed_text_mismatch", "observed_from_source meaning must appear in its exact source line")
            elif kind in {"entity", "alias"}:
                canonical_key, display_name = item.get("canonical_key"), item.get("display_name")
                if not isinstance(canonical_key, str) or not _SAFE_CODE.fullmatch(canonical_key):
                    reject("invalid_canonical_key", "canonical entity keys must be stable lower-case identifiers")
                if not isinstance(display_name, str) or not display_name.strip() or display_name != display_name.strip() or len(display_name) > 256 or "\n" in display_name or "\r" in display_name:
                    reject("invalid_display_name", "entity display name must be one non-empty line")
                raw_business_type = item.get("business_type")
                declared = (resolve_concept_in(concept_state, raw_business_type)
                            if raw_business_type is not None else None)
                business_type = declared.concept_id if declared is not None else None
                if raw_business_type is not None and business_type is None:
                    reject("invalid_business_type",
                           "entity business_type must be one concept of this scope's concept set")
                canonical_key = _norm(canonical_key)
                canonical = _proposed_canonical_id(self.wiki.scope_id, source_id, canonical_key)
                entry_key = canonical_key if kind == "entity" else _norm(display_name)
                normalized_key = entry_key
                meaning = display_name
                if evidence_class == "observed_from_source" and (
                    canonical_key not in _norm(quote) or display_name not in quote
                ):
                    reject("observed_text_mismatch", "observed_from_source entity mapping must appear in its exact source line")
            else:
                subject, predicate, object_ = item.get("subject"), item.get("predicate"), item.get("object")
                if any(not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 256 or "\n" in value or "\r" in value for value in (subject, predicate, object_)):
                    reject("invalid_relation", "relation requires one-line subject, predicate, and object values")
                subject_key = subject[1:] if subject.startswith("@") else None
                object_key = object_[1:] if object_.startswith("@") else None
                if subject_key is not None and not _SAFE_CODE.fullmatch(subject_key):
                    reject("invalid_relation_endpoint", "canonical relation references must use stable lower-case identifiers")
                if object_key is not None and not _SAFE_CODE.fullmatch(object_key):
                    reject("invalid_relation_endpoint", "canonical relation references must use stable lower-case identifiers")
                entry_key = f"{_norm(subject)}|{_norm(predicate)}|{_norm(object_)}"
                normalized_key = entry_key
                meaning = f"{subject} {predicate} {object_}"
                if evidence_class == "observed_from_source" and not all(
                    _contains_text_token(quote, part) for part in (subject, predicate, object_)
                ):
                    reject("observed_text_mismatch", "observed_from_source relation fields must appear in its exact source line")

            duplicate_key = f"{kind}:{normalized_key}"
            if duplicate_key in seen_keys:
                reject("duplicate_candidate_key", "external candidate keys must be unique within one submission")
            seen_keys.add(duplicate_key)
            matched_claim = next(
                (claim for claim in r6_claims if claim.get("revision") == source_revision and claim.get("line_start") == line_start),
                None,
            )
            row: dict[str, Any] = {
                "meaning_id": _meaning_id(self.wiki.scope_id, kind, entry_key),
                "kind": kind,
                "key": normalized_key,
                "meaning": meaning,
                "heading": None,
                "claim_id": matched_claim.get("claim_id") if matched_claim else None,
                "source_id": source_id,
                "source_revision": source_revision,
                "line_start": line_start,
                "line_end": line_end,
                "span_sha256": span_sha256,
                "evidence_class": evidence_class,
            }
            if kind == "unknown" and (absence or searched):
                # An absence speaks for what it searched, not for the material: the row
                # that says 本页未说明 is refutable only while the page it read travels
                # with it, and a store that keeps the places keeps the doubt checkable
                # against every other page of the same source.
                if absence:
                    row["absence"] = absence
                if searched:
                    row["searched"] = searched
                if unread_scopes:
                    row["unread_scopes"] = unread_scopes
            if kind in {"condition", "exception"}:
                # A limit travels with what it limits; a limit nobody can attach says so.
                row["applies_to"] = list(applies_to)
                row["unattached"] = not applies_to
            if kind in {"duty", "event"}:
                qualification, row_verification, basis = _reading_qualification(
                    kind, quote=quote, names=names_by_key, holder=holder, ends=sides,
                    predicate=predicate_field, evidence_class=evidence_class, meaning=meaning)
                # The row is saved whatever this says. It is read as a fact only when the
                # passage its own row cites carries it, and then the store says so on the
                # row instead of leaving a reader to decide from the sentence alone.
                row["qualification"] = qualification
                row["verification"] = row_verification
                row["qualification_basis"] = basis
                if kind == "duty":
                    row["holder"] = holder
                else:
                    row["from"] = list(sides["from"])
                    row["to"] = list(sides["to"])
                    row["ends_source"] = ends_source
                    row["keeps_legal_entity"] = keeps_legal_entity
                    if keeps_legal_entity_scope is not None:
                        row["keeps_legal_entity_scope"] = keeps_legal_entity_scope
                if predicate_field:
                    row["predicate"] = predicate_field
            if origin is not None:
                row["source_origin"] = origin
            if scope_state in {"current", "proposed"}:
                row["scope_state"] = scope_state
            if verification in {"confirmed", "unconfirmed"}:
                row["verification"] = verification
            if kind in {"entity", "alias"}:
                row.update({
                    "canonical_key": canonical_key,
                    "canonical_id": canonical,
                    "identity_basis": "producer_key_only",
                    "canonical_identity_status": "proposed_unverified",
                })
                if business_type is not None:
                    row["business_type"] = business_type
            elif kind == "relation":
                row.update({
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_,
                    "canonical_subject_id": _proposed_canonical_id(self.wiki.scope_id, source_id, subject[1:]) if subject.startswith("@") else None,
                    "canonical_object_id": _proposed_canonical_id(self.wiki.scope_id, source_id, object_[1:]) if object_.startswith("@") else None,
                })
            entries.append(row)

        entries.sort(key=lambda row: (row["line_start"], row["kind"], row["meaning_id"]))
        state = self.wiki.semantic_state()
        parent_id = state["active_version_id"]
        parent = state["accepted_versions"].get(parent_id, {}) if parent_id else {}
        active_meanings = parent.get("meanings", {}) if isinstance(parent, dict) else {}
        parent_meanings = _relation_identity_history(state, active_meanings)
        _apply_explicit_alias_mappings(
            entries,
            source_content=snapshot["content"],
            active_meanings=active_meanings,
            scope_id=self.wiki.scope_id,
            source_id=source_id,
        )
        _assign_relation_identities(entries, scope_id=self.wiki.scope_id, parent_meanings=parent_meanings)
        candidate_id = _identity("candidate", [self.wiki.scope_id, source_id, source_revision, entries])
        existing = state["candidates"].get(candidate_id)
        transition = self._begin("candidate.external_submit", actor_origin, {"candidate_id": candidate_id})
        if existing is not None:
            self._complete(
                transition,
                "semantic.candidate.proposed",
                candidate_id=candidate_id,
                parent_version_id=existing.get("parent_version_id"),
                source_id=source_id,
                source_revision=source_revision,
                meaning_count=len(entries),
                meaning_ids_sha256=_digest(_canonical(sorted({row["meaning_id"] for row in entries}))),
                actor_origin=actor_origin,
                status="no_op",
            )
            status = "no_op"
        else:
            candidate = {
                "candidate_id": candidate_id,
                "scope_id": self.wiki.scope_id,
                "source_id": source_id,
                "source_revision": source_revision,
                "parent_version_id": parent_id,
                "proposer_origin": actor_origin,
                "entries": entries,
                "status": "PROPOSED",
                "created_run_id": self.recorder.run_id,
                "latest_evaluation_id": None,
            }
            self._complete(
                transition,
                "semantic.candidate.proposed",
                changes=lambda mutable: mutable["candidates"].__setitem__(candidate_id, candidate),
                candidate_id=candidate_id,
                parent_version_id=parent_id,
                source_id=source_id,
                source_revision=source_revision,
                meaning_count=len(entries),
                meaning_ids_sha256=_digest(_canonical(sorted({row["meaning_id"] for row in entries}))),
                actor_origin=actor_origin,
                status="proposed",
            )
            for entry in entries:
                self._emit(
                    "semantic.candidate.evidence",
                    candidate_id=candidate_id,
                    meaning_id=entry["meaning_id"],
                    canonical_id=entry.get("canonical_id"),
                    source_id=entry["source_id"],
                    source_revision=entry["source_revision"],
                    line_start=entry["line_start"],
                    line_end=entry["line_end"],
                    span_sha256=entry["span_sha256"],
                    actor_origin=actor_origin,
                )
            status = "proposed"
        emit_external(
            "semantic.external.action",
            action="candidate_submitted",
            producer_origin=actor_origin,
            evidence_level="DIRECTLY_OBSERVED",
            source_id=source_id,
            source_revision=source_revision,
            submission_sha256=submission_digest,
            candidate_id=candidate_id,
            item_count=len(entries),
            internal_reasoning_status="NOT_OBSERVABLE",
            producer_usage_status="unknown",
            status="submitted" if status == "proposed" else "recorded",
        )
        return {
            "status": status,
            "producer_origin": actor_origin,
            "candidate_id": candidate_id,
            "source_id": source_id,
            "source_revision": source_revision,
            "meaning_ids": sorted({row["meaning_id"] for row in entries}),
            "meaning_count": len(entries),
        }

    def propose(self, path, *, actor_origin: str) -> dict[str, Any]:
        actor_origin = _actor(actor_origin)
        stage = self.wiki.stage_markdown(path)
        self._emit(
            "knowledge.source.staged",
            source_id=stage["source_id"],
            source_revision=stage["revision"],
            status=stage["status"],
            claim_count=stage["claim_count"],
        )
        snapshot = self.wiki.source_snapshot(stage["source_id"])
        source = snapshot["source"]
        claims = self.wiki.claim_history(stage["source_id"])
        current_claims = [claim for claim in claims if claim.get("revision") == stage["revision"]]
        entries = _entry_rows(snapshot["content"], source, current_claims)
        if not entries:
            raise SemanticTransitionError("no_supported_markers", "the source contains no supported semantic markers")
        state = self.wiki.semantic_state()
        parent_id = state["active_version_id"]
        parent = state["accepted_versions"].get(parent_id, {}) if parent_id else {}
        active_meanings = parent.get("meanings", {}) if isinstance(parent, dict) else {}
        parent_meanings = _relation_identity_history(state, active_meanings)
        _apply_explicit_alias_mappings(
            entries,
            source_content=snapshot["content"],
            active_meanings=active_meanings,
            scope_id=self.wiki.scope_id,
            source_id=stage["source_id"],
        )
        _assign_relation_identities(entries, scope_id=self.wiki.scope_id, parent_meanings=parent_meanings)
        candidate_id = _identity(
            "candidate",
            [self.wiki.scope_id, stage["source_id"], stage["revision"], entries],
        )
        existing = state["candidates"].get(candidate_id)
        if existing is not None:
            transition = self._begin("candidate.propose", actor_origin)
            self._complete(
                transition,
                "semantic.candidate.proposed",
                candidate_id=candidate_id,
                parent_version_id=existing.get("parent_version_id"),
                source_id=stage["source_id"],
                source_revision=stage["revision"],
                meaning_count=len(entries),
                meaning_ids_sha256=_digest(_canonical(sorted({row["meaning_id"] for row in entries}))),
                actor_origin=actor_origin,
                status="no_op",
            )
            return {"status": "no_op", "candidate_id": candidate_id, "source_id": stage["source_id"], "source_revision": stage["revision"], "meaning_ids": sorted({row["meaning_id"] for row in entries})}
        transition = self._begin("candidate.propose", actor_origin, {"candidate_id": candidate_id})
        candidate = {
            "candidate_id": candidate_id,
            "scope_id": self.wiki.scope_id,
            "source_id": stage["source_id"],
            "source_revision": stage["revision"],
            "parent_version_id": parent_id,
            "proposer_origin": actor_origin,
            "entries": entries,
            "status": "PROPOSED",
            "created_run_id": self.recorder.run_id,
            "latest_evaluation_id": None,
        }

        def add(state):
            state["candidates"][candidate_id] = candidate

        self._complete(
            transition,
            "semantic.candidate.proposed",
            changes=add,
            candidate_id=candidate_id,
            parent_version_id=parent_id,
            source_id=stage["source_id"],
            source_revision=stage["revision"],
            meaning_count=len(entries),
            meaning_ids_sha256=_digest(_canonical(sorted({row["meaning_id"] for row in entries}))),
            actor_origin=actor_origin,
            status="proposed",
        )
        for entry in entries:
            self._emit(
                "semantic.candidate.evidence",
                candidate_id=candidate_id,
                meaning_id=entry["meaning_id"],
                canonical_id=entry.get("canonical_id"),
                source_id=entry["source_id"],
                source_revision=entry["source_revision"],
                line_start=entry["line_start"],
                line_end=entry["line_end"],
                span_sha256=entry["span_sha256"],
                actor_origin=actor_origin,
            )
        return {"status": "proposed", "candidate_id": candidate_id, "source_id": stage["source_id"], "source_revision": stage["revision"], "meaning_ids": sorted({row["meaning_id"] for row in entries}), "meaning_count": len(entries)}

    def evaluate(self, candidate_id: str, *, actor_origin: str, evaluator_id: str = "structural-evaluator-v1") -> dict[str, Any]:
        actor_origin = _actor(actor_origin)
        if actor_origin != "independent_evaluator":
            raise SemanticTransitionError("evaluator_origin_required", "evaluation must use the independent_evaluator origin")
        state = self.wiki.semantic_state()
        candidate = self._candidate(state, candidate_id)
        findings: list[dict[str, Any]] = []
        try:
            snapshot = self.wiki.source_snapshot(candidate["source_id"])
            if snapshot["current_revision"] != candidate["source_revision"]:
                findings.append({"code": "source_revision_changed", "meaning_id": ""})
            lines = snapshot["content"].splitlines()
            for entry in candidate["entries"]:
                line = entry["line_start"]
                if not 1 <= line <= len(lines) or _digest(lines[line - 1].encode("utf-8")) != entry["span_sha256"]:
                    findings.append({"code": "evidence_anchor_mismatch", "meaning_id": entry["meaning_id"]})
        except WikiError:
            findings.append({"code": "source_unavailable", "meaning_id": ""})
        active = state["accepted_versions"].get(state["active_version_id"], {}) if state.get("active_version_id") else {}
        active_meanings = active.get("meanings", {}) if isinstance(active, dict) else {}
        known_canonical_ids = {
            row.get("canonical_id")
            for row in active_meanings.values()
            if isinstance(row.get("canonical_id"), str)
        }
        known_canonical_ids.update(
            entry.get("canonical_id")
            for entry in candidate["entries"]
            if entry.get("kind") == "entity" and isinstance(entry.get("canonical_id"), str)
        )
        candidate_relation_tuples = {
            _relation_tuple(entry)
            for entry in candidate["entries"]
            if entry.get("kind") == "relation"
        }
        candidate_relation_pairs = {(subject, predicate) for subject, predicate, _object in candidate_relation_tuples}
        candidate_meaning_ids = {str(entry.get("meaning_id")) for entry in candidate["entries"]}
        for prior in active_meanings.values():
            if prior.get("kind") != "relation":
                continue
            prior_tuple = _relation_tuple(prior)
            if prior_tuple in candidate_relation_tuples or prior_tuple[:2] not in candidate_relation_pairs:
                continue
            if str(prior.get("meaning_id")) in candidate_meaning_ids:
                continue
            prior_evidence = _meaning_evidence(prior)
            same_source_evidence = [row for row in prior_evidence if row.get("source_id") == candidate["source_id"]]
            if not same_source_evidence:
                findings.append({
                    "code": "relation_target_ambiguity",
                    "meaning_id": str(prior.get("meaning_id", "")),
                })
                continue
            reviewable = all(
                row.get("source_revision") != candidate["source_revision"]
                for row in prior_evidence
            ) and all(row.get("source_id") == candidate["source_id"] for row in prior_evidence)
            findings.append({
                "code": "active_meaning_conflict",
                "meaning_id": str(prior.get("meaning_id", "")),
                "reviewable_material_change": reviewable,
            })
        for entry in candidate["entries"]:
            prior = active_meanings.get(entry["meaning_id"])
            if prior and prior.get("meaning") != entry.get("meaning"):
                prior_evidence = _meaning_evidence(prior)
                reviewable = bool(prior_evidence) and all(
                    item.get("source_id") == candidate["source_id"]
                    and item.get("source_revision") != candidate["source_revision"]
                    for item in prior_evidence
                )
                findings.append({
                    "code": "active_meaning_conflict",
                    "meaning_id": entry["meaning_id"],
                    "reviewable_material_change": reviewable,
                })
            if prior and prior.get("canonical_id") != entry.get("canonical_id"):
                if prior.get("canonical_id") or entry.get("canonical_id"):
                    findings.append({"code": "active_identity_mapping_conflict", "meaning_id": entry["meaning_id"]})
            if entry.get("kind") == "alias" and entry.get("identity_basis") == "producer_key_only":
                findings.append({"code": "alias_mapping_evidence_missing", "meaning_id": entry["meaning_id"]})
            elif entry.get("kind") == "alias" and entry.get("canonical_id") not in known_canonical_ids:
                findings.append({"code": "canonical_identity_unresolved", "meaning_id": entry["meaning_id"]})
            if entry.get("kind") in {"entity", "alias"} and entry.get("identity_basis") == "producer_key_only":
                matching_active = [
                    row for row in active_meanings.values()
                    if row.get("kind") in {"entity", "alias"}
                    and row.get("canonical_key") == entry.get("canonical_key")
                    and row.get("source_id") != candidate["source_id"]
                ]
                if matching_active:
                    findings.append({
                        "code": "producer_entity_key_not_identity_evidence",
                        "meaning_id": entry["meaning_id"],
                    })
            for endpoint in (entry.get("canonical_subject_id"), entry.get("canonical_object_id")):
                if endpoint is not None and endpoint not in known_canonical_ids:
                    findings.append({"code": "canonical_relation_endpoint_unresolved", "meaning_id": entry["meaning_id"]})
        status = "pass" if not findings else "needs_review"
        evaluation_id = _identity("evaluation", [candidate_id, evaluator_id, findings, status])
        existing_evaluation = evaluation_id in state["evaluations"]
        transition = self._begin(
            "candidate.evaluate",
            actor_origin,
            {
                "evaluation_id": evaluation_id,
                "candidate_id": candidate_id,
                "created_evaluation": not existing_evaluation,
                "previous_evaluation_id": candidate.get("latest_evaluation_id"),
                "previous_candidate_status": candidate.get("status"),
            },
        )
        evaluation = {
            "evaluation_id": evaluation_id,
            "candidate_id": candidate_id,
            "evaluator_id": evaluator_id,
            "evaluation_type": "structural_validation",
            "actor_origin": actor_origin,
            "status": status,
            "findings": findings,
            "created_run_id": self.recorder.run_id,
        }

        def add(state):
            state["evaluations"][evaluation_id] = evaluation
            state["candidates"][candidate_id]["latest_evaluation_id"] = evaluation_id
            state["candidates"][candidate_id]["status"] = "EVALUATED" if status == "pass" else "NEEDS_REVIEW"

        self._complete(
            transition,
            "semantic.candidate.evaluated",
            changes=None if existing_evaluation else add,
            candidate_id=candidate_id,
            evaluation_id=evaluation_id,
            evaluator_id=evaluator_id,
            **self._v15_fields(evaluation_type="structural_validation"),
            status=status,
            source_id=candidate["source_id"],
            source_revision=candidate["source_revision"],
            finding_count=len(findings),
            finding_codes="|".join(sorted({str(item["code"]) for item in findings})),
            finding_ids_sha256=_digest(_canonical(sorted({str(item["meaning_id"]) for item in findings if item.get("meaning_id")}))),
            actor_origin=actor_origin,
        )
        return dict(evaluation)

    def record_external_evaluation_receipt(
        self,
        *,
        receipt: Mapping[str, Any],
        actor_origin: str,
    ) -> dict[str, Any]:
        """Record a separately signed semantic recommendation without granting authority."""
        actor_origin = _actor(actor_origin)
        if getattr(self.recorder, "event_schema_version", "1.4") != "1.5":
            raise SemanticTransitionError("event_schema_v15_required", "external semantic receipts require the additive R4 event schema 1.5")
        candidate_id = receipt.get("candidate_id") if isinstance(receipt, Mapping) else None
        state = self.wiki.semantic_state()
        candidate = self._candidate(state, candidate_id)
        structural_id = candidate.get("latest_evaluation_id")
        structural = state["evaluations"].get(structural_id) if structural_id else None
        if structural is None:
            raise SemanticTransitionError("structural_evaluation_required", "external semantic evaluation must follow recorded structural validation")
        if not isinstance(receipt, Mapping) or receipt.get("disposition") not in {"ACCEPT", "REVISE", "REJECT", "DEFER"}:
            raise SemanticTransitionError("semantic_receipt_disposition_invalid", "external semantic receipt requires a supported disposition")
        evaluator_id = receipt.get("evaluator_id")
        if not isinstance(evaluator_id, str) or not _SAFE_CODE.fullmatch(evaluator_id):
            raise SemanticTransitionError("semantic_receipt_evaluator_invalid", "external semantic receipt requires a stable evaluator identity")
        if evaluator_id == candidate.get("proposer_origin"):
            raise SemanticTransitionError("semantic_evaluator_not_independent", "the candidate producer cannot submit its own evaluation receipt")
        for field in ("rubric_sha256", "report_sha256", "finding_ids_sha256"):
            if not isinstance(receipt.get(field), str) or not _SHA256.fullmatch(receipt[field]):
                raise SemanticTransitionError("semantic_receipt_evidence_invalid", "external semantic receipt must bind its rubric, report, and findings digests")
        finding_count = receipt.get("finding_count")
        if type(finding_count) is not int or finding_count < 0:
            raise SemanticTransitionError("semantic_receipt_findings_invalid", "external semantic receipt finding count must be a non-negative integer")
        snapshot = self.wiki.source_snapshot(str(candidate["source_id"]))
        if snapshot["current_revision"] != candidate["source_revision"]:
            raise SemanticTransitionError("source_revision_changed", "candidate source revision changed before semantic evaluation was recorded")
        verified = self._verified_receipt(
            receipt,
            receipt_type="semantic_evaluation",
            candidate=candidate,
            allowed_authority_classes={"test_evaluator", "independent_evaluator"},
            expected={
                "disposition": receipt["disposition"],
                "evaluator_id": evaluator_id,
                "rubric_sha256": receipt["rubric_sha256"],
                "report_sha256": receipt["report_sha256"],
                "finding_count": finding_count,
                "finding_ids_sha256": receipt["finding_ids_sha256"],
            },
        )
        evaluation_id = _identity("external_evaluation", [verified["receipt_id"], candidate["candidate_id"]])
        existing = candidate.get("external_evaluations", {}).get(evaluation_id)
        transition = self._begin(
            "candidate.external_evaluation.record",
            actor_origin,
            {
                "candidate_id": candidate_id,
                "evaluation_id": evaluation_id,
                "created_external_evaluation": existing is None,
                "previous_external_evaluation_id": candidate.get("latest_external_evaluation_id"),
            },
        )
        evaluation = {
            "evaluation_id": evaluation_id,
            "candidate_id": candidate_id,
            "scope_id": self.wiki.scope_id,
            "source_id": candidate["source_id"],
            "source_revision": candidate["source_revision"],
            "candidate_sha256": verified["candidate_sha256"],
            "evaluator_id": evaluator_id,
            "issuer_id": verified["issuer_id"],
            "authority_class": verified["authority_class"],
            "disposition": receipt["disposition"],
            "rubric_sha256": receipt["rubric_sha256"],
            "report_sha256": receipt["report_sha256"],
            "finding_count": finding_count,
            "finding_ids_sha256": receipt["finding_ids_sha256"],
            "receipt_id": verified["receipt_id"],
            "receipt_sha256": verified["receipt_sha256"],
            "expires_at": verified["expires_at"],
            "created_run_id": self.recorder.run_id,
        }
        # An external review binds the package it read and who read it; both are signed.
        for optional in ("review_package_sha256", "evaluator_context"):
            if optional in verified:
                evaluation[optional] = verified[optional]

        def add(state):
            row = state["candidates"][candidate_id]
            row.setdefault("external_evaluations", {})[evaluation_id] = evaluation
            row["latest_external_evaluation_id"] = evaluation_id

        self._complete(
            transition,
            "semantic.candidate.external_evaluation.received",
            changes=None if existing is not None else add,
            candidate_id=candidate_id,
            source_id=candidate["source_id"],
            source_revision=candidate["source_revision"],
            evaluation_id=evaluation_id,
            evaluation_type="external_semantic_recommendation",
            evaluator_id=evaluator_id,
            recommendation=receipt["disposition"],
            authority_status="verified_recommendation_only",
            candidate_sha256=verified["candidate_sha256"],
            receipt_id=verified["receipt_id"],
            receipt_authority_class=verified["authority_class"],
            rubric_sha256=receipt["rubric_sha256"],
            report_sha256=receipt["report_sha256"],
            finding_count=finding_count,
            finding_ids_sha256=receipt["finding_ids_sha256"],
            internal_reasoning_status="NOT_OBSERVABLE",
            external_usage_status="unknown",
            actor_origin=actor_origin,
            status="no_op" if existing is not None else "recorded",
        )
        return {
            "status": "recorded",
            "candidate_id": candidate_id,
            "evaluation_id": evaluation_id,
            "disposition": receipt["disposition"],
            "authority_status": "verified_recommendation_only",
        }

    def decide(
        self,
        candidate_id: str,
        *,
        decision: str,
        actor_origin: str,
        reason_code: str,
        external_evaluation_id: str | None = None,
        authority_receipt: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        actor_origin = _actor(actor_origin)
        if decision not in {"ACCEPTED", "REJECTED", "DEFERRED", "NEEDS_REVIEW"}:
            raise SemanticTransitionError("invalid_decision", "decision is outside the R7 local review contract")
        if not _SAFE_CODE.fullmatch(reason_code):
            raise SemanticTransitionError("invalid_reason_code", "reason code must be a short non-sensitive token")
        state = self.wiki.semantic_state()
        candidate = self._candidate(state, candidate_id)
        if actor_origin == candidate["proposer_origin"]:
            raise SemanticTransitionError("self_approval_denied", "candidate proposer and manager decision origin must be separate")
        if decision == "ACCEPTED" and actor_origin != "manager_acceptance":
            raise SemanticTransitionError("manager_acceptance_required", "acceptance requires the manager acceptance operation label; the label alone is not authority")
        evaluation_id = candidate.get("latest_evaluation_id")
        evaluation = state["evaluations"].get(evaluation_id) if evaluation_id else None
        if evaluation is None:
            raise SemanticTransitionError("evaluation_required", "a candidate requires a recorded evaluation before review")
        if decision == "ACCEPTED":
            if evaluation.get("status") != "pass":
                findings = evaluation.get("findings", [])
                reviewed_change_only = bool(findings) and all(
                    finding.get("code") == "active_meaning_conflict"
                    and finding.get("reviewable_material_change") is True
                    for finding in findings
                )
                if reason_code != "reviewed_material_change" or not reviewed_change_only:
                    raise SemanticTransitionError(
                        "reviewed_material_change_required",
                        "a needs_review candidate cannot be accepted without the reviewed material change reason code and same-source evidence",
                    )
            fresh = self.wiki.source_snapshot(candidate["source_id"])
            if fresh["current_revision"] != candidate["source_revision"]:
                raise SemanticTransitionError("source_revision_changed", "candidate source revision changed before manager acceptance")
            external_evaluation_id = external_evaluation_id or candidate.get("latest_external_evaluation_id")
            external_evaluation = candidate.get("external_evaluations", {}).get(external_evaluation_id) if external_evaluation_id else None
            if external_evaluation is None:
                raise SemanticTransitionError("external_semantic_evaluation_required", "structural validation is not semantic support; a verified external semantic evaluation receipt is required")
            if external_evaluation.get("disposition") != "ACCEPT":
                raise SemanticTransitionError("external_semantic_evaluation_not_accept", "external semantic evaluation did not recommend acceptance")
            if external_evaluation.get("expires_at", 0) <= int(time.time()):
                raise SemanticTransitionError("external_semantic_evaluation_expired", "external semantic evaluation receipt has expired")
            if external_evaluation.get("candidate_sha256") != _candidate_content_digest(candidate):
                raise SemanticTransitionError("external_semantic_evaluation_stale", "external semantic evaluation no longer binds the current candidate")
            owner_basis = self._verified_receipt(
                authority_receipt,
                receipt_type="owner_authority",
                candidate=candidate,
                allowed_authority_classes={"test_only", "organization_owner"},
                expected={"action": "ACCEPT", "decision": "ACCEPTED"},
            )
            if getattr(self.recorder, "event_schema_version", "1.4") != "1.5":
                raise SemanticTransitionError("event_schema_v15_required", "accepted semantic versions require the additive R4 event schema 1.5")
        else:
            external_evaluation = candidate.get("external_evaluations", {}).get(external_evaluation_id) if external_evaluation_id else None
            owner_basis = None
        decision_id = _identity(
            "decision",
            [candidate_id, evaluation_id, external_evaluation_id, owner_basis and owner_basis["receipt_id"], decision, actor_origin, reason_code],
        )
        version_id = _identity("version", [self.wiki.scope_id, candidate_id, candidate.get("parent_version_id"), decision_id]) if decision == "ACCEPTED" else None
        existing_decision = decision_id in state["decisions"]
        created_version = version_id is not None and version_id not in state["accepted_versions"]
        transition = self._begin(
            "candidate.decide",
            actor_origin,
            {
                "decision_id": decision_id,
                "version_id": version_id,
                "candidate_id": candidate_id,
                "created_decision": not existing_decision,
                "created_version": created_version,
                "previous_latest_decision_id": candidate.get("latest_decision_id"),
                "previous_candidate_status": candidate.get("status"),
            },
        )
        decision_record = {
            "decision_id": decision_id,
            "candidate_id": candidate_id,
            "source_id": candidate["source_id"],
            "source_revision": candidate["source_revision"],
            "evaluation_id": evaluation_id,
            "external_evaluation_id": external_evaluation_id,
            "decision": decision,
            "actor_origin": actor_origin,
            "reason_code": reason_code,
            "owner_acceptance_basis": owner_basis,
            "created_run_id": self.recorder.run_id,
            "version_id": version_id,
        }

        def add(state):
            state["decisions"][decision_id] = decision_record
            state["candidates"][candidate_id]["latest_decision_id"] = decision_id
            state["candidates"][candidate_id]["status"] = decision
            if version_id:
                parent_id = candidate.get("parent_version_id")
                parent = state["accepted_versions"].get(parent_id, {}) if parent_id else {}
                carried = self._carry_confirmed_by_absence(parent.get("meanings", {}), candidate)
                meanings = _merge_candidate_meanings(
                    parent.get("meanings", {}), candidate, carried=carried)
                state["accepted_versions"][version_id] = {
                    "version_id": version_id,
                    "parent_version_id": parent_id,
                    "candidate_id": candidate_id,
                    "source_id": candidate["source_id"],
                    "source_revision": candidate["source_revision"],
                    "decision_id": decision_id,
                    "scope_id": self.wiki.scope_id,
                    "meanings": meanings,
                    "diff": _meaning_diff(parent.get("meanings", {}), meanings),
                    "confirmed_by_absence_count": len(carried),
                    "structural_evaluation_id": evaluation_id,
                    "external_evaluation_id": external_evaluation_id,
                    "owner_acceptance_basis": owner_basis,
                    "authority_class": owner_basis["authority_class"] if owner_basis else None,
                    "created_run_id": self.recorder.run_id,
                }

        self._complete(
            transition,
            "semantic.candidate.decided",
            changes=None if existing_decision else add,
            candidate_id=candidate_id,
            evaluation_id=evaluation_id,
            decision_id=decision_id,
            decision=decision,
            version_id=version_id,
            source_id=candidate["source_id"],
            source_revision=candidate["source_revision"],
            reason_code=reason_code,
            **self._v15_fields(
                external_evaluation_id=external_evaluation_id,
                authority_receipt_id=owner_basis["receipt_id"] if owner_basis else None,
                authority_class=owner_basis["authority_class"] if owner_basis else None,
                authority_issuer_id=owner_basis["issuer_id"] if owner_basis else None,
            ),
            actor_origin=actor_origin,
            status="no_op" if existing_decision else "recorded",
        )
        if version_id:
            self._emit(
                "semantic.version.accepted",
                transition_id=transition["transition_id"],
                candidate_id=candidate_id,
                decision_id=decision_id,
                **self._v15_fields(
                    external_evaluation_id=external_evaluation_id,
                    authority_receipt_id=owner_basis["receipt_id"] if owner_basis else None,
                    authority_class=owner_basis["authority_class"] if owner_basis else None,
                    authority_issuer_id=owner_basis["issuer_id"] if owner_basis else None,
                ),
                version_id=version_id,
                parent_version_id=candidate.get("parent_version_id"),
                source_id=candidate["source_id"],
                source_revision=candidate["source_revision"],
                meaning_count=len(candidate["entries"]),
                actor_origin=actor_origin,
                status="no_op" if existing_decision else "accepted",
            )
        return {"status": decision.lower(), "decision_id": decision_id, "version_id": version_id, "candidate_id": candidate_id}

    def activate(
        self,
        version_id: str,
        *,
        actor_origin: str,
        authority_receipt: Mapping[str, Any] | None = None,
        expected_head_version_id: str | None | object = _UNSET,
        allow_branch_switch: bool = False,
    ) -> dict[str, Any]:
        return self._set_active(
            version_id,
            actor_origin=actor_origin,
            authority_receipt=authority_receipt,
            rollback=False,
            expected_head_version_id=expected_head_version_id,
            allow_branch_switch=allow_branch_switch,
        )

    def rollback(
        self,
        version_id: str,
        *,
        actor_origin: str,
        authority_receipt: Mapping[str, Any] | None = None,
        expected_head_version_id: str | None | object = _UNSET,
    ) -> dict[str, Any]:
        return self._set_active(
            version_id,
            actor_origin=actor_origin,
            authority_receipt=authority_receipt,
            rollback=True,
            expected_head_version_id=expected_head_version_id,
            allow_branch_switch=True,
        )

    def _set_active(
        self,
        version_id: str,
        *,
        actor_origin: str,
        authority_receipt: Mapping[str, Any] | None,
        rollback: bool,
        expected_head_version_id: str | None | object = _UNSET,
        allow_branch_switch: bool = False,
    ) -> dict[str, Any]:
        actor_origin = _actor(actor_origin)
        state = self.wiki.semantic_state()
        if version_id not in state["accepted_versions"]:
            raise SemanticTransitionError("accepted_version_not_found", "activation target is not an accepted semantic version")
        previous = state.get("active_version_id")
        expected_head = previous if expected_head_version_id is _UNSET else expected_head_version_id
        if expected_head is not None and not isinstance(expected_head, str):
            raise SemanticTransitionError("invalid_expected_head", "expected semantic head must be a version ID or null")
        if expected_head != previous:
            raise SemanticTransitionError("expected_head_mismatch", "active semantic head differs from the caller's expected head")
        operation = "version.rollback" if rollback else "version.activate"
        event_type = "semantic.version.rolled_back" if rollback else "semantic.version.activated"
        accepted_version = state["accepted_versions"][version_id]
        candidate = self._candidate(state, str(accepted_version["candidate_id"]))
        action = "ROLLBACK" if rollback else "ACTIVATE"
        owner_basis = self._verified_receipt(
            authority_receipt,
            receipt_type="version_authority",
            candidate=candidate,
            allowed_authority_classes={"test_only", "organization_owner"},
            expected={
                "action": action,
                "version_id": version_id,
                "expected_head_version_id": expected_head,
            },
        )
        if getattr(self.recorder, "event_schema_version", "1.4") != "1.5":
            raise SemanticTransitionError("event_schema_v15_required", "authorized version changes require the additive R4 event schema 1.5")
        parent_id = accepted_version.get("parent_version_id")
        branch_switch = bool(not rollback and version_id != previous and parent_id != expected_head)
        if branch_switch and not allow_branch_switch:
            raise SemanticTransitionError(
                "sibling_head_conflict",
                "accepted version is on a sibling branch; explicitly reconcile or request a branch switch",
            )
        transition = self._begin(
            operation,
            actor_origin,
            {
                "previous_version_id": previous,
                "target_version_id": version_id,
                "expected_head_version_id": expected_head,
            },
        )

        def set_pointer(state):
            if state.get("active_version_id") != expected_head:
                raise SemanticTransitionError("expected_head_mismatch", "active semantic head changed during pointer update")
            state["active_version_id"] = version_id

        self._complete(
            transition,
            event_type,
            changes=set_pointer,
            candidate_id=accepted_version["candidate_id"],
            source_id=accepted_version["source_id"],
            source_revision=accepted_version["source_revision"],
            version_id=version_id,
            active_version_id=version_id,
            from_version_id=previous,
            to_version_id=version_id,
            expected_head_version_id=expected_head,
            branch_switch=branch_switch,
            **self._v15_fields(
                authority_receipt_id=owner_basis["receipt_id"],
                authority_class=owner_basis["authority_class"],
                authority_issuer_id=owner_basis["issuer_id"],
            ),
            status="active",
            actor_origin=actor_origin,
        )
        return {
            "status": "active",
            "active_version_id": version_id,
            "previous_version_id": previous,
            "expected_head_version_id": expected_head,
            "branch_switch": branch_switch,
        }

    def _carry_confirmed_by_absence(
        self, parent_meanings: Mapping[str, Mapping[str, Any]], candidate: Mapping[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Meanings this source still states that the candidate never mentioned.

        A re-reading that models part of a document must not delete the rest of what that
        document says. An unmentioned meaning is carried only when its own line is still in
        the accepted revision, byte for byte: then the text keeps it, not the model's silence.
        When the line is gone the document really dropped it, and it is not carried.
        """
        source_id = str(candidate["source_id"])
        revision = str(candidate["source_revision"])
        mentioned = {str(entry.get("meaning_id")) for entry in candidate.get("entries") or []}
        try:
            content = str(self.wiki.source_snapshot(source_id).get("content") or "")
        except Exception:
            return {}
        index = line_index(content)
        carried: dict[str, dict[str, Any]] = {}
        for meaning_id, prior in parent_meanings.items():
            if str(meaning_id) in mentioned:
                continue
            rows = _meaning_evidence(prior)
            own = [row for row in rows if row.get("source_id") == source_id]
            if not own:
                continue
            rewritten: list[dict[str, Any]] = []
            intact = True
            for row in own:
                start = row.get("line_start")
                span = row.get("span_sha256")
                if not isinstance(span, str):
                    # Nothing to check the text against: only a row written at the accepted
                    # revision itself may be trusted as still there.
                    if row.get("source_revision") == revision and isinstance(start, int):
                        rewritten.append(dict(row))
                        continue
                    intact = False
                    break
                candidates = index.get(span)
                if not isinstance(start, int) or not candidates:
                    intact = False
                    break
                # The line is checked even when the revision matches: a file edited on disk
                # without being re-staged must not be carried on trust.
                nearest = start if start in candidates else min(
                    candidates, key=lambda number: (abs(number - start), number))
                end = row.get("line_end")
                # The evidence contract has a fixed field set, so the move is expressed as
                # the new line and revision; that a meaning was carried at all is recorded on
                # the meaning (confirmed_by_absence).
                rewritten.append({
                    **dict(row),
                    "source_revision": revision,
                    "line_start": nearest,
                    "line_end": (end if isinstance(end, int) else start) + (nearest - start),
                })
            if not intact:
                continue
            others = [row for row in rows if row.get("source_id") != source_id]
            carried[str(meaning_id)] = {
                **_with_evidence(prior, [*others, *rewritten]),
                "confirmed_by_absence": True,
                "confirmed_at_source_revision": revision,
            }
        return carried

    def accepted_version_diff(self, version_id: str) -> dict[str, Any]:
        """What one accepted version changed, read instead of recomputed.

        The version keeps the comparison it was accepted with, so what a reader sees now is
        what the reviewer approved - not a second reading of a candidate whose source may
        have moved on since. A version accepted before diffs were kept is compared on read
        from its own meanings and its parent's, and says so.
        """
        state = self.wiki.semantic_state()
        version = state["accepted_versions"].get(version_id)
        if not isinstance(version, Mapping):
            raise SemanticTransitionError("accepted_version_not_found",
                                          "the version to compare is not an accepted semantic version")
        parent = state["accepted_versions"].get(version.get("parent_version_id"), {})
        stored = version.get("diff")
        if isinstance(stored, Mapping):
            return {
                "status": "read",
                "source": "stored",
                "version_id": version_id,
                "parent_version_id": version.get("parent_version_id"),
                "candidate_id": version.get("candidate_id"),
                **{key: list(value) for key, value in stored.items() if isinstance(value, list)},
            }
        return {
            "status": "read",
            "source": "computed",
            "version_id": version_id,
            "parent_version_id": version.get("parent_version_id"),
            "candidate_id": version.get("candidate_id"),
            **_meaning_diff(parent.get("meanings", {}), version.get("meanings", {})),
        }

    def diff(self, candidate_id: str, *, actor_origin: str) -> dict[str, Any]:
        actor_origin = _actor(actor_origin)
        state = self.wiki.semantic_state()
        candidate = self._candidate(state, candidate_id)
        parent = state["accepted_versions"].get(candidate.get("parent_version_id"), {}) if candidate.get("parent_version_id") else {}
        old = parent.get("meanings", {})
        projected = _merge_candidate_meanings(
            old, candidate, carried=self._carry_confirmed_by_absence(old, candidate))
        compared = _meaning_diff(old, projected)
        added = compared["added_meaning_ids"]
        removed = compared["removed_meaning_ids"]
        changed = compared["changed_meaning_ids"]
        evidence_added = compared["evidence_added_meaning_ids"]
        evidence_removed = compared["evidence_removed_meaning_ids"]
        transition = self._begin("version.diff", actor_origin)
        self._complete(
            transition,
            "semantic.version.diffed",
            candidate_id=candidate_id,
            parent_version_id=candidate.get("parent_version_id"),
            source_id=candidate["source_id"],
            source_revision=candidate["source_revision"],
            added_count=len(added),
            changed_count=len(changed),
            removed_count=len(removed),
            evidence_added_count=len(evidence_added),
            evidence_removed_count=len(evidence_removed),
            status="compared",
            actor_origin=actor_origin,
        )
        return {
            "status": "compared",
            "candidate_id": candidate_id,
            "parent_version_id": candidate.get("parent_version_id"),
            "added_meaning_ids": added,
            "changed_meaning_ids": changed,
            "removed_meaning_ids": removed,
            "evidence_added_meaning_ids": evidence_added,
            "evidence_removed_meaning_ids": evidence_removed,
        }

    def _resolve(self, query: str) -> tuple[str | None, list[dict[str, Any]]]:
        if not isinstance(query, str) or not query.strip():
            raise SemanticTransitionError("empty_query", "semantic query must be non-empty")
        state = self.wiki.semantic_state()
        version_id = state.get("active_version_id")
        version = state["accepted_versions"].get(version_id, {}) if version_id else {}
        query_terms = _wiki_tokens(query)
        rows = []
        for row in version.get("meanings", {}).values():
            terms = _wiki_tokens(f"{row.get('meaning', '')} {row.get('key', '')} {row.get('heading') or ''} {row.get('kind', '')}")
            if query_terms & terms:
                rows.append(dict(row))
        rows.sort(key=lambda row: (row["line_start"], row["meaning_id"]))
        return version_id, rows

    def query(self, query: str, *, actor_origin: str) -> dict[str, Any]:
        return self.ontology_projection(query, actor_origin=actor_origin)

    def read_knowledge(
        self,
        query: str,
        *,
        mode: str,
        actor_origin: str,
        capabilities=(),
        limit: int = 8,
        version_id: str | None = None,
        expand_relations_for: str | None = None,
        include_all_active: bool = False,
        consumer_read_mode: str | None = None,
        about: str | None = None,
    ) -> dict[str, Any]:
        """Expose the single ProjectWiki read contract and record its evidence in R4."""
        actor_origin = _actor(actor_origin)
        result = self.wiki.read_knowledge(
            query,
            mode=mode,
            capabilities=capabilities,
            limit=limit,
            version_id=version_id,
            expand_relations_for=expand_relations_for,
            include_all_active=include_all_active,
            about=about,
        )
        self._record_consumer_read(
            result,
            query=query,
            read_mode=consumer_read_mode or mode,
            actor_origin=actor_origin,
        )
        return result

    def _record_consumer_read(
        self,
        result: Mapping[str, Any],
        *,
        query: str,
        read_mode: str,
        actor_origin: str,
    ) -> None:
        if read_mode not in {
            "source_discovery",
            "grounded_claims",
            "accepted_enterprise_semantics",
            "relation_expansion",
            "ontology_graph",
        }:
            raise SemanticTransitionError("invalid_consumer_read_mode", "consumer read mode is outside the bounded Wiki contract")
        meaning_ids = list(result.get("meaning_ids", []))
        document_ids = sorted({row["document_id"] for row in result.get("documents", [])})
        claim_ids = sorted({row["claim_id"] for row in [*result.get("claims", []), *result.get("stale_claims", [])]})
        stale_meaning_count = sum(row.get("freshness_status") != "fresh" for row in result.get("meanings", []))
        self._emit(
            "semantic.consumer.queried",
            read_mode=read_mode,
            version_id=result.get("version_id"),
            active_version_id=result.get("active_version_id"),
            query_sha256=_digest(query.encode("utf-8")),
            meaning_count=len(meaning_ids),
            meaning_ids_sha256=_digest(_canonical(meaning_ids)),
            document_count=len(document_ids),
            document_ids_sha256=_digest(_canonical(document_ids)),
            claim_count=len(claim_ids),
            claim_ids_sha256=_digest(_canonical(claim_ids)),
            stale_meaning_count=stale_meaning_count,
            freshness_status=result["freshness_status"],
            knowledge_status=result["knowledge_status"],
            status=result["knowledge_status"],
            actor_origin=actor_origin,
        )
        record_consumption(
            self.wiki.workspace,
            query=query,
            result=result,
            read_mode=read_mode,
            actor_origin=actor_origin,
            run_id=self.recorder.run_id,
        )
        for document in result.get("documents", []):
            self._emit(
                "knowledge.document.discovered",
                read_mode=read_mode,
                document_id=document["document_id"],
                source_id=document["source_id"],
                source_revision=document.get("source_revision"),
                current_revision=document.get("current_revision"),
                revision_status=document.get("revision_status"),
                freshness_status=document.get("freshness_status"),
                status=document.get("knowledge_status"),
                actor_origin=actor_origin,
            )
        for claim in [*result.get("claims", []), *result.get("stale_claims", [])]:
            event_fields = {
                "read_mode": read_mode,
                "scope_id": self.wiki.scope_id,
                "claim_id": claim["claim_id"],
                "source_id": claim["source_id"],
                "source_revision": claim["revision"],
                "claim_status": claim.get("status"),
                "freshness_status": claim.get("freshness_status"),
                "authority": claim.get("authority"),
            }
            for field in ("line_start", "line_end", "span_sha256", "capability_id", "capability_version"):
                if claim.get(field) is not None:
                    event_fields[field] = claim[field]
            self.recorder.event("knowledge.claim.retrieved", **event_fields)
        for capability in result.get("capabilities", []):
            self.recorder.event(
                "knowledge.claim.retrieved",
                read_mode=read_mode,
                scope_id=self.wiki.scope_id,
                claim_id=capability["claim_id"],
                source_id=capability["source_id"],
                source_revision=capability["revision"],
                claim_status=capability.get("status"),
                freshness_status=capability.get("freshness_status"),
                authority=capability.get("authority"),
                capability_id=capability["capability_id"],
                capability_version=capability["capability_version"],
            )
        for row in result.get("meanings", []):
            for evidence in row.get("evidence", []):
                self._emit(
                    "semantic.consumer.meaning_consumed",
                    version_id=result.get("version_id"),
                    meaning_id=row["meaning_id"],
                    canonical_id=row.get("canonical_id"),
                    source_id=evidence["source_id"],
                    source_revision=evidence["source_revision"],
                    claim_id=evidence.get("claim_id"),
                    line_start=evidence["line_start"],
                    line_end=evidence["line_end"],
                    span_sha256=evidence["span_sha256"],
                    freshness_status=evidence.get("freshness_status"),
                    actor_origin=actor_origin,
                    status=evidence.get("freshness_status", "unknown"),
                )

    def resolve_relations(
        self,
        query: str,
        *,
        actor_origin: str,
        version_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Resolve an exact active entity label/key, then expand one outgoing relation hop."""
        actor_origin = _actor(actor_origin)
        if not isinstance(query, str) or not query.strip():
            raise SemanticTransitionError("empty_query", "entity query must be non-empty")
        if type(limit) is not int or limit < 1 or limit > 100:
            raise SemanticTransitionError("invalid_limit", "relation expansion limit must be between 1 and 100")

        base = self.wiki.read_knowledge(
            query,
            mode="accepted_enterprise_semantics",
            version_id=version_id,
        )
        normalized_query = _norm(query)
        entity_rows = [
            row
            for row in base["meanings"]
            if row.get("kind") in {"entity", "alias"}
            and normalized_query in {
                _norm(str(row.get("meaning", ""))),
                _norm(str(row.get("key", ""))),
                _norm(str(row.get("canonical_key", ""))),
            }
            and isinstance(row.get("canonical_id"), str)
        ]
        entity_ids = sorted({str(row["canonical_id"]) for row in entity_rows})
        if len(entity_ids) != 1:
            self._record_consumer_read(
                base,
                query=query,
                read_mode="relation_expansion",
                actor_origin=actor_origin,
            )
            status = "unknown" if not entity_ids else "ambiguous"
            return {
                "contract_version": 1,
                "scope_id": base["scope_id"],
                "authority": base["authority"],
                "status": status,
                "query": query,
                "version_id": base["version_id"],
                "active_version_id": base["active_version_id"],
                "entities": [],
                "relations": [],
                "unlinked_applicability": [],
                "applicability_status": "unknown",
                "knowledge_status": base["knowledge_status"],
                "freshness_status": base["freshness_status"],
                "warnings": ["entity_identity_unresolved" if not entity_ids else "entity_identity_ambiguous"],
                "truncated": False,
                "causal_influence_proven": False,
            }

        entity_id = entity_ids[0]
        result = self.wiki.read_knowledge(
            query,
            mode="accepted_enterprise_semantics",
            version_id=version_id,
            expand_relations_for=entity_id,
            limit=limit,
        )
        relation_rows = [row for row in result["meanings"] if row.get("kind") == "relation"]
        related_source_ids = {
            str(evidence.get("source_id"))
            for row in relation_rows
            for evidence in row.get("evidence", [])
            if isinstance(evidence.get("source_id"), str)
        }
        unlinked_rows: list[dict[str, Any]] = []
        if related_source_ids:
            all_active = self.wiki.read_knowledge(
                query,
                mode="accepted_enterprise_semantics",
                version_id=result["version_id"],
                include_all_active=True,
                limit=100,
            )
            for row in all_active["meanings"]:
                if row.get("kind") not in {"condition", "exception"}:
                    continue
                if row.get("relation_meaning_id") or row.get("applies_to_relation_id"):
                    continue
                if any(str(evidence.get("source_id")) in related_source_ids for evidence in row.get("evidence", [])):
                    unlinked_rows.append(row)

        meanings_by_id = {row["meaning_id"]: row for row in result["meanings"]}
        for row in unlinked_rows:
            meanings_by_id.setdefault(row["meaning_id"], row)
        result["meanings"] = sorted(meanings_by_id.values(), key=lambda row: (row.get("line_start", 0), row["meaning_id"]))
        result["meaning_ids"] = sorted(meanings_by_id)
        result["meaning_count"] = len(result["meanings"])
        evidence_freshness = [
            evidence.get("freshness_status", "unknown")
            for row in result["meanings"]
            for evidence in row.get("evidence", [])
        ]
        result["freshness_status"] = self.wiki._aggregate_freshness(evidence_freshness)
        result["knowledge_status"] = "needs_reconciliation" if result["freshness_status"] != "fresh" else "current"
        entity_by_id = {
            str(row.get("canonical_id")): row
            for row in result["meanings"]
            if row.get("kind") == "entity" and isinstance(row.get("canonical_id"), str)
        }
        for row in all_active["meanings"] if related_source_ids else []:
            if row.get("kind") == "entity" and isinstance(row.get("canonical_id"), str):
                entity_by_id.setdefault(str(row["canonical_id"]), row)
        relations = []
        for row in relation_rows:
            object_id = row.get("canonical_object_id")
            object_row = entity_by_id.get(str(object_id)) if object_id else None
            relations.append({
                "meaning_id": row["meaning_id"],
                "subject_id": row.get("canonical_subject_id"),
                "predicate": row.get("predicate"),
                "object_id": object_id,
                "object_label": object_row.get("meaning") if object_row else row.get("object"),
                "endpoint_status": "resolved" if object_row else "unresolved",
                "identity_status": row.get("canonical_identity_status", "proposed_unverified"),
                "freshness_status": row.get("freshness_status", "unknown"),
                "evidence": row.get("evidence", []),
            })
        warnings = []
        if unlinked_rows:
            warnings.append("condition_exception_linkage_unavailable")
        if any(row["endpoint_status"] != "resolved" for row in relations):
            warnings.append("relation_endpoint_unresolved")
        if result["freshness_status"] != "fresh":
            warnings.append("stale_source_evidence")
        if result.get("truncated"):
            warnings.append("relation_expansion_truncated")
        entity_summaries = [
            {
                "meaning_id": row["meaning_id"],
                "canonical_id": row["canonical_id"],
                "label": row.get("meaning"),
                "identity_status": row.get("canonical_identity_status", "proposed_unverified"),
                "freshness_status": row.get("freshness_status", "unknown"),
                "evidence": row.get("evidence", []),
            }
            for row in entity_rows
            if row.get("canonical_id") == entity_id
        ]
        self._record_consumer_read(
            result,
            query=query,
            read_mode="relation_expansion",
            actor_origin=actor_origin,
        )
        return {
            "contract_version": 1,
            "scope_id": result["scope_id"],
            "authority": result["authority"],
            "status": "resolved",
            "query": query,
            "version_id": result["version_id"],
            "active_version_id": result["active_version_id"],
            "entities": entity_summaries,
            "relations": relations,
            "unlinked_applicability": [
                {
                    "meaning_id": row["meaning_id"],
                    "kind": row["kind"],
                    "meaning": row["meaning"],
                    "freshness_status": row["freshness_status"],
                    "evidence": row["evidence"],
                    "applies_to_relation_id": None,
                }
                for row in unlinked_rows
            ],
            "applicability_status": "unknown",
            "knowledge_status": result["knowledge_status"],
            "freshness_status": result["freshness_status"],
            "warnings": warnings,
            "truncated": result.get("truncated", False),
            "causal_influence_proven": False,
        }

    def ontology_graph(
        self,
        *,
        actor_origin: str,
        version_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Return a bounded graph projection from one accepted ProjectWiki version."""
        actor_origin = _actor(actor_origin)
        if type(limit) is not int or limit < 1 or limit > 100:
            raise SemanticTransitionError("invalid_limit", "ontology graph limit must be between 1 and 100")
        query = "ontology_graph"
        result = self.wiki.read_knowledge(
            query,
            mode="accepted_enterprise_semantics",
            version_id=version_id,
            include_all_active=True,
            limit=limit,
        )
        self._record_consumer_read(result, query=query, read_mode="ontology_graph", actor_origin=actor_origin)

        meanings = result["meanings"]
        entity_rows = [row for row in meanings if row.get("kind") == "entity"]
        entity_nodes: dict[str, dict[str, Any]] = {}
        meaning_nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        source_index: dict[tuple[str, str], dict[str, Any]] = {}
        warnings: list[str] = []
        if not result.get("version_id"):
            warnings.append("active_version_unknown")
        for row in meanings:
            meaning_id = str(row["meaning_id"])
            meaning_node_id = f"meaning:{meaning_id}"
            evidence_ids = []
            for evidence in row.get("evidence", []):
                source_id = str(evidence.get("source_id", ""))
                source_revision = str(evidence.get("source_revision", ""))
                evidence_payload = {
                    "source_id": source_id,
                    "source_revision": source_revision,
                    "line_start": evidence.get("line_start"),
                    "line_end": evidence.get("line_end"),
                    "span_sha256": evidence.get("span_sha256"),
                    "freshness_status": evidence.get("freshness_status", "unknown"),
                }
                evidence_id = _identity("evidence", evidence_payload)
                evidence_ids.append(evidence_id)
                key = (source_id, source_revision)
                index_row = source_index.setdefault(key, {"source_id": source_id, "source_revision": source_revision, "evidence": []})
                index_row["evidence"].append({"evidence_id": evidence_id, **evidence_payload})
                source_node_id = f"source:{source_id}@{source_revision}"
                meaning_node = meaning_nodes.setdefault(meaning_node_id, {
                    "id": meaning_node_id,
                    "type": "meaning",
                    "kind": row.get("kind"),
                    "key": row.get("key"),
                    "label": row.get("meaning"),
                    "canonical_id": row.get("canonical_id"),
                    "canonical_identity_status": row.get("canonical_identity_status"),
                    "freshness_status": row.get("freshness_status", "unknown"),
                    "evidence_ids": [],
                })
                meaning_node["evidence_ids"].append(evidence_id)
                edges.append({
                    "id": f"evidence:{evidence_id}",
                    "type": "supported_by",
                    "source": source_node_id,
                    "target": meaning_node_id,
                    "evidence_id": evidence_id,
                })
                if evidence.get("freshness_status") != "fresh":
                    warnings.append("stale_source_evidence")
            if row.get("kind") == "entity" and isinstance(row.get("canonical_id"), str):
                entity_id = str(row["canonical_id"])
                entity_nodes.setdefault(entity_id, {
                    "id": f"entity:{entity_id}",
                    "type": "entity",
                    "canonical_id": entity_id,
                    "label": row.get("meaning"),
                    "identity_status": row.get("canonical_identity_status", "proposed_unverified"),
                    "meaning_ids": [],
                })["meaning_ids"].append(meaning_id)
        for row in meanings:
            if row.get("kind") == "alias":
                alias_id = row.get("canonical_id")
                if isinstance(alias_id, str) and alias_id in entity_nodes:
                    edges.append({
                        "id": f"alias:{row['meaning_id']}",
                        "type": "alias_of",
                        "source": f"meaning:{row['meaning_id']}",
                        "target": entity_nodes[alias_id]["id"],
                        "meaning_id": row["meaning_id"],
                    })
            if row.get("kind") == "relation":
                subject_id = row.get("canonical_subject_id")
                object_id = row.get("canonical_object_id")
                if isinstance(subject_id, str) and isinstance(object_id, str) and subject_id in entity_nodes and object_id in entity_nodes:
                    edges.append({
                        "id": f"relation:{row['meaning_id']}",
                        "type": "relation",
                        "source": entity_nodes[subject_id]["id"],
                        "target": entity_nodes[object_id]["id"],
                        "predicate": row.get("predicate"),
                        "meaning_id": row["meaning_id"],
                        "evidence_ids": sorted({
                            _identity("evidence", {
                                "source_id": evidence.get("source_id"),
                                "source_revision": evidence.get("source_revision"),
                                "line_start": evidence.get("line_start"),
                                "line_end": evidence.get("line_end"),
                                "span_sha256": evidence.get("span_sha256"),
                                "freshness_status": evidence.get("freshness_status", "unknown"),
                            })
                            for evidence in row.get("evidence", [])
                        }),
                    })
                else:
                    warnings.append(f"relation_endpoint_unresolved:{row['meaning_id']}")
            if row.get("kind") in {"condition", "exception"} and not (row.get("relation_meaning_id") or row.get("applies_to_relation_id")):
                warnings.append("condition_exception_linkage_unavailable")
        nodes = [*entity_nodes.values(), *meaning_nodes.values()]
        for (source_id, source_revision), source_row in source_index.items():
            nodes.append({
                "id": f"source:{source_id}@{source_revision}",
                "type": "source_revision",
                "source_id": source_id,
                "source_revision": source_revision,
            })
            source_row["evidence"].sort(key=lambda item: (item["line_start"] or 0, item["evidence_id"]))
        nodes.sort(key=lambda row: (row["type"], row["id"]))
        edges.sort(key=lambda row: (row["type"], row["id"]))
        freshness_values = [row.get("freshness_status", "unknown") for row in meanings]
        freshness_status = self.wiki._aggregate_freshness(freshness_values)
        if result.get("truncated"):
            warnings.append("graph_truncated")
        return {
            "schema": "catalyst.ontology_graph.v0.1",
            "scope_id": result["scope_id"],
            "authority": result["authority"],
            "version_id": result["version_id"],
            "active_version_id": result["active_version_id"],
            "knowledge_status": result["knowledge_status"],
            "freshness_status": freshness_status,
            "nodes": nodes,
            "edges": edges,
            "source_index": [source_index[key] for key in sorted(source_index)],
            "warnings": sorted(set(warnings)),
            "truncated": result.get("truncated", False),
            "candidate_meanings_included": False,
            "causal_influence_proven": False,
        }

    def ontology_projection(self, query: str, *, actor_origin: str) -> dict[str, Any]:
        return self.read_knowledge(
            query,
            mode="accepted_enterprise_semantics",
            actor_origin=actor_origin,
        )

    def wiki_projection(self, query: str, *, actor_origin: str) -> dict[str, Any]:
        result = self.ontology_projection(query, actor_origin=actor_origin)
        lines = [
            f"# Semantic Wiki — {self.wiki.scope_id}",
            "",
            f"Active semantic version: `{result['version_id'] or 'UNKNOWN'}`",
            f"Knowledge status: `{result['knowledge_status']}`; freshness: `{result['freshness_status']}`.",
            "",
        ]
        if not result["meanings"]:
            lines.append("UNKNOWN: no matching accepted meaning is active.")
        for row in result["meanings"]:
            refs = "; ".join(
                f"source `{evidence['source_id']}` revision `{evidence['source_revision']}` line {evidence['line_start']} ({evidence.get('freshness_status', 'unknown')})"
                for evidence in row.get("evidence", [])
            )
            lines.append(
                f"- **{row['kind']}** {row['meaning']} [{row.get('freshness_status', 'unknown')}] "
                f"(meaning `{row['meaning_id']}`; canonical `{row.get('canonical_id') or 'unmapped'}`; evidence: {refs})"
            )
        return {**result, "wiki_markdown": "\n".join(lines), "causal_influence_proven": False}

    def inspect(self, *, actor_origin: str) -> dict[str, Any]:
        _actor(actor_origin)
        state = self.wiki.semantic_state()
        active_version = state["accepted_versions"].get(state["active_version_id"], {}) if state["active_version_id"] else {}
        candidate_ids = sorted(state["candidates"])
        accepted_version_ids = sorted(state["accepted_versions"])
        active_meaning_ids = sorted(active_version.get("meanings", {}))
        summary = {
            "scope_id": self.wiki.scope_id,
            "active_version_id": state["active_version_id"],
            "candidate_count": len(candidate_ids),
            "candidate_ids": candidate_ids,
            "accepted_version_ids": accepted_version_ids,
            "active_meaning_ids": active_meaning_ids,
            "pending_transition_ids": sorted(row["transition_id"] for row in state["transitions"] if row.get("status") in {"started", "pending_completion", "awaiting_terminal"}),
        }
        transition = self._begin("semantic.inspect", actor_origin)
        self._complete(
            transition,
            "semantic.state.inspected",
            version_id=summary["active_version_id"],
            candidate_count=len(candidate_ids),
            candidate_ids_sha256=_digest(_canonical(candidate_ids)),
            accepted_version_count=len(accepted_version_ids),
            accepted_version_ids_sha256=_digest(_canonical(accepted_version_ids)),
            meaning_count=len(active_meaning_ids),
            meaning_ids_sha256=_digest(_canonical(active_meaning_ids)),
            status="success",
            actor_origin=actor_origin,
        )
        return summary

    @staticmethod
    def _candidate(state: dict[str, Any], candidate_id: str) -> dict[str, Any]:
        candidate = state["candidates"].get(candidate_id)
        if not isinstance(candidate, dict):
            raise SemanticTransitionError("candidate_not_found", "semantic candidate was not found in this scope")
        if candidate.get("candidate_type") == "understand_handoff.v1":
            raise SemanticTransitionError(
                "candidate_requires_mapping",
                "Understand handoffs remain candidate-only until an explicit semantic mapping contract exists",
            )
        return candidate

