"""Platform Standard Core v0.1 — Platform Validator (Spec §10).

Checks ONLY the Platform Standard contract:

    object envelope
    required fields
    JSON compatibility
    Extension structure
    Result status semantics
    Capability descriptor minimum structure

Fail-closed: raises ValidationError, never silently repairs malformed payloads.

It MUST NOT duplicate Runtime business/execution validation. The existing
Runtime / CapabilityExecutor remains responsible for actual capability input
validation during execution.
"""

from __future__ import annotations

from typing import Any

from .extensions import (
    RESULT_STATUSES,
    SUPPORTED_EVENT_TYPES,
    SUPPORTED_SIDE_EFFECTS,
    validate_extensions,
)
from .models import ArtifactRef, CapabilityDescriptor, Invocation, Result, TraceEvent


class ValidationError(Exception):
    """Platform Standard contract violation (fail-closed)."""


def _is_json_compatible(value) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_is_json_compatible(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_json_compatible(v) for k, v in value.items())
    return False


def _require_nonempty_str(obj, field_name: str, errors: list[str]) -> None:
    value = getattr(obj, field_name, None)
    if not isinstance(value, str) or not value:
        errors.append(f"{type(obj).__name__}.{field_name} must be a non-empty string")


def _require_json_compatible(obj, field_name: str, errors: list[str]) -> None:
    value = getattr(obj, field_name, None)
    if not _is_json_compatible(value):
        errors.append(f"{type(obj).__name__}.{field_name} must be JSON-compatible")


def _check_envelope(obj, errors: list[str]) -> None:
    if getattr(obj, "standard_version", None) != "0.1":
        errors.append("standard_version must be '0.1'")
    _require_nonempty_str(obj, "kind", errors)
    _require_nonempty_str(obj, "id", errors)
    extensions = getattr(obj, "extensions", None)
    if extensions is not None:
        errors.extend(validate_extensions(extensions))


class PlatformValidator:
    """Fail-closed validator for Platform Standard Core v0.1 objects."""

    def validate_capability(self, descriptor: CapabilityDescriptor) -> None:
        errors: list[str] = []
        _check_envelope(descriptor, errors)
        if descriptor.kind != "capability":
            errors.append("kind must be 'capability'")
        _require_nonempty_str(descriptor, "name", errors)
        _require_nonempty_str(descriptor, "description", errors)
        _require_nonempty_str(descriptor, "capability_version", errors)
        _require_json_compatible(descriptor, "input_schema", errors)
        _require_json_compatible(descriptor, "output_schema", errors)
        if not isinstance(descriptor.execution, dict) or "side_effect" not in descriptor.execution:
            errors.append("execution.side_effect is required")
        elif descriptor.execution.get("side_effect") not in SUPPORTED_SIDE_EFFECTS:
            errors.append(f"execution.side_effect must be one of {SUPPORTED_SIDE_EFFECTS}")
        self._raise_if(errors)

    def validate_invocation(self, invocation: Invocation) -> None:
        errors: list[str] = []
        _check_envelope(invocation, errors)
        if invocation.kind != "invocation":
            errors.append("kind must be 'invocation'")
        _require_nonempty_str(invocation, "capability_id", errors)
        _require_nonempty_str(invocation, "capability_version", errors)
        _require_json_compatible(invocation, "input", errors)
        if not isinstance(invocation.context, dict):
            errors.append("invocation.context must be a map")
        else:
            ctx_ext = invocation.context.get("extensions")
            if ctx_ext is not None:
                errors.extend(validate_extensions(ctx_ext))
        _require_nonempty_str(invocation, "trace_id", errors)
        self._raise_if(errors)

    def validate_result(self, result: Result) -> None:
        errors: list[str] = []
        _check_envelope(result, errors)
        if result.kind != "result":
            errors.append("kind must be 'result'")
        _require_nonempty_str(result, "invocation_id", errors)
        if result.status not in RESULT_STATUSES:
            errors.append(f"status must be one of {RESULT_STATUSES}")
        _require_json_compatible(result, "output", errors)
        if not isinstance(result.artifacts, (list, tuple)):
            errors.append("artifacts must be a list")
        else:
            for artifact in result.artifacts:
                try:
                    self.validate_artifact_ref(artifact)
                except ValidationError as exc:
                    errors.append(f"invalid artifact: {exc}")
        # Status semantics (Spec §7).
        if result.status == "success":
            if result.error is not None:
                errors.append("success result must have error == null")
        elif result.status in ("failure", "unresolved"):
            if result.error is None or not isinstance(result.error, dict):
                errors.append(f"'{result.status}' result must have error {{code, message}}")
            elif "code" not in result.error or "message" not in result.error:
                errors.append("error must contain 'code' and 'message'")
        self._raise_if(errors)

    def validate_artifact_ref(self, artifact: ArtifactRef) -> None:
        errors: list[str] = []
        _check_envelope(artifact, errors)
        if artifact.kind != "artifact_ref":
            errors.append("kind must be 'artifact_ref'")
        _require_nonempty_str(artifact, "artifact_type", errors)
        _require_nonempty_str(artifact, "artifact_version", errors)
        _require_nonempty_str(artifact, "uri", errors)
        producer = artifact.producer
        if isinstance(producer, dict):
            producer_capability_id = producer.get("capability_id")
            producer_invocation_id = producer.get("invocation_id")
        else:
            producer_capability_id = getattr(producer, "capability_id", None)
            producer_invocation_id = getattr(producer, "invocation_id", None)
        if not producer_capability_id or not producer_invocation_id:
            errors.append("producer must contain capability_id and invocation_id")
        self._raise_if(errors)

    def validate_trace_event(self, event: TraceEvent) -> None:
        errors: list[str] = []
        _check_envelope(event, errors)
        if event.kind != "trace_event":
            errors.append("kind must be 'trace_event'")
        _require_nonempty_str(event, "trace_id", errors)
        if event.event_type not in SUPPORTED_EVENT_TYPES:
            errors.append(f"event_type must be one of {SUPPORTED_EVENT_TYPES}")
        _require_nonempty_str(event, "timestamp", errors)
        _require_nonempty_str(event, "subject_id", errors)
        self._raise_if(errors)

    def validate(self, obj) -> None:
        """Dispatch validation by Standard object kind."""
        if isinstance(obj, CapabilityDescriptor):
            self.validate_capability(obj)
        elif isinstance(obj, Invocation):
            self.validate_invocation(obj)
        elif isinstance(obj, Result):
            self.validate_result(obj)
        elif isinstance(obj, ArtifactRef):
            self.validate_artifact_ref(obj)
        elif isinstance(obj, TraceEvent):
            self.validate_trace_event(obj)
        else:
            raise ValidationError(f"unknown Platform Standard object type: {type(obj).__name__}")

    @staticmethod
    def _raise_if(errors: list[str]) -> None:
        if errors:
            raise ValidationError("; ".join(errors))


__all__ = ["PlatformValidator", "ValidationError"]
