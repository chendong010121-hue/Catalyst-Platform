"""Pre-Provider Safety & Lifecycle Hardening 测试。

覆盖：Runtime 生命周期、Policy fail-closed、Capability 契约、Loop budget、
Capability identity、History immutability、deterministic rendering。
"""

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
    ModelResponse,
    ModelUsage,
    ReasoningResult,
    Stop,
    Success,
)
from agent_runtime.errors import (
    CapabilityContractError,
    CapabilityRegistrationError,
    PolicyContractError,
    RuntimeExecutionError,
)
from agent_runtime.llm_reasoner import LLMReasoner, _render_json
from agent_runtime.policies import StepLimitPolicy, TokenBudgetPolicy
from agent_runtime.runtime import Runtime

from .fakes import (
    AllowAllPolicy,
    FakeCapability,
    FakeReasoner,
    InMemoryStateStore,
    ScriptedModelProvider,
)


# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------

class RaisingReasoner:
    def decide(self, goal, state, history, capabilities):
        raise RuntimeError("reasoner exploded")


class AlwaysActReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class FixedActReasoner:
    """第一次返回固定 Act，之后 Complete。用于 immutability 测试。"""

    def __init__(self, action):
        self._action = action

    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(self._action))


class BoomThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="saw failure"))
        return ReasoningResult(decision=Act(Action("boom", {})))


class BoomCapability:
    def describe(self):
        return CapabilityDescriptor(id="boom", name="boom", description="fails")

    def invoke(self, parameters, context):
        return Failure("kaput")


class ReturnCapability:
    def __init__(self, value):
        self._value = value

    def describe(self):
        return CapabilityDescriptor(id="ret", name="ret", description="returns value")

    def invoke(self, parameters, context):
        return self._value


class DictResultCapability:
    def __init__(self, data):
        self._data = data

    def describe(self):
        return CapabilityDescriptor(id="dict", name="dict", description="returns dict")

    def invoke(self, parameters, context):
        return Success(self._data)


class MismatchCapability:
    """descriptor.id 与 mapping key 不一致。"""

    def describe(self):
        return CapabilityDescriptor(id="search", name="search", description="mismatch")

    def invoke(self, parameters, context):
        return Success(None)


class BadCheckPolicy:
    def __init__(self, verdict):
        self._verdict = verdict

    def check_action(self, action, state):
        return self._verdict

    def should_stop(self, state, history):
        return Continue()


class BadStopPolicy:
    def check_action(self, action, state):
        return Allow()

    def should_stop(self, state, history):
        return None


# ---------------------------------------------------------------------------
# A. Runtime lifecycle
# ---------------------------------------------------------------------------

def test_a_create_returns_persistent_session():
    store = InMemoryStateStore()
    rt = Runtime(FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    snapshot = rt.create(Goal("得到数字 42"))
    assert snapshot.history == ()
    assert store.load(snapshot.session_id) == snapshot


def test_a_run_failure_session_recoverable():
    store = InMemoryStateStore()
    rt = Runtime(RaisingReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    snapshot = rt.create(Goal("得到数字 42"))
    session_id = snapshot.session_id

    try:
        rt.run(session_id)
    except RuntimeError as exc:
        assert str(exc) == "reasoner exploded"
    else:
        raise AssertionError("expected run to raise")

    # session 仍存在
    assert store.load(session_id).goal.description == "得到数字 42"

    # 用同一个 session_id 可以再次恢复并跑通
    rt2 = Runtime(FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), state_store=store)
    final = rt2.resume(session_id)
    assert isinstance(final.history[-1].decision, Complete)


def test_a_start_failure_exposes_session_id():
    rt = Runtime(RaisingReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), state_store=InMemoryStateStore())
    try:
        rt.start(Goal("x"))
    except RuntimeExecutionError as exc:
        assert exc.session_id
        assert isinstance(exc.__cause__, RuntimeError)
        return
    raise AssertionError("expected RuntimeExecutionError")


# ---------------------------------------------------------------------------
# B. Policy fail-closed
# ---------------------------------------------------------------------------

def test_b_policy_check_fail_closed():
    for bad in [None, object()]:
        store = InMemoryStateStore()
        rt = Runtime(AlwaysActReasoner(), {"add": FakeCapability()}, BadCheckPolicy(bad), state_store=store)
        snapshot = rt.create(Goal("x"))
        try:
            rt.run(snapshot.session_id)
        except PolicyContractError:
            pass
        else:
            raise AssertionError(f"expected PolicyContractError for check_action -> {bad!r}")
        # Capability 未被执行，也未 commit 任何 step
        assert store.load(snapshot.session_id).history == ()


def test_b_policy_should_stop_fail_closed():
    rt = Runtime(AlwaysActReasoner(), {"add": FakeCapability()}, BadStopPolicy(), state_store=InMemoryStateStore())
    snapshot = rt.create(Goal("x"))
    try:
        rt.run(snapshot.session_id)
    except PolicyContractError:
        return
    raise AssertionError("expected PolicyContractError for should_stop -> None")


# ---------------------------------------------------------------------------
# C. Capability contract
# ---------------------------------------------------------------------------

def test_c_capability_invalid_return():
    for bad in [123, None, {"ok": True}]:
        store = InMemoryStateStore()
        rt = Runtime(FixedActReasoner(Action("ret", {})), {"ret": ReturnCapability(bad)}, AllowAllPolicy(), state_store=store)
        snapshot = rt.create(Goal("x"))
        try:
            rt.run(snapshot.session_id)
        except CapabilityContractError:
            pass
        else:
            raise AssertionError(f"expected CapabilityContractError for {bad!r}")
        # 非法 observation 未进入历史
        assert store.load(snapshot.session_id).history == ()


def test_c_capability_exception_still_failure():
    rt = Runtime(BoomThenCompleteReasoner(), {"boom": BoomCapability()}, AllowAllPolicy(), state_store=InMemoryStateStore())
    final = rt.start(Goal("x"))
    assert isinstance(final.history[0].observation, Failure)
    assert isinstance(final.history[-1].decision, Complete)


# ---------------------------------------------------------------------------
# D. Loop budget
# ---------------------------------------------------------------------------

def test_d_step_limit_policy():
    rt = Runtime(AlwaysActReasoner(), {"add": FakeCapability()}, StepLimitPolicy(3), state_store=InMemoryStateStore())
    final = rt.start(Goal("x"))
    assert len(final.history) == 3
    term = final.history[-1].termination
    assert isinstance(term, Stop)
    assert term.reason == "step limit reached"


def test_d_token_budget_policy():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content='{"kind": "act", "capability_id": "add", '
                '"parameters": {"a": 20, "b": 22}}',
                usage=ModelUsage(input_tokens=10, output_tokens=5),
            ),
        ]
    )
    rt = Runtime(LLMReasoner(provider), {"add": FakeCapability()}, TokenBudgetPolicy(15), state_store=InMemoryStateStore())
    final = rt.start(Goal("x"))
    term = final.history[-1].termination
    assert isinstance(term, Stop)
    assert term.reason == "token budget reached"


# ---------------------------------------------------------------------------
# E. Capability identity
# ---------------------------------------------------------------------------

def test_e_capability_identity_ok():
    Runtime(FakeReasoner(), {"add": FakeCapability()}, AllowAllPolicy(), state_store=InMemoryStateStore())


def test_e_capability_identity_mismatch():
    try:
        Runtime(FakeReasoner(), {"actual_key": MismatchCapability()}, AllowAllPolicy(), state_store=InMemoryStateStore())
    except CapabilityRegistrationError:
        return
    raise AssertionError("expected CapabilityRegistrationError at construction")


# ---------------------------------------------------------------------------
# F. History immutability
# ---------------------------------------------------------------------------

def test_f_history_immutability_parameters():
    params = {"a": 20, "b": 22}
    action = Action("add", params)
    rt = Runtime(FixedActReasoner(action), {"add": FakeCapability()}, AllowAllPolicy(), state_store=InMemoryStateStore())
    final = rt.start(Goal("x"))
    params["a"] = 999  # commit 之后修改原始 dict
    assert final.history[0].decision.action.parameters == {"a": 20, "b": 22}


def test_f_history_immutability_observation():
    result = {"value": 42}
    rt = Runtime(FixedActReasoner(Action("dict", {})), {"dict": DictResultCapability(result)}, AllowAllPolicy(), state_store=InMemoryStateStore())
    final = rt.start(Goal("x"))
    result["value"] = 100  # commit 之后修改原始 dict
    assert final.history[0].observation.data == {"value": 42}


# ---------------------------------------------------------------------------
# G. Deterministic rendering
# ---------------------------------------------------------------------------

def test_g_deterministic_set_rendering():
    assert _render_json({"b", "a", "c"}) == '["a", "b", "c"]'
    assert _render_json({"a", "c", "b"}) == '["a", "b", "c"]'

    class Foo:
        pass

    rendered = _render_json(Foo())
    assert "<Foo>" in rendered
    assert "0x" not in rendered  # 不输出内存地址


def main() -> None:
    tests = [
        ("A create 返回持久 session", test_a_create_returns_persistent_session),
        ("A run 失败后 session 可恢复", test_a_run_failure_session_recoverable),
        ("A start 失败暴露 session id", test_a_start_failure_exposes_session_id),
        ("B check_action fail-closed", test_b_policy_check_fail_closed),
        ("B should_stop fail-closed", test_b_policy_should_stop_fail_closed),
        ("C capability 非法返回值", test_c_capability_invalid_return),
        ("C capability 异常仍为 Failure", test_c_capability_exception_still_failure),
        ("D StepLimitPolicy", test_d_step_limit_policy),
        ("D TokenBudgetPolicy", test_d_token_budget_policy),
        ("E capability identity ok", test_e_capability_identity_ok),
        ("E capability identity mismatch", test_e_capability_identity_mismatch),
        ("F history immutability (parameters)", test_f_history_immutability_parameters),
        ("F history immutability (observation)", test_f_history_immutability_observation),
        ("G deterministic set rendering", test_g_deterministic_set_rendering),
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
    print("\nALL PRE-PROVIDER HARDENING TESTS PASSED")


if __name__ == "__main__":
    main()
