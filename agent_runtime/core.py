"""AgentCore：最小 Agent Loop（只负责控制流，不直接调用 Capability）。

Execution Lifecycle（Policy Allow 后）：
  canonical Action snapshot
  → policy.check_action → Allow
  → allocate execution_id
  → 持久化 PendingExecution（prepare save，BEFORE 执行）
  → CapabilityExecutor.execute
  → 构造 settled StepRecord（含 execution_id + observation）
  → policy.should_stop → 继续 / 终止（终止时把 Stop 附着到 step.termination）
  → 单次 settled snapshot commit（history += step，pending=None）

Crash semantics：
  - prepare save 失败 → Capability 不运行（call_count == 0）。
  - settlement save 失败 → durable store 仍保留 pending_execution。
  - resume 遇到 pending_execution → UnresolvedExecutionError（fail-closed，绝不自动重放）。

边界：AgentCore 不 lookup capability、不直接调用 Capability.invoke、不做 input schema
validation、不解析模型协议（tool_call_id / ModelToolCall / DeepSeek）。
"""

from __future__ import annotations

import uuid
from dataclasses import replace

from .contracts import (
    Act,
    Action,
    Allow,
    Blocked,
    CapabilityExecutor,
    Complete,
    Continue,
    Deny,
    Fail,
    ModelCallRecord,
    PendingExecution,
    Policy,
    Reasoner,
    ReasoningResult,
    SessionSnapshot,
    StateStore,
    StepRecord,
    Stop,
)
from .errors import PolicyContractError, ReasonerContractError, UnresolvedExecutionError
from .snapshot import (
    decision_model_call_mismatch,
    snapshot_action,
    snapshot_history,
    snapshot_model_call,
    snapshot_pending_execution,
    snapshot_state,
    validate_session_snapshot,
)


def resolve_step_termination(policy, snapshot, step):
    """post-step termination 语义（normal 与 reconciliation 共享）。

    should_stop → 把 Termination 附着到 step 上（Stop 则写入 step.termination）。
    """
    candidate = SessionSnapshot(
        session_id=snapshot.session_id,
        goal=snapshot.goal,
        state=snapshot.state,
        history=snapshot.history + (step,),
    )
    termination = policy.should_stop(
        snapshot_state(candidate.state),
        snapshot_history(candidate.history),
    )
    if isinstance(termination, Continue):
        return step
    if isinstance(termination, Stop):
        return replace(step, termination=termination)
    raise PolicyContractError(
        f"policy should_stop returned invalid termination: {type(termination).__name__}"
    )


class AgentCore:
    """驱动 Agent Loop 的最小核心，依赖全部构造注入。"""

    def __init__(
        self,
        reasoner: Reasoner,
        capability_executor: CapabilityExecutor,
        policy: Policy,
        state_store: StateStore,
        execution_id_factory=None,
    ) -> None:
        self._reasoner = reasoner
        self._capability_executor = capability_executor
        self._policy = policy
        self._state_store = state_store
        self._execution_id_factory = execution_id_factory or (lambda: uuid.uuid4().hex)

    @staticmethod
    def _validate_reasoning_result(result) -> None:
        """Reasoner 输出 fail-closed：result/decision/terminal payload 必须符合契约。"""
        if not isinstance(result, ReasoningResult):
            raise ReasonerContractError(
                f"Reasoner.decide must return ReasoningResult, got {type(result).__name__}"
            )
        decision = result.decision
        if isinstance(decision, Act):
            action = decision.action
            if (
                not isinstance(action, Action)
                or not isinstance(action.capability_id, str)
                or not action.capability_id
            ):
                raise ReasonerContractError("Act decision must contain a valid Action")
            if not isinstance(action.parameters, dict):
                raise ReasonerContractError("Act Action.parameters must be a dict")
        elif isinstance(decision, Complete):
            if decision.reason is not None and not isinstance(decision.reason, str):
                raise ReasonerContractError("Complete.reason must be None or str")
        elif isinstance(decision, (Fail, Blocked)):
            if not isinstance(decision.reason, str):
                raise ReasonerContractError(
                    f"{type(decision).__name__}.reason must be a str"
                )
        else:
            raise ReasonerContractError(
                f"invalid Decision type: {type(decision).__name__}"
            )
        if result.model_call is not None and not isinstance(
            result.model_call, ModelCallRecord
        ):
            raise ReasonerContractError(
                "ReasoningResult.model_call must be ModelCallRecord or None"
            )
        # native tool facts 必须与 Decision/Action 一致，否则在 Policy/Executor 之前失败
        if isinstance(result.model_call, ModelCallRecord):
            mismatch = decision_model_call_mismatch(result.decision, result.model_call)
            if mismatch:
                raise ReasonerContractError(mismatch)

    def run(self, session_id: str) -> SessionSnapshot:
        """在已存在的 session 上继续运行，返回最终快照（含逐步历史）。"""
        while True:
            snapshot = self._state_store.load(session_id)
            # 每次 authoritative load 都先结构校验 + 身份校验，才能驱动 Reasoner/Policy/Executor
            snapshot = validate_session_snapshot(
                snapshot, expected_session_id=session_id
            )

            # resume gate：unresolved execution → fail-closed，绝不自动重放
            pending = snapshot.pending_execution
            if pending is not None:
                raise UnresolvedExecutionError(
                    session_id=snapshot.session_id,
                    execution_id=pending.execution_id,
                    action=snapshot_action(pending.action),
                )

            result = self._reasoner.decide(
                snapshot.goal,
                snapshot_state(snapshot.state),
                snapshot_history(snapshot.history),
                self._capability_executor.descriptors(),
            )
            self._validate_reasoning_result(result)
            decision = result.decision

            if isinstance(decision, Act):
                snapshot = self._advance(snapshot, decision, result.model_call)
                if snapshot.history[-1].termination is not None:
                    return snapshot
                continue

            # Complete / Fail / Blocked：记录终止 step 并结束 loop。
            step = StepRecord(
                index=len(snapshot.history),
                decision=decision,
                model_call=result.model_call,
            )
            return self._commit(snapshot, step)

    def execute_action(
        self,
        snapshot: SessionSnapshot,
        action: Action,
        *,
        policy_verdict=None,
        execution_id: str | None = None,
    ) -> SessionSnapshot:
        """Run one concrete Action through the existing v0.1 lifecycle.

        Native-tools v2 uses this narrow shared seam for each sibling call.  The
        method does not broaden the v0.1 Reasoner/Decision protocol; it only
        exposes the already-tested single-Action lifecycle to a v2 batch host.
        """
        return self._advance(
            snapshot,
            Act(snapshot_action(action)),
            None,
            prechecked_verdict=policy_verdict,
            execution_id=execution_id,
        )

    def _advance(
        self,
        snapshot: SessionSnapshot,
        decision: Act,
        model_call: ModelCallRecord | None,
        *,
        prechecked_verdict=None,
        execution_id: str | None = None,
    ) -> SessionSnapshot:
        """执行一次 Act：Policy 校验 → (Allow) prepare → execute → settle。"""
        canonical_action = snapshot_action(decision.action)
        index = len(snapshot.history)
        verdict = (
            prechecked_verdict
            if prechecked_verdict is not None
            else self._policy.check_action(
                snapshot_action(canonical_action),
                snapshot_state(snapshot.state),
            )
        )

        if isinstance(verdict, Deny):
            # 不执行能力；Deny 不创建 pending / execution_id。
            step = StepRecord(
                index=index,
                decision=Act(canonical_action),
                policy_verdict=verdict,
                model_call=model_call,
            )
            return self._finalize(snapshot, step)

        if isinstance(verdict, Allow):
            execution_id = execution_id or self._execution_id_factory()
            self._validate_execution_id(snapshot, execution_id)
            pending = PendingExecution(
                execution_id=execution_id,
                step_index=index,
                action=canonical_action,
                model_call=snapshot_model_call(model_call),
            )
            # prepare：在 Capability 可能产生副作用之前，先耐久记录执行意图。
            self._commit_snapshot(self._with_pending(snapshot, pending))

            # execute（execution_id 来自 durable PendingExecution identity；session_id 用于 registry）
            observation = self._capability_executor.execute(
                canonical_action,
                execution_id=execution_id,
                session_id=snapshot.session_id,
            )

            # settle：单次 snapshot commit（history += step，pending=None）
            step = StepRecord(
                index=index,
                decision=Act(canonical_action),
                policy_verdict=verdict,
                observation=observation,
                model_call=model_call,
                execution_id=execution_id,
            )
            return self._finalize(snapshot, step)

        raise PolicyContractError(
            f"policy check_action returned invalid verdict: {type(verdict).__name__}"
        )

    @staticmethod
    def _validate_execution_id(snapshot, execution_id) -> None:
        """prepare 前校验 execution_id 非空且不与 pending / settled history 冲突。"""
        if not isinstance(execution_id, str) or not execution_id:
            raise ValueError("execution_id must be a non-empty string")
        if (
            snapshot.pending_execution is not None
            and snapshot.pending_execution.execution_id == execution_id
        ):
            raise ValueError(
                f"execution_id {execution_id!r} conflicts with pending execution"
            )
        for step in snapshot.history:
            if step.execution_id is not None and step.execution_id == execution_id:
                raise ValueError(
                    f"execution_id {execution_id!r} conflicts with settled history"
                )

    def _finalize(self, snapshot, step) -> SessionSnapshot:
        """终止护栏判定（共享语义）+ 单次 settled snapshot commit。"""
        step = resolve_step_termination(self._policy, snapshot, step)
        next_snapshot = self._append(snapshot, step)
        return self._commit_snapshot(next_snapshot)

    def _with_pending(self, snapshot, pending) -> SessionSnapshot:
        """构造带 pending execution 的快照（history 不变）。"""
        return SessionSnapshot(
            session_id=snapshot.session_id,
            goal=snapshot.goal,
            state=snapshot.state,
            history=snapshot.history,
            pending_execution=snapshot_pending_execution(pending),
            native_tools_v2_turns=snapshot.native_tools_v2_turns,
        )

    def _append(
        self, snapshot: SessionSnapshot, step: StepRecord
    ) -> SessionSnapshot:
        """构造"追加一步后"的新快照（pending 默认清空；不落盘）。"""
        return SessionSnapshot(
            session_id=snapshot.session_id,
            goal=snapshot.goal,
            state=snapshot.state,
            history=snapshot.history + (step,),
            native_tools_v2_turns=snapshot.native_tools_v2_turns,
        )

    def _commit(
        self, snapshot: SessionSnapshot, step: StepRecord
    ) -> SessionSnapshot:
        """追加一步并作为一个检查点原子提交。"""
        next_snapshot = self._append(snapshot, step)
        return self._commit_snapshot(next_snapshot)

    def _commit_snapshot(self, snapshot: SessionSnapshot) -> SessionSnapshot:
        """Core-owned canonical commit boundary：先 validate/canonicalize，再 StateStore.commit。

        保证任何进入任意 StateStore 的 authoritative snapshot 都通过同一 canonical session
        boundary，不依赖具体 Store 实现帮忙兜底结构一致性。
        """
        canonical = validate_session_snapshot(snapshot)
        self._state_store.commit(canonical)
        return canonical
