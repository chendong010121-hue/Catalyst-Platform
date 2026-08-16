"""DeepSeek Native Tool Calling Live Smoke。

只从环境变量读取 secret；无 key 则 SKIP。不打印 prompt / secret / Authorization。
"""

from __future__ import annotations

import os

from agent_runtime.contracts import CapabilityDescriptor, Goal, Success
from agent_runtime.execution import RuntimeDomainBindable
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


class MemStore(RuntimeDomainBindable):
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
    runtime = Runtime(reasoner=LLMReasoner(provider, decision_protocol="native_tools"), capabilities={"add": AddCapability()}, policy=StepLimitPolicy(max_steps=8), domain=RuntimeDomain(state_store=MemStore()))

    goal = Goal("使用 add capability 计算 20 + 22，然后告诉我结果。")
    final = runtime.start(goal)

    print("=== final session history ===")
    for step in final.history:
        decision = type(step.decision).__name__
        tool_ids = (
            [c.id for c in step.model_call.tool_calls]
            if step.model_call is not None and step.model_call.tool_calls
            else []
        )
        print(
            f"step {step.index}: decision={decision}, observation={step.observation}, "
            f"tool_call_ids={tool_ids}"
        )

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
