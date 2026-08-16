"""DeepSeekModelProvider 离线单元测试（不消耗真实 API，无网络）。"""

from __future__ import annotations

import json

from agent_runtime.contracts import (
    Message,
    ModelRequest,
    ModelToolCall,
    ModelToolDefinition,
)
from agent_runtime.errors import ModelProviderError
from agent_runtime.providers.deepseek import DeepSeekModelProvider

_GOOD_RESPONSE = {
    "choices": [
        {"message": {"role": "assistant", "content": "42"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


def _provider(responses_or_fn, api_key="sk-SECRET-123456"):
    """构造一个用假 transport 的 provider。"""
    if callable(responses_or_fn):
        transport = responses_or_fn
    else:
        queue = list(responses_or_fn)

        def transport(url, headers, body):
            if not queue:
                raise AssertionError("transport called more times than scripted")
            return queue.pop(0)

    return DeepSeekModelProvider(api_key=api_key, transport=transport)


# ---------------------------------------------------------------------------

def test_a_request_mapping():
    captured = {}

    def transport(url, headers, body):
        captured["url"] = url
        captured["headers"] = dict(headers)
        captured["body"] = json.loads(body.decode("utf-8"))
        return (200, _GOOD_RESPONSE)

    provider = _provider(transport)
    provider.request(
        ModelRequest(messages=[Message("system", "sys"), Message("user", "hi")])
    )

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-SECRET-123456"
    assert captured["headers"]["Content-Type"] == "application/json"
    body = captured["body"]
    assert body["model"] == "deepseek-v4-flash"
    assert body["thinking"] == {"type": "disabled"}
    assert body["stream"] is False
    assert body["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    # 无 Agent-specific 字段
    assert "decision" not in body
    assert "capability" not in body


def test_b_normal_response():
    provider = _provider([(200, _GOOD_RESPONSE)])
    resp = provider.request(ModelRequest(messages=[Message("user", "hi")]))

    assert resp.content == "42"
    assert resp.finish_reason == "stop"
    assert resp.usage.input_tokens == 10
    assert resp.usage.output_tokens == 5
    assert resp.usage.total_tokens == 15


def test_c_api_error():
    provider = _provider(
        [(401, {"error": {"message": "Invalid API key", "code": "invalid_api_key"}})]
    )
    try:
        provider.request(ModelRequest(messages=[Message("user", "hi")]))
    except ModelProviderError as exc:
        assert exc.status == 401
        assert exc.code == "invalid_api_key"
        # secret 不出现在异常消息里
        assert "sk-SECRET-123456" not in str(exc)
        assert "Authorization" not in str(exc)
        return
    raise AssertionError("expected ModelProviderError for API error")


def test_d_transport_error_one_attempt():
    calls = []

    def transport(url, headers, body):
        calls.append(1)
        raise ModelProviderError("transport error: connection refused")

    provider = _provider(transport)
    try:
        provider.request(ModelRequest(messages=[Message("user", "hi")]))
    except ModelProviderError:
        pass
    else:
        raise AssertionError("expected ModelProviderError for transport failure")

    assert len(calls) == 1  # 无隐藏 retry


def test_e_malformed_response():
    bad_payloads = [
        {"choices": []},
        {"choices": [{"finish_reason": "stop"}]},  # 缺 message
        {"choices": [{"message": {"content": 123}}]},  # content 非 str
        "not a dict",
    ]
    for bad in bad_payloads:
        provider = _provider([(200, bad)])
        try:
            provider.request(ModelRequest(messages=[Message("user", "hi")]))
        except ModelProviderError:
            continue
        raise AssertionError(f"expected ModelProviderError for {bad!r}")


def test_f_provider_safe_serialization():
    # 非空 parameters（v0.1 不支持）→ 明确失败，不静默丢字段
    provider = _provider([(200, _GOOD_RESPONSE)])
    try:
        provider.request(
            ModelRequest(
                messages=[Message("user", "hi")], parameters={"temperature": 0.5}
            )
        )
    except ModelProviderError:
        pass
    else:
        raise AssertionError("expected ModelProviderError for unsupported parameters")


# ---------------------------------------------------------------------------
# Native tool calling mapping
# ---------------------------------------------------------------------------

def test_g_tools_mapping():
    captured = {}

    def transport(url, headers, body):
        captured["body"] = json.loads(body.decode("utf-8"))
        return (200, _GOOD_RESPONSE)

    provider = _provider(transport)
    provider.request(
        ModelRequest(
            messages=[Message("user", "hi")],
            tools=(
                ModelToolDefinition(
                    name="add",
                    description="adds two ints",
                    parameters={"type": "object", "properties": {"a": {"type": "integer"}}},
                ),
            ),
        )
    )

    tools = captured["body"]["tools"]
    assert len(tools) == 1
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "add"
    assert tools[0]["function"]["description"] == "adds two ints"
    assert tools[0]["function"]["parameters"]["type"] == "object"


def test_h_assistant_tool_call_message_mapping():
    captured = {}

    def transport(url, headers, body):
        captured["body"] = json.loads(body.decode("utf-8"))
        return (200, _GOOD_RESPONSE)

    provider = _provider(transport)
    provider.request(
        ModelRequest(
            messages=[
                Message(
                    "assistant",
                    None,
                    (ModelToolCall("call_1", "add", '{"a":20}'),),
                )
            ]
        )
    )

    msg = captured["body"]["messages"][0]
    assert msg["role"] == "assistant"
    assert msg["content"] is None
    assert msg["tool_calls"][0]["id"] == "call_1"
    assert msg["tool_calls"][0]["type"] == "function"
    assert msg["tool_calls"][0]["function"]["name"] == "add"
    assert msg["tool_calls"][0]["function"]["arguments"] == '{"a":20}'


def test_i_tool_result_mapping():
    captured = {}

    def transport(url, headers, body):
        captured["body"] = json.loads(body.decode("utf-8"))
        return (200, _GOOD_RESPONSE)

    provider = _provider(transport)
    provider.request(ModelRequest(messages=[Message("tool", "42", tool_call_id="call_1")]))

    msg = captured["body"]["messages"][0]
    assert msg["role"] == "tool"
    assert msg["tool_call_id"] == "call_1"
    assert msg["content"] == "42"


def test_j_response_tool_calls_mapping():
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "add", "arguments": '{"a":20,"b":22}'},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    provider = _provider([(200, resp)])
    result = provider.request(ModelRequest(messages=[Message("user", "hi")]))

    assert result.content is None
    assert result.finish_reason == "tool_calls"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_123"
    assert result.tool_calls[0].name == "add"
    assert result.tool_calls[0].arguments == '{"a":20,"b":22}'


def test_k_invalid_raw_arguments_stays_raw():
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c",
                            "type": "function",
                            "function": {"name": "add", "arguments": "{invalid-json"},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    provider = _provider([(200, resp)])
    result = provider.request(ModelRequest(messages=[Message("user", "hi")]))

    # Provider 不 parse arguments，保留原始 string
    assert result.tool_calls[0].arguments == "{invalid-json"


def test_l_malformed_tool_call_envelope():
    bad_payloads = [
        # 缺 id
        {"choices": [{"message": {"tool_calls": [{"type": "function", "function": {"name": "add", "arguments": "{}"}}]}}]},
        # type != function
        {"choices": [{"message": {"tool_calls": [{"id": "c", "type": "other", "function": {"name": "add", "arguments": "{}"}}]}}]},
        # 缺 name
        {"choices": [{"message": {"tool_calls": [{"id": "c", "type": "function", "function": {"arguments": "{}"}}]}}]},
        # arguments 非 string
        {"choices": [{"message": {"tool_calls": [{"id": "c", "type": "function", "function": {"name": "add", "arguments": 123}}]}}]},
        # tool_calls 非 list
        {"choices": [{"message": {"tool_calls": "nope"}}]},
    ]
    for bad in bad_payloads:
        provider = _provider([(200, bad)])
        try:
            provider.request(ModelRequest(messages=[Message("user", "hi")]))
        except ModelProviderError:
            continue
        raise AssertionError(f"expected ModelProviderError for {bad!r}")


def main() -> None:
    tests = [
        ("A request mapping", test_a_request_mapping),
        ("B normal response", test_b_normal_response),
        ("C API error（含 secret 不泄露）", test_c_api_error),
        ("D transport error one-attempt", test_d_transport_error_one_attempt),
        ("E malformed response", test_e_malformed_response),
        ("F provider-safe serialization", test_f_provider_safe_serialization),
        ("G tools mapping", test_g_tools_mapping),
        ("H assistant tool-call message mapping", test_h_assistant_tool_call_message_mapping),
        ("I tool result mapping", test_i_tool_result_mapping),
        ("J response tool_calls mapping", test_j_response_tool_calls_mapping),
        ("K invalid raw arguments stays raw", test_k_invalid_raw_arguments_stays_raw),
        ("L malformed tool-call envelope", test_l_malformed_tool_call_envelope),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED: {name}")
        except AssertionError as exc:
            failed.append(name)
            print(f"FAILED: {name} -> {exc}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"ERROR : {name} -> {type(exc).__name__}: {exc}")

    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        raise SystemExit(1)
    print("\nALL DEEPSEEK PROVIDER TESTS PASSED")


if __name__ == "__main__":
    main()
