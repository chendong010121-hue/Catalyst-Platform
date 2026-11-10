"""Shared result vocabulary: the request/result objects, the evidence and item shapes, the
exceptions the port raises, and the small derivations over them.

Both directions of work -- decoding an artifact into parts, and reading meaning out of
evidence -- import from here and neither owns it.  That is deliberate: a new field on a
result or a new exception is a change to the shared contract, not to one side's logic.
"""

from __future__ import annotations

import hashlib

from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class UnderstandIntent(str, Enum):
    TASK_USE = "TASK_USE"
    KNOWLEDGE_PROPOSE = "KNOWLEDGE_PROPOSE"
    ASSET_INSPECT = "ASSET_INSPECT"

class ResultStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    NEEDS_CONTEXT = "NEEDS_CONTEXT"
    DENIED = "DENIED"
    UNSUPPORTED = "UNSUPPORTED"

@dataclass(frozen=True)
class IntentRoute:
    intent: UnderstandIntent
    target: str
    reason: str
    requested_depth: str = "targeted_structural"
    budget_steps: int = 4
    stopping_reason: str = "bounded_default"

@dataclass(frozen=True)
class UnderstandingRequest:
    request_id: str
    message: str
    source_refs: tuple[Path | str, ...] = ()
    intent: UnderstandIntent | str | None = None
    scope_id: str | None = None
    requested_depth: str = "targeted_structural"
    budget_steps: int = 4
    actor_context: Mapping[str, Any] | None = None
    # Bounded revision: findings from a refused answer, as rule slugs and item keys.
    revision: Mapping[str, Any] | None = None

@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    relative_path: str
    media_type: str
    source_revision: str
    source_sha256: str
    byte_size: int
    extracted_text_sha256: str
    locator_count: int
    extraction_status: str = "COMPLETE"

@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    source_id: str
    relative_path: str
    source_revision: str
    source_sha256: str
    locator: str
    quote: str
    span_sha256: str
    evidence_class: str = "observed_from_source"

@dataclass(frozen=True)
class EvidenceExpansionRequest:
    """A bounded request to find additional evidence in already inventoried sources."""

    request_id: str
    query: str
    allowed_source_ids: tuple[str, ...]
    known_evidence_ids: tuple[str, ...] = ()
    locator_hints: tuple[str, ...] = ()
    max_steps: int = 4
    max_additional_refs: int = 8
    max_bytes: int = 512 * 1024

@dataclass(frozen=True)
class EvidenceExpansionResult:
    request_id: str
    status: str
    map_status: str
    evidence_refs: tuple[EvidenceRef, ...] = ()
    source_ids_scanned: tuple[str, ...] = ()
    steps_used: int = 0
    bytes_read: int = 0
    remaining_steps: int = 0
    remaining_refs: int = 0
    remaining_bytes: int = 0
    stopping_reason: str = "no_matching_evidence"

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

@dataclass(frozen=True)
class GroundedItem:
    item_id: str
    kind: str
    key: str
    meaning: str
    evidence_refs: tuple[str, ...]
    evidence_class: str
    confidence: str
    uncertainty: str | None = None
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    # A relation either has a sentence that names both ends (TEXT) or was read off a
    # diagram layout (LAYOUT); the second may never be presented as an observation.
    relation_source: str | None = None
    layout_ref: str | None = None
    # An absence is a state, not a quotation: the rows it was searched over and the
    # phrase that was looked for. Neither can be proven by the passage that raised
    # the question, so the item states its own scope instead.
    scope_refs: tuple[str, ...] = ()
    observed_absence: str | None = None
    # What kind of thing an entity is: one concept of the scope's concept set, which the
    # starter pack of `ontology_types` seeds. It may be empty: an entity the source
    # supports and no concept classifies keeps its row with the type left out, and the
    # gap is recorded row by row in the run's type gaps - an untyped entity is never
    # demoted to a claim.
    business_type: str | None = None
    # A deck often draws the current organisation and the proposed one on separate
    # pages. A row taken from a page that says which it is carries that word, so the
    # two charts can be told apart after they are one candidate: a proposed deputy
    # manager is not a second identity for the one the current chart names.
    scope_state: str | None = None
    # A change is one action, not a pair of ends. 整合甲、乙，设置为乙 names 乙 on both
    # sides - it was already there - and a (subject, object) row cannot say it: the row
    # that would say it is a change whose two ends are one item, which this contract
    # refuses. The two lists are therefore the action's own shape (types.v0.2's
    # event_types), and subject/object remain for a unit abolished or newly set up.
    event_from: tuple[str, ...] = ()
    event_to: tuple[str, ...] = ()
    # Where those two lists came from: the answer wrote them ("lists"), or the contract
    # read a single pair into them ("pair"). A row read from a pair is one of the pairs a
    # sentence about one action can be split into, which is what a reader has to know
    # before folding several rows back into the action they came from.
    event_ends_source: str | None = None
    # Whether the absorbed unit's legal person survives the merge: true, false, or
    # unknown because the page did not say.
    keeps_legal_entity: bool | None = None
    # Which party that answer is about, when it is not the whole change: several absorbed
    # parties that disagree, or a sentence that covers only some of them, leave the answer
    # `null` and say here that its scope is `unclear`.
    keeps_legal_entity_scope: str | None = None
    # --- fields the execution layer writes, never the producer -------------------
    # Which step wrote this row, and what it may therefore be: a claim about the
    # material (`source_claim`), a note about the run (`run_diagnostic`), or a source
    # nobody can verify (`unverifiable`). Written where the row is made, never read
    # from a producer or a model, and carried through the store so a saved row is read
    # back as the same kind of row it was saved as.
    source_origin: Mapping[str, Any] | None = None
    # A row the contract refused keeps its statement under another shape. Which refusal
    # it was, and whether the row is still a semantic statement (`business_unknown`) or
    # only run evidence (`run_diagnostic`), is decided here: the layer that validated the
    # row, not the answer that offered it. A producer that writes this field is ignored;
    # the value is recomputed on every pass.
    degradation: Mapping[str, Any] | None = None
    # Where the statement stands: `stated` (the page says it), `inferred`, or `pending`
    # (the row waits on a decision it cannot make itself).
    qualification: str | None = None
    # Whether the row's own content was confirmed against the passage it cites, and which
    # passages could not be read at all: a scope that was never read is a limit on the
    # statement, never a statement that the material was silent.
    verification: str | None = None
    unread_scopes: tuple[str, ...] = ()
    # The duties or events a condition limits, by their keys. A restriction that cannot
    # say what it restricts is not carried on the nearest sentence: it says so instead,
    # and the row is stored unattached.
    applies_to: tuple[str, ...] = ()
    # --- fields the reviewer writes, and only through a review record -------------
    # `resolves` is the part of the question `remaining` leaves open; `review_id` names
    # the record that decided it; an archived row keeps its history and leaves the
    # current set. None of these may arrive from a producer or a submission.
    resolution: str | None = None
    resolves: tuple[str, ...] = ()
    remaining: str | None = None
    resolved_by: str | None = None
    review_id: str | None = None
    archived: bool | None = None
    archived_by: str | None = None
    archived_basis: str | None = None

@dataclass(frozen=True)
class CoverageRecord:
    question_id: str
    status: str
    evidence_ids: tuple[str, ...] = ()
    reason: str | None = None
    item_ids: tuple[str, ...] = ()

@dataclass(frozen=True)
class SelectedSkill:
    skill_id: str
    version: str
    skill_sha256: str
    instruction_sha256: str
    loaded_reference_paths: tuple[str, ...] = ()
    strategy_id: str = ""
    status: str = "SELECTED"
    instructions: str = ""
    reference_texts: tuple[tuple[str, str], ...] = ()
    # The content identity of each reference file, not only its path. The modeling
    # method lives in those files (ontology-generator.md is 18K characters per call),
    # so a card that records paths alone cannot say which method produced it.
    reference_sha256: tuple[tuple[str, str], ...] = ()

@dataclass(frozen=True)
class StrategyRunReceipt:
    skill_id: str
    version: str
    digest: str
    strategy_id: str
    status: str
    output_count: int
    exit_reason: str

@dataclass(frozen=True)
class TaskContextOutput:
    goal: str
    authority: str
    evidence_ids: tuple[str, ...]
    unknowns: tuple[str, ...]

@dataclass(frozen=True)
class DocumentKnowledgeOutput:
    claims: tuple[GroundedItem, ...]
    authority: str = "UNREVIEWED_PROJECT_SUGGESTION"
    persistence_status: str = "NOT_PERSISTED"

@dataclass(frozen=True)
class SemanticCandidateOutput:
    scope_id: str | None
    items: tuple[GroundedItem, ...]
    producer_origin: str
    persistence_status: str = "NOT_PERSISTED"

@dataclass(frozen=True)
class AssetCandidateOutput:
    asset_type: str
    name: str
    relative_path: str
    source_sha256: str
    description: str = ""
    version: str | None = None
    declared_tools: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    entrypoints: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    reference_paths: tuple[str, ...] = ()
    script_paths: tuple[str, ...] = ()
    registration_status: str = "DISCOVERED_ONLY"
    binding_status: str = "UNBOUND"
    permission_status: str = "NOT_EVALUATED"
    evaluation_status: str = "NOT_EVALUATED"
    execution_status: str = "NOT_EXECUTED"

@dataclass(frozen=True)
class UnderstandingResult:
    version: str
    request_id: str
    intent: UnderstandIntent
    result_type: str
    status: str
    route: IntentRoute
    source_inventory: tuple[SourceRecord, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    extracted_facts: tuple[GroundedItem, ...] = ()
    inferred_items: tuple[GroundedItem, ...] = ()
    unknowns: tuple[GroundedItem, ...] = ()
    task_context: TaskContextOutput | None = None
    document_knowledge: DocumentKnowledgeOutput | None = None
    semantic_candidate: SemanticCandidateOutput | None = None
    asset_candidate: AssetCandidateOutput | None = None
    selected_skills: tuple[SelectedSkill, ...] = ()
    coverage_receipt: tuple[CoverageRecord, ...] = ()
    strategy_run_receipt: tuple[StrategyRunReceipt, ...] = ()
    stopping_reason: str = "bounded_complete"
    wiki_handoff: str = "NOT_REQUESTED"
    source_warnings: tuple[str, ...] = ()
    handoff_receipt: Mapping[str, Any] | None = None
    producer_attribution: Mapping[str, Any] | None = None
    revision: Mapping[str, Any] | None = None
    # Rows the run could not establish, kept whole: what they said, why they were not
    # answered, and where they went. They are run evidence - the record and the review
    # surface read them - and never Wiki semantic candidates, so no consumer has to
    # filter a candidate to be safe.
    run_diagnostics: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        # Every row this result carries was written in this run. A row whose tag does not
        # yet name a call is given the run's own id here, so a saved row can always be
        # traced back to the call that wrote it, whichever pass assembled the result.
        for field in ("extracted_facts", "inferred_items", "unknowns"):
            rows = getattr(self, field)
            if rows:
                object.__setattr__(self, field, tuple(stamp_call(row, self.request_id)
                                                     for row in rows))
        candidate = self.semantic_candidate
        if candidate is not None and candidate.items:
            object.__setattr__(self, "semantic_candidate", replace(
                candidate, items=tuple(stamp_call(row, self.request_id)
                                       for row in candidate.items)))

    def to_dict(self) -> dict[str, Any]:
        data = _jsonable(asdict(self))
        # An event's two lists are the type's own field names (`from` / `to` in
        # types.v0.2), which Python cannot use as attribute names. They leave this
        # process under the name the type gave them, so a card and a gold file speak
        # the same keys.
        for item in (data.get("semantic_candidate") or {}).get("items") or []:
            if isinstance(item, dict) and item.get("kind") == "event":
                item["from"] = list(item.pop("event_from", ()) or ())
                item["to"] = list(item.pop("event_to", ()) or ())
                item["ends_source"] = item.pop("event_ends_source", None)
        return data

@dataclass(frozen=True)
class _TextUnit:
    """One addressed cell of a source: what a quote can point at.

    The first six fields are the address itself and have not changed. The rest describe
    the cell in the file's own terms, so a semantic layer does not have to guess from the
    locator string what it is looking at: a heading with a level, a body paragraph, a
    table cell. They are optional because a format that says nothing about role must be
    able to say nothing (``None``), not a plausible default.

    ``path`` is the chain of headings this cell sits under, outermost first, as the file
    declared them. ``role_source`` says whether the role came from the format itself
    (``"format"``) or from a shape rule (``"inferred"``, which then carries ``reason``).
    ``witness`` is the whole cell a name was assembled from, when it was assembled from
    more than one run; a name may rest on it, a fact may not.
    """
    source_id: str
    relative_path: str
    source_revision: str
    source_sha256: str
    locator: str
    quote: str
    unit_kind: str = "format"
    role: str | None = None
    level: int | None = None
    path: tuple[str, ...] = ()
    role_source: str | None = None
    reason: str | None = None
    witness: dict[str, str] | None = None

class SemanticCapacityError(ValueError):
    """A candidate that does not fit the envelope is refused whole, never trimmed.

    Trimming would make a partial candidate look complete: the caller could no
    longer tell "the source has 142 facts" from "the source has 128".  The count
    of refused rows travels with the error so a caller can report the gap.
    """

    public_code = "semantic_capacity_exceeded"

    def __init__(self, limit: int, received: int, *, what: str = "semantic output",
                 segment: str | None = None) -> None:
        self.limit = limit
        self.received = received
        self.segment = segment
        self.refused_item_count = max(0, received - limit)
        super().__init__(
            f"{what} carries {received} items but the envelope accepts at most {limit}; "
            f"{self.refused_item_count} items were refused, not truncated"
        )

class SemanticVerificationError(ValueError):
    """An independent review refused the candidate; the findings are handed on.

    The message never carries a finding's reason: that text is about the source.
    What travels is the verdict, the item keys and the finding count, which is what
    a bounded revision needs and what a receipt may show.
    """

    public_code = "semantic_verification_failed"

    def __init__(self, verdict: str, findings) -> None:
        self.verdict = verdict
        self.findings = tuple(findings)
        keys = tuple(dict.fromkeys(
            key for finding in self.findings for key in (finding.get("item_keys") or ())
            if isinstance(key, str) and key))[:8]
        self.item_keys = keys
        super().__init__(
            f"independent verification returned {verdict} with {len(self.findings)} findings; "
            "the candidate is not fit for evaluation until they are repaired")

class SemanticContractError(ValueError):
    """A model answer broke the item contract; the defects are named so a revision can act.

    The message stays content-free: a rule slug and the model-chosen item keys only,
    never source text. The keys are what a bounded revision needs in order to know
    which rows to repair, and what the caller needs in order to say what was refused.
    """

    public_code = "semantic_item_contract_violation"

    def __init__(self, rule: str, item_keys=()) -> None:
        self.rule = rule
        self.item_keys = tuple(key for key in item_keys if isinstance(key, str) and key)
        super().__init__(f"semantic item contract broken: {rule}; items={list(self.item_keys)}")

class _UnreadableAnswer(ValueError):
    """One unit's answer cannot be read at all; the code says which way it failed.

    The refusal belongs to that unit alone, and the code travels with it so a card
    can tell a truncated answer from a malformed one without reading the text.
    """

    public_code = "unreadable_answer"

class _TruncatedAnswer(_UnreadableAnswer):
    public_code = "truncated"

class _ToolCallAnswer(_UnreadableAnswer):
    public_code = "tool_calls"

class _OversizeAnswer(_UnreadableAnswer):
    public_code = "output_over_budget"

class _MalformedJsonAnswer(_UnreadableAnswer):
    public_code = "invalid_json"

class _InvalidEnvelopeAnswer(_UnreadableAnswer):
    public_code = "envelope_invalid"

def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value

def _new_evidence(unit: _TextUnit, evidence_class: str = "observed_from_source") -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev_" + _sha(f"{unit.source_id}\0{unit.locator}\0{unit.quote}".encode("utf-8"))[:24],
        source_id=unit.source_id,
        relative_path=unit.relative_path,
        source_revision=unit.source_revision,
        source_sha256=unit.source_sha256,
        locator=unit.locator,
        quote=unit.quote,
        span_sha256=_sha(unit.quote.encode("utf-8")),
        evidence_class=evidence_class,
    )

# Who wrote a row, and what it may therefore be. A claim about the material is a
# claim only when the trusted reader wrote it as one; the reading's own guard
# sentences are notes about the run, never statements of the material. The table is
# closed: a step it does not name, or a tag whose category disagrees with the step
# that wrote it, leaves the row's source unverified - it keeps its content and does
# not enter the knowledge of the run.
SOURCE_CATEGORIES = frozenset({"source_claim", "run_diagnostic", "unverifiable"})
SOURCE_STEPS = {
    "reading:passage": "source_claim",
    "reading:layout": "source_claim",
    "reading:guard": "run_diagnostic",
    "answer:model": "source_claim",
    "submission:producer": "source_claim",
}


def source_origin_tag(step: str, item_id: str, call: str | None = None) -> dict[str, Any] | None:
    """The tag the layer writes for a row it just made, or None for an unknown step.

    `call` is the call that wrote the row, when the writer knows it; the run stamps its
    own id on rows that do not. It is never read off the row when the question is asked.
    """
    category = SOURCE_STEPS.get(step)
    if category is None:
        return None
    return {"category": category, "step": step, "call": call, "item_id": item_id}


def source_origin_is_well_formed(item) -> bool:
    """Whether the tag is internally coherent: a named category, its own step, this row.

    Coherent is not the whole answer. It says the tag does not contradict itself; it
    cannot say the call it names ever ran. `verified_source_origin` asks that too, and
    only against records the run holds.
    """
    tag = getattr(item, "source_origin", None)
    if not isinstance(tag, Mapping):
        return False
    category = tag.get("category")
    step = tag.get("step")
    if category not in SOURCE_CATEGORIES or SOURCE_STEPS.get(step) != category:
        return False
    return tag.get("item_id") == getattr(item, "item_id", None)


def verified_source_origin(item, calls: Iterable[str] | None = None) -> dict[str, Any] | None:
    """The provenance this layer can stand behind, or None when it cannot.

    Four things are asked of the tag: a category the contract names, a step that
    produced that category, the row's own identity, and a call this run can account
    for. The fourth is the one a tag cannot answer about itself: a call nobody ran is
    a string, so the calls come from the run's records (`calls`), never from the row.
    A caller that passes no records has verified nothing, and gets None.
    """
    tag = getattr(item, "source_origin", None)
    if not source_origin_is_well_formed(item):
        return None
    if tag.get("category") == "unverifiable":
        return None
    call = tag.get("call")
    if not isinstance(call, str) or not call.strip():
        return None
    if not calls or call not in set(calls):
        return None
    return dict(tag)


def stamp_call(item, call: str | None):
    """Name the call a row was written in, once, on the tag its step wrote.

    The step says what kind of row it is; the call says where it was written. A row that
    already names one keeps it - a row read back out of a store came from the call that
    read it then, not from this one.
    """
    if not call:
        return item
    tag = getattr(item, "source_origin", None)
    if not isinstance(tag, Mapping) or tag.get("call"):
        return item
    if not source_origin_is_well_formed(item):
        return item
    return replace(item, source_origin={**dict(tag), "call": call})


def _new_item(kind: str, key: str, meaning: str, evidence: Sequence[EvidenceRef], *, evidence_class: str = "observed_from_source", uncertainty: str | None = None, source_step: str = "reading:passage") -> GroundedItem:
    payload = f"{kind}\0{key}\0{meaning}\0" + "\0".join(item.evidence_id for item in evidence)
    item_id = "item_" + _sha(payload.encode("utf-8"))[:24]
    return GroundedItem(
        item_id=item_id,
        kind=kind,
        key=key,
        meaning=meaning,
        evidence_refs=tuple(item.evidence_id for item in evidence),
        evidence_class=evidence_class,
        confidence="not_calibrated" if evidence_class == "inferred" else "source_anchored_not_truth",
        uncertainty=uncertainty,
        source_origin=source_origin_tag(source_step, item_id),
    )

def _coverage(
    intent: UnderstandIntent,
    facts: Sequence[GroundedItem],
    unknowns: Sequence[GroundedItem],
    warnings: Sequence[str],
    *,
    known_evidence_ids: set[str] | None = None,
    tested: bool = True,
) -> tuple[CoverageRecord, ...]:
    if intent is UnderstandIntent.KNOWLEDGE_PROPOSE:
        questions = {
            "business_entities": {"entity"},
            "responsibility": {"claim"},
            "relations": {"relation"},
            "conditions": {"condition"},
            "exceptions_and_negative": {"negative_claim", "exception"},
            "aliases": {"alias"},
            "conflicts": {"conflict"},
            "authority_boundary": set(),
        }
    elif intent is UnderstandIntent.ASSET_INSPECT:
        questions = {
            "entrypoints": {"function", "class", "entrypoint"}, "dependencies": {"import", "dependency"},
            "tools_and_workers": {"worker", "tool"},
            "state_and_failure": {"state_write", "exception", "failure"},
            "effects": {"side_effect", "state_write"}, "cancellation": {"cancel"},
        }
    else:
        questions = {"task_text": {"observed_text", "grounded_claim"}}
        if any(warning.startswith("NEEDS_VISION") for warning in warnings):
            questions["visual_content"] = {"visual"}
    rows = []
    for question_id, expected in questions.items():
        if not tested:
            rows.append(CoverageRecord(question_id, "NOT_TESTED", reason="coverage strategy did not run within the requested budget"))
            continue
        if question_id == "authority_boundary":
            unresolved_items = [item for item in unknowns if item.kind == "unknown" and item.key in {"approval", "binding", "authority"}]
            rows.append(CoverageRecord(
                question_id,
                "EXPLICITLY_UNRESOLVED",
                evidence_ids=tuple(dict.fromkeys(ref for item in unresolved_items for ref in item.evidence_refs)),
                reason="text understanding cannot establish current owner authorization or executable binding",
                item_ids=tuple(item.item_id for item in unresolved_items),
            ))
            continue
        matching_items = [
            item for item in facts
            if item.kind in expected
            and item.evidence_refs
            and (known_evidence_ids is None or any(ref in known_evidence_ids for ref in item.evidence_refs))
            and (item.kind != "relation" or all((item.subject, item.predicate, item.object)))
        ]
        matching = tuple(item.item_id for item in matching_items)
        if matching:
            evidence_ids = tuple(dict.fromkeys(ref for item in matching_items for ref in item.evidence_refs))
            rows.append(CoverageRecord(question_id, "ANSWERED", evidence_ids=evidence_ids, item_ids=matching))
        else:
            reason = "non-text visual content requires a vision-capable reader" if question_id == "visual_content" else "not established by inspected source"
            if any(item.kind == "unknown" for item in unknowns):
                reason += "; source or producer recorded unresolved items"
            if warnings:
                reason += "; " + ", ".join(warnings[:3])
            state = "NOT_DISCOVERED" if warnings else "EXPLICITLY_UNRESOLVED"
            rows.append(CoverageRecord(question_id, state, reason=reason))
    return tuple(rows)
