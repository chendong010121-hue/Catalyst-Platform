from __future__ import annotations

from pathlib import Path


class WorkspaceViolation(Exception):
    """A requested path is outside the authorized Workspace."""


class WorkspaceBoundary:
    def __init__(self, root: str | Path):
        candidate = Path(root).expanduser()
        if not candidate.is_dir():
            raise ValueError("workspace root must be an existing directory")
        self.root = candidate.resolve()

    def resolve(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path:
            raise WorkspaceViolation("path must be a non-empty relative string")
        requested = Path(relative_path)
        if requested.is_absolute():
            raise WorkspaceViolation("absolute paths are not allowed")
        lexical = self.root / requested
        try:
            lexical.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceViolation("parent traversal is not allowed") from exc
        resolved = lexical.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceViolation("symlink escape is not allowed") from exc
        return resolved

    def read(self, relative_path: str, *, max_bytes: int = 1_000_000) -> str:
        path = self.resolve(relative_path)
        if not path.is_file():
            raise WorkspaceViolation("read target is not a file")
        data = path.read_bytes()
        if len(data) > max_bytes:
            raise WorkspaceViolation("read target exceeds the bounded output limit")
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceViolation("read target is not UTF-8 text") from exc

    def write(self, relative_path: str, content: str) -> None:
        if not isinstance(content, str):
            raise WorkspaceViolation("write content must be text")
        path = self.resolve(relative_path)
        if not path.parent.is_dir() or path.is_dir():
            raise WorkspaceViolation("write target must be an existing file")
        path.write_text(content, encoding="utf-8", newline="")
