"""One registered semantic method, one lease, one run, and the record of what happened.

The product already knows how to admit a data-only method package and how to freeze one for
the length of a run (`ComponentStore.admit` / `acquire_method`). It also knows how to read a
Skill directory into a `UnderstandingResult` (`UnderstandPort(skill_root=...)`). What was
missing is the step in between: the lease hands out `{path: text}`, the port reads a
directory, and nothing turned one into the other -- so a run could not be bound to the
version of the method that was registered.

This module is that step and nothing more:

  acquire a lease -> verify and materialise its files -> run the port against them
  -> record the identity of the whole run -> release the lease, on success and on failure

Two rules keep a record honest.

**A run's identity is a four-tuple.** The method package alone says nothing about what was
actually executed: the same package ran with two extraction modes, and the repairs that
produced a candidate live outside the package as their own implementation. So every run
records `method` (component, version, package digest), `extraction_mode`, `repairs`
(name, version, implementation digest, scope, enabled) and `sources` (per-source digests).

**A repair is off unless it is named, scoped and re-validated.** `repairs=None` means the
result is the model's own; the record says so instead of leaving it blank. When a repair is
named, it must declare the labels it applies to, and a run under any other label is refused
before a lease is taken. A repaired result is never written back over the validated one: the
repaired items go through the same typed validator the model's own answer went through
(`UnderstandPort.attach_producer_items`), and the record carries the validator's verdict
beside the original and the revised forms.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .ontology_types import STARTER_PACK, concept_set_identity
from .understand_manifest import _SKILL_ROOT
from .understand_models import UnderstandingResult

# The one Skill contract this seam serves. Declared in `method_bundle` as well, where the
# admission gate reads it; kept here so a caller does not have to import that module.
SEMANTIC_INTERFACE = "semantic-proposal.v1"
SEMANTIC_SERVICES = frozenset({"semantic_submit_candidate"})
SEMANTIC_COMPONENT = "enterprise-ontology"
SEMANTIC_SKILL = "understand-enterprise-semantics"
EXTRACTION_MODES = ("single_stage", "source_local_two_stage")

# The product's own Skill tree. A method package replaces one Skill inside it; the rest is
# product text and is recorded, not leased.
BUILTIN_SKILLS = _SKILL_ROOT


class SemanticMethodError(Exception):
    """A run could not be bound to the method, or the binding was not honoured."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------- the method on disk


def verify_snapshot(snapshot: Mapping[str, Any]) -> dict[str, str]:
    """The frozen files, checked against the digests the manifest declares.

    A lease is supposed to be immutable already; this re-checks it against its own manifest
    so a corrupted or hand-built snapshot cannot become a run's method by being passed here.
    """
    manifest = snapshot.get("manifest") or {}
    declared = manifest.get("files") or {}
    files = snapshot.get("files") or {}
    if set(files) != set(declared):
        raise SemanticMethodError("method_snapshot_file_set_mismatch",
                                  f"{sorted(set(files) ^ set(declared))}")
    if "SKILL.md" not in files:
        raise SemanticMethodError("method_snapshot_without_skill")
    for name, text in files.items():
        if _sha(text.encode("utf-8")) != declared[name]:
            raise SemanticMethodError("method_snapshot_file_changed", name)
    return dict(files)


def materialize_method(snapshot: Mapping[str, Any], *, base_root: Path | str | None = None) -> Path:
    """Write the frozen files where `UnderstandPort(skill_root=...)` looks for them.

    The resolver reads `<root>/<skill_name>/SKILL.md` plus `<root>/<skill_name>/references/`
    (`understand_manifest._SkillSTRATEGIES`), so the snapshot's package-relative paths are
    nested one level deeper.

    `base_root` names the product tree the payload is laid over; a replay that reproduces a
    recording passes the tree that recording was made with, and the record keeps its digests.
    The caller owns the directory and removes it when the run ends.
    """
    files = verify_snapshot(snapshot)
    skill = str((snapshot.get("manifest") or {}).get("skill_name") or "")
    if skill != SEMANTIC_SKILL:
        raise SemanticMethodError("method_skill_not_served_by_this_seam", skill)
    base = Path(base_root or BUILTIN_SKILLS)
    if not (base / "_methods").is_dir():
        raise SemanticMethodError("method_base_root_unusable", str(base))
    root = Path(tempfile.mkdtemp(prefix="catalyst-method-"))
    # A method package is one Skill. The Port loads `_methods/understand-*.md` beside it and
    # reads everything from one root, so the product tree is laid down first and the frozen
    # payload goes over it. Writing only the payload left every run here stopping at
    # `trusted_skill_unavailable` -- an empty result that reads like a refusal to read.
    for path in sorted(base.rglob("*")):
        if path.is_file() and not path.is_symlink():
            target = root / path.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    folder = root / skill
    if folder.is_dir():
        # The package's file list is the whole of its Skill. A reference it does not carry
        # is not borrowed from the product's copy of the same Skill: then two packages with
        # different bytes could put the same method text in front of a model, and the lease
        # would still look like the thing that decided it.
        shutil.rmtree(folder)
    for name, text in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    return root


def builtin_skill_digests(root: Path, pinned_files: Sequence[str]) -> dict[str, str]:
    """The built-in Skill files a run read, by digest, with the package's own left out.

    Those files are product text: the lease cannot pin them, so the record names them. The
    package's files are already pinned by `package_sha256` and its manifest, and repeating
    them here would let the two disagree without anyone noticing. `pinned_files` are
    root-relative, i.e. already nested under the Skill's own folder.
    """
    pinned = set(pinned_files)
    return {path.relative_to(root).as_posix(): _sha(path.read_bytes())
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.relative_to(root).as_posix() not in pinned}


# ---------------------------------------------------------------- repairs, named and scoped


@dataclass(frozen=True)
class RepairSpec:
    """One post-processing implementation, with the scope it is allowed to act on.

    `apply` receives the validated result and returns the producer items that should stand
    in its place -- the rows `producer_items(result)` gives, which are the form the validator
    reads. It never returns a `UnderstandingResult`: the seam does not accept a repaired
    result that skipped the typed validator, it asks for items and re-validates.
    """

    name: str
    version: str
    implementation: str          # "module:function"
    sha256: str                  # digest of the module that implements it
    scope: Mapping[str, Any]     # {"labels": [...], "kinds": [...]}
    apply: Callable[[UnderstandingResult], Sequence[Mapping[str, Any]]]

    def allowed_for(self, label: str) -> bool:
        labels = tuple((self.scope or {}).get("labels") or ())
        return bool(labels) and label in labels

    def identity(self, *, enabled: bool) -> dict[str, Any]:
        return {"name": self.name, "version": self.version, "implementation": self.implementation,
                "sha256": self.sha256, "scope": dict(self.scope or {}), "enabled": bool(enabled)}


def repair_spec(*, name: str, version: str, implementation: str,
                scope: Mapping[str, Any],
                apply: Callable[[UnderstandingResult], Sequence[Mapping[str, Any]]] | None = None) -> RepairSpec:
    """Build a spec whose digest is read from the module that implements it, not supplied.

    A caller cannot claim a digest it likes: the bytes are hashed here, and the name has to
    resolve to a callable in that module. `apply` defaults to the function the name resolves
    to; passing one that is a different function is refused, because a record that names one
    implementation while another runs is worse than no record at all.
    """
    import importlib

    module_name, _, attribute = implementation.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:  # pragma: no cover - misconfiguration, not a data case
        raise SemanticMethodError("repair_implementation_missing", module_name) from exc
    path = Path(getattr(module, "__file__", "") or "")
    if not path.is_file():
        raise SemanticMethodError("repair_implementation_unreadable", module_name)
    function = getattr(module, attribute, None) if attribute else None
    if not callable(function):
        raise SemanticMethodError("repair_implementation_missing", implementation)
    if apply is None:
        apply = function
    elif apply is not function:
        raise SemanticMethodError("repair_implementation_mismatch", implementation)
    if not tuple((scope or {}).get("labels") or ()):
        raise SemanticMethodError("repair_without_scope", "a repair must name the labels it applies to")
    return RepairSpec(name=name, version=version, implementation=implementation,
                      sha256=_sha(path.read_bytes()), scope=dict(scope), apply=apply)


# ---------------------------------------------------------------- replay without a vendor


class RecordedResponseProvider:
    """Answers from a run's recorded `calls/` files; refuses anything else.

    This is the zero-API path: the same requests go to the same recorded answers, so a run
    can be reproduced without a model and without a key. It does not pretend to be a model
    -- `mode` says what it is, and a request that was never recorded raises instead of
    being answered by a heuristic.
    """

    provider_id = "catalyst-recorded-replay"
    mode = "recorded"
    external_calls = 0

    def __init__(self, capture: Path | str, *, model: str = "recorded-run",
                 structured_output_token_limit: int = 8192, model_output_token_limit: int = 8192) -> None:
        self.capture = Path(capture)
        self.model = model
        self.structured_output_token_limit = structured_output_token_limit
        self.model_output_token_limit = model_output_token_limit
        self.answered: list[int] = []
        self.missed: list[str] = []
        self._pending: dict[str, tuple[int, Mapping[str, Any]]] = {}
        for path in sorted((self.capture / "calls").glob("*_response.json")):
            number = int(path.name.split("_")[0])
            request_path = path.with_name(f"{path.name.split('_')[0]}_request.json")
            if not request_path.is_file():
                continue
            recorded = json.loads(request_path.read_text(encoding="utf-8"))
            self._pending.setdefault(_sha(_canonical(recorded)), (number, json.loads(path.read_text(encoding="utf-8"))))

    @property
    def request_count(self) -> int:
        return len(self.answered) + len(self.missed)

    def request(self, request):
        from agent_runtime.contracts import ModelResponse, ModelToolCall, ModelUsage

        from dataclasses import asdict

        key = _sha(_canonical(asdict(request)))
        recorded = self._pending.get(key)
        if recorded is None:
            self.missed.append(key)
            raise SemanticMethodError("replay_request_not_recorded",
                                      "the pipeline asked something this run never asked")
        number, body = recorded
        self.answered.append(number)
        usage = body.get("usage")
        return ModelResponse(
            content=body.get("content"),
            tool_calls=tuple(ModelToolCall(id=call["id"], name=call["name"],
                                           arguments=call["arguments"])
                             for call in body.get("tool_calls") or ()),
            finish_reason=body.get("finish_reason"),
            usage=ModelUsage(**usage) if isinstance(usage, Mapping) else None,
        )


# ---------------------------------------------------------------- the run


@dataclass(frozen=True)
class SemanticMethodRun:
    """What was registered, what executed, and what each of the two produced."""

    identity: Mapping[str, Any]
    original: UnderstandingResult
    result: UnderstandingResult
    diff: tuple[dict[str, Any], ...]
    validation: Mapping[str, Any]
    lease: Mapping[str, Any]
    # The per-row ledger of what the validator did with what the repair submitted.
    disposition: Mapping[str, Any] = field(default_factory=dict)
    # The whole row sets and their digests, when the caller asked for them to be kept.
    record_files: Mapping[str, Any] = field(default_factory=dict)

    def record(self) -> dict[str, Any]:
        return {"identity": dict(self.identity),
                "original": _form(self.original),
                "result": _form(self.result),
                "diff": list(self.diff),
                "validation": dict(self.validation),
                "disposition": dict(self.disposition),
                "record_files": dict(self.record_files),
                "lease": dict(self.lease)}


def _form(result: UnderstandingResult) -> dict[str, Any]:
    """A result as a record: its digest, its counts, and one digest per item."""
    rendered = result.to_dict()
    items = (rendered.get("semantic_candidate") or {}).get("items") or []
    return {"digest": _sha(_canonical(rendered)),
            "items": len(items),
            "kinds": {kind: sum(1 for row in items if row.get("kind") == kind)
                      for kind in sorted({row.get("kind") for row in items})},
            "item_digests": {f"{row.get('kind')}:{row.get('key')}": _sha(_canonical(row))
                             for row in items},
            "producer_attribution": dict(rendered.get("producer_attribution") or {})}


def _items(result: UnderstandingResult) -> list[dict[str, Any]]:
    rendered = result.to_dict()
    return list((rendered.get("semantic_candidate") or {}).get("items") or [])


# Fields the validator assigns on every pass rather than a producer declaring them, so
# comparing them would report every row as changed after every repair. `source_origin` is
# the same kind of field: the step and the call that wrote the row are the layer's account
# of itself, written anew each pass, and a repair never sees them (the rows it is handed
# are `_comparable`, which strips them).
_BOOKKEEPING = ("item_id", "confidence", "source_origin")


def _source_origin_entry(before: Any, after: Any) -> dict[str, Any]:
    """Who wrote a row, as the ledger keeps it: the tag is bookkeeping, not content.

    The content comparison leaves the tag out, so a row this ledger calls `kept` says
    its words survived unchanged; it does not say the row's source did. The tag still
    travels on the line, so a reader can trace a row to the step and the call that
    wrote it even when nothing about the wording moved.
    """
    before_tag = dict(before) if isinstance(before, Mapping) else None
    after_tag = dict(after) if isinstance(after, Mapping) else None
    entry: dict[str, Any] = {"after": after_tag}
    if before_tag is not None:
        entry["before"] = before_tag
        entry["changed"] = before_tag != after_tag
    return entry


def _stating(value: Any) -> bool:
    return not (value is None or value == "" or value == [] or value == {} or value == ())


def _comparable(row: Mapping[str, Any]) -> dict[str, Any]:
    """One row as content: what it states, without what the validator added to it.

    A row that omits an empty field and a row that carries the field as null state the same
    thing, and a field one name is not is dropped by both readings, so the comparison is
    made on the fields that carry something.
    """
    return {name: value for name, value in row.items()
            if name not in _BOOKKEEPING and _stating(value)}


def producer_items(result: UnderstandingResult) -> list[dict[str, Any]]:
    """The candidate's rows in the form a producer submits them.

    A repair reads rows from here, not from `to_dict()`: the rendered form carries the
    validator's own bookkeeping (`item_id`, `confidence`) and handing that back reads as a
    producer inventing schema -- every row would be dropped and named for it.
    """
    return [_comparable(row) for row in _items(result)]


def diff_items(before: Sequence[Mapping[str, Any]], after: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Field-level difference between two item sets, keyed by (kind, key) **and by position**.

    Reported per item and per field, in both directions, so a reader can see what a repair
    changed without diffing two JSON files by hand.

    Two rows may share a kind and a key: a reading that named the same thing twice, or a
    repair that split one row into two. Folding them onto a single identity makes the second
    row vanish from the difference, and the difference is the one place a lost row cannot be
    seen -- a card of three hundred rows then diffs as two hundred and ninety and every count
    still adds up. Rows are therefore paired by their order of appearance, and an identity that
    holds more than one row names the `occurrence` that tells them apart.
    """
    def index(rows):
        out: dict[tuple, list[dict[str, Any]]] = {}
        for row in rows:
            out.setdefault((row.get("kind"), row.get("key")), []).append(_comparable(row))
        return out

    left, right = index(before), index(after)
    changes: list[dict[str, Any]] = []
    for identity in sorted(set(left) | set(right), key=lambda pair: (str(pair[0]), str(pair[1]))):
        old_rows, new_rows = left.get(identity) or [], right.get(identity) or []
        for position in range(max(len(old_rows), len(new_rows))):
            old = old_rows[position] if position < len(old_rows) else None
            new = new_rows[position] if position < len(new_rows) else None
            line: dict[str, Any] = {"kind": identity[0], "key": identity[1]}
            if len(old_rows) > 1 or len(new_rows) > 1:
                line["occurrence"] = position
            if old is None:
                # A row that arrived is named by what it says, so a reader does not have to
                # hold two row sets open to find out which row this line is about.
                changes.append({**line, "change": "added", "meaning": new.get("meaning")})
            elif new is None:
                changes.append({**line, "change": "removed", "meaning": old.get("meaning")})
            else:
                fields = [name for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)]
                if fields:
                    changes.append({**line, "change": "changed",
                                    "fields": {name: {"before": old.get(name), "after": new.get(name)}
                                               for name in fields}})
    return changes


# ------------------------------------------------------------ the room a repair is re-read in


def segment_budget_for(original: UnderstandingResult, *,
                       authorised: Sequence[int] | None = None) -> dict[str, Any]:
    """The room a repaired answer is re-validated in: the answer's own counts, clamped.

    A repair reads the rows a reading produced and hands back some of them, so it can never
    *need* more room than the reading itself used. Re-validating it against the narrower
    per-answer ceiling instead refuses a repaired card the reading already carried: one live
    deck's answer held 93 entities and 255 other rows, and a whole-card handback was refused on
    the 128-row ceiling alone -- which is why that handoff shipped a 14-row slice.

    A run must not authorise itself, though. The reading that produced this answer ran inside a
    room somebody chose -- 64/128 for a single answer, 384/384 for the merged candidate of a unit
    split -- and a repair may not be handed a bigger room than that, or every large answer would
    grant itself room by being large. So the caller passes the ceiling **the run was authorised
    for** as `authorised`; with none passed the budget stays at the per-answer default and a
    wider room has to be declared, not inferred from how many rows came back.

    Within that ceiling the budget is the wider of "what this answer used" and "the default", so
    a widened budget is a derived fact and not a raised constant, and the record keeps all three
    numbers plus whether the ceiling -- rather than the answer -- decided it.
    """
    from .understand_semantic import _MAX_SEMANTIC_ENTITIES, _MAX_SEMANTIC_OTHER_ITEMS

    rows = _items(original)
    entities = sum(1 for row in rows if row.get("kind") == "entity")
    other = len(rows) - entities
    default = (_MAX_SEMANTIC_ENTITIES, _MAX_SEMANTIC_OTHER_ITEMS)
    ceiling = default if authorised is None else tuple(authorised)
    if len(ceiling) != 2 or any(not isinstance(value, int) or value < 0 for value in ceiling):
        raise SemanticMethodError("segment_budget_invalid", repr(authorised))
    if ceiling[0] < default[0] or ceiling[1] < default[1]:
        # A ceiling below the per-answer default is not a narrow run, it is a mistake: the
        # reading could not have been accepted in it at all.
        raise SemanticMethodError("segment_budget_below_default", f"{ceiling} < {default}")
    wanted = (max(default[0], entities), max(default[1], other))
    budget = (min(wanted[0], ceiling[0]), min(wanted[1], ceiling[1]))
    return {"entities": budget[0], "other_items": budget[1],
            "answer_segments": {"entities": entities, "other_items": other},
            "default_segments": {"entities": default[0], "other_items": default[1]},
            "authorised_segments": ({"entities": ceiling[0], "other_items": ceiling[1]}
                                    if authorised is not None else None),
            "wider_than_default": budget != default,
            # True when the run's own ceiling, not the answer, set the number: the answer used
            # more rows than it was ever authorised to hand back.
            "clamped_by_authorisation": wanted != budget}


# ------------------------------------------------------------------- keeping the whole record


# Every digest this module writes, and the bytes it covers. A digest without its unit is a
# number nobody can recompute: the same Skill file hashes differently as file bytes and as the
# body a model reads, and the two have been confused once already.
DIGEST_UNITS = {
    "producer_output_sha256": "canonical JSON of the rows this run accepted",
    "skills_provided[].instruction_sha256": "the Skill body after its frontmatter, utf-8, BOM stripped",
    "skill_reference_sha256[].references[].sha256": "a reference file's body, utf-8, BOM stripped",
    "method.package_sha256": "the component package as the store computed it at admission",
    "repairs.sha256": "the implementation module's file bytes",
    "concepts.digest": "canonical JSON of the concept rows this run extracted with",
    "implementation.sha256": "each named product entry point's file bytes, in release order",
    "builtin_skills.files": "each built-in Skill file's bytes",
    "sources[].source_sha256": "each source file's bytes",
    "record.files[].sha256": "the bytes of that JSON file as written",
}


def _write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One complete row set on disk, with the digest of exactly what was written."""
    payload = json.dumps(list(rows), ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    path.write_bytes(payload)
    return {"path": str(path), "count": len(rows), "sha256": _sha(payload), "bytes": len(payload)}


def pair_original_to_stored(original: Sequence[Mapping[str, Any]],
                            stored: Sequence[Mapping[str, Any]]) -> tuple[list[tuple[int, int]],
                                                                          list[int], list[int]]:
    """Pair every stored row with the row of the original it came from.

    A repair hands back rows it read, and the validator may keep one under another kind: an
    entity whose class it cannot read comes back as `unknown` with the same key. So a stored
    row is matched by exact content first, then by key with the same kind, then by key with any
    kind. What is left on the original's side is a row that was not submitted; what is left on
    the stored side is a row the repair added.
    """
    pairs: list[tuple[int, int]] = []
    taken: set[int] = set()
    for position, row in enumerate(stored):
        want = _canonical(_comparable(row))
        found = None
        for index, candidate in enumerate(original):
            if index not in taken and _canonical(_comparable(candidate)) == want:
                found = index
                break
        if found is None:
            for index, candidate in enumerate(original):
                if index not in taken and candidate.get("key") == row.get("key") \
                        and candidate.get("kind") == row.get("kind"):
                    found = index
                    break
        if found is None:
            for index, candidate in enumerate(original):
                if index not in taken and candidate.get("key") == row.get("key"):
                    found = index
                    break
        if found is None:
            continue
        taken.add(found)
        pairs.append((found, position))
    return pairs, [index for index in range(len(original)) if index not in taken], \
        [position for position in range(len(stored)) if position not in {pair[1] for pair in pairs}]


def write_record(directory: Path, *, original: UnderstandingResult, repaired: Sequence[Mapping[str, Any]],
                 submitted: Sequence[Mapping[str, Any]], stored: UnderstandingResult,
                 identity: Mapping[str, Any], validation: Mapping[str, Any],
                 segment_budget: Mapping[str, Any],
                 probe: Mapping[str, Any] | None = None,
                 overwrite: bool = False) -> dict[str, Any]:
    """Write the four row sets of a run, whole, with their digests and what each is compared with.

    The validator's own refusal lists keep twenty rows and the diff names identities, so
    neither of them is a record of a card: a handoff that ships a slice needs the rows it did
    not ship to still exist somewhere, or "the whole answer was kept" is a sentence rather than
    an artifact. Every set here is written complete -- the reading's own rows, what the repair
    returned, what the validator was handed, what it accepted, and the rows nothing paired with
    -- and the sum is checked before the record is written, so a row cannot leave the run
    silently.

    `submitted` and `repaired` are the same list on every run today, and both are written: a
    reader comparing them byte for byte then learns that the seam carried the repair's rows
    unedited, which is exactly what a repair that rewrites on the way in would hide.
    """
    directory.mkdir(parents=True, exist_ok=True)
    existing = sorted(path.name for path in directory.iterdir())
    if existing and not overwrite:
        # A record is run evidence. Two runs writing one folder means the second silently
        # replaces the first, and a frozen run then has no artifact that says what it saw.
        # Callers that want to freeze a run give it a new directory; nothing here deletes.
        raise SemanticMethodError(
            "record_directory_in_use",
            f"{directory} already holds {existing}; a run's record is written once -- "
            "pass a new record directory, or overwrite=True if this is a rehearsal")
    original_rows = _items(original)
    stored_rows = _items(stored)
    pairs, unsubmitted, added = pair_original_to_stored(original_rows, stored_rows)
    if len(pairs) + len(unsubmitted) != len(original_rows):
        raise SemanticMethodError("record_not_conserved",
                                  f"{len(pairs)} paired + {len(unsubmitted)} unsubmitted "
                                  f"!= {len(original_rows)} original")
    if len(pairs) + len(added) != len(stored_rows):
        raise SemanticMethodError("record_not_conserved",
                                  f"{len(pairs)} paired + {len(added)} added != {len(stored_rows)} stored")
    # A row the validator holds that the repair never submitted would be a row minted by the
    # seam. It is not a size problem, an identity problem or a wording problem: it is a row
    # with no producer, and a record that quietly lists it as "added" would hide that.
    submitted_canonical = {_canonical(_comparable(row)) for row in submitted}
    unexplained = [stored_rows[index] for index in added
                   if _canonical(_comparable(stored_rows[index])) not in submitted_canonical]
    if unexplained:
        raise SemanticMethodError("record_row_not_accounted",
                                  f"{[row.get('key') for row in unexplained]}")
    # A repair may not put a citation on a row it did not receive.
    invented: list[dict[str, Any]] = []
    for origin, position in pairs:
        before = set(original_rows[origin].get("evidence_refs") or ())
        after = set(stored_rows[position].get("evidence_refs") or ())
        extra = sorted(after - before)
        if extra:
            invented.append({"kind": stored_rows[position].get("kind"),
                             "key": stored_rows[position].get("key"), "citations": extra})
    # What the run could not establish is written whole beside the row sets: it is the
    # run's evidence, it is never a candidate row, and a record that kept only the card
    # could not say what the reading refused to answer. A repair submits a subset of the
    # answer, so these rows are not required to be among what was submitted again - they
    # travel with the result and are written as they are.
    diagnostic_rows = [dict(row) for row in (getattr(stored, "run_diagnostics", ()) or ())]
    files = {
        "original": _write_rows(directory / "original-items.json", original_rows),
        "repaired": _write_rows(directory / "repaired-items.json", repaired),
        "submitted": _write_rows(directory / "submitted-items.json", submitted),
        "stored": _write_rows(directory / "stored-items.json", stored_rows),
        "unsubmitted": _write_rows(directory / "unsubmitted-items.json",
                                   [original_rows[index] for index in unsubmitted]),
        "diagnostics": _write_rows(directory / "run-diagnostics.json", diagnostic_rows),
    }
    baseline = {
        "original": "the model's own rows, before any repair",
        "repaired": "the rows the repair returned",
        "submitted": "the rows this run handed to the validator",
        "stored": "the rows the validator accepted as statements",
        "unsubmitted": "rows of the original that no stored row was paired with, in full",
        "diagnostics": ("the rows the run could not establish: kept whole with their reason and "
                        "destination, never candidates and never counted as statements"),
    }
    record = {
        "request_id": getattr(original, "request_id", None),
        "baseline": baseline,
        "files": {name: {**entry, "baseline": baseline[name]} for name, entry in files.items()},
        "conservation": {
            "original": len(original_rows), "paired": len(pairs),
            "unsubmitted": len(unsubmitted), "stored": len(stored_rows), "added": len(added),
            "holds": True,
            "submitted_equals_repaired": files["submitted"]["sha256"] == files["repaired"]["sha256"],
            "citations_preserved": len(pairs) - len(invented),
            "citations_invented_by_repair": invented,
            "added_rows": [{"kind": stored_rows[index].get("kind"),
                            "key": stored_rows[index].get("key")} for index in added],
            # What the validator accepted and then classified: a statement about the
            # material, or evidence about this run. Both existed at the same moment, so
            # the sum is checked rather than assumed.
            "diagnostics": len(diagnostic_rows),
            "diagnostic_classes": _class_counts(diagnostic_rows),
            # Stored rows plus run evidence: what the validator held after it decided
            # which rows were statements and which were about the reading itself.
            "accounted": len(stored_rows) + len(diagnostic_rows),
        },
        "segment_budget": dict(segment_budget),
        "capacity_probe": dict(probe or {}),
        "validation": dict(validation),
        # What the validator wrote about itself: the refusals, the merges and the
        # references it bound by letter case, each with the spelling it arrived with.
        # A row set alone cannot say any of that, and the stored row keeps only the
        # declaration - so the record is where both spellings live.
        "validator": {"producer_attribution": dict(
            getattr(stored, "producer_attribution", None) or {})},
        "attribution": {"method": dict(identity.get("method") or {}),
                        "repairs": dict(identity.get("repairs") or {}),
                        "builtin_skills": dict(identity.get("builtin_skills") or {}),
                        "digest_units": dict(DIGEST_UNITS)},
    }
    payload = json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
    (directory / "run-record.json").write_bytes(payload)
    return {"path": str(directory / "run-record.json"), "sha256": _sha(payload),
            "files": files, "conservation": record["conservation"],
            "segment_budget": dict(segment_budget), "capacity_probe": dict(probe or {}),
            "baseline": baseline}


def whole_answer_probe(port: Any, seed: UnderstandingResult, original: UnderstandingResult,
                       budget: Mapping[str, Any], *, model_id: str | None) -> dict[str, Any]:
    """Hand the whole answer back through the validator, twice, and record both verdicts.

    This publishes nothing and decides nothing. It answers one question by measurement: does the
    whole answer survive **re-validation** in the room this run derived, and what refuses it in
    the per-answer default room. The two calls differ only in the room they are given, so a
    refusal names a ceiling rather than an opinion.

    The verdict is named `whole_answer_passes_revalidation` and not "can be handed on": passing
    the validator says nothing about whether the Wiki would take the card -- duty, event,
    retirement and degraded rows still have contract gaps (C/D/E), and this round's published
    handoff is a slice either way.
    """
    rows = producer_items(original)
    out: dict[str, Any] = {
        "rows": len(rows), "segment_budget": dict(budget),
        "measures": ("re-validation of the whole answer through attach_producer_items, once in "
                     "the room this run derived and once in the per-answer default"),
        "handoff_authorised": False,
        "handoff_note": ("passing re-validation is not a handoff and not an admission: the Wiki "
                         "still decides what C/D/E allow, and this run publishes a slice"),
    }
    for name, segment in (("with_the_answers_room", (budget["entities"], budget["other_items"])),
                          ("with_the_default_room", None)):
        try:
            kept = port.attach_producer_items(seed, producer_kind="CATALYST_NATIVE_MODEL",
                                              producer_invocation_id=f"probe:{name}",
                                              items=rows, producer_model_id=model_id,
                                              segment_budget=segment)
        except Exception as exc:            # a refusal is the measurement, not a failure
            out[name] = {"accepted": None, "refused": f"{type(exc).__name__}: {exc}"}
        else:
            out[name] = {"accepted": len(_items(kept)), "refused": None}
    out["whole_answer_passes_revalidation"] = out["with_the_answers_room"]["accepted"] == len(rows)
    return out


def _implementation_identity() -> dict[str, Any]:
    """The product files this build executed, by digest.

    The method package is one half of what ran; the rules that live in product code --
    holder hints, type hints, the mechanical checks -- are the other. The release file
    names the same bytes, so a card that records this digest can be checked against it.
    """
    from .capability_release import entry_points, implementation_digest, repository_root

    rows = entry_points(repository_root())
    return {"sha256": implementation_digest(rows), "files": rows}


def carry_run_identity(result: UnderstandingResult, identity: Mapping[str, Any]) -> UnderstandingResult:
    """Put the method, the repairs and the built-in Skills into the result's own attribution.

    A candidate handed to the Wiki carries `producer_attribution` into its derived package, and
    that package is the only thing a later reader is guaranteed to have. Without this the
    package names the producer's skills and output digest but not which method version read the
    material or which repair reshaped it -- so "the same card came from the same method" could
    not be checked from the card. The values are the run's own, not a second computation.
    """
    attribution = dict(result.producer_attribution or {})
    attribution.update({
        "method": dict(identity.get("method") or {}),
        "concepts": dict(identity.get("concepts") or {}),
        "implementation": dict(identity.get("implementation") or {}),
        "repairs": dict(identity.get("repairs") or {}),
        "builtin_skills": dict(identity.get("builtin_skills") or {}),
        "digest_units": dict(DIGEST_UNITS),
    })
    return replace(result, producer_attribution=attribution)


# ---------------------------------------------------------------- what became of every row


def _known_evidence(result: UnderstandingResult) -> set[str]:
    return {ref.evidence_id for ref in result.evidence_refs}


def _degraded_rule(row: Mapping[str, Any]) -> str | None:
    """The rule the validator wrote on a row it kept under another shape, if it wrote one."""
    text = str(row.get("uncertainty") or "")
    if not text.startswith("degraded:"):
        return None
    return text.split(":", 2)[1] or None


def _class_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """How many rows of each classification the run wrote."""
    counts: dict[str, int] = {}
    for row in rows:
        degradation = row.get("degradation") if isinstance(row.get("degradation"), Mapping) else {}
        name = str(degradation.get("class") or "unclassified")
        counts[name] = counts.get(name, 0) + 1
    return counts


def _named_rules(attribution: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Every rule the validator wrote against a key, and where it wrote it.

    Two lists refuse a row outright or take a field off it; a third folds a duplicate entity
    into the one that keeps the name. All three are the validator naming what it did, so all
    three are read here and a row none of them names stays unnamed.
    """
    rules: dict[str, list[dict[str, Any]]] = {}

    def add(key: Any, rule: Any, source: str, **extra: Any) -> None:
        if isinstance(key, str):
            rules.setdefault(key, []).append({"rule": str(rule), "source": source, **extra})

    for row in attribution.get("item_contract_degraded") or ():
        if isinstance(row, Mapping):
            add(row.get("item_key"), row.get("rule"), "producer_attribution.item_contract_degraded",
                kept_as=row.get("as"))
    for row in attribution.get("item_contract_drops") or ():
        if isinstance(row, Mapping):
            add(row.get("item_key"), row.get("rule"), "producer_attribution.item_contract_drops")
    for row in attribution.get("merged_duplicate_entities") or ():
        if isinstance(row, Mapping):
            for merged in row.get("merged_keys") or ():
                add(merged, "merged_duplicate_entity", "producer_attribution.merged_duplicate_entities",
                    merged_into=row.get("kept_key"))
    return rules


def dispositions(submitted: Sequence[Mapping[str, Any]], result: UnderstandingResult) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """What became of every row the repair submitted, one line each.

    The validator already says what it did, but it says it in three places -- the counts,
    the twenty-row lists of refusals, and the rows themselves -- and only the rows are
    complete. A repair that submitted 300 rows could not be audited against a list that
    keeps its first twenty, so the run writes the whole ledger: for each submitted row,
    which stored row it became, under which kind, with which fields changed, which of the
    citations it brought survived, and the rule that decided it. A row nothing names is
    recorded as unnamed rather than left looking like a plain drop.
    """
    known = _known_evidence(result)
    rules = _named_rules(result.producer_attribution or {})
    stored = _items(result)
    # Rows this run could not establish are not missing from the ledger: they are in it
    # with the destination they went to, because "dropped" would read as lost and
    # "kept" would read as a statement about the material.
    diagnostics: dict[tuple, Mapping[str, Any]] = {}
    for row in getattr(result, "run_diagnostics", ()) or ():
        if not isinstance(row, Mapping):
            continue
        # A refused row keeps its key and its sentence and may come back under another
        # kind (an entity whose class could not be read arrives as `unknown`), so the
        # ledger matches it by key and meaning, not by the kind the validator chose.
        for identity in ((row.get("kind"), row.get("key"), row.get("meaning")),
                         (row.get("key"), row.get("meaning"))):
            diagnostics.setdefault(identity, row)
    taken: set[int] = set()

    def find(submitted_row: Mapping[str, Any], *, same_kind_only: bool) -> int | None:
        want = _canonical(_comparable(submitted_row))
        key = submitted_row.get("key")
        kind = submitted_row.get("kind")
        for position, candidate in enumerate(stored):
            if position in taken:
                continue
            if _canonical(_comparable(candidate)) == want:
                return position
        for position, candidate in enumerate(stored):
            if position in taken or candidate.get("key") != key:
                continue
            if same_kind_only and candidate.get("kind") != kind:
                continue
            return position
        return None

    rows: list[dict[str, Any]] = []
    counts = {"submitted": len(submitted), "kept": 0, "changed": 0, "degraded": 0,
              "dropped": 0, "run_diagnostic": 0}
    for index, row in enumerate(submitted):
        cited = [ref for ref in (row.get("evidence_refs") or ()) if isinstance(ref, str)]
        entry = {"index": index, "kind": row.get("kind"), "key": row.get("key"),
                 "meaning": row.get("meaning"),
                 "evidence": {"submitted": cited, "not_in_evidence": [ref for ref in cited if ref not in known]}}
        carried = _degraded_rule(row)
        if carried:
            # A row that arrives already degraded is not this pass`s doing, and a ledger that
            # called it `kept` would hide the reason a handoff has to refuse it.
            entry["carried_degradation"] = carried
        moved = (diagnostics.get((row.get("kind"), row.get("key"), row.get("meaning")))
                 or diagnostics.get((row.get("key"), row.get("meaning"))))
        if moved is not None:
            degradation = moved.get("degradation") if isinstance(moved.get("degradation"), Mapping) else {}
            counts["run_diagnostic"] += 1
            entry.update({"outcome": "run_diagnostic", "item_id": None, "kind_out": row.get("kind"),
                          "reason": moved.get("reason"),
                          "diagnostic_class": degradation.get("class"),
                          "missing": list(moved.get("missing") or ()),
                          "destination": moved.get("destination") or "run_evidence",
                          "evidence": {**entry["evidence"], "kept": []},
                          "source_origin": _source_origin_entry(
                              row.get("source_origin"), moved.get("source_origin"))})
            rows.append(entry)
            continue
        position = find(row, same_kind_only=True)
        if position is None:
            # A row that survived under another kind is the validator keeping the statement
            # and refusing the shape it asked for; that is a degradation, not a vanish.
            position = find(row, same_kind_only=False)
        if position is None:
            reasons = rules.get(str(row.get("key"))) or []
            counts["dropped"] += 1
            entry.update({"outcome": "dropped", "item_id": None, "kind_out": None,
                          "reason": reasons[0]["rule"] if reasons else "not recorded by the validator",
                          "reasons": reasons,
                          "source": reasons[0]["source"] if reasons else "unrecorded",
                          "evidence": {**entry["evidence"], "kept": []},
                          "source_origin": _source_origin_entry(
                              row.get("source_origin"), None)})
            rows.append(entry)
            continue
        taken.add(position)
        stored_row = stored[position]
        kept_refs = [ref for ref in (stored_row.get("evidence_refs") or ()) if isinstance(ref, str)]
        entry["item_id"] = stored_row.get("item_id")
        entry["kind_out"] = stored_row.get("kind")
        # Who the validator says wrote this row, kept beside the content verdict so a
        # `kept` row can still be traced to its step and its call.
        entry["source_origin"] = _source_origin_entry(
            row.get("source_origin"), stored_row.get("source_origin"))
        entry["evidence"] = {**entry["evidence"], "kept": kept_refs,
                             "refused": [ref for ref in cited if ref not in kept_refs]}
        before, after = _comparable(row), _comparable(stored_row)
        fields = {name: {"before": before.get(name), "after": after.get(name)}
                  for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)}
        rule = _degraded_rule(stored_row)
        if not fields:
            counts["kept"] += 1
            entry.update({"outcome": "kept", "reason": None, "fields": {}, "source": None})
        elif rule or stored_row.get("kind") != row.get("kind"):
            counts["degraded"] += 1
            named = rules.get(str(row.get("key"))) or []
            entry.update({"outcome": "degraded", "fields": fields,
                          "reason": rule or (named[0]["rule"] if named else "not recorded by the validator"),
                          "reasons": named,
                          "source": ("producer_attribution.item_contract_degraded" if rule
                                     else (named[0]["source"] if named else "unrecorded"))})
        else:
            counts["changed"] += 1
            named = rules.get(str(row.get("key"))) or []
            entry.update({"outcome": "changed", "fields": fields,
                          "reason": named[0]["rule"] if named else None,
                          "reasons": named,
                          "source": named[0]["source"] if named else None})
        rows.append(entry)
    counts["unrecorded"] = sum(1 for row in rows if row.get("source") == "unrecorded")
    counts["carried_degradation"] = sum(1 for row in rows if row.get("carried_degradation"))
    counts["changed_without_a_rule"] = sum(1 for row in rows
                                          if row.get("outcome") == "changed" and not row.get("reason"))
    # The rows that left the candidate on purpose, counted under the name a reader of
    # this ledger looks for: nothing here was dropped.
    counts["moved_to_run_evidence"] = counts["run_diagnostic"]
    return rows, counts


def write_disposition(path: Path | str, *, header: Mapping[str, Any],
                      rows: Sequence[Mapping[str, Any]], counts: Mapping[str, int]) -> dict[str, Any]:
    """Write the ledger beside the run's other artifacts, and return what the record keeps.

    The summary carries the counts, the path and the digest of the bytes written: a reader
    who has the file can prove it is the file this run wrote, and a reader who has only the
    record still knows how many rows went each way.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"header": dict(header), "counts": dict(counts), "rows": list(rows)},
                         ensure_ascii=False, indent=1)
    raw = payload.encode("utf-8")
    target.write_bytes(raw)
    return {"path": str(target), "sha256": _sha(raw), "rows": len(rows), "counts": dict(counts)}


def run_semantic_method(methods: Any, request: Any, *, source_root: Path | str, provider: Any,
                        extraction_mode: str, label: str, recorder: Any | None = None,
                        repairs: RepairSpec | None = None,
                        component_id: str = SEMANTIC_COMPONENT,
                        base_root: Path | str | None = None,
                        disposition_path: Path | str | None = None,
                        record_dir: Path | str | None = None,
                        probe_whole_answer: bool = False,
                        authorised_budget: Sequence[int] | None = None,
                        concepts: Any | None = None,
                        verifier_provider: Any | None = None):
    """Run one semantic request against one registered method, and keep its record.

    `methods` is the component store a workbench owns. The lease is taken before anything is
    read and released in `finally`, so a failed run leaves no method pinned; the record says
    whether the release happened. `base_root` is the product Skill tree the method is laid
    over -- see `materialize_method`; omit it and the run reads this product's own tree.

    `disposition_path` names the file the run writes its per-row ledger to -- every row the
    repair submitted, what became of it and why. It is optional because a run without it is
    still a run; it is not optional for a run whose result is handed on, because the
    validator's twenty-row refusal lists are not a record of three hundred rows.

    `record_dir` names a folder the run writes **every row set whole** into: the reading's own
    answer, the repair's rows, what the validator was handed, what it accepted, and the rows
    nothing accepted. `run-record.json` beside them carries each file's digest, what each set is
    compared with, the size of the room the repair was re-read in, and the sum -- so a slice
    handed to the Wiki can be checked against the result it was cut from instead of standing in
    for it.

    `probe_whole_answer` re-validates the reading's whole row list through the same entry point,
    once with the room the answer used and once with the per-answer default, and keeps both
    verdicts in the record. It is off by default because it is a measurement, not a step.

    `concepts` is the concept set of the scope this request is read for. The run records
    it, because a card read against eleven types and a card read against thirteen are
    different readings and `package_sha256` cannot tell them apart.

    `verifier_provider` is the separate reader that checks the candidate in its own
    context; the host supplies its budget, exactly as it does for the reading.

    `authorised_budget` is the ceiling this run's reading was authorised for -- 384/384 for a
    merged unit-split answer, 64/128 for a single one -- and it is the only way a repair gets a
    room wider than the per-answer default. The seam never infers it from the row count: a run
    that wants to hand back more than the default has to say what it was allowed to read.
    """
    from .understand_only import UnderstandPort

    if extraction_mode not in EXTRACTION_MODES:
        raise SemanticMethodError("extraction_mode_unsupported", extraction_mode)
    if repairs is not None and not repairs.allowed_for(label):
        # Scope is checked before the lease: a repair that does not apply to this card must
        # not even hold the method.
        raise SemanticMethodError("repair_out_of_scope",
                                  f"{repairs.name} does not apply to {label!r}")
    lease = methods.acquire_method(component_id)
    snapshot = lease.__enter__()
    root: Path | None = None
    released = False
    try:
        root = materialize_method(snapshot, base_root=base_root)
        port = UnderstandPort(skill_root=root, extraction_mode=extraction_mode)
        read = {"semantic_provider": provider, "recorder": recorder}
        if concepts is not None:
            read["concepts"] = concepts
        if verifier_provider is not None:
            read["verifier_provider"] = verifier_provider
        original = port.understand(request, source_root=source_root, **read)
        identity = {
            "method": {"component_id": snapshot["component_id"], "version": snapshot["version"],
                       "package_sha256": snapshot["package_sha256"],
                       "skill_name": (snapshot.get("manifest") or {}).get("skill_name")},
            "extraction_mode": extraction_mode,
            "repairs": (repairs.identity(enabled=True) if repairs is not None
                        else {"enabled": False, "reason": "no repair was named for this run"}),
            "sources": [{"source_id": row.source_id, "source_sha256": row.source_sha256,
                         "relative_path": row.relative_path,
                         "extraction_status": getattr(row, "extraction_status", None)}
                        for row in original.source_inventory],
            "builtin_skills": {
                "root": str(Path(base_root or BUILTIN_SKILLS)),
                "files": builtin_skill_digests(root, tuple(
                    f"{(snapshot.get('manifest') or {}).get('skill_name')}/{name}"
                    for name in (snapshot.get("files") or {})))},
            "concepts": concept_set_identity(
                STARTER_PACK if concepts is None else concepts),
            "implementation": _implementation_identity(),
            "label": label,
            "provider": {"provider_id": getattr(provider, "provider_id", None),
                         "mode": getattr(provider, "mode", None),
                         "model": getattr(provider, "model", None)},
        }
        if repairs is None:
            # One object, not two: there is no second form of an answer nobody reshaped. Its
            # rows are the model's; only the attribution gains the run's identity, which is a
            # fact about this run and not a change to what the answer says.
            result = original = carry_run_identity(original, identity)
            diff = ()
            budget = segment_budget_for(original, authorised=authorised_budget)
            validation = {"ran": False, "reason": "repairs disabled: the result is the model's own",
                          "validator": None, "segment_budget": budget}
            probe = None
        else:
            items = list(repairs.apply(original))
            # Clamped by the ceiling the caller declares for this run, never by the row count
            # alone: a repair that hands back more rows than the run was authorised to hold is
            # refused by the validator, whole, and names the segment.
            budget = segment_budget_for(original, authorised=authorised_budget)
            # The seed keeps the candidate's identity and none of its rows: the scope the
            # reading was made for travels with the repaired result, and the rows the model
            # answered do not. Dropping the whole candidate took the scope with it, and a
            # repaired result then could not be handed to a Wiki read for that scope at all.
            seed = replace(original, semantic_candidate=(
                replace(original.semantic_candidate, items=()) if original.semantic_candidate else None))
            # The same typed validator the model's own answer goes through. A repaired
            # result is re-validated, never promoted on the strength of the old pass.
            if not items:
                # A reading whose every row was run evidence has nothing to hand back, and
                # that is a result rather than an error: the run says it validated no rows
                # and keeps the original's diagnostics, so nothing is lost by having none.
                result = carry_run_identity(seed, identity)
                diff = ()
                validation = {"ran": True, "validator": "UnderstandPort.attach_producer_items",
                              "items_submitted": 0, "items_accepted": 0,
                              "original_items": len(_items(original)),
                              "reason": "the repair returned no rows to validate",
                              "segment_budget": budget}
                probe = None
            else:
                result = port.attach_producer_items(
                    seed, producer_kind="CATALYST_NATIVE_MODEL",
                    producer_invocation_id=f"{request.request_id}:repair:{repairs.name}:{repairs.version}",
                    items=items, producer_model_id=getattr(provider, "model", None),
                    # The room the answer itself was accepted in, not the narrower per-answer
                    # default: a repair hands back a subset of these rows and can need no more.
                    segment_budget=(budget["entities"], budget["other_items"]))
                diff = tuple(diff_items(_items(original), _items(result)))
                validation = {"ran": True, "validator": "UnderstandPort.attach_producer_items",
                              "items_submitted": len(items),
                              "items_accepted": len(_items(result)),
                              "original_items": len(_items(original)),
                              "segment_budget": budget}
                probe = (whole_answer_probe(port, seed, original, budget,
                                            model_id=getattr(provider, "model", None))
                         if probe_whole_answer else None)
            # The derived package a Wiki read receives is the only artifact a later reader is
            # guaranteed to hold, so the run's identity travels inside it as well as beside it.
            result = carry_run_identity(result, identity)
        if record_dir is None:
            record = {"written": False, "reason": "no record_dir was named for this run"}
        else:
            record = write_record(Path(record_dir), original=original,
                                  repaired=(items if repairs is not None else _items(original)),
                                  submitted=(items if repairs is not None else _items(original)),
                                  stored=result, identity=identity, validation=validation,
                                  segment_budget=budget, probe=probe)
        if disposition_path is None:
            disposition = {"written": False,
                           "reason": "no disposition_path was named for this run"}
        elif repairs is None:
            # Without a repair the rows the model submitted are not retained: `understand`
            # returns what the validator accepted, so there is nothing to compare against
            # and a ledger here would be an invention.
            disposition = {"written": False, "reason": "no repair was named for this run: "
                                                       "the submitted rows are not retained"}
        else:
            rows, counts = dispositions(items, result)
            disposition = {"written": True, **write_disposition(
                disposition_path,
                header={"interface": SEMANTIC_INTERFACE,
                        "request_id": getattr(request, "request_id", None),
                        # A reader who opens only this file has to be able to tell a kept row
                        # from an unchanged one, so the baseline is named and not implied.
                        "compared_with": {
                            "baseline": ("each row of this ledger is one submitted row, compared with "
                                         "the row the validator stored for it; `kept` means the "
                                         "submitted row survived unchanged, not that nothing "
                                         "changed anywhere"),
                            "submitted": "the rows this run handed to the validator",
                            "stored": "the rows the validator accepted as statements about the material",
                            "run_diagnostic": ("a submitted row this run could not establish: kept in "
                                               "run evidence (run-diagnostics.json) with its reason, "
                                               "never a candidate and never counted as dropped"),
                            "source_origin": ("a row's tag says which step wrote it and in which "
                                              "call; it is carried on every ledger row and left "
                                              "out of the content comparison, so `kept` means the "
                                              "row's words did not change, not that its source did"),
                            "other_record": ("run-record.json holds original vs repaired, repaired vs "
                                             "stored and the unsubmitted rows whole")},
                        "digests": {name: entry["sha256"]
                                    for name, entry in ((record.get("files") or {}) if isinstance(record, Mapping)
                                                        else {}).items()},
                        "segment_budget": dict(budget),
                        "method": identity["method"],
                        "extraction_mode": extraction_mode,
                        "repairs": identity["repairs"],
                        "validator": validation.get("validator"),
                        "ruled_by": ["producer_attribution.item_contract_degraded",
                                     "producer_attribution.item_contract_drops",
                                     "producer_attribution.merged_duplicate_entities"],
                        "unrecorded": "not recorded by the validator"},
                rows=rows, counts=counts)}
    finally:
        if root is not None:
            shutil.rmtree(root, ignore_errors=True)
        lease.__exit__(None, None, None)
        released = True
    return SemanticMethodRun(identity=identity, original=original, result=result, diff=diff,
                             validation=validation, disposition=disposition, record_files=record,
                             lease={"acquired": True, "released": released,
                                    "component_id": component_id, "version": snapshot["version"],
                                    "package_sha256": snapshot["package_sha256"]})
