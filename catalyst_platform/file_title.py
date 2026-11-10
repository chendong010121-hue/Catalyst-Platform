"""Deterministic local file-title capability used by the Catalyst CLI."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from agent_runtime.contracts import (
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Failure,
    Success,
)

from platform_standard.models import CapabilityDescriptor


CAPABILITY_ID = "read_file_title"
CAPABILITY_VERSION = "1.0.0"
INPUT_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}},
    "required": ["path"],
    "additionalProperties": False,
}
OUTPUT_SCHEMA = {"type": "object"}
_MARKDOWN_H1 = re.compile(r"^ {0,3}#(?!#)(?:[ \t]+)(.+?)[ \t]*$")
_MARKDOWN_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_MARKDOWN_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id=CAPABILITY_ID,
        name="Read a local text file title",
        description=(
            "Read a UTF-8 Markdown or text file and return a deterministic title "
            "with source path, SHA-256, line number, and the original line."
        ),
        capability_version=CAPABILITY_VERSION,
        input_schema=INPUT_SCHEMA,
        output_schema=OUTPUT_SCHEMA,
        execution={"side_effect": "none"},
    )


class FileTitleCapability:
    """Read a bounded title convention from one user-selected local file."""

    def __init__(
        self,
        *,
        workspace: Path,
        event_sink: Callable[[dict[str, Any]], None],
    ) -> None:
        self._workspace = workspace
        self._event_sink = event_sink

    def describe(self) -> RuntimeCapabilityDescriptor:
        return RuntimeCapabilityDescriptor(
            id=CAPABILITY_ID,
            name="Read a local text file title",
            description="Extract a Markdown H1 or the first non-empty text line.",
            input_schema=INPUT_SCHEMA,
            output_schema=OUTPUT_SCHEMA,
        )

    def invoke(self, parameters, context) -> Success | Failure:
        requested_path = parameters["path"]
        try:
            path = Path(requested_path).expanduser()
            if not path.is_absolute():
                path = self._workspace / path
            path = path.resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            return self._fail(
                "invalid_path",
                f"The requested file path cannot be resolved ({type(exc).__name__}).",
                requested_path=str(requested_path),
            )

        self._event_sink(
            {
                "event_type": "tool.started",
                "timestamp": _utc_now(),
                "tool_id": CAPABILITY_ID,
                "tool_version": CAPABILITY_VERSION,
                "source_path": str(path),
            }
        )

        if path.suffix.lower() not in {".md", ".txt"}:
            return self._fail(
                "unsupported_file_type",
                "R0 reads UTF-8 Markdown (.md) and text (.txt) files only.",
                source_path=str(path),
            )

        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            return self._fail(
                "file_not_found",
                f"File does not exist: {path}",
                source_path=str(path),
            )
        except PermissionError:
            return self._fail(
                "permission_denied",
                f"The current local process cannot read: {path}",
                source_path=str(path),
            )
        except IsADirectoryError:
            return self._fail(
                "not_a_file",
                f"The requested path is a directory: {path}",
                source_path=str(path),
            )
        except OSError as exc:
            return self._fail(
                "file_read_error",
                f"Could not read {path} ({type(exc).__name__}).",
                source_path=str(path),
            )

        digest = hashlib.sha256(raw).hexdigest()
        source_base = {
            "path": str(path),
            "source_id": f"sha256:{digest}",
            "sha256": digest,
            "byte_length": len(raw),
        }
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return self._fail(
                "invalid_utf8",
                "The file is not valid UTF-8 text.",
                source=source_base,
            )

        lines = text.splitlines()
        if path.suffix.lower() == ".md":
            match = self._first_markdown_h1(lines)
            if match is None:
                return self._fail(
                    "title_not_found",
                    "No Markdown level-one heading was found; no title was guessed.",
                    source=source_base,
                )
            line_number, source_line, title = match
            extraction_method = "markdown_h1"
        else:
            candidate = next(
                (
                    (line_number, line)
                    for line_number, line in enumerate(lines, start=1)
                    if line.strip()
                ),
                None,
            )
            if candidate is None:
                return self._fail(
                    "title_not_found",
                    "The text file contains no non-empty line; no title was guessed.",
                    source=source_base,
                )
            line_number, source_line = candidate
            title = source_line.strip()
            extraction_method = "text_first_nonempty_line"

        source = {
            **source_base,
            "line": line_number,
            "excerpt": source_line,
            "extraction_method": extraction_method,
        }
        output = {"title": title, "source": source}
        self._event_sink(
            {
                "event_type": "tool.completed",
                "timestamp": _utc_now(),
                "tool_id": CAPABILITY_ID,
                "tool_version": CAPABILITY_VERSION,
                "source": source,
                "title": title,
            }
        )
        return Success(output)

    @staticmethod
    def _first_markdown_h1(lines: list[str]) -> tuple[int, str, str] | None:
        fence_character: str | None = None
        fence_length = 0
        for line_number, line in enumerate(lines, start=1):
            if fence_character is not None:
                closing = _MARKDOWN_FENCE_CLOSE.match(line)
                if (
                    closing is not None
                    and closing.group(1)[0] == fence_character
                    and len(closing.group(1)) >= fence_length
                ):
                    fence_character = None
                    fence_length = 0
                continue

            opening = _MARKDOWN_FENCE_OPEN.match(line)
            if opening is not None:
                marker, info = opening.groups()
                if marker[0] != "`" or "`" not in info:
                    fence_character = marker[0]
                    fence_length = len(marker)
                    continue

            heading = _MARKDOWN_H1.match(line)
            if heading is None:
                continue
            raw_title = heading.group(1).strip()
            if re.fullmatch(r"#+", raw_title):
                title = ""
            else:
                title = re.sub(r"[ \t]+#+$", "", raw_title)
            if not title:
                continue
            return line_number, line, title
        return None

    def _fail(
        self,
        code: str,
        message: str,
        *,
        source_path: str | None = None,
        requested_path: str | None = None,
        source: dict[str, Any] | None = None,
    ) -> Failure:
        event: dict[str, Any] = {
            "event_type": "tool.failed",
            "timestamp": _utc_now(),
            "tool_id": CAPABILITY_ID,
            "tool_version": CAPABILITY_VERSION,
            "error_code": code,
            "message": message,
        }
        if requested_path is not None:
            event["requested_path"] = requested_path
        if source_path is not None:
            event["source_path"] = source_path
        if source is not None:
            event["source"] = source
        self._event_sink(event)
        return Failure(f"{code}: {message}")
