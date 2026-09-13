"""Focused Product HOW-B candidate tests.

These tests cover the bounded Runtime owner-fact seam and the candidate-local
outward carrier. They deliberately do not execute Test-Lab P1-P11 or any
provider/model path.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_runtime.contracts.values as contract_values

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    Blocked,
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Failure,
    Goal,
    PendingExecution,
    SessionSnapshot,
    StepRecord,
    Success,
)
from agent_runtime.errors import RuntimeExecutionError
from agent_runtime.runtime import Runtime
from examples.fakes import AllowAllPolicy, FakeCapability, FakeReasoner, InMemoryStateStore
from examples.platform_standard_reference import (
    ComposeReportCapability,
    compose_report_descriptor,
    make_report_invocation,
    make_stack,
    reference_runtime_factory,
)
from platform_standard.models import CapabilityDescriptor, Invocation, Result
from platform_standard.registry import InMemoryDescriptorRegistry
import platform_standard.runtime_adapter as runtime_adapter_module
from platform_standard.runtime_adapter import RuntimeAdapter
from platform_standard.validation import PlatformValidator


RuntimeOutcomeFact = getattr(contract_values, "RuntimeOutcomeFact", None)
_continuity_extension = getattr(runtime_adapter_module, "_continuity_extension", None)


def _fact(
    *,
    session_id: str,
    execution_id: str | None,
    execution_started: bool,
    certainty: str,
    identity_status: str,
):
    assert RuntimeOutcomeFact is not None, "RuntimeOutcomeFact is not implemented"
    return RuntimeOutcomeFact(
        session_id=session_id,
        execution_id=execution_id,
        execution_started=execution_started,
        certainty=certainty,
        identity_status=identity_status,
    )


def _read_fact(runtime: Runtime, session_id: str):
    method = getattr(runtime, "read_outcome_fact", None)
    assert callable(method), "Runtime.read_outcome_fact is not implemented"
    return method(session_id)


def _project(fact, *, expected_session_id: str | None = None, settled_execution_id: str | None = None):
    assert callable(_continuity_extension), "candidate continuity projection is not implemented"
    return _continuity_extension(
        fact,
        expected_session_id=expected_session_id,
        settled_execution_id=settled_execution_id,
    )


def _runtime_with_store():
    store = InMemoryStateStore()
    runtime = Runtime(
        FakeReasoner(),
        {"add": FakeCapability()},
        AllowAllPolicy(),
        store,
    )
    return runtime, store


def _commit(runtime_store, snapshot):
    runtime_store.commit(snapshot)
    return snapshot.session_id


def _a1_snapshot(session_id: str) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=session_id,
        goal=Goal("a1"),
        state={},
        history=(
            StepRecord(
                index=0,
                decision=Blocked("validation blocked before protected execution"),
            ),
        ),
    )


def _settled_snapshot(session_id: str, execution_id: str, observation) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=session_id,
        goal=Goal("settled"),
        state={},
        history=(
            StepRecord(
                index=0,
                decision=Act(Action("add", {"a": 20, "b": 22})),
                policy_verdict=Allow(),
                observation=observation,
                execution_id=execution_id,
            ),
        ),
    )


def _pending_snapshot(session_id: str, execution_id: str) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=session_id,
        goal=Goal("pending"),
        state={},
        pending_execution=PendingExecution(
            execution_id=execution_id,
            step_index=0,
            action=Action("add", {"a": 20, "b": 22}),
        ),
    )


class FailureCapability:
    def describe(self) -> RuntimeCapabilityDescriptor:
        return RuntimeCapabilityDescriptor(
            id="known_failure",
            name="Known Failure",
            description="Returns an authoritative capability failure.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        return Failure("known capability failure")


def _failure_adapter() -> RuntimeAdapter:
    registry = InMemoryDescriptorRegistry()
    registry.register(
        CapabilityDescriptor(
            id="known_failure",
            name="Known Failure",
            description="Returns an authoritative capability failure.",
            capability_version="1.0.0",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            execution={"side_effect": "none"},
        )
    )
    return RuntimeAdapter(
        registry,
        bindings={("known_failure", "1.0.0"): FailureCapability()},
        runtime_factory=reference_runtime_factory,
    )


def _failure_invocation() -> Invocation:
    return Invocation(
        id="inv_failure",
        capability_id="known_failure",
        capability_version="1.0.0",
        input={},
        context={"extensions": {}},
        trace_id="trace_failure",
    )


def test_runtime_outcome_fact_is_immutable_and_has_only_frozen_fields():
    assert RuntimeOutcomeFact is not None, "RuntimeOutcomeFact is not implemented"
    fact = _fact(
        session_id="s",
        execution_id=None,
        execution_started=False,
        certainty="NOT_STARTED",
        identity_status="ABSENT",
    )
    assert fact.__dataclass_params__.frozen is True
    assert set(fact.__dataclass_fields__) == {
        "session_id",
        "execution_id",
        "execution_started",
        "certainty",
        "identity_status",
    }


def test_a0_pre_runtime_rejection_has_no_runtime_fact_or_carrier():
    _, adapter = make_stack()
    invocation = Invocation(
        id="inv_missing",
        capability_id="missing",
        capability_version="1.0.0",
        input={},
        context={"extensions": {}},
        trace_id="trace_missing",
    )

    result = adapter.execute(invocation)

    assert result.status == "failure"
    assert result.error["code"] == "capability_not_found"
    assert result.extensions == {}


def test_a1_runtime_owned_not_started_has_exact_absent_carrier():
    runtime, store = _runtime_with_store()
    session_id = _commit(store, _a1_snapshot("s_a1"))

    fact = _read_fact(runtime, session_id)

    assert fact == _fact(
        session_id="s_a1",
        execution_id=None,
        execution_started=False,
        certainty="NOT_STARTED",
        identity_status="ABSENT",
    )
    extension = _project(fact, expected_session_id=session_id)
    assert extension["interop.execution_continuity"]["payload"] == {
        "execution_id": None,
        "execution_started": False,
        "certainty": "NOT_STARTED",
        "identity_status": "ABSENT",
    }


def test_b_settled_success_uses_exact_owner_id_and_preserves_base_result():
    _, adapter = make_stack()

    result = adapter.execute(
        make_report_invocation(
            {"title": "HOW-B", "sections": ["success"]},
            invocation_id="inv_success",
            trace_id="trace_success",
        )
    )

    assert result.status == "success"
    assert result.output["report_text"].startswith("# HOW-B")
    payload = result.extensions["interop.execution_continuity"]["payload"]
    assert payload["execution_started"] is True
    assert payload["certainty"] == "CONFIRMED_EXECUTED"
    assert payload["identity_status"] == "AUTHORITATIVE"
    assert isinstance(payload["execution_id"], str) and payload["execution_id"]
    PlatformValidator().validate_result(result)


def test_c_settled_capability_failure_uses_exact_owner_id_and_base_failure_semantics():
    adapter = _failure_adapter()

    result = adapter.execute(_failure_invocation())

    assert result.status == "failure"
    assert result.error["code"] == "capability_failed"
    payload = result.extensions["interop.execution_continuity"]["payload"]
    assert payload["execution_started"] is True
    assert payload["certainty"] == "CONFIRMED_EXECUTED"
    assert payload["identity_status"] == "AUTHORITATIVE"
    assert isinstance(payload["execution_id"], str) and payload["execution_id"]
    PlatformValidator().validate_result(result)


def test_d_unresolved_uses_exact_pending_owner_id_without_safe_retry_claim():
    class UnresolvedRuntime:
        def start(self, goal):
            raise RuntimeExecutionError("s_d")

        def read_outcome_fact(self, session_id):
            return _fact(
                session_id=session_id,
                execution_id="exec_d",
                execution_started=True,
                certainty="UNRESOLVED",
                identity_status="AUTHORITATIVE",
            )

    registry = InMemoryDescriptorRegistry()
    registry.register(compose_report_descriptor())
    adapter = RuntimeAdapter(
        registry,
        bindings={("compose_report", "1.0.0"): ComposeReportCapability()},
        runtime_factory=lambda capabilities, reasoner: UnresolvedRuntime(),
    )

    result = adapter.execute(make_report_invocation({"title": "D"}, invocation_id="inv_d"))

    assert result.status == "unresolved"
    assert "safe_to_retry" not in result.to_dict()
    payload = result.extensions["interop.execution_continuity"]["payload"]
    assert payload == {
        "execution_id": "exec_d",
        "execution_started": True,
        "certainty": "UNRESOLVED",
        "identity_status": "AUTHORITATIVE",
    }


def test_e_unrecoverable_fact_emits_no_carrier():
    fact = _fact(
        session_id="s_e",
        execution_id=None,
        execution_started=True,
        certainty="UNRESOLVED",
        identity_status="UNRECOVERABLE",
    )

    assert _project(fact, expected_session_id="s_e") == {}


def test_f_conflicting_ids_emit_no_carrier_and_select_no_identity():
    fact = _fact(
        session_id="s_f",
        execution_id=None,
        execution_started=True,
        certainty="UNRESOLVED",
        identity_status="CONFLICTING",
    )

    assert _project(fact, expected_session_id="s_f") == {}


def test_wrong_or_synthetic_settled_id_is_rejected_against_returned_snapshot_identity():
    fact = _fact(
        session_id="s_wrong",
        execution_id="synthetic-id",
        execution_started=True,
        certainty="CONFIRMED_EXECUTED",
        identity_status="AUTHORITATIVE",
    )

    assert (
        _project(
            fact,
            expected_session_id="s_wrong",
            settled_execution_id="owner-id",
        )
        == {}
    )


def test_session_id_is_never_used_as_execution_id():
    fact = _fact(
        session_id="session-only",
        execution_id=None,
        execution_started=False,
        certainty="NOT_STARTED",
        identity_status="ABSENT",
    )

    payload = _project(fact, expected_session_id="session-only")[
        "interop.execution_continuity"
    ]["payload"]
    assert payload["execution_id"] is None
    assert "session_id" not in payload


def test_read_outcome_fact_is_read_only_for_a1_b_and_d():
    runtime, store = _runtime_with_store()
    snapshots = (
        _a1_snapshot("s_read_a1"),
        _settled_snapshot("s_read_b", "exec_b", Success(42)),
        _pending_snapshot("s_read_d", "exec_d"),
    )
    for snapshot in snapshots:
        _commit(store, snapshot)
        before = store.load(snapshot.session_id)
        _read_fact(runtime, snapshot.session_id)
        after = store.load(snapshot.session_id)
        assert after == before


def test_runtime_owner_facts_cover_settled_success_failure_and_unresolved():
    runtime, store = _runtime_with_store()
    _commit(store, _settled_snapshot("s_b", "exec_b", Success(42)))
    _commit(store, _settled_snapshot("s_c", "exec_c", Failure("known")))
    _commit(store, _pending_snapshot("s_d", "exec_d"))

    assert _read_fact(runtime, "s_b").execution_id == "exec_b"
    assert _read_fact(runtime, "s_b").certainty == "CONFIRMED_EXECUTED"
    assert _read_fact(runtime, "s_c").execution_id == "exec_c"
    assert _read_fact(runtime, "s_c").certainty == "CONFIRMED_EXECUTED"
    assert _read_fact(runtime, "s_d").execution_id == "exec_d"
    assert _read_fact(runtime, "s_d").certainty == "UNRESOLVED"


def test_no_authoritative_fact_means_no_continuity_extension():
    assert _project(None, expected_session_id="s_none") == {}


def test_invalid_outward_combinations_are_not_emitted():
    invalid_facts = (
        _fact(
            session_id="s_invalid_1",
            execution_id="exec",
            execution_started=False,
            certainty="NOT_STARTED",
            identity_status="ABSENT",
        ),
        _fact(
            session_id="s_invalid_2",
            execution_id=None,
            execution_started=True,
            certainty="UNRESOLVED",
            identity_status="AUTHORITATIVE",
        ),
        _fact(
            session_id="s_invalid_3",
            execution_id="exec",
            execution_started=True,
            certainty="CONFIRMED_EXECUTED",
            identity_status="ABSENT",
        ),
    )

    for fact in invalid_facts:
        assert _project(fact, expected_session_id=fact.session_id) == {}


def test_optional_carrier_remains_compatible_with_existing_result_validation():
    result = Result(
        id="r_optional",
        invocation_id="inv_optional",
        status="success",
        output={"ok": True},
        artifacts=(),
        error=None,
        extensions={
            "interop.execution_continuity": {
                "version": "1",
                "required": False,
                "payload": {
                    "execution_id": "exec_optional",
                    "execution_started": True,
                    "certainty": "CONFIRMED_EXECUTED",
                    "identity_status": "AUTHORITATIVE",
                },
            }
        },
    )

    PlatformValidator().validate_result(result)
    assert result.to_dict()["extensions"]["interop.execution_continuity"]["required"] is False
