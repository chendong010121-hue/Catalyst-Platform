"""Explicit Case-local Knowledge Revision binding for BREA v0.6."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class KnowledgeBindingError(RuntimeError):
    """Missing, malformed, unreadable, or hash-mismatched binding."""


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
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha != expected_sha.lower():
        raise KnowledgeBindingError("knowledge revision SHA mismatch")
    try:
        knowledge = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeBindingError("knowledge revision is not valid JSON") from exc
    if not isinstance(knowledge, dict) or knowledge.get("knowledge_revision_id") != revision_id:
        raise KnowledgeBindingError("knowledge revision identity mismatch")
    required = ("sources", "standards", "routes", "fact_descriptors")
    if any(key not in knowledge for key in required):
        raise KnowledgeBindingError("knowledge revision schema is incomplete")
    return knowledge, {"revision_id": revision_id, "sha256": actual_sha}
