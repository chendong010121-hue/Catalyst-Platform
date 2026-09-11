"""Platform Standard Core v0.1 — Runtime Adapter (Spec §12 / §13).

Maps:  Standard Invocation -> existing Agent Runtime -> Standard Result,
attaching ArtifactRef(s) (via adapter-local per-capability mappers) and
emitting minimal Trace events.

The descriptor Registry stores Standard descriptors only. The Adapter keeps a
simple internal binding:

    (capability_id, capability_version) -> existing Runtime Capability implementation

For the current direct-binding reference path, the Adapter also performs a
minimal preflight conformance check: the bound Runtime implementation must
declare input/output schemas structurally equivalent to the registered
Platform Capability contract. This is intentionally a reference direct-binding
rule, not a universal requirement for future mapping Adapters.

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

import copy
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
    Allow,
    Deny,
    ReasoningResult,
    Success,
)
from agent_runtime.errors import RuntimeExecutionError
from agent_runtime.runtime import Runtime

from .models import ArtifactRef, CapabilityDescriptor, Invocation, Result, TraceEvent
from .registry import InMemoryDescriptorRegistry
from .runtime_continuity import (
    AuthorityDecisionFact,
    BindingContinuityFact,
    build_continuity_extension,
)
from .validation import PlatformValidator


class AdapterConfigurationError(Exception):
    """RuntimeAdapter composition/binding configuration is invalid."""


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


def _normalize_schema(value: Any) -> Any:
    """Normalize ordinary map ordering for deterministic direct-binding compare.

    This is deliberately NOT a JSON-Schema implication/subtyping engine. Lists
    remain ordered; only mapping key order is normalized recursively.
    """
    if isinstance(value, Mapping):
        return tuple(
            (key, _normalize_schema(value[key]))
            for key in sorted(value)
        )
    if isinstance(value, list):
        return tuple(_normalize_schema(item) for item in value)
    return value


def _checked_direct_binding_descriptor(
    platform_descriptor: CapabilityDescriptor,
    impl: Any,
    capability_id: str,
    capability_version: str,
) -> RuntimeCapabilityDescriptor:
    """Return a frozen checked Runtime descriptor or fail closed.

    Current v0.1 evidence rule: direct bindings use structural schema
    equivalence. A future mapping Adapter may use different implementation
    schemas if it provides explicit transformation/conformance evidence.

    The checked descriptor is deep-copied and reused by the Runtime wrapper so
    the implementation cannot pass preflight with one descriptor and expose a
    different descriptor during Runtime registration.
    """
    try:
        runtime_descriptor = impl.describe()
    except Exception as exc:  # noqa: BLE001
        raise AdapterConfigurationError(
            f"binding {capability_id!r} v{capability_version!r} cannot be inspected: "
            "implementation.describe() failed"
        ) from exc

    if not isinstance(runtime_descriptor, RuntimeCapabilityDescriptor):
        raise AdapterConfigurationError(
            f"binding {capability_id!r} v{capability_version!r} returned invalid "
            f"Runtime CapabilityDescriptor: {type(runtime_descriptor).__name__}"
        )

    checks = (
        ("input_schema", platform_descriptor.input_schema, runtime_descriptor.input_schema),
        ("output_schema", platform_descriptor.output_schema, runtime_descriptor.output_schema),
    )
    for label, platform_schema, runtime_schema in checks:
        if _normalize_schema(platform_schema) != _normalize_schema(runtime_schema):
            raise AdapterConfigurationError(
                f"binding {capability_id!r} v{capability_version!r} violates Platform "
                f"Capability {label}: direct-binding schemas are not structurally equivalent"
            )

    return copy.deepcopy(runtime_descriptor)


class _RuntimeCapabilityBinding:
    """Adapter-local wrapper: binds one (capability_id, version) to a unique Runtime key."""

    def __init__(
        self,
        impl: Any,
        internal_key: str,
        checked_descriptor: RuntimeCapabilityDescriptor,
    ) -> None:
        self._impl = impl
        self._internal_key = internal_key
        self._checked_descriptor = checked_descriptor

    def describe(self) -> RuntimeCapabilityDescriptor:
        d = self._checked_descriptor
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
        binding_continuity: Mapping[tuple[str, str], BindingContinuityFact] | None = None,
        authority_consumer: Any | None = None,
    ) -> None:
        self._registry = registry
        self._bindings = dict(bindings)
        self._validator = validator or PlatformValidator()
        self._artifact_mappers = dict(artifact_mappers or {})
        if (binding_continuity is None) != (authority_consumer is None):
            raise AdapterConfigurationError(
                "binding_continuity and authority_consumer must be supplied together"
            )
        self._continuity_enabled = binding_continuity is not None
        self._binding_continuity = dict(binding_continuity or {})
        self._authority_consumer = authority_consumer
        if self._continuity_enabled:
            if not callable(getattr(authority_consumer, "consume", None)):
                raise AdapterConfigurationError(
                    "authority_consumer must provide consume(invocation, binding_fact)"
                )
            if set(self._binding_continuity) != set(self._bindings):
                raise AdapterConfigurationError(
                    "every configured binding must have exactly one continuity fact"
                )
            for key, fact in self._binding_continuity.items():
                if not isinstance(fact, BindingContinuityFact):
                    raise AdapterConfigurationError(
                        f"continuity fact for {key!r} is not BindingContinuityFact"
                    )
                if key != (fact.capability_id, fact.capability_version):
                    raise AdapterConfigurationError(
                        f"continuity fact identity does not match binding key {key!r}"
                    )
        self._reasoner = DirectedReasoner()
        if runtime_factory is None:
            raise AdapterConfigurationError(
                "runtime_factory is required: the Adapter must not decide Policy / StateStore"
            )
        self._key_for: dict[tuple[str, str], str] = {}
        capabilities: dict[str, Any] = {}
        for (capability_id, capability_version), impl in self._bindings.items():
            descriptor = self._registry.get(capability_id, capability_version)
            checked_descriptor = None
            if descriptor is not None:
                checked_descriptor = _checked_direct_binding_descriptor(
                    descriptor,
                    impl,
                    capability_id,
                    capability_version,
                )
            else:
                # Preserve existing behavior for a binding whose Standard
                # descriptor is not registered yet: execute() will return
                # capability_not_found. Runtime registration still needs one
                # stable descriptor snapshot.
                try:
                    runtime_descriptor = impl.describe()
                except Exception as exc:  # noqa: BLE001
                    raise AdapterConfigurationError(
                        f"binding {capability_id!r} v{capability_version!r} cannot be inspected: "
                        "implementation.describe() failed"
                    ) from exc
                if not isinstance(runtime_descriptor, RuntimeCapabilityDescriptor):
                    raise AdapterConfigurationError(
                        f"binding {capability_id!r} v{capability_version!r} returned invalid "
                        f"Runtime CapabilityDescriptor: {type(runtime_descriptor).__name__}"
                    )
                checked_descriptor = copy.deepcopy(runtime_descriptor)

            key = _internal_key(capability_id, capability_version)
            self._key_for[(capability_id, capability_version)] = key
            capabilities[key] = _RuntimeCapabilityBinding(
                impl,
                key,
                checked_descriptor,
            )
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
        self._validator.validate_invocation(invocation)
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

        result_id = _new_id("result")
        binding_fact = self._binding_continuity.get(
            (invocation.capability_id, invocation.capability_version)
        )
        authority_fact = None
        authority_status = "missing"
        if self._continuity_enabled:
            try:
                authority_fact = self._authority_consumer.consume(
                    invocation, binding_fact
                )
            except Exception:
                return self._continuity_fail(
                    invocation,
                    result_id,
                    binding_fact,
                    "authority_identity_mismatch",
                    "Authority consumer failed to return a valid decision fact",
                    authority_status="invalid",
                )
            if authority_fact is None:
                return self._continuity_fail(
                    invocation,
                    result_id,
                    binding_fact,
                    "authority_missing",
                    "Authority consumer returned no decision fact",
                    authority_status="missing",
                )
            if not isinstance(authority_fact, AuthorityDecisionFact):
                return self._continuity_fail(
                    invocation,
                    result_id,
                    binding_fact,
                    "authority_identity_mismatch",
                    "Authority consumer returned an invalid decision fact",
                    authority_status="invalid",
                )
            if not self._authority_matches(invocation, binding_fact, authority_fact):
                return self._continuity_fail(
                    invocation,
                    result_id,
                    binding_fact,
                    "authority_identity_mismatch",
                    "Authority decision does not bind to the current invocation",
                    authority_status="invalid",
                )
            authority_status = "allow" if authority_fact.decision == "ALLOW" else "deny"
            if authority_fact.decision == "DENY":
                return self._continuity_fail(
                    invocation,
                    result_id,
                    binding_fact,
                    "authority_denied",
                    authority_fact.reason_code or "Authority denied invocation",
                    authority_status="deny",
                    authority_fact=authority_fact,
                )

        self._emit("invocation.started", invocation.trace_id, invocation.id)
        self._reasoner.pending_action = Action(key, invocation.input)
        try:
            snapshot = self._runtime.start(Goal(invocation.capability_id))
        except RuntimeExecutionError as exc:
            self._emit("invocation.unresolved", invocation.trace_id, invocation.id)
            execution_id = exc.execution_id
            extensions = (
                self._continuity_extension(
                    result_id=result_id,
                    invocation=invocation,
                    binding_fact=binding_fact,
                    authority_status=authority_status,
                    authority_fact=authority_fact,
                    session_id=exc.session_id,
                    execution_id=execution_id,
                    protected_dispatch_started=True if execution_id else None,
                    certainty="unresolved",
                    blocker=None,
                    artifacts=(),
                    continuity_status="complete" if execution_id else "incomplete",
                )
                if self._continuity_enabled
                else {}
            )
            return Result(
                id=result_id,
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
                extensions=extensions,
            )

        if self._continuity_enabled:
            relevant = [
                step
                for step in snapshot.history
                if isinstance(step.decision, Act)
                and step.decision.action.capability_id == key
            ]
            if len(relevant) != 1:
                return self._continuity_contract_failure(
                    invocation,
                    result_id,
                    binding_fact,
                    authority_status,
                    authority_fact,
                    snapshot.session_id,
                    "expected exactly one Runtime step for the adapter binding",
                )
            step = relevant[0]
            if isinstance(step.policy_verdict, Deny):
                if step.observation is not None or step.execution_id is not None:
                    return self._continuity_contract_failure(
                        invocation,
                        result_id,
                        binding_fact,
                        authority_status,
                        authority_fact,
                        snapshot.session_id,
                        "Runtime policy Deny step has an inconsistent execution record",
                    )
                return self._runtime_policy_denied(
                    invocation,
                    result_id,
                    binding_fact,
                    authority_status,
                    authority_fact,
                    snapshot.session_id,
                    getattr(step.policy_verdict, "reason", "Runtime policy denied"),
                )
            if not isinstance(step.policy_verdict, Allow):
                return self._continuity_contract_failure(
                    invocation,
                    result_id,
                    binding_fact,
                    authority_status,
                    authority_fact,
                    snapshot.session_id,
                    "Runtime step has no Allow or Deny policy verdict",
                )
            if not isinstance(step.execution_id, str) or not step.execution_id:
                return self._continuity_contract_failure(
                    invocation,
                    result_id,
                    binding_fact,
                    authority_status,
                    authority_fact,
                    snapshot.session_id,
                    "settled Runtime step has no execution identity",
                )
            observation = step.observation
        else:
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
            extensions = (
                self._continuity_extension(
                    result_id=result_id,
                    invocation=invocation,
                    binding_fact=binding_fact,
                    authority_status=authority_status,
                    authority_fact=authority_fact,
                    session_id=snapshot.session_id,
                    execution_id=step.execution_id,
                    protected_dispatch_started=True,
                    certainty="settled_success",
                    blocker=None,
                    artifacts=artifacts,
                    continuity_status="complete",
                )
                if self._continuity_enabled
                else {}
            )
            return Result(
                id=result_id,
                invocation_id=invocation.id,
                status="success",
                output=output,
                artifacts=artifacts,
                error=None,
                extensions=extensions,
            )
        if isinstance(observation, Failure):
            self._emit("invocation.failed", invocation.trace_id, invocation.id)
            extensions = (
                self._continuity_extension(
                    result_id=result_id,
                    invocation=invocation,
                    binding_fact=binding_fact,
                    authority_status=authority_status,
                    authority_fact=authority_fact,
                    session_id=snapshot.session_id,
                    execution_id=step.execution_id,
                    protected_dispatch_started=True,
                    certainty="settled_failure",
                    blocker=None,
                    artifacts=(),
                    continuity_status="complete",
                )
                if self._continuity_enabled
                else {}
            )
            return Result(
                id=result_id,
                invocation_id=invocation.id,
                status="failure",
                output=None,
                artifacts=(),
                error={
                    "code": "capability_failed",
                    "message": observation.error or "capability returned a terminal failure",
                },
                extensions=extensions,
            )
        # Unexpected: a Runtime step exists without a terminal observation.
        self._emit("invocation.failed", invocation.trace_id, invocation.id)
        extensions = (
            self._continuity_extension(
                result_id=result_id,
                invocation=invocation,
                binding_fact=binding_fact,
                authority_status=authority_status,
                authority_fact=authority_fact,
                session_id=snapshot.session_id if self._continuity_enabled else None,
                execution_id=None,
                protected_dispatch_started=None,
                certainty="unresolved",
                blocker=None,
                artifacts=(),
                continuity_status="incomplete",
            )
            if self._continuity_enabled
            else {}
        )
        return Result(
            id=result_id,
            invocation_id=invocation.id,
            status="failure",
            output=None,
            artifacts=(),
            error={
                "code": "runtime_contract_violation",
                "message": "settled execution step has no observation",
            },
            extensions=extensions,
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

    @staticmethod
    def _authority_matches(invocation, binding_fact, authority_fact) -> bool:
        return (
            authority_fact.invocation_id == invocation.id
            and authority_fact.capability_id == invocation.capability_id
            and authority_fact.capability_version == invocation.capability_version
            and authority_fact.binding_ref == binding_fact.binding_ref
        )

    def _continuity_extension(
        self,
        *,
        result_id,
        invocation,
        binding_fact,
        authority_status,
        authority_fact,
        session_id,
        execution_id,
        protected_dispatch_started,
        certainty,
        blocker,
        artifacts,
        continuity_status,
    ):
        return {
            "experimental.execution_continuity": build_continuity_extension(
                continuity_status=continuity_status,
                binding=binding_fact,
                authority_status=authority_status,
                authority_fact=authority_fact,
                session_id=session_id,
                execution_id=execution_id,
                protected_dispatch_started=protected_dispatch_started,
                certainty=certainty,
                blocker=blocker,
                invocation_id=invocation.id,
                result_id=result_id,
                trace_id=invocation.trace_id,
                artifact_ids=[artifact.id for artifact in artifacts],
            )
        }

    def _continuity_fail(
        self,
        invocation,
        result_id,
        binding_fact,
        code,
        message,
        *,
        authority_status,
        authority_fact=None,
    ):
        self._emit("invocation.failed", invocation.trace_id, invocation.id)
        return Result(
            id=result_id,
            invocation_id=invocation.id,
            status="failure",
            output=None,
            artifacts=(),
            error={"code": code, "message": message},
            extensions=self._continuity_extension(
                result_id=result_id,
                invocation=invocation,
                binding_fact=binding_fact,
                authority_status=authority_status,
                authority_fact=authority_fact,
                session_id=None,
                execution_id=None,
                protected_dispatch_started=False,
                certainty="not_dispatched",
                blocker="authority",
                artifacts=(),
                continuity_status="incomplete",
            ),
        )

    def _runtime_policy_denied(
        self,
        invocation,
        result_id,
        binding_fact,
        authority_status,
        authority_fact,
        session_id,
        message,
    ):
        self._emit("invocation.failed", invocation.trace_id, invocation.id)
        return Result(
            id=result_id,
            invocation_id=invocation.id,
            status="failure",
            output=None,
            artifacts=(),
            error={"code": "runtime_policy_denied", "message": message},
            extensions=self._continuity_extension(
                result_id=result_id,
                invocation=invocation,
                binding_fact=binding_fact,
                authority_status=authority_status,
                authority_fact=authority_fact,
                session_id=session_id,
                execution_id=None,
                protected_dispatch_started=False,
                certainty="not_dispatched",
                blocker="runtime_policy",
                artifacts=(),
                continuity_status="incomplete",
            ),
        )

    def _continuity_contract_failure(
        self,
        invocation,
        result_id,
        binding_fact,
        authority_status,
        authority_fact,
        session_id,
        message,
    ):
        self._emit("invocation.failed", invocation.trace_id, invocation.id)
        return Result(
            id=result_id,
            invocation_id=invocation.id,
            status="failure",
            output=None,
            artifacts=(),
            error={"code": "runtime_contract_violation", "message": message},
            extensions=self._continuity_extension(
                result_id=result_id,
                invocation=invocation,
                binding_fact=binding_fact,
                authority_status=authority_status,
                authority_fact=authority_fact,
                session_id=session_id,
                execution_id=None,
                protected_dispatch_started=None,
                certainty="unresolved",
                blocker=None,
                artifacts=(),
                continuity_status="incomplete",
            ),
        )


__all__ = [
    "AdapterConfigurationError",
    "DirectedReasoner",
    "RuntimeAdapter",
]
