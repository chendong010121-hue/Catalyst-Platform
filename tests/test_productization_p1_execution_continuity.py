"""Standalone P1 execution-continuity proof matrix.

This module deliberately uses only local fakes and the existing Runtime.  It
is also runnable without pytest so the proof can be executed as a Product
regression artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runtime.contracts import (
    Action,
    Allow,
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Continue,
    Deny,
    Failure,
    Success,
)
from examples.fakes import InMemoryStateStore
from platform_standard.models import ArtifactRef, CapabilityDescriptor, Invocation, Producer
from platform_standard.registry import InMemoryDescriptorRegistry
from platform_standard.runtime_adapter import AdapterConfigurationError, RuntimeAdapter
from platform_standard.runtime_continuity import (
    AuthorityDecisionFact,
    BindingContinuityFact,
    validate_continuity_extension,
)


CAPABILITY_ID = "continuity_probe"
VERSION = "1.0.0"
BINDING_REF = "binding://continuity-probe/v1"
IMPLEMENTATION_REF = "impl://continuity-probe/v1"


class ProbeCapability:
    def __init__(self, outcome=Success({"ok": True}), *, raise_after_side_effect=False):
        self.outcome = outcome
        self.raise_after_side_effect = raise_after_side_effect
        self.call_count = 0
        self.side_effect_marker = 0
        self.parameters = None

    def describe(self):
        return RuntimeCapabilityDescriptor(
            id=CAPABILITY_ID,
            name="Continuity Probe",
            description="P1 proof capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        self.call_count += 1
        self.parameters = parameters
        if self.raise_after_side_effect:
            self.side_effect_marker += 1
            raise RuntimeError("simulated ambiguous dispatch")
        return self.outcome


class AllowPolicy:
    def check_action(self, action, state):
        return Allow()

    def should_stop(self, state, history):
        return Continue()


class DenyPolicy(AllowPolicy):
    def check_action(self, action, state):
        return Deny("runtime policy denied")


class CountingRuntime:
    def __init__(self, reasoner, capabilities, policy, store):
        from agent_runtime.runtime import Runtime

        self.runtime = Runtime(reasoner, capabilities, policy, store)
        self.start_count = 0
        self.store = store

    def start(self, goal):
        self.start_count += 1
        return self.runtime.start(goal)


@dataclass
class Authority:
    response: AuthorityDecisionFact | None
    calls: int = 0

    def consume(self, invocation, binding_fact):
        self.calls += 1
        return self.response


def _descriptor():
    return CapabilityDescriptor(
        id=CAPABILITY_ID,
        name="Continuity Probe",
        description="P1 proof capability",
        capability_version=VERSION,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        execution={"side_effect": "bounded"},
    )


def _invocation(value=None, *, invocation_id="inv-1", trace_id="trace-1"):
    return Invocation(
        id=invocation_id,
        capability_id=CAPABILITY_ID,
        capability_version=VERSION,
        input={"value": value or "parity"},
        context={"extensions": {}},
        trace_id=trace_id,
    )


def _binding_fact():
    return BindingContinuityFact(
        capability_id=CAPABILITY_ID,
        capability_version=VERSION,
        binding_ref=BINDING_REF,
        implementation_ref=IMPLEMENTATION_REF,
        admission_ref="admission://p1" ,
    )


def _authority(invocation, *, decision="ALLOW", reason_code=None, **overrides):
    values = {
        "authority_decision_id": "auth-1",
        "decision": decision,
        "invocation_id": invocation.id,
        "capability_id": invocation.capability_id,
        "capability_version": invocation.capability_version,
        "binding_ref": BINDING_REF,
        "subject_ref": "subject://test",
        "authority_source_ref": "authority://test",
        "resource_ref": "resource://test",
        "scope_ref": "scope://test",
        "reason_code": reason_code,
    }
    values.update(overrides)
    return AuthorityDecisionFact(**values)


def _make_adapter(capability, authority, *, policy=None, binding_facts=None, artifact_mapper=None):
    registry = InMemoryDescriptorRegistry()
    registry.register(_descriptor())
    holder = {}

    def factory(capabilities, reasoner):
        holder["runtime"] = CountingRuntime(
            reasoner, capabilities, policy or AllowPolicy(), InMemoryStateStore()
        )
        return holder["runtime"]

    adapter = RuntimeAdapter(
        registry,
        {(CAPABILITY_ID, VERSION): capability},
        runtime_factory=factory,
        binding_continuity=binding_facts or {(CAPABILITY_ID, VERSION): _binding_fact()},
        authority_consumer=authority,
        artifact_mappers=(
            {(CAPABILITY_ID, VERSION): artifact_mapper} if artifact_mapper else None
        ),
    )
    return adapter, holder


def _receipt(result):
    extension = result.extensions["experimental.execution_continuity"]
    return extension["payload"]


def _assert_receipt(result, invocation):
    extension = result.extensions["experimental.execution_continuity"]
    validate_continuity_extension(extension)
    payload = extension["payload"]
    assert payload["evidence"]["invocation_id"] == invocation.id
    assert payload["evidence"]["result_id"] == result.id
    assert payload["evidence"]["trace_id"] == invocation.trace_id
    return payload


def test_p1_0a_partial_configuration():
    registry = InMemoryDescriptorRegistry()
    capability = ProbeCapability()
    for kwargs in (
        {"binding_continuity": {(CAPABILITY_ID, VERSION): _binding_fact()}},
        {"authority_consumer": Authority(None)},
    ):
        try:
            RuntimeAdapter(
                registry,
                {(CAPABILITY_ID, VERSION): capability},
                runtime_factory=lambda capabilities, reasoner: None,
                **kwargs,
            )
        except AdapterConfigurationError:
            pass
        else:
            raise AssertionError("partial P1 configuration must fail closed")


def test_p1_0b_metadata_mismatch():
    invocation = _invocation()
    try:
        _make_adapter(
            ProbeCapability(),
            Authority(_authority(invocation)),
            binding_facts={("wrong", VERSION): _binding_fact()},
        )
    except AdapterConfigurationError:
        return
    raise AssertionError("binding metadata mismatch must fail at composition")


def test_p1_a_success_and_parity():
    invocation = _invocation()
    capability = ProbeCapability()
    def mapper(output, current_invocation):
        return (
            ArtifactRef(
                id="artifact-proof-1",
                artifact_type="proof",
                artifact_version="1",
                uri="memory://proof-1",
                producer=Producer(
                    capability_id=current_invocation.capability_id,
                    invocation_id=current_invocation.id,
                ),
            ),
        )

    adapter, holder = _make_adapter(
        capability, Authority(_authority(invocation)), artifact_mapper=mapper
    )
    result = adapter.execute(invocation)
    assert result.status == "success"
    assert capability.call_count == 1
    assert capability.parameters == invocation.input
    payload = _assert_receipt(result, invocation)
    assert payload["continuity_status"] == "complete"
    assert payload["execution"]["certainty"] == "settled_success"
    assert payload["execution"]["protected_dispatch_started"] is True
    assert payload["execution"]["execution_id"]
    assert payload["evidence"]["artifact_ids"] == ["artifact-proof-1"]
    assert [artifact.id for artifact in result.artifacts] == ["artifact-proof-1"]
    assert holder["runtime"].start_count == 1


def test_p1_b1_missing_authority():
    invocation = _invocation()
    capability = ProbeCapability()
    adapter, holder = _make_adapter(capability, Authority(None))
    result = adapter.execute(invocation)
    assert result.error["code"] == "authority_missing"
    assert capability.call_count == 0
    assert holder["runtime"].start_count == 0
    payload = _assert_receipt(result, invocation)
    assert payload["execution"]["certainty"] == "not_dispatched"
    assert payload["execution"]["blocker"] == "authority"


def test_p1_b2_to_b5_authority_denials():
    for reason in ("subject_mismatch", "resource_mismatch", "scope_exceeded", "explicit_deny"):
        invocation = _invocation(reason, invocation_id=f"inv-{reason}")
        capability = ProbeCapability()
        adapter, holder = _make_adapter(
            capability, Authority(_authority(invocation, decision="DENY", reason_code=reason))
        )
        result = adapter.execute(invocation)
        assert result.error["code"] == "authority_denied"
        assert capability.call_count == 0
        assert holder["runtime"].start_count == 0
        payload = _assert_receipt(result, invocation)
        assert payload["authority"]["status"] == "deny"
        assert payload["authority"]["reason_code"] == reason


def test_p1_b6_authority_identity_mismatch():
    invocation = _invocation()
    capability = ProbeCapability()
    adapter, holder = _make_adapter(
        capability, Authority(_authority(invocation, invocation_id="wrong-invocation"))
    )
    result = adapter.execute(invocation)
    assert result.error["code"] == "authority_identity_mismatch"
    assert capability.call_count == 0
    assert holder["runtime"].start_count == 0
    payload = _assert_receipt(result, invocation)
    assert payload["authority"]["status"] == "invalid"


def test_p1_c_known_failure():
    invocation = _invocation()
    capability = ProbeCapability(Failure("known failure"))
    adapter, _ = _make_adapter(capability, Authority(_authority(invocation)))
    result = adapter.execute(invocation)
    assert result.status == "failure"
    assert result.error["code"] == "capability_failed"
    payload = _assert_receipt(result, invocation)
    assert payload["continuity_status"] == "complete"
    assert payload["execution"]["certainty"] == "settled_failure"
    assert payload["execution"]["execution_id"]


def test_p1_d_unresolved_preserves_pending_identity():
    invocation = _invocation()
    capability = ProbeCapability(raise_after_side_effect=True)
    adapter, holder = _make_adapter(capability, Authority(_authority(invocation)))
    result = adapter.execute(invocation)
    assert result.status == "unresolved"
    assert result.error["code"] == "runtime_outcome_uncertain"
    assert capability.call_count == 1
    assert capability.side_effect_marker == 1
    payload = _assert_receipt(result, invocation)
    pending = holder["runtime"].store.load(payload["execution"]["session_id"]).pending_execution
    assert pending is not None
    assert payload["continuity_status"] == "complete"
    assert payload["execution"]["execution_id"] == pending.execution_id
    assert payload["execution"]["protected_dispatch_started"] is True
    assert payload["execution"]["certainty"] == "unresolved"
    assert "safe_to_retry" not in result.error
    assert "did_not_execute" not in result.error


def test_p1_e_runtime_policy_deny():
    invocation = _invocation()
    capability = ProbeCapability()
    adapter, holder = _make_adapter(
        capability, Authority(_authority(invocation)), policy=DenyPolicy()
    )
    result = adapter.execute(invocation)
    assert result.error["code"] == "runtime_policy_denied"
    assert capability.call_count == 0
    payload = _assert_receipt(result, invocation)
    assert payload["authority"]["status"] == "allow"
    assert payload["execution"]["session_id"]
    assert payload["execution"]["execution_id"] is None
    assert payload["execution"]["protected_dispatch_started"] is False
    assert payload["execution"]["certainty"] == "not_dispatched"
    assert payload["execution"]["blocker"] == "runtime_policy"
    assert holder["runtime"].start_count == 1


def test_p1_f_legacy_compatibility():
    from examples.platform_standard_reference import make_report_invocation, make_stack

    _, adapter = make_stack()
    result = adapter.execute(make_report_invocation({"title": "legacy"}))
    assert result.status == "success"
    assert "experimental.execution_continuity" not in result.extensions


def test_p1_g_independent_consumer_and_h_malformed_receipts():
    invocation = _invocation()
    capability = ProbeCapability()
    adapter, _ = _make_adapter(capability, Authority(_authority(invocation)))
    result = adapter.execute(invocation)
    extension = result.extensions["experimental.execution_continuity"]
    validate_continuity_extension(extension)
    payload = extension["payload"]
    recovered = (
        payload["binding"]["capability_id"],
        payload["binding"]["capability_version"],
        payload["binding"]["binding_ref"],
        payload["binding"]["implementation_ref"],
        payload["authority"]["authority_decision_id"],
        payload["execution"]["protected_dispatch_started"],
    )
    assert recovered == (
        CAPABILITY_ID,
        VERSION,
        BINDING_REF,
        IMPLEMENTATION_REF,
        "auth-1",
        True,
    )
    malformed = {
        "version": "1",
        "required": False,
        "payload": {
            "continuity_status": "complete",
            "authority": {"status": "allow", "authority_decision_id": None},
            "execution": {
                "session_id": None,
                "execution_id": None,
                "protected_dispatch_started": False,
                "certainty": "settled_success",
                "blocker": None,
            },
            "evidence": {
                "invocation_id": invocation.id,
                "result_id": "result-1",
                "trace_id": invocation.trace_id,
                "artifact_ids": [],
            },
        },
    }
    try:
        validate_continuity_extension(malformed)
    except ValueError:
        return
    raise AssertionError("malformed continuity receipt must fail closed")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"P1 standalone proof: {len(tests)} tests passed")
