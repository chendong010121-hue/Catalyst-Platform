"""Unresolved Execution Reconciliation v0.1 测试。"""

from __future__ import annotations

import threading

from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    ConfirmedExecuted,
    ConfirmedNotExecuted,
    Continue,
    Failure,
    Goal,
    ModelResponse,
    ModelToolCall,
    ReasoningResult,
    SessionSnapshot,
    Success,
)
from agent_runtime.core import AgentCore
from agent_runtime.errors import CapabilityContractError, ReconciliationError
from agent_runtime.llm_reasoner import LLMReasoner
from agent_runtime.runtime import Runtime

from .fakes import AllowAllPolicy, ScriptedModelProvider


ADD_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
    "required": ["a", "b"],
    "additionalProperties": False,
}


class RecordingStore:
    def __init__(self, fail_on=None):
        self._snapshots = {}
        self.save_count = 0
        self.fail_on = fail_on or set()

    def load(self, session_id):
        return self._snapshots[session_id]

    def seed(self, snapshot):
        self._snapshots[snapshot.session_id] = snapshot

    def commit(self, snapshot):
        self.save_count += 1
        if self.save_count in self.fail_on:
            raise RuntimeError("simulated store failure")
        self._snapshots[snapshot.session_id] = snapshot

    def last_saved(self):
        return list(self._snapshots.values())[-1] if self._snapshots else None


class AddCapability:
    def __init__(self):
        self.invoke_count = 0

    def describe(self):
        return CapabilityDescriptor(
            id="add", name="add", description="adds", input_schema=ADD_SCHEMA
        )

    def invoke(self, parameters, context):
        self.invoke_count += 1
        return Success(parameters["a"] + parameters["b"])


class CountingReasoner:
    def __init__(self):
        self.decide_calls = 0

    def decide(self, goal, state, history, capabilities):
        self.decide_calls += 1
        return ReasoningResult(decision=Complete(reason="done"))


class AddThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class CountingPolicy:
    def __init__(self):
        self.check_calls = 0
        self.stop_calls = 0

    def check_action(self, action, state):
        self.check_calls += 1
        return Allow()

    def should_stop(self, state, history):
        self.stop_calls += 1
        return Continue()


def _make_pending(store, reasoner, capabilities=None, policy=None, exec_factory=None):
    capabilities = capabilities or {"add": AddCapability()}
    policy = policy or AllowAllPolicy()
    core = AgentCore(
        reasoner=reasoner,
        capability_executor=DefaultCapabilityExecutor(capabilities),
        policy=policy,
        state_store=store,
        execution_id_factory=exec_factory or (lambda: "exec_1"),
    )
    store.seed(SessionSnapshot("s", Goal("x"), {}, ()))
    store.save_count = 0
    try:
        core.run("s")
    except RuntimeError:
        pass
    return store


# ---------------------------------------------------------------------------

def test_a_pending_contains_model_call():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_abc", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
                usage=None,
            )
        ]
    )
    reasoner = LLMReasoner(provider, decision_protocol="native_tools")
    store = _make_pending(
        RecordingStore(fail_on={2}), reasoner, exec_factory=lambda: "exec_xyz"
    )
    pending = store.last_saved().pending_execution
    assert pending is not None
    assert pending.execution_id == "exec_xyz"
    assert pending.model_call is not None
    assert pending.model_call.assistant_message.tool_calls[0].id == "call_abc"


def test_b_confirmed_executed_success():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    snap = rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))

    assert snap.pending_execution is None
    step0 = snap.history[0]
    assert step0.execution_id == "exec_1"
    assert isinstance(step0.observation, Success) and step0.observation.data == 42
    assert step0.reconciliation.resolution == "confirmed_executed"


def test_c_confirmed_executed_failure():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    snap = rt.reconcile("s", "exec_1", ConfirmedExecuted(Failure("remote rejected")))

    assert isinstance(snap.history[0].observation, Failure)
    assert snap.history[0].observation.error == "remote rejected"


def test_d_confirmed_not_executed():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    snap = rt.reconcile("s", "exec_1", ConfirmedNotExecuted())

    assert snap.pending_execution is None
    step0 = snap.history[0]
    assert isinstance(step0.observation, Failure)
    assert "confirmed: capability did not execute" in step0.observation.error
    assert step0.reconciliation.resolution == "confirmed_not_executed"


def test_e_no_pending_rejects():
    store = RecordingStore()
    store.seed(SessionSnapshot("s", Goal("x"), {}, ()))
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.reconcile("s", "exec_1", ConfirmedNotExecuted())
    except ReconciliationError:
        return
    raise AssertionError("expected ReconciliationError for no pending")


def test_f_wrong_execution_id_rejects():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.reconcile("s", "exec_old", ConfirmedNotExecuted())
    except ReconciliationError:
        pass
    else:
        raise AssertionError("expected ReconciliationError for wrong execution_id")
    assert store.last_saved().pending_execution.execution_id == "exec_1"


def test_h_unsnapshotable_observation():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(threading.Lock())))
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError for unsnapshotable observation")
    assert store.last_saved().pending_execution is not None  # pending 未清


def test_i_commit_failure():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    # reconcile commit 也会失败（save #3 失败）
    store.fail_on = {2, 3}
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected reconciliation commit failure")
    assert store.last_saved().pending_execution is not None


def test_j_reconcile_does_not_invoke():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    cap = AddCapability()
    reasoner = CountingReasoner()
    policy = CountingPolicy()
    rt = Runtime(reasoner, {"add": cap}, policy, state_store=store)
    rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))

    assert reasoner.decide_calls == 0
    assert cap.invoke_count == 0
    assert policy.check_calls == 0  # 原始 Action 早已 Allow，不重复 check
    assert policy.stop_calls == 1  # post-step should_stop 必须重跑（reconciliation parity）


def test_k_no_auto_resume():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    reasoner = CountingReasoner()
    rt = Runtime(reasoner, {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))
    assert reasoner.decide_calls == 0  # reconcile 后不自动 resume


def test_l_native_round_trip():
    provider1 = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_abc", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
            )
        ]
    )
    store = _make_pending(
        RecordingStore(fail_on={2}),
        LLMReasoner(provider1, decision_protocol="native_tools"),
        exec_factory=lambda: "exec_xyz",
    )
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    rt.reconcile("s", "exec_xyz", ConfirmedExecuted(Success(42)))

    provider2 = ScriptedModelProvider([ModelResponse(content="done", finish_reason="stop")])
    rt2 = Runtime(LLMReasoner(provider2, decision_protocol="native_tools"), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    final = rt2.resume("s")

    req = provider2.requests[0]
    assistant = [m for m in req.messages if m.role == "assistant"]
    tool = [m for m in req.messages if m.role == "tool"]
    assert len(assistant) == 1
    assert assistant[0].tool_calls[0].id == "call_abc"
    assert len(tool) == 1
    assert tool[0].tool_call_id == "call_abc"
    assert tool[0].content == "42"
    assert isinstance(final.history[-1].decision, Complete)


def test_m_native_not_executed_round_trip():
    provider1 = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_abc", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
            )
        ]
    )
    store = _make_pending(
        RecordingStore(fail_on={2}),
        LLMReasoner(provider1, decision_protocol="native_tools"),
        exec_factory=lambda: "exec_xyz",
    )
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    rt.reconcile("s", "exec_xyz", ConfirmedNotExecuted())

    provider2 = ScriptedModelProvider([ModelResponse(content="done", finish_reason="stop")])
    rt2 = Runtime(LLMReasoner(provider2, decision_protocol="native_tools"), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    rt2.resume("s")

    tool = [m for m in provider2.requests[0].messages if m.role == "tool"]
    assert len(tool) == 1
    assert tool[0].tool_call_id == "call_abc"
    assert "Tool execution failed" in tool[0].content


def test_n_legacy_reconciliation():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))

    # legacy resume：textual history 包含 resolved observation
    provider = ScriptedModelProvider(['{"kind": "complete", "reason": "done"}'])
    rt2 = Runtime(LLMReasoner(provider), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    final = rt2.resume("s")
    assert isinstance(final.history[-1].decision, Complete)


def test_o_note_durability():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    snap = rt.reconcile(
        "s", "exec_1", ConfirmedExecuted(Success(42), note="confirmed via external system")
    )
    assert snap.history[0].reconciliation.note == "confirmed via external system"


def test_p_duplicate_reconcile_rejected():
    store = _make_pending(RecordingStore(fail_on={2}), AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))
    try:
        rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))
    except ReconciliationError:
        return
    raise AssertionError("expected ReconciliationError for duplicate reconcile")


def test_q_normal_settled_regression():
    store = RecordingStore()
    rt = Runtime(AddThenCompleteReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    final = rt.start(Goal("x"))
    assert final.pending_execution is None
    assert len(final.history) == 2
    # resume terminal
    reasoner = CountingReasoner()
    rt2 = Runtime(reasoner, {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    rt2.resume(final.session_id)
    assert reasoner.decide_calls == 0


def test_r_provenance():
    provider1 = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_abc", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
            )
        ]
    )
    store = _make_pending(
        RecordingStore(fail_on={2}),
        LLMReasoner(provider1, decision_protocol="native_tools"),
        exec_factory=lambda: "exec_xyz",
    )
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    snap = rt.reconcile("s", "exec_xyz", ConfirmedExecuted(Success(42)))

    step0 = snap.history[0]
    assert step0.execution_id == "exec_xyz"
    assert step0.model_call.assistant_message.tool_calls[0].id == "call_abc"
    assert step0.execution_id != step0.model_call.assistant_message.tool_calls[0].id


def main() -> None:
    tests = [
        ("A pending contains model_call", test_a_pending_contains_model_call),
        ("B confirmed executed success", test_b_confirmed_executed_success),
        ("C confirmed executed failure", test_c_confirmed_executed_failure),
        ("D confirmed not executed", test_d_confirmed_not_executed),
        ("E no pending rejects", test_e_no_pending_rejects),
        ("F wrong execution_id rejects", test_f_wrong_execution_id_rejects),
        ("H unsnapshotable observation", test_h_unsnapshotable_observation),
        ("I commit failure leaves pending", test_i_commit_failure),
        ("J reconcile does not invoke", test_j_reconcile_does_not_invoke),
        ("K no auto resume", test_k_no_auto_resume),
        ("L native round-trip", test_l_native_round_trip),
        ("M native not-executed round-trip", test_m_native_not_executed_round_trip),
        ("N legacy reconciliation", test_n_legacy_reconciliation),
        ("O note durability", test_o_note_durability),
        ("P duplicate reconcile rejected", test_p_duplicate_reconcile_rejected),
        ("Q normal settled regression", test_q_normal_settled_regression),
        ("R provenance", test_r_provenance),
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
    print("\nALL RECONCILIATION TESTS PASSED")


if __name__ == "__main__":
    main()
