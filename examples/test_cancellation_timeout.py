"""Cooperative Cancellation & Timeout v0.1 测试。

覆盖（依据 COOPERATIVE_CANCELLATION_TIMEOUT_V0_1.md）：
- T1/T2  normal Success/Failure unchanged
- T3/T4  manual cooperative cancel（cancel 是请求，不是结算）
- T5–T7  timeout → cooperative cancel / grace 期 Success/Failure
- T8–T12 timeout 非合作 → unresolved + late completion 不 auto-settle + resume/reconcile
- T13/T14 ordinary exception（含 cancel 后普通异常）仍 unresolved
- T15/T16/T17 registry：无 active / wrong session / stale cleanup
- T18    timeout config validation
- T19    context 不 durable
- T20    worker 不 commit SessionStore
- T21/T22 race 恰好一个 authoritative outcome
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
    Failure,
    Goal,
    ReasoningResult,
    Success,
)
from agent_runtime.errors import (
    CapabilityContractError,
    CapabilityExecutionError,
    CapabilityTimeoutUncertainError,
    SessionConsistencyError,
    UnresolvedExecutionError,
)
from agent_runtime.execution import (
    ActiveExecutionRegistry,
    CancellationSource,
    ExecutionContext,
    ExecutionControlPlane,
    ExecutionTimeoutConfig,
)
from agent_runtime.runtime import Runtime
from agent_runtime.snapshot import snapshot_value

from .fakes import AllowAllPolicy, InMemoryStateStore


class ActThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class AddCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="adds")

    def invoke(self, parameters, context):
        return Success(42)


class KnownFailureCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="fails")

    def invoke(self, parameters, context):
        return Failure("known rejection")


def _runtime(capability, timeout_config=None, store=None, reasoner=None):
    return Runtime(reasoner=reasoner or ActThenCompleteReasoner(), capabilities={"add": capability}, policy=AllowAllPolicy(), timeout_config=timeout_config, state_store=store or InMemoryStateStore())


# ---------------------------------------------------------------------------
# T1 / T2：normal Success / Failure unchanged
# ---------------------------------------------------------------------------

def test_t1_normal_success():
    rt = _runtime(AddCapability())
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Success)


def test_t2_normal_failure():
    rt = _runtime(KnownFailureCapability())
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert final.history[0].observation.error == "known rejection"


# ---------------------------------------------------------------------------
# T3 / T4：manual cooperative cancel
# ---------------------------------------------------------------------------

class WaitForCancelCapability:
    def __init__(self):
        self.started = threading.Event()
        self.cancel_observed = threading.Event()
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="wait for cancel")

    def invoke(self, parameters, context):
        self.started.set()
        while not context.is_cancel_requested():
            time.sleep(0.001)
        self.cancel_observed.set()
        self.release.wait(timeout=5)
        context.raise_if_cancelled()  # cooperative stop → ExecutionCancelled


class WaitThenReturnCapability:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="wait then return")

    def invoke(self, parameters, context):
        self.started.set()
        self.release.wait(timeout=5)
        return Success(7)


def test_t3_manual_cancel_cooperative():
    cap = WaitForCancelCapability()
    store = InMemoryStateStore()
    rt = _runtime(cap, store=store)
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
    res = rt.cancel(sid)
    assert res.requested is True
    assert res.execution_id is not None
    cap.release.set()
    t.join(timeout=5)

    assert "error" not in outcome
    final = outcome["final"]
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert final.history[0].observation.error == "execution cancelled"
    assert isinstance(final.history[-1].decision, Complete)


def test_t4_cancel_request_does_not_settle():
    cap = WaitForCancelCapability()
    store = InMemoryStateStore()
    rt = _runtime(cap, store=store)
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
    assert cap.cancel_observed.wait(timeout=5)  # cancel 已请求，但 capability 尚未退出

    # cancel 只发 signal，不写 Session：此刻 durable Session 仍 pending
    stored = store.load(sid)
    assert stored.pending_execution is not None
    assert stored.history == ()

    cap.release.set()
    t.join(timeout=5)
    assert "error" not in outcome


# ---------------------------------------------------------------------------
# T5–T7：timeout
# ---------------------------------------------------------------------------

class PeriodicCheckCapability:
    def __init__(self):
        self.checked = 0

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="periodic check")

    def invoke(self, parameters, context):
        while True:
            self.checked += 1
            context.raise_if_cancelled()
            time.sleep(0.01)


class GraceSuccessCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="grace success")

    def invoke(self, parameters, context):
        while not context.is_cancel_requested():
            time.sleep(0.005)
        return Success(42)  # deadline 后仍返回 authoritative Success


class GraceFailureCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="grace failure")

    def invoke(self, parameters, context):
        while not context.is_cancel_requested():
            time.sleep(0.005)
        return Failure("known late rejection")


def test_t5_timeout_cooperative_cancel():
    cap = PeriodicCheckCapability()
    rt = _runtime(
        cap, timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.5)
    )
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert final.history[0].observation.error == "execution cancelled"
    assert cap.checked >= 1


def test_t6_timeout_then_success_during_grace():
    rt = _runtime(
        GraceSuccessCapability(),
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.5),
    )
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Success)
    assert final.history[0].observation.data == 42  # authoritative Success 不能被 timeout 覆盖


def test_t7_timeout_then_failure_during_grace():
    rt = _runtime(
        GraceFailureCapability(),
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.5),
    )
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert final.history[0].observation.error == "known late rejection"


# ---------------------------------------------------------------------------
# T8–T12：timeout non-cooperative → unresolved + late completion
# ---------------------------------------------------------------------------

class NonCooperativeCapability:
    def __init__(self):
        self.release = threading.Event()
        self.completed = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="blocks forever")

    def invoke(self, parameters, context):
        try:
            self.release.wait()  # 忽略 token，block beyond grace
            return Success(42)
        finally:
            self.completed.set()


class NonCooperativeRaisesCapability:
    def __init__(self):
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="blocks then raises")

    def invoke(self, parameters, context):
        self.release.wait()
        raise RuntimeError("secret=late-error")


def test_t8_timeout_non_cooperative_uncertain():
    cap = NonCooperativeCapability()
    store = InMemoryStateStore()
    rt = _runtime(
        cap,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1),
        store=store,
    )
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        assert exc.execution_id is not None
    else:
        cap.release.set()
        raise AssertionError("expected CapabilityTimeoutUncertainError")

    stored = store.load(sid)
    assert stored.pending_execution is not None  # pending 未清
    assert stored.history == ()  # 无 settled StepRecord

    # 让后台 worker 最终完成
    cap.release.set()
    assert cap.completed.wait(timeout=5)


def test_t9_late_worker_completion_does_not_auto_settle():
    cap = NonCooperativeCapability()
    store = InMemoryStateStore()
    rt = _runtime(
        cap,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1),
        store=store,
    )
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError:
        pass

    cap.release.set()  # worker 最终返回 Success
    assert cap.completed.wait(timeout=5)
    time.sleep(0.1)  # 给任何（不该有的）auto-settle 时间

    stored = store.load(sid)
    assert stored.pending_execution is not None  # 仍 pending
    assert stored.history == ()  # 未追加 StepRecord


def test_t10_late_worker_exception_does_not_mutate_session():
    cap = NonCooperativeRaisesCapability()
    store = InMemoryStateStore()
    rt = _runtime(
        cap,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1),
        store=store,
    )
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError:
        pass

    cap.release.set()  # worker 最终 raise
    time.sleep(0.1)

    stored = store.load(sid)
    assert stored.pending_execution is not None
    assert stored.history == ()


def test_t11_resume_after_uncertain_timeout():
    cap = NonCooperativeCapability()
    store = InMemoryStateStore()
    rt = _runtime(
        cap,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1),
        store=store,
    )
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError:
        pass
    cap.release.set()
    assert cap.completed.wait(timeout=5)

    try:
        rt.resume(sid)
    except UnresolvedExecutionError:
        pass
    else:
        raise AssertionError("expected UnresolvedExecutionError on resume")


def test_t12_reconciliation_after_uncertain_timeout():
    cap = NonCooperativeCapability()
    store = InMemoryStateStore()
    rt = _runtime(
        cap,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1),
        store=store,
    )
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")
    cap.release.set()
    assert cap.completed.wait(timeout=5)

    # 等待 live execution 真正 quiesce（done callback 移除 registry entry）后才 reconcile
    deadline = time.time() + 5
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert rt.control_plane.active.get(sid) is None

    rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))
    final = rt.resume(sid)
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Success)
    assert final.history[0].execution_id == exec_id


# ---------------------------------------------------------------------------
# T13 / T14：ordinary exception（含 cancel 后普通异常）
# ---------------------------------------------------------------------------

class OrdinaryRaisesCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="raises")

    def invoke(self, parameters, context):
        raise RuntimeError("boom")


class CancelThenOrdinaryRaisesCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="cancel then raise")

    def invoke(self, parameters, context):
        while not context.is_cancel_requested():
            time.sleep(0.001)
        raise RuntimeError("socket reset")  # 不是 ExecutionCancelled


def test_t13_ordinary_exception_unchanged():
    store = InMemoryStateStore()
    rt = _runtime(OrdinaryRaisesCapability(), store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityExecutionError:
        pass
    else:
        raise AssertionError("expected CapabilityExecutionError")
    assert store.load(sid).pending_execution is not None


def test_t14_cancel_then_ordinary_exception_still_uncertain():
    cap = CancelThenOrdinaryRaisesCapability()
    store = InMemoryStateStore()
    rt = _runtime(cap, store=store)
    snap = rt.create(Goal("x"))
    sid = snap.session_id

    outcome = {}

    def run_thread():
        try:
            rt.run(sid)
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    t = threading.Thread(target=run_thread)
    t.start()
    time.sleep(0.05)
    rt.cancel(sid)  # 请求取消
    t.join(timeout=5)

    assert isinstance(outcome["error"], CapabilityExecutionError)  # 不能当作 ExecutionCancelled
    assert store.load(sid).pending_execution is not None


# ---------------------------------------------------------------------------
# T15 / T16 / T17：registry
# ---------------------------------------------------------------------------

def test_t15_no_active_cancel():
    rt = _runtime(AddCapability())
    res = rt.cancel("no-such-session")
    assert res.requested is False
    assert res.execution_id is None


def test_t16_wrong_session_cancel():
    cap = WaitThenReturnCapability()
    store = InMemoryStateStore()
    rt = _runtime(cap, store=store)
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

    res = rt.cancel("wrong-session")
    assert res.requested is False

    cap.release.set()  # capability 正常返回 Success(7)
    t.join(timeout=5)
    assert "error" not in outcome
    assert isinstance(outcome["final"].history[0].observation, Success)


def test_t17_registry_stale_cleanup():
    reg = ActiveExecutionRegistry()
    s1 = CancellationSource()
    reg.register("A", "exec_1", s1)
    # 旧 cleanup 带错 execution_id 不能删新 registration
    reg.remove("A", "exec_stale")
    assert reg.get("A") is not None

    # 同 session 重复 register fail-closed
    try:
        reg.register("A", "exec_2", CancellationSource())
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError for duplicate active execution")

    # 正确 identity 才能删
    reg.remove("A", "exec_1")
    assert reg.get("A") is None


# ---------------------------------------------------------------------------
# T18 / T19 / T20
# ---------------------------------------------------------------------------

def test_t18_timeout_config_validation():
    bad = [
        (0, 0.5),
        (-1, 0.5),
        (True, 0.5),
        (float("nan"), 0.5),
        (float("inf"), 0.5),
        (1.0, -1),
        (1.0, True),
        (1.0, float("nan")),
    ]
    for t, g in bad:
        try:
            ExecutionTimeoutConfig(timeout_seconds=t, cancellation_grace_seconds=g)
        except ValueError:
            continue
        raise AssertionError(f"ExecutionTimeoutConfig({t!r}, {g!r}) should raise ValueError")


def test_t19_context_not_durable():
    source = CancellationSource()
    ctx = ExecutionContext(execution_id="e", cancellation_token=source.token)
    try:
        snapshot_value(ctx)
    except CapabilityContractError:
        return
    raise AssertionError("ExecutionContext must not be snapshot-able")


class ThreadRecordingCapability:
    def __init__(self):
        self.worker_tid = None

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="records thread")

    def invoke(self, parameters, context):
        self.worker_tid = threading.get_ident()
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


def test_t20_worker_never_commits_store():
    owner_tid = threading.get_ident()
    cap = ThreadRecordingCapability()
    store = ThreadRecordingStore()
    rt = _runtime(
        cap,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=1.0, cancellation_grace_seconds=0.5),
        store=store,
    )
    rt.start(Goal("x"))

    # timeout>0 时 capability 在 worker 线程运行
    assert cap.worker_tid is not None
    assert cap.worker_tid != owner_tid
    # 所有 StateStore.commit 都发生在 owner 线程
    assert store.commit_threads
    assert all(t == owner_tid for t in store.commit_threads)


# ---------------------------------------------------------------------------
# T21 / T22：race 恰好一个 authoritative outcome
# ---------------------------------------------------------------------------

class FastThenBlockCapability:
    def __init__(self, block_event):
        self.block = block_event

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="fast then block")

    def invoke(self, parameters, context):
        time.sleep(0.002)
        return Success(1)


def _assert_exactly_one_outcome(store, sid):
    stored = store.load(sid)
    assert stored.pending_execution is None
    # 恰好一个 settled execution step（terminal Complete 无 execution_id）
    exec_steps = [s for s in stored.history if s.execution_id is not None]
    assert len(exec_steps) == 1


def test_t21_cancel_race_with_normal_completion():
    # 反复运行 cancel 与快速完成之间的竞争，断言从不 double settlement / 矛盾
    for _ in range(10):
        store = InMemoryStateStore()
        rt = _runtime(AddCapability(), store=store)
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
        # 与完成竞争
        rt.cancel(sid)
        t.join(timeout=5)

        if "error" in outcome and isinstance(outcome["error"], (CapabilityExecutionError, CapabilityTimeoutUncertainError)):
            assert store.load(sid).pending_execution is not None
        else:
            _assert_exactly_one_outcome(store, sid)


def test_t22_timeout_race_with_normal_completion():
    for _ in range(5):
        store = InMemoryStateStore()
        rt = _runtime(
            AddCapability(),
            timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.001, cancellation_grace_seconds=0.05),
            store=store,
        )
        snap = rt.create(Goal("x"))
        sid = snap.session_id
        try:
            rt.run(sid)
        except CapabilityTimeoutUncertainError:
            assert store.load(sid).pending_execution is not None
            continue
        _assert_exactly_one_outcome(store, sid)


def main() -> None:
    tests = [
        ("T1 normal success", test_t1_normal_success),
        ("T2 normal failure", test_t2_normal_failure),
        ("T3 manual cancel cooperative", test_t3_manual_cancel_cooperative),
        ("T4 cancel request does not settle", test_t4_cancel_request_does_not_settle),
        ("T5 timeout cooperative cancel", test_t5_timeout_cooperative_cancel),
        ("T6 timeout then success during grace", test_t6_timeout_then_success_during_grace),
        ("T7 timeout then failure during grace", test_t7_timeout_then_failure_during_grace),
        ("T8 timeout non-cooperative uncertain", test_t8_timeout_non_cooperative_uncertain),
        ("T9 late worker completion no auto-settle", test_t9_late_worker_completion_does_not_auto_settle),
        ("T10 late worker exception no mutate", test_t10_late_worker_exception_does_not_mutate_session),
        ("T11 resume after uncertain timeout", test_t11_resume_after_uncertain_timeout),
        ("T12 reconciliation after uncertain timeout", test_t12_reconciliation_after_uncertain_timeout),
        ("T13 ordinary exception unchanged", test_t13_ordinary_exception_unchanged),
        ("T14 cancel then ordinary exception", test_t14_cancel_then_ordinary_exception_still_uncertain),
        ("T15 no active cancel", test_t15_no_active_cancel),
        ("T16 wrong session cancel", test_t16_wrong_session_cancel),
        ("T17 registry stale cleanup", test_t17_registry_stale_cleanup),
        ("T18 timeout config validation", test_t18_timeout_config_validation),
        ("T19 context not durable", test_t19_context_not_durable),
        ("T20 worker never commits store", test_t20_worker_never_commits_store),
        ("T21 cancel race", test_t21_cancel_race_with_normal_completion),
        ("T22 timeout race", test_t22_timeout_race_with_normal_completion),
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
    print("\nALL CANCELLATION & TIMEOUT TESTS PASSED")


if __name__ == "__main__":
    main()
