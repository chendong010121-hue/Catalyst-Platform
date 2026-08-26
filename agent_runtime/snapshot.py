"""Durable Fact Boundary：把数据递归复制为稳定 snapshot。

只接受 JSON-native 数据；runtime object（socket/lock/generator 等）抛 CapabilityContractError。
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping as MappingABC

from .contracts import (
    Act,
    Action,
    Allow,
    Blocked,
    Complete,
    Deny,
    ExecutionReconciliation,
    Fail,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelToolCall,
    ModelUsage,
    NativeToolsV2Call,
    NativeToolsV2FailureAttribution,
    NativeToolsV2RecoveryEvidence,
    NativeToolsV2Turn,
    PendingExecution,
    SessionSnapshot,
    Stop,
    StepRecord,
    Success,
)
from .errors import CapabilityContractError, SessionConsistencyError


def snapshot_value(value):
    """JsonValue contract：只接受 None/bool/int/finite-float/str、list、dict（key 必须 str）。

    明确拒绝 bytes / tuple / set / frozenset / 非 str mapping key / runtime object。
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CapabilityContractError(
                f"non-finite float is not a valid JSON number: {value!r}"
            )
        return value
    if isinstance(value, MappingABC):
        result = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise CapabilityContractError(
                    f"mapping key must be a str, got {type(k).__name__}"
                )
            result[k] = snapshot_value(v)
        return result
    if isinstance(value, list):
        return [snapshot_value(v) for v in value]
    raise CapabilityContractError(
        f"value is not durable: {type(value).__name__} is not a JsonValue"
    )


def snapshot_action(action: Action) -> Action:
    return Action(action.capability_id, snapshot_value(action.parameters))


def snapshot_observation(observation):
    """Observation 的 closed union snapshot：Success / Failure / None，其它 → CapabilityContractError。"""
    if observation is None:
        return None
    if isinstance(observation, Success):
        return Success(snapshot_value(observation.data))
    if isinstance(observation, Failure):
        if not isinstance(observation.error, str):
            raise CapabilityContractError(
                f"Failure.error must be a str, got {type(observation.error).__name__}"
            )
        return Failure(observation.error)
    raise CapabilityContractError(
        f"observation must be Success or Failure, got {type(observation).__name__}"
    )


def snapshot_model_tool_call(call) -> ModelToolCall:
    if not isinstance(call, ModelToolCall):
        raise CapabilityContractError(
            f"model tool call must be a ModelToolCall, got {type(call).__name__}"
        )
    return ModelToolCall(id=call.id, name=call.name, arguments=call.arguments)


def snapshot_message(message):
    if not isinstance(message, Message):
        raise CapabilityContractError(
            f"message must be a Message, got {type(message).__name__}"
        )
    return Message(
        role=message.role,
        content=message.content,
        tool_calls=tuple(snapshot_model_tool_call(c) for c in message.tool_calls),
        tool_call_id=message.tool_call_id,
    )


def snapshot_model_usage(usage):
    """重建 ModelUsage，重新触发 non-negative int / 排除 bool 的 invariant。

    recovery 场景下 corrupt/deserialized ModelUsage 不能靠"恰好是正确 class"绕过，
    因此必须重建而不是直接复用对象。
    """
    if usage is None:
        return None
    if not isinstance(usage, ModelUsage):
        raise CapabilityContractError(
            f"usage must be None or ModelUsage, got {type(usage).__name__}"
        )
    return ModelUsage(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)


def snapshot_model_call(model_call):
    """把 ModelCallRecord 逐字段 canonicalize；非法 nested fact 一律 fail-closed。

    usage/finish_reason/tool_calls/assistant_message 均由 ModelCallRecord.__post_init__
    逐字段校验，非法即 ValueError。这里额外做外层 isinstance 守卫。
    """
    if model_call is None:
        return None
    if not isinstance(model_call, ModelCallRecord):
        raise CapabilityContractError(
            f"model call must be a ModelCallRecord, got {type(model_call).__name__}"
        )
    return ModelCallRecord(
        usage=snapshot_model_usage(model_call.usage),
        finish_reason=model_call.finish_reason,
        tool_calls=tuple(snapshot_model_tool_call(c) for c in model_call.tool_calls),
        assistant_message=(
            snapshot_message(model_call.assistant_message)
            if model_call.assistant_message is not None
            else None
        ),
    )


def snapshot_native_tools_v2_attribution(attribution):
    if attribution is None:
        return None
    if not isinstance(attribution, NativeToolsV2FailureAttribution):
        raise CapabilityContractError(
            "native_tools_v2 failure attribution must be a NativeToolsV2FailureAttribution"
        )
    return NativeToolsV2FailureAttribution(
        stage=attribution.stage,
        owner=attribution.owner,
        failure_type=attribution.failure_type,
        observed_fact=attribution.observed_fact,
        provider_completed=attribution.provider_completed,
        downstream_tool_execution_started=attribution.downstream_tool_execution_started,
        side_effect_certainty=attribution.side_effect_certainty,
        unproven_downstream_boundary=attribution.unproven_downstream_boundary,
        evidence_reference=attribution.evidence_reference,
    )


def snapshot_native_tools_v2_recovery_evidence(event):
    if not isinstance(event, NativeToolsV2RecoveryEvidence):
        raise CapabilityContractError(
            "native_tools_v2 recovery evidence must be a NativeToolsV2RecoveryEvidence"
        )
    return NativeToolsV2RecoveryEvidence(
        kind=event.kind,
        tool_call_id=event.tool_call_id,
        execution_id=event.execution_id,
        source=event.source,
        replayed=event.replayed,
        observed_fact=event.observed_fact,
    )


def snapshot_native_tools_v2_call(call):
    if not isinstance(call, NativeToolsV2Call):
        raise CapabilityContractError("native_tools_v2 call must be a NativeToolsV2Call")
    policy_verdict = call.policy_verdict
    if isinstance(policy_verdict, Allow):
        policy_verdict = Allow()
    elif isinstance(policy_verdict, Deny):
        policy_verdict = Deny(policy_verdict.reason)
    elif policy_verdict is not None:
        raise CapabilityContractError("native_tools_v2 call policy verdict is invalid")
    return NativeToolsV2Call(
        tool_call_id=call.tool_call_id,
        name=call.name,
        arguments=call.arguments,
        action=snapshot_action(call.action) if call.action is not None else None,
        status=call.status,
        policy_verdict=policy_verdict,
        execution_id=call.execution_id,
        observation=snapshot_observation(call.observation),
        uncertainty=call.uncertainty,
    )


def snapshot_native_tools_v2_turn(turn):
    if not isinstance(turn, NativeToolsV2Turn):
        raise CapabilityContractError("native_tools_v2 turn must be a NativeToolsV2Turn")
    return NativeToolsV2Turn(
        turn_id=turn.turn_id,
        model_call=snapshot_model_call(turn.model_call),
        calls=tuple(snapshot_native_tools_v2_call(call) for call in turn.calls),
        next_index=turn.next_index,
        status=turn.status,
        failure_attribution=snapshot_native_tools_v2_attribution(turn.failure_attribution),
        recovery_evidence=tuple(
            snapshot_native_tools_v2_recovery_evidence(event)
            for event in turn.recovery_evidence
        ),
    )


# ---------------------------------------------------------------------------
# native tool facts ↔ Decision/Action 一致性（shared pure validators）
# ---------------------------------------------------------------------------

def json_value_equal(a, b) -> bool:
    """type-aware JSON equality：bool != number（True != 1），递归 dict/list，标量有限数值。"""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        return all(k in b and json_value_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            json_value_equal(x, y) for x, y in zip(a, b)
        )
    return False


def observation_equal(a, b) -> bool:
    """Observation 的 JsonValue-aware equality（Success/Failure）。

    禁止用 Python `==` 作为 execution fact identity，因为 Success(True) == Success(1)
    在 Python 里为 True（bool==int）。这里对 data 用 json_value_equal。
    """
    if isinstance(a, Success) and isinstance(b, Success):
        return json_value_equal(a.data, b.data)
    if isinstance(a, Failure) and isinstance(b, Failure):
        return a.error == b.error
    return False


def action_model_call_mismatch(action, model_call):
    """校验 native tool facts 与 Action 一致；不一致返回错误描述，否则 None。"""
    if model_call is None:
        return None
    tool_calls = model_call.tool_calls
    if not tool_calls:
        return None  # legacy / rule-based：无 native 约束
    if len(tool_calls) != 1:
        return f"native v0.1 requires exactly one tool call, got {len(tool_calls)}"
    call = tool_calls[0]
    if call.name != action.capability_id:
        return (
            f"tool_call.name {call.name!r} != capability_id {action.capability_id!r}"
        )
    try:
        parsed = json.loads(call.arguments)
    except json.JSONDecodeError as exc:
        return f"tool call arguments are not valid JSON: {exc}"
    if not isinstance(parsed, dict):
        return "tool call arguments must be a JSON object"
    if not json_value_equal(parsed, action.parameters):
        return "tool call arguments do not match action.parameters"
    return None


def decision_model_call_mismatch(decision, model_call):
    """Decision 与 native ModelCallRecord.tool_calls 的一致性。"""
    if model_call is None or not model_call.tool_calls:
        return None
    if not isinstance(decision, Act):
        return (
            f"native tool_calls require an Act decision, got {type(decision).__name__}"
        )
    return action_model_call_mismatch(decision.action, model_call)


def snapshot_decision(decision):
    if isinstance(decision, Act):
        return Act(snapshot_action(decision.action))
    return decision  # Complete / Fail / Blocked：reason 为 str


def snapshot_pending_execution(pending):
    if pending is None:
        return None
    return PendingExecution(
        execution_id=pending.execution_id,
        step_index=pending.step_index,
        action=snapshot_action(pending.action),
        model_call=snapshot_model_call(pending.model_call),
    )


def snapshot_execution_reconciliation(reconciliation):
    if reconciliation is None:
        return None
    return ExecutionReconciliation(
        execution_id=reconciliation.execution_id,
        resolution=reconciliation.resolution,
        observation=snapshot_observation(reconciliation.observation),
        note=reconciliation.note,
    )


def _snapshot_verdict(verdict):
    """重建 policy verdict；corrupt payload（如 Deny.reason 非 str）→ fail-closed。"""
    if verdict is None:
        return None
    if isinstance(verdict, Allow):
        return Allow()
    if isinstance(verdict, Deny):
        if not isinstance(verdict.reason, str):
            raise CapabilityContractError(
                f"Deny.reason must be a str, got {type(verdict.reason).__name__}"
            )
        return Deny(verdict.reason)
    raise CapabilityContractError(f"invalid policy verdict: {type(verdict).__name__}")


def _snapshot_termination(termination):
    """重建 termination；corrupt payload（如 Stop.reason 非 str）→ fail-closed。"""
    if termination is None:
        return None
    if isinstance(termination, Stop):
        if not isinstance(termination.reason, str):
            raise CapabilityContractError(
                f"Stop.reason must be a str, got {type(termination.reason).__name__}"
            )
        return Stop(termination.reason)
    raise CapabilityContractError(f"invalid termination: {type(termination).__name__}")


def snapshot_step(step: StepRecord) -> StepRecord:
    return StepRecord(
        index=step.index,
        decision=snapshot_decision(step.decision),
        policy_verdict=_snapshot_verdict(step.policy_verdict),
        observation=snapshot_observation(step.observation),
        model_call=snapshot_model_call(step.model_call),
        termination=_snapshot_termination(step.termination),
        execution_id=step.execution_id,
        reconciliation=snapshot_execution_reconciliation(step.reconciliation),
    )


def snapshot_history(history):
    return tuple(snapshot_step(step) for step in history)


def snapshot_state(state):
    return snapshot_value(dict(state))


def _validate_action(action, session_id, where):
    if not isinstance(action, Action):
        raise SessionConsistencyError(f"{where} must be an Action", session_id=session_id)
    if not isinstance(action.capability_id, str) or not action.capability_id:
        raise SessionConsistencyError(
            f"{where}.capability_id must be a non-empty str", session_id=session_id
        )
    if not isinstance(action.parameters, MappingABC):
        raise SessionConsistencyError(
            f"{where}.parameters must be a Mapping", session_id=session_id
        )
    try:
        snapshot_value(action.parameters)
    except CapabilityContractError as exc:
        raise SessionConsistencyError(
            f"{where}.parameters is not a valid JsonValue: {exc}", session_id=session_id
        ) from exc


def _validate_step(step, position, session_id, settled_execution_ids):
    """校验单步并返回 canonical snapshot；任何结构不一致 → SessionConsistencyError。"""
    if not isinstance(step, StepRecord):
        raise SessionConsistencyError(
            f"history[{position}] is not a StepRecord, got {type(step).__name__}",
            session_id=session_id,
        )
    if isinstance(step.index, bool) or not isinstance(step.index, int) or step.index < 0:
        raise SessionConsistencyError(
            f"history[{position}].index must be a non-negative int, got {step.index!r}",
            session_id=session_id,
        )
    if step.index != position:
        raise SessionConsistencyError(
            f"history[{position}].index {step.index!r} != position {position}",
            session_id=session_id,
        )

    decision = step.decision
    if not isinstance(decision, (Act, Complete, Fail, Blocked)):
        raise SessionConsistencyError(
            f"history[{position}].decision must be Act/Complete/Fail/Blocked, "
            f"got {type(decision).__name__}",
            session_id=session_id,
        )
    if isinstance(decision, Act):
        _validate_action(decision.action, session_id, f"history[{position}].decision.action")
    elif isinstance(decision, Complete):
        if decision.reason is not None and not isinstance(decision.reason, str):
            raise SessionConsistencyError(
                f"history[{position}].decision(Complete).reason must be None or str",
                session_id=session_id,
            )
    else:  # Fail / Blocked
        if not isinstance(decision.reason, str):
            raise SessionConsistencyError(
                f"history[{position}].decision({type(decision).__name__}).reason must be a str",
                session_id=session_id,
            )

    if step.policy_verdict is not None and not isinstance(
        step.policy_verdict, (Allow, Deny)
    ):
        raise SessionConsistencyError(
            f"history[{position}].policy_verdict must be None/Allow/Deny, "
            f"got {type(step.policy_verdict).__name__}",
            session_id=session_id,
        )

    if step.termination is not None and not isinstance(step.termination, Stop):
        raise SessionConsistencyError(
            f"history[{position}].termination must be None/Stop, "
            f"got {type(step.termination).__name__}",
            session_id=session_id,
        )

    # --- StepRecord cross-field semantic consistency（真实 Agent Loop 可产生的合法形态）---
    verdict = step.policy_verdict
    if isinstance(decision, Act):
        if isinstance(verdict, Allow):
            if not isinstance(step.observation, (Success, Failure)):
                raise SessionConsistencyError(
                    f"history[{position}]: Act+Allow must carry a Success/Failure observation",
                    session_id=session_id,
                )
            if not isinstance(step.execution_id, str) or not step.execution_id:
                raise SessionConsistencyError(
                    f"history[{position}]: Act+Allow must carry a non-empty execution_id",
                    session_id=session_id,
                )
        elif isinstance(verdict, Deny):
            if step.observation is not None:
                raise SessionConsistencyError(
                    f"history[{position}]: Act+Deny must not carry an observation",
                    session_id=session_id,
                )
            if step.execution_id is not None:
                raise SessionConsistencyError(
                    f"history[{position}]: Act+Deny must not carry an execution_id",
                    session_id=session_id,
                )
            if step.reconciliation is not None:
                raise SessionConsistencyError(
                    f"history[{position}]: Act+Deny must not carry reconciliation",
                    session_id=session_id,
                )
        else:
            raise SessionConsistencyError(
                f"history[{position}]: Act step must have Allow or Deny policy_verdict, "
                f"got {type(verdict).__name__ if verdict is not None else None}",
                session_id=session_id,
            )
    else:  # Complete / Fail / Blocked：terminal decision 不得携带 execution settlement facts
        if verdict is not None:
            raise SessionConsistencyError(
                f"history[{position}]: terminal decision must not carry policy_verdict",
                session_id=session_id,
            )
        if step.observation is not None:
            raise SessionConsistencyError(
                f"history[{position}]: terminal decision must not carry observation",
                session_id=session_id,
            )
        if step.execution_id is not None:
            raise SessionConsistencyError(
                f"history[{position}]: terminal decision must not carry execution_id",
                session_id=session_id,
            )
        if step.reconciliation is not None:
            raise SessionConsistencyError(
                f"history[{position}]: terminal decision must not carry reconciliation",
                session_id=session_id,
            )
        if step.termination is not None:
            raise SessionConsistencyError(
                f"history[{position}]: terminal decision must not carry termination",
                session_id=session_id,
            )

    # native tool facts 与 decision/action 必须一致（settled recovery validation）
    if isinstance(step.model_call, ModelCallRecord):
        mismatch = decision_model_call_mismatch(step.decision, step.model_call)
        if mismatch:
            raise SessionConsistencyError(
                f"history[{position}]: {mismatch}", session_id=session_id
            )

    if step.execution_id is not None:
        if not isinstance(step.execution_id, str) or not step.execution_id:
            raise SessionConsistencyError(
                f"history[{position}].execution_id must be None or non-empty str",
                session_id=session_id,
            )
        if step.execution_id in settled_execution_ids:
            raise SessionConsistencyError(
                f"duplicate settled execution_id {step.execution_id!r}",
                session_id=session_id,
            )
        settled_execution_ids.append(step.execution_id)

    if step.reconciliation is not None:
        if not isinstance(step.reconciliation, ExecutionReconciliation):
            raise SessionConsistencyError(
                f"history[{position}].reconciliation must be None or ExecutionReconciliation",
                session_id=session_id,
            )
        if step.execution_id is None:
            raise SessionConsistencyError(
                f"history[{position}].reconciliation requires an execution_id",
                session_id=session_id,
            )
        if step.reconciliation.execution_id != step.execution_id:
            raise SessionConsistencyError(
                f"history[{position}].reconciliation.execution_id "
                f"{step.reconciliation.execution_id!r} != step.execution_id {step.execution_id!r}",
                session_id=session_id,
            )
        # 同一 execution 只允许一种 canonical durable outcome（JsonValue-aware equality）
        if not observation_equal(step.observation, step.reconciliation.observation):
            raise SessionConsistencyError(
                f"history[{position}]: reconciliation.observation != step.observation",
                session_id=session_id,
            )

    # canonical snapshot（observation / model_call / reconciliation 逐字段校验，
    # 非法 nested fact 会以 CapabilityContractError/ValueError 抛出）
    try:
        return snapshot_step(step)
    except (CapabilityContractError, ValueError) as exc:
        raise SessionConsistencyError(
            f"history[{position}] failed canonical snapshot: {exc}",
            session_id=session_id,
        ) from exc


def validate_session_snapshot(snapshot, expected_session_id=None) -> SessionSnapshot:
    """StateStore.load 之后的 recovery 结构一致性校验 + 规范化。

    合法 → 返回 canonical defensive snapshot（与调用方 mutation 解耦）；
    非法 → SessionConsistencyError（fail-closed）。不做 migration / repair / reorder / renumber。

    若提供 expected_session_id，则 snapshot.session_id 必须与之一致（跨 Session 防护）。

    校验项：
    - session 是 SessionSnapshot，session_id 非空 str，goal 合法
    - state 是合法 JsonValue（str key / JSON-native）
    - history 有序，step.index == position，逐字段 closed-union
    - settled execution_id 唯一
    - pending None|PendingExecution，step_index == len(history)，execution_id 不与 settled 冲突，Action 合法
    - native tool facts 与 decision/action 一致
    """
    if not isinstance(snapshot, SessionSnapshot):
        raise SessionConsistencyError(
            f"loaded value is not a SessionSnapshot, got {type(snapshot).__name__}"
        )

    session_id = snapshot.session_id
    if not isinstance(session_id, str) or not session_id:
        raise SessionConsistencyError("session_id must be a non-empty str")
    if expected_session_id is not None and session_id != expected_session_id:
        raise SessionConsistencyError(
            f"loaded snapshot.session_id {session_id!r} != requested "
            f"{expected_session_id!r}",
            session_id=session_id,
        )

    if not isinstance(snapshot.goal, Goal):
        raise SessionConsistencyError("goal must be a Goal", session_id=session_id)
    if not isinstance(snapshot.goal.description, str):
        raise SessionConsistencyError(
            "goal.description must be a str", session_id=session_id
        )

    if not isinstance(snapshot.state, MappingABC):
        raise SessionConsistencyError("state must be a Mapping", session_id=session_id)
    try:
        state = snapshot_value(snapshot.state)
    except CapabilityContractError as exc:
        raise SessionConsistencyError(
            f"state is not a valid JsonValue: {exc}", session_id=session_id
        ) from exc

    history = snapshot.history
    if not isinstance(history, (tuple, list)):
        raise SessionConsistencyError(
            "history must be a tuple/list of StepRecord", session_id=session_id
        )

    settled_execution_ids: list = []
    steps = []
    for position, step in enumerate(history):
        steps.append(_validate_step(step, position, session_id, settled_execution_ids))

    # terminal ordering：terminal step（decision ∈ terminal 或 termination 是 Stop）必须是 history tail
    for position, step in enumerate(steps):
        is_terminal = isinstance(step.decision, (Complete, Fail, Blocked)) or isinstance(
            step.termination, Stop
        )
        if is_terminal and position != len(steps) - 1:
            raise SessionConsistencyError(
                f"terminal step at history[{position}] must be the last history step",
                session_id=session_id,
            )

    pending = snapshot.pending_execution
    if pending is not None:
        if not isinstance(pending, PendingExecution):
            raise SessionConsistencyError(
                "pending_execution must be None or PendingExecution", session_id=session_id
            )
        if not isinstance(pending.execution_id, str) or not pending.execution_id:
            raise SessionConsistencyError(
                "pending.execution_id must be a non-empty str", session_id=session_id
            )
        if (
            isinstance(pending.step_index, bool)
            or not isinstance(pending.step_index, int)
            or pending.step_index < 0
        ):
            raise SessionConsistencyError(
                "pending.step_index must be a non-negative int", session_id=session_id
            )
        if pending.step_index != len(steps):
            raise SessionConsistencyError(
                f"pending.step_index {pending.step_index!r} != len(history) {len(steps)}",
                session_id=session_id,
            )
        if pending.execution_id in settled_execution_ids:
            raise SessionConsistencyError(
                f"pending.execution_id {pending.execution_id!r} already settled",
                session_id=session_id,
            )
        _validate_action(pending.action, session_id, "pending.action")
        if pending.model_call is not None:
            try:
                snapshot_model_call(pending.model_call)
            except (CapabilityContractError, ValueError) as exc:
                raise SessionConsistencyError(
                    f"pending.model_call invalid: {exc}", session_id=session_id
                ) from exc
            mismatch = action_model_call_mismatch(pending.action, pending.model_call)
            if mismatch:
                raise SessionConsistencyError(
                    f"pending.action/model_call mismatch: {mismatch}",
                    session_id=session_id,
                )

    native_turns = snapshot.native_tools_v2_turns
    if not isinstance(native_turns, (tuple, list)):
        raise SessionConsistencyError(
            "native_tools_v2_turns must be a tuple/list", session_id=session_id
        )
    try:
        canonical_native_turns = tuple(
            snapshot_native_tools_v2_turn(turn) for turn in native_turns
        )
    except (CapabilityContractError, ValueError) as exc:
        raise SessionConsistencyError(
            f"native_tools_v2_turns failed canonical snapshot: {exc}",
            session_id=session_id,
        ) from exc
    turn_ids = [turn.turn_id for turn in canonical_native_turns]
    if len(turn_ids) != len(set(turn_ids)):
        raise SessionConsistencyError(
            "native_tools_v2_turns turn_id values must be unique", session_id=session_id
        )
    if pending is not None and canonical_native_turns:
        pending_matches = [
            call
            for turn in canonical_native_turns
            for call in turn.calls
            if call.execution_id == pending.execution_id
        ]
        if len(pending_matches) != 1:
            raise SessionConsistencyError(
                "pending v2 execution must match exactly one durable native_tools_v2 call",
                session_id=session_id,
            )

    return SessionSnapshot(
        session_id=session_id,
        goal=snapshot.goal,
        state=state,
        history=tuple(steps),
        pending_execution=snapshot_pending_execution(pending),
        native_tools_v2_turns=canonical_native_turns,
    )


# 向后兼容别名：StateStore ownership isolation 亦复用同一 validator。
snapshot_session = validate_session_snapshot
