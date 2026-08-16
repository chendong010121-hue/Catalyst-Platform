"""Tool Execution Lifecycle & Audit v0.1 测试（A–M）。"""

from __future__ import annotations

from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Continue,
    Deny,
    Failure,
    Goal,
    ModelResponse,
    ModelToolCall,
    PendingExecution,
    ReasoningResult,
    SessionSnapshot,
    StepRecord,
    Success,
)
from agent_runtime.core import AgentCore
from agent_runtime.errors import CapabilityContractError, UnresolvedExecutionError
from agent_runtime.llm_reasoner import LLMReasoner
from agent_runtime.runtime import Runtime

from .fakes import AllowAllPolicy, FakeCapability, InMemoryStateStore, ScriptedModelProvider


# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------

ADD_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
    "required": ["a", "b"],
    "additionalProperties": False,
}


class RecordingStateStore:
    def __init__(self, fail_on=None):
        self._snapshots = {}
        self.save_count = 0
        self.fail_on = fail_on or set()  # 1-based save 序号
        self.events = []
        self.pending_seen = []

    def load(self, session_id):
        return self._snapshots[session_id]

    def seed(self, snapshot):
        # 直接写入，绕过 fail_on / save 计数（用于建初始 session）
        self._snapshots[snapshot.session_id] = snapshot

    def commit(self, snapshot):
        self.save_count += 1
        kind = "pending" if snapshot.pending_execution is not None else "settled"
        self.events.append(f"save:{kind}")
        if snapshot.pending_execution is not None:
            self.pending_seen.append(snapshot.pending_execution.execution_id)
        if self.save_count in self.fail_on:
            raise RuntimeError("simulated store failure")
        self._snapshots[snapshot.session_id] = snapshot

    def last_saved(self):
        return list(self._snapshots.values())[-1] if self._snapshots else None


class CountingAddCapability:
    def __init__(self, events=None):
        self.events = events
        self.call_count = 0

    def describe(self):
        return CapabilityDescriptor(
            id="add", name="add", description="adds", input_schema=ADD_SCHEMA
        )

    def invoke(self, parameters, context):
        self.call_count += 1
        if self.events is not None:
            self.events.append("invoke")
        return Success(parameters["a"] + parameters["b"])


class RaisingAddCapability:
    def __init__(self):
        self.call_count = 0

    def describe(self):
        return CapabilityDescriptor(
            id="add", name="add", description="raises", input_schema=ADD_SCHEMA
        )

    def invoke(self, parameters, context):
        self.call_count += 1
        raise RuntimeError("boom")


class ReturnsFailureCapability:
    def describe(self):
        return CapabilityDescriptor(
            id="add", name="add", description="returns failure", input_schema=ADD_SCHEMA
        )

    def invoke(self, parameters, context):
        return Failure("boom: known rejection")


class BadReturnCapability:
    def describe(self):
        return CapabilityDescriptor(
            id="add", name="add", description="bad", input_schema=ADD_SCHEMA
        )

    def invoke(self, parameters, context):
        return 123  # 非法返回值 → CapabilityContractError


class AddThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class InvalidArgsReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": "20", "b": 22})))


class FixedActReasoner:
    def __init__(self, action):
        self._action = action

    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(self._action))


class CountingReasoner:
    def __init__(self):
        self.decide_calls = 0

    def decide(self, goal, state, history, capabilities):
        self.decide_calls += 1
        return ReasoningResult(decision=Complete(reason="done"))


class AlwaysActReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class DenyPolicy:
    def check_action(self, action, state):
        return Deny("blocked")

    def should_stop(self, state, history):
        return Continue()


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _core(store, reasoner=None, capabilities=None, policy=None, exec_factory=None):
    reasoner = reasoner or AddThenCompleteReasoner()
    capabilities = capabilities or {"add": CountingAddCapability()}
    policy = policy or AllowAllPolicy()
    return AgentCore(
        reasoner=reasoner,
        capability_executor=DefaultCapabilityExecutor(capabilities),
        policy=policy,
        state_store=store,
        execution_id_factory=exec_factory,
    )


def _new_session(store, session_id="s"):
    store.seed(SessionSnapshot(session_id, Goal("x"), {}, ()))
    store.save_count = 0
    store.events.clear()
    store.pending_seen.clear()
    return session_id


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

def test_a_prepare_before_body():
    store = RecordingStateStore()
    cap = CountingAddCapability(events=store.events)
    core = _core(store, capabilities={"add": cap})
    _new_session(store)
    core.run("s")
    assert store.events[:3] == ["save:pending", "invoke", "save:settled"]


def test_b_prepare_failure_prevents_side_effect():
    store = RecordingStateStore(fail_on={1})
    cap = CountingAddCapability()
    core = _core(store, capabilities={"add": cap})
    _new_session(store)
    try:
        core.run("s")
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected prepare save failure")
    assert cap.call_count == 0


def test_c_normal_success_settles():
    store = RecordingStateStore()
    core = _core(store)
    _new_session(store)
    core.run("s")
    snap = store.last_saved()
    assert snap.pending_execution is None
    step0 = snap.history[0]
    assert step0.execution_id is not None
    assert isinstance(step0.observation, Success) and step0.observation.data == 42
    assert store.pending_seen[0] == step0.execution_id


def test_d_normal_failure_settles():
    store = RecordingStateStore()
    core = _core(store, capabilities={"add": ReturnsFailureCapability()})
    _new_session(store)
    core.run("s")
    snap = store.last_saved()
    assert snap.pending_execution is None
    step0 = snap.history[0]
    assert step0.execution_id is not None
    assert isinstance(step0.observation, Failure)
    assert "boom" in step0.observation.error


def test_e_invalid_args_settles_failure():
    store = RecordingStateStore()
    cap = CountingAddCapability()
    core = _core(store, reasoner=InvalidArgsReasoner(), capabilities={"add": cap})
    _new_session(store)
    core.run("s")
    snap = store.last_saved()
    assert snap.pending_execution is None
    step0 = snap.history[0]
    assert step0.execution_id is not None
    assert isinstance(step0.observation, Failure)
    assert cap.call_count == 0  # body 未执行


def test_f_policy_deny_no_execution():
    store = RecordingStateStore()
    cap = CountingAddCapability()
    core = _core(store, capabilities={"add": cap}, policy=DenyPolicy())
    _new_session(store)
    core.run("s")
    snap = store.last_saved()
    assert cap.call_count == 0
    assert store.pending_seen == []
    deny_step = snap.history[0]
    assert deny_step.execution_id is None
    assert isinstance(deny_step.policy_verdict, Deny)


def test_g_settlement_failure_leaves_pending():
    store = RecordingStateStore(fail_on={2})
    cap = CountingAddCapability()
    core = _core(store, capabilities={"add": cap})
    _new_session(store)
    try:
        core.run("s")
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected settlement save failure")
    assert cap.call_count == 1  # 副作用已发生
    snap = store.last_saved()
    assert snap.pending_execution is not None
    assert len(snap.history) == 0  # settled step 未落盘


def test_h_resume_unresolved_refuses():
    store = RecordingStateStore(fail_on={2})
    core = _core(store, capabilities={"add": CountingAddCapability()})
    _new_session(store)
    try:
        core.run("s")
    except RuntimeError:
        pass

    reasoner2 = CountingReasoner()
    cap2 = CountingAddCapability()
    core2 = _core(store, reasoner=reasoner2, capabilities={"add": cap2})
    try:
        core2.run("s")
    except UnresolvedExecutionError:
        pass
    else:
        raise AssertionError("expected UnresolvedExecutionError on resume")
    assert reasoner2.decide_calls == 0
    assert cap2.call_count == 0


def test_i_executor_infrastructure_exception_leaves_pending():
    store = RecordingStateStore()
    core = _core(store, capabilities={"add": BadReturnCapability()})
    _new_session(store)
    try:
        core.run("s")
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError")
    assert store.last_saved().pending_execution is not None  # pending 未清

    # resume fail-closed
    try:
        _core(store, capabilities={"add": BadReturnCapability()}).run("s")
    except UnresolvedExecutionError:
        return
    raise AssertionError("expected UnresolvedExecutionError on resume")


def test_j_pending_snapshot_isolation():
    store = RecordingStateStore(fail_on={2})
    cap = CountingAddCapability()
    params = {"a": 20, "b": 22}
    core = _core(store, reasoner=FixedActReasoner(Action("add", params)), capabilities={"add": cap})
    _new_session(store)
    try:
        core.run("s")
    except RuntimeError:
        pass
    params["a"] = 999  # 修改原始 dict
    snap = store.last_saved()
    assert snap.pending_execution.action.parameters == {"a": 20, "b": 22}


def test_k_execution_id_distinct_from_tool_call_id():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_abc", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
            ),
            ModelResponse(content="done", finish_reason="stop"),
        ]
    )
    reasoner = LLMReasoner(provider, decision_protocol="native_tools")
    store = RecordingStateStore()
    core = _core(
        store,
        reasoner=reasoner,
        capabilities={"add": CountingAddCapability()},
        exec_factory=lambda: "exec_xyz",
    )
    _new_session(store)
    final = core.run("s")

    step0 = final.history[0]
    assert step0.execution_id == "exec_xyz"
    tool_call_id = step0.model_call.assistant_message.tool_calls[0].id
    assert tool_call_id == "call_abc"
    assert step0.execution_id != tool_call_id


def test_l_resume_normal_settled_unchanged():
    store = InMemoryStateStore()
    rt = Runtime(AddThenCompleteReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    final = rt.start(Goal("x"))
    assert final.pending_execution is None

    reasoner = CountingReasoner()
    rt2 = Runtime(reasoner, {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    final2 = rt2.resume(final.session_id)
    assert reasoner.decide_calls == 0  # terminal 直接返回
    assert final2.pending_execution is None


def test_m_complete_has_no_execution_id():
    store = RecordingStateStore()
    core = _core(store)
    _new_session(store)
    final = core.run("s")
    assert final.history[0].execution_id is not None
    assert final.history[1].execution_id is None
    assert isinstance(final.history[1].decision, Complete)


def test_n_pending_priority_over_terminal():
    store = InMemoryStateStore()
    # 手工构造 corrupt 快照：terminal history + pending_execution
    snap = SessionSnapshot(
        "s",
        Goal("x"),
        {},
        (StepRecord(0, Complete("done")),),
        pending_execution=PendingExecution("exec_1", 1, Action("add", {"a": 1})),
    )
    store.commit(snap)

    reasoner = CountingReasoner()
    rt = Runtime(reasoner, {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.resume("s")
    except UnresolvedExecutionError:
        pass
    else:
        raise AssertionError("expected UnresolvedExecutionError (pending priority over terminal)")
    assert reasoner.decide_calls == 0


def test_o_empty_execution_id_fails_before_prepare():
    store = RecordingStateStore()
    cap = CountingAddCapability()
    core = _core(store, capabilities={"add": cap}, exec_factory=lambda: "")
    _new_session(store)
    try:
        core.run("s")
    except ValueError:
        pass
    else:
        raise AssertionError("expected empty execution_id failure")
    assert cap.call_count == 0
    assert store.pending_seen == []  # 无 prepare save


def test_p_duplicate_execution_id_fails():
    store = RecordingStateStore()
    cap = CountingAddCapability()
    core = _core(
        store,
        reasoner=AlwaysActReasoner(),
        capabilities={"add": cap},
        exec_factory=lambda: "exec_1",
    )
    _new_session(store)
    try:
        core.run("s")
    except ValueError:
        pass
    else:
        raise AssertionError("expected duplicate execution_id failure")
    assert cap.call_count == 1  # 只第一次执行


def test_q_pending_invariants():
    # step_index = -1
    try:
        PendingExecution(execution_id="exec_1", step_index=-1, action=Action("add", {}))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for negative step_index")
    # execution_id 空
    try:
        PendingExecution(execution_id="", step_index=0, action=Action("add", {}))
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty execution_id")


def main() -> None:
    tests = [
        ("A prepare before body", test_a_prepare_before_body),
        ("B prepare failure prevents side effect", test_b_prepare_failure_prevents_side_effect),
        ("C normal success settles", test_c_normal_success_settles),
        ("D normal failure settles", test_d_normal_failure_settles),
        ("E invalid args settles failure", test_e_invalid_args_settles_failure),
        ("F policy deny no execution", test_f_policy_deny_no_execution),
        ("G settlement failure leaves pending", test_g_settlement_failure_leaves_pending),
        ("H resume unresolved refuses", test_h_resume_unresolved_refuses),
        ("I executor infra exception leaves pending", test_i_executor_infrastructure_exception_leaves_pending),
        ("J pending snapshot isolation", test_j_pending_snapshot_isolation),
        ("K execution_id != tool_call_id", test_k_execution_id_distinct_from_tool_call_id),
        ("L resume normal settled unchanged", test_l_resume_normal_settled_unchanged),
        ("M complete has no execution_id", test_m_complete_has_no_execution_id),
        ("N pending priority over terminal", test_n_pending_priority_over_terminal),
        ("O empty execution_id fails before prepare", test_o_empty_execution_id_fails_before_prepare),
        ("P duplicate execution_id fails", test_p_duplicate_execution_id_fails),
        ("Q pending invariants", test_q_pending_invariants),
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
    print("\nALL EXECUTION LIFECYCLE TESTS PASSED")


if __name__ == "__main__":
    main()
