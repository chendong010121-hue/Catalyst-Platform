"""Platform Standard Core v0.1 — Standard object models.

All payloads are JSON-compatible. Each top-level Standard object carries the
Common Object Envelope (Spec §3):

    standard_version: "0.1"
    kind: <kind>
    id: <non-empty stable string>
    extensions: {}

Validation is deliberately NOT embedded in these models; the Platform Validator
(validation.py) is the single fail-closed contract check point.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Standard Capability (Spec §5)."""

    standard_version: str = "0.1"
    kind: str = "capability"
    id: str = ""
    extensions: Mapping[str, Any] = field(default_factory=dict)
    name: str = ""
    description: str = ""
    capability_version: str = ""
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    output_schema: Mapping[str, Any] = field(default_factory=dict)
    execution: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Invocation:
    """Standard Invocation (Spec §6)."""

    standard_version: str = "0.1"
    kind: str = "invocation"
    id: str = ""
    extensions: Mapping[str, Any] = field(default_factory=dict)
    capability_id: str = ""
    capability_version: str = ""
    input: Any = None
    context: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Producer:
    """ArtifactRef.producer (Spec §8)."""

    capability_id: str = ""
    invocation_id: str = ""


@dataclass(frozen=True)
class ArtifactRef:
    """Standard ArtifactRef (Spec §8)."""

    standard_version: str = "0.1"
    kind: str = "artifact_ref"
    id: str = ""
    extensions: Mapping[str, Any] = field(default_factory=dict)
    artifact_type: str = ""
    artifact_version: str = ""
    uri: str = ""
    producer: Producer = field(default_factory=Producer)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Result:
    """Standard Result (Spec §7)."""

    standard_version: str = "0.1"
    kind: str = "result"
    id: str = ""
    extensions: Mapping[str, Any] = field(default_factory=dict)
    invocation_id: str = ""
    status: str = ""
    output: Any = None
    artifacts: tuple[ArtifactRef, ...] = ()
    error: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TraceEvent:
    """Minimal Trace Event (Spec §9)."""

    standard_version: str = "0.1"
    kind: str = "trace_event"
    id: str = ""
    extensions: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    event_type: str = ""
    timestamp: str = ""
    subject_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


__all__ = [
    "ArtifactRef",
    "CapabilityDescriptor",
    "Invocation",
    "Producer",
    "Result",
    "TraceEvent",
]
