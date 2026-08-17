"""Platform Standard Core v0.1 — Extension Contract (Spec §4).

Extensions are a first-class mechanism: enterprise/domain/governance/interop/
experimental change should enter through Extensions first, not through new Core
fields. Core v0.1 supports NO extension semantics, therefore:

    required=False  -> preserved unchanged (ignored semantically)
    required=True   -> fail closed (unsupported implementation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RESERVED_NAMESPACES = (
    "enterprise.",
    "domain.",
    "governance.",
    "interop.",
    "experimental.",
)

SUPPORTED_EVENT_TYPES = (
    "invocation.started",
    "invocation.completed",
    "invocation.failed",
    "invocation.unresolved",
    "artifact.created",
)

SUPPORTED_SIDE_EFFECTS = ("none", "possible")

RESULT_STATUSES = ("success", "failure", "unresolved")


@dataclass(frozen=True)
class Extension:
    """Typed view of one Extension value (version / required / payload)."""

    version: str = "1"
    required: bool = False
    payload: Any = None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "required": self.required,
            "payload": self.payload,
        }


def validate_extensions(extensions) -> list[str]:
    """Structural + Core v0.1 required/optional semantics.

    Returns a list of contract errors (empty list = OK). Raises nothing; the
    Validator decides how to fail closed.
    """
    errors: list[str] = []
    if extensions is None:
        return errors
    if not isinstance(extensions, dict):
        return ["extensions must be a map"]
    for name, value in extensions.items():
        if not isinstance(name, str) or not name:
            errors.append("extension name must be a non-empty string")
            continue
        if not isinstance(value, dict):
            errors.append(f"extension {name!r} must be an object with version/required/payload")
            continue
        version = value.get("version")
        if not isinstance(version, str) or not version:
            errors.append(f"extension {name!r} requires non-empty string 'version'")
        required = value.get("required")
        if not isinstance(required, bool):
            errors.append(f"extension {name!r} requires boolean 'required'")
        elif required is True:
            errors.append(
                f"extension {name!r} is required but unsupported by Core v0.1 (fail closed)"
            )
        if "payload" not in value:
            errors.append(f"extension {name!r} requires 'payload'")
    return errors


__all__ = [
    "Extension",
    "RESERVED_NAMESPACES",
    "RESULT_STATUSES",
    "SUPPORTED_EVENT_TYPES",
    "SUPPORTED_SIDE_EFFECTS",
    "validate_extensions",
]
