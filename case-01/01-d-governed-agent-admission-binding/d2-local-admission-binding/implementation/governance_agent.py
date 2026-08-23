"""D2 — Case-local governance.agent interpreter (Stage Spec §8, P-D2-01).

Canonical Agent attribution source: Invocation.extensions["governance.agent"] ONLY.
Invocation.context.extensions must NOT carry governance.agent (ambiguous authority -> fail closed).
Attribution rides TraceEvent.extensions; conflicts fail closed.
Generic platform_standard/extensions.py is NOT modified.
"""
from __future__ import annotations

from platform_standard.models import Invocation, TraceEvent

EXTENSION_NAME = "governance.agent"
EXTENSION_VERSION = "0.1"


class GovernanceAgentError(ValueError):
    pass


def parse_governance_agent(invocation: Invocation) -> dict:
    context_ext = (invocation.context or {}).get("extensions") or {}
    if context_ext.get(EXTENSION_NAME) is not None:
        raise GovernanceAgentError(
            "governance.agent must not appear in Invocation.context.extensions (ambiguous attribution authority)"
        )
    ext = (invocation.extensions or {}).get(EXTENSION_NAME)
    if ext is None:
        raise GovernanceAgentError("governance.agent missing on governed execution")
    if not isinstance(ext, dict):
        raise GovernanceAgentError("governance.agent must be an object")
    if ext.get("version") != EXTENSION_VERSION:
        raise GovernanceAgentError(f"governance.agent version {ext.get('version')!r} unsupported")
    if ext.get("required") is not False:
        raise GovernanceAgentError("governance.agent.required must be false under Core v0.1")
    payload = ext.get("payload")
    if not isinstance(payload, dict):
        raise GovernanceAgentError("governance.agent.payload must be an object")
    for field in ("agent_id", "agent_version", "admission_ref", "binding_ref"):
        if not isinstance(payload.get(field), str) or not payload[field]:
            raise GovernanceAgentError(f"governance.agent.payload.{field} missing or empty")
    return payload


def validate_against_records(payload: dict, admission: dict, binding: dict) -> None:
    if admission["admission_status"] != "ADMITTED":
        raise GovernanceAgentError("admission status is not ADMITTED")
    if binding["binding_status"] != "BOUND":
        raise GovernanceAgentError("binding status is not BOUND")
    if payload["agent_id"] != admission["agent_id"] or payload["agent_version"] != admission["agent_version"]:
        raise GovernanceAgentError("governance.agent agent identity mismatch with Admission Record")
    if payload["admission_ref"] != admission["admission_ref"]:
        raise GovernanceAgentError("admission_ref mismatch with Admission Record")
    if payload["binding_ref"] != binding["binding_id"]:
        raise GovernanceAgentError("binding_ref mismatch with Binding Record")


def attribute_trace(events, payload: dict) -> tuple[TraceEvent, ...]:
    extension_value = {
        EXTENSION_NAME: {"version": EXTENSION_VERSION, "required": False, "payload": payload}
    }
    attributed = []
    for event in events:
        existing = (event.extensions or {}).get(EXTENSION_NAME)
        if existing is not None:
            if existing != extension_value[EXTENSION_NAME]:
                raise GovernanceAgentError("conflicting governance.agent trace attribution")
            attributed.append(event)
            continue
        merged = dict(event.extensions or {})
        merged.update(extension_value)
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
