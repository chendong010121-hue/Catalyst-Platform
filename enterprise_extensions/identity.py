"""Enterprise Extension Pilot v0.1 — `enterprise.identity` semantic.

`enterprise.identity` answers: *in which enterprise identity context was this
Invocation issued?*

Identity here is an ATTRIBUTION CONTEXT, not a business parameter, not
authentication, not authorization.

Rules:
- Extend via Extension Contract only; no new Core fields.
- Only `version == "0.1"` is interpretable by this handler; any other version
  fails closed (EnterpriseIdentityError).
- Attribution rides on `TraceEvent.extensions`; generic TraceEvent schema is
  unchanged. Conflicts are never silently overwritten (fail closed).
- `execute_with_enterprise_identity` is a lightweight reference orchestration
  seam (validate -> parse -> generic adapter.execute -> attribute trace). It is
  NOT a Platform Standard object, an Enterprise Runtime, a workflow or a
  control plane.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platform_standard.models import Invocation, TraceEvent
from platform_standard.validation import PlatformValidator

EXTENSION_NAME = "enterprise.identity"
EXTENSION_VERSION = "0.1"


class EnterpriseIdentityError(ValueError):
    """Invalid / unsupported enterprise.identity payload (fail-closed)."""


@dataclass(frozen=True)
class EnterpriseIdentity:
    organization_id: str
    user_id: str
    project_id: str | None = None

    def to_extension(self) -> dict:
        payload = {"organization_id": self.organization_id, "user_id": self.user_id}
        if self.project_id is not None:
            payload["project_id"] = self.project_id
        return {
            EXTENSION_NAME: {
                "version": EXTENSION_VERSION,
                "required": False,
                "payload": payload,
            }
        }


def _require_nonempty_str(value, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise EnterpriseIdentityError(
            f"enterprise.identity payload.{field} must be a non-empty string"
        )


def parse_enterprise_identity(invocation: Invocation) -> EnterpriseIdentity | None:
    """Extract and validate `enterprise.identity` from an Invocation.

    Returns None when the extension is absent (identity is optional). Raises
    EnterpriseIdentityError on an unsupported version or invalid payload
    (fail-closed).
    """
    extensions = invocation.extensions or {}
    raw = extensions.get(EXTENSION_NAME)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise EnterpriseIdentityError(
            "enterprise.identity must be an object with version/required/payload"
        )
    version = raw.get("version")
    if version != EXTENSION_VERSION:
        raise EnterpriseIdentityError(
            f"enterprise.identity version {version!r} is not supported "
            f"(expected {EXTENSION_VERSION!r})"
        )
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise EnterpriseIdentityError("enterprise.identity.payload must be an object")
    organization_id = payload.get("organization_id")
    user_id = payload.get("user_id")
    _require_nonempty_str(organization_id, "organization_id")
    _require_nonempty_str(user_id, "user_id")
    project_id = payload.get("project_id")
    if project_id is not None:
        _require_nonempty_str(project_id, "project_id")
    return EnterpriseIdentity(
        organization_id=organization_id,
        user_id=user_id,
        project_id=project_id,
    )


def attribute_trace(events, identity: EnterpriseIdentity) -> tuple[TraceEvent, ...]:
    """Attach enterprise.identity attribution to trace events.

    Uses `TraceEvent.extensions` (no new Core trace fields). Conflict rule:

    - no existing identity            -> attach
    - existing identical identity     -> preserve / accept
    - existing conflicting identity   -> EnterpriseIdentityError (fail closed)
    """
    attribution = identity.to_extension()
    attribution_value = attribution[EXTENSION_NAME]
    attributed: list[TraceEvent] = []
    for event in events:
        existing = (event.extensions or {}).get(EXTENSION_NAME)
        if existing is not None:
            if existing != attribution_value:
                raise EnterpriseIdentityError(
                    "trace already carries a conflicting enterprise.identity "
                    "attribution; refusing to overwrite"
                )
            # identical -> preserve unchanged
            attributed.append(event)
            continue
        merged = dict(event.extensions or {})
        merged.update(attribution)
        attributed.append(
            TraceEvent(
                standard_version=event.standard_version,
                kind=event.kind,
                id=event.id,
                extensions=merged,
                trace_id=event.trace_id,
                event_type=event.event_type,
                timestamp=event.timestamp,
                subject_id=event.subject_id,
            )
        )
    return tuple(attributed)


def execute_with_enterprise_identity(adapter, invocation: Invocation, *, validator=None):
    """Reference Enterprise Extension execution path (REPAIR 2).

    PlatformValidator.validate_invocation
    -> parse enterprise.identity
    -> existing generic RuntimeAdapter.execute
    -> retrieve trace
    -> apply identity attribution (if identity present)

    Returns `(result, attributed_trace_events)`.
    """
    v = validator or PlatformValidator()
    v.validate_invocation(invocation)
    identity = parse_enterprise_identity(invocation)
    result = adapter.execute(invocation)
    if identity is not None:
        events = attribute_trace(adapter.trace_events(), identity)
    else:
        events = tuple(adapter.trace_events())
    return result, events


__all__ = [
    "EXTENSION_NAME",
    "EXTENSION_VERSION",
    "EnterpriseIdentity",
    "EnterpriseIdentityError",
    "attribute_trace",
    "execute_with_enterprise_identity",
    "parse_enterprise_identity",
]
