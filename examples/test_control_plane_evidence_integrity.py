"""Control Plane Publication & Evidence Integrity Closure 测试。

覆盖（依据 DEEPSEEK_IMPLEMENTATION_SELF_VERIFICATION_CROSS_AUDIT_PLAN）：
- A  active→late evidence publication race（deterministic order spy）
- B  timeout-enabled 下层 executor 必须提供 execution-control 依赖（fail-closed）
- C  late ExecutionCancelled 与 normal cooperative cancellation 语义一致
- D  Observation equality 使用 JsonValue-aware equality
- E  LateCompletionEvidence ownership isolation（record/read 双向防御快照）
- F  evidence cleanup 只在 reconciliation durable commit 成功后
- G  auditor-created 额外 adversarial cases
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
    ReconciliationError,
    RuntimeConfigurationError,
)
from agent_runtime.execution import (
    ActiveExecutionRegistry,
    ExecutionControlPlane,
    ExecutionTimeoutConfig,
    LateCompletionEvidenceRegistry,
    ThreadedExecutionRunner,
)
from agent_runtime.runtime import Runtime
from agent_runtime.snapshot import observation_equal

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


class LateCancelCapability:
    """side effect 后 block，release 后 context.raise_if_cancelled()。"""

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.effects = 0
        self.calls = 0

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="late cancel")

    def invoke(self, parameters, context):
        self.calls += 1
        self.effects += 1
        self.started.set()
        self.release.wait()
        context.raise_if_cancelled()  # token 已被 timeout request → ExecutionCancelled


def _timeout_config():
    return ExecutionTimeoutConfig(timeout_seconds=0.05, cancellation_grace_seconds=0.1)


def _make_late(cap, store, timeout=0.05, grace=0.1):
    rt = Runtime(
        ActThenCompleteReasoner(),
        {"add": cap},
        AllowAllPolicy(),
        state_store=store,
        timeout_config=ExecutionTimeoutConfig(timeout_seconds=timeout, cancellation_grace_seconds=grace),
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
    deadline = time.time() + 5
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert rt.control_plane.active.get(sid) is None
    return rt, sid, exec_id


# ---------------------------------------------------------------------------
# A：publication order（evidence 先于 active removal）
# ---------------------------------------------------------------------------

class _SpyActiveRegistry(ActiveExecutionRegistry):
    def __init__(self, timeline):
        super().__init__()
        self._timeline = timeline

    def remove(self, session_id, execution_id):
        self._timeline.append("remove")
        super().remove(session_id, execution_id)


class _SpyEvidenceRegistry(LateCompletionEvidenceRegistry):
    def __init__(self, timeline):
        super().__init__()
        self._timeline = timeline

    def record_observation(self, session_id, execution_id, observation):
        self._timeline.append("record")
        super().record_observation(session_id, execution_id, observation)


def test_a_publication_order_evidence_before_remove():
    timeline = []
    cp = ExecutionControlPlane(
        active_registry=_SpyActiveRegistry(timeline),
        evidence_registry=_SpyEvidenceRegistry(timeline),
    )
    runner = ThreadedExecutionRunner(control_plane=cp)
    cap = BlockThenReturnCapability(Success(42))
    try:
        runner.run(cap, {}, execution_id="e1", session_id="s1", timeout_seconds=0.05, grace_seconds=0.1)
    except CapabilityTimeoutUncertainError:
        pass
    else:
        raise AssertionError("expected CapabilityTimeoutUncertainError")
    cap.release.set()
    deadline = time.time() + 5
    while cp.active.get("s1") is not None and time.time() < deadline:
        time.sleep(0.01)

    # Invariant I2：publish evidence 必须在 remove active 之前（无 visibility hole）
    assert timeline == ["record", "remove"]


# ---------------------------------------------------------------------------
# B：composition fail-closed
# ---------------------------------------------------------------------------

def test_b1_runtime_requires_state_store_and_lower_level_guard():
    # Runtime 必须提供 state_store（无 state_store → TypeError，结构上要求持久化依赖）
    try:
        Runtime(
            ActThenCompleteReasoner(),
            {"add": BlockThenReturnCapability(Success(1))},
            AllowAllPolicy(),
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Runtime requires a state_store")

    # 下层 executor：timeout 会产生 live worker，必须提供 execution-control 依赖
    from agent_runtime.capability_executor import DefaultCapabilityExecutor
    try:
        DefaultCapabilityExecutor(
            {"add": BlockThenReturnCapability(Success(1))},
            timeout_config=_timeout_config(),
        )
    except RuntimeConfigurationError:
        return
    raise AssertionError("lower-level timeout executor requires control_plane")


def test_b2_timeout_disabled_control_plane_optional():
    rt = Runtime(ActThenCompleteReasoner(), {"add": BlockThenReturnCapability(Success(1))}, AllowAllPolicy(), state_store=InMemoryStateStore())
    assert rt is not None


def test_b3_same_runtime_live_guard_blocks_reconcile():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))

    rt = Runtime(ActThenCompleteReasoner(), {"add": cap}, AllowAllPolicy(), state_store=store, timeout_config=_timeout_config())
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id

    # 同一 Runtime 仍能看到 live execution → reconcile 被拒（ExecutionStillLiveError）
    from agent_runtime.errors import ExecutionStillLiveError
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ExecutionStillLiveError:
        pass
    else:
        raise AssertionError("expected ExecutionStillLiveError from same Runtime")
    cap.release.set()
    deadline = time.time() + 5
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)


# ---------------------------------------------------------------------------
# C：late ExecutionCancelled parity
# ---------------------------------------------------------------------------

def test_c1_late_execution_cancelled_becomes_authoritative_cancel_evidence():
    store = InMemoryStateStore()
    cap = LateCancelCapability()
    rt, sid, exec_id = _make_late(cap, store)
    evidence = rt.control_plane.evidence.get_authoritative_observation(sid, exec_id)
    assert isinstance(evidence, Failure)
    assert evidence.error == "execution cancelled"


def test_c2_late_cancel_blocks_confirmed_not_executed():
    store = InMemoryStateStore()
    cap = LateCancelCapability()
    rt, sid, exec_id = _make_late(cap, store)
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("late cancel must block ConfirmedNotExecuted")


def test_c3_late_cancel_matching_confirmed_executed_allowed():
    store = InMemoryStateStore()
    cap = LateCancelCapability()
    rt, sid, exec_id = _make_late(cap, store)
    rt.reconcile(sid, exec_id, ConfirmedExecuted(Failure("execution cancelled")))
    assert store.load(sid).pending_execution is None


def test_c4_late_cancel_no_duplicate_side_effect():
    store = InMemoryStateStore()
    cap = LateCancelCapability()
    rt, sid, exec_id = _make_late(cap, store)
    assert cap.effects == 1
    assert cap.calls == 1
    # ConfirmedNotExecuted 被拒 → 不能 resume 启动第二次 execution
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    assert cap.calls == 1
    assert cap.effects == 1


# ---------------------------------------------------------------------------
# D：JsonValue-aware Observation equality
# ---------------------------------------------------------------------------

def test_d_observation_equality_json_value_aware():
    assert not observation_equal(Success(True), Success(1))
    assert not observation_equal(Success(False), Success(0))
    assert not observation_equal(Success({"x": True}), Success({"x": 1}))
    assert not observation_equal(Success([True]), Success([1]))
    assert observation_equal(Success({"x": 1}), Success({"x": 1}))
    assert observation_equal(Success(1), Success(1.0))  # 都是 JSON number
    assert observation_equal(Failure("x"), Failure("x"))
    assert not observation_equal(Failure("x"), Failure("y"))
    assert not observation_equal(Success(1), Failure("x"))


def test_d2_bool_int_mismatch_rejected_in_reconcile():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(True))  # late evidence = Success(True)
    rt, sid, exec_id = _make_late(cap, store)
    try:
        rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(1)))  # 1 是 number，不是 True
    except ReconciliationError:
        pass
    else:
        raise AssertionError("Success(True) vs Success(1) must be treated as mismatch")


# ---------------------------------------------------------------------------
# E：evidence ownership isolation
# ---------------------------------------------------------------------------

def test_e_record_side_isolation():
    cp = ExecutionControlPlane()
    data = {"x": [1]}
    cp.evidence.record_observation("s", "e", Success(data))
    data["x"].append(99)  # 修改 caller 原始 dict
    obs = cp.evidence.get_authoritative_observation("s", "e")
    assert obs.data["x"] == [1]


def test_e_read_side_isolation():
    cp = ExecutionControlPlane()
    cp.evidence.record_observation("s", "e", Success({"x": [1, 2, 3]}))
    obs = cp.evidence.get_authoritative_observation("s", "e")
    obs.data["x"].append(99)  # 修改读取结果
    obs2 = cp.evidence.get_authoritative_observation("s", "e")
    assert obs2.data["x"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# F：evidence cleanup lifecycle
# ---------------------------------------------------------------------------

class _FailingStore:
    def __init__(self):
        self.snapshot = None
        self.fail_commit = False

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        if self.fail_commit:
            raise RuntimeError("commit failure")
        self.snapshot = snapshot


def test_f1_evidence_removed_after_successful_reconcile():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))
    rt, sid, exec_id = _make_late(cap, store)
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is not None
    rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is None  # 已清理


def test_f2_evidence_retained_on_commit_failure():
    failing = _FailingStore()
    cap = BlockThenReturnCapability(Success(42))
    rt = Runtime(
        ActThenCompleteReasoner(),
        {"add": cap},
        AllowAllPolicy(),
        state_store=failing,
        timeout_config=_timeout_config(),
    )
    snap = rt.create(Goal("x"))
    sid = snap.session_id
    try:
        rt.run(sid)
    except CapabilityTimeoutUncertainError as exc:
        exec_id = exc.execution_id
    cap.release.set()
    deadline = time.time() + 5
    while rt.control_plane.active.get(sid) is not None and time.time() < deadline:
        time.sleep(0.01)
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is not None

    # 开启 commit 失败后 reconcile → pending 保留 + evidence 保留
    failing.fail_commit = True
    try:
        rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected commit failure")
    # pending 保留 + evidence 保留（commit 失败不提前丢 evidence）
    assert failing.load(sid).pending_execution is not None
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is not None


# ---------------------------------------------------------------------------
# G：auditor-created additional adversarial cases
# ---------------------------------------------------------------------------

def test_g1_uncertain_evidence_removed_after_reconcile():
    store = InMemoryStateStore()
    cap = BlockThenRaiseCapability()
    rt, sid, exec_id = _make_late(cap, store)
    # 无 authoritative evidence（uncertain）→ 外部 reconciliation 允许
    assert rt.control_plane.evidence.get_authoritative_observation(sid, exec_id) is None
    rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    assert store.load(sid).pending_execution is None


def test_g2_same_runtime_late_evidence_blocks_confirmed_not_executed():
    store = InMemoryStateStore()
    cap = BlockThenReturnCapability(Success(42))
    rt, sid, exec_id = _make_late(cap, store)  # rt 产生 late Success(42) evidence
    try:
        rt.reconcile(sid, exec_id, ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("Runtime must see its own late authoritative evidence")


def test_g3_late_cancel_evidence_is_failure_not_success():
    store = InMemoryStateStore()
    cap = LateCancelCapability()
    rt, sid, exec_id = _make_late(cap, store)
    # late cancel → Failure("execution cancelled")，不是 Success
    try:
        rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(1)))
    except ReconciliationError:
        pass
    else:
        raise AssertionError("late cancel evidence is Failure, not Success")


def test_g4_uncertain_evidence_allows_confirmed_executed():
    store = InMemoryStateStore()
    cap = BlockThenRaiseCapability()
    rt, sid, exec_id = _make_late(cap, store)
    rt.reconcile(sid, exec_id, ConfirmedExecuted(Success(42)))  # 外部确认执行成功
    assert store.load(sid).pending_execution is None


def test_g5_observation_equal_distinguishes_float_and_bool():
    # 1.0 是 number，1 是 number（相等）；True 是 bool（不等于 1）
    assert observation_equal(Success(1), Success(1.0))
    assert not observation_equal(Success(1.0), Success(True))


def main() -> None:
    tests = [
        ("A publication order evidence before remove", test_a_publication_order_evidence_before_remove),
        ("B1 runtime requires state_store + lower-level guard", test_b1_runtime_requires_state_store_and_lower_level_guard),
        ("B2 timeout disabled control_plane optional", test_b2_timeout_disabled_control_plane_optional),
        ("B3 same-runtime live guard blocks reconcile", test_b3_same_runtime_live_guard_blocks_reconcile),
        ("C1 late cancel authoritative evidence", test_c1_late_execution_cancelled_becomes_authoritative_cancel_evidence),
        ("C2 late cancel blocks ConfirmedNotExecuted", test_c2_late_cancel_blocks_confirmed_not_executed),
        ("C3 late cancel matching ConfirmedExecuted", test_c3_late_cancel_matching_confirmed_executed_allowed),
        ("C4 late cancel no duplicate side effect", test_c4_late_cancel_no_duplicate_side_effect),
        ("D observation equality json-value-aware", test_d_observation_equality_json_value_aware),
        ("D2 bool/int mismatch rejected in reconcile", test_d2_bool_int_mismatch_rejected_in_reconcile),
        ("E record side isolation", test_e_record_side_isolation),
        ("E read side isolation", test_e_read_side_isolation),
        ("F1 evidence removed after successful reconcile", test_f1_evidence_removed_after_successful_reconcile),
        ("F2 evidence retained on commit failure", test_f2_evidence_retained_on_commit_failure),
        ("G1 uncertain evidence removed after reconcile", test_g1_uncertain_evidence_removed_after_reconcile),
        ("G2 same-runtime late evidence blocks ConfirmedNotExecuted", test_g2_same_runtime_late_evidence_blocks_confirmed_not_executed),
        ("G3 late cancel evidence is Failure", test_g3_late_cancel_evidence_is_failure_not_success),
        ("G4 uncertain evidence allows ConfirmedExecuted", test_g4_uncertain_evidence_allows_confirmed_executed),
        ("G5 float/bool equality distinction", test_g5_observation_equal_distinguishes_float_and_bool),
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
    print("\nALL CONTROL PLANE & EVIDENCE INTEGRITY TESTS PASSED")


if __name__ == "__main__":
    main()
