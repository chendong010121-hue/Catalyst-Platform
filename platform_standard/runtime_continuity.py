"""P1 execution-continuity value shapes and pure receipt validation.

The module intentionally has no Runtime, Registry, I/O, or authorization
policy.  It carries owner-supplied identity facts and checks the small
cross-field contract at the Platform boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


NAMESPACE = "experimental.execution_continuity"


class ContinuityContractError(ValueError):
    """A malformed or internally inconsistent P1 continuity receipt."""


def _non_empty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")


@dataclass(frozen=True)
class BindingContinuityFact:
    capability_id: str
    capability_version: str
    binding_ref: str
    implementation_ref: str
    admission_ref: str | None = None

    def __post_init__(self) -> None:
        for label in (
            "capability_id",
            "capability_version",
            "binding_ref",
            "implementation_ref",
        ):
            _non_empty(getattr(self, label), f"BindingContinuityFact.{label}")
        if self.admission_ref is not None:
            _non_empty(self.admission_ref, "BindingContinuityFact.admission_ref")


@dataclass(frozen=True)
class AuthorityDecisionFact:
    authority_decision_id: str
    decision: str
    invocation_id: str
    capability_id: str
    capability_version: str
    binding_ref: str
    subject_ref: str
    authority_source_ref: str
    resource_ref: str
    scope_ref: str
    reason_code: str | None = None

    def __post_init__(self) -> None:
        for label in (
            "authority_decision_id",
            "invocation_id",
            "capability_id",
            "capability_version",
            "binding_ref",
            "subject_ref",
            "authority_source_ref",
            "resource_ref",
            "scope_ref",
        ):
            _non_empty(getattr(self, label), f"AuthorityDecisionFact.{label}")
        if self.decision not in ("ALLOW", "DENY"):
            raise ValueError("AuthorityDecisionFact.decision must be ALLOW or DENY")
        if self.reason_code is not None:
            _non_empty(self.reason_code, "AuthorityDecisionFact.reason_code")


class AuthorityDecisionConsumer(Protocol):
    def consume(
        self, invocation: Any, binding_fact: BindingContinuityFact
    ) -> AuthorityDecisionFact | None:
        ...


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContinuityContractError(f"{label} must be a mapping")
    return value


def _require_key(mapping: Mapping[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise ContinuityContractError(f"{label} missing {key!r}")
    return mapping[key]


def build_continuity_extension(
    *,
    continuity_status: str,
    binding: BindingContinuityFact,
    authority_status: str,
    authority_fact: AuthorityDecisionFact | None,
    session_id: str | None,
    execution_id: str | None,
    protected_dispatch_started: bool | None,
    certainty: str,
    blocker: str | None,
    invocation_id: str,
    result_id: str,
    trace_id: str,
    artifact_ids: Sequence[str],
) -> dict[str, Any]:
    """Build and validate one P1 optional Result extension."""
    if not isinstance(binding, BindingContinuityFact):
        raise ContinuityContractError("binding must be BindingContinuityFact")
    if authority_status not in ("allow", "deny", "missing", "invalid"):
        raise ContinuityContractError("invalid authority status")
    if authority_status in ("allow", "deny") and not isinstance(
        authority_fact, AuthorityDecisionFact
    ):
        raise ContinuityContractError(
            "allow/deny authority status requires an AuthorityDecisionFact"
        )
    if authority_status in ("missing", "invalid") and authority_fact is not None:
        raise ContinuityContractError(
            "missing/invalid authority status must not carry a decision fact"
        )
    if authority_fact is not None and authority_status != authority_fact.decision.lower():
        raise ContinuityContractError("authority status does not match decision fact")
    _non_empty(invocation_id, "invocation_id")
    _non_empty(result_id, "result_id")
    _non_empty(trace_id, "trace_id")
    if not isinstance(artifact_ids, Sequence) or isinstance(artifact_ids, (str, bytes)):
        raise ContinuityContractError("artifact_ids must be a sequence")
    for artifact_id in artifact_ids:
        _non_empty(artifact_id, "artifact_id")

    authority_payload = {
        "status": authority_status,
        "authority_decision_id": (
            authority_fact.authority_decision_id if authority_fact else None
        ),
        "subject_ref": authority_fact.subject_ref if authority_fact else None,
        "authority_source_ref": (
            authority_fact.authority_source_ref if authority_fact else None
        ),
        "resource_ref": authority_fact.resource_ref if authority_fact else None,
        "scope_ref": authority_fact.scope_ref if authority_fact else None,
        "reason_code": authority_fact.reason_code if authority_fact else None,
    }
    extension = {
        "version": "1",
        "required": False,
        "payload": {
            "continuity_status": continuity_status,
            "binding": {
                "capability_id": binding.capability_id,
                "capability_version": binding.capability_version,
                "binding_ref": binding.binding_ref,
                "implementation_ref": binding.implementation_ref,
                "admission_ref": binding.admission_ref,
            },
            "authority": authority_payload,
            "execution": {
                "session_id": session_id,
                "execution_id": execution_id,
                "protected_dispatch_started": protected_dispatch_started,
                "certainty": certainty,
                "blocker": blocker,
            },
            "evidence": {
                "invocation_id": invocation_id,
                "result_id": result_id,
                "trace_id": trace_id,
                "artifact_ids": list(artifact_ids),
            },
        },
    }
    validate_continuity_extension(extension)
    return extension


def validate_continuity_extension(extension: Mapping[str, Any]) -> None:
    """Validate the P1 envelope, payload, and cross-field invariants."""
    try:
        if not isinstance(extension, Mapping):
            raise ContinuityContractError("extension must be a mapping")
        if _require_key(extension, "version", "extension") != "1":
            raise ContinuityContractError("extension.version must be '1'")
        if _require_key(extension, "required", "extension") is not False:
            raise ContinuityContractError("extension.required must be false")
        payload = _require_mapping(_require_key(extension, "payload", "extension"), "payload")
        continuity_status = _require_key(payload, "continuity_status", "payload")
        if continuity_status not in ("complete", "incomplete"):
            raise ContinuityContractError("invalid continuity_status")

        binding = _require_mapping(_require_key(payload, "binding", "payload"), "binding")
        for key in (
            "capability_id",
            "capability_version",
            "binding_ref",
            "implementation_ref",
        ):
            _non_empty(_require_key(binding, key, "binding"), f"binding.{key}")
        if binding.get("admission_ref") is not None:
            _non_empty(binding["admission_ref"], "binding.admission_ref")

        authority = _require_mapping(
            _require_key(payload, "authority", "payload"), "authority"
        )
        status = _require_key(authority, "status", "authority")
        if status not in ("allow", "deny", "missing", "invalid"):
            raise ContinuityContractError("invalid authority.status")
        for key in (
            "authority_decision_id",
            "subject_ref",
            "authority_source_ref",
            "resource_ref",
            "scope_ref",
            "reason_code",
        ):
            _require_key(authority, key, "authority")
        decision_id = authority["authority_decision_id"]
        if status in ("allow", "deny"):
            _non_empty(decision_id, "authority.authority_decision_id")
        elif decision_id is not None:
            raise ContinuityContractError(
                "missing/invalid authority must not fabricate decision identity"
            )

        execution = _require_mapping(
            _require_key(payload, "execution", "payload"), "execution"
        )
        session_id = _require_key(execution, "session_id", "execution")
        execution_id = _require_key(execution, "execution_id", "execution")
        protected = _require_key(execution, "protected_dispatch_started", "execution")
        certainty = _require_key(execution, "certainty", "execution")
        blocker = _require_key(execution, "blocker", "execution")
        if certainty not in (
            "settled_success",
            "settled_failure",
            "unresolved",
            "not_dispatched",
        ):
            raise ContinuityContractError("invalid execution.certainty")
        if blocker not in (None, "authority", "runtime_policy"):
            raise ContinuityContractError("invalid execution.blocker")
        if protected not in (True, False, None):
            raise ContinuityContractError(
                "execution.protected_dispatch_started must be bool or null"
            )
        if execution_id is not None:
            _non_empty(execution_id, "execution.execution_id")
        if session_id is not None:
            _non_empty(session_id, "execution.session_id")

        if certainty == "not_dispatched":
            if execution_id is not None or protected is not False:
                raise ContinuityContractError(
                    "not_dispatched requires no execution_id and protected=false"
                )
        if blocker == "authority" or blocker == "runtime_policy":
            if certainty != "not_dispatched":
                raise ContinuityContractError("blocker requires not_dispatched certainty")
        if blocker == "authority" and session_id is not None:
            raise ContinuityContractError("authority blocker must not have a session")
        if blocker == "runtime_policy":
            if session_id is None or execution_id is not None:
                raise ContinuityContractError(
                    "runtime_policy blocker requires session and no execution"
                )
        if certainty in ("settled_success", "settled_failure"):
            if (
                continuity_status != "complete"
                or session_id is None
                or execution_id is None
                or protected is not True
            ):
                raise ContinuityContractError(
                    "settled execution requires complete protected identity"
                )
        if certainty == "unresolved":
            if continuity_status == "complete" and (
                session_id is None or execution_id is None or protected is not True
            ):
                raise ContinuityContractError(
                    "complete unresolved execution requires protected identity"
                )
            if execution_id is None and protected is True:
                raise ContinuityContractError(
                    "unresolved without execution identity cannot claim protected dispatch"
                )

        evidence = _require_mapping(
            _require_key(payload, "evidence", "payload"), "evidence"
        )
        for key in ("invocation_id", "result_id", "trace_id"):
            _non_empty(_require_key(evidence, key, "evidence"), f"evidence.{key}")
        artifact_ids = _require_key(evidence, "artifact_ids", "evidence")
        if not isinstance(artifact_ids, list):
            raise ContinuityContractError("evidence.artifact_ids must be a list")
        for artifact_id in artifact_ids:
            _non_empty(artifact_id, "evidence.artifact_id")
    except (ContinuityContractError, ValueError):
        raise
    except Exception as exc:  # malformed third-party mapping/proxy
        raise ContinuityContractError("malformed continuity extension") from exc


__all__ = [
    "AuthorityDecisionConsumer",
    "AuthorityDecisionFact",
    "BindingContinuityFact",
    "ContinuityContractError",
    "NAMESPACE",
    "build_continuity_extension",
    "validate_continuity_extension",
]
