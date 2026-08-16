"""Agent Runtime —— 最小、可扩展、fail-closed 的 Agent 运行时。

分层（只收敛与加固，不扩张）：

- contracts          —— 中性契约层（值对象 + 抽象接口）
- core               —— AgentCore（Agent Loop / 控制流，不推理、不直接调用 Capability）
- runtime            —— Runtime（宿主 / 生命周期 / 组合根，含 reconcile 恢复）
- llm_reasoner       —— LLMReasoner（legacy_json + native_tools 两种 decision_protocol）
- capability_executor—— DefaultCapabilityExecutor（resolve/validate/invoke/normalize）
- execution          —— cooperative cancellation / timeout 执行控制（runtime-only，不 durable）
- policies           —— 生产级安全 Policy（StepLimitPolicy / TokenBudgetPolicy）
- snapshot           —— Durable Fact Boundary（JsonValue strict snapshot）
- providers          —— DeepSeekModelProvider（deepseek-v4-flash，one-attempt，non-thinking）
- errors             —— 最小异常类型（契约违反 / 生命周期 / 恢复 / 执行确定性）

尚未接入任何其它真实模型 Provider（GPT / 本地）。
"""

from . import contracts

__all__ = ["contracts"]
