"""Platform Standard Core v0.1 — Runtime Adapter (Spec §12 / §13).

Maps:  Standard Invocation -> existing Agent Runtime -> Standard Result,
attaching ArtifactRef(s) and emitting minimal Trace events.

The descriptor Registry stores Standard descriptors only. The Adapter keeps a
simple internal binding:

    (capability_id, capability_version) -> existing Runtime Capability implementation

That binding is an implementation detail, not a Platform object.

The Adapter maps SEMANTICS, not Runtime exception class names:

    known successful completion  -> success
    known terminal failure       -> failure
    execution certainty not closed -> unresolved

It MUST NOT modify AgentCore, reimplement Runtime lifecycle, invent retry, or
auto-replay unresolved execution.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Mapping

from agent_runtime.contracts import (
    Action,
    Act,
    Complete,
    Failure,
    Goal,
    ReasoningResult,
    Success,
)
from agent_runtime.errors import RuntimeExecutionError
from agent_runtime.runtime import Runtime

from examples.fakes import AllowAllPolicy, InMemoryStateStore

from .models import ArtifactRef, Invocation, Producer, Result, TraceEvent
from .registry import InMemoryDescriptorRegistry
from .validation import PlatformValidator


class AdapterBindingError(Exception):
    """No Runtime implementation bound for the requested capability."""


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


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class RuntimeAdapter:
    """Executes Standard Invocations through the existing Agent Runtime."""

    def __init__(
        self,
        registry: InMemoryDescriptorRegistry,
        bindings: Mapping[tuple[str, str], Any],
        *,
        validator: PlatformValidator | None = None,
        timeout_config=None,
    ) -> None:
        self._registry = registry
        self._bindings = dict(bindings)
        self._validator = validator or PlatformValidator()
        self._reasoner = DirectedReasoner()
        capabilities: dict[str, Any] = {}
        for (capability_id, _version), impl in self._bindings.items():
            capabilities[capability_id] = impl
        self._runtime = Runtime(
            self._reasoner,
            capabilities,
            AllowAllPolicy(),
            InMemoryStateStore(),
            timeout_config=timeout_config,
        )
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
    # artifacts
    # ------------------------------------------------------------------
    def _build_artifacts(self, invocation: Invocation, output: Any) -> tuple[ArtifactRef, ...]:
        artifacts: list[ArtifactRef] = []
        if isinstance(output, dict):
            uri = output.get("artifact_uri")
            if isinstance(uri, str) and uri:
                artifacts.append(
                    ArtifactRef(
                        id=_new_id("artifact"),
                        artifact_type="report",
                        artifact_version="1",
                        uri=uri,
                        producer=Producer(
                            capability_id=invocation.capability_id,
                            invocation_id=invocation.id,
                        ),
                    )
                )
        return tuple(artifacts)

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

        # 3. resolve implementation binding
        impl = self._bindings.get((invocation.capability_id, invocation.capability_version))
        if impl is None:
            return self._fail(
                invocation,
                "capability_not_bound",
                f"capability {invocation.capability_id!r} v{invocation.capability_version!r} has no Runtime binding",
            )
        del impl  # binding resolved; execution goes through the Runtime

        # 4. emit started
        self._emit("invocation.started", invocation.trace_id, invocation.id)

        # 5. call the existing Runtime through the Agent Loop
        self._reasoner.pending_action = Action(invocation.capability_id, invocation.input)
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
            artifacts = self._build_artifacts(invocation, output)
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


__all__ = ["AdapterBindingError", "DirectedReasoner", "RuntimeAdapter"]
