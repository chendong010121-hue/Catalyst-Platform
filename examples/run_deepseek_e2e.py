"""DeepSeek 端到端 Live Smoke：Runtime → AgentCore → LLMReasoner → DeepSeekModelProvider。

只从环境变量读取 secret；无 key 则 SKIP。
不打印完整 prompt / secret / Authorization header。
"""

from __future__ import annotations

import os

from agent_runtime.contracts import CapabilityDescriptor, Goal, Success
from agent_runtime.llm_reasoner import LLMReasoner
from agent_runtime.policies import StepLimitPolicy
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from agent_runtime.runtime import Runtime
from agent_runtime.execution import RuntimeDomain


class AddCapability:
    def describe(self):
        return CapabilityDescriptor(
            id="add",
            name="add",
            description="把两个数 a、b 相加并返回结果。",
            input_schema={
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
                "additionalProperties": False,
            },
            output_schema={"sum": "number"},
        )

    def invoke(self, parameters, context):
        return Success(parameters["a"] + parameters["b"])


class MemStore:
    def __init__(self):
        self._snapshots = {}

    def load(self, session_id):
        return self._snapshots[session_id]

    def commit(self, snapshot):
        self._snapshots[snapshot.session_id] = snapshot


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("SKIPPED: DEEPSEEK_API_KEY not set")
        return

    provider = DeepSeekModelProvider(
        api_key=api_key, model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )
    runtime = Runtime(reasoner=LLMReasoner(provider), capabilities={"add": AddCapability()}, policy=StepLimitPolicy(max_steps=8), domain=RuntimeDomain(state_store=MemStore()))

    goal = Goal("使用提供的 add capability 计算 20 + 22，并在获得结果后完成任务。")
    final = runtime.start(goal)

    print("=== final session history ===")
    for step in final.history:
        decision = type(step.decision).__name__
        observation = step.observation
        print(f"step {step.index}: decision={decision}, observation={observation}")

    print("=== model usage ===")
    for step in final.history:
        if step.model_call is not None and step.model_call.usage is not None:
            u = step.model_call.usage
            print(
                f"step {step.index}: input={u.input_tokens} "
                f"output={u.output_tokens} total={u.total_tokens}"
            )


if __name__ == "__main__":
    main()
