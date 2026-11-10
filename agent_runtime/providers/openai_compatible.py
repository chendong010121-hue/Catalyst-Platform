"""Generic OpenAI-compatible ModelProvider.

This is a replaceable provider adapter, not Runtime/Core authority.
One request() is exactly one HTTP attempt; there is no hidden retry.
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


class OpenAICompatibleModelProvider:
    """Map provider-neutral ModelRequest to an OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 90.0,
        extra_headers: Mapping[str, str] | None = None,
        transport: Callable[[str, Mapping[str, str], bytes], tuple[int, Any]] | None = None,
        *, transport_guard: Callable | None = None,
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
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._extra_headers = dict(extra_headers or {})
        self._transport = transport or self._urllib_transport
        if transport_guard is not None and not callable(transport_guard):
            raise ValueError('transport_guard must be callable')
        self._transport_guard = transport_guard
        self.provider_id = "openai-compatible"
        self._external_call_observer: Callable[[], None] | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def set_external_call_observer(self, observer: Callable[[], None]) -> None:
        """Observe the boundary immediately before one transport attempt begins."""

        self._external_call_observer = observer

    def request(self, request: ModelRequest) -> ModelResponse:
        try:
            payload = self._build_payload(request)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except ModelProviderError as exc:
            raise attach_provider_context(exc, self.provider_id, category="invalid_request")
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
                f"{self._base_url}/chat/completions", self._headers(), body
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
            return self._parse_response(status, data, headers)
        except ModelProviderError as exc:
            raise attach_provider_context(exc, self.provider_id, category="protocol")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self._extra_headers)
        return headers

    def _build_payload(self, request: ModelRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [self._map_message(m) for m in request.messages],
            "stream": False,
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": dict(t.parameters),
                    },
                }
                for t in request.tools
            ]
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice

        allowed = {
            "temperature",
            "top_p",
            "max_tokens",
            "max_completion_tokens",
            "frequency_penalty",
            "presence_penalty",
            "seed",
            "response_format",
        }
        unsupported = sorted(set(request.parameters) - allowed)
        if unsupported:
            raise ModelProviderError(f"unsupported request parameters: {unsupported}")
        payload.update(dict(request.parameters))
        return payload

    @staticmethod
    def _map_message(message: Message) -> dict[str, Any]:
        mapped: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.role == "assistant" and message.tool_calls:
            mapped["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in message.tool_calls
            ]
        if message.role == "tool":
            mapped["tool_call_id"] = message.tool_call_id
        return mapped

    def _urllib_transport(
        self, url: str, headers: Mapping[str, str], body: bytes
    ) -> tuple[int, Any, Mapping[str, str]]:
        req = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with open_single_attempt(req, timeout=self._timeout) as resp:
                status = resp.status
                raw = resp.read()
                response_headers = dict(resp.headers.items())
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read(64 * 1024)
            response_headers = dict(exc.headers.items()) if exc.headers else {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            if status >= 400:
                data = {}
            else:
                raise ModelProviderError(
                    "provider returned a non-JSON success response",
                    provider_id=self.provider_id,
                    category="protocol",
                ) from None
        return status, data, response_headers

    def _unpack_transport_result(self, result: Any) -> tuple[int, Any, Mapping[str, str]]:
        if isinstance(result, tuple) and len(result) == 2:
            status, data = result
            return validate_status(status, self.provider_id), data, {}
        if isinstance(result, tuple) and len(result) == 3:
            status, data, headers = result
            return (
                validate_status(status, self.provider_id),
                data,
                headers if isinstance(headers, Mapping) else {},
            )
        raise ModelProviderError(
            "transport returned an invalid response envelope",
            provider_id=self.provider_id,
            category="protocol",
        )

    def _parse_response(
        self, status: int, data: Any, headers: Mapping[str, Any] | None = None
    ) -> ModelResponse:
        if status >= 400:
            raise http_provider_error(
                provider_id=self.provider_id,
                status=status,
                data=data,
                headers=headers,
                secret=self._api_key,
            )
        if not isinstance(data, dict):
            raise ModelProviderError(
                "malformed provider response: not an object",
                provider_id=self.provider_id,
                category="protocol",
            )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ModelProviderError(
                "malformed provider response: missing choices",
                provider_id=self.provider_id,
                category="protocol",
            )
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ModelProviderError(
                "malformed provider response: missing message",
                provider_id=self.provider_id,
                category="protocol",
            )
        role = message.get("role")
        if role is not None and role != "assistant":
            raise ModelProviderError(
                "malformed provider response: message.role must be 'assistant'",
                provider_id=self.provider_id,
                category="protocol",
            )

        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise ModelProviderError(
                "malformed provider response: content must be string/null",
                provider_id=self.provider_id,
                category="protocol",
            )

        calls = []
        for raw_call in message.get("tool_calls") or []:
            try:
                function = raw_call["function"]
                calls.append(
                    ModelToolCall(
                        id=str(raw_call["id"]),
                        name=str(function["name"]),
                        arguments=str(function["arguments"]),
                    )
                )
            except (KeyError, TypeError) as exc:
                raise ModelProviderError(
                    "malformed provider response: invalid tool call",
                    provider_id=self.provider_id,
                    category="protocol",
                ) from None

        usage = None
        raw_usage = data.get("usage")
        if isinstance(raw_usage, dict):
            input_tokens = raw_usage.get("prompt_tokens", raw_usage.get("input_tokens"))
            output_tokens = raw_usage.get("completion_tokens", raw_usage.get("output_tokens"))
            if type(input_tokens) is not int or type(output_tokens) is not int or min(input_tokens, output_tokens) < 0:
                raise ModelProviderError('malformed provider usage: expected non-negative integer counts',
                                         provider_id=self.provider_id, category='protocol')
            usage = ModelUsage(input_tokens=input_tokens, output_tokens=output_tokens)
        elif raw_usage is not None:
            raise ModelProviderError('malformed provider usage: expected an object',
                                     provider_id=self.provider_id, category='protocol')

        return ModelResponse(
            content=content,
            tool_calls=tuple(calls),
            finish_reason=choice.get("finish_reason"),
            usage=usage,
        )
