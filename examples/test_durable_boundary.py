"""Durable Fact Boundary 测试。

验证：外部组件（Policy/Capability/Reasoner）只能拿到 defensive copy，
无法改写已持久 Session facts；不可持久化 Observation.data 必须产生明确的
contract failure（而不是裸 TypeError）。
"""

from __future__ import annotations

import threading

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    CapabilityDescriptor,
    Complete,
    Continue,
    Goal,
    ReasoningResult,
    Success,
)
from agent_runtime.errors import CapabilityContractError
from agent_runtime.runtime import Runtime
from agent_runtime.execution import RuntimeDomain

from .fakes import AllowAllPolicy, FakeCapability, InMemoryStateStore


# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------

class AddThenCompleteReasoner:
    """第一次 Act(add, a=20,b=22)，之后 Complete。"""

    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class MutatingPolicy:
    """把收到的 action.parameters 改成 999。"""

    def check_action(self, action, state):
        action.parameters["a"] = 999
        return Allow()

    def should_stop(self, state, history):
        return Continue()


class RecordingCapability:
    """记录自己实际收到的 parameters。"""

    def __init__(self):
        self.received = None

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="records params")

    def invoke(self, parameters, context):
        self.received = dict(parameters)
        return Success(42)


class MutatingCapability:
    """把收到的 parameters 改成 999。"""

    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="mutates params")

    def invoke(self, parameters, context):
        parameters["a"] = 999
        return Success(42)


class MutatingHistoryReasoner:
    """第二轮尝试改写 history[0] 的嵌套参数。"""

    def decide(self, goal, state, history, capabilities):
        if history:
            history[0].decision.action.parameters["a"] = 777
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class UnsnapshotableCapability:
    """返回 Success 内含不可 snapshot 的 runtime object（threading.Lock）。"""

    def describe(self):
        return CapabilityDescriptor(id="bad", name="bad", description="returns lock")

    def invoke(self, parameters, context):
        return Success(threading.Lock())


class BadCapReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Act(Action("bad", {})))


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

def test_mutating_policy():
    cap = RecordingCapability()
    rt = Runtime(AddThenCompleteReasoner(), {"add": cap}, MutatingPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("x"))

    assert cap.received == {"a": 20, "b": 22}  # Capability 仍收到 a=20
    assert final.history[0].decision.action.parameters == {"a": 20, "b": 22}


def test_mutating_capability():
    rt = Runtime(AddThenCompleteReasoner(), {"add": MutatingCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("x"))

    assert final.history[0].decision.action.parameters == {"a": 20, "b": 22}


def test_mutating_history_reasoner():
    rt = Runtime(MutatingHistoryReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("x"))

    assert final.history[0].decision.action.parameters == {"a": 20, "b": 22}


def test_unsnapshotable_observation():
    rt = Runtime(BadCapReasoner(), {"bad": UnsnapshotableCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    snapshot = rt.create(Goal("x"))
    try:
        rt.run(snapshot.session_id)
    except CapabilityContractError as exc:
        assert "not durable" in str(exc) or "snapshot" in str(exc)
        return
    raise AssertionError("expected CapabilityContractError for unsnapshotable observation")


def main() -> None:
    tests = [
        ("MutatingPolicy 不影响 Capability 与 history", test_mutating_policy),
        ("MutatingCapability 不影响 history", test_mutating_capability),
        ("MutatingHistoryReasoner 无法改写持久 step0", test_mutating_history_reasoner),
        ("UnsnapshotableObservation 明确 contract failure", test_unsnapshotable_observation),
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
    print("\nALL DURABLE BOUNDARY TESTS PASSED")


if __name__ == "__main__":
    main()
