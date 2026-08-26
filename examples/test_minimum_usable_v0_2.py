"""Deterministic regression for Catalyst Minimum Usable V0.2 surfaces.

This module does NOT claim live usability. The live gate is owned by
.github/workflows/live-capability-eval.yml and the real API runner.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.contracts import Message, ModelRequest, ModelToolDefinition
from agent_runtime.providers import OpenAICompatibleModelProvider

ROOT = Path(__file__).resolve().parents[1]


def fake_transport(url, headers, body):
    payload = json.loads(body.decode("utf-8"))
    assert url == "https://provider.example/v1/chat/completions"
    assert headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "example-model"
    assert payload["messages"][0] == {"role": "user", "content": "hello"}
    assert payload["tools"][0]["function"]["name"] == "lookup"
    return 200, {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": "{\"q\":\"x\"}"},
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def main() -> None:
    provider = OpenAICompatibleModelProvider(
        api_key="test-key",
        model="example-model",
        base_url="https://provider.example/v1",
        transport=fake_transport,
    )
    response = provider.request(
        ModelRequest(
            messages=[Message(role="user", content="hello")],
            tools=(
                ModelToolDefinition(
                    name="lookup",
                    description="lookup",
                    parameters={"type": "object", "properties": {}},
                ),
            ),
            tool_choice="auto",
        )
    )
    assert response.tool_calls[0].name == "lookup"
    assert response.usage is not None and response.usage.total_tokens == 15

    public = json.loads(
        (ROOT / "platform-harness/live_eval/benchmark_v0_2/public_cases.json").read_text(encoding="utf-8")
    )
    private = json.loads(
        (ROOT / "platform-harness/live_eval/benchmark_v0_2/private_rubric.json").read_text(encoding="utf-8")
    )
    assert public["benchmark_id"] == private["benchmark_id"]
    assert len(public["cases"]) == 5
    assert {c["case_id"] for c in public["cases"]} == set(private["rubric"])

    for skill in (
        "capability-benchmark-design",
        "capability-evaluation",
        "capability-optimization",
    ):
        text = (ROOT / f"platform-harness/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
        assert "replaceable Harness-side" in text
        assert "Platform Core" in text or "Platform Standard" in text

    live = (ROOT / "platform-harness/live_eval/run_live_user_capability_eval.py").read_text(encoding="utf-8")
    assert "no fake fallback" in live.lower() or "never falls back" in live.lower()
    assert "api.github.com" in live
    assert "OpenAICompatibleModelProvider" in live

    print("PASS: Catalyst Minimum Usable V0.2 deterministic surface regression")


if __name__ == "__main__":
    main()
