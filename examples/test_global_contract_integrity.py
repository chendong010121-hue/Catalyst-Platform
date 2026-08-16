"""Global Contract & Recovery Integrity Hardening 测试。

覆盖审计清单 P0 A–I：
- reconciliation 复用 post-step should_stop（A，StepLimit / TokenBudget 两条 parity）
- 非法 Reasoner Decision / 非法 terminal payload 不进 history
- Observation closed union + Failure.error 必须是 str（snapshot_observation 校验）
- ConfirmedExecuted 非 Observation / ModelUsage bool/negative / DeepSeek 畸形 usage
- JsonValue strict snapshot（bytes/tuple/set/frozenset/非 str key/非 finite float）
- input_schema properties 非 str key 注册拒绝
- Provider json.dumps 序列化失败 → ModelProviderError（不泄露原始 TypeError）
- InMemoryStateStore ownership isolation（commit/load 双向隔离）
"""

from __future__ import annotations

import math
import threading

from agent_runtime.capability_executor import (
    DefaultCapabilityExecutor,
    _validate_schema_supported,
    _SchemaError,
)
from agent_runtime.contracts import (
    Action,
    Act,
    Allow,
    Blocked,
    CapabilityDescriptor,
    Complete,
    ConfirmedExecuted,
    ConfirmedNotExecuted,
    Continue,
    Deny,
    ExecutionReconciliation,
    Fail,
    Failure,
    Goal,
    ModelCallRecord,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelToolDefinition,
    ModelUsage,
    Message,
    ReasoningResult,
    SessionSnapshot,
    StepRecord,
    Stop,
    Success,
)
from agent_runtime.core import AgentCore
from agent_runtime.errors import (
    CapabilityContractError,
    CapabilityRegistrationError,
    ModelProviderError,
    ReasonerContractError,
)
from agent_runtime.llm_reasoner import LLMReasoner
from agent_runtime.policies import StepLimitPolicy, TokenBudgetPolicy
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from agent_runtime.runtime import Runtime
from agent_runtime.snapshot import snapshot_observation, snapshot_value

from .fakes import AllowAllPolicy, InMemoryStateStore, ScriptedModelProvider


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


class AddThenCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        if history:
            return ReasoningResult(decision=Complete(reason="done"))
        return ReasoningResult(decision=Act(Action("add", {"a": 20, "b": 22})))


class CountingReasoner:
    def __init__(self):
        self.decide_calls = 0

    def decide(self, goal, state, history, capabilities):
        self.decide_calls += 1
        return ReasoningResult(decision=Complete(reason="done"))


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


class BadDecisionReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision="not-a-decision")


class BadCompleteReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Complete(reason=123))


class BadActionReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Act(Action("add", [1, 2])))


class ActBadCapabilityReasoner:
    def decide(self, goal, state, history, capabilities):
        return ReasoningResult(decision=Act(Action("bad", {})))


class BadReturnCapability:
    def describe(self):
        return CapabilityDescriptor(id="bad", name="bad", description="", input_schema={})

    def invoke(self, parameters, context):
        return 42  # 非 Success/Failure


class BadFailureCapability:
    def describe(self):
        return CapabilityDescriptor(id="bad", name="bad", description="", input_schema={})

    def invoke(self, parameters, context):
        return Failure(threading.Lock())  # error 非 str


def _pending_store(reasoner, policy=None, exec_id="exec_1"):
    store = RecordingStore(fail_on={2})
    core = AgentCore(
        reasoner=reasoner,
        capability_executor=DefaultCapabilityExecutor({"add": AddCapability()}),
        policy=policy or AllowAllPolicy(),
        state_store=store,
        execution_id_factory=lambda: exec_id,
    )
    store.seed(SessionSnapshot("s", Goal("x"), {}, ()))
    store.save_count = 0
    try:
        core.run("s")
    except RuntimeError:
        pass
    return store


# ---------------------------------------------------------------------------
# A：reconciliation 复用 post-step should_stop（parity）
# ---------------------------------------------------------------------------

def test_a1_step_limit_reconcile_parity():
    store = _pending_store(AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, StepLimitPolicy(1), state_store=store)
    snap = rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))
    step0 = snap.history[0]
    assert isinstance(step0.termination, Stop)
    assert step0.termination.reason == "step limit reached"


def test_a2_token_budget_reconcile_parity():
    provider = ScriptedModelProvider(
        [
            ModelResponse(
                content=None,
                tool_calls=(ModelToolCall("call_1", "add", '{"a":20,"b":22}'),),
                finish_reason="tool_calls",
                usage=ModelUsage(input_tokens=5, output_tokens=3),
            )
        ]
    )
    store = _pending_store(LLMReasoner(provider, decision_protocol="native_tools"))
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, TokenBudgetPolicy(1), state_store=store)
    snap = rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))
    assert isinstance(snap.history[0].termination, Stop)
    assert snap.history[0].termination.reason == "token budget reached"


def test_a3_reconcile_runs_should_stop_but_not_check_action():
    store = _pending_store(AddThenCompleteReasoner())
    reasoner = CountingReasoner()
    policy = CountingPolicy()
    rt = Runtime(reasoner, {"add": AddCapability()}, policy, state_store=store)
    rt.reconcile("s", "exec_1", ConfirmedExecuted(Success(42)))
    assert policy.check_calls == 0  # 原始 Action 早已 Allow，不重复 check
    assert policy.stop_calls == 1  # post-step should_stop 必须重跑


# ---------------------------------------------------------------------------
# B：非法 Reasoner Decision / terminal payload 不进 history
# ---------------------------------------------------------------------------

def _run_reasoner_expect_contract_error(reasoner, error_type):
    store = RecordingStore()
    store.seed(SessionSnapshot("s", Goal("x"), {}, ()))
    core = AgentCore(
        reasoner=reasoner,
        capability_executor=DefaultCapabilityExecutor({"add": AddCapability()}),
        policy=AllowAllPolicy(),
        state_store=store,
    )
    try:
        core.run("s")
    except error_type:
        pass
    else:
        raise AssertionError(f"expected {error_type.__name__}")
    assert store.last_saved().history == ()  # 无任何 step 写入


def test_b1_invalid_decision_type():
    _run_reasoner_expect_contract_error(BadDecisionReasoner(), ReasonerContractError)


def test_b2_invalid_terminal_reason():
    _run_reasoner_expect_contract_error(BadCompleteReasoner(), ReasonerContractError)


def test_b3_act_with_non_dict_parameters():
    _run_reasoner_expect_contract_error(BadActionReasoner(), ReasonerContractError)


def test_b4_reasoning_result_wrong_type():
    class BadResultReasoner:
        def decide(self, goal, state, history, capabilities):
            return "not-a-result"

    _run_reasoner_expect_contract_error(BadResultReasoner(), ReasonerContractError)


def test_b5_invalid_model_call():
    class BadModelCallReasoner:
        def decide(self, goal, state, history, capabilities):
            return ReasoningResult(decision=Complete(reason="x"), model_call=123)

    _run_reasoner_expect_contract_error(BadModelCallReasoner(), ReasonerContractError)


# ---------------------------------------------------------------------------
# C / D：Observation closed union + Failure.error 必须是 str
# ---------------------------------------------------------------------------

def test_c_invalid_observation_not_in_history():
    store = RecordingStore()
    store.seed(SessionSnapshot("s", Goal("x"), {}, ()))
    core = AgentCore(
        reasoner=ActBadCapabilityReasoner(),
        capability_executor=DefaultCapabilityExecutor({"bad": BadReturnCapability()}),
        policy=AllowAllPolicy(),
        state_store=store,
        execution_id_factory=lambda: "exec_1",
    )
    try:
        core.run("s")
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError for non-Observation return")
    saved = store.last_saved()
    assert saved.history == ()  # 无 StepRecord 携带非法 Observation
    assert saved.pending_execution is not None  # unresolved 保留


def test_d_failure_error_runtime_object_not_masked():
    store = RecordingStore()
    store.seed(SessionSnapshot("s", Goal("x"), {}, ()))
    core = AgentCore(
        reasoner=ActBadCapabilityReasoner(),
        capability_executor=DefaultCapabilityExecutor(
            {"bad": BadFailureCapability()}
        ),
        policy=AllowAllPolicy(),
        state_store=store,
        execution_id_factory=lambda: "exec_1",
    )
    try:
        core.run("s")
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError for Failure.error runtime object")


def test_c2_snapshot_observation_closed_union():
    for bad in (123, "err", [], {"e": "x"}, threading.Lock()):
        try:
            snapshot_observation(bad)
        except CapabilityContractError:
            continue
        raise AssertionError(f"snapshot_observation should reject {bad!r}")


def test_d2_snapshot_observation_failure_error_str():
    try:
        snapshot_observation(Failure(threading.Lock()))
    except CapabilityContractError:
        return
    raise AssertionError("snapshot_observation must reject non-str Failure.error")


# ---------------------------------------------------------------------------
# E：ConfirmedExecuted 必须携带 authoritative Observation
# ---------------------------------------------------------------------------

def test_e_confirmed_executed_non_observation():
    store = _pending_store(AddThenCompleteReasoner())
    rt = Runtime(CountingReasoner(), {"add": AddCapability()}, AllowAllPolicy(), state_store=store)
    try:
        rt.reconcile("s", "exec_1", ConfirmedExecuted(123))
    except CapabilityContractError:
        pass
    else:
        raise AssertionError("expected CapabilityContractError for non-Observation")
    assert store.last_saved().pending_execution is not None  # pending 未清


# ---------------------------------------------------------------------------
# F：ModelUsage bool/negative 在构造处拒绝
# ---------------------------------------------------------------------------

def test_f_modelusage_bool_negative():
    for bad in ((True, 5), (5, True), (-1, 5), (5, -1), (1.5, 5), ("5", 3)):
        try:
            ModelUsage(bad[0], bad[1])
        except ValueError:
            continue
        raise AssertionError(f"ModelUsage{bad} should raise ValueError")
    assert ModelUsage(0, 0).total_tokens == 0


def test_f2_goal_deny_stop_reason_str():
    for ctor, arg in ((Goal, 123), (Deny, 123), (Stop, None)):
        try:
            ctor(arg)
        except ValueError:
            continue
        raise AssertionError(f"{ctor.__name__}({arg!r}) should raise ValueError")


def test_f3_execution_reconciliation_post_init():
    try:
        ExecutionReconciliation("", "confirmed_not_executed")
    except ValueError:
        pass
    else:
        raise AssertionError("empty execution_id should raise")
    try:
        ExecutionReconciliation("e", "bad")
    except ValueError:
        pass
    else:
        raise AssertionError("bad resolution should raise")
    try:
        ExecutionReconciliation("e", "confirmed_not_executed", note=123)
    except ValueError:
        pass
    else:
        raise AssertionError("non-str note should raise")
    try:
        ExecutionReconciliation("e", "confirmed_executed", observation=123)
    except ValueError:
        pass
    else:
        raise AssertionError("non-Observation should raise")


# ---------------------------------------------------------------------------
# G：DeepSeek 畸形 usage → ModelProviderError
# ---------------------------------------------------------------------------

def test_g_deepseek_malformed_usage():
    cases = [
        "not-a-dict",
        {"prompt_tokens": True, "completion_tokens": 1},
        {"prompt_tokens": -1, "completion_tokens": 1},
        {"prompt_tokens": "5", "completion_tokens": 1},
        {"prompt_tokens": 5, "completion_tokens": None},
    ]
    for usage in cases:
        try:
            DeepSeekModelProvider._map_usage(usage)
        except ModelProviderError:
            continue
        raise AssertionError(f"_map_usage({usage!r}) should raise ModelProviderError")
    assert DeepSeekModelProvider._map_usage(None) is None
    mapped = DeepSeekModelProvider._map_usage(
        {"prompt_tokens": 5, "completion_tokens": 3}
    )
    assert mapped.input_tokens == 5 and mapped.output_tokens == 3


def test_g2_deepseek_malformed_usage_via_transport():
    provider = DeepSeekModelProvider(
        api_key="k",
        transport=lambda url, headers, body: (
            200,
            {
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": -1, "completion_tokens": 0},
            },
        ),
    )
    req = ModelRequest(messages=[Message(role="system", content="hi")])
    try:
        provider.request(req)
    except ModelProviderError:
        return
    raise AssertionError("expected ModelProviderError for malformed usage")


# ---------------------------------------------------------------------------
# H：JsonValue strict snapshot
# ---------------------------------------------------------------------------

def test_h_jsonvalue_rejects():
    bad_values = [
        b"bytes",
        (1, 2),
        {1, 2},
        frozenset({1, 2}),
        {1: "non-str key"},
        math.inf,
        math.nan,
        object(),
    ]
    for value in bad_values:
        try:
            snapshot_value(value)
        except CapabilityContractError:
            continue
        raise AssertionError(f"snapshot_value({value!r}) should raise CapabilityContractError")


def test_h2_jsonvalue_accepts():
    ok = {
        "none": None,
        "bool": True,
        "int": 1,
        "float": 1.5,
        "str": "x",
        "list": [1, {"a": [2, 3.5]}],
        "nested": {"k": "v"},
    }
    assert snapshot_value(ok) == ok


# ---------------------------------------------------------------------------
# I：input_schema properties 非 str key 注册拒绝
# ---------------------------------------------------------------------------

def test_i_schema_properties_non_str_key():
    try:
        _validate_schema_supported(
            {"type": "object", "properties": {1: {"type": "integer"}}}
        )
    except _SchemaError:
        pass
    else:
        raise AssertionError("_validate_schema_supported should reject non-str property key")


def test_i2_schema_properties_non_str_key_registration():
    class NonStrPropCapability:
        def describe(self):
            return CapabilityDescriptor(
                id="nsp",
                name="nsp",
                description="",
                input_schema={
                    "type": "object",
                    "properties": {1: {"type": "integer"}},
                },
            )

        def invoke(self, parameters, context):
            return Success(None)

    try:
        DefaultCapabilityExecutor({"nsp": NonStrPropCapability()})
    except CapabilityRegistrationError:
        return
    raise AssertionError("expected CapabilityRegistrationError for non-str property key")


# ---------------------------------------------------------------------------
# J：ModelToolDefinition.parameters 拒绝 runtime object（构造 fail-fast）
# ---------------------------------------------------------------------------

def test_j_model_tool_definition_rejects_runtime_object():
    # runtime object 现在在 ModelToolDefinition 构造期即被拒绝，根本到不了
    # Provider 的 json.dumps（provider 层 json.dumps 的 try/except 只是防御纵深）。
    try:
        ModelToolDefinition("t", "d", {"x": threading.Lock()})
    except ValueError:
        return
    raise AssertionError("expected ValueError for runtime object in tool parameters")


# ---------------------------------------------------------------------------
# K：InMemoryStateStore ownership isolation
# ---------------------------------------------------------------------------

def test_k_inmemory_store_isolation_state():
    store = InMemoryStateStore()
    snap = SessionSnapshot("s", Goal("x"), {"n": 1}, ())
    store.commit(snap)
    snap.state["n"] = 999  # 篡改已提交对象
    assert store.load("s").state["n"] == 1  # 存储不受影响


def test_k2_inmemory_store_isolation_loaded():
    store = InMemoryStateStore()
    store.commit(SessionSnapshot("s", Goal("x"), {"n": 1}, ()))
    loaded = store.load("s")
    loaded.state["n"] = 999  # 篡改已加载对象
    assert store.load("s").state["n"] == 1  # 再次 load 仍干净


def test_k3_inmemory_store_isolation_deep_history():
    store = InMemoryStateStore()
    snap = SessionSnapshot(
        "s",
        Goal("x"),
        {},
        (
            StepRecord(
                index=0,
                decision=Act(Action("add", {"a": 1})),
                policy_verdict=Allow(),
                observation=Success({"result": [1, 2, 3]}),
                execution_id="exec_0",
            ),
        ),
    )
    store.commit(snap)
    loaded = store.load("s")
    loaded.history[0].observation.data["result"].append(99)
    assert store.load("s").history[0].observation.data["result"] == [1, 2, 3]


def main() -> None:
    tests = [
        ("A1 step-limit reconcile parity", test_a1_step_limit_reconcile_parity),
        ("A2 token-budget reconcile parity", test_a2_token_budget_reconcile_parity),
        ("A3 reconcile should_stop not check_action", test_a3_reconcile_runs_should_stop_but_not_check_action),
        ("B1 invalid decision type", test_b1_invalid_decision_type),
        ("B2 invalid terminal reason", test_b2_invalid_terminal_reason),
        ("B3 act non-dict parameters", test_b3_act_with_non_dict_parameters),
        ("B4 reasoning result wrong type", test_b4_reasoning_result_wrong_type),
        ("B5 invalid model_call", test_b5_invalid_model_call),
        ("C invalid observation not in history", test_c_invalid_observation_not_in_history),
        ("D Failure.error runtime object not masked", test_d_failure_error_runtime_object_not_masked),
        ("C2 snapshot_observation closed union", test_c2_snapshot_observation_closed_union),
        ("D2 snapshot_observation Failure.error str", test_d2_snapshot_observation_failure_error_str),
        ("E ConfirmedExecuted non-observation", test_e_confirmed_executed_non_observation),
        ("F ModelUsage bool/negative", test_f_modelusage_bool_negative),
        ("F2 Goal/Deny/Stop reason str", test_f2_goal_deny_stop_reason_str),
        ("F3 ExecutionReconciliation post_init", test_f3_execution_reconciliation_post_init),
        ("G DeepSeek malformed usage", test_g_deepseek_malformed_usage),
        ("G2 DeepSeek malformed usage via transport", test_g2_deepseek_malformed_usage_via_transport),
        ("H JsonValue rejects", test_h_jsonvalue_rejects),
        ("H2 JsonValue accepts", test_h2_jsonvalue_accepts),
        ("I schema properties non-str key", test_i_schema_properties_non_str_key),
        ("I2 schema non-str key registration", test_i2_schema_properties_non_str_key_registration),
        ("J ModelToolDefinition rejects runtime object", test_j_model_tool_definition_rejects_runtime_object),
        ("K1 store isolation committed", test_k_inmemory_store_isolation_state),
        ("K2 store isolation loaded", test_k2_inmemory_store_isolation_loaded),
        ("K3 store isolation deep history", test_k3_inmemory_store_isolation_deep_history),
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
    print("\nALL GLOBAL CONTRACT & RECOVERY INTEGRITY TESTS PASSED")


if __name__ == "__main__":
    main()
