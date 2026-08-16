"""中性契约层 —— 抽象接口（Protocol）。

实现方只需在结构上满足这些方法即可，无需继承任何基类。
本模块不含任何实现、任何厂商、任何 I/O。
"""

from __future__ import annotations

from typing import Protocol, Sequence

from .values import (
    Action,
    CapabilityDescriptor,
    Goal,
    ModelRequest,
    ModelResponse,
    Observation,
    Parameters,
    PolicyVerdict,
    ReasoningResult,
    SessionSnapshot,
    State,
    StepRecord,
    Termination,
)

__all__ = ["Reasoner", "ModelProvider", "Capability", "CapabilityExecutor", "Policy", "StateStore"]


class Reasoner(Protocol):
    """如何思考：组织上下文、调用 ModelProvider、产生结构化 Decision 及
    本次推理的 model-call facts（ReasoningResult）。

    实现方不得直接网络 I/O、不得持有厂商 SDK，只依赖 ModelProvider 接口。
    """

    def decide(
        self,
        goal: Goal,
        state: State,
        history: Sequence[StepRecord],
        capabilities: Sequence[CapabilityDescriptor],
    ) -> ReasoningResult:
        """基于目标/状态/历史/可用能力描述，决定下一步。"""
        ...


class ModelProvider(Protocol):
    """由哪个模型完成推理：收一个通用请求，返回一个通用响应。

    一次 request() = 一次模型 attempt。实现方负责 SDK、endpoint、auth、
    request mapping、response normalization、transport timeout、厂商错误映射，
    但不得默认做隐藏自动 retry（retry 属更高层显式 recovery/policy）。

    实现方不认识 AgentCore / Reasoner / Capability / Policy。
    """

    def request(self, request: ModelRequest) -> ModelResponse:
        """发送模型请求，返回归一化响应。"""
        ...


class Capability(Protocol):
    """一种 Agent-facing 可执行能力：自描述 + 执行。

    Reasoner 可以选择、AgentCore 可以执行、并得到 Observation。
    StateStore / filesystem / HTTP transport / credential store / sandbox /
    LLM provider / telemetry 等基础设施服务不应被强迫实现此接口。
    """

    def describe(self) -> CapabilityDescriptor:
        """返回本能力的自描述元数据。"""
        ...

    def invoke(self, parameters: Parameters, context) -> Observation:
        """执行本能力并返回观测结果。

        context 是 runtime-only ExecutionContext（提供 cooperative cancellation /
        deadline 检查）。只返回 Success/Failure（authoritative outcome）；抛异常代表
        outcome uncertain，由 Executor/Runner 处理为 infrastructure uncertainty。
        """
        ...


class CapabilityExecutor(Protocol):
    """执行 Agent-facing Capability：resolve / validate / invoke / normalize。

    不做 reasoning、policy、session lifecycle、retry、approval、sandbox、model calls。
    """

    def descriptors(self) -> tuple[CapabilityDescriptor, ...]:
        """返回 model-visible capability descriptors（stable order，id 与 lookup identity 一致）。"""
        ...

    def execute(self, action: Action, *, execution_id: str, session_id: str) -> Observation:
        """执行一个已通过 Policy 的 Action，返回 Observation。

        execution_id 来自 durable PendingExecution identity；session_id 用于
        live cancellation registry。返回 Success/Failure（authoritative）；
        抛 CapabilityExecutionError / CapabilityTimeoutUncertainError 表示 outcome
        uncertain（Core 保留 pending unresolved）。
        """
        ...


class Policy(Protocol):
    """纯规则护栏：权限/安全/预算/资源/终止。

    不做推理、不选能力、不调能力；Action 的产生与修改始终属于 Reasoner。
    """

    def check_action(self, action: Action, state: State) -> PolicyVerdict:
        """对拟执行的动作做前置校验（Allow / Deny）。"""
        ...

    def should_stop(self, state: State, history: Sequence[StepRecord]) -> Termination:
        """终止护栏：是否应停止，以及停止原因。"""
        ...


class StateStore(Protocol):
    """状态与执行历史的持久化。只存数据，不含逻辑。

    以 SessionSnapshot 为读写单位。durability contract：

    - commit(snapshot) 正常返回，意味着该 snapshot 已达到本实现承诺的
      durability level，并成为后续 load/recovery 可观察到的 authoritative snapshot。
    - atomicity（一个快照作为整体不可分割地提交）与 durability（持久到何种程度、
      能否在进程崩溃后恢复）是两个不同要求。
    """

    def load(self, session_id: str) -> SessionSnapshot:
        """读取一个 Session 当前可恢复的 authoritative 快照。"""
        ...

    def commit(self, snapshot: SessionSnapshot) -> None:
        """提交一个检查点；正常返回即表示该 snapshot 已 durable。"""
        ...
