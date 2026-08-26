"""中性契约层：值对象 + 抽象接口。

这是所有模块共同遵守的最小语言，不含任何行为实现、任何具体厂商、任何 I/O。
"""

from .interfaces import (
    Capability,
    CapabilityExecutor,
    ModelProvider,
    Policy,
    Reasoner,
    StateStore,
)
from .values import (
    Act,
    Action,
    Allow,
    Blocked,
    CapabilityDescriptor,
    Complete,
    ConfirmedExecuted,
    ConfirmedNotExecuted,
    Continue,
    Decision,
    Deny,
    ExecutionReconciliation,
    ExecutionResolution,
    Fail,
    Failure,
    Goal,
    Message,
    ModelCallRecord,
    ModelRequest,
    ModelResponse,
    ModelToolCall,
    ModelToolDefinition,
    ModelUsage,
    NativeToolsV2Call,
    NativeToolsV2FailureAttribution,
    NativeToolsV2RecoveryEvidence,
    NativeToolsV2Turn,
    Observation,
    Parameters,
    PendingExecution,
    PolicyVerdict,
    ReasoningResult,
    SessionSnapshot,
    State,
    StepRecord,
    Stop,
    Success,
    Termination,
)

__all__ = [
    # 基础值对象
    "Goal",
    "Action",
    "CapabilityDescriptor",
    # Decision 联合
    "Act",
    "Complete",
    "Fail",
    "Blocked",
    "Decision",
    # Observation 联合
    "Success",
    "Failure",
    "Observation",
    # Model
    "Message",
    "ModelToolDefinition",
    "ModelToolCall",
    "ModelRequest",
    "ModelUsage",
    "ModelResponse",
    "ModelCallRecord",
    "NativeToolsV2Call",
    "NativeToolsV2Turn",
    "NativeToolsV2FailureAttribution",
    "NativeToolsV2RecoveryEvidence",
    "ReasoningResult",
    # Policy 前置校验联合
    "Allow",
    "Deny",
    "PolicyVerdict",
    # Reconciliation
    "ConfirmedNotExecuted",
    "ConfirmedExecuted",
    "ExecutionResolution",
    "ExecutionReconciliation",
    # Session 快照
    "PendingExecution",
    "SessionSnapshot",
    # Policy 终止联合
    "Continue",
    "Stop",
    "Termination",
    # 占位类型
    "State",
    "StepRecord",
    "Parameters",
    # 抽象接口
    "Reasoner",
    "ModelProvider",
    "Capability",
    "CapabilityExecutor",
    "Policy",
    "StateStore",
]
