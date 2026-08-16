"""DeepSeekModelProvider 真实 Live Smoke（provider-only）。

只从环境变量读取 secret；无 key 则 SKIP，绝不导致离线测试失败。
不打印完整 prompt / secret / Authorization header。
"""

from __future__ import annotations

import os

from agent_runtime.contracts import Message, ModelRequest
from agent_runtime.providers.deepseek import DeepSeekModelProvider


def main() -> None:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("SKIPPED: DEEPSEEK_API_KEY not set")
        return

    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    provider = DeepSeekModelProvider(api_key=api_key, model=model, base_url=base_url)
    request = ModelRequest(
        messages=[
            Message("system", "You are a helpful assistant."),
            Message("user", "Reply with exactly one word: ok"),
        ]
    )

    response = provider.request(request)

    print("provider request succeeded")
    print("finish_reason =", response.finish_reason)
    if response.usage is not None:
        print("input_tokens =", response.usage.input_tokens)
        print("output_tokens =", response.usage.output_tokens)
        print("total_tokens =", response.usage.total_tokens)
    print("content length =", len(response.content))


if __name__ == "__main__":
    main()
