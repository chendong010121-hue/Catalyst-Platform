"""Generic OpenAI-compatible ModelProvider.

This is a replaceable provider adapter, not Runtime/Core authority.
One request() is exactly one HTTP attempt; there is no hidden retry.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

from ..contracts import Message, ModelRequest, ModelResponse, ModelToolCall, ModelUsage
from ..errors import ModelProviderError


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
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be non-empty")
        if not model:
            raise ValueError("model must be non-empty")
        if not base_url:
            raise ValueError("base_url must be non-empty")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._extra_headers = dict(extra_headers or {})
        self._transport = transport or self._urllib_transport

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def request(self, request: ModelRequest) -> ModelResponse:
        payload = self._build_payload(request)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status, data = self._transport(
            f"{self._base_url}/chat/completions", self._headers(), body
        )
        return self._parse_response(status, data)

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
    ) -> tuple[int, Any]:
        req = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
        except OSError as exc:
            raise ModelProviderError(f"transport error: {exc}") from exc
        try:
            return status, json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelProviderError("malformed provider response (non-JSON)") from exc

    @staticmethod
    def _parse_response(status: int, data: Any) -> ModelResponse:
        if status >= 400:
            detail = data.get("error") if isinstance(data, dict) else data
            raise ModelProviderError(f"provider HTTP {status}: {detail!r}")
        if not isinstance(data, dict):
            raise ModelProviderError("malformed provider response: not an object")
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ModelProviderError("malformed provider response: missing choices")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ModelProviderError("malformed provider response: missing message")

        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise ModelProviderError("malformed provider response: content must be string/null")

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
                raise ModelProviderError("malformed provider response: invalid tool call") from exc

        usage = None
        raw_usage = data.get("usage")
        if isinstance(raw_usage, dict):
            input_tokens = raw_usage.get("prompt_tokens", raw_usage.get("input_tokens"))
            output_tokens = raw_usage.get("completion_tokens", raw_usage.get("output_tokens"))
            if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                usage = ModelUsage(input_tokens=input_tokens, output_tokens=output_tokens)

        return ModelResponse(
            content=content,
            tool_calls=tuple(calls),
            finish_reason=choice.get("finish_reason"),
            usage=usage,
        )
