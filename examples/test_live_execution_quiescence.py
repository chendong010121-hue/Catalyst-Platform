"""Live Execution Quiescence Closure 测试。

覆盖（依据 LIVE_EXECUTION_QUIESCENCE_CLOSURE.md）：
- Q1/Q2  timeout uncertain 后 worker 仍 live → registry 保留 + cancel 仍可定位
- Q3     late completion 才移除 registry
- Q4     done callback / remove 的 identity-safety
- Q5/Q6  live worker 时 ConfirmedNotExecuted / ConfirmedExecuted 都被拒绝
- Q7     live worker 时无法经 reconcile/resume 启动第二次 execution
- Q8     spurious ExecutionCancelled → unresolved（不结算取消 Failure）
- Q9     requested cooperative cancellation 仍正常结算
- Q10    task TimeoutError → CapabilityExecutionError（非 Harness timeout）
- Q11    true Harness timeout → CapabilityTimeoutUncertainError
- Q12    late result 仍不 auto-settle
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
    CapabilityContractError,
    CapabilityExecutionError,
    CapabilityTimeoutUncertainError,
    ExecutionCancelled,
    ExecutionStillLiveError,
    UnresolvedExecutionError,
)
from agent_runtime.execution import (
    ActiveExecutionRegistry,
    CancellationSource,
    ExecutionControlPlane,
    ExecutionTimeoutConfig,
)
from agent_runtime.runtime import Runtime

from .fakes import AllowAllPolicy, InMemoryStateStore


class ActThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class BlockBeforeSideEffectCapability:
    """block 在 side effect 之前，忽略 cancellation。"""

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
        self.release.wait()  # block before side effect，忽略 token
        self.effects += 1
        return Success(self.effects)


class BlockForeverCapability:
    def __init__(self):
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="block forever")

    def invoke(self, parameters, context):
        self.release.wait()
        return Success(42)


class SpuriousCancelCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="spurious cancel")

    def invoke(self, parameters, context):
        raise ExecutionCancelled()  # 没有 cancel request


class WaitForCancelCapability:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="wait for cancel")

    def invoke(self, parameters, context):
        self.started.set()
        while not context.is_cancel_requested():
            time.sleep(0.001)
        self.release.wait(timeout=5)
        context.raise_if_cancelled()


class TaskTimeoutCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="task timeout")

    def invoke(self, parameters, context):
        raise TimeoutError("capability-local timeout")


def _make_live_uncertain(cap, store, timeout=0.05, grace=0.1):
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), timeout_config=ExecutionTimeoutConfig(timeout_seconds=timeout, cancellation_grace_seconds=grace), state_store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")
    return rt, sid, exec_id


def _wait_registry_cleared(control_plane, sid, timeout=5.0):
    deadline = time.time() + timeout
    while control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert control_plane.active.get(sid) is None


# ---------------------------------------------------------------------------
# Q1 / Q2：timeout uncertain 后 registry 保留 + cancel 仍可定位
# ---------------------------------------------------------------------------

def test_q1_q2_registry_retains_and_cancel_targets_live():
    cap = BlockBeforeSideEffectCapability()
    store = InMemoryStateStore()
    rt, sid, exec_id = _make_live_uncertain(cap, store)

    # Q1：worker 仍 live，registry 保留原 execution_id
    assert cap.started.is_set()
    assert cap.effects == 0  # block 在 side effect 前
    assert rt.control_plane.active.get(sid) == exec_id

    # Q2：cancel 仍定位同一 live execution（幂等）
    res = rt.cancel(sid)
    assert res.requested is True
    assert res.execution_id == exec_id

    # cleanup
    cap.release.set()
    _wait_registry_cleared(rt.control_plane, sid)


# ---------------------------------------------------------------------------
# Q5 / Q6 / Q7：live worker 阻止 reconcile + 无法启动第二次 execution
# ---------------------------------------------------------------------------

def test_q5_live_blocks_confirmed_not_executed():
    cap = BlockBeforeSideEffectCapability()
    store = InMemoryStateStore()
    rt, sid, exec_id = _make_live_uncertain(cap, store)

    assert cap.effects == 0  # 此刻外部观察 truthfully "未发生"
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("expected ExecutionStillLiveError for live ConfirmedNotExecuted")

    # 仍 pending，未结算
    assert store.load(sid).pending_execution is not None
    cap.release.set()
    _wait_registry_cleared(rt.control_plane, sid)


def test_q6_live_blocks_confirmed_executed():
    cap = BlockBeforeSideEffectCapability()
    store = InMemoryStateStore()
    rt, sid, exec_id = _make_live_uncertain(cap, store)

    try:
        rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("expected ExecutionStillLiveError for live ConfirmedExecuted")

    assert store.load(sid).pending_execution is not None
    cap.release.set()
    _wait_registry_cleared(rt.control_plane, sid)


def test_q7_no_second_execution_while_live():
    cap = BlockBeforeSideEffectCapability()
    store = InMemoryStateStore()
    rt, sid, exec_id = _make_live_uncertain(cap, store)

    # reconcile 被拒
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("expected ExecutionStillLiveError")

    # resume 被 pending gate 拒（无法启动 execution #2）
    try:
        rt.resume(sid)
    except UnresolvedExecutionError:
        pass
    else:
        raise AssertionError("expected UnresolvedExecutionError")

    assert cap.calls == 1  # 未启动第二次 execution
    assert cap.effects == 0  # worker #1 仍 block 在 side effect 前

    cap.release.set()
    _wait_registry_cleared(rt.control_plane, sid)
    assert cap.effects == 1  # 释放后 side effect 恰好发生一次


# ---------------------------------------------------------------------------
# Q3 / Q4：late completion 移除 registry + identity-safe
# ---------------------------------------------------------------------------

def test_q3_late_completion_removes_registry_then_reconcile_allowed():
    cap = BlockBeforeSideEffectCapability()
    store = InMemoryStateStore()
    rt, sid, exec_id = _make_live_uncertain(cap, store)

    cap.release.set()
    _wait_registry_cleared(rt.control_plane, sid)
    assert cap.effects == 1

    # quiescence 后 reconciliation 可用
    rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(cap.effects)))
    final = rt.resume(sid)
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Success)


def test_q4_stale_callback_identity_safe():
    reg = ActiveExecutionRegistry()
    reg.register("A", "exec_1", CancellationSource())

    # 旧 cleanup（错误 identity）不能删
    reg.remove("A", "exec_stale")
    assert reg.get("A") == "exec_1"

    # 正确 identity 才能删
    reg.remove("A", "exec_1")
    assert reg.get("A") is None

    # 同 session 新 execution 可再注册
    reg.register("A", "exec_2", CancellationSource())
    assert reg.get("A") == "exec_2"


# ---------------------------------------------------------------------------
# Q8 / Q9：ExecutionCancelled provenance
# ---------------------------------------------------------------------------

def test_q8_spurious_execution_cancelled_unresolved():
    store = InMemoryStateStore()
    rt = Runtime(ActThenCompleteReasoner(), {"add": SpuriousCancelCapability()}, AllowAllPolicy(), state_store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError for spurious ExecutionCancelled")
    assert store.load(sid).pending_execution is not None


def test_q9_requested_cooperative_cancel_settles():
    cap = WaitForCancelCapability()
    store = InMemoryStateStore()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), state_store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id

    outcome = {}

    def run_thread():
        try:
            outcome["final"] = rt.run(sid)
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    t = threading.Thread(target=run_thread)
    t.start()
    assert cap.started.wait(timeout=5)
    rt.cancel(sid)
    cap.release.set()
    t.join(timeout=5)

    assert "error" not in outcome
    final = outcome["final"]
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert final.history[0].observation.error == "execution cancelled"


# ---------------------------------------------------------------------------
# Q10 / Q11 / Q12：timeout classification + late result
# ---------------------------------------------------------------------------

def test_q10_task_timeout_classified_as_execution_error():
    store = InMemoryStateStore()
    rt = Runtime(ActThenCompleteReasoner(), {"add": TaskTimeoutCapability()}, AllowAllPolicy(), timeout_config=ExecutionTimeoutConfig(timeout_seconds=10.0, cancellation_grace_seconds=0.5), state_store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityExecutionError:
        pass
    except CapabilityTimeoutUncertainError:
        raise AssertionError("task TimeoutError must NOT be classified as Harness timeout")
    else:
        raise AssertionError("expected CapabilityExecutionError")
    assert store.load(sid).pending_execution is not None


def test_q11_true_harness_timeout_uncertain():
    cap = BlockForeverCapability()
    store = InMemoryStateStore()
    rt, sid, exec_id = _make_live_uncertain(cap, store)
    assert rt.control_plane.active.get(sid) == exec_id
    assert store.load(sid).pending_execution is not None
    cap.release.set()
    _wait_registry_cleared(rt.control_plane, sid)


def test_q12_late_result_never_auto_settles():
    cap = BlockBeforeSideEffectCapability()
    store = InMemoryStateStore()
    rt, sid, exec_id = _make_live_uncertain(cap, store)

    cap.release.set()  # worker 最终返回 Success
    _wait_registry_cleared(rt.control_plane, sid)
    time.sleep(0.05)  # 额外观察窗口

    stored = store.load(sid)
    assert stored.pending_execution is not None  # 仍 unresolved
    assert stored.history == ()  # 未 auto-settle


def main() -> None:
    tests = [
        ("Q1/Q2 registry retains + cancel targets live", test_q1_q2_registry_retains_and_cancel_targets_live),
        ("Q3 late completion removes registry + reconcile", test_q3_late_completion_removes_registry_then_reconcile_allowed),
        ("Q4 stale callback identity-safe", test_q4_stale_callback_identity_safe),
        ("Q5 live blocks ConfirmedNotExecuted", test_q5_live_blocks_confirmed_not_executed),
        ("Q6 live blocks ConfirmedExecuted", test_q6_live_blocks_confirmed_executed),
        ("Q7 no second execution while live", test_q7_no_second_execution_while_live),
        ("Q8 spurious ExecutionCancelled unresolved", test_q8_spurious_execution_cancelled_unresolved),
        ("Q9 requested cooperative cancel settles", test_q9_requested_cooperative_cancel_settles),
        ("Q10 task TimeoutError classified as execution error", test_q10_task_timeout_classified_as_execution_error),
        ("Q11 true Harness timeout uncertain", test_q11_true_harness_timeout_uncertain),
        ("Q12 late result never auto-settles", test_q12_late_result_never_auto_settles),
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
    print("\nALL LIVE EXECUTION QUIESCENCE TESTS PASSED")


if __name__ == "__main__":
    main()
