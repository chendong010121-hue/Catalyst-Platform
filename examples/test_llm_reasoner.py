"""LLMReasoner / ModelProvider seam 测试。"""

from __future__ import annotations

from agent_runtime.contracts import Act, Complete, Goal, Success
from agent_runtime.errors import RuntimeExecutionError
from agent_runtime.llm_reasoner import DecisionParseError, LLMReasoner
from agent_runtime.runtime import Runtime
from agent_runtime.execution import RuntimeDomain

from .fakes import (
    AllowAllPolicy,
    FakeCapability,
    InMemoryStateStore,
    ScriptedModelProvider,
)


def _user_content(request):
    return next(m.content for m in request.messages if m.role == "user")


def _run_42():
    provider = ScriptedModelProvider(
        [
            '{"kind": "act", "capability_id": "add", "parameters": {"a": 20, "b": 22}}',
            '{"kind": "complete", "reason": "42 obtained"}',
        ]
    )
    rt = Runtime(reasoner=LLMReasoner(provider), capabilities={"add": FakeCapability()}, policy=AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("得到数字 42"))
    return final, provider


def _decide_with_response(json_str):
    provider = ScriptedModelProvider([json_str])
    return LLMReasoner(provider).decide(Goal("g"), {}, [], []).decision


class RaisingModelProvider:
    def request(self, request):
        raise RuntimeError("provider down")


# ---------------------------------------------------------------------------

def test_llm_reasoner_runs_42_scenario():
    final, provider = _run_42()
    assert len(provider.requests) == 2
    assert len(final.history) == 2
    assert isinstance(final.history[0].decision, Act)
    assert isinstance(final.history[0].observation, Success)
    assert final.history[0].observation.data == 42
    assert isinstance(final.history[-1].decision, Complete)
    assert final.history[-1].decision.reason == "42 obtained"


def test_first_request_sees_goal_and_capability():
    _, provider = _run_42()
    user = _user_content(provider.requests[0])
    assert "得到数字 42" in user
    assert "add" in user
    assert "把两个数" in user


def test_second_request_sees_observation_42():
    _, provider = _run_42()
    user = _user_content(provider.requests[1])
    assert "Success(42)" in user
    assert "step 0" in user


def test_act_json_parses_to_act():
    decision = _decide_with_response(
        '{"kind": "act", "capability_id": "add", "parameters": {"a": 20, "b": 22}}'
    )
    assert isinstance(decision, Act)
    assert decision.action.capability_id == "add"
    assert decision.action.parameters == {"a": 20, "b": 22}


def test_complete_json_parses_to_complete():
    decision = _decide_with_response('{"kind": "complete", "reason": "done"}')
    assert isinstance(decision, Complete)
    assert decision.reason == "done"


def test_invalid_json_raises_parse_error():
    try:
        _decide_with_response("this is not json")
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for non-JSON")


def test_unknown_kind_raises_parse_error():
    try:
        _decide_with_response('{"kind": "dance"}')
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for unknown kind")


def test_act_missing_capability_id_raises():
    try:
        _decide_with_response('{"kind": "act", "parameters": {}}')
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for act without capability_id")


def test_act_parameters_not_object_raises():
    try:
        _decide_with_response(
            '{"kind": "act", "capability_id": "add", "parameters": []}'
        )
    except DecisionParseError:
        return
    raise AssertionError("expected DecisionParseError for non-object parameters")


def test_model_provider_exception_propagates():
    rt = Runtime(reasoner=LLMReasoner(RaisingModelProvider()), capabilities={"add": FakeCapability()}, policy=AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    try:
        rt.start(Goal("will blow up"))
    except RuntimeExecutionError as exc:
        assert exc.session_id
        assert isinstance(exc.__cause__, RuntimeError)
        assert str(exc.__cause__) == "provider down"
        return
    raise AssertionError(
        "expected ModelProvider exception to propagate as infrastructure failure"
    )


def main() -> None:
    tests = [
        ("42 场景经 LLMReasoner+FakeModelProvider 跑通", test_llm_reasoner_runs_42_scenario),
        ("第一次请求能看到 Goal 与 add 描述", test_first_request_sees_goal_and_capability),
        ("第二次请求能看到 Observation=42", test_second_request_sees_observation_42),
        ("act JSON → Act", test_act_json_parses_to_act),
        ("complete JSON → Complete", test_complete_json_parses_to_complete),
        ("非法 JSON 明确失败", test_invalid_json_raises_parse_error),
        ("未知 kind 明确失败", test_unknown_kind_raises_parse_error),
        ("act 缺 capability_id 失败", test_act_missing_capability_id_raises),
        ("parameters 非对象失败", test_act_parameters_not_object_raises),
        ("ModelProvider 异常作为 infrastructure failure 传播", test_model_provider_exception_propagates),
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
    print("\nALL LLM REASONER TESTS PASSED")


if __name__ == "__main__":
    main()
