"""DeepSeekModelProvider：第一个真实（非流式、non-thinking、one-attempt）ModelProvider。

只做 provider-neutral ModelRequest → DeepSeek request mapping → 一次真实 HTTP 调用
→ DeepSeek response → provider-neutral ModelResponse。

边界：
- 一次 request() = 一次真实 provider attempt，无隐藏 retry。
- 不解析 Agent Decision、不选能力、不做 Policy、不做 Session。
- HTTP client 使用标准库 urllib（无第三方依赖），timeout 可配置。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

from ..contracts import Message, ModelRequest, ModelResponse, ModelToolCall, ModelUsage
from ..errors import ModelProviderError

# 官方默认 base URL（OpenAI 兼容）：https://api.deepseek.com
_DEFAULT_BASE_URL = "https://api.deepseek.com"
# 当前官方主要模型：deepseek-v4-flash / deepseek-v4-pro；v0.1 默认 flash。
_DEFAULT_MODEL = "deepseek-v4-flash"

# 当前 Harness 只使用这三种 message role。
_ALLOWED_ROLES = ("system", "user", "assistant", "tool")

# DeepSeek non-stream Chat Completion response 的 concrete finish_reason。
# generic ModelResponse 仍允许 None（fake/local provider），但 DeepSeek adapter 必须严格要求。
_SUPPORTED_FINISH_REASONS = (
    "stop",
    "length",
    "content_filter",
    "tool_calls",
    "insufficient_system_resource",
)


class DeepSeekModelProvider:
    """把 provider-neutral ModelRequest 映射为一次 DeepSeek chat/completions 请求。

    transport 为可注入的 HTTP 边界：`(url, headers, body_bytes) -> (status, json_data)`，
    便于离线单测；默认使用 urllib（一次 attempt、finite timeout）。
    """

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 60.0,
        transport: Callable[[str, Mapping[str, str], bytes], tuple[int, Any]] | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport or self._urllib_transport

    def request(self, request: ModelRequest) -> ModelResponse:
        payload = self._build_request_payload(request)
        try:
            body = json.dumps(payload).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ModelProviderError(f"request serialization failed: {exc}") from exc
        status, data = self._transport(
            f"{self._base_url}/chat/completions",
            self._headers(),
            body,
        )
        return self._parse_response(status, data)

    # -- request mapping ----------------------------------------------------

    def _build_request_payload(self, request: ModelRequest) -> dict:
        # v0.1 不支持 parameters：非空即显式失败，不静默丢弃。
        if request.parameters:
            raise ModelProviderError(
                f"unsupported request parameters: {sorted(request.parameters)}"
            )

        messages = [self._map_message(message) for message in request.messages]

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "thinking": {"type": "disabled"},
        }

        if request.tools:
            payload["tools"] = [self._map_tool(tool) for tool in request.tools]

        if request.tool_choice is not None:
            if request.tool_choice != "auto":
                raise ModelProviderError(
                    f"unsupported tool_choice: {request.tool_choice!r}"
                )
            payload["tool_choice"] = request.tool_choice

        return payload

    @staticmethod
    def _coerce_content(content) -> str:
        if isinstance(content, str):
            return content
        raise ModelProviderError(
            f"unsupported message content type: {type(content).__name__}"
        )

    @staticmethod
    def _coerce_content_or_none(content):
        if content is None or isinstance(content, str):
            return content
        raise ModelProviderError(
            f"unsupported message content type: {type(content).__name__}"
        )

    def _map_message(self, message: Message) -> dict:
        role = message.role
        if role == "system":
            return {"role": "system", "content": self._coerce_content(message.content)}
        if role == "user":
            return {"role": "user", "content": self._coerce_content(message.content)}
        if role == "assistant":
            mapped = {
                "role": "assistant",
                "content": self._coerce_content_or_none(message.content),
            }
            if message.tool_calls:
                mapped["tool_calls"] = [
                    self._map_tool_call(c) for c in message.tool_calls
                ]
            return mapped
        if role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": self._coerce_content(message.content),
            }
        raise ModelProviderError(f"unsupported message role: {role!r}")

    @staticmethod
    def _map_tool(tool) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": dict(tool.parameters),
            },
        }

    @staticmethod
    def _map_tool_call(call: ModelToolCall) -> dict:
        return {
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": call.arguments},
        }

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    # -- transport ----------------------------------------------------------

    def _urllib_transport(
        self, url: str, headers: Mapping[str, str], body: bytes
    ) -> tuple[int, Any]:
        req = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            # 4xx/5xx：读取官方 error body 供后续映射。
            status = exc.code
            raw = exc.read()
        except OSError as exc:  # URLError / TimeoutError / socket error 等
            raise ModelProviderError(f"transport error: {exc}") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ModelProviderError("malformed provider response (non-JSON)") from exc
        return status, data

    # -- response mapping ---------------------------------------------------

    def _parse_response(self, status: int, data: Any) -> ModelResponse:
        if status >= 400:
            raise self._to_api_error(status, data)

        if not isinstance(data, dict):
            raise ModelProviderError("malformed provider response: not a JSON object")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelProviderError("malformed provider response: missing choices")

        choice = choices[0]
        if not isinstance(choice, dict):
            raise ModelProviderError("malformed provider response: invalid choice")

        message = choice.get("message")
        if not isinstance(message, dict):
            raise ModelProviderError("malformed provider response: missing message")

        # DeepSeek non-stream completion 返回的 message 必须是 assistant turn。
        role = message.get("role")
        if role != "assistant":
            raise ModelProviderError(
                f"malformed provider response: message.role must be 'assistant', got {role!r}"
            )

        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise ModelProviderError(
                f"malformed provider response: content is {type(content).__name__}"
            )

        tool_calls = self._map_tool_calls(message.get("tool_calls"))

        # DeepSeek non-stream concrete response 必须带 concrete supported finish_reason。
        # missing / null / non-string / unknown 都算 vendor envelope malformed，不进 Reasoner。
        finish_reason = choice.get("finish_reason")
        if not isinstance(finish_reason, str) or finish_reason not in _SUPPORTED_FINISH_REASONS:
            raise ModelProviderError(
                f"malformed provider response: finish_reason must be one of "
                f"{_SUPPORTED_FINISH_REASONS}, got {finish_reason!r}"
            )

        usage = self._map_usage(data.get("usage"))
        try:
            return ModelResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage=usage,
            )
        except ValueError as exc:
            # provider-neutral value-object 构造失败统一归一化为 provider adapter error
            raise ModelProviderError(f"malformed provider response: {exc}") from exc

    @staticmethod
    def _map_tool_calls(raw) -> tuple[ModelToolCall, ...]:
        if raw is None:
            return ()
        if not isinstance(raw, list):
            raise ModelProviderError(
                "malformed provider response: tool_calls is not a list"
            )
        calls = []
        for item in raw:
            if not isinstance(item, dict):
                raise ModelProviderError("malformed provider response: invalid tool_call")
            if item.get("type") != "function":
                raise ModelProviderError(
                    f"malformed provider response: unsupported tool_call type {item.get('type')!r}"
                )
            fn = item.get("function")
            if not isinstance(fn, dict):
                raise ModelProviderError(
                    "malformed provider response: tool_call missing function"
                )
            call_id = item.get("id")
            if not isinstance(call_id, str) or not call_id:
                raise ModelProviderError("malformed provider response: tool_call missing id")
            name = fn.get("name")
            if not isinstance(name, str) or not name:
                raise ModelProviderError("malformed provider response: tool_call missing name")
            arguments = fn.get("arguments")
            if not isinstance(arguments, str):
                raise ModelProviderError(
                    "malformed provider response: tool_call arguments must be string"
                )
            calls.append(ModelToolCall(id=call_id, name=name, arguments=arguments))
        return tuple(calls)

    @staticmethod
    def _map_usage(usage: Any) -> ModelUsage | None:
        if usage is None:
            return None
        if not isinstance(usage, dict):
            raise ModelProviderError("malformed provider response: usage is not an object")
        # 官方语义：prompt_tokens = prompt_cache_hit_tokens + prompt_cache_miss_tokens；
        # total_tokens = prompt_tokens + completion_tokens。
        # 因此 input=prompt_tokens / output=completion_tokens 对 total 预算是正确的。
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        if not (type(prompt) is int and prompt >= 0) or not (
            type(completion) is int and completion >= 0
        ):
            raise ModelProviderError(
                "malformed provider response: usage prompt_tokens/completion_tokens "
                "must be non-negative integers"
            )
        return ModelUsage(input_tokens=prompt, output_tokens=completion)

    def _to_api_error(self, status: int, data: Any) -> ModelProviderError:
        message = f"DeepSeek API error (HTTP {status})"
        code = None
        request_id = None
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict):
                if isinstance(err.get("message"), str):
                    message = err["message"]
                code = err.get("code")
                request_id = err.get("request_id")
            if isinstance(data.get("request_id"), str):
                request_id = data["request_id"]
        return ModelProviderError(
            message, status=status, code=code, request_id=request_id
        )
