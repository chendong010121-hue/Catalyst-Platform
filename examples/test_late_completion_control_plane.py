"""Late Completion Evidence & Control Plane Closure 测试。

覆盖（依据 LATE_COMPLETION_EVIDENCE_AND_CONTROL_PLANE_CLOSURE）：
- L1     timeout uncertain → late Success 保留为本地 evidence
- L2     late Success → ConfirmedNotExecuted 被拒
- L3     late Success(42) → ConfirmedExecuted(Success(99)) 被拒（矛盾）
- L4     late Success(42) → matching ConfirmedExecuted 允许
- L5     late Failure → 矛盾 reconciliation 被拒
- L6     late 普通异常 → 外部 reconciliation 仍允许
- L7/L8/L9 同一 Runtime 的 live guard + cancel + quiesce
- L10    submit failure 清除 false-live registry
- L11    done callback 不写 StateStore
"""

from __future__ import annotations

import threading
import time

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
)
from agent_runtime.execution import (
    ExecutionControlPlane,
    ExecutionTimeoutConfig,
    ThreadedExecutionRunner,
)
from agent_runtime.runtime import Runtime

from .fakes import AllowAllPolicy, InMemoryStateStore


class ActThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


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


class BlockThenRaiseCapability:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="block then raise")

    def invoke(self, parameters, context):
        self.started.set()
        self.release.wait()
        raise RuntimeError("late error")


class AddCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="adds")

    def invoke(self, parameters, context):
        return Success(42)


class ThreadRecordingStore:
    def __init__(self):
        self.snapshot = None
        self.commit_threads = []

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        self.commit_threads.append(threading.get_ident())
        self.snapshot = snapshot


def _make_late(cap, store, timeout=0.05, grace=0.1):
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), timeout_config=ExecutionTimeoutConfig(timeout_seconds=timeout, cancellation_grace_seconds=grace), state_store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")
    cap.release.set()
    deadline = time.time() + 5
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert rt.control_plane.active.get(sid) is None  # 已 quiesce
    return rt, sid, exec_id


# ---------------------------------------------------------------------------
# L1–L4：late Success evidence
# ---------------------------------------------------------------------------

def test_l1_late_success_retained_as_evidence():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))
    rt, sid, exec_id = _make_late(cap, store)
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) == Success(42)


def test_l2_late_success_blocks_confirmed_not_executed():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))
    rt, sid, exec_id = _make_late(cap, store)

    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("late Success must block ConfirmedNotExecuted")
    assert store.load(sid).pending_execution is not None


def test_l3_late_success_blocks_mismatched_confirmed_executed():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))
    rt, sid, exec_id = _make_late(cap, store)

    try:
        rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(99)))
    except ReconciliationError:
        pass
    else:
        raise AssertionError("mismatched ConfirmedExecuted must be rejected")
    assert store.load(sid).pending_execution is not None


def test_l4_late_success_matching_confirmed_executed_allowed():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))
    rt, sid, exec_id = _make_late(cap, store)

    rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))
    final = rt.resume(sid)
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Success)
    assert final.history[0].observation.data == 42


# ---------------------------------------------------------------------------
# L5：late Failure evidence
# ---------------------------------------------------------------------------

def test_l5_late_failure_blocks_contradictory_reconciliation():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Failure("known rejection"))
    rt, sid, exec_id = _make_late(cap, store)

    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("late Failure must block ConfirmedNotExecuted")

    try:
        rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(1)))
    except ReconciliationError:
        pass
    else:
        raise AssertionError("mismatched ConfirmedExecuted must be rejected")

    # matching Failure 允许
    rt.reconcile(sid, exec_id, ConfirmedExecuted(Failure("known rejection")))
    assert store.load(sid).pending_execution is None


# ---------------------------------------------------------------------------
# L6：late ordinary exception → 外部 reconciliation 仍允许
# ---------------------------------------------------------------------------

def test_l6_late_ordinary_exception_allows_external_reconciliation():
    store = InMemoryStateStore()
    cap = BlockThenRaiseCapability()
    rt, sid, exec_id = _make_late(cap, store)

    # 无 authoritative evidence（uncertain）→ 外部 reconciliation 允许
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is None
    rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    assert store.load(sid).pending_execution is None


# ---------------------------------------------------------------------------
# L7/L8/L9：同一 Runtime 的 live guard + cancel + quiesce
# ---------------------------------------------------------------------------

def test_l7_l8_l9_same_runtime_live_guard_cancel_quiesce():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))

    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1), state_store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")

    # L7：同一 Runtime 仍能看到 live execution → reconcile 拒绝
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("expected ExecutionStillLiveError from same Runtime")

    # L8：同一 Runtime.cancel 定位同一 live execution（Runtime-local control plane）
    res = rt.cancel(sid)
    assert res.requested is True
    assert res.execution_id == exec_id

    # L9：worker quiesce → 同一 Runtime 的 control plane 观察到不再 live
    cap.release.set()
    deadline = time.time() + 5
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert rt.control_plane.active.get(sid) is None


# ---------------------------------------------------------------------------
# L10：submit failure 清除 false-live registry
# ---------------------------------------------------------------------------

def test_l10_submit_failure_clears_false_live_registry():
    cp = ExecutionControlPlane()
    runner = ThreadedExecutionRunner(control_plane=cp)
    runner._pool.shutdown(wait=True)  # 之后 submit 会抛 RuntimeError

    try:
        runner.run(
            AddCapability(),
            {},
            execution_id="exec_1",
            session_id="s",
            timeout_seconds=1.0,
            grace_seconds=0.5,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected submit failure")
    assert cp.active.get("s") is None  # false-live entry 已清除


# ---------------------------------------------------------------------------
# L11：done callback 不写 StateStore
# ---------------------------------------------------------------------------

def test_l11_no_background_callback_writes_store():
    owner_tid = threading.get_ident()
    store = ThreadRecordingStore()
    cap = BlockThenReturnCapability(Success(42))

    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1), state_store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError:
        pass

    cap.release.set()
    deadline = time.time() + 5
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)

    # done callback 只做 runtime-local cleanup，不 commit Session
    assert store.commit_threads
    assert all(t == owner_tid for t in store.commit_threads)


def main() -> None:
    tests = [
        ("L1 late Success retained as evidence", test_l1_late_success_retained_as_evidence),
        ("L2 late Success blocks ConfirmedNotExecuted", test_l2_late_success_blocks_confirmed_not_executed),
        ("L3 late Success blocks mismatched ConfirmedExecuted", test_l3_late_success_blocks_mismatched_confirmed_executed),
        ("L4 late Success matching ConfirmedExecuted allowed", test_l4_late_success_matching_confirmed_executed_allowed),
        ("L5 late Failure blocks contradictory reconciliation", test_l5_late_failure_blocks_contradictory_reconciliation),
        ("L6 late ordinary exception allows reconciliation", test_l6_late_ordinary_exception_allows_external_reconciliation),
        ("L7/L8/L9 same-Runtime live guard + cancel + quiesce", test_l7_l8_l9_same_runtime_live_guard_cancel_quiesce),
        ("L10 submit failure clears false-live registry", test_l10_submit_failure_clears_false_live_registry),
        ("L11 no background callback writes store", test_l11_no_background_callback_writes_store),
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
    print("\nALL LATE COMPLETION & CONTROL PLANE TESTS PASSED")


if __name__ == "__main__":
    main()
