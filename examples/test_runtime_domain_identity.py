"""RuntimeDomain Identity Closure 测试。

覆盖（依据 RUNTIME_DOMAIN_IDENTITY_CLOSURE_EXECUTION_SPEC）：
- DI-1..DI-8 domain identity / timeout-disabled bypass / cross-runtime / wrong-identity fail-closed
- AU-1..AU-8 Internal Auditor 自创的 identity mismatch / alternate composition / asymmetry / recovery
"""

from __future__ import annotations

import threading
import time

from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    ConfirmedExecuted,
    ConfirmedNotExecuted,
    Failure,
    Goal,
    ReasoningResult,
    Success,
)
from agent_runtime.errors import (
    CapabilityTimeoutUncertainError,
    ExecutionStillLiveError,
    ReconciliationError,
    RuntimeConfigurationError,
    UnresolvedExecutionError,
)
from agent_runtime.execution import (
    ExecutionControlPlane,
    ExecutionTimeoutConfig,
    RuntimeDomain,
)
from agent_runtime.runtime import Runtime

from .fakes import AllowAllPolicy, InMemoryStateStore


class ActThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class BlockBeforeSideEffectCapability:
    """block 在 side effect 前，忽略 cancellation。"""

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.effects = 0
        self.calls = 0

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="block before side effect")

    def invoke(self, parameters, context):
        self.calls += 1
        self.started.set()
        self.release.wait()
        self.effects += 1
        return Success(self.effects)


class BlockThenReturnCapability:
    def __init__(self, result):
        self.started = threading.Event()
        self.release = threading.Event()
        self._result = result

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="block then return")

    def invoke(self, parameters, context):
        self.started.set()
        self.release.wait()
        return self._result


def _timeout_config():
    return ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1)


def _start_live(domain, cap):
    """domain 内启动一个 timeout-uncertain live worker，返回 (rtA, sid, exec_id)。"""
    rtA = Runtime(
        ActThenCompleteReasoner(),
        {"add": cap},
        AllowAllPolicy(),
        domain,
        timeout_config=_timeout_config(),
    )
    snap = rtA.create(Goal("x"))
    sid = snap.session_id
    try:
        rtA.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")
    return rtA, sid, exec_id


def _wait_quiesce(domain, sid):
    deadline = time.time() + 5
    while domain.execution_control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert domain.execution_control_plane.active.get(sid) is None


# ---------------------------------------------------------------------------
# DI-1..DI-4：共享 domain 的正常组合 / live guard / evidence / cancel
# ---------------------------------------------------------------------------

def test_di1_shared_domain_same_store_same_control_plane():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    rtA = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), domain)
    rtB = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), domain)
    assert rtA._state_store is rtB._state_store is store
    assert rtA._control_plane is rtB._control_plane is domain.execution_control_plane


def test_di2_timeout_disabled_runtime_cannot_bypass_live_guard():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockBeforeSideEffectCapability()
    rtA, sid, exec_id = _start_live(domain, cap)
    assert cap.started.is_set()
    assert cap.effects == 0

    # B timeout disabled，同一 domain
    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    try:
        rtB.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("timeout-disabled B must see A's live worker")

    cap.release.set()
    _wait_quiesce(domain, sid)


def test_di3_timeout_disabled_runtime_sees_late_evidence():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockThenReturnCapability(Success(42))
    rtA, sid, exec_id = _start_live(domain, cap)
    cap.release.set()
    _wait_quiesce(domain, sid)

    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    try:
        rtB.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("timeout-disabled B must see late authoritative evidence")


def test_di4_cross_runtime_cancel_same_execution():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockBeforeSideEffectCapability()
    rtA, sid, exec_id = _start_live(domain, cap)

    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    res = rtB.cancel(sid)
    assert res.requested is True
    assert res.execution_id == exec_id

    cap.release.set()
    _wait_quiesce(domain, sid)


# ---------------------------------------------------------------------------
# DI-5..DI-7：独立 store/cp 组合在 Runtime API 上不可能
# ---------------------------------------------------------------------------

def test_di5_independent_store_control_plane_pair_impossible():
    store = InMemoryStateStore()
    cp = ExecutionControlPlane()
    # 旧 API：Runtime(state_store=..., control_plane=...) 不再存在 → TypeError
    try:
        Runtime(
            ActThenCompleteReasoner(),
            {"add": BlockThenReturnCapability(Success(1))},
            AllowAllPolicy(),
            state_store=store,
            control_plane=cp,
        )
    except TypeError:
        return
    raise AssertionError("Runtime must not accept independent state_store + control_plane")


def test_di6_no_alternate_constructor_bypass():
    store = InMemoryStateStore()
    try:
        Runtime(
            ActThenCompleteReasoner(),
            {"add": BlockThenReturnCapability(Success(1))},
            AllowAllPolicy(),
            state_store=store,
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Runtime must require a RuntimeDomain (no independent store)")


def test_di7_runtime_store_and_cp_are_exactly_domain():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    rt = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), domain)
    assert rt._state_store is store
    assert rt._control_plane is domain.execution_control_plane


# ---------------------------------------------------------------------------
# DI-8：live worker 无法经任何 alternate Runtime 构造 reconcile/resume 到第二次执行
# ---------------------------------------------------------------------------

def test_di8_no_second_execution_via_identity_mismatch():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockBeforeSideEffectCapability()
    rtA, sid, exec_id = _start_live(domain, cap)

    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    try:
        rtB.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("expected ExecutionStillLiveError")
    try:
        rtB.resume(sid)
    except UnresolvedExecutionError:
        pass
    else:
        raise AssertionError("expected UnresolvedExecutionError")

    assert cap.calls == 1  # 未启动第二次 execution
    assert cap.effects == 0
    cap.release.set()
    _wait_quiesce(domain, sid)


# ---------------------------------------------------------------------------
# AU：Internal Auditor 自创 adversarial cases
# ---------------------------------------------------------------------------

def test_au1_second_domain_over_same_store_rejected():
    from agent_runtime.errors import RuntimeDomainConflictError
    store = InMemoryStateStore()
    d1 = RuntimeDomain(state_store=store)
    try:
        RuntimeDomain(state_store=store)
    except RuntimeDomainConflictError:
        return
    raise AssertionError("second independent RuntimeDomain over same store must fail closed")


def test_au2_lower_level_executor_timeout_requires_control_plane():
    try:
        DefaultCapabilityExecutor(
            {"add": BlockThenReturnCapability(Success(1))},
            timeout_config=_timeout_config(),
        )
    except RuntimeConfigurationError:
        return
    raise AssertionError("lower-level timeout executor requires control plane")


def test_au3_timeout_disabled_runtime_can_cancel():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockBeforeSideEffectCapability()
    rtA, sid, exec_id = _start_live(domain, cap)
    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    res = rtB.cancel(sid)
    assert res.requested is True
    assert res.execution_id == exec_id
    cap.release.set()
    _wait_quiesce(domain, sid)


def test_au4_reconcile_after_cleanup_is_no_pending_not_stale():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockThenReturnCapability(Success(42))
    rt, sid, exec_id = _start_live(domain, cap)
    cap.release.set()
    _wait_quiesce(domain, sid)
    rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))
    # 第二次 reconcile：evidence 已清理，pending 已 settle → "no pending"，不是 stale evidence
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError as exc:
        assert "no pending" in str(exc)
        return
    raise AssertionError("expected ReconciliationError for no pending")


def test_au5_control_plane_identity_is_object_identity():
    cp1 = ExecutionControlPlane()
    cp2 = ExecutionControlPlane()
    assert cp1 is not cp2  # 值等价的两个 cp 也不是同一 safety domain


def test_au6_lower_level_executor_with_explicit_control_plane_ok():
    cp = ExecutionControlPlane()
    executor = DefaultCapabilityExecutor(
        {"add": BlockThenReturnCapability(Success(1))},
        timeout_config=_timeout_config(),
        control_plane=cp,
    )
    assert executor is not None


def test_au7_runtime_from_domain_sees_domain_evidence():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockThenReturnCapability(Success(42))
    rtA, sid, exec_id = _start_live(domain, cap)
    cap.release.set()
    _wait_quiesce(domain, sid)

    evidence = domain.execution_control_plane.evidence.get_authoritative_observation(sid, exec_id)
    assert isinstance(evidence, Success)
    assert evidence.data == 42


def test_au8_domain_binds_single_store_object():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    assert domain.state_store is store
    rt = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), domain)
    assert rt._state_store is domain.state_store


def main() -> None:
    tests = [
        ("DI-1 shared domain same store same cp", test_di1_shared_domain_same_store_same_control_plane),
        ("DI-2 timeout-disabled cannot bypass live guard", test_di2_timeout_disabled_runtime_cannot_bypass_live_guard),
        ("DI-3 timeout-disabled sees late evidence", test_di3_timeout_disabled_runtime_sees_late_evidence),
        ("DI-4 cross-runtime cancel", test_di4_cross_runtime_cancel_same_execution),
        ("DI-5 independent store+cp impossible", test_di5_independent_store_control_plane_pair_impossible),
        ("DI-6 no alternate constructor bypass", test_di6_no_alternate_constructor_bypass),
        ("DI-7 runtime store/cp exactly domain", test_di7_runtime_store_and_cp_are_exactly_domain),
        ("DI-8 no second execution via mismatch", test_di8_no_second_execution_via_identity_mismatch),
        ("AU-1 second domain over same store rejected", test_au1_second_domain_over_same_store_rejected),
        ("AU-2 lower-level executor guard", test_au2_lower_level_executor_timeout_requires_control_plane),
        ("AU-3 timeout-disabled can cancel", test_au3_timeout_disabled_runtime_can_cancel),
        ("AU-4 reconcile after cleanup no pending", test_au4_reconcile_after_cleanup_is_no_pending_not_stale),
        ("AU-5 cp identity is object identity", test_au5_control_plane_identity_is_object_identity),
        ("AU-6 lower-level explicit cp ok", test_au6_lower_level_executor_with_explicit_control_plane_ok),
        ("AU-7 runtime sees domain evidence", test_au7_runtime_from_domain_sees_domain_evidence),
        ("AU-8 domain binds single store", test_au8_domain_binds_single_store_object),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED: {name}")
        except AssertionError as exc:
            failed.append(name)
            print(f"FAILED: {name} -> {exc}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"ERROR : {name} -> {type(exc).__name__}: {exc}")

    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        raise SystemExit(1)
    print("\nALL RUNTIME DOMAIN IDENTITY TESTS PASSED")


if __name__ == "__main__":
    main()
