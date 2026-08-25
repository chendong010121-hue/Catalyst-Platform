from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from brea.knowledge import _canonical_knowledge_sha


def canonical_knowledge_sha(path: Path) -> str:
    document = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    if not isinstance(document, dict):
        raise ValueError("knowledge revision must be an object")
    return _canonical_knowledge_sha(document)


def canonical_binding(path: Path) -> dict[str, str]:
    revision = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    return {
        "revision_id": revision["knowledge_revision_id"],
        "path": str(path),
        "sha256": canonical_knowledge_sha(path),
    }


def raw_file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_revision(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    if not isinstance(value, dict):
        raise ValueError("knowledge revision must be an object")
    return value


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {value}")
