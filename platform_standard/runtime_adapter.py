"""Platform Standard Core v0.1 — Runtime Adapter (Spec §12 / §13).

Maps:  Standard Invocation -> existing Agent Runtime -> Standard Result,
attaching ArtifactRef(s) (via adapter-local per-capability mappers) and
emitting minimal Trace events.

The descriptor Registry stores Standard descriptors only. The Adapter keeps a
simple internal binding:

    (capability_id, capability_version) -> existing Runtime Capability implementation

Version routing stays in the Adapter: each (capability_id, capability_version)
gets a unique internal Runtime key through an adapter-local wrapper, so two
versions of the same capability_id never collapse into one implementation.

The Adapter maps SEMANTICS, not Runtime exception class names:

    known successful completion      -> success
    known terminal failure           -> failure
    execution certainty not closed   -> unresolved

It MUST NOT modify AgentCore, reimplement Runtime lifecycle, invent retry, or
auto-replay unresolved execution. It carries NO business/domain semantics.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any, Callable, Mapping

from agent_runtime.contracts import (
    Action,
    Act,
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Complete,
    Failure,
    Goal,
    ReasoningResult,
    Success,
)
from agent_runtime.errors import RuntimeExecutionError
from agent_runtime.runtime import Runtime

from .models import ArtifactRef, Invocation, Result, TraceEvent
from .registry import InMemoryDescriptorRegistry
from .validation import PlatformValidator


class AdapterConfigurationError(Exception):
    """RuntimeAdapter is missing a required composition input."""


class DirectedReasoner:
    """Reasoner that returns the Adapter-supplied Action, then Complete.

    Keeps the vertical slice inside the existing Agent Loop without modifying
    AgentCore or the Runtime.
    """

    def __init__(self) -> None:
        self.pending_action: Action | None = None

    def decide(self, goal, state, history, capabilities) -> ReasoningResult:
        if not history:
            return ReasoningResult(decision=Act(self.pending_action))
        return ReasoningResult(decision=Complete(reason="done"))


def _internal_key(capability_id: str, capability_version: str) -> str:
    """Deterministic portable Runtime key for one (capability_id, version)."""
    digest = hashlib.sha1(f"{capability_id}@{capability_version}".encode("utf-8")).hexdigest()
    return f"cap_{digest[:12]}"


class _RuntimeCapabilityBinding:
    """Adapter-local wrapper: binds one (capability_id, version) to a unique Runtime key."""

    def __init__(self, impl, internal_key: str) -> None:
        self._impl = impl
        self._internal_key = internal_key

    def describe(self) -> RuntimeCapabilityDescriptor:
        d = self._impl.describe()
        return RuntimeCapabilityDescriptor(
            id=self._internal_key,
            name=d.name,
            description=d.description,
            input_schema=d.input_schema,
            output_schema=d.output_schema,
        )

    def invoke(self, parameters, context):
        return self._impl.invoke(parameters, context)


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class RuntimeAdapter:
    """Executes Standard Invocations through an existing Agent Runtime.

    The caller supplies a `runtime_factory` (how to compose the Runtime from the
    adapter-local bindings and the directed reasoner) and optional per-capability
    `artifact_mappers` (adapter-local mapping from output to ArtifactRefs). The
    generic Adapter itself decides no Policy, StateStore or artifact semantics.
    """

    def __init__(
        self,
        registry: InMemoryDescriptorRegistry,
        bindings: Mapping[tuple[str, str], Any],
        *,
        runtime_factory: Callable[[Mapping[str, Any], DirectedReasoner], Runtime] | None = None,
        artifact_mappers: Mapping[tuple[str, str], Callable[[Any, Invocation], tuple[ArtifactRef, ...]]] | None = None,
        validator: PlatformValidator | None = None,
    ) -> None:
        self._registry = registry
        self._bindings = dict(bindings)
        self._validator = validator or PlatformValidator()
        self._artifact_mappers = dict(artifact_mappers or {})
        self._reasoner = DirectedReasoner()
        if runtime_factory is None:
            raise AdapterConfigurationError(
                "runtime_factory is required: the Adapter must not decide Policy / StateStore"
            )
        self._key_for: dict[tuple[str, str], str] = {}
        capabilities: dict[str, Any] = {}
        for (capability_id, capability_version), impl in self._bindings.items():
            key = _internal_key(capability_id, capability_version)
            self._key_for[(capability_id, capability_version)] = key
            capabilities[key] = _RuntimeCapabilityBinding(impl, key)
        self._runtime = runtime_factory(capabilities, self._reasoner)
        self._trace_events: list[TraceEvent] = []

    # ------------------------------------------------------------------
    # trace
    # ------------------------------------------------------------------
    def trace_events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._trace_events)

    def _emit(self, event_type: str, trace_id: str, subject_id: str) -> None:
        self._trace_events.append(
            TraceEvent(
                id=_new_id("event"),
                trace_id=trace_id,
                event_type=event_type,
                timestamp=_utc_now_iso(),
                subject_id=subject_id,
            )
        )

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------
    def execute(self, invocation: Invocation) -> Result:
        # 1. validate Invocation (Platform contract only)
        self._validator.validate_invocation(invocation)

        # 2. resolve Standard descriptor
        descriptor = self._registry.get(
            invocation.capability_id, invocation.capability_version
        )
        if descriptor is None:
            return self._fail(
                invocation,
                "capability_not_found",
                f"capability {invocation.capability_id!r} v{invocation.capability_version!r} is not registered",
            )

        # 3. resolve the exact (capability_id, capability_version) Runtime binding
        key = self._key_for.get((invocation.capability_id, invocation.capability_version))
        if key is None:
            return self._fail(
                invocation,
                "capability_not_bound",
                f"capability {invocation.capability_id!r} v{invocation.capability_version!r} has no Runtime binding",
            )

        # 4. emit started
        self._emit("invocation.started", invocation.trace_id, invocation.id)

        # 5. call the existing Runtime through the Agent Loop, routing to the
        #    exact (capability_id, capability_version) internal key
        self._reasoner.pending_action = Action(key, invocation.input)
        try:
            snapshot = self._runtime.start(Goal(invocation.capability_id))
        except RuntimeExecutionError:
            # execution certainty not closed: exception / timeout / cancellation
            # after a possible side effect -> unresolved (NOT did-not-execute,
            # NOT safe-to-retry)
            self._emit("invocation.unresolved", invocation.trace_id, invocation.id)
            return Result(
                id=_new_id("result"),
                invocation_id=invocation.id,
                status="unresolved",
                output=None,
                artifacts=(),
                error={
                    "code": "runtime_outcome_uncertain",
                    "message": (
                        "execution certainty is not closed; outcome is unknown and MUST NOT "
                        "be treated as did-not-execute or safe-to-retry"
                    ),
                },
            )

        # 6. map settled outcome (semantics, not exception names)
        observation = snapshot.history[0].observation
        if isinstance(observation, Success):
            output = observation.data
            mapper = self._artifact_mappers.get(
                (invocation.capability_id, invocation.capability_version)
            )
            artifacts = mapper(output, invocation) if mapper is not None else ()
            self._emit("invocation.completed", invocation.trace_id, invocation.id)
            for artifact in artifacts:
                self._emit("artifact.created", invocation.trace_id, artifact.id)
            return Result(
                id=_new_id("result"),
                invocation_id=invocation.id,
                status="success",
                output=output,
                artifacts=artifacts,
                error=None,
            )
        if isinstance(observation, Failure):
            self._emit("invocation.failed", invocation.trace_id, invocation.id)
            return Result(
                id=_new_id("result"),
                invocation_id=invocation.id,
                status="failure",
                output=None,
                artifacts=(),
                error={
                    "code": "capability_failed",
                    "message": observation.error or "capability returned a terminal failure",
                },
            )
        # unexpected: settled step without an Observation
        self._emit("invocation.failed", invocation.trace_id, invocation.id)
        return Result(
            id=_new_id("result"),
            invocation_id=invocation.id,
            status="failure",
            output=None,
            artifacts=(),
            error={
                "code": "runtime_contract_violation",
                "message": "settled execution step has no observation",
            },
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _fail(self, invocation: Invocation, code: str, message: str) -> Result:
        self._emit("invocation.failed", invocation.trace_id, invocation.id)
        return Result(
            id=_new_id("result"),
            invocation_id=invocation.id,
            status="failure",
            output=None,
            artifacts=(),
            error={"code": code, "message": message},
        )


__all__ = [
    "AdapterConfigurationError",
    "DirectedReasoner",
    "RuntimeAdapter",
]
