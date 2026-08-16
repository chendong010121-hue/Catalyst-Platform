"""第二轮加固的回归测试：resume / 执行边界 / Policy Stop 持久化。"""

from __future__ import annotations

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Continue,
    Failure,
    Goal,
    ReasoningResult,
    SessionSnapshot,
    StepRecord,
    Stop,
    Success,
)
from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.core import AgentCore
from agent_runtime.errors import CapabilityExecutionError

from .fakes import AllowAllPolicy, FakeCapability, FakeReasoner, InMemoryStateStore


# ---------------------------------------------------------------------------
# 测试替身（仅本测试文件使用）
# ---------------------------------------------------------------------------

class UnknownCapReasoner:
    """第一步调用不存在的能力，之后看到结果就 Complete。"""

    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="observed a result"))
        return ReasoningResult(decision=Act(Action("missing", {})))


class ThrowingReasoner:
    """第一步调用会抛异常的能力，之后看到结果就 Complete。"""

    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="observed a result"))
        return ReasoningResult(decision=Act(Action("boom", {})))


class AlwaysActReasoner:
    """永远调用 add，用于触发 Policy 强制停止。"""

    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class ThrowingCapability:
    """invoke 时抛异常，验证执行边界归一化为 Failure。"""

    def describe(self):
        return CapabilityDescriptor(
            id="boom", name="boom", description="always raises"
        )

    def invoke(self, parameters):
        raise RuntimeError("boom!")


class StopAfterPolicy:
    """允许前 max_steps 步；达到后返回 Stop(reason)。"""

    def __init__(self, max_steps, reason="max steps reached"):
        self._max_steps = max_steps
        self._reason = reason

    def check_action(self, action, state):
        return Allow()

    def should_stop(self, state, history):
        if len(history) >= self._max_steps:
            return Stop(self._reason)
        return Continue()


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

def _make_core(store, reasoner, capabilities, policy):
    return AgentCore(
        reasoner=reasoner,
        capability_executor=DefaultCapabilityExecutor(capabilities),
        policy=policy,
        state_store=store,
    )


def test_resume_does_not_overwrite():
    store = InMemoryStateStore()
    goal = Goal("得到数字 42")
    pre = StepRecord(
        index=0,
        decision=Act(Action("add", {"a": 20, "b": 22})),
        policy_verdict=Allow(),
        observation=Success(42),
        execution_id="exec_0",
    )
    store.commit(SessionSnapshot("resume", goal, {}, (pre,)))

    final = _make_core(
        store, FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy()
    ).run("resume")

    assert len(final.history) == 2, final.history
    assert final.history[0] == pre, "resume 时原有 step 必须原样保留"
    assert isinstance(final.history[1].decision, Complete)


def test_unknown_capability_does_not_crash():
    store = InMemoryStateStore()
    goal = Goal("调用一个不存在的工具")
    store.commit(SessionSnapshot("unknown", goal, {}, ()))

    final = _make_core(store, UnknownCapReasoner(), {}, AllowAllPolicy()).run(
        "unknown"
    )

    first = final.history[0]
    assert isinstance(first.observation, Failure)
    assert "unknown capability" in first.observation.error
    assert isinstance(final.history[-1].decision, Complete)


def test_capability_exception_does_not_crash():
    store = InMemoryStateStore()
    goal = Goal("调用一个会抛异常的工具")
    store.commit(SessionSnapshot("boom", goal, {}, ()))

    try:
        _make_core(
            store, ThrowingReasoner(), {"boom": ThrowingCapability()}, AllowAllPolicy()
        ).run("boom")
    except CapabilityExecutionError:
        pass
    else:
        raise AssertionError("expected CapabilityExecutionError for capability raise")

    # capability raise = outcome unknown：pending 保持 unresolved，不产生 settled Failure
    saved = store.load("boom")
    assert saved.pending_execution is not None
    assert saved.history == ()


def test_policy_stop_recorded():
    store = InMemoryStateStore()
    goal = Goal("永远不完成，靠 Policy 强制停止")
    store.commit(SessionSnapshot("stop", goal, {}, ()))

    final = _make_core(
        store,
        AlwaysActReasoner(),
        {"add": FakeCapability()},
        StopAfterPolicy(max_steps=1, reason="max steps reached"),
    ).run("stop")

    assert len(final.history) == 1, final.history
    term = final.history[-1].termination
    assert isinstance(term, Stop)
    assert term.reason == "max steps reached"


def main() -> None:
    tests = [
        ("resume 不覆盖历史", test_resume_does_not_overwrite),
        ("unknown capability 不崩溃", test_unknown_capability_does_not_crash),
        ("capability 抛异常不崩溃", test_capability_exception_does_not_crash),
        ("Policy Stop 原因可见", test_policy_stop_recorded),
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
    print("\nALL HARDENING TESTS PASSED")


if __name__ == "__main__":
    main()
