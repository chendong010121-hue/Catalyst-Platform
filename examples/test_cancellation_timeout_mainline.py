"""Cooperative Cancellation & Timeout v0.1 — Mainline Alignment 验收测试。

CT-MA-1..CT-MA-12 逐条证明：移除 RuntimeDomain / cross-Runtime domain 扩张后，
Runtime 在同一「执行所有权边界」内仍满足 cooperative cancellation / timeout /
late-evidence / live-guard 语义，且 StateStore 契约回归到纯 load/commit。

确定性并发：以 Event 为 primary proof；sleep 仅用于 quiescence 轮询窗口。
"""

from __future__ import annotations

import inspect
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
    CapabilityExecutionError,
    CapabilityTimeoutUncertainError,
    ExecutionStillLiveError,
    ReconciliationError,
    UnresolvedExecutionError,
)
from agent_runtime.execution import ExecutionTimeoutConfig
from agent_runtime.runtime import Runtime

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


class CooperativeCancelCapability:
    """等待 cancel request，然后通过 token 抛 ExecutionCancelled（cooperative）。"""

    def __init__(self):
        self.started = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="cooperative cancel")

    def invoke(self, parameters, context):
        self.started.set()
        while not context.is_cancel_requested():
            time.sleep(0.001)
        context.raise_if_cancelled()


class NonCooperativeBlockCapability:
    """block 忽略 cancellation，直到 release（用于 timeout-uncertain）。"""

    def __init__(self, result=Success(42)):
        self.started = threading.Event()
        self.release = threading.Event()
        self._result = result

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="non-cooperative block")

    def invoke(self, parameters, context):
        self.started.set()
        self.release.wait()
        return self._result


class LateRaiseCapability:
    """block 忽略 cancellation，release 后抛普通异常。"""

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="late raise")

    def invoke(self, parameters, context):
        self.started.set()
        self.release.wait()
        raise RuntimeError("late error")


class TaskTimeoutCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="task timeout")

    def invoke(self, parameters, context):
        raise TimeoutError("capability-local timeout")


class PlainLoadCommitStore:
    """只有 load/commit，没有任何 domain claim / get_runtime_domain / mixin。"""

    def __init__(self):
        self._snapshots = {}

    def load(self, session_id):
        from agent_runtime.snapshot import validate_session_snapshot
        return validate_session_snapshot(self._snapshots[session_id])

    def commit(self, snapshot):
        from agent_runtime.snapshot import validate_session_snapshot
        self._snapshots[snapshot.session_id] = validate_session_snapshot(snapshot)


def _timeout_config(timeout=0.05, grace=0.1):
    return ExecutionTimeoutConfig(timeout_seconds=timeout, cancellation_grace_seconds=grace)


def _wait_quiesced(rt, sid, timeout=5.0):
    deadline = time.time() + timeout
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert rt.control_plane.active.get(sid) is None


# ---------------------------------------------------------------------------
# CT-MA-1 normal execution
# ---------------------------------------------------------------------------

def test_ct_ma_1_normal_execution():
    rt = Runtime(ActThenCompleteReasoner(), {"add": AddCapability()}, AllowAllPolicy(), InMemoryStateStore())
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Success)
    assert final.history[0].observation.data == 42
    assert isinstance(final.history[-1].decision, Complete)


# ---------------------------------------------------------------------------
# CT-MA-2 explicit cancel signal only（cancel 不写 Session）
# ---------------------------------------------------------------------------

def test_ct_ma_2_explicit_cancel_signal_only():
    store = InMemoryStateStore()
    cap = NonCooperativeBlockCapability()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store)
    sid = rt.create(Goal("x")).session_id

    outcome = {}
    t = threading.Thread(target=lambda: _run_capture(rt, sid, outcome))
    t.start()
    assert cap.started.wait(timeout=5)

    res = rt.cancel(sid)
    assert res.requested is True
    assert res.execution_id is not None
    # cancel 只请求，不 commit Session：pending 仍在
    assert store.load(sid).pending_execution is not None

    cap.release.set()
    t.join(timeout=5)
    # 非 cooperative：release 后返回 Success(42)，owner 正常 settle
    final = outcome.get("final")
    assert final is not None and final.pending_execution is None


def _run_capture(rt, sid, outcome):
    try:
        outcome["final"] = rt.run(sid)
    except Exception as exc:  # noqa: BLE001
        outcome["error"] = exc


# ---------------------------------------------------------------------------
# CT-MA-3 cooperative cancel → Failure("execution cancelled")
# ---------------------------------------------------------------------------

def test_ct_ma_3_cooperative_cancel_settles():
    store = InMemoryStateStore()
    cap = CooperativeCancelCapability()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store)
    sid = rt.create(Goal("x")).session_id

    outcome = {}
    t = threading.Thread(target=lambda: _run_capture(rt, sid, outcome))
    t.start()
    assert cap.started.wait(timeout=5)
    rt.cancel(sid)
    t.join(timeout=5)

    final = outcome.get("final")
    assert final is not None
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert final.history[0].observation.error == "execution cancelled"


# ---------------------------------------------------------------------------
# CT-MA-4 non-cooperative timeout → pending 保留 + worker 仍 active
# ---------------------------------------------------------------------------

def test_ct_ma_4_non_cooperative_timeout_uncertain():
    store = InMemoryStateStore()
    cap = NonCooperativeBlockCapability()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store, timeout_config=_timeout_config())
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")

    assert store.load(sid).pending_execution is not None
    assert rt.control_plane.active.get(sid) == exec_id  # worker 仍 live

    cap.release.set()
    _wait_quiesced(rt, sid)


# ---------------------------------------------------------------------------
# CT-MA-5 same-Runtime live reconcile guard
# ---------------------------------------------------------------------------

def test_ct_ma_5_same_runtime_live_guard():
    store = InMemoryStateStore()
    cap = NonCooperativeBlockCapability()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store, timeout_config=_timeout_config())
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id

    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("expected ExecutionStillLiveError")
    cap.release.set()
    _wait_quiesced(rt, sid)


# ---------------------------------------------------------------------------
# CT-MA-6 late authoritative Success → ConfirmedNotExecuted 被拒
# ---------------------------------------------------------------------------

def test_ct_ma_6_late_success_blocks_not_executed():
    store = InMemoryStateStore()
    cap = NonCooperativeBlockCapability(Success(42))
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store, timeout_config=_timeout_config())
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id

    cap.release.set()
    _wait_quiesced(rt, sid)
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) == Success(42)

    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("late Success must block ConfirmedNotExecuted")


# ---------------------------------------------------------------------------
# CT-MA-7 matching explicit reconciliation → 允许 + evidence 清理
# ---------------------------------------------------------------------------

def test_ct_ma_7_matching_reconcile_allows_and_cleans():
    store = InMemoryStateStore()
    cap = NonCooperativeBlockCapability(Success(42))
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store, timeout_config=_timeout_config())
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id

    cap.release.set()
    _wait_quiesced(rt, sid)
    rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))

    assert store.load(sid).pending_execution is None
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is None


# ---------------------------------------------------------------------------
# CT-MA-8 late ordinary exception → uncertain evidence + 外部 reconciliation 允许
# ---------------------------------------------------------------------------

def test_ct_ma_8_late_exception_uncertain_reconcile_allowed():
    store = InMemoryStateStore()
    cap = LateRaiseCapability()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store, timeout_config=_timeout_config())
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id

    cap.release.set()
    _wait_quiesced(rt, sid)
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is None

    rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    assert store.load(sid).pending_execution is None


# ---------------------------------------------------------------------------
# CT-MA-9 task TimeoutError vs harness timeout
# ---------------------------------------------------------------------------

def test_ct_ma_9_task_timeout_classified_as_execution_error():
    store = InMemoryStateStore()
    rt = Runtime(
        ActThenCompleteReasoner(),
        {"add": TaskTimeoutCapability()},
        AllowAllPolicy(),
        store,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=10.0, cancellation_grace_seconds=0.5),
    )
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityExecutionError:
        pass
    except CapabilityTimeoutUncertainError:
        raise AssertionError("task TimeoutError must NOT be harness timeout")
    else:
        raise AssertionError("expected CapabilityExecutionError")
    assert store.load(sid).pending_execution is not None


# ---------------------------------------------------------------------------
# CT-MA-10 no RuntimeDomain dependency（纯 load/commit store）
# ---------------------------------------------------------------------------

def test_ct_ma_10_plain_load_commit_store_supported():
    store = PlainLoadCommitStore()
    assert not hasattr(store, "claim_runtime_domain")
    assert not hasattr(store, "get_runtime_domain")
    rt = Runtime(ActThenCompleteReasoner(), {"add": AddCapability()}, AllowAllPolicy(), store)
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[-1].decision, Complete)


# ---------------------------------------------------------------------------
# CT-MA-11 no public RuntimeDomain requirement
# ---------------------------------------------------------------------------

def test_ct_ma_11_no_runtime_domain_constructor_requirement():
    sig = inspect.signature(Runtime.__init__)
    params = list(sig.parameters)
    assert "state_store" in params
    assert "domain" not in params
    # 4 个位置参数直接构造，无需任何 domain 对象
    rt = Runtime(ActThenCompleteReasoner(), {"add": AddCapability()}, AllowAllPolicy(), InMemoryStateStore())
    assert rt.control_plane is not None  # Runtime-local control plane 由组合根创建
    final = rt.start(Goal("x"))
    assert final.pending_execution is None


# ---------------------------------------------------------------------------
# CT-MA-12 historical regression（代表性：normal + reconcile + resume terminal）
# ---------------------------------------------------------------------------

def test_ct_ma_12_historical_regression_representative():
    store = InMemoryStateStore()
    rt = Runtime(ActThenCompleteReasoner(), {"add": AddCapability()}, AllowAllPolicy(), store)
    final = rt.start(Goal("x"))
    sid = final.session_id
    assert final.pending_execution is None
    assert len(final.history) == 2

    # resume terminal：不重新调用 Reasoner
    class CountingReasoner(ActThenCompleteReasoner):
        def __init__(self):
            self.decide_calls = 0

        def decide(self, goal, state, history, capabilities):
            self.decide_calls += 1
            return super().decide(goal, state, history, capabilities)

    reasoner = CountingReasoner()
    rt2 = Runtime(reasoner, {"add": AddCapability()}, AllowAllPolicy(), store)
    final2 = rt2.resume(sid)
    assert reasoner.decide_calls == 0
    assert final2.pending_execution is None


def main() -> None:
    tests = [
        ("CT-MA-1 normal execution", test_ct_ma_1_normal_execution),
        ("CT-MA-2 explicit cancel signal only", test_ct_ma_2_explicit_cancel_signal_only),
        ("CT-MA-3 cooperative cancel settles", test_ct_ma_3_cooperative_cancel_settles),
        ("CT-MA-4 non-cooperative timeout uncertain", test_ct_ma_4_non_cooperative_timeout_uncertain),
        ("CT-MA-5 same-Runtime live guard", test_ct_ma_5_same_runtime_live_guard),
        ("CT-MA-6 late Success blocks not-executed", test_ct_ma_6_late_success_blocks_not_executed),
        ("CT-MA-7 matching reconcile allows + cleans", test_ct_ma_7_matching_reconcile_allows_and_cleans),
        ("CT-MA-8 late exception uncertain + reconcile", test_ct_ma_8_late_exception_uncertain_reconcile_allowed),
        ("CT-MA-9 task TimeoutError classification", test_ct_ma_9_task_timeout_classified_as_execution_error),
        ("CT-MA-10 plain load/commit store", test_ct_ma_10_plain_load_commit_store_supported),
        ("CT-MA-11 no RuntimeDomain requirement", test_ct_ma_11_no_runtime_domain_constructor_requirement),
        ("CT-MA-12 historical regression", test_ct_ma_12_historical_regression_representative),
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
    print("\nALL CT-MA MAINLINE ALIGNMENT ACCEPTANCE TESTS PASSED")


if __name__ == "__main__":
    main()
