"""Execution Certainty & Session Identity Closure 测试。

覆盖（依据 EXECUTION_CERTAINTY_SESSION_IDENTITY_CLOSURE.md）：
- E：Capability raise = outcome unknown（保留 pending unresolved，不 auto retry）；
      explicit Failure / unknown capability / schema-invalid 仍 settle
- I：requested session_id 与 loaded snapshot.session_id 必须一致
- M：Decision/Action 与 native ModelCallRecord.tool_calls 必须一致
- U：recovered ModelUsage 重新 canonicalize，不绕过 TokenBudgetPolicy
- C：Runtime.create 走 validate-before-commit
"""

from __future__ import annotations

from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    ConfirmedNotExecuted,
    Failure,
    Goal,
    ModelCallRecord,
    ModelToolCall,
    ModelUsage,
    PendingExecution,
    ReasoningResult,
    SessionSnapshot,
    StepRecord,
    Success,
)
from agent_runtime.core import AgentCore
from agent_runtime.errors import (
    CapabilityExecutionError,
    ReasonerContractError,
    SessionConsistencyError,
    UnresolvedExecutionError,
)
from agent_runtime.policies import TokenBudgetPolicy
from agent_runtime.runtime import Runtime
from agent_runtime.execution import RuntimeDomain
from agent_runtime.snapshot import validate_session_snapshot

from .fakes import AllowAllPolicy, FakeCapability, FakeReasoner, InMemoryStateStore


ADD_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
    "required": ["a", "b"],
    "additionalProperties": False,
}


class _RawStore:
    """只按原样保存/返回，不做任何 validate/copy。"""

    def __init__(self, snapshot=None):
        self.snapshot = snapshot

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        self.snapshot = snapshot


class _RecordingRawStore:
    def __init__(self):
        self.commits = 0
        self.snapshot = None

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        self.commits += 1
        self.snapshot = snapshot


class AddCapability:
    def __init__(self):
        self.call_count = 0

    def describe(self):
        return CapabilityDescriptor(
            id="add", name="add", description="adds", input_schema=ADD_SCHEMA
        )

    def invoke(self, parameters, context):
        self.call_count += 1
        return Success(parameters["a"] + parameters["b"])


class SideEffectThenRaiseCapability:
    def __init__(self):
        self.effects = 0

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="side effect")

    def invoke(self, parameters, context):
        self.effects += 1  # 真实副作用已发生
        raise RuntimeError("connection dropped after commit may have happened")


class ReturnsFailureCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="returns failure")

    def invoke(self, parameters, context):
        return Failure("known rejection")


class ActOnceReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class ActThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class ActUnknownReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("missing", {})))


class InvalidArgsReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": "20", "b": 22})))


class CountingReasoner:
    def __init__(self):
        self.decide_calls = 0

    def decide(self, goal, state, history, capabilities):
        self.decide_calls += 1
        return ReasoningResult(decision=Complete(reason="done"))


# ---------------------------------------------------------------------------
# E：Capability raise = outcome unknown
# ---------------------------------------------------------------------------

def test_e1_side_effect_then_raise():
    cap = SideEffectThenRaiseCapability()
    store = InMemoryStateStore()
    rt = Runtime(ActOnceReasoner(), {"add": cap}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    snap = rt.create(Goal("x"))
    sid = snap.session_id

    try:
        rt.run(sid)
    except CapabilityExecutionError as exc:
        assert exc.capability_id == "add"
    else:
        raise AssertionError("expected CapabilityExecutionError")

    assert cap.effects == 1  # body 只运行一次
    stored = store.load(sid)
    assert stored.pending_execution is not None  # pending 未清
    assert stored.history == ()  # 无 settled StepRecord

    # resume → unresolved，自动 retry 不可能
    try:
        rt.resume(sid)
    except UnresolvedExecutionError:
        pass
    else:
        raise AssertionError("expected UnresolvedExecutionError on resume")
    assert cap.effects == 1  # 未再次调用


def test_e2_explicit_failure_settles():
    store = InMemoryStateStore()
    rt = Runtime(ActThenCompleteReasoner(), {"add": ReturnsFailureCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert isinstance(final.history[-1].decision, Complete)


def test_e3_unknown_capability_settles():
    rt = Runtime(ActUnknownReasoner(), {}, AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert "unknown capability" in final.history[0].observation.error


def test_e4_schema_invalid_settles():
    cap = AddCapability()
    rt = Runtime(InvalidArgsReasoner(), {"add": cap}, AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert isinstance(final.history[0].observation, Failure)
    assert cap.call_count == 0  # body 未执行


# ---------------------------------------------------------------------------
# I：Session identity
# ---------------------------------------------------------------------------

class _WrongIdentityStore:
    def __init__(self):
        self._b = SessionSnapshot("B", Goal("x"), {}, ())

    def load(self, session_id):
        return self._b  # 无视 requested id，总是返回 B

    def commit(self, snapshot):
        pass


class _FirstValidSecondWrongStore:
    def __init__(self):
        self.load_count = 0
        self._a = SessionSnapshot("A", Goal("x"), {}, ())
        self._b = SessionSnapshot("B", Goal("x"), {}, ())

    def load(self, session_id):
        self.load_count += 1
        return self._a if self.load_count == 1 else self._b

    def commit(self, snapshot):
        pass


def test_i1_runtime_run_mismatch():
    store = _WrongIdentityStore()
    reasoner = CountingReasoner()
    rt = Runtime(reasoner, {"add": FakeCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    try:
        rt.run("A")
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError for identity mismatch")
    assert reasoner.decide_calls == 0


def test_i2_core_second_load_mismatch():
    store = _FirstValidSecondWrongStore()
    reasoner = CountingReasoner()
    rt = Runtime(reasoner, {"add": FakeCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    try:
        rt.run("A")
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError on second load mismatch")
    assert reasoner.decide_calls == 0


def test_i3_reconcile_mismatch():
    store = _WrongIdentityStore()
    rt = Runtime(CountingReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    try:
        rt.reconcile("A", "exec_1", ConfirmedNotExecuted())
    except SessionConsistencyError:
        return
    raise AssertionError("expected SessionConsistencyError for reconcile identity mismatch")


# ---------------------------------------------------------------------------
# M：Decision/native tool facts 一致性
# ---------------------------------------------------------------------------

def _run_expect_contract_error(reasoner, capabilities):
    store = InMemoryStateStore()
    store.commit(SessionSnapshot("s", Goal("x"), {}, ()))
    core = AgentCore(
        reasoner=reasoner,
        capability_executor=DefaultCapabilityExecutor(capabilities),
        policy=AllowAllPolicy(),
        state_store=store,
        execution_id_factory=lambda: "exec_1",
    )
    try:
        core.run("s")
    except ReasonerContractError:
        return
    raise AssertionError("expected ReasonerContractError")


class NameMismatchReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(
            decision=Act(Action("add", {"a": 1, "b": 2})),
            model_call=ModelCallRecord(
                tool_calls=(ModelToolCall("c1", "sub", '{"a":1,"b":2}'),)
            ),
        )


class ArgsMismatchReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(
            decision=Act(Action("add", {"a": 1, "b": 2})),
            model_call=ModelCallRecord(
                tool_calls=(ModelToolCall("c1", "add", '{"a":9,"b":9}'),)
            ),
        )


class BoolIntMismatchReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(
            decision=Act(Action("add", {"a": True})),
            model_call=ModelCallRecord(
                tool_calls=(ModelToolCall("c1", "add", '{"a": 1}'),)
            ),
        )


class MultiToolCallReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(
            decision=Act(Action("add", {"a": 1, "b": 2})),
            model_call=ModelCallRecord(
                tool_calls=(
                    ModelToolCall("c1", "add", '{"a":1,"b":2}'),
                    ModelToolCall("c2", "add", '{"a":5,"b":6}'),
                )
            ),
        )


class TerminalWithToolCallsReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(
            decision=Complete(reason="done"),
            model_call=ModelCallRecord(
                tool_calls=(ModelToolCall("c1", "add", '{"a":1,"b":2}'),)
            ),
        )


class NativeConsistentReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(
            decision=Act(Action("add", {"a": 1, "b": 2})),
            model_call=ModelCallRecord(
                tool_calls=(ModelToolCall("c1", "add", '{"a":1,"b":2}'),)
            ),
        )


class LegacyEmptyToolCallsReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(
            decision=Act(Action("add", {"a": 1, "b": 2})),
            model_call=ModelCallRecord(),  # legacy：无 native tool_calls
        )


def test_m1_native_name_mismatch():
    cap = AddCapability()
    _run_expect_contract_error(NameMismatchReasoner(), {"add": cap})
    assert cap.call_count == 0  # Capability 未执行


def test_m2_native_args_mismatch():
    cap = AddCapability()
    _run_expect_contract_error(ArgsMismatchReasoner(), {"add": cap})
    assert cap.call_count == 0


def test_m3_native_bool_int_mismatch():
    cap = AddCapability()
    _run_expect_contract_error(BoolIntMismatchReasoner(), {"add": cap})
    assert cap.call_count == 0


def test_m4_native_multiple_tool_calls():
    cap = AddCapability()
    _run_expect_contract_error(MultiToolCallReasoner(), {"add": cap})
    assert cap.call_count == 0


def test_m5_terminal_with_tool_calls():
    _run_expect_contract_error(TerminalWithToolCallsReasoner(), {"add": AddCapability()})


def test_m6_valid_native_passes():
    store = InMemoryStateStore()
    store.commit(SessionSnapshot("s", Goal("x"), {}, ()))
    cap = AddCapability()
    core = AgentCore(
        reasoner=NativeConsistentReasoner(),
        capability_executor=DefaultCapabilityExecutor({"add": cap}),
        policy=AllowAllPolicy(),
        state_store=store,
        execution_id_factory=lambda: "exec_1",
    )
    final = core.run("s")
    assert cap.call_count == 1
    assert isinstance(final.history[0].observation, Success)
    assert final.history[0].observation.data == 3


def test_m7_valid_legacy_passes():
    store = InMemoryStateStore()
    store.commit(SessionSnapshot("s", Goal("x"), {}, ()))
    cap = AddCapability()
    core = AgentCore(
        reasoner=LegacyEmptyToolCallsReasoner(),
        capability_executor=DefaultCapabilityExecutor({"add": cap}),
        policy=AllowAllPolicy(),
        state_store=store,
        execution_id_factory=lambda: "exec_1",
    )
    final = core.run("s")
    assert cap.call_count == 1
    assert isinstance(final.history[0].observation, Success)


def _expect_consistency_error(snapshot):
    try:
        validate_session_snapshot(snapshot)
    except SessionConsistencyError:
        return
    raise AssertionError("expected SessionConsistencyError")


def test_m8_pending_mismatch():
    # pending.action = add，model_call.tool_call = sub
    pending = PendingExecution(
        execution_id="exec_1",
        step_index=0,
        action=Action("add", {"a": 1}),
        model_call=ModelCallRecord(
            tool_calls=(ModelToolCall("c1", "sub", '{"a":1}'),)
        ),
    )
    _expect_consistency_error(SessionSnapshot("s", Goal("x"), {}, (), pending_execution=pending))


def test_m9_settled_mismatch():
    step = StepRecord(
        index=0,
        decision=Act(Action("add", {"a": 1})),
        policy_verdict=Allow(),
        observation=Success(3),
        execution_id="exec_1",
        model_call=ModelCallRecord(
            tool_calls=(ModelToolCall("c1", "sub", '{"a":1}'),)
        ),
    )
    _expect_consistency_error(SessionSnapshot("s", Goal("x"), {}, (step,)))


# ---------------------------------------------------------------------------
# U：recovered ModelUsage canonicalization
# ---------------------------------------------------------------------------

def _corrupt_usage_snapshot(field, value):
    usage = ModelUsage(10, 5)
    object.__setattr__(usage, field, value)
    mc = ModelCallRecord(usage=usage)
    step = StepRecord(
        index=0,
        decision=Act(Action("add", {})),
        policy_verdict=Allow(),
        observation=Success(1),
        execution_id="e",
        model_call=mc,
    )
    return SessionSnapshot("s", Goal("x"), {}, (step,))


def test_u1_corrupt_negative_usage():
    _expect_consistency_error(_corrupt_usage_snapshot("input_tokens", -100))


def test_u2_corrupt_bool_usage():
    _expect_consistency_error(_corrupt_usage_snapshot("output_tokens", True))


def test_u3_corrupt_usage_never_reaches_policy():
    store = _RawStore(_corrupt_usage_snapshot("input_tokens", -100))
    rt = Runtime(CountingReasoner(), {"add": FakeCapability()}, TokenBudgetPolicy(1), domain=RuntimeDomain(state_store=store))
    try:
        rt.resume("s")
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("corrupt usage must fail recovery validation before Policy")


# ---------------------------------------------------------------------------
# C：Runtime.create validate-before-commit
# ---------------------------------------------------------------------------

def test_c1_invalid_goal_create():
    store = _RecordingRawStore()
    rt = Runtime(FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    try:
        rt.create("not a Goal")
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError for invalid Goal")
    assert store.commits == 0  # 未 commit


def test_c2_corrupt_goal_create():
    store = _RecordingRawStore()
    rt = Runtime(FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    goal = Goal("x")
    object.__setattr__(goal, "description", 123)
    try:
        rt.create(goal)
    except SessionConsistencyError:
        pass
    else:
        raise AssertionError("expected SessionConsistencyError for corrupt Goal")
    assert store.commits == 0


def test_c3_valid_create():
    store = _RecordingRawStore()
    rt = Runtime(FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=store))
    snap = rt.create(Goal("x"))
    assert store.commits == 1  # commit 恰好一次
    assert snap.session_id  # 非空
    assert snap.goal.description == "x"
    assert snap.history == ()
    assert snap.pending_execution is None


def main() -> None:
    tests = [
        ("E1 side effect then raise", test_e1_side_effect_then_raise),
        ("E2 explicit Failure settles", test_e2_explicit_failure_settles),
        ("E3 unknown capability settles", test_e3_unknown_capability_settles),
        ("E4 schema invalid settles", test_e4_schema_invalid_settles),
        ("I1 Runtime.run mismatch", test_i1_runtime_run_mismatch),
        ("I2 Core second-load mismatch", test_i2_core_second_load_mismatch),
        ("I3 reconcile mismatch", test_i3_reconcile_mismatch),
        ("M1 native name mismatch", test_m1_native_name_mismatch),
        ("M2 native args mismatch", test_m2_native_args_mismatch),
        ("M3 native bool/int mismatch", test_m3_native_bool_int_mismatch),
        ("M4 native multiple tool calls", test_m4_native_multiple_tool_calls),
        ("M5 terminal with tool_calls", test_m5_terminal_with_tool_calls),
        ("M6 valid native passes", test_m6_valid_native_passes),
        ("M7 valid legacy passes", test_m7_valid_legacy_passes),
        ("M8 pending mismatch", test_m8_pending_mismatch),
        ("M9 settled mismatch", test_m9_settled_mismatch),
        ("U1 corrupt negative usage", test_u1_corrupt_negative_usage),
        ("U2 corrupt bool usage", test_u2_corrupt_bool_usage),
        ("U3 corrupt usage never reaches policy", test_u3_corrupt_usage_never_reaches_policy),
        ("C1 invalid Goal create", test_c1_invalid_goal_create),
        ("C2 corrupt Goal create", test_c2_corrupt_goal_create),
        ("C3 valid create", test_c3_valid_create),
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
    print("\nALL EXECUTION CERTAINTY & IDENTITY TESTS PASSED")


if __name__ == "__main__":
    main()
