"""Runtime v0.1 测试：依赖装配 / Session 创建与恢复 / 失败边界。"""

from __future__ import annotations

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Failure,
    Goal,
    ReasoningResult,
    SessionSnapshot,
    StepRecord,
    Stop,
    Success,
)
from agent_runtime.errors import RuntimeExecutionError
from agent_runtime.runtime import Runtime

from .fakes import AllowAllPolicy, FakeCapability, FakeReasoner, InMemoryStateStore


# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------

class CountingCompleteReasoner:
    """每次 decide 计数并返回 Complete；用于验证 terminal resume 不再调用 Reasoner。"""

    def __init__(self):
        self.decide_calls = 0

    def decide(self, goal, state, history, capabilities):
        self.decide_calls += 1
        return ReasoningResult(decision=Complete(reason="done"))


class RaisingReasoner:
    """decide 时抛异常；用于验证 Reasoner 异常作为 Runtime failure 传播。"""

    def decide(self, goal, state, history, capabilities):
        raise RuntimeError("reasoner exploded")


class FailThenCompleteReasoner:
    """先调用一个会抛异常的能力，看到 Failure 后 Complete。"""

    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="saw a failure"))
        return ReasoningResult(decision=Act(Action("boom", {})))


class RaisingCapability:
    """invoke 返回 explicit Failure（authoritative known failure）。"""

    def describe(self):
        return CapabilityDescriptor(id="boom", name="boom", description="fails")

    def invoke(self, parameters, context):
        return Failure("kaput")


def _runtime(reasoner, capabilities=None, policy=None, store=None):
    return Runtime(reasoner=reasoner, capabilities=capabilities if capabilities is not None else {"add": FakeCapability()}, policy=policy if policy is not None else AllowAllPolicy(), state_store=store if store is not None else InMemoryStateStore())


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

def test_start_runs_42_scenario():
    final = _runtime(FakeReasoner()).start(Goal("得到数字 42"))
    assert len(final.history) == 2
    assert isinstance(final.history[0].observation, Success)
    assert final.history[0].observation.data == 42
    assert isinstance(final.history[-1].decision, Complete)


def test_session_ids_unique():
    store = InMemoryStateStore()
    rt = _runtime(FakeReasoner(), store=store)
    a = rt.start(Goal("first"))
    b = rt.start(Goal("second"))
    assert a.session_id != b.session_id


def test_resume_does_not_overwrite_history():
    store = InMemoryStateStore()
    goal = Goal("得到数字 42")
    pre = StepRecord(
        index=0,
        decision=Act(Action("add", {"a": 20, "b": 22})),
        policy_verdict=Allow(),
        observation=Success(42),
        execution_id="exec_0",
    )
    store.commit(SessionSnapshot("s-resume", goal, {}, (pre,)))

    final = _runtime(FakeReasoner(), store=store).resume("s-resume")

    assert len(final.history) == 2
    assert final.history[0] == pre
    assert isinstance(final.history[-1].decision, Complete)


def test_resume_terminal_complete_does_not_call_reasoner():
    store = InMemoryStateStore()
    goal = Goal("already done")
    store.commit(
        SessionSnapshot("s-done", goal, {}, (StepRecord(0, Complete("done")),))
    )
    reasoner = CountingCompleteReasoner()

    final = _runtime(reasoner, store=store).resume("s-done")

    assert reasoner.decide_calls == 0
    assert len(final.history) == 1
    assert isinstance(final.history[0].decision, Complete)


def test_resume_terminal_stop_does_not_call_reasoner():
    store = InMemoryStateStore()
    goal = Goal("force stopped")
    stopped = StepRecord(
        index=0,
        decision=Act(Action("add", {"a": 20, "b": 22})),
        policy_verdict=Allow(),
        observation=Success(42),
        termination=Stop("budget exhausted"),
        execution_id="exec_0",
    )
    store.commit(SessionSnapshot("s-stopped", goal, {}, (stopped,)))
    reasoner = CountingCompleteReasoner()

    final = _runtime(reasoner, store=store).resume("s-stopped")

    assert reasoner.decide_calls == 0
    assert isinstance(final.history[-1].termination, Stop)


def test_resume_non_terminal_continues():
    store = InMemoryStateStore()
    goal = Goal("得到数字 42")
    store.commit(SessionSnapshot("s-fresh", goal, {}, ()))  # 空历史 = 非 terminal

    final = _runtime(FakeReasoner(), store=store).resume("s-fresh")

    assert len(final.history) == 2
    assert isinstance(final.history[-1].decision, Complete)


def test_capability_failure_stays_in_history():
    rt = _runtime(
        FailThenCompleteReasoner(), capabilities={"boom": RaisingCapability()}
    )
    final = rt.start(Goal("trigger a failing capability"))

    assert isinstance(final.history[0].observation, Failure)
    assert isinstance(final.history[-1].decision, Complete)


def test_reasoner_exception_propagates_as_runtime_failure():
    rt = _runtime(RaisingReasoner())
    try:
        rt.start(Goal("will blow up"))
    except RuntimeExecutionError as exc:
        assert exc.session_id
        assert isinstance(exc.__cause__, RuntimeError)
        assert str(exc.__cause__) == "reasoner exploded"
        return
    raise AssertionError("expected RuntimeExecutionError from Reasoner failure")


def main() -> None:
    tests = [
        ("start 自动创建 session 并跑通 42", test_start_runs_42_scenario),
        ("session id 唯一", test_session_ids_unique),
        ("resume 不覆盖已有 history", test_resume_does_not_overwrite_history),
        ("terminal(Complete) resume 不再调用 Reasoner", test_resume_terminal_complete_does_not_call_reasoner),
        ("terminal(Stop) resume 不再调用 Reasoner", test_resume_terminal_stop_does_not_call_reasoner),
        ("非 terminal 继续运行", test_resume_non_terminal_continues),
        ("Capability Failure 留在 Agent history", test_capability_failure_stays_in_history),
        ("Reasoner 异常作为 Runtime failure 传播", test_reasoner_exception_propagates_as_runtime_failure),
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
    print("\nALL RUNTIME TESTS PASSED")


if __name__ == "__main__":
    main()
