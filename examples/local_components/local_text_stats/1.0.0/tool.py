from __future__ import annotations

import hashlib
import re
from pathlib import Path

from agent_runtime.contracts import CapabilityDescriptor, Failure, Success


class LocalTextStatsTool:
    """Count content in the one file explicitly selected by the user."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    def describe(self):
        return CapabilityDescriptor(
            id="local_text_stats",
            name="Local text statistics",
            description="Count lines, words, and characters in the explicitly selected local text file.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "line_count": {"type": "integer"},
                    "word_count": {"type": "integer"},
                    "character_count": {"type": "integer"},
                    "source_sha256": {"type": "string"},
                },
                "required": ["line_count", "word_count", "character_count", "source_sha256"],
                "additionalProperties": False,
            },
        )

    def invoke(self, parameters, context):
        source = Path(parameters["path"]).expanduser().resolve()
        roots = tuple(Path(root).resolve() for root in context.allowed_source_roots)
        if not any(source == root or (root.is_dir() and source.is_relative_to(root)) for root in roots):
            return Failure("selected source is outside the current read scope")
        try:
            raw = source.read_bytes()
            text = raw.decode("utf-8")
        except FileNotFoundError:
            return Failure("selected source file was not found")
        except (OSError, UnicodeDecodeError):
            return Failure("selected source file could not be read as UTF-8")
        if len(raw) > 1048576:
            return Failure("selected source file exceeds the 1 MiB limit")
        words = re.findall('[A-Za-z0-9_]+', text)
        return Success({
            "line_count": len(text.splitlines()),
            "word_count": len(words),
            "character_count": len(text),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
        })
