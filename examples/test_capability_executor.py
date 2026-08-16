"""CapabilityExecutor 测试：resolve / input validation / invoke / normalize。"""

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
    ReasoningResult,
    Success,
)
from agent_runtime.errors import (
    CapabilityContractError,
    CapabilityExecutionError,
    CapabilityRegistrationError,
)
from agent_runtime.runtime import Runtime
from agent_runtime.execution import RuntimeDomain

from .fakes import AllowAllPolicy, InMemoryStateStore


ADD_SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
    "required": ["a", "b"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# 测试替身
# ---------------------------------------------------------------------------

class CountingCapability:
    def __init__(self, id="add", input_schema=None, result=42):
        self._id = id
        self._input_schema = input_schema if input_schema is not None else {}
        self._result = result
        self.call_count = 0

    def describe(self):
        return CapabilityDescriptor(
            id=self._id, name=self._id, description="test", input_schema=self._input_schema
        )

    def invoke(self, parameters, context):
        self.call_count += 1
        return Success(self._result)


class RaisingCapability:
    def describe(self):
        return CapabilityDescriptor(id="boom", name="boom", description="raises")

    def invoke(self, parameters, context):
        raise RuntimeError("boom")


class BadReturnCapability:
    def describe(self):
        return CapabilityDescriptor(id="bad", name="bad", description="bad return")

    def invoke(self, parameters, context):
        return 123


class MismatchCapability:
    def describe(self):
        return CapabilityDescriptor(id="search", name="search", description="mismatch")

    def invoke(self, parameters, context):
        return Success(None)


class MinLengthCapability:
    def describe(self):
        return CapabilityDescriptor(
            id="ml", name="ml", description="bad schema",
            input_schema={"type": "string", "minLength": 5},
        )

    def invoke(self, parameters, context):
        return Success(None)


class MutatingCapability:
    def describe(self):
        return CapabilityDescriptor(id="add", name="add", description="mutates")

    def invoke(self, parameters, context):
        parameters["a"] = 999
        return Success(42)


class AddThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class DenyPolicy:
    def check_action(self, action, state):
        return Deny("blocked")

    def should_stop(self, state, history):
        return Continue()


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

def test_a_descriptor_identity():
    # 合法 registry
    DefaultCapabilityExecutor({"add": CountingCapability("add")})
    # key != descriptor.id
    try:
        DefaultCapabilityExecutor({"actual_key": MismatchCapability()})
    except CapabilityRegistrationError:
        return
    raise AssertionError("expected CapabilityRegistrationError for key != descriptor.id")


def test_b_valid_parameters():
    cap = CountingCapability("add", ADD_SCHEMA)
    executor = DefaultCapabilityExecutor({"add": cap})
    obs = executor.execute(Action("add", {"a": 20, "b": 22}), execution_id="e", session_id="s")
    assert isinstance(obs, Success)
    assert obs.data == 42
    assert cap.call_count == 1


def test_c_missing_required():
    cap = CountingCapability("add", ADD_SCHEMA)
    executor = DefaultCapabilityExecutor({"add": cap})
    obs = executor.execute(Action("add", {"a": 20}), execution_id="e", session_id="s")
    assert isinstance(obs, Failure)
    assert "missing required property" in obs.error
    assert cap.call_count == 0


def test_d_wrong_type():
    cap = CountingCapability("add", ADD_SCHEMA)
    executor = DefaultCapabilityExecutor({"add": cap})
    obs = executor.execute(Action("add", {"a": "20", "b": 22}), execution_id="e", session_id="s")
    assert isinstance(obs, Failure)
    assert "expected integer" in obs.error
    assert cap.call_count == 0


def test_e_additional_properties():
    cap = CountingCapability("add", ADD_SCHEMA)
    executor = DefaultCapabilityExecutor({"add": cap})
    obs = executor.execute(Action("add", {"a": 20, "b": 22, "c": 1}), execution_id="e", session_id="s")
    assert isinstance(obs, Failure)
    assert "unexpected property" in obs.error
    assert cap.call_count == 0


def test_f_nested_path_error():
    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "integer"}}},
        "required": ["items"],
    }
    cap = CountingCapability("n", schema)
    executor = DefaultCapabilityExecutor({"n": cap})
    obs = executor.execute(Action("n", {"items": [1, "x", 3]}), execution_id="e", session_id="s")
    assert isinstance(obs, Failure)
    assert "$.items[1]" in obs.error
    assert cap.call_count == 0


def test_g_enum():
    schema = {
        "type": "object",
        "properties": {"mode": {"type": "string", "enum": ["a", "b"]}},
    }
    cap = CountingCapability("e", schema)
    executor = DefaultCapabilityExecutor({"e": cap})
    obs = executor.execute(Action("e", {"mode": "c"}), execution_id="e", session_id="s")
    assert isinstance(obs, Failure)
    assert "not one of" in obs.error
    assert cap.call_count == 0


def test_h_unsupported_schema_keyword():
    try:
        DefaultCapabilityExecutor({"ml": MinLengthCapability()})
    except CapabilityRegistrationError:
        return
    raise AssertionError("expected CapabilityRegistrationError for minLength")


def test_i_unknown_capability():
    executor = DefaultCapabilityExecutor({})
    obs = executor.execute(Action("does_not_exist", {}), execution_id="e", session_id="s")
    assert isinstance(obs, Failure)
    assert "unknown capability" in obs.error


def test_j_capability_raises():
    executor = DefaultCapabilityExecutor({"boom": RaisingCapability()})
    try:
        executor.execute(Action("boom", {}), execution_id="e", session_id="s")
    except CapabilityExecutionError as exc:
        assert exc.capability_id == "boom"
        return
    raise AssertionError("expected CapabilityExecutionError for capability raise")


def test_k_invalid_return():
    executor = DefaultCapabilityExecutor({"bad": BadReturnCapability()})
    try:
        executor.execute(Action("bad", {}), execution_id="e", session_id="s")
    except CapabilityContractError:
        return
    raise AssertionError("expected CapabilityContractError for invalid return")


def test_l_policy_deny_short_circuit():
    cap = CountingCapability("add", ADD_SCHEMA)
    rt = Runtime(AddThenCompleteReasoner(), {"add": cap}, DenyPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("x"))
    assert cap.call_count == 0  # Executor 未被调用
    assert isinstance(final.history[0].policy_verdict, Deny)
    assert final.history[0].observation is None


def test_m_durable_mutation_regression():
    rt = Runtime(AddThenCompleteReasoner(), {"add": MutatingCapability()}, AllowAllPolicy(), domain=RuntimeDomain(state_store=InMemoryStateStore()))
    final = rt.start(Goal("x"))
    assert final.history[0].decision.action.parameters == {"a": 20, "b": 22}


def main() -> None:
    tests = [
        ("A descriptor identity", test_a_descriptor_identity),
        ("B valid parameters", test_b_valid_parameters),
        ("C missing required", test_c_missing_required),
        ("D wrong type", test_d_wrong_type),
        ("E additionalProperties=false", test_e_additional_properties),
        ("F nested path error", test_f_nested_path_error),
        ("G enum", test_g_enum),
        ("H unsupported schema keyword", test_h_unsupported_schema_keyword),
        ("I unknown capability", test_i_unknown_capability),
        ("J capability raises", test_j_capability_raises),
        ("K invalid return", test_k_invalid_return),
        ("L policy deny short-circuit", test_l_policy_deny_short_circuit),
        ("M durable mutation regression", test_m_durable_mutation_regression),
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
    print("\nALL CAPABILITY EXECUTOR TESTS PASSED")


if __name__ == "__main__":
    main()
