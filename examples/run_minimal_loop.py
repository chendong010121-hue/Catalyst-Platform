"""最小测试场景：Goal = "得到数字 42"。

验证 Agent Loop 完整跑通：
Goal → Decision(Act) → Policy(Allow) → Capability(add) → Observation(42)
→ StateStore.commit → 下一步 Decision(Complete) → 结束。

Session 由测试侧（模拟 Runtime）创建后交给 Core 运行。
"""

from __future__ import annotations

from agent_runtime.capability_executor import DefaultCapabilityExecutor
from agent_runtime.contracts import Act, Complete, Goal, SessionSnapshot, Success
from agent_runtime.core import AgentCore

from .fakes import AllowAllPolicy, FakeCapability, FakeReasoner, InMemoryStateStore


def main() -> None:
    store = InMemoryStateStore()
    goal = Goal("得到数字 42")
    # 模拟 Runtime：创建 session（含 goal），Core 只负责在其上运行。
    store.commit(SessionSnapshot("demo-42", goal, {}, ()))

    core = AgentCore(
        reasoner=FakeReasoner(),
        capability_executor=DefaultCapabilityExecutor({"add": FakeCapability()}),
        policy=AllowAllPolicy(),
        state_store=store,
    )

    final = core.run("demo-42")

    print("=== 实际 step history ===")
    for step in final.history:
        decision = type(step.decision).__name__
        observation = (
            f"Success({step.observation.data})"
            if isinstance(step.observation, Success)
            else step.observation
        )
        termination = (
            f"Stop({step.termination.reason})"
            if step.termination is not None
            else None
        )
        print(
            f"step {step.index}: decision={decision}, "
            f"policy={type(step.policy_verdict).__name__ if step.policy_verdict else None}, "
            f"observation={observation}, termination={termination}"
        )

    # 断言：完整跑通两步，得到 42 后 Complete。
    assert len(final.history) == 2, final.history
    first, second = final.history
    assert isinstance(first.decision, Act)
    assert isinstance(first.observation, Success) and first.observation.data == 42
    assert isinstance(second.decision, Complete)
    assert second.observation is None

    print("\nPASSED: 2 steps — add(20,22)=42, then Complete")


if __name__ == "__main__":
    main()
