"""最小异常类型（不建立复杂异常继承体系）。"""

from __future__ import annotations


class PolicyContractError(RuntimeError):
    """Policy 返回了契约之外的判定（非 Allow/Deny 或非 Continue/Stop）。"""


class RuntimeConfigurationError(RuntimeError):
    """Runtime 组合配置违反 safety composition contract（fail-closed）。

    例如：timeout-enabled 的下层 executor 必须提供 execution-control 依赖
    （Runtime-local control plane），否则无法维护 live-execution guard。
    """


class CapabilityContractError(RuntimeError):
    """Capability.invoke 返回了 Success/Failure 之外的值（契约违反）。"""


class CapabilityExecutionError(RuntimeError):
    """Capability.invoke 抛异常：execution outcome 不确定（可能已产生真实副作用）。

    与 Observation.Failure（authoritative known failure）严格区分：exception 不
    代表"确定失败"，只代表"结果未知"。只携带 capability_id 与安全摘要，不把完整
    exception repr 变成 agent-visible Observation（避免泄漏路径/凭据）。
    """

    def __init__(self, capability_id: str, message: str | None = None) -> None:
        self.capability_id = capability_id
        super().__init__(
            message
            or f"capability {capability_id!r} raised during execution (outcome unknown)"
        )


class ExecutionCancelled(RuntimeError):
    """Capability 在 cooperative cancellation point 主动退出（body 已 quiesce）。

    仅当 Capability 明确通过 Harness 提供的 cancellation token API
    （raise_if_cancelled / is_cancel_requested）退出时，才由 token 抛出。
    普通 RuntimeError/IOError 即使恰逢 cancel request，也绝不能当 ExecutionCancelled。
    """


class CapabilityTimeoutUncertainError(RuntimeError):
    """deadline 到达、cancellation 已请求，但执行未确认 quiesce：outcome unknown。

    worker 可能在后台继续运行。属于 infrastructure uncertainty，绝不能变成
    agent-visible Observation.Failure("timeout")。Core 保留 durable PendingExecution
    unresolved，只能由 operator/external verification → Runtime.reconcile 恢复。
    """

    def __init__(self, session_id: str, execution_id: str) -> None:
        self.session_id = session_id
        self.execution_id = execution_id
        super().__init__(
            f"execution {execution_id!r} in session {session_id!r} did not confirm "
            f"quiescence before deadline; outcome unknown"
        )


class CapabilityRegistrationError(RuntimeError):
    """Capability 的 lookup key 与 CapabilityDescriptor.id 不一致等注册错误。"""


class RuntimeExecutionError(RuntimeError):
    """Runtime.start 的 run 阶段失败，但 session 已创建；携带 session_id 供恢复。"""

    def __init__(self, session_id: str, message: str | None = None) -> None:
        super().__init__(
            message or f"runtime execution failed for session {session_id!r}"
        )
        self.session_id = session_id


class ModelProviderError(RuntimeError):
    """ModelProvider 失败（HTTP/API/transport/protocol），不泄露 secret。

    只保存官方实际提供的可审计字段：HTTP status、provider error code、request id。
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.request_id = request_id


class UnresolvedExecutionError(RuntimeError):
    """Session 存在 unresolved execution，自动 resume 不安全。

    表达：Harness 对真实世界 execution outcome 不确定。不是模型或 Capability
    的已知结果，不能自动 retry / 清 pending / 当成功或失败。
    """

    def __init__(self, session_id: str, execution_id: str, action) -> None:
        self.session_id = session_id
        self.execution_id = execution_id
        self.action = action
        self.capability_id = action.capability_id
        super().__init__(
            f"session {session_id!r} has unresolved execution {execution_id!r} "
            f"(capability {action.capability_id!r}); automatic resume is unsafe"
        )


class ReconciliationError(RuntimeError):
    """Reconciliation 失败（no pending / execution_id 不匹配 / 非法 resolution 等）。

    不是 Agent execution outcome，不能伪装成 Observation.Failure。
    """


class ExecutionStillLiveError(ReconciliationError):
    """Reconciliation 被拒绝：pending execution 对应的 local worker 仍 live。

    一个仍可能改变现实的 live execution 不能被 reconcile（无论 ConfirmedNotExecuted
    还是 ConfirmedExecuted），否则外部断言会与后续真实副作用矛盾。必须等 worker 真正
    quiesce（future done + registry cleanup）后，reconciliation 才可用。
    """

    def __init__(self, session_id: str, execution_id: str) -> None:
        self.session_id = session_id
        self.execution_id = execution_id
        super().__init__(
            f"session {session_id!r} execution {execution_id!r} is still live; "
            f"reconciliation requires quiescence"
        )


class ReasonerContractError(RuntimeError):
    """Reasoner 输出了非法 ReasoningResult / Decision（contract violation）。"""


class SessionConsistencyError(RuntimeError):
    """从 StateStore load 出的 SessionSnapshot 结构不一致（recovery fail-closed）。

    只携带 session_id 与 reason，不 dump 完整 payload，避免暴露大对象/secret。
    """

    def __init__(self, reason: str, *, session_id: str | None = None) -> None:
        self.session_id = session_id
        self.reason = reason
        label = f" for session {session_id!r}" if session_id is not None else ""
        super().__init__(f"session consistency violation{label}: {reason}")
