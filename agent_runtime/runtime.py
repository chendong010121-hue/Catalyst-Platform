"""Runtime：宿主 / 生命周期 / 组合根（生命周期加固）。

生命周期 API：
- create(goal)        → 生成 id、建初始快照、持久化、返回快照（不调 AgentCore）
- run(session_id)     → load + 结构校验 + pending gate + terminal 检查 + AgentCore.run
- resume(session_id)  → run 的别名，语义相同
- start(goal)         → create + run；run 失败抛 RuntimeExecutionError（携带 session_id）
- reconcile(session_id, execution_id, resolution) → load + 结构校验 + 显式 recovery

recovery 顺序（run / resume / reconcile 共用）：
    load → validate_session_snapshot → pending gate → terminal / execution

组合：
- Capability 注册不变量（key==descriptor.id、schema 支持）由 DefaultCapabilityExecutor 校验。
- Runtime 只装配：executor = DefaultCapabilityExecutor(capabilities)；core = AgentCore(reasoner, executor, policy, state_store)。

失败边界：
- Capability 执行失败由 CapabilityExecutor 归一化为 Observation.Failure。
- Reasoner / ModelProvider / Policy 契约违反 / Capability 契约违反 / StateStore
  失败均作为 infrastructure failure 向调用方传播，不伪装成 Capability Failure。
"""

from __future__ import annotations

import uuid
from typing import Mapping

from .capability_executor import DefaultCapabilityExecutor
from .contracts import (
    Act,
    Allow,
    Blocked,
    Capability,
    Complete,
    ConfirmedExecuted,
    ConfirmedNotExecuted,
    ExecutionReconciliation,
    Fail,
    Failure,
    Goal,
    Policy,
    Reasoner,
    SessionSnapshot,
    StateStore,
    StepRecord,
    Stop,
)
from .core import AgentCore, resolve_step_termination
from .errors import ReconciliationError, RuntimeExecutionError, UnresolvedExecutionError
from .snapshot import (
    snapshot_action,
    snapshot_execution_reconciliation,
    snapshot_model_call,
    snapshot_observation,
    validate_session_snapshot,
)


def _is_terminal(snapshot: SessionSnapshot) -> bool:
    """terminal 定义：最后一步 decision ∈ {Complete, Fail, Blocked} 或 termination 是 Stop。"""
    if not snapshot.history:
        return False
    last = snapshot.history[-1]
    if isinstance(last.decision, (Complete, Fail, Blocked)):
        return True
    return isinstance(last.termination, Stop)


class Runtime:
    """组合根：装配 AgentCore 及其依赖，管理 Session 生命周期。"""

    def __init__(
        self,
        reasoner: Reasoner,
        capabilities: Mapping[str, Capability],
        policy: Policy,
        state_store: StateStore,
    ) -> None:
        self._reasoner = reasoner
        self._capabilities = capabilities
        self._policy = policy
        self._state_store = state_store
        executor = DefaultCapabilityExecutor(capabilities)
        self._core = AgentCore(reasoner, executor, policy, state_store)

    def create(self, goal: Goal) -> SessionSnapshot:
        """创建新 Session（唯一 id）并持久化初始快照；不调用 AgentCore。"""
        session_id = uuid.uuid4().hex
        snapshot = SessionSnapshot(session_id, goal, {}, ())
        # canonical authoritative commit boundary：validate-before-commit，不依赖 Store 兜底
        canonical = validate_session_snapshot(snapshot, expected_session_id=session_id)
        self._state_store.commit(canonical)
        return canonical

    def run(self, session_id: str) -> SessionSnapshot:
        """在已存在的 session 上运行；terminal 直接返回，否则交 Core 继续。"""
        snapshot = self._state_store.load(session_id)
        # recovery 结构/身份校验必须先于任何 pending/terminal/Reasoner 行为
        snapshot = validate_session_snapshot(snapshot, expected_session_id=session_id)
        # pending gate 优先于 terminal fast-path：unresolved 绝不能因 terminal 被隐藏
        if snapshot.pending_execution is not None:
            pending = snapshot.pending_execution
            raise UnresolvedExecutionError(
                session_id=snapshot.session_id,
                execution_id=pending.execution_id,
                action=pending.action,
            )
        if _is_terminal(snapshot):
            return snapshot
        return self._core.run(session_id)

    def resume(self, session_id: str) -> SessionSnapshot:
        """run 的别名，语义相同。"""
        return self.run(session_id)

    def reconcile(self, session_id: str, execution_id: str, resolution) -> SessionSnapshot:
        """把 unresolved pending execution 显式 reconciliation 为 durable settled step。

        不调用 Reasoner / CapabilityExecutor / Capability / ModelProvider；
        不调用 Policy.check_action（原始 Action 早已 Allow）；
        但会调用 Policy.should_stop（复用 resolve_step_termination，保持 post-step termination parity）。
        成功返回 settled snapshot，不自动 resume。
        """
        snapshot = self._state_store.load(session_id)
        # recovery 结构/身份校验：malformed/跨 Session pending 必须 fail-closed，不能 settle 进 history
        snapshot = validate_session_snapshot(snapshot, expected_session_id=session_id)
        pending = snapshot.pending_execution
        if pending is None:
            raise ReconciliationError("session has no pending execution")
        if pending.execution_id != execution_id:
            raise ReconciliationError(
                f"execution_id mismatch: got {execution_id!r}, expected {pending.execution_id!r}"
            )
        if pending.step_index != len(snapshot.history):
            raise ReconciliationError(
                f"pending.step_index {pending.step_index} != len(history) {len(snapshot.history)}"
            )
        for step in snapshot.history:
            if step.execution_id is not None and step.execution_id == execution_id:
                raise ReconciliationError(
                    f"execution_id {execution_id!r} already settled"
                )

        if isinstance(resolution, ConfirmedNotExecuted):
            resolution_str = "confirmed_not_executed"
            observation = Failure(
                "execution reconciliation confirmed: capability did not execute"
            )
            note = resolution.note
        elif isinstance(resolution, ConfirmedExecuted):
            resolution_str = "confirmed_executed"
            observation = resolution.observation
            note = resolution.note
        else:
            raise ReconciliationError(f"invalid resolution: {type(resolution).__name__}")

        # durable snapshot（unsnapshotable observation 在此 fail-fast，pending 不清）
        observation = snapshot_observation(observation)

        reconciliation = ExecutionReconciliation(
            execution_id=execution_id,
            resolution=resolution_str,
            observation=observation,
            note=note,
        )

        step = StepRecord(
            index=pending.step_index,
            decision=Act(snapshot_action(pending.action)),
            policy_verdict=Allow(),
            observation=observation,
            model_call=snapshot_model_call(pending.model_call),
            execution_id=execution_id,
            reconciliation=snapshot_execution_reconciliation(reconciliation),
        )

        # post-step termination parity：与 normal settlement 共享同一套 should_stop 语义
        step = resolve_step_termination(self._policy, snapshot, step)

        settled = SessionSnapshot(
            session_id=snapshot.session_id,
            goal=snapshot.goal,
            state=snapshot.state,
            history=snapshot.history + (step,),
            pending_execution=None,
        )
        # canonical commit boundary：reconcile 的 settled snapshot 也必须先 validate，再 commit
        settled = validate_session_snapshot(settled)
        self._state_store.commit(settled)
        return settled

    def start(self, goal: Goal) -> SessionSnapshot:
        """convenience：create + run。run 失败抛 RuntimeExecutionError（含 session_id）。"""
        snapshot = self.create(goal)
        try:
            return self.run(snapshot.session_id)
        except Exception as exc:
            raise RuntimeExecutionError(session_id=snapshot.session_id) from exc
