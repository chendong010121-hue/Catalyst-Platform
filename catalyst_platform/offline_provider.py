"""Explicit deterministic Provider for local demonstrations and acceptance replay."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Mapping

from agent_runtime.contracts import ModelResponse, ModelToolCall


class DeterministicOfflineProvider:
    """Exercise the existing tool loop without a live model or external call.

    This provider is intentionally a deterministic test aid. It does not claim
    general language understanding or Live LLM tool-selection quality.
    """

    provider_id = "catalyst-deterministic-offline"
    model = "local-acceptance-fixture-v1"
    mode = "offline"
    external_calls = 0

    def __init__(
        self,
        *,
        message: str,
        selected_file: Path | str | None,
        wiki_result: Mapping[str, Any] | None,
    ) -> None:
        self.message = message
        self.selected_file = Path(selected_file).expanduser().resolve() if selected_file is not None else None
        self.wiki_result = dict(wiki_result or {})
        self.request_count = 0

    def request(self, request) -> ModelResponse:
        self.request_count += 1
        if self.request_count == 1:
            tool = self._title_tool(request.tools)
            if tool is not None and self.selected_file is not None and self._asks_for_title(self.message):
                return ModelResponse(
                    tool_calls=(
                        ModelToolCall(
                            id=f"offline_{uuid.uuid4().hex[:12]}",
                            name=tool.name,
                            arguments=json.dumps({"path": str(self.selected_file)}, separators=(",", ":")),
                        ),
                    ),
                    finish_reason="tool_calls",
                )
            return ModelResponse(content=self._direct_answer(), finish_reason="stop")

        tool_messages = [message for message in request.messages if message.role == "tool"]
        if not tool_messages:
            return ModelResponse(content="No tool result was returned; the request is unresolved.", finish_reason="stop")
        try:
            value = json.loads(tool_messages[-1].content or "null")
        except json.JSONDecodeError:
            return ModelResponse(content="The local tool result was not valid JSON; no claim is made.", finish_reason="stop")
        title = value.get("title") if isinstance(value, dict) else None
        if isinstance(title, str) and title:
            return ModelResponse(content=f"The selected document title is {title}.", finish_reason="stop")
        return ModelResponse(content=f"The selected read-only tool returned: {json.dumps(value, ensure_ascii=False)}", finish_reason="stop")

    @staticmethod
    def _title_tool(tools):
        for tool in tools:
            description = str(getattr(tool, "description", "")).casefold()
            if "title" in description or "heading" in description or "markdown h1" in description:
                return tool
        return None

    @staticmethod
    def _asks_for_title(message: str) -> bool:
        lowered = message.casefold()
        return any(
            term in lowered
            for term in (
                "title", "heading", "top-level label", "document name", "file name",
                "what is the name", "标题", "文件名", "文档名",
            )
        )

    def _direct_answer(self) -> str:
        capabilities = self.wiki_result.get("capabilities", [])
        if capabilities and any(term in self.message.casefold() for term in ("what can", "capabilit", "process files", "处理文件", "能做什么")):
            options = "; ".join(
                f"{item.get('name')}: {item.get('meaning')} "
                f"(active exact binding {item.get('capability_id')}@{item.get('capability_version')})"
                for item in capabilities
            )
            return f"The project Wiki found these active read-only capabilities: {options}. Invocation still requires the R5 policy check."
        if self.selected_file is not None and self.wiki_result.get("applicability_status") == "UNKNOWN":
            return "The source contains an unresolved applicability or approval condition; no file was read."
        if self.selected_file is not None and self._asks_for_title(self.message):
            return "No matching active read-only Capability was retrieved; no file was read."
        if self._asks_for_title(self.message):
            return "Please select a local Markdown or text file before asking for its title."
        return "This deterministic offline Provider made no tool call. Live LLM understanding is not being tested."
