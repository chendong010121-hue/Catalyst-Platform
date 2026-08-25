"""Explicit Case-local Knowledge Revision binding for BREA v0.9-candidate.

Knowledge Revision identity is a deterministic canonical SHA256 over the
Knowledge Revision content, NOT the raw file bytes. This keeps the binding
stable across JSON indentation / object-key order / line-ending serialization
differences and across machine-local `sources[].local_reference` relocation,
while any knowledge-bearing change still changes the identity.

Only `sources[].local_reference` (an execution-local machine path) is excluded
from the identity projection. All other content — source SHA, authority, title,
version, standards, routes, facts, schemas, etc. — participates in the hash.
Malformed JSON, identity mismatch, non-standard JSON numeric constants such as
NaN/Infinity, and expected-hash mismatch all fail closed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


class KnowledgeBindingError(RuntimeError):
    """Missing, malformed, unreadable, or hash-mismatched binding."""


def _reject_non_standard_constant(value: str) -> Any:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def _canonical_knowledge_sha(document: dict[str, Any]) -> str:
    """Deterministic canonical Knowledge Revision SHA256."""
    projection = copy.deepcopy(document)
    sources = projection.get("sources")
    if not isinstance(sources, list):
        raise KnowledgeBindingError("knowledge revision sources must be a list")
    for source in sources:
        if not isinstance(source, dict):
            raise KnowledgeBindingError("knowledge revision source record must be an object")
        source.pop("local_reference", None)
    try:
        payload = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise KnowledgeBindingError("knowledge revision cannot be deterministically serialized") from exc
    return hashlib.sha256(payload).hexdigest()


def load_knowledge_binding(binding: dict[str, Any] | None) -> tuple[dict, dict]:
    if not isinstance(binding, dict):
        raise KnowledgeBindingError("knowledge binding is required")
    revision_id = binding.get("revision_id")
    raw_path = binding.get("path")
    expected_sha = binding.get("sha256")
    if not isinstance(revision_id, str) or not revision_id:
        raise KnowledgeBindingError("knowledge binding revision_id is required")
    if not isinstance(raw_path, str) or not raw_path:
        raise KnowledgeBindingError("knowledge binding path is required")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        raise KnowledgeBindingError("knowledge binding sha256 is required")
    path = Path(raw_path)
    if not path.is_file():
        raise KnowledgeBindingError("knowledge revision file is missing")
    try:
        raw_text = path.read_text(encoding="utf-8")
        knowledge = json.loads(raw_text, parse_constant=_reject_non_standard_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise KnowledgeBindingError("knowledge revision is not valid JSON") from exc
    if not isinstance(knowledge, dict):
        raise KnowledgeBindingError("knowledge revision must be a JSON object")
    if knowledge.get("knowledge_revision_id") != revision_id:
        raise KnowledgeBindingError("knowledge revision identity mismatch")
    required = ("sources", "standards", "routes", "fact_descriptors")
    if any(key not in knowledge for key in required):
        raise KnowledgeBindingError("knowledge revision schema is incomplete")
    actual_sha = _canonical_knowledge_sha(knowledge)
    if actual_sha != expected_sha.lower():
        raise KnowledgeBindingError("knowledge revision SHA mismatch")
    return knowledge, {"revision_id": revision_id, "sha256": actual_sha}
