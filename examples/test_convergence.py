"""架构收敛（Pre-Provider Convergence）测试。

覆盖：History projection（A/B/C/D）、ModelUsage 持久化与预算（E/F）、
Reasoner 契约收敛（G）、Decision 解析收紧（H/I）、Provider one-attempt（J）。
"""

from __future__ import annotations

from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    Blocked,
    CapabilityDescriptor,
    Complete,
    Continue,
    Deny,
    Fail,
    Failure,
    Goal,
    ModelResponse,
    ModelUsage,
    ReasoningResult,
    StepRecord,
    Stop,
)
from agent_runtime.errors import RuntimeExecutionError
from agent_runtime.llm_reasoner import DecisionParseError, LLMReasoner, _format_history
from agent_runtime.policies import TokenBudgetPolicy
from agent_runtime.runtime import Runtime

from .fakes import (
    AllowAllPolicy,
    FakeCapability,
    FakeReasoner,
    InMemoryStateStore,
    ScriptedModelProvider,
)


def _user_content(request):
    return next(m.content for m in request.messages if m.role == "user")


def _decide(json_str):
    provider = ScriptedModelProvider([json_str])
    return LLMReasoner(provider).decide(Goal("g"), {}, [], []).decision


def _runtime(provider, capabilities, policy):
    return Runtime(
        reasoner=LLMReasoner(provider),
        capabilities=capabilities,
        policy=policy,
        state_store=InMemoryStateStore(),
    )


# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------

class DenyWriteFilePolicy:
    def check_action(self, action, state):
        if action.capability_id == "write_file":
            return Deny("outside workspace")
        return Allow()

    def should_stop(self, state, history):
        return Continue()


class BoomCapability:
    def describe(self):
        return CapabilityDescriptor(id="boom", name="boom", description="fails")

    def invoke(self, parameters):
        return Failure("RuntimeError: kaput")


class RaisingOnceProvider:
    def __init__(self):
        self.call_count = 0

    def request(self, request):
        self.call_count += 1
        raise RuntimeError("first call fails")


# ---------------------------------------------------------------------------
# A/B/C/D：History projection
# ---------------------------------------------------------------------------

def test_a_deny_feedback():
    provider = ScriptedModelProvider(
        [
            '{"kind": "act", "capability_id": "write_file", '
            '"parameters": {"path": "/etc/passwd"}}',
            '{"kind": "complete", "reason": "done"}',
        ]
    )
    _runtime(provider, {}, DenyWriteFilePolicy()).start(Goal("写文件"))

    user = _user_content(provider.requests[1])
    assert "write_file" in user
    assert "/etc/passwd" in user
    assert "Deny" in user
    assert "outside workspace" in user


def test_b_allow_success():
    provider = ScriptedModelProvider(
        [
            '{"kind": "act", "capability_id": "add", "parameters": {"a": 20, "b": 22}}',
            '{"kind": "complete", "reason": "done"}',
        ]
    )
    _runtime(provider, {"add": FakeCapability()}, AllowAllPolicy()).start(
        Goal("得到数字 42")
    )

    user = _user_content(provider.requests[1])
    assert "add" in user
    assert '"a": 20' in user
    assert '"b": 22' in user
    assert "Allow" in user
    assert "Success(42)" in user


def test_c_failure():
    provider = ScriptedModelProvider(
        [
            '{"kind": "act", "capability_id": "boom", "parameters": {}}',
            '{"kind": "complete", "reason": "done"}',
        ]
    )
    _runtime(provider, {"boom": BoomCapability()}, AllowAllPolicy()).start(
        Goal("boom")
    )

    user = _user_content(provider.requests[1])
    assert "Failure" in user
    assert "RuntimeError" in user


def test_d_terminal_stop_renderer():
    steps = [
        StepRecord(index=0, decision=Complete(reason="done")),
        StepRecord(index=1, decision=Fail(reason="failed")),
        StepRecord(index=2, decision=Blocked(reason="blocked")),
        StepRecord(
            index=3,
            decision=Act(Action("x", {})),
            policy_verdict=Allow(),
            termination=Stop("budget"),
        ),
    ]
    text = _format_history(steps)
    assert "Complete" in text and "done" in text
    assert "Fail" in text and "failed" in text
    assert "Blocked" in text and "blocked" in text
    assert "Stop" in text and "budget" in text


# ---------------------------------------------------------------------------
# E/F：ModelUsage 持久化与预算
# ---------------------------------------------------------------------------

def test_e_model_usage_persistence():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content='{"kind": "act", "capability_id": "add", '
                '"parameters": {"a": 20, "b": 22}}',
                usage=ModelUsage(input_tokens=10, output_tokens=5),
            ),
            ModelResponse(
                content='{"kind": "complete", "reason": "done"}',
                usage=ModelUsage(input_tokens=20, output_tokens=4),
            ),
        ]
    )
    final = _runtime(provider, {"add": FakeCapability()}, AllowAllPolicy()).start(
        Goal("得到数字 42")
    )

    assert len(final.history) == 2
    c1 = final.history[0].model_call
    c2 = final.history[1].model_call
    assert c1 is not None and c1.usage.total_tokens == 15
    assert c2 is not None and c2.usage.total_tokens == 24
    total = sum(
        s.model_call.usage.total_tokens
        for s in final.history
        if s.model_call is not None and s.model_call.usage is not None
    )
    assert total == 39


def test_f_token_budget_policy():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content='{"kind": "act", "capability_id": "add", '
                '"parameters": {"a": 20, "b": 22}}',
                usage=ModelUsage(input_tokens=10, output_tokens=5),
            ),
        ]
    )
    final = _runtime(provider, {"add": FakeCapability()}, TokenBudgetPolicy(15)).start(
        Goal("得到数字 42")
    )

    assert len(final.history) == 1
    term = final.history[-1].termination
    assert isinstance(term, Stop)
    assert "token budget" in term.reason


# ---------------------------------------------------------------------------
# G：Reasoner 契约收敛
# ---------------------------------------------------------------------------

def test_g_reasoner_contract():
    from agent_runtime.contracts import Reasoner

    # Reasoner Protocol 不再有 evaluate
    assert not hasattr(Reasoner, "evaluate")

    # LLMReasoner 返回 ReasoningResult
    provider = ScriptedModelProvider(['{"kind": "complete", "reason": "done"}'])
    result = LLMReasoner(provider).decide(Goal("g"), {}, [], [])
    assert isinstance(result, ReasoningResult)
    assert isinstance(result.decision, Complete)
    assert result.model_call is not None

    # FakeReasoner 返回 ReasoningResult，model_call 为 None
    fresult = FakeReasoner().decide(Goal("g"), {}, [], [])
    assert isinstance(fresult, ReasoningResult)
    assert isinstance(fresult.decision, Act)
    assert fresult.model_call is None


# ---------------------------------------------------------------------------
# H/I：Decision 解析收紧
# ---------------------------------------------------------------------------

def test_h_complete_reason_valid():
    for payload in [
        '{"kind": "complete"}',
        '{"kind": "complete", "reason": null}',
        '{"kind": "complete", "reason": "done"}',
    ]:
        decision = _decide(payload)
        assert isinstance(decision, Complete), payload


def test_i_complete_reason_invalid():
    for payload in [
        '{"kind": "complete", "reason": 123}',
        '{"kind": "complete", "reason": []}',
        '{"kind": "complete", "reason": {}}',
    ]:
        try:
            _decide(payload)
        except DecisionParseError:
            continue
        raise AssertionError(f"expected DecisionParseError for {payload}")

    # fail / blocked reason 必须是 string
    for payload in [
        '{"kind": "fail", "reason": 123}',
        '{"kind": "blocked", "reason": 123}',
    ]:
        try:
            _decide(payload)
        except DecisionParseError:
            continue
        raise AssertionError(f"expected DecisionParseError for {payload}")


# ---------------------------------------------------------------------------
# J：Provider one-attempt rule
# ---------------------------------------------------------------------------

def test_j_provider_one_attempt():
    provider = RaisingOnceProvider()
    rt = Runtime(
        reasoner=LLMReasoner(provider),
        capabilities={"add": FakeCapability()},
        policy=AllowAllPolicy(),
        state_store=InMemoryStateStore(),
    )
    try:
        rt.start(Goal("x"))
    except RuntimeExecutionError as exc:
        assert isinstance(exc.__cause__, RuntimeError)
        assert str(exc.__cause__) == "first call fails"
        assert provider.call_count == 1
        return
    raise AssertionError("expected RuntimeError from provider to propagate")


def main() -> None:
    tests = [
        ("A Deny feedback 进入下一次请求", test_a_deny_feedback),
        ("B Allow+Success 进入下一次请求", test_b_allow_success),
        ("C Failure 进入下一次请求", test_c_failure),
        ("D terminal/stop reason renderer", test_d_terminal_stop_renderer),
        ("E ModelUsage 持久化（累计 39）", test_e_model_usage_persistence),
        ("F TokenBudgetPolicy 从 history 触发 Stop", test_f_token_budget_policy),
        ("G Reasoner 契约收敛（无 evaluate / ReasoningResult）", test_g_reasoner_contract),
        ("H complete.reason 合法值", test_h_complete_reason_valid),
        ("I complete/fail/blocked.reason 非法值", test_i_complete_reason_invalid),
        ("J Provider one-attempt（无 retry）", test_j_provider_one_attempt),
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
    print("\nALL CONVERGENCE TESTS PASSED")


if __name__ == "__main__":
    main()
