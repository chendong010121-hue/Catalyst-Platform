"""Small project-scoped Wiki stores consumed by Catalyst's existing Harness."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from typing import Any, Callable, Mapping, Sequence

from .ontology_concepts import concept_set_of, concept_state_is_valid, empty_concept_state
from .understand_models import SOURCE_CATEGORIES
from .ontology_types import ConceptSet


class WikiError(RuntimeError):
    """Base error for a scoped Wiki operation."""


class WikiUnavailable(WikiError):
    """The requested Wiki backend is disconnected or cannot be read."""


class WikiScopeError(WikiError):
    """A source or identifier is outside the configured project boundary."""


class WikiSourceIdentityAmbiguous(WikiScopeError):
    """Configured roots cannot safely distinguish a source from another source."""


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_RULE = re.compile(r"^\s*(rule|condition|exception|unknown)\s*:\s*(.*?)\s*$", re.IGNORECASE)
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_STOP_WORDS = {
    "a", "an", "and", "are", "can", "could", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "please",
    "show", "tell", "that", "the", "this", "to", "what", "which", "who",
    "with", "you", "your", "capability", "capabilities", "tool", "tools",
}
_SYNONYMS = {
    "heading": "title", "headings": "title", "label": "title", "labels": "title",
    "name": "title", "names": "title", "document": "file", "documents": "file",
    "note": "file", "notes": "file", "read": "read", "reading": "read",
    "files": "file", "processed": "process", "processing": "process",
}
# One Markdown file is one text part, so it carries the extractor's text bound:
# a 2 MiB gate here refused documents the reader itself could read.
_MAX_SOURCE_BYTES = 8 * 1024 * 1024
# Native documents are budgeted by what extraction reads, not by how many images
# they carry: one real deck is 34.5 MiB of file and 1.17 MiB of text.
_MAX_NATIVE_BYTES = 128 * 1024 * 1024
# A reader that suddenly returns a third of the units it returned before has
# regressed; the same bytes do not lose a third of their text.
_SHRINK_RATIO = 0.7
_KNOWLEDGE_READ_MODES = {
    "source_discovery",
    "grounded_claims",
    "accepted_enterprise_semantics",
}
_UNRESOLVED_APPLICABILITY = re.compile(
    r"(?i)(?:owner\s+approval|approval\s+required|owner\s+must\s+approve|"
    r"only\s+after\s+approval|unknown\s+outside|unverified\s+condition)"
)


def _digest(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _tokens(value: str) -> set[str]:
    result: set[str] = set()
    for raw in _TOKEN.findall(value.casefold()):
        if any("\u4e00" <= char <= "\u9fff" for char in raw):
            result.update(char for char in raw if char.strip())
            result.update(raw[index:index + 2] for index in range(max(0, len(raw) - 1)))
            continue
        word = raw
        if word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("s") and len(word) > 3 and not word.endswith("ss"):
            word = word[:-1]
        word = _SYNONYMS.get(word, word)
        if len(word) > 1 and word not in _STOP_WORDS:
            result.add(word)
    return result


def _score(query_terms: set[str], text: str) -> int:
    if not query_terms:
        return 0
    return len(query_terms & _tokens(text))


_DOCUMENT_SCHEMA_VERSION = 2
_SUPPORTED_DOCUMENT_SCHEMA_VERSIONS = (1, _DOCUMENT_SCHEMA_VERSION)
_SEMANTIC_SCHEMA_VERSION = 2
_SUPPORTED_SEMANTIC_SCHEMA_VERSIONS = (1, _SEMANTIC_SCHEMA_VERSION)
_ARTIFACT_MARKER = "_artifact"
_VERSION_PAYLOAD_FIELDS = ("meanings",)
_CANDIDATE_PAYLOAD_FIELDS = ("entries", "understanding_result", "evidence_mappings")
_ARTIFACT_KEY_FIELDS = {"meanings": "meaning_id"}


def _empty_semantic_state() -> dict[str, Any]:
    return {
        "schema_version": _SEMANTIC_SCHEMA_VERSION,
        "candidates": {},
        "evaluations": {},
        "decisions": {},
        "accepted_versions": {},
        "active_version_id": None,
        "transitions": [],
    }


_VERSION_DIFF_FIELDS = (
    "added_meaning_ids",
    "changed_meaning_ids",
    "removed_meaning_ids",
    "evidence_added_meaning_ids",
    "evidence_removed_meaning_ids",
    "carried_meaning_ids",
)


def _valid_version_diff(value: Any) -> bool:
    """A stored diff is what a reviewer approved, so a broken one is a broken store."""
    if value is None:
        return True
    if not isinstance(value, dict):
        return False
    return all(
        isinstance(value.get(field), list)
        and all(isinstance(item, str) for item in value[field])
        for field in _VERSION_DIFF_FIELDS
    )


def _valid_semantic_state(value: Any, *, scope_id: str | None = None) -> bool:
    if (
        not isinstance(value, dict)
        or type(value.get("schema_version")) is not int
        or value["schema_version"] not in _SUPPORTED_SEMANTIC_SCHEMA_VERSIONS
    ):
        return False
    for field in ("candidates", "evaluations", "decisions", "accepted_versions"):
        if not isinstance(value.get(field), dict):
            return False
    if not isinstance(value.get("transitions"), list):
        return False
    active = value.get("active_version_id")
    if active is not None and (not isinstance(active, str) or active not in value["accepted_versions"]):
        return False
    if any(not isinstance(key, str) or not isinstance(row, dict) for field in (
        "candidates", "evaluations", "decisions", "accepted_versions"
    ) for key, row in value[field].items()):
        return False

    def valid_digest(item: Any) -> bool:
        return isinstance(item, str) and re.fullmatch(r"[0-9a-f]{64}", item) is not None

    def valid_reference(item: Any) -> bool:
        return isinstance(item, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,256}", item) is not None

    def valid_evidence(item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        return bool(
            isinstance(item.get("source_id"), str) and item["source_id"]
            and valid_digest(item.get("source_revision"))
            and (item.get("claim_id") is None or isinstance(item.get("claim_id"), str))
            and type(item.get("line_start")) is int and item["line_start"] > 0
            and type(item.get("line_end")) is int and item["line_end"] >= item["line_start"]
            and valid_digest(item.get("span_sha256"))
            and item.get("evidence_class") in {"observed_from_source", "inferred", "unresolved"}
        )

    def valid_meaning(key: Any, row: Any) -> bool:
        if not isinstance(key, str) or not isinstance(row, dict) or row.get("meaning_id") != key:
            return False
        if not isinstance(row.get("kind"), str) or not isinstance(row.get("key"), str) or not isinstance(row.get("meaning"), str):
            return False
        evidence = row.get("evidence")
        refs = evidence if isinstance(evidence, list) and evidence else [row]
        if not refs or not all(valid_evidence(ref) for ref in refs):
            return False
        if isinstance(evidence, list) and evidence:
            primary = refs[0]
            return all(row.get(field) == primary.get(field) for field in (
                "source_id", "source_revision", "claim_id", "line_start", "line_end", "span_sha256", "evidence_class"
            ))
        return True

    for key, row in value["candidates"].items():
        if row.get("candidate_type") == "understand_handoff.v1":
            if (
                row.get("candidate_id") != key
                or not isinstance(row.get("scope_id"), str)
                or (scope_id is not None and row.get("scope_id") != scope_id)
                or row.get("authority") != "CANDIDATE_ONLY"
                or row.get("status") not in {"PROPOSED", "PROPOSED_NEEDS_MAPPING"}
                or row.get("mapping_status") not in {"COMPLETE", "NEEDS_MAPPING"}
                or not valid_digest(row.get("understanding_result_sha256"))
                or not isinstance(row.get("understanding_result"), dict)
                or not isinstance(row.get("source_bindings"), list)
                or not isinstance(row.get("evidence_mappings"), list)
                or row.get("latest_evaluation_id") is not None
                or row.get("latest_decision_id") is not None
            ):
                return False
            for binding in row["source_bindings"]:
                if (
                    not isinstance(binding, dict)
                    or not isinstance(binding.get("producer_source_id"), str)
                    or not isinstance(binding.get("relative_path"), str)
                    or not valid_reference(binding.get("source_revision"))
                    or not valid_digest(binding.get("source_sha256"))
                    or binding.get("status") not in {
                        "STAGED", "SOURCE_UNAVAILABLE", "UNSUPPORTED_SOURCE_TYPE",
                        "SOURCE_REVISION_MISMATCH", "SOURCE_NOT_STAGEABLE",
                    }
                ):
                    return False
                if binding.get("wiki_source_id") is not None and not isinstance(binding.get("wiki_source_id"), str):
                    return False
            for evidence in row["evidence_mappings"]:
                if (
                    not isinstance(evidence, dict)
                    or not isinstance(evidence.get("evidence_id"), str)
                    or not valid_reference(evidence.get("source_revision"))
                    or not valid_digest(evidence.get("span_sha256"))
                    or not isinstance(evidence.get("locator"), str)
                    or evidence.get("mapping_status") not in {
                        "MAPPED", "NEEDS_MAPPING", "SOURCE_REVISION_MISMATCH",
                        "SOURCE_UNAVAILABLE", "UNSUPPORTED_SOURCE_TYPE",
                        "SOURCE_NOT_STAGEABLE", "UNKNOWN_SOURCE_REFERENCE", "SOURCE_IDENTITY_MISMATCH",
                        "SPAN_DIGEST_MISMATCH", "ANCHOR_MISMATCH",
                    }
                ):
                    return False
            continue
        if (
            row.get("candidate_id") != key
            or not isinstance(row.get("scope_id"), str)
            or (scope_id is not None and row.get("scope_id") != scope_id)
            or not isinstance(row.get("source_id"), str)
            or not valid_digest(row.get("source_revision"))
            or not isinstance(row.get("entries"), list)
            or not all(valid_meaning(entry.get("meaning_id"), entry) for entry in row["entries"] if isinstance(entry, dict))
            or any(not isinstance(entry, dict) for entry in row["entries"])
        ):
            return False
        if any(entry.get("source_id") != row.get("source_id") or entry.get("source_revision") != row.get("source_revision") for entry in row["entries"]):
            return False
        latest_evaluation = row.get("latest_evaluation_id")
        if latest_evaluation is not None and (
            latest_evaluation not in value["evaluations"]
            or value["evaluations"][latest_evaluation].get("candidate_id") != key
        ):
            return False
        latest_decision = row.get("latest_decision_id")
        if latest_decision is not None and (
            latest_decision not in value["decisions"]
            or value["decisions"][latest_decision].get("candidate_id") != key
        ):
            return False
    for key, row in value["evaluations"].items():
        if key != row.get("evaluation_id") or row.get("candidate_id") not in value["candidates"]:
            return False
    for key, row in value["decisions"].items():
        if (
            key != row.get("decision_id")
            or row.get("candidate_id") not in value["candidates"]
            or row.get("evaluation_id") not in value["evaluations"]
            or row.get("decision") not in {"ACCEPTED", "REJECTED", "DEFERRED", "NEEDS_REVIEW"}
        ):
            return False
    for key, row in value["accepted_versions"].items():
        decision = value["decisions"].get(row.get("decision_id"))
        if (
            row.get("version_id") != key
            or not isinstance(row.get("meanings"), dict)
            or (scope_id is not None and row.get("scope_id") != scope_id)
            or row.get("candidate_id") not in value["candidates"]
            or not isinstance(decision, dict) or decision.get("decision") != "ACCEPTED"
            or decision.get("version_id") != key
            or (row.get("parent_version_id") is not None and row.get("parent_version_id") not in value["accepted_versions"])
            or not _valid_version_diff(row.get("diff"))
            or not all(valid_meaning(meaning_id, meaning) for meaning_id, meaning in row["meanings"].items())
        ):
            return False
    transition_ids = set()
    for row in value["transitions"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("transition_id"), str)
            or row["transition_id"] in transition_ids
            or not isinstance(row.get("run_id"), str)
            or not isinstance(row.get("operation"), str)
            or row.get("status") not in {"started", "pending_completion", "awaiting_terminal", "committed", "incomplete", "recovered_rollback"}
        ):
            return False
        transition_ids.add(row["transition_id"])
    return True


def _empty_document(scope_id: str) -> dict[str, Any]:
    return {
        "schema_version": _DOCUMENT_SCHEMA_VERSION,
        "scope_id": scope_id,
        "sources": {},
        "claims": {},
    }


def _valid_document(value: Any, scope_id: str) -> bool:
    return bool(
        isinstance(value, dict)
        and type(value.get("schema_version")) is int
        and value["schema_version"] in _SUPPORTED_DOCUMENT_SCHEMA_VERSIONS
        and value.get("scope_id") == scope_id
        and isinstance(value.get("sources"), dict)
        and isinstance(value.get("claims"), dict)
    )


def _migrate_document(document: dict[str, Any]) -> dict[str, Any]:
    """Lift a document read at a revision this build names to the shape this process writes.

    The lift is in memory only. A reader that changes nothing leaves the file exactly as it
    found it, so the previous release can still open the same store.

    A revision this build does not know is refused, not relabelled: rewriting an unknown
    version to the current one would claim a record satisfies a contract nothing checked.
    """
    version = document.get("schema_version")
    if type(version) is not int or version not in _SUPPORTED_DOCUMENT_SCHEMA_VERSIONS:
        raise WikiUnavailable(
            "the local Wiki document declares a schema version this build does not read"
        )
    semantic = document.get("semantic")
    if semantic is not None:
        declared = semantic.get("schema_version") if isinstance(semantic, dict) else None
        if type(declared) is not int or declared not in _SUPPORTED_SEMANTIC_SCHEMA_VERSIONS:
            raise WikiUnavailable(
                "the local Wiki semantic ledger declares a schema version this build does not read"
            )
    document["schema_version"] = _DOCUMENT_SCHEMA_VERSION
    if isinstance(semantic, dict):
        semantic["schema_version"] = _SEMANTIC_SCHEMA_VERSION
    return document


_LONG_PATH_PREFIX = "\\\\?\\"


def _os_path(path: Path) -> str:
    """The path as Windows must receive it to open past its 260-character limit.

    The index sits at whatever workspace depth the caller chose, and a version's meanings are
    two directories below it, so the readable layout can outrun ``MAX_PATH`` on a deeply
    nested workspace. The extended-length form lifts that limit and changes nothing on disk;
    every other platform, and every short path, gets the plain path.
    """
    text = os.fspath(path)
    if os.name != "nt" or len(text) < 240 or text.startswith(_LONG_PATH_PREFIX):
        return text
    resolved = os.fspath(path.resolve())
    return resolved if resolved.startswith(_LONG_PATH_PREFIX) else _LONG_PATH_PREFIX + resolved


def _unlink_quietly(path: Path) -> None:
    try:
        os.unlink(_os_path(path))
    except FileNotFoundError:
        pass


def _artifact_target(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or relative.startswith("/") or ":" in relative:
        raise WikiUnavailable("the local Wiki artifact reference is not a relative path")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise WikiUnavailable("the local Wiki artifact reference leaves the store")
    target = root.joinpath(*parts).resolve()
    if not target.is_relative_to(root.resolve()):
        raise WikiUnavailable("the local Wiki artifact reference leaves the store")
    return target


def _artifact_layout(field: str, value: Any) -> tuple[str, Any]:
    """Choose the on-disk shape for one payload field: keyed rows, ordered rows, or one value."""
    if isinstance(value, list) and all(isinstance(row, dict) for row in value):
        return "sequence", list(value)
    key_field = _ARTIFACT_KEY_FIELDS.get(field)
    if (
        isinstance(value, dict)
        and key_field
        and all(isinstance(row, dict) and row.get(key_field) == key for key, row in value.items())
    ):
        return "mapping", [value[key] for key in sorted(value)]
    return "json", value


def _artifact_bytes(kind: str, payload: Any) -> bytes:
    if kind == "json":
        return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in payload
    ).encode("utf-8")


def _write_artifact(root: Path, relative: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    target = _artifact_target(root, relative)
    try:
        if os.path.isfile(_os_path(target)):
            with open(_os_path(target), "rb") as stream:
                if hashlib.sha256(stream.read()).hexdigest() == digest:
                    return digest
    except OSError:
        pass
    os.makedirs(_os_path(target.parent), exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(_os_path(temporary), "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(_os_path(temporary), _os_path(target))
    except OSError as exc:
        raise WikiUnavailable("the local Wiki artifact could not be written") from exc
    finally:
        _unlink_quietly(temporary)
    return digest


class _ArtifactError(WikiUnavailable):
    """One artifact failed its own contract; the reason travels as a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite number in a stored artifact: {value}")


def _decode_artifact(descriptor: Any, content: bytes) -> Any:
    """The one place an artifact's bytes become the record its reader expects.

    Both the reader and the health check call this, so "verify says OK" and "the record
    reads back" are the same statement: the descriptor's kind, format, count, key field and
    digest, and the bytes' JSON shape, are judged once.
    """
    if not isinstance(descriptor, dict):
        raise _ArtifactError("descriptor_unreadable", "the local Wiki stores an unreadable artifact reference")
    relative = descriptor.get("path")
    expected = descriptor.get("sha256")
    kind = descriptor.get("kind")
    key_field = descriptor.get("key_field")
    count = descriptor.get("count")
    if (
        not isinstance(relative, str)
        or not isinstance(expected, str)
        or not re.fullmatch(r"[0-9a-f]{64}", expected)
        or kind not in {"sequence", "mapping", "json"}
    ):
        raise _ArtifactError("descriptor_unreadable", "the local Wiki stores an unreadable artifact reference")
    if descriptor.get("format") != ("json" if kind == "json" else "jsonl"):
        raise _ArtifactError("format_mismatch", "a stored Wiki artifact does not declare the format its kind implies")
    if type(count) is not int or count < 0:
        raise _ArtifactError("descriptor_unreadable", "a stored Wiki artifact does not declare a row count")
    if hashlib.sha256(content).hexdigest() != expected:
        raise _ArtifactError("digest_mismatch", "a stored Wiki artifact does not match its recorded digest")
    try:
        text = content.decode("utf-8")
        if kind == "json":
            return json.loads(text, parse_constant=_reject_constant)
        rows = [json.loads(line, parse_constant=_reject_constant)
                for line in text.splitlines() if line.strip()]
    except (UnicodeDecodeError, ValueError) as exc:
        raise _ArtifactError("unreadable", "a stored Wiki artifact is unreadable") from exc
    if kind == "sequence":
        if any(not isinstance(row, dict) for row in rows):
            raise _ArtifactError("rows_not_objects", "a stored Wiki artifact holds rows that are not records")
    else:
        if not isinstance(key_field, str) or any(
            not isinstance(row, dict) or not isinstance(row.get(key_field), str) for row in rows
        ):
            raise _ArtifactError("keys_missing", "a stored Wiki artifact no longer keys its rows")
        if len({row[key_field] for row in rows}) != len(rows):
            raise _ArtifactError("duplicate_row_key", "a stored Wiki artifact repeats a row key")
    if count != len(rows):
        raise _ArtifactError("count_mismatch", "a stored Wiki artifact holds a different number of rows than it records")
    if kind == "mapping":
        return {row[key_field]: row for row in rows}
    return rows


def _artifact_content(root: Path, descriptor: Any) -> bytes:
    """The bytes a descriptor names, with the reference checked before the disk is touched."""
    relative = descriptor.get("path") if isinstance(descriptor, dict) else None
    if not isinstance(relative, str) or not relative:
        raise _ArtifactError("descriptor_unreadable", "the local Wiki stores an unreadable artifact reference")
    try:
        target = _artifact_target(root, relative)
    except WikiUnavailable as exc:
        raise _ArtifactError("outside_store", str(exc)) from exc
    try:
        with open(_os_path(target), "rb") as stream:
            return stream.read()
    except OSError as exc:
        raise _ArtifactError("missing", "the local Wiki is missing a stored artifact") from exc


def _read_artifact(root: Path, descriptor: Any) -> Any:
    return _decode_artifact(descriptor, _artifact_content(root, descriptor))


def _artifact_descriptors(document: dict[str, Any]) -> list[tuple[str, Any]]:
    """Every artifact the index names, labelled by the record and field that names it."""
    found: list[tuple[str, Any]] = []
    semantic = document.get("semantic")
    if not isinstance(semantic, dict):
        return found
    for holder, fields in (
        ("candidates", _CANDIDATE_PAYLOAD_FIELDS),
        ("accepted_versions", _VERSION_PAYLOAD_FIELDS),
    ):
        records = semantic.get(holder)
        if not isinstance(records, dict):
            continue
        for record_id, record in sorted(records.items()):
            if not isinstance(record, dict):
                continue
            for field in fields:
                payload = record.get(field)
                if isinstance(payload, dict) and set(payload) == {_ARTIFACT_MARKER}:
                    found.append((f"{holder}/{record_id}/{field}", payload[_ARTIFACT_MARKER]))
    return found


def _verify_artifact(root: Path, descriptor: Any) -> dict[str, Any]:
    """Read one artifact exactly as its reader would, and name the reason it fails."""
    row: dict[str, Any] = {
        "path": descriptor.get("path") if isinstance(descriptor, dict) else None,
        "status": "ok",
    }
    try:
        _read_artifact(root, descriptor)
    except _ArtifactError as exc:
        row["status"] = exc.code
    except WikiUnavailable:
        row["status"] = "unreadable"
    return row


def _artifact_files(root: Path) -> list[str]:
    """The store-relative path of every artifact-shaped file already on disk."""
    found: list[str] = []
    for directory in ("candidates", "versions"):
        base = root / directory
        if not os.path.isdir(_os_path(base)):
            continue
        for current, _directories, files in os.walk(_os_path(base)):
            text = current[len(_LONG_PATH_PREFIX):] if current.startswith(_LONG_PATH_PREFIX) else current
            for name in files:
                if name.endswith((".json", ".jsonl")):
                    found.append(f"{directory}/{Path(text, name).relative_to(base).as_posix()}")
    return sorted(found)


def _split_payload(root: Path, directory: str, field: str, value: Any) -> dict[str, Any]:
    """Write one payload beside the index under a name that carries its own digest.

    The name is the transaction boundary: content that differs lands in a different file,
    so an index that still names the old bytes keeps reading them even when a later commit
    never reaches its index write. A failed commit therefore leaves an unreferenced file,
    never a file whose bytes no longer match what the committed index promised.
    """
    kind, payload = _artifact_layout(field, value)
    suffix = "json" if kind == "json" else "jsonl"
    content = _artifact_bytes(kind, payload)
    digest = hashlib.sha256(content).hexdigest()
    relative = f"{directory}/{field}.{digest[:16]}.{suffix}"
    _write_artifact(root, relative, content)
    return {
        _ARTIFACT_MARKER: {
            "path": relative,
            "sha256": digest,
            "count": len(payload) if isinstance(payload, (list, dict)) else 1,
            "format": suffix,
            "kind": kind,
            "key_field": _ARTIFACT_KEY_FIELDS.get(field) if kind == "mapping" else None,
        }
    }


def _split_document(document: dict[str, Any], root: Path) -> dict[str, Any]:
    """Write every large semantic payload beside the index and return what the index keeps."""
    value = json.loads(_canonical_json(document))
    value["schema_version"] = _DOCUMENT_SCHEMA_VERSION
    semantic = value.get("semantic")
    if isinstance(semantic, dict):
        semantic["schema_version"] = _SEMANTIC_SCHEMA_VERSION
        candidates = semantic.get("candidates")
        if isinstance(candidates, dict):
            for candidate_id, candidate in sorted(candidates.items()):
                if not isinstance(candidate, dict):
                    continue
                for field in _CANDIDATE_PAYLOAD_FIELDS:
                    if field in candidate:
                        candidate[field] = _split_payload(root, f"candidates/{candidate_id}", field, candidate[field])
        versions = semantic.get("accepted_versions")
        if isinstance(versions, dict):
            for version_id, version in sorted(versions.items()):
                if not isinstance(version, dict):
                    continue
                for field in _VERSION_PAYLOAD_FIELDS:
                    if field in version:
                        version[field] = _split_payload(root, f"versions/{version_id}", field, version[field])
    return value


def _hydrate_document(document: dict[str, Any], root: Path) -> dict[str, Any]:
    """Read each artifact an index points at back into the record its reader expects."""
    semantic = document.get("semantic")
    if not isinstance(semantic, dict):
        return document
    for holder, fields in (
        ("candidates", _CANDIDATE_PAYLOAD_FIELDS),
        ("accepted_versions", _VERSION_PAYLOAD_FIELDS),
    ):
        records = semantic.get(holder)
        if not isinstance(records, dict):
            continue
        for record in records.values():
            if not isinstance(record, dict):
                continue
            for field in fields:
                payload = record.get(field)
                if isinstance(payload, dict) and set(payload) == {_ARTIFACT_MARKER}:
                    record[field] = _read_artifact(root, payload[_ARTIFACT_MARKER])
    return document


def _ledger_problems(document: dict[str, Any], root: Path | None = None) -> list[dict[str, Any]]:
    """Judge the index's own ledgers, after every payload they name has been read back.

    A payload this build cannot read back leaves its ledger unjudged: the artifact row already
    names those bytes, and calling the record invalid on top of that would hide the cause.
    """
    problems: list[dict[str, Any]] = []
    semantic = document.get("semantic")
    declared = semantic.get("schema_version") if isinstance(semantic, dict) else None
    if semantic is not None:
        if type(declared) is not int or declared not in _SUPPORTED_SEMANTIC_SCHEMA_VERSIONS:
            problems.append({"ledger": "semantic", "status": "schema_unsupported", "declared": declared})
            semantic = None
    if root is not None:
        try:
            _hydrate_document(document, root)
        except WikiUnavailable:
            return problems
    if isinstance(semantic, dict) and not _valid_semantic_state(semantic, scope_id=document.get("scope_id")):
        problems.append({"ledger": "semantic", "status": "ledger_invalid", "declared": declared})
    concepts = document.get("concepts")
    if concepts is not None and not concept_state_is_valid(concepts):
        problems.append({"ledger": "concepts", "status": "ledger_invalid"})
    return problems


class _JsonStore:
    def __init__(self, path: Path, scope_id: str) -> None:
        self.path = path
        self.scope_id = scope_id
        self._lock = threading.RLock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not os.path.exists(_os_path(self.path)):
                return _empty_document(self.scope_id)
            try:
                with open(_os_path(self.path), encoding="utf-8") as stream:
                    value = json.load(stream)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise WikiUnavailable("the local Wiki JSON store is unreadable") from exc
            if not _valid_document(value, self.scope_id):
                raise WikiUnavailable("the local Wiki JSON store has an unsupported or mismatched scope")
            return _migrate_document(_hydrate_document(value, self.path.parent))

    def save(self, value: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write_index(_split_document(value, self.path.parent))

    def index_digest(self) -> str | None:
        """The digest of the committed index, or nothing when this scope holds no document."""
        if not os.path.exists(_os_path(self.path)):
            return None
        try:
            with open(_os_path(self.path), "rb") as stream:
                return hashlib.sha256(stream.read()).hexdigest()
        except OSError as exc:
            raise WikiUnavailable("the local Wiki JSON store is unreadable") from exc

    def _write_index(self, index: dict[str, Any]) -> None:
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            with open(_os_path(temporary), "w", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(_os_path(temporary), _os_path(self.path))
        except OSError as exc:
            raise WikiUnavailable("the local Wiki JSON store could not be updated") from exc
        finally:
            _unlink_quietly(temporary)

    def verify(self) -> dict[str, Any]:
        """Check every artifact this index names, and name every artifact it does not."""
        with self._lock:
            report: dict[str, Any] = {
                "scope_id": self.scope_id,
                "backend": "json",
                "index_path": str(self.path),
                "index_present": os.path.exists(_os_path(self.path)),
                "artifacts": [],
                "orphans": [],
            }
            if not report["index_present"]:
                # Nothing was ever committed for this scope, so there is nothing to lose.
                return {**report, "status": "EMPTY", "artifact_count": 0}
            try:
                with open(_os_path(self.path), encoding="utf-8") as stream:
                    document = json.load(stream)
            except (OSError, UnicodeError, json.JSONDecodeError):
                return {**report, "status": "BROKEN", "artifact_count": 0,
                        "problems": [{"path": self.path.name, "status": "index_unreadable"}]}
            if not _valid_document(document, self.scope_id):
                return {**report, "status": "BROKEN", "artifact_count": 0,
                        "problems": [{"path": self.path.name, "status": "index_unsupported"}]}
            named: set[str] = set()
            for label, descriptor in _artifact_descriptors(document):
                row = {**_verify_artifact(self.path.parent, descriptor), "field": label}
                if isinstance(row.get("path"), str):
                    named.add(row["path"])
                report["artifacts"].append(row)
            report["orphans"] = [path for path in _artifact_files(self.path.parent) if path not in named]
            report["artifact_count"] = len(report["artifacts"])
            problems = [row for row in report["artifacts"] if row.get("status") != "ok"]
            problems.extend(_ledger_problems(document, self.path.parent))
            report["status"] = "BROKEN" if problems else "OK"
            if problems:
                report["problems"] = problems
            return report

    def update(self, update: Callable[[dict[str, Any]], Any]) -> Any:
        """Apply one serialized read/modify/write to the state file."""
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = self.path.with_name(f".{self.path.name}.lock")
            with open(_os_path(lock_path), "a+b") as lock_stream:
                lock_stream.seek(0, os.SEEK_END)
                if lock_stream.tell() == 0:
                    lock_stream.write(b"\0")
                    lock_stream.flush()
                lock_stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock_stream.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]

                    def unlock() -> None:
                        msvcrt.locking(lock_stream.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
                else:
                    import fcntl

                    fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)  # type: ignore[attr-defined]

                    def unlock() -> None:
                        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
                try:
                    value = self.load()
                    original = _canonical_json(value)
                    result = update(value)
                    if _canonical_json(value) != original:
                        self.save(value)
                    return result
                finally:
                    unlock()


class _SQLiteStore:
    """A second conforming local persistence adapter; it shares the same record contract."""

    def __init__(self, path: Path, scope_id: str) -> None:
        self.path = path
        self.scope_id = scope_id
        self._lock = threading.RLock()

    def _connect(self):
        """The write connection. Only `save` and `update` reach it, so only they create anything."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS wiki_state (scope_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        return connection

    def _open_readonly(self):
        """A connection that cannot change the file, so reading a store leaves its bytes alone."""
        uri = f"file:{quote(self.path.as_posix(), safe='/:')}?mode=ro"
        return sqlite3.connect(uri, uri=True, timeout=5)

    def _read_row(self) -> tuple[bool, str | None]:
        """Whether the table is there, and this scope's payload when it has a row."""
        with self._open_readonly() as connection:
            present = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'wiki_state'"
            ).fetchone()
            if present is None:
                return False, None
            row = connection.execute(
                "SELECT payload FROM wiki_state WHERE scope_id = ?", (self.scope_id,)
            ).fetchone()
        return True, None if row is None else row[0]

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return _empty_document(self.scope_id)
            try:
                present, payload = self._read_row()
            except (OSError, sqlite3.Error) as exc:
                raise WikiUnavailable("the local Wiki SQLite store is unavailable") from exc
            # A database that has no row for this scope holds nothing for this scope.
            if not present or payload is None:
                return _empty_document(self.scope_id)
            try:
                value = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise WikiUnavailable("the local Wiki SQLite store is unavailable") from exc
            if not _valid_document(value, self.scope_id):
                raise WikiUnavailable("the local Wiki SQLite store has an unsupported or mismatched scope")
            return _migrate_document(value)

    def verify(self) -> dict[str, Any]:
        """Check a store that keeps every payload inline; nothing sits beside the index here."""
        with self._lock:
            report: dict[str, Any] = {
                "scope_id": self.scope_id,
                "backend": "sqlite",
                "index_path": str(self.path),
                "index_present": os.path.exists(_os_path(self.path)),
                "artifacts": [],
                "orphans": [],
                "inline_payload": True,
                "table_present": False,
                "scope_row_present": False,
            }
            if not report["index_present"]:
                return {**report, "status": "EMPTY", "artifact_count": 0}
            try:
                present, payload = self._read_row()
            except (OSError, sqlite3.Error):
                return {**report, "status": "BROKEN", "artifact_count": 0,
                        "problems": [{"path": self.path.name, "status": "store_unreadable"}]}
            report["table_present"] = present
            report["scope_row_present"] = payload is not None
            if not present or payload is None:
                # Nothing committed for this scope is not the same finding as bytes we cannot read.
                return {**report, "status": "EMPTY", "artifact_count": 0}
            try:
                document = json.loads(payload)
            except json.JSONDecodeError:
                return {**report, "status": "BROKEN", "artifact_count": 0,
                        "problems": [{"path": self.path.name, "status": "store_unreadable"}]}
            if not _valid_document(document, self.scope_id):
                return {**report, "status": "BROKEN", "artifact_count": 0,
                        "problems": [{"path": self.path.name, "status": "index_unsupported"}]}
            problems = _ledger_problems(document)
            report["status"] = "BROKEN" if problems else "OK"
            if problems:
                report["problems"] = problems
            return report

    def index_digest(self) -> str | None:
        """The digest of this scope's committed payload, or nothing when it has no row."""
        try:
            present, payload = self._read_row()
        except (OSError, sqlite3.Error) as exc:
            raise WikiUnavailable("the local Wiki SQLite store is unavailable") from exc
        if not present or payload is None:
            return None
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def save(self, value: dict[str, Any]) -> None:
        with self._lock:
            try:
                with self._connect() as connection:
                    connection.execute(
                        "INSERT INTO wiki_state(scope_id, payload) VALUES(?, ?) "
                        "ON CONFLICT(scope_id) DO UPDATE SET payload = excluded.payload",
                        (self.scope_id, _canonical_json(value)),
                    )
            except (OSError, sqlite3.Error) as exc:
                raise WikiUnavailable("the local Wiki SQLite store could not be updated") from exc

    def update(self, update: Callable[[dict[str, Any]], Any]) -> Any:
        """Apply one SQLite transaction while preserving the shared Wiki document contract."""
        with self._lock:
            try:
                with self._connect() as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    row = connection.execute(
                        "SELECT payload FROM wiki_state WHERE scope_id = ?", (self.scope_id,)
                    ).fetchone()
                    value = _empty_document(self.scope_id) if row is None else json.loads(row[0])
                    if not _valid_document(value, self.scope_id):
                        raise WikiUnavailable("the local Wiki SQLite store has an unsupported or mismatched scope")
                    _migrate_document(value)
                    original = _canonical_json(value)
                    result = update(value)
                    _migrate_document(value)
                    payload = _canonical_json(value)
                    if payload != original:
                        connection.execute(
                            "INSERT INTO wiki_state(scope_id, payload) VALUES(?, ?) "
                            "ON CONFLICT(scope_id) DO UPDATE SET payload = excluded.payload",
                            (self.scope_id, payload),
                        )
                    connection.commit()
                    return result
            except (OSError, sqlite3.Error, json.JSONDecodeError) as exc:
                raise WikiUnavailable("the local Wiki SQLite store could not be updated") from exc


def reads_as_pending(row: Mapping[str, Any]) -> bool:
    """Whether the read itself says this row may only be read as a candidate.

    A row saved for review carries its limit on the row; a consumer that places it
    among facts is answering with something the read never confirmed.
    """
    restriction = row.get("restriction")
    return isinstance(restriction, Mapping) and restriction.get("reads_as") == "candidate_only"


class ProjectWiki:
    """Store project-scoped source snapshots and evidence for retrieval and downstream consumers."""

    def __init__(
        self,
        workspace: Path | str,
        roots: Sequence[Path | str],
        *,
        enterprise_id: str,
        project_id: str,
        backend: str = "json",
        available: bool = True,
    ) -> None:
        if not _ID.fullmatch(enterprise_id) or not _ID.fullmatch(project_id):
            raise WikiScopeError("Enterprise and project IDs must be simple local identifiers")
        self.workspace = Path(workspace).expanduser().resolve()
        self.roots = tuple(Path(root).expanduser().resolve() for root in roots)
        if not self.roots:
            raise WikiScopeError("at least one source root must be configured")
        self.enterprise_id = enterprise_id
        self.project_id = project_id
        self.scope_id = f"enterprise:{enterprise_id}/project:{project_id}"
        self.available = bool(available)
        state_root = (self.workspace / ".catalyst" / "wiki" / enterprise_id / project_id).resolve()
        if not state_root.is_relative_to(self.workspace):
            raise WikiScopeError("Wiki store path escapes the configured workspace")
        self._store: _JsonStore | _SQLiteStore
        if backend == "json":
            self.backend = backend
            self._store = _JsonStore(state_root / "wiki.json", self.scope_id)
        elif backend == "sqlite":
            self.backend = backend
            self._store = _SQLiteStore(state_root / "wiki.sqlite3", self.scope_id)
        elif backend == "unavailable":
            self.backend = backend
            self._store = _JsonStore(state_root / "wiki.json", self.scope_id)
            self.available = False
        else:
            raise WikiUnavailable(f"unsupported local Wiki backend: {backend}")

    def _require_available(self) -> None:
        if not self.available:
            raise WikiUnavailable("project Wiki is unavailable")

    def index_digest(self) -> str | None:
        """What a projection can name as its input: the bytes this scope last committed.

        A page tree that does not record this cannot be told apart from one projected out of a
        different store or an older generation of this one, so the digest travels with the
        manifest and with every PageSet.
        """
        self._require_available()
        return self._store.index_digest()

    def semantic_state(self) -> dict[str, Any]:
        """Return the optional Enterprise Ontology ledger without exposing mutable store state."""
        self._require_available()
        document = self._store.load()
        state = document.get("semantic", _empty_semantic_state())
        if not _valid_semantic_state(state, scope_id=self.scope_id):
            raise WikiUnavailable("the local Wiki semantic state is unreadable")
        return json.loads(_canonical_json(state))

    def update_semantic_state(self, update: Callable[[dict[str, Any]], Any]) -> Any:
        """Mutate only the additive semantic ledger inside the existing scoped Wiki document."""
        self._require_available()

        def apply(document: dict[str, Any]) -> Any:
            state = document.get("semantic", _empty_semantic_state())
            if not _valid_semantic_state(state, scope_id=self.scope_id):
                raise WikiUnavailable("the local Wiki semantic state is unreadable")
            state = json.loads(_canonical_json(state))
            result = update(state)
            if not _valid_semantic_state(state, scope_id=self.scope_id):
                raise WikiUnavailable("the local Wiki semantic state update is invalid")
            document["semantic"] = state
            return result

        return self._store.update(apply)

    def verify(self) -> dict[str, Any]:
        """Check the store against its own index without reading a source or writing anything."""
        self._require_available()
        report = self._store.verify()
        report["wiki_action"] = "verify"
        return report

    def concept_state(self) -> dict[str, Any]:
        """Return the scope's own concept ledger without exposing mutable store state."""
        self._require_available()
        document = self._store.load()
        state = document.get("concepts", empty_concept_state())
        if not concept_state_is_valid(state):
            raise WikiUnavailable("the local Wiki concept state is unreadable")
        return json.loads(_canonical_json(state))

    def update_concept_state(self, update: Callable[[dict[str, Any]], Any]) -> Any:
        """Mutate only the additive concept ledger inside the existing scoped Wiki document.

        A concept is the scope's own type, so it lives beside the scope's claims and needs no
        second store, no second scope id and no release; the version it publishes is what makes
        the change reviewable later.
        """
        self._require_available()

        def apply(document: dict[str, Any]) -> Any:
            state = document.get("concepts", empty_concept_state())
            if not concept_state_is_valid(state):
                raise WikiUnavailable("the local Wiki concept state is unreadable")
            state = json.loads(_canonical_json(state))
            result = update(state)
            if not concept_state_is_valid(state):
                raise WikiUnavailable("the local Wiki concept state update is invalid")
            document["concepts"] = state
            return result

        return self._store.update(apply)

    def concept_set(self) -> ConceptSet:
        """The types this scope extracts with: its own declared set, or the starter pack."""
        return concept_set_of(self.concept_state())

    def source_record(self, source_id: str) -> dict[str, Any]:
        """Return one stored source record without reading or decoding its file."""
        self._require_available()
        source = self._store.load()["sources"].get(source_id)
        if not isinstance(source, dict) or source.get("scope_id") != self.scope_id:
            raise WikiScopeError("the requested staged Wiki source is unavailable")
        return dict(source)

    def source_snapshot(self, source_id: str) -> dict[str, Any]:
        """Resolve a previously staged source and report current bytes against its saved revision."""
        self._require_available()
        document = self._store.load()
        source = document["sources"].get(source_id)
        if not isinstance(source, dict) or source.get("scope_id") != self.scope_id:
            raise WikiScopeError("the requested staged Wiki source is unavailable")
        relative_path = source.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path:
            raise WikiUnavailable("the staged Wiki source has no valid relative identity")
        relative = Path(*relative_path.split("/"))
        matches = []
        for root in set(self.roots):
            candidate = root / relative
            try:
                resolved, candidate_relative = self._source_identity(candidate)
            except (WikiScopeError, OSError):
                continue
            if candidate_relative == relative_path and resolved.is_file():
                matches.append(resolved)
        if len(matches) != 1:
            raise WikiScopeError("the staged Wiki source is missing or has an ambiguous identity")
        try:
            raw = matches[0].read_bytes()
            content = raw.decode("utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise WikiScopeError("the staged Wiki source is not readable UTF-8 Markdown") from exc
        return {
            "source": dict(source),
            "content": content,
            "current_revision": hashlib.sha256(raw).hexdigest(),
        }

    def _source_identity(self, path: Path) -> tuple[Path, str]:
        try:
            resolved = path.expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise WikiScopeError("the selected Wiki source does not exist or cannot be resolved") from exc
        if not resolved.is_file() or resolved.suffix.casefold() != ".md":
            raise WikiScopeError("only Markdown files beneath configured Wiki roots can be staged")
        matching_roots = {
            root for root in self.roots if resolved == root or resolved.is_relative_to(root)
        }
        if not matching_roots:
            raise WikiScopeError("only Markdown files beneath configured Wiki roots can be staged")
        if len(matching_roots) != 1:
            raise WikiSourceIdentityAmbiguous(
                "the selected source is beneath multiple configured Wiki roots"
            )
        root = next(iter(matching_roots))
        relative_path = resolved.relative_to(root).as_posix()
        if self._has_duplicate_relative_source(root, relative_path, resolved):
            raise WikiSourceIdentityAmbiguous(
                "multiple configured Wiki roots contain different Markdown sources at the same relative path"
            )
        return resolved, relative_path

    def _has_duplicate_relative_source(self, selected_root: Path, relative_path: str, resolved: Path) -> bool:
        """Reject ambiguous legacy source identities without changing stored IDs or records."""
        relative_parts = relative_path.split("/")
        for root in set(self.roots):
            if root == selected_root:
                continue
            candidate = root.joinpath(*relative_parts)
            try:
                candidate_resolved = candidate.resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if candidate_resolved == resolved:
                continue
            if (
                candidate_resolved.is_file()
                and candidate_resolved.suffix.casefold() == ".md"
                and (candidate_resolved == root or candidate_resolved.is_relative_to(root))
            ):
                return True
        return False

    def validate_selected_file(self, path: Path | str) -> Path:
        """Keep task evidence inside the same explicitly configured project roots."""
        self._require_available()
        try:
            resolved = Path(path).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise WikiScopeError("the selected task file does not exist or cannot be resolved") from exc
        if not resolved.is_file() or not any(
            resolved == root or resolved.is_relative_to(root)
            for root in self.roots
        ):
            raise WikiScopeError("the selected task file is outside the configured project Wiki roots")
        return resolved

    @staticmethod
    def _candidate_claims(scope_id: str, source_id: str, revision: str, text: str) -> list[dict[str, Any]]:
        claims: list[dict[str, Any]] = []
        heading = None
        fence_character: str | None = None
        fence_length = 0
        for line_number, line in enumerate(text.splitlines(), start=1):
            if fence_character is not None:
                closing = _FENCE_CLOSE.match(line)
                if (
                    closing is not None
                    and closing.group(1)[0] == fence_character
                    and len(closing.group(1)) >= fence_length
                ):
                    fence_character = None
                    fence_length = 0
                continue

            opening = _FENCE_OPEN.match(line)
            if opening is not None:
                marker, info = opening.groups()
                if marker[0] != "`" or "`" not in info:
                    fence_character = marker[0]
                    fence_length = len(marker)
                    continue

            heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
            if heading_match:
                heading = heading_match.group(1).strip()
            match = _RULE.match(line)
            if not match or not match.group(2):
                continue
            kind = match.group(1).casefold()
            claim_id = "claim_" + _digest(
                f"{scope_id}\0{source_id}\0{revision}\0{line_number}\0{kind}".encode("utf-8")
            )[:24]
            claims.append(
                {
                    "claim_id": claim_id,
                    "scope_id": scope_id,
                    "source_id": source_id,
                    "revision": revision,
                    "kind": kind,
                    "meaning": match.group(2).strip(),
                    "heading": heading,
                    "line_start": line_number,
                    "line_end": line_number,
                    "status": "UNKNOWN" if kind == "unknown" else "CANDIDATE_ONLY",
                    "authority": "PROJECT_CANDIDATE",
                }
            )
        return claims

    def stage_markdown(self, path: Path | str) -> dict[str, Any]:
        self._require_available()
        resolved, relative_path = self._source_identity(Path(path))
        try:
            raw = resolved.read_bytes()
        except OSError as exc:
            raise WikiScopeError("the selected Wiki source could not be read") from exc
        if len(raw) > _MAX_SOURCE_BYTES:
            raise WikiScopeError(
                "the selected Wiki source exceeds the "
                f"{_MAX_SOURCE_BYTES // (1024 * 1024)} MiB Markdown limit"
            )
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise WikiScopeError("the selected Wiki source must be valid UTF-8 Markdown") from exc
        revision = _digest(raw)
        source_id = "source_" + _digest(f"{self.scope_id}\0{relative_path}".encode("utf-8"))[:24]
        claims = self._candidate_claims(self.scope_id, source_id, revision, content)

        def apply(document: dict[str, Any]) -> dict[str, Any]:
            previous = document["sources"].get(source_id)
            if isinstance(previous, dict) and previous.get("revision") == revision:
                return {
                    "status": "no_op",
                    "scope_id": self.scope_id,
                    "source_id": source_id,
                    "revision": revision,
                    "claim_ids": list(previous.get("claim_ids", [])),
                    "claim_count": len(previous.get("claim_ids", [])),
                }
            if isinstance(previous, dict):
                for claim_id in previous.get("claim_ids", []):
                    old = document["claims"].get(claim_id)
                    if isinstance(old, dict):
                        old["status"] = "STALE"
                        old["superseded_by_revision"] = revision
            document["claims"].update({claim["claim_id"]: claim for claim in claims})
            document["sources"][source_id] = {
                "source_id": source_id,
                "scope_id": self.scope_id,
                "relative_path": relative_path,
                "revision": revision,
                "byte_length": len(raw),
                "line_count": len(content.splitlines()),
                "claim_ids": [claim["claim_id"] for claim in claims],
            }
            return {
                "status": "staged" if previous is None else "updated",
                "scope_id": self.scope_id,
                "source_id": source_id,
                "revision": revision,
                "claim_ids": [claim["claim_id"] for claim in claims],
                "claim_count": len(claims),
            }

        return self._store.update(apply)

    def _native_source_identity(self, path: Path) -> tuple[Path, str]:
        """Resolve supported native files without changing Markdown staging rules."""
        try:
            if path.is_symlink():
                raise WikiScopeError("native source symlinks are not supported")
            resolved = path.expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise WikiScopeError("native source cannot be resolved") from exc
        roots = {root for root in self.roots if resolved.is_relative_to(root)}
        if (
            not resolved.is_file()
            or resolved.suffix.casefold() not in {".docx", ".pptx", ".pdf", ".xlsx"}
            or len(roots) != 1
        ):
            raise WikiScopeError("native source must be an allowed document under one Wiki root")
        root = next(iter(roots))
        relative = resolved.relative_to(root).as_posix()
        for other in set(self.roots) - {root}:
            candidate = other.joinpath(*relative.split("/"))
            if candidate.is_file() and candidate.resolve() != resolved:
                raise WikiSourceIdentityAmbiguous("native source path is ambiguous across Wiki roots")
        return resolved, relative

    def stage_native_source(self, path: Path | str) -> dict[str, Any]:
        """Record native bytes identity as a candidate source; no text or claims are generated."""
        self._require_available()
        resolved, relative = self._native_source_identity(Path(path))
        try:
            raw = resolved.read_bytes()
        except OSError as exc:
            raise WikiScopeError("native source cannot be read") from exc
        if len(raw) > _MAX_NATIVE_BYTES:
            raise WikiScopeError("native source exceeds the bounded size")
        revision = _digest(raw)
        source_id = "source_" + _digest(f"{self.scope_id}\0{relative}".encode("utf-8"))[:24]
        def apply(document: dict[str, Any]) -> dict[str, Any]:
            previous = document["sources"].get(source_id)
            if isinstance(previous, dict) and previous.get("revision") == revision:
                return {
                    "status": "no_op",
                    "scope_id": self.scope_id,
                    "source_id": source_id,
                    "revision": revision,
                    "claim_ids": list(previous.get("claim_ids", [])),
                    "claim_count": len(previous.get("claim_ids", [])),
                }
            if isinstance(previous, dict):
                for claim_id in previous.get("claim_ids", []):
                    old = document["claims"].get(claim_id)
                    if isinstance(old, dict):
                        old["status"] = "STALE"
                        old["superseded_by_revision"] = revision
            document["sources"][source_id] = {
                "source_id": source_id,
                "scope_id": self.scope_id,
                "relative_path": relative,
                "revision": revision,
                "byte_length": len(raw),
                "line_count": 0,
                "claim_ids": [],
                "source_format": resolved.suffix.casefold()[1:],
                "content_status": "NOT_PARSED",
            }
            return {
                "status": "staged" if previous is None else "updated",
                "scope_id": self.scope_id,
                "source_id": source_id,
                "revision": revision,
                "claim_ids": [],
                "claim_count": 0,
            }

        return self._store.update(apply)

    def record_extraction(self, source_id: str, report: Mapping[str, Any]) -> dict[str, Any]:
        """Record what extraction read for one staged source; the bytes stay the only content."""
        self._require_available()
        if not isinstance(source_id, str) or not source_id:
            raise WikiScopeError("a staged source identity is required")
        status = report.get("status")
        content_status = {
            "complete": "PARSED",
            "partial": "PARSED_PARTIAL",
            "truncated": "PARSED_TRUNCATED",
            "no_text": "NOT_PARSED",
        }
        if status not in content_status:
            raise WikiScopeError("extraction status is not a bounded completeness state")
        for field in ("unit_count", "locator_count"):
            if type(report.get(field)) is not int or report[field] < 0:
                raise WikiScopeError("extraction counts must be non-negative integers")
        for field in ("part_errors", "vision_missing", "warnings"):
            value = report.get(field, ())
            if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
                raise WikiScopeError(f"extraction {field} must be a list of strings")
        frozen = {
            "status": status,
            "unit_count": report["unit_count"],
            "locator_count": report["locator_count"],
            "truncated": bool(report.get("truncated", False)),
            "part_errors": list(report.get("part_errors", ()))[:64],
            "vision_missing": list(report.get("vision_missing", ()))[:512],
            "warnings": list(report.get("warnings", ()))[:256],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

        def apply(document: dict[str, Any]) -> dict[str, Any]:
            source = document["sources"].get(source_id)
            if not isinstance(source, dict) or source.get("scope_id") != self.scope_id:
                raise WikiScopeError("only a staged source can record extraction")
            revision = source.get("revision")
            frozen["revision"] = revision
            previous = source.get("extraction")
            frozen["shrink_suspect"] = None
            if isinstance(previous, dict) and previous.get("revision") == revision:
                before = previous.get("unit_count")
                after = frozen["unit_count"]
                if type(before) is int and before > 0 and after < before * _SHRINK_RATIO:
                    # The bytes are the same, so the shortfall is the reader's, and it
                    # is reported instead of being written over the earlier reading.
                    frozen["shrink_suspect"] = {
                        "previous_unit_count": before,
                        "unit_count": after,
                        "ratio": round(after / before, 4),
                    }
                    frozen["warnings"] = (
                        frozen["warnings"]
                        + [f"EXTRACTION_SHRINK_SUSPECT:{before}->{after}"]
                    )[:256]
            source["extraction"] = frozen
            source["content_status"] = content_status[status]
            return {"status": "recorded", "source_id": source_id, "extraction": dict(frozen)}

        return self._store.update(apply)

    def native_source_snapshot(self, source_id: str) -> dict[str, Any]:
        """Read identity/freshness only; never return or interpret document bytes."""
        self._require_available()
        source = self._store.load()["sources"].get(source_id)
        if (
            not isinstance(source, dict)
            or source.get("scope_id") != self.scope_id
            or source.get("source_format") not in {"docx", "pptx", "pdf", "xlsx"}
        ):
            raise WikiScopeError("native source identity is unavailable")
        relative = source.get("relative_path")
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise WikiScopeError("invalid native source identity")
        matches = []
        for root in set(self.roots):
            try:
                resolved, resolved_relative = self._native_source_identity(root / relative)
            except (WikiScopeError, OSError):
                continue
            if resolved_relative == relative:
                matches.append(resolved)
        if len(matches) != 1:
            raise WikiScopeError("native source is missing or ambiguous")
        raw = matches[0].read_bytes()
        if len(raw) > _MAX_NATIVE_BYTES:
            raise WikiScopeError("native source exceeds the bounded size")
        return {"source": dict(source), "current_revision": _digest(raw)}

    def withdraw_source(self, source_id: str) -> dict[str, Any]:
        """Stop a staged source from being read or searched; keep its history readable."""
        self._require_available()
        if not isinstance(source_id, str) or not source_id:
            raise WikiScopeError("a staged Wiki source identity is required")

        def apply(document: dict[str, Any]) -> dict[str, Any]:
            source = document["sources"].get(source_id)
            if not isinstance(source, dict) or source.get("scope_id") != self.scope_id:
                raise WikiScopeError("the requested staged Wiki source is unavailable")
            claim_ids = [claim_id for claim_id in source.get("claim_ids", []) if isinstance(claim_id, str)]
            if source.get("status") == "WITHDRAWN":
                return {
                    "status": "no_op",
                    "scope_id": self.scope_id,
                    "source_id": source_id,
                    "revision": source.get("revision"),
                    "withdrawn_claim_count": sum(
                        1
                        for claim_id in claim_ids
                        if document["claims"].get(claim_id, {}).get("status") == "WITHDRAWN"
                    ),
                }
            source["status"] = "WITHDRAWN"
            source["withdrawn_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            for claim_id in claim_ids:
                claim = document["claims"].get(claim_id)
                if isinstance(claim, dict):
                    claim["status"] = "WITHDRAWN"
            return {
                "status": "withdrawn",
                "scope_id": self.scope_id,
                "source_id": source_id,
                "revision": source.get("revision"),
                "withdrawn_claim_count": len(claim_ids),
            }

        return self._store.update(apply)

    def restore_source(self, source_id: str) -> dict[str, Any]:
        """Return a withdrawn source to the readable set without touching its bytes."""
        self._require_available()

        def apply(document: dict[str, Any]) -> dict[str, Any]:
            source = document["sources"].get(source_id)
            if not isinstance(source, dict) or source.get("scope_id") != self.scope_id:
                raise WikiScopeError("the requested staged Wiki source is unavailable")
            claim_ids = [claim_id for claim_id in source.get("claim_ids", []) if isinstance(claim_id, str)]
            if source.get("status") != "WITHDRAWN":
                return {
                    "status": "no_op",
                    "scope_id": self.scope_id,
                    "source_id": source_id,
                    "revision": source.get("revision"),
                    "restored_claim_count": 0,
                }
            source.pop("status", None)
            source.pop("withdrawn_at", None)
            restored = 0
            for claim_id in claim_ids:
                claim = document["claims"].get(claim_id)
                if isinstance(claim, dict) and claim.get("status") == "WITHDRAWN":
                    claim["status"] = "UNKNOWN" if claim.get("kind") == "unknown" else "CANDIDATE_ONLY"
                    restored += 1
            return {
                "status": "restored",
                "scope_id": self.scope_id,
                "source_id": source_id,
                "revision": source.get("revision"),
                "restored_claim_count": restored,
            }

        return self._store.update(apply)

    def claim_history(self, source_id: str) -> list[dict[str, Any]]:
        self._require_available()
        document = self._store.load()
        return sorted(
            (dict(claim) for claim in document["claims"].values() if claim.get("source_id") == source_id),
            key=lambda claim: (claim.get("line_start", 0), claim.get("revision", "")),
        )

    def search(
        self,
        query: str,
        *,
        capabilities: Sequence[Mapping[str, Any]] = (),
        limit: int = 8,
    ) -> dict[str, Any]:
        self._require_available()
        if not isinstance(query, str) or not query.strip():
            raise WikiScopeError("Wiki query must be a non-empty string")
        query_terms = _tokens(query)
        document = self._store.load()
        claims = []
        for claim in document["claims"].values():
            if claim.get("scope_id") != self.scope_id or claim.get("status") in {"STALE", "WITHDRAWN"}:
                continue
            score = _score(query_terms, f"{claim.get('meaning', '')} {claim.get('heading', '')}")
            if score:
                row = dict(claim)
                row["_score"] = score
                claims.append(row)
        claims.sort(key=lambda row: (-row["_score"], row["source_id"], row["line_start"], row["claim_id"]))
        matched_source_ids = {claim["source_id"] for claim in claims}
        if matched_source_ids:
            # Once a source contributes a matching section, bring its exception
            # and condition rows into the same context pack. This prevents a
            # positive rule from hiding a limiting sentence in the same file.
            present_ids = {claim["claim_id"] for claim in claims}
            for claim in document["claims"].values():
                if (
                    claim.get("scope_id") == self.scope_id
                    and claim.get("source_id") in matched_source_ids
                    and claim.get("status") not in {"STALE", "WITHDRAWN"}
                    and claim.get("claim_id") not in present_ids
                ):
                    row = dict(claim)
                    row["_score"] = 0
                    claims.append(row)
        claims.sort(key=lambda row: (-row["_score"], row["source_id"], row["line_start"], row["claim_id"]))

        projected: list[dict[str, Any]] = []
        for capability in capabilities:
            capability_id = capability.get("capability_id")
            version = capability.get("capability_version")
            name = capability.get("name")
            description = capability.get("description")
            descriptor_sha256 = capability.get("descriptor_sha256")
            if not all(isinstance(value, str) and value for value in (capability_id, version, name, description, descriptor_sha256)):
                continue
            score = _score(query_terms, f"{name} {description}")
            if not score:
                continue
            source_id = "catalog_" + _digest(f"{self.scope_id}\0{capability_id}@{version}".encode("utf-8"))[:24]
            claim_id = "capclaim_" + _digest(
                f"{self.scope_id}\0{capability_id}@{version}\0{descriptor_sha256}".encode("utf-8")
            )[:24]
            projected.append(
                {
                    "claim_id": claim_id,
                    "scope_id": self.scope_id,
                    "source_id": source_id,
                    "revision": descriptor_sha256,
                    "kind": "capability_projection",
                    "meaning": description,
                    "status": "ACTIVE_CATALOG_PROJECTION",
                    "authority": "DERIVED_NON_AUTHORITY",
                    "capability_id": capability_id,
                    "capability_version": version,
                    "name": name,
                    "side_effect": capability.get("side_effect"),
                    "binding_digest": capability.get("binding_digest"),
                    "_score": score,
                }
            )
        projected.sort(key=lambda row: (-row["_score"], row["capability_id"], row["capability_version"]))

        # Connect a staged source claim to a live Catalog projection only when
        # their source-backed wording overlaps; the live Catalog remains the
        # execution authority and this link never grants permission.
        for claim in claims[:limit]:
            linked = max(
                projected,
                key=lambda row: _score(_tokens(claim["meaning"]), row["meaning"]),
                default=None,
            )
            if linked is not None and _score(_tokens(claim["meaning"]), linked["meaning"]):
                claim["capability_ref"] = {
                    "capability_id": linked["capability_id"],
                    "capability_version": linked["capability_version"],
                    "claim_id": linked["claim_id"],
                }

        combined = sorted(
            [*claims[:limit], *projected[:limit]],
            key=lambda row: (-row["_score"], row["kind"], row["source_id"], row["claim_id"]),
        )[:limit]
        for row in combined:
            row.pop("_score", None)
        unresolved = [
            claim
            for claim in claims
            if claim.get("kind") in {"condition", "exception", "unknown"}
            and _UNRESOLVED_APPLICABILITY.search(str(claim.get("meaning", "")))
        ]
        best = combined[0] if combined else None
        return {
            "status": "FOUND" if combined else "UNKNOWN",
            "applicability_status": "UNKNOWN" if unresolved else "CANDIDATE_ONLY",
            "applicability_unknown_claim_ids": [claim["claim_id"] for claim in unresolved],
            "scope_id": self.scope_id,
            "source_id": best.get("source_id") if best else None,
            "source_revision": best.get("revision") if best else None,
            "claims": [row for row in combined if row["kind"] != "capability_projection"],
            "capabilities": [row for row in combined if row["kind"] == "capability_projection"],
        }

    def sources(self) -> list[dict[str, Any]]:
        """Every source record in this scope, withdrawn ones included.

        A projection needs the whole shelf, not one search result: this is the read
        side of :meth:`stage_markdown` and :meth:`stage_native_source`.
        """
        return [
            dict(row)
            for row in self._store.load()["sources"].values()
            if isinstance(row, dict) and row.get("scope_id") == self.scope_id
        ]

    def _current_source_revision(self, source_id: str) -> str | None:
        """The revision this source has on disk right now, or None when it is gone."""
        source = self._store.load()["sources"].get(source_id)
        if not isinstance(source, dict) or source.get("scope_id") != self.scope_id:
            return None
        try:
            if source.get("source_format") in {"docx", "pptx", "pdf", "xlsx"}:
                return self.native_source_snapshot(source_id)["current_revision"]
            return self.source_snapshot(source_id)["current_revision"]
        except (WikiUnavailable, WikiScopeError):
            return None

    def accepted_meanings(self) -> dict[str, Any]:
        """Every meaning of the active accepted version, with per-evidence freshness.

        A page projection renders exactly this set, so it may not be bounded by a query
        budget: truncating here would silently drop pages instead of shortening an answer.
        """
        self._require_available()
        state = self.semantic_state()
        active = state.get("active_version_id")
        version = state["accepted_versions"].get(active) if isinstance(active, str) else None
        meanings: list[dict[str, Any]] = []
        if isinstance(version, dict):
            revisions: dict[str, str | None] = {}
            for row in version.get("meanings", {}).values():
                evidence_rows = row.get("evidence") if isinstance(row.get("evidence"), list) else [row]
                evidence_out = []
                for evidence in evidence_rows:
                    source_id = str(evidence.get("source_id") or "")
                    if source_id not in revisions:
                        revisions[source_id] = self._current_source_revision(source_id)
                    current = revisions[source_id]
                    if current is None:
                        freshness = "unknown"
                    else:
                        freshness = "fresh" if evidence.get("source_revision") == current else "stale"
                    evidence_out.append({**dict(evidence), "freshness_status": freshness})
                entry = dict(row)
                entry["evidence"] = evidence_out
                entry["freshness_status"] = self._aggregate_freshness(
                    [item["freshness_status"] for item in evidence_out]
                )
                meanings.append(entry)
        return {
            "scope_id": self.scope_id,
            "active_version_id": active if isinstance(active, str) else None,
            "meanings": meanings,
        }

    def read_knowledge(
        self,
        query: str,
        *,
        mode: str,
        capabilities: Sequence[Mapping[str, Any]] = (),
        limit: int = 8,
        version_id: str | None = None,
        expand_relations_for: str | None = None,
        include_all_active: bool = False,
        about: str | None = None,
    ) -> dict[str, Any]:
        """Read one explicit knowledge tier from the existing ProjectWiki authority.

        Source, document, R6 claim, and accepted semantic identities remain distinct.
        Freshness is calculated from the exact source revision referenced by each row;
        this method never rewrites accepted history.
        """
        self._require_available()
        if mode not in _KNOWLEDGE_READ_MODES:
            raise WikiScopeError("unsupported ProjectWiki knowledge read mode")
        if not isinstance(query, str) or not query.strip():
            raise WikiScopeError("Wiki query must be a non-empty string")
        if type(limit) is not int or limit < 1 or limit > 100:
            raise WikiScopeError("Wiki read limit must be between 1 and 100")
        if version_id is not None and mode != "accepted_enterprise_semantics":
            raise WikiScopeError("a semantic version can only be selected for accepted semantic reads")
        if expand_relations_for is not None and mode != "accepted_enterprise_semantics":
            raise WikiScopeError("relation expansion is only available for accepted semantic reads")
        if type(include_all_active) is not bool:
            raise WikiScopeError("include_all_active must be a boolean")
        if include_all_active and mode != "accepted_enterprise_semantics":
            raise WikiScopeError("complete semantic projection is only available for accepted semantic reads")
        if about is not None and (not isinstance(about, str) or not about.strip()):
            raise WikiScopeError("a read by object must name the entity it asks about")
        if about is not None and mode != "accepted_enterprise_semantics":
            raise WikiScopeError("reading by the object a row addresses is only available for accepted semantic meanings")

        query_terms = _tokens(query)
        stored = self._store.load()
        semantic_state = self.semantic_state()
        active_version_id = semantic_state.get("active_version_id")
        selected_version_id = version_id or active_version_id
        if version_id is not None and version_id not in semantic_state["accepted_versions"]:
            raise WikiScopeError("the requested accepted semantic version is unavailable in this Wiki scope")
        if expand_relations_for is not None:
            selected_version = semantic_state["accepted_versions"].get(selected_version_id, {}) if selected_version_id else {}
            entity_ids = {
                row.get("canonical_id")
                for row in selected_version.get("meanings", {}).values()
                if row.get("kind") in {"entity", "alias"} and isinstance(row.get("canonical_id"), str)
            }
            if expand_relations_for not in entity_ids:
                raise WikiScopeError("the requested relation subject is not an entity identity in this Wiki version")
        source_views: dict[str, dict[str, Any]] = {}
        documents: list[dict[str, Any]] = []
        for source_id, source in sorted(stored["sources"].items()):
            if not isinstance(source, dict) or source.get("scope_id") != self.scope_id:
                continue
            if source.get("status") == "WITHDRAWN":
                continue
            relative_path = str(source.get("relative_path", ""))
            source_format = source.get("source_format")
            native = source_format in {"docx", "pptx", "pdf"}
            try:
                if native:
                    # A native document has no rendered text; only its byte identity
                    # and freshness can be read. This is not a missing source.
                    native_snapshot = self.native_source_snapshot(source_id)
                    current_revision = native_snapshot["current_revision"]
                    current_content = ""
                    current = current_revision == source.get("revision")
                    revision_status = "native_not_parsed" if current else "changed_unstaged"
                    freshness = "fresh" if current else "stale"
                else:
                    snapshot = self.source_snapshot(source_id)
                    current_revision = snapshot["current_revision"]
                    current_content = snapshot["content"]
                    revision_status = "current" if current_revision == source.get("revision") else "changed_unstaged"
                    freshness = "fresh" if revision_status == "current" else "stale"
            except WikiUnavailable:
                current_revision = None
                current_content = ""
                revision_status = "unavailable"
                freshness = "unknown"
            except WikiScopeError:
                current_revision = None
                current_content = ""
                revision_status = "missing_or_unresolvable"
                freshness = "unknown"

            headings = [
                match.group(1).strip()
                for line in current_content.splitlines()
                if (match := re.match(r"^ {0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", line))
            ]
            title = headings[0] if headings else Path(relative_path).stem
            document_id = "document_" + _digest(f"{self.scope_id}\0{source_id}".encode("utf-8"))[:24]
            document_row = {
                "document_id": document_id,
                "source_id": source_id,
                "source_revision": source.get("revision"),
                "current_revision": current_revision,
                "document_revision": current_revision or source.get("revision"),
                "title": title,
                "headings": headings,
                "relative_path": relative_path,
                "revision_status": revision_status,
                "freshness_status": revision_status if revision_status != "current" else "fresh",
                "knowledge_status": (
                    "current" if revision_status in {"current", "native_not_parsed"} else "needs_reconciliation"
                ),
                "authority": "SOURCE_DERIVED_DOCUMENT_METADATA",
            }
            if native:
                document_row["source_format"] = source_format
                document_row["content_status"] = source.get("content_status") or "NOT_PARSED"
                # Freshness of a native document is about its bytes, not about
                # whether a text revision matches.
                document_row["freshness_status"] = freshness

            source_views[source_id] = {
                "source": source,
                "current_revision": current_revision,
                "revision_status": revision_status,
                "freshness_status": freshness,
                "content": current_content,
                "document_id": document_id,
                "document": document_row,
            }
            if not query_terms or _score(query_terms, f"{title} {' '.join(headings)} {relative_path}"):
                documents.append(document_row)

        meanings: list[dict[str, Any]] = []
        restricted_meaning_count = 0
        meaning_ids: list[str] = []
        pending_conflicts: list[dict[str, Any]] = []
        claims: list[dict[str, Any]] = []
        stale_claims: list[dict[str, Any]] = []
        capability_rows: list[dict[str, Any]] = []
        applicability_status = "CANDIDATE_ONLY"
        applicability_unknown_claim_ids: list[str] = []
        knowledge_status = "unknown"
        freshness_status = "unknown"
        truncated = False
        authority = {
            "source_discovery": "SOURCE_REFERENCE",
            "grounded_claims": "CANDIDATE_ONLY",
            "accepted_enterprise_semantics": "MANAGER_ACCEPTED_SCOPED_SEMANTICS",
        }[mode]

        if mode == "source_discovery":
            freshness_values = [row["freshness_status"] for row in documents]
            if documents:
                freshness_status = self._aggregate_freshness(freshness_values)
                knowledge_status = "needs_reconciliation" if any(value != "fresh" for value in freshness_values) else "current"
        elif mode == "grounded_claims":
            search_result = self.search(query, capabilities=capabilities, limit=limit)
            applicability_status = search_result["applicability_status"]
            applicability_unknown_claim_ids = list(search_result["applicability_unknown_claim_ids"])
            for original in search_result["claims"]:
                row = dict(original)
                source_view = source_views.get(str(row.get("source_id")))
                if source_view is None:
                    row["freshness_status"] = "unknown"
                    row["document_id"] = None
                else:
                    row["document_id"] = source_view["document_id"]
                    row["freshness_status"] = (
                        "fresh"
                        if source_view["revision_status"] == "current"
                        and row.get("revision") == source_view["current_revision"]
                        and row.get("status") != "STALE"
                        else "stale"
                        if source_view["revision_status"] in {"current", "changed_unstaged"}
                        else "unknown"
                    )
                row["authority"] = "SOURCE_GROUNDED_CANDIDATE"
                span_sha256 = None
                if row["freshness_status"] == "fresh" and source_view is not None:
                    source_lines = source_view["content"].splitlines()
                    start = row.get("line_start")
                    end = row.get("line_end", start)
                    if type(start) is int and type(end) is int and 1 <= start <= end <= len(source_lines):
                        span_sha256 = _digest("\n".join(source_lines[start - 1:end]).encode("utf-8"))
                row["span_sha256"] = span_sha256
                row["evidence_refs"] = [{
                    "source_id": row.get("source_id"),
                    "source_revision": row.get("revision"),
                    "claim_id": row.get("claim_id"),
                    "line_start": row.get("line_start"),
                    "line_end": row.get("line_end"),
                    "span_sha256": span_sha256,
                    "evidence_class": "observed_from_source",
                }]
                (claims if row["freshness_status"] == "fresh" else stale_claims).append(row)
            capability_rows = [dict(row) for row in search_result["capabilities"]]
            for row in capability_rows:
                row["authority"] = "DERIVED_NON_AUTHORITY"
                row["freshness_status"] = "current_catalog_projection"
            applicability_status = search_result["applicability_status"]
            freshness_status = self._aggregate_freshness(
                [row["freshness_status"] for row in [*claims, *stale_claims]]
            )
            if claims or capability_rows:
                knowledge_status = "current" if not stale_claims else "needs_reconciliation"
            elif stale_claims:
                knowledge_status = "needs_reconciliation"
            used_source_ids = {row["source_id"] for row in [*claims, *stale_claims]}
            documents = [
                source_views[source_id]["document"]
                for source_id in sorted(used_source_ids)
                if source_id in source_views
            ]
        else:
            version = semantic_state["accepted_versions"].get(selected_version_id, {}) if selected_version_id else {}
            # What the rows call the entities they address. A duty is found by the object
            # that holds it and an event by the units on either side, so the name has to be
            # in the text a query is matched against, not only the key the row stores.
            entity_names = {str(row.get("key")): str(row.get("meaning") or "")
                            for row in version.get("meanings", {}).values()
                            if row.get("kind") == "entity"}
            # Asking by the object a row addresses is an index lookup, not a search: the
            # caller names one unit, and the answer is what that unit holds and what it is
            # a side of. The text query is not used as well, because token overlap on the
            # words of a name is what an index exists to replace.
            about_keys: set[str] | None = None
            if about is not None:
                target = about.strip().lstrip("@")
                about_keys = {target}
                spelled = {str(row.get("key")): str(row.get("meaning") or "")
                           for row in version.get("meanings", {}).values()
                           if row.get("kind") in {"entity", "alias"}}
                about_keys.update(key for key, name in spelled.items() if name == target)
                about_keys.update(key for key, name in spelled.items() if name and target in name)
            for row in version.get("meanings", {}).values():
                searchable = f"{row.get('kind', '')} {row.get('key', '')} {row.get('meaning', '')} {row.get('heading') or ''}"
                if row.get("kind") == "duty":
                    searchable += " " + entity_names.get(str(row.get("holder") or ""), "")
                elif row.get("kind") == "event":
                    searchable += " " + " ".join(
                        entity_names.get(str(key), "")
                        for side in ("from", "to") for key in (row.get(side) or ()))
                    searchable += " " + str(row.get("predicate") or "")
                relation_match = (
                    expand_relations_for is not None
                    and row.get("kind") == "relation"
                    and row.get("canonical_subject_id") == expand_relations_for
                )
                if about_keys is not None:
                    addressed: set[str] = set()
                    if row.get("kind") == "duty":
                        addressed = {str(row.get("holder") or "")}
                    elif row.get("kind") == "event":
                        addressed = {str(key) for side in ("from", "to")
                                     for key in (row.get(side) or ())}
                    elif row.get("kind") in {"entity", "alias"}:
                        addressed = {str(row.get("key") or "")}
                    if not addressed & about_keys:
                        continue
                elif not include_all_active and not relation_match and query_terms and not _score(query_terms, searchable):
                    continue
                meaning = dict(row)
                # Who wrote this row, as it was saved. A row that cannot show a step
                # this layer ran is not a statement of the material: a store written
                # before this contract carries no tag at all, and it reads as
                # unverified rather than as a fact - nothing on disk is rewritten.
                origin = meaning.get("source_origin")
                if not isinstance(origin, Mapping) or origin.get("category") not in SOURCE_CATEGORIES:
                    meaning["source_origin"] = {"category": "unverifiable", "step": None,
                                                 "call": None, "item_id": None}
                evidence_rows = row.get("evidence") if isinstance(row.get("evidence"), list) else [row]
                evidence_out = []
                for evidence in evidence_rows:
                    source_view = source_views.get(str(evidence.get("source_id")))
                    if source_view is None:
                        evidence_freshness = "unknown"
                    elif source_view["revision_status"] not in {"current", "changed_unstaged"}:
                        evidence_freshness = "unknown"
                    else:
                        evidence_freshness = (
                            "fresh"
                            if evidence.get("source_revision") == source_view["current_revision"]
                            else "stale"
                        )
                    evidence_out.append({
                        **dict(evidence),
                        "document_id": source_view["document_id"] if source_view else None,
                        "freshness_status": evidence_freshness,
                    })
                meaning["evidence"] = evidence_out
                meaning["canonical_identity_basis"] = meaning.get("identity_basis") or (
                    "legacy_unverified_identity"
                    if meaning.get("canonical_id")
                    else "legacy_scoped_proposition_key"
                )
                meaning["canonical_identity_status"] = meaning.get("canonical_identity_status") or (
                    "proposed_unverified"
                    if meaning.get("identity_basis") == "producer_key_only"
                    else "legacy_unverified"
                    if meaning.get("canonical_id") and not meaning.get("identity_basis")
                    else "source_asserted"
                    if meaning.get("canonical_id")
                    else "not_applicable"
                )
                meaning["freshness_status"] = self._aggregate_freshness(
                    [evidence["freshness_status"] for evidence in evidence_out]
                )
                if meaning.get("kind") == "duty":
                    # Who holds it, in the words a reader uses: the field the row stores
                    # addresses an entity key, and the key alone answers nothing.
                    meaning["holder_name"] = entity_names.get(str(meaning.get("holder") or ""))
                elif meaning.get("kind") == "event":
                    # A change is read by its two sides: which units went in, which came
                    # out, and where those two lists came from.
                    meaning["from_names"] = [entity_names.get(str(key), "")
                                             for key in (meaning.get("from") or ())]
                    meaning["to_names"] = [entity_names.get(str(key), "")
                                           for key in (meaning.get("to") or ())]
                if meaning.get("kind") in {"duty", "event"}:
                    # Saved and reviewable is not the same as read as a fact. A row whose
                    # own evidence does not carry it, or that was read as pending, comes
                    # back with the limit it was read under - never dressed as confirmed.
                    if (meaning.get("qualification") not in {"stated", "inferred"}
                            or meaning.get("verification") != "confirmed"):
                        meaning["restriction"] = {
                            "kind": "pending",
                            "reads_as": "candidate_only",
                            "qualification": meaning.get("qualification"),
                            "verification": meaning.get("verification"),
                            "missing": [meaning.get("qualification_basis")
                                        or "not_confirmed_against_its_evidence"],
                        }
                        restricted_meaning_count += 1
                if meaning.get("kind") == "unknown":
                    # An absence speaks for the places it searched, never for the material.
                    # The read says that on the row, so a consumer cannot take "not stated
                    # here" as "not true anywhere" without seeing the limit it was read under.
                    restriction = {
                        "kind": "absence",
                        "reads_as": "searched_scope_only",
                        "absence": meaning.get("absence"),
                        "searched": list(meaning.get("searched") or ()),
                    }
                    if meaning.get("unread_scopes"):
                        # How much of the source this row was read over, when the run wrote
                        # one: a reader is told the limit on the row it reads, not asked to
                        # open the raw quote again to find it.
                        restriction["unread_scopes"] = list(meaning.get("unread_scopes") or ())
                    meaning["restriction"] = restriction
                    restricted_meaning_count += 1
                meanings.append(meaning)
            meanings.sort(key=lambda row: (row.get("line_start", 0), row["meaning_id"]))
            if (include_all_active or expand_relations_for is not None) and len(meanings) > limit:
                meanings = meanings[:limit]
                truncated = True
            meaning_ids = sorted(row["meaning_id"] for row in meanings)
            for candidate in semantic_state["candidates"].values():
                decision_id = candidate.get("latest_decision_id")
                decision = semantic_state["decisions"].get(decision_id, {}) if decision_id else {}
                if decision.get("decision") in {"ACCEPTED", "REJECTED"}:
                    continue
                evaluation_id = candidate.get("latest_evaluation_id")
                evaluation = semantic_state["evaluations"].get(evaluation_id, {}) if evaluation_id else {}
                if evaluation.get("status") != "needs_review":
                    continue
                for finding in evaluation.get("findings", []):
                    if finding.get("code") != "active_meaning_conflict":
                        continue
                    entry = next(
                        (item for item in candidate.get("entries", []) if item.get("meaning_id") == finding.get("meaning_id")),
                        None,
                    )
                    if entry is not None and (not query_terms or _score(query_terms, f"{entry.get('kind', '')} {entry.get('key', '')} {entry.get('meaning', '')}")):
                        pending_conflicts.append({
                            "candidate_id": candidate["candidate_id"],
                            "meaning_id": entry["meaning_id"],
                            "source_id": entry["source_id"],
                            "source_revision": entry["source_revision"],
                            "status": "needs_review",
                            "reason_code": finding["code"],
                        })
            if meanings:
                freshness_status = self._aggregate_freshness([row["freshness_status"] for row in meanings])
                knowledge_status = "needs_reconciliation" if freshness_status != "fresh" or pending_conflicts else "current"

        if mode == "accepted_enterprise_semantics":
            used_source_ids = {
                evidence["source_id"]
                for meaning in meanings
                for evidence in meaning.get("evidence", [])
            }
            documents = [
                source_views[source_id]["document"]
                for source_id in sorted(used_source_ids)
                if source_id in source_views
            ]

        if mode == "grounded_claims":
            status = "FOUND" if claims or capability_rows else "UNKNOWN"
        elif mode == "source_discovery":
            status = "FOUND" if documents else "UNKNOWN"
        else:
            status = "success" if knowledge_status == "current" else "needs_reconciliation" if knowledge_status == "needs_reconciliation" else "unknown"
        return {
            "contract_version": 1,
            "scope_id": self.scope_id,
            "read_mode": mode,
            "authority": authority,
            "knowledge_status": knowledge_status,
            "freshness_status": freshness_status,
            "status": status,
            "active_version_id": active_version_id,
            "version_id": selected_version_id,
            "source_count": len({row["source_id"] for row in documents}),
            "document_count": len(documents),
            "claim_count": len(claims),
            "capability_count": len(capability_rows),
            "meaning_count": len(meanings),
            # How many of the returned meanings carry a stated limit: an absence is read
            # for the scope it searched and nothing wider.
            "restricted_meaning_count": restricted_meaning_count,
            "truncated": truncated,
            "documents": documents,
            "claims": claims,
            "stale_claims": stale_claims,
            "capabilities": capability_rows,
            "meanings": meanings,
            "meaning_ids": meaning_ids,
            "pending_conflicts": pending_conflicts,
            "applicability_status": applicability_status,
            "applicability_unknown_claim_ids": applicability_unknown_claim_ids,
            "causal_influence_proven": False,
        }

    @staticmethod
    def _aggregate_freshness(values: Sequence[str]) -> str:
        if not values:
            return "unknown"
        normalized = {value for value in values}
        if normalized == {"fresh"}:
            return "fresh"
        fresh_count = sum(value == "fresh" for value in values)
        if fresh_count:
            return "partial"
        if any(value in {"stale", "changed_unstaged", "missing_or_unresolvable"} for value in values):
            return "stale"
        if all(value == "current_catalog_projection" for value in values):
            return "fresh"
        return "unknown"

    @staticmethod
    def format_context(result: Mapping[str, Any]) -> str:
        scope_id = result.get("scope_id", "unknown")
        lines = [
            "Wiki context (DERIVED / NON-AUTHORITY; source and scope are explicit):",
            f"Scope: {scope_id}",
            f"Applicability: {result.get('applicability_status', 'UNKNOWN')}",
            f"Knowledge read mode: {result.get('read_mode', 'grounded_claims')}; freshness: {result.get('freshness_status', 'unknown')}; active semantic version: {result.get('active_version_id') or 'UNKNOWN'}.",
        ]
        if result.get("applicability_unknown_claim_ids"):
            lines.append(
                "A matched source contains an unresolved approval or condition requirement. "
                "Do not expose a Capability for this task; ask for authoritative clarification."
            )
        claims = result.get("claims", [])
        for claim in claims:
            lines.append(
                f"Claim {claim['claim_id']} [{claim['status']}], source {claim['source_id']} "
                f"revision {claim['revision']} line {claim['line_start']}: {claim['kind']} — {claim['meaning']}"
            )
        fresh = [
            row for row in result.get("accepted_semantics", [])
            if row.get("freshness_status") == "fresh"
        ]
        # Saved and reviewed is not the same as read as a fact: a row the read marked
        # candidate-only is said under that limit, never among the accepted meanings.
        accepted = [row for row in fresh if not reads_as_pending(row)]
        pending = [row for row in fresh if reads_as_pending(row)]
        semantic_view = result.get("accepted_semantic_view") or {}
        if accepted:
            lines.append(
                "Locally accepted scoped semantics (still not execution permission; each row carries source evidence):"
            )
            for row in accepted:
                evidence = "; ".join(
                    f"{item['source_id']}@{item['source_revision']} line {item['line_start']}"
                    for item in row.get("evidence", []) if item.get("freshness_status") == "fresh"
                )
                lines.append(
                    f"Meaning {row['meaning_id']} [{row['kind']}] {row['meaning']} "
                    f"(canonical {row.get('canonical_id') or 'unmapped'}; evidence: {evidence})"
                )
        elif semantic_view.get("knowledge_status") == "needs_reconciliation":
            lines.append(
                f"Accepted semantic version {semantic_view.get('active_version_id') or 'UNKNOWN'} has changed or unresolved source dependencies. "
                "Do not rely on it as current; request reconciliation or authoritative clarification."
            )
        if pending:
            lines.append(
                "Locally saved but still pending scoped semantics (read as candidate only; "
                "not a fact of the material, not execution permission, and not a basis for "
                "acting or for answering as confirmed):"
            )
            for row in pending:
                missing = row["restriction"].get("missing") or ["not_confirmed_against_its_evidence"]
                lines.append(
                    f"Candidate {row['meaning_id']} [{row['kind']}] pending "
                    f"({row.get('qualification') or 'pending'}/{row.get('verification') or 'unconfirmed'}; "
                    f"missing {', '.join(missing)}): {row['meaning']}"
                )
        capabilities = result.get("capabilities", [])
        if capabilities:
            lines.append("Currently active, read-only Catalog projections retrieved for this request:")
            for capability in capabilities:
                lines.append(
                    f"{capability['name']} — {capability['meaning']} "
                    f"(exact binding {capability['capability_id']}@{capability['capability_version']}; "
                    f"catalog claim {capability['claim_id']}; recheck R5 policy before execution)"
                )
        else:
            lines.append("No matching active read-only Capability projection was found; report UNKNOWN if needed.")
        return "\n".join(lines)
