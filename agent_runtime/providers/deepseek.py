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
import math
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

from ..contracts import Message, ModelRequest, ModelResponse, ModelToolCall, ModelUsage
from ..errors import ModelProviderError
from ._http import open_single_attempt, guarded_transport_attempt
from ._errors import (
    attach_provider_context,
    http_provider_error,
    provider_transport_error,
    validate_status,
)

# 官方默认 base URL（OpenAI 兼容）：https://api.deepseek.com
_DEFAULT_BASE_URL = "https://api.deepseek.com"
# Current official defaults: deepseek-flash / deepseek-v4-pro.
_DEFAULT_MODEL = "deepseek-flash"

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
        *, output_token_limit: int = 4096, transport_guard: Callable | None = None,
        model_output_token_limit: int | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip() or any(
            character in api_key for character in "\r\n"
        ):
            raise ValueError("api_key must be non-empty and contain no line breaks")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be non-empty")
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be non-empty")
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        capacity=8192 if model_output_token_limit is None else model_output_token_limit
        if type(capacity) is not int or not 1<=capacity<=1_048_576:
            raise ValueError("invalid declared model output capacity")
        if type(output_token_limit) is not int or not 1 <= output_token_limit <= capacity:
            raise ValueError("output_token_limit exceeds declared model capacity")
        self._output_token_limit = output_token_limit
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport or self._urllib_transport
        if transport_guard is not None and not callable(transport_guard):
            raise ValueError('transport_guard must be callable')
        self._transport_guard = transport_guard
        self.provider_id = "deepseek"
        self.model = model
        self._external_call_observer: Callable[[], None] | None = None

    def set_external_call_observer(self, observer: Callable[[], None]) -> None:
        """Observe the boundary immediately before one transport attempt begins."""

        self._external_call_observer = observer

    def request(self, request: ModelRequest) -> ModelResponse:
        try:
            payload = self._build_request_payload(request)
        except ModelProviderError as exc:
            raise attach_provider_context(exc, self.provider_id, category="invalid_request")
        try:
            body = json.dumps(payload).encode("utf-8")
        except (TypeError, ValueError):
            raise ModelProviderError(
                "request serialization failed",
                provider_id=self.provider_id,
                category="invalid_request",
            ) from None
        if self._external_call_observer is not None:
            self._external_call_observer()
        try:
            transport_result = guarded_transport_attempt(self._transport, self._transport_guard,
                f"{self._base_url}/chat/completions",
                self._headers(),
                body,
            )
        except ModelProviderError as exc:
            raise attach_provider_context(exc, self.provider_id, category="transport")
        except Exception as exc:
            raise provider_transport_error(self.provider_id, exc) from None

        status, data, headers = self._unpack_transport_result(transport_result)
        if status < 200 or 300 <= status < 400:
            raise ModelProviderError('unexpected HTTP status; redirects are not followed',
                                     provider_id=self.provider_id, category='protocol', status=status)
        if status >= 400:
            raise http_provider_error(
                provider_id=self.provider_id,
                status=status,
                data=data,
                headers=headers,
                secret=self._api_key,
            )
        try:
            return self._parse_response(status, data)
        except ModelProviderError as exc:
            raise attach_provider_context(exc, self.provider_id, category="protocol")

    # -- request mapping ----------------------------------------------------

    def _build_request_payload(self, request: ModelRequest) -> dict:
        allowed = {"max_tokens", "response_format"}
        unsupported = sorted(set(request.parameters) - allowed)
        if unsupported:
            raise ModelProviderError(f"unsupported request parameters: {unsupported}")
        parameters = dict(request.parameters)
        if "max_tokens" in parameters and (
            type(parameters["max_tokens"]) is not int or not 1 <= parameters["max_tokens"] <= self._output_token_limit
        ):
            raise ModelProviderError(f"max_tokens must be an integer between 1 and {self._output_token_limit}")
        if "response_format" in parameters and parameters["response_format"] != {"type": "json_object"}:
            raise ModelProviderError("only JSON object response_format is supported")

        messages = [self._map_message(message) for message in request.messages]

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "thinking": {"type": "disabled"},
            **parameters,
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
    ) -> tuple[int, Any, Mapping[str, str]]:
        req = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with open_single_attempt(req, timeout=self._timeout) as resp:
                status = resp.status
                # Output tokens do not bound malformed response metadata.
                # Keep the existing one-attempt adapter and fail closed.
                raw = resp.read(4 * 1024 * 1024 + 1)
                if len(raw) > 4 * 1024 * 1024:
                    raise ModelProviderError('provider response exceeded local byte limit',
                                             provider_id=self.provider_id, category='protocol')
                response_headers = dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read(64 * 1024)
            response_headers = dict(exc.headers.items()) if exc.headers else {}

        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            if status >= 400:
                data = {}
            else:
                raise ModelProviderError(
                    "provider returned a non-JSON success response",
                    provider_id=self.provider_id,
                    category="protocol",
                ) from None
        return status, data, response_headers

    @staticmethod
    def _unpack_transport_result(result: Any) -> tuple[int, Any, Mapping[str, str]]:
        if isinstance(result, tuple) and len(result) == 2:
            status, data = result
            return validate_status(status, "deepseek"), data, {}
        if isinstance(result, tuple) and len(result) == 3:
            status, data, headers = result
            return (
                validate_status(status, "deepseek"),
                data,
                headers if isinstance(headers, Mapping) else {},
            )
        raise ModelProviderError(
            "transport returned an invalid response envelope",
            provider_id="deepseek",
            category="protocol",
        )

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
                "malformed provider response: message.role must be 'assistant'"
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
                "malformed provider response: unsupported finish_reason"
            )

        usage = self._map_usage(data.get("usage"))
        try:
            return ModelResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage=usage,
            )
        except ValueError:
            # provider-neutral value-object 构造失败统一归一化为 provider adapter error
            raise ModelProviderError("malformed provider response: invalid model response") from None

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
                    "malformed provider response: unsupported tool_call type"
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
        hit = usage.get("prompt_cache_hit_tokens")
        miss = usage.get("prompt_cache_miss_tokens")
        details = usage.get("prompt_tokens_details")
        if details is not None:
            if not isinstance(details, dict):
                raise ModelProviderError("malformed provider response: prompt_tokens_details is not an object")
            detail_hit = details.get("cached_tokens")
            if detail_hit is not None:
                if type(detail_hit) is not int or detail_hit < 0 or detail_hit > prompt:
                    raise ModelProviderError("malformed provider response: cached_tokens is invalid")
                if hit is not None and hit != detail_hit:
                    raise ModelProviderError("malformed provider response: cache hit counts disagree")
                hit = detail_hit
        if hit is not None or miss is not None:
            if hit is None and type(miss) is int:
                hit = prompt - miss
            if miss is None and type(hit) is int:
                miss = prompt - hit
            if type(hit) is not int or type(miss) is not int or hit < 0 or miss < 0 or hit + miss != prompt:
                raise ModelProviderError("malformed provider response: cache counts must be non-negative and sum to prompt_tokens")
        return ModelUsage(input_tokens=prompt, output_tokens=completion,
                          cache_hit_input_tokens=hit, cache_miss_input_tokens=miss)

    def _to_api_error(
        self, status: int, data: Any, headers: Mapping[str, Any] | None = None
    ) -> ModelProviderError:
        return http_provider_error(
            provider_id=self.provider_id,
            status=status,
            data=data,
            headers=headers,
            secret=self._api_key,
        )
