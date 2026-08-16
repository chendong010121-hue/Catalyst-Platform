"""RuntimeDomain Uniqueness Final Closure 测试。

覆盖（依据 RUNTIME_DOMAIN_UNIQUENESS_FINAL_CLOSURE）：
- UD-1..UD-3 同一 persistence namespace 的第二个独立 RuntimeDomain 必须 fail closed
- UD-4..UD-8 同一 domain 共享 + 跨 Runtime safety（简化为复用既有 DI 语义）
- UD-9/UD-10 failed second claim 不改动 first domain / StateStore session 数据
- UD-CONCURRENT 并发 claim：exactly one wins
"""

from __future__ import annotations

import threading

from agent_runtime.contracts import (
    Action, Act, Allow, CapabilityDescriptor, Complete, ConfirmedExecuted,
    ConfirmedNotExecuted, Goal, ReasoningResult, Success,
)
from agent_runtime.errors import (
    CapabilityTimeoutUncertainError,
    ExecutionStillLiveError,
    RuntimeDomainConflictError,
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


# ---------------------------------------------------------------------------
# UD-1..UD-3：second independent RuntimeDomain rejected
# ---------------------------------------------------------------------------

def test_ud1_second_default_domain_rejected():
    store = InMemoryStateStore()
    RuntimeDomain(state_store=store)
    try:
        RuntimeDomain(state_store=store)
    except RuntimeDomainConflictError:
        return
    raise AssertionError("second default RuntimeDomain must fail")


def test_ud2_second_explicit_different_cp_rejected():
    store = InMemoryStateStore()
    d1 = RuntimeDomain(state_store=store, execution_control_plane=ExecutionControlPlane())
    try:
        RuntimeDomain(state_store=store, execution_control_plane=ExecutionControlPlane())
    except RuntimeDomainConflictError:
        return
    raise AssertionError("second explicit different-cp RuntimeDomain must fail")


def test_ud3_equivalent_but_distinct_cp_rejected():
    store = InMemoryStateStore()
    cp1 = ExecutionControlPlane()
    cp2 = ExecutionControlPlane()  # 等价（空状态）但 distinct object
    assert cp1 is not cp2
    RuntimeDomain(state_store=store, execution_control_plane=cp1)
    try:
        RuntimeDomain(state_store=store, execution_control_plane=cp2)
    except RuntimeDomainConflictError:
        return
    raise AssertionError("equivalent-but-distinct control plane must still fail")


# ---------------------------------------------------------------------------
# UD-4：same domain reused by multiple Runtime instances
# ---------------------------------------------------------------------------

def test_ud4_same_domain_reused():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    rtA = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), domain)
    rtB = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), domain)
    assert rtA._control_plane is rtB._control_plane is domain.execution_control_plane


# ---------------------------------------------------------------------------
# UD-5..UD-8：timeout-disabled 跨 Runtime safety（domain 内）
# ---------------------------------------------------------------------------

def _start_live(domain, cap):
    rtA = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain, timeout_config=ExecutionTimeoutConfig(0.05, 0.1))
    snap = rtA.create(Goal("x"))
    sid = snap.session_id
    try:
        rtA.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")
    return rtA, sid, exec_id


def test_ud5_timeout_disabled_cannot_bypass_live_guard():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockBeforeSideEffectCapability()
    rtA, sid, exec_id = _start_live(domain, cap)
    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)  # timeout disabled
    try:
        rtB.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("timeout-disabled B must see live worker")
    cap.release.set()
    import time
    deadline = time.time() + 5
    while domain.execution_control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)


def test_ud6_timeout_disabled_sees_late_evidence():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockThenReturnCapability(Success(42))
    rtA, sid, exec_id = _start_live(domain, cap)
    cap.release.set()
    import time
    deadline = time.time() + 5
    while domain.execution_control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    from agent_runtime.errors import ReconciliationError
    try:
        rtB.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("timeout-disabled B must see late authoritative evidence")


def test_ud7_cross_runtime_cancel():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockBeforeSideEffectCapability()
    rtA, sid, exec_id = _start_live(domain, cap)
    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    res = rtB.cancel(sid)
    assert res.requested is True
    assert res.execution_id == exec_id
    cap.release.set()
    import time
    deadline = time.time() + 5
    while domain.execution_control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)


def test_ud8_duplicate_side_effect_closed():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    cap = BlockBeforeSideEffectCapability()
    rtA, sid, exec_id = _start_live(domain, cap)
    assert cap.calls == 1 and cap.effects == 0
    rtB = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), domain)
    try:
        rtB.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("must not reconcile a live execution")
    from agent_runtime.errors import UnresolvedExecutionError
    try:
        rtB.resume(sid)
    except UnresolvedExecutionError:
        pass
    else:
        raise AssertionError("must not resume a live execution")
    assert cap.calls == 1  # 未启动第二次 execution
    cap.release.set()


# ---------------------------------------------------------------------------
# UD-9 / UD-10：failed second claim 不 mutate first domain / store data
# ---------------------------------------------------------------------------

def test_ud9_failed_second_claim_does_not_mutate_first_domain():
    store = InMemoryStateStore()
    cp1 = ExecutionControlPlane()
    d1 = RuntimeDomain(state_store=store, execution_control_plane=cp1)
    try:
        RuntimeDomain(state_store=store, execution_control_plane=ExecutionControlPlane())
    except RuntimeDomainConflictError:
        pass
    else:
        raise AssertionError("expected conflict")
    # d1 仍绑定原 cp1，claim 未被覆盖
    assert d1.execution_control_plane is cp1
    assert store.get_runtime_domain() is d1


def test_ud10_failed_second_claim_does_not_alter_session_data():
    store = InMemoryStateStore()
    domain = RuntimeDomain(state_store=store)
    rt = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), domain)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    before = store.load(sid)
    try:
        RuntimeDomain(state_store=store)
    except RuntimeDomainConflictError:
        pass
    else:
        raise AssertionError("expected conflict")
    after = store.load(sid)
    assert after == before  # session 数据未被改写


# ---------------------------------------------------------------------------
# UD-CONCURRENT：并发 claim exactly one wins
# ---------------------------------------------------------------------------

def test_ud_concurrent_claim_exactly_one_wins():
    store = InMemoryStateStore()
    barrier = threading.Barrier(2)
    results = []

    def make_domain():
        barrier.wait()
        try:
            RuntimeDomain(state_store=store)
            results.append("ok")
        except RuntimeDomainConflictError:
            results.append("conflict")

    t1 = threading.Thread(target=make_domain)
    t2 = threading.Thread(target=make_domain)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert sorted(results) == ["conflict", "ok"]  # exactly one wins
    assert store.get_runtime_domain() is not None


def main() -> None:
    tests = [
        ("UD-1 second default domain rejected", test_ud1_second_default_domain_rejected),
        ("UD-2 second explicit different cp rejected", test_ud2_second_explicit_different_cp_rejected),
        ("UD-3 equivalent-but-distinct cp rejected", test_ud3_equivalent_but_distinct_cp_rejected),
        ("UD-4 same domain reused", test_ud4_same_domain_reused),
        ("UD-5 timeout-disabled cannot bypass live guard", test_ud5_timeout_disabled_cannot_bypass_live_guard),
        ("UD-6 timeout-disabled sees late evidence", test_ud6_timeout_disabled_sees_late_evidence),
        ("UD-7 cross-runtime cancel", test_ud7_cross_runtime_cancel),
        ("UD-8 duplicate side effect closed", test_ud8_duplicate_side_effect_closed),
        ("UD-9 failed second claim no mutate first domain", test_ud9_failed_second_claim_does_not_mutate_first_domain),
        ("UD-10 failed second claim no alter session data", test_ud10_failed_second_claim_does_not_alter_session_data),
        ("UD-CONCURRENT exactly one wins", test_ud_concurrent_claim_exactly_one_wins),
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
    print("\nALL RUNTIME DOMAIN UNIQUENESS TESTS PASSED")


if __name__ == "__main__":
    main()
