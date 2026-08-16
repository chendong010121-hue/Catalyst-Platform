"""ExecutionCancelled Provenance Race Closure 测试（PRV-1..PRV-7）。

证明：ExecutionCancelled 只有携带本 execution 的 CancellationToken provenance
marker（由 token.raise_if_cancelled() 产生）才被视为 confirmed cooperative
cancellation；raw/spurious/foreign ExecutionCancelled 一律 unresolved。post-hoc
request_cancel 不能 retroactively 合法化更早产生的 unproven exception。
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
    Failure,
    Goal,
    ReasoningResult,
    Success,
)
from agent_runtime.errors import (
    CapabilityContractError,
    CapabilityTimeoutUncertainError,
    ExecutionCancelled,
)
from agent_runtime.execution import ExecutionTimeoutConfig
from agent_runtime.runtime import Runtime

from .fakes import AllowAllPolicy, InMemoryStateStore


class ActThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class SpuriousCancelCapability:
    """raw ExecutionCancelled()（无 marker），无 cancel request。"""

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="raw spurious cancel")

    def invoke(self, parameters, context):
        raise ExecutionCancelled()


class SideEffectThenSpuriousCancelCapability:
    """先做 side effect，再 raw raise ExecutionCancelled()（race 场景）。"""

    def __init__(self):
        self.effects = 0

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="side effect then spurious cancel")

    def invoke(self, parameters, context):
        self.effects += 1
        raise ExecutionCancelled()


class ForeignMarkerCapability:
    """携带 foreign marker 的 ExecutionCancelled。"""

    def __init__(self, marker):
        self._marker = marker

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="foreign marker cancel")

    def invoke(self, parameters, context):
        raise ExecutionCancelled(self._marker)


class WaitForCancelCapability:
    """cooperative：等待 cancel request，然后 token.raise_if_cancelled()。"""

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


class TimeoutCooperativeCapability:
    """timeout 触发 cancel 后 cooperative 退出（proven）。"""

    def __init__(self):
        self.started = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="timeout cooperative cancel")

    def invoke(self, parameters, context):
        self.started.set()
        while not context.is_cancel_requested():
            time.sleep(0.001)
        context.raise_if_cancelled()


class BlockThenRawCancelCapability:
    """block 后 raw raise ExecutionCancelled()（late spurious）。"""

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="block then raw cancel")

    def invoke(self, parameters, context):
        self.started.set()
        self.release.wait()
        raise ExecutionCancelled()


class BlockThenCooperativeCancelCapability:
    """block 后 token.raise_if_cancelled()（late proven）。"""

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="block then cooperative cancel")

    def invoke(self, parameters, context):
        self.started.set()
        self.release.wait()
        context.raise_if_cancelled()


def _timeout_config(timeout=0.05, grace=0.1):
    return ExecutionTimeoutConfig(timeout_seconds=timeout, cancellation_grace_seconds=grace)


def _wait_quiesced(rt, sid, timeout=5.0):
    deadline = time.time() + timeout
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.001)
    assert rt.control_plane.active.get(sid) is None, f"session {sid} never quiesced"


def _run_in_thread(rt, sid, outcome):
    try:
        outcome["final"] = rt.run(sid)
    except Exception as exc:  # noqa: BLE001
        outcome["error"] = exc


# ---------------------------------------------------------------------------
# PRV-1 raw spurious exception, no request -> unresolved
# ---------------------------------------------------------------------------

def test_prv_1_raw_spurious_unresolved():
    store = InMemoryStateStore()
    cap = SpuriousCancelCapability()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store)
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError for raw spurious ExecutionCancelled")
    assert store.load(sid).pending_execution is not None


# ---------------------------------------------------------------------------
# PRV-2 deterministic post-hoc request race -> unresolved
# ---------------------------------------------------------------------------

def test_prv_2_post_hoc_request_race_unresolved():
    import agent_runtime.execution as execution

    store = InMemoryStateStore()
    cap = SideEffectThenSpuriousCancelCapability()
    calls = {"n": 0}
    real_wait = execution._futures_wait

    def fake_wait(fs, timeout=None):
        calls["n"] += 1
        future = fs[0]
        if calls["n"] == 1:
            # first wait：等待 worker 真正完成（future 已持有 spurious exception）
            deadline = time.time() + 5
            while not future.done() and time.time() < deadline:
                time.sleep(0.001)
            assert future.done(), "worker never completed before first wait"
            # 谎报 not-done：模拟 first wait 已判定 timeout/not-done
            return (set(), set())
        # second wait（grace）：暴露已完成的 future
        return ({future}, set())

    execution._futures_wait = fake_wait
    try:
        rt = Runtime(
            ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store,
            timeout_config=_timeout_config(),
        )
        sid = rt.create(Goal("x")).session_id
        try:
            rt.run(sid)
        except CapabilityContractError:
            pass
        else:
            raise AssertionError("expected CapabilityContractError for post-hoc request race")
    finally:
        execution._futures_wait = real_wait

    assert calls["n"] == 2
    assert cap.effects == 1  # side effect 恰好一次，未重放
    assert store.load(sid).pending_execution is not None  # unresolved，非 Failure("execution cancelled")


# ---------------------------------------------------------------------------
# PRV-3 legitimate manual cancel via token -> confirmed
# ---------------------------------------------------------------------------

def test_prv_3_legitimate_token_cancel_settles():
    store = InMemoryStateStore()
    cap = WaitForCancelCapability()
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store)
    sid = rt.create(Goal("x")).session_id
    outcome = {}
    t = threading.Thread(target=lambda: _run_in_thread(rt, sid, outcome))
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
# PRV-4 timeout cooperative cancellation -> confirmed
# ---------------------------------------------------------------------------

def test_prv_4_timeout_cooperative_cancel_settles():
    store = InMemoryStateStore()
    cap = TimeoutCooperativeCapability()
    rt = Runtime(
        ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.5),
    )
    sid = rt.create(Goal("x")).session_id
    final = rt.run(sid)
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert final.history[0].observation.error == "execution cancelled"


# ---------------------------------------------------------------------------
# PRV-5 foreign provenance -> unproven -> unresolved
# ---------------------------------------------------------------------------

def test_prv_5_foreign_provenance_unresolved():
    store = InMemoryStateStore()
    cap = ForeignMarkerCapability(object())  # foreign marker
    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store)
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError for foreign marker")
    assert store.load(sid).pending_execution is not None


# ---------------------------------------------------------------------------
# PRV-6 late callback raw spurious -> uncertain evidence
# ---------------------------------------------------------------------------

def test_prv_6_late_raw_spurious_uncertain():
    store = InMemoryStateStore()
    cap = BlockThenRawCancelCapability()
    rt = Runtime(
        ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store,
        timeout_config=_timeout_config(),
    )
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")

    cap.release.set()
    _wait_quiesced(rt, sid)
    # late raw spurious -> 不确定，不是 authoritative cancellation
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is None


# ---------------------------------------------------------------------------
# PRV-7 late callback legitimate token -> authoritative cancellation evidence
# ---------------------------------------------------------------------------

def test_prv_7_late_legitimate_token_authoritative():
    store = InMemoryStateStore()
    cap = BlockThenCooperativeCancelCapability()
    rt = Runtime(
        ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), store,
        timeout_config=_timeout_config(),
    )
    sid = rt.create(Goal("x")).session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")

    cap.release.set()
    _wait_quiesced(rt, sid)
    evidence = rt.control_plane.evidence.get_authoritative_observation(sid, exec_id)
    assert isinstance(evidence, Failure)
    assert evidence.error == "execution cancelled"


def main() -> None:
    tests = [
        ("PRV-1 raw spurious unresolved", test_prv_1_raw_spurious_unresolved),
        ("PRV-2 post-hoc request race unresolved", test_prv_2_post_hoc_request_race_unresolved),
        ("PRV-3 legitimate token cancel settles", test_prv_3_legitimate_token_cancel_settles),
        ("PRV-4 timeout cooperative cancel settles", test_prv_4_timeout_cooperative_cancel_settles),
        ("PRV-5 foreign provenance unresolved", test_prv_5_foreign_provenance_unresolved),
        ("PRV-6 late raw spurious uncertain", test_prv_6_late_raw_spurious_uncertain),
        ("PRV-7 late legitimate token authoritative", test_prv_7_late_legitimate_token_authoritative),
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
    print("\nALL EXECUTION_CANCELLED PROVENANCE TESTS PASSED")


if __name__ == "__main__":
    main()
