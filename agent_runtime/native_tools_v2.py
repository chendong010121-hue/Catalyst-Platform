"""Replaceable native-tools v2 interaction path.

This module owns model-turn batching only.  Each concrete Action is handed to
the existing AgentCore single-action lifecycle; v0.1 is not widened here.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from typing import Sequence

from .contracts import (
    Act,
    Action,
    Allow,
    Blocked,
    CapabilityDescriptor,
    Complete,
    Deny,
    Fail,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelToolDefinition,
    NativeToolsV2Call,
    NativeToolsV2FailureAttribution,
    NativeToolsV2RecoveryEvidence,
    NativeToolsV2Turn,
    SessionSnapshot,
    State,
    StepRecord,
    Success,
)
from .errors import UnresolvedExecutionError
from .runtime import Runtime
from .snapshot import json_value_equal, snapshot_action, validate_session_snapshot


_NATIVE_SYSTEM_PROMPT = (
    "You are an agent. Use the supplied tools when needed. "
    "When a tool result gives you enough information, answer directly. "
    "Do not invent tool results."
)


def _render_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _is_terminal(snapshot: SessionSnapshot) -> bool:
    if not snapshot.history:
        return False
    last = snapshot.history[-1]
    return isinstance(last.decision, (Complete, Fail, Blocked)) or last.termination is not None


def _tool_result_text(call: NativeToolsV2Call) -> str:
    if isinstance(call.policy_verdict, Deny):
        return f"Tool call denied by policy: {call.policy_verdict.reason}"
    if call.status == "skipped":
        return "Tool call not executed because the v2 batch stopped fail-closed after a sibling result."
    if call.status == "invalid":
        return "Tool call rejected because its arguments were malformed; no capability was executed."
    if call.uncertainty is not None:
        return f"Tool execution outcome is uncertain: {call.uncertainty}"
    if isinstance(call.observation, Failure):
        return f"Tool execution failed: {call.observation.error}"
    if isinstance(call.observation, Success):
        return _render_json(call.observation.data)
    return "null"


@dataclass(frozen=True)
class NativeToolsV2TurnResult:
    model_call: ModelCallRecord
    turn: NativeToolsV2Turn | None = None
    decision: Complete | None = None
    protocol_error: "NativeToolsV2ProtocolError | None" = None


class NativeToolsV2ProtocolError(Exception):
    """Provider/model turn cannot be represented or safely executed by v2."""

    def __init__(self, message: str, attribution: NativeToolsV2FailureAttribution):
        super().__init__(message)
        self.attribution = attribution


class NativeToolsV2Reasoner:
    """Provider-neutral model-turn parser accepting zero or more tool calls."""

    def __init__(self, model_provider: ModelProvider):
        self._model_provider = model_provider

    def decide_turn(
        self,
        goal: Goal,
        state: State,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
        turns: Sequence[NativeToolsV2Turn],
    ) -> NativeToolsV2TurnResult:
        request = self._build_request(goal, history, capabilities, turns)
        response = self._model_provider.request(request)
        model_call = self._model_call(response)

        if not response.tool_calls:
            if response.finish_reason == "tool_calls":
                raise self._protocol_error(
                    "finish_reason 'tool_calls' but no tool_calls",
                    "empty tool-call set with tool_calls finish reason",
                )
            if not response.content or not response.content.strip():
                raise self._protocol_error(
                    "empty model response (no content and no tool calls)",
                    "provider completed without content or tool calls",
                )
            if response.finish_reason not in (None, "stop"):
                raise self._protocol_error(
                    f"final text requires finish_reason 'stop' or None, got {response.finish_reason!r}",
                    f"final text with finish_reason={response.finish_reason!r}",
                )
            return NativeToolsV2TurnResult(model_call=model_call, decision=Complete(response.content))

        calls: list[NativeToolsV2Call] = []
        invalid: list[str] = []
        for raw_call in response.tool_calls:
            action = None
            status = "pending"
            try:
                parameters = json.loads(raw_call.arguments)
                if not isinstance(parameters, dict):
                    raise ValueError("tool call arguments must be a JSON object")
                action = Action(raw_call.name, parameters)
            except (json.JSONDecodeError, ValueError) as exc:
                status = "invalid"
                invalid.append(f"{raw_call.id}: {exc}")
            calls.append(
                NativeToolsV2Call(
                    tool_call_id=raw_call.id,
                    name=raw_call.name,
                    arguments=raw_call.arguments,
                    action=action,
                    status=status,
                )
            )

        attribution = None
        protocol_error = None
        status = "executing"
        if invalid:
            attribution = NativeToolsV2FailureAttribution(
                stage="native_model_interaction",
                owner="Harness native-tools v2 interaction",
                failure_type="malformed_tool_arguments",
                observed_fact="; ".join(invalid),
                provider_completed=True,
                downstream_tool_execution_started=False,
                side_effect_certainty="none",
                unproven_downstream_boundary="Capability execution",
            )
            status = "failed"
            protocol_error = NativeToolsV2ProtocolError(
                "one or more tool call arguments are malformed", attribution
            )

        turn = NativeToolsV2Turn(
            turn_id=uuid.uuid4().hex,
            model_call=model_call,
            calls=tuple(calls),
            status=status,
            failure_attribution=attribution,
        )
        return NativeToolsV2TurnResult(
            model_call=model_call,
            turn=turn,
            protocol_error=protocol_error,
        )

    def _build_request(
        self,
        goal: Goal,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
        turns: Sequence[NativeToolsV2Turn],
    ) -> ModelRequest:
        tools = tuple(
            ModelToolDefinition(
                name=capability.id,
                description=capability.description,
                parameters=dict(capability.input_schema),
            )
            for capability in capabilities
        )
        messages = [
            Message(role="system", content=_NATIVE_SYSTEM_PROMPT),
            Message(role="user", content=goal.description),
        ]
        for turn in turns:
            if turn.status not in ("completed", "blocked", "failed"):
                continue
            assistant = turn.model_call.assistant_message
            if assistant is None:
                assistant = Message(
                    role="assistant",
                    content=None,
                    tool_calls=tuple(turn.model_call.tool_calls),
                )
            messages.append(assistant)
            messages.extend(
                Message(
                    role="tool",
                    content=_tool_result_text(call),
                    tool_call_id=call.tool_call_id,
                )
                for call in turn.calls
            )
        return ModelRequest(
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
        )

    @staticmethod
    def _model_call(response: ModelResponse) -> ModelCallRecord:
        assistant = None
        if response.tool_calls:
            assistant = Message(
                role="assistant",
                content=response.content,
                tool_calls=tuple(response.tool_calls),
            )
        return ModelCallRecord(
            usage=response.usage,
            finish_reason=response.finish_reason,
            tool_calls=response.tool_calls,
            assistant_message=assistant,
        )

    @staticmethod
    def _protocol_error(message: str, observed_fact: str) -> NativeToolsV2ProtocolError:
        attribution = NativeToolsV2FailureAttribution(
            stage="native_model_interaction",
            owner="Harness native-tools v2 interaction",
            failure_type="unsupported_model_turn_shape",
            observed_fact=observed_fact,
            provider_completed=True,
            downstream_tool_execution_started=False,
            side_effect_certainty="none",
            unproven_downstream_boundary="Capability execution",
        )
        return NativeToolsV2ProtocolError(message, attribution)


class NativeToolsV2Runtime(Runtime):
    """Runtime host for v2 model-turn batches; v0.1 Runtime path remains selectable."""

    def __init__(self, reasoner, capabilities, policy, state_store, *, timeout_config=None):
        if not isinstance(reasoner, NativeToolsV2Reasoner):
            raise TypeError("NativeToolsV2Runtime requires NativeToolsV2Reasoner")
        super().__init__(
            reasoner=reasoner,
            capabilities=capabilities,
            policy=policy,
            state_store=state_store,
            timeout_config=timeout_config,
        )
        self._v2_reasoner = reasoner

    def run(self, session_id: str) -> SessionSnapshot:
        snapshot = validate_session_snapshot(
            self._state_store.load(session_id), expected_session_id=session_id
        )
        if snapshot.pending_execution is not None:
            pending = snapshot.pending_execution
            raise UnresolvedExecutionError(
                session_id=snapshot.session_id,
                execution_id=pending.execution_id,
                action=snapshot_action(pending.action),
            )
        if _is_terminal(snapshot):
            return snapshot
        return self._run_v2(session_id)

    def reconcile(self, session_id: str, execution_id: str, resolution):
        snapshot = super().reconcile(session_id, execution_id, resolution)
        turns = list(snapshot.native_tools_v2_turns)
        for turn_index, turn in enumerate(turns):
            for call_index, call in enumerate(turn.calls):
                if call.execution_id != execution_id:
                    continue
                settled_call = replace(
                    call,
                    status="settled",
                    observation=snapshot.history[-1].observation,
                    uncertainty=None,
                )
                calls = list(turn.calls)
                calls[call_index] = settled_call
                for index in range(call_index + 1, len(calls)):
                    calls[index] = replace(calls[index], status="skipped")
                attribution = NativeToolsV2FailureAttribution(
                    stage="execution_reconciliation",
                    owner="Catalyst execution certainty boundary",
                    failure_type="execution_uncertain_reconciled",
                    observed_fact="pending sibling execution was explicitly reconciled",
                    provider_completed=True,
                    downstream_tool_execution_started=True,
                    side_effect_certainty="explicitly reconciled",
                    unproven_downstream_boundary="later sibling calls",
                )
                turns[turn_index] = replace(
                    turn,
                    calls=tuple(calls),
                    next_index=len(calls),
                    status="blocked",
                    failure_attribution=attribution,
                )
                snapshot = replace(snapshot, native_tools_v2_turns=tuple(turns))
                self._commit(snapshot)
                return snapshot
        return snapshot

    def _run_v2(self, session_id: str) -> SessionSnapshot:
        while True:
            snapshot = validate_session_snapshot(
                self._state_store.load(session_id), expected_session_id=session_id
            )
            active = self._active_turn(snapshot)
            if active is not None:
                if active.status == "executing":
                    snapshot = self._execute_next_call(snapshot, active)
                    if snapshot.history and isinstance(snapshot.history[-1].decision, (Fail, Blocked)):
                        return snapshot
                    continue
            result = self._v2_reasoner.decide_turn(
                snapshot.goal,
                snapshot.state,
                snapshot.history,
                self._core._capability_executor.descriptors(),
                snapshot.native_tools_v2_turns,
            )
            if result.turn is not None:
                snapshot = replace(
                    snapshot,
                    native_tools_v2_turns=snapshot.native_tools_v2_turns + (result.turn,),
                )
                self._commit(snapshot)
                if result.protocol_error is not None:
                    raise result.protocol_error
                continue
            step = StepRecord(
                index=len(snapshot.history),
                decision=result.decision,
                model_call=result.model_call,
            )
            snapshot = replace(snapshot, history=snapshot.history + (step,))
            return self._commit(snapshot)

    def _execute_next_call(self, snapshot: SessionSnapshot, turn: NativeToolsV2Turn):
        index = next(
            (index for index, call in enumerate(turn.calls) if call.status == "pending"),
            None,
        )
        if index is None:
            completed = replace(turn, next_index=len(turn.calls), status="completed")
            return self._commit(self._replace_turn(snapshot, completed))
        call = turn.calls[index]
        if call.action is None:
            raise NativeToolsV2ProtocolError(
                "pending v2 call has no parsed Action",
                turn.failure_attribution
                or NativeToolsV2FailureAttribution(
                    stage="native_model_interaction",
                    owner="Harness native-tools v2 interaction",
                    failure_type="missing_action",
                    observed_fact=call.tool_call_id,
                    provider_completed=True,
                    downstream_tool_execution_started=False,
                    side_effect_certainty="none",
                    unproven_downstream_boundary="Capability execution",
                ),
            )

        if call.execution_id is not None:
            settled_step = next(
                (
                    step
                    for step in snapshot.history
                    if step.execution_id == call.execution_id
                ),
                None,
            )
            if settled_step is not None:
                if not isinstance(settled_step.decision, Act) or not self._same_action(
                    call.action, settled_step.decision.action
                ):
                    return self._fail_recovery(
                        snapshot,
                        turn,
                        index,
                        "execution_id_action_mismatch",
                        (
                            f"execution_id {call.execution_id!r} is already present in "
                            "authoritative history but its Action identity does not match "
                            f"tool_call_id {call.tool_call_id!r}"
                        ),
                    )
                if not isinstance(settled_step.policy_verdict, Allow) or not isinstance(
                    settled_step.observation, (Success, Failure)
                ):
                    return self._fail_recovery(
                        snapshot,
                        turn,
                        index,
                        "invalid_settled_history_for_recovery",
                        (
                            f"execution_id {call.execution_id!r} matched Action identity but "
                            "the settled StepRecord lacks an Allow verdict or Observation"
                        ),
                    )
                recovered_call = replace(
                    call,
                    status="settled",
                    policy_verdict=Allow(),
                    observation=settled_step.observation,
                    uncertainty=None,
                )
                recovery = NativeToolsV2RecoveryEvidence(
                    kind="settled_history_recovered",
                    tool_call_id=call.tool_call_id,
                    execution_id=call.execution_id,
                    source="authoritative_history",
                    replayed=False,
                    observed_fact=(
                        "v2 pending call recovered from matching settled Core history; "
                        "Capability was not replayed"
                    ),
                )
                recovered_turn = self._replace_call(turn, index, recovered_call)
                recovered_turn = replace(
                    recovered_turn,
                    next_index=index + 1,
                    recovery_evidence=turn.recovery_evidence + (recovery,),
                )
                return self._commit(self._replace_turn(snapshot, recovered_turn))

        verdict = self._policy.check_action(snapshot_action(call.action), snapshot.state)
        if isinstance(verdict, Allow):
            execution_id = call.execution_id or uuid.uuid4().hex
            prepared_call = replace(call, policy_verdict=Allow(), execution_id=execution_id)
            prepared_turn = self._replace_call(turn, index, prepared_call)
            prepared_snapshot = self._commit(self._replace_turn(snapshot, prepared_turn))
            settled_snapshot = self._core.execute_action(
                prepared_snapshot,
                call.action,
                policy_verdict=Allow(),
                execution_id=execution_id,
            )
            observation = settled_snapshot.history[-1].observation
            settled_call = replace(
                prepared_call,
                status="settled",
                observation=observation,
            )
            settled_turn = self._replace_call(
                prepared_turn,
                index,
                settled_call,
            )
            settled_turn = replace(settled_turn, next_index=index + 1)
            if isinstance(observation, Failure):
                return self._halt_batch(
                    settled_snapshot,
                    settled_turn,
                    "known_capability_failure_batch_halted",
                    "known Observation.Failure halted later sibling calls",
                )
            return self._commit(self._replace_turn(settled_snapshot, settled_turn))

        if isinstance(verdict, Deny):
            denied_call = replace(call, status="denied", policy_verdict=Deny(verdict.reason))
            denied_turn = self._replace_call(turn, index, denied_call)
            denied_snapshot = self._commit(self._replace_turn(snapshot, denied_turn))
            settled_snapshot = self._core.execute_action(
                denied_snapshot,
                call.action,
                policy_verdict=Deny(verdict.reason),
            )
            return self._halt_batch(
                settled_snapshot,
                denied_turn,
                "policy_denied_batch_halted",
                "policy Deny halted later sibling calls in this v2 batch",
            )
        raise TypeError(f"invalid policy verdict: {type(verdict).__name__}")

    @staticmethod
    def _same_action(left: Action, right: Action) -> bool:
        return left.capability_id == right.capability_id and json_value_equal(
            left.parameters, right.parameters
        )

    def _fail_recovery(
        self,
        snapshot: SessionSnapshot,
        turn: NativeToolsV2Turn,
        index: int,
        failure_type: str,
        observed_fact: str,
    ):
        attribution = NativeToolsV2FailureAttribution(
            stage="native_tool_batch_recovery",
            owner="Harness native-tools v2 recovery",
            failure_type=failure_type,
            observed_fact=observed_fact,
            provider_completed=True,
            downstream_tool_execution_started=False,
            side_effect_certainty="authoritative history was not safely reusable",
            unproven_downstream_boundary="Capability execution for the mismatched call",
        )
        failed_turn = replace(
            turn,
            next_index=index,
            status="failed",
            failure_attribution=attribution,
        )
        self._commit(self._replace_turn(snapshot, failed_turn))
        raise NativeToolsV2ProtocolError(
            "v2 execution recovery failed closed: " + observed_fact,
            attribution,
        )

    def _halt_batch(self, snapshot, turn, failure_type: str, observed_fact: str):
        calls = [
            replace(call, status="skipped") if call.status == "pending" else call
            for call in turn.calls
        ]
        attribution = NativeToolsV2FailureAttribution(
            stage="native_tool_batch_execution",
            owner="Harness native-tools v2 batch policy",
            failure_type=failure_type,
            observed_fact=observed_fact,
            provider_completed=True,
            downstream_tool_execution_started=any(call.execution_id for call in calls),
            side_effect_certainty="known for settled calls",
            unproven_downstream_boundary="skipped sibling calls",
        )
        blocked = replace(
            turn,
            calls=tuple(calls),
            next_index=len(calls),
            status="blocked",
            failure_attribution=attribution,
        )
        snapshot = self._commit(self._replace_turn(snapshot, blocked))
        step = StepRecord(
            index=len(snapshot.history),
            decision=Fail(observed_fact),
        )
        return self._commit(replace(snapshot, history=snapshot.history + (step,)))

    @staticmethod
    def _active_turn(snapshot):
        for turn in reversed(snapshot.native_tools_v2_turns):
            if turn.status == "executing":
                return turn
        return None

    @staticmethod
    def _replace_turn(snapshot, turn):
        turns = list(snapshot.native_tools_v2_turns)
        for index in range(len(turns) - 1, -1, -1):
            if turns[index].turn_id == turn.turn_id:
                turns[index] = turn
                return replace(snapshot, native_tools_v2_turns=tuple(turns))
        raise ValueError(f"v2 turn {turn.turn_id!r} is not in the session snapshot")

    @staticmethod
    def _replace_call(turn, index, call):
        calls = list(turn.calls)
        calls[index] = call
        return replace(turn, calls=tuple(calls))

    def _commit(self, snapshot):
        canonical = validate_session_snapshot(snapshot)
        self._state_store.commit(canonical)
        return canonical


__all__ = [
    "NativeToolsV2ProtocolError",
    "NativeToolsV2Reasoner",
    "NativeToolsV2Runtime",
]
