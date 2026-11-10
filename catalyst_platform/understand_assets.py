"""Static inspection of an asset package: a Skill manifest, the Python sources beside it.
Nothing here executes the package, follows a link out of the trusted root or reads a byte
the caller did not select.
"""

from __future__ import annotations

import ast
import re

from pathlib import Path
from typing import Mapping, Sequence

from .understand_manifest import _parse_frontmatter
from .understand_models import (
    AssetCandidateOutput,
    EvidenceRef,
    GroundedItem,
    SourceRecord,
    _new_item,
    _sha,
)


class _AssetMixin:
    """Methods of :class:`UnderstandPort` that belong to this concern."""

    @staticmethod
    def _inspect_asset(
        sources: Sequence[tuple[Path, str]],
        records: Sequence[SourceRecord],
        evidence_by_locator: Mapping[tuple[str, str], EvidenceRef],
        source_root: Path,
    ) -> tuple[AssetCandidateOutput, list[GroundedItem], list[GroundedItem]]:
        first_path, relative = sources[0]
        first_record = next((item for item in records if item.relative_path == relative), records[0] if records else None)
        if first_record is None:
            raise ValueError("asset inventory is empty")
        facts: list[GroundedItem] = []
        unknowns: list[GroundedItem] = []
        if first_path.name.casefold() == "skill.md":
            text = first_path.read_text(encoding="utf-8-sig")
            manifest, body = _parse_frontmatter(text)
            root = first_path.parent
            # The ecosystem spells this folder both ways; read whichever exists,
            # in a stable order, and never follow a link out of the trusted root.
            reference_dirs = [
                folder for folder in (root / "references", root / "reference")
                if folder.is_dir() and not folder.is_symlink()
            ]
            references = tuple(sorted(
                (item.relative_to(source_root).as_posix() for folder in reference_dirs for item in folder.glob("*")
                 if item.is_file() and not item.is_symlink()),
                key=str.casefold,
            ))
            scripts = tuple(sorted((item.relative_to(source_root).as_posix() for item in (root / "scripts").glob("*") if item.is_file() and not item.is_symlink()), key=str.casefold)) if (root / "scripts").is_dir() else ()
            # User-provided instructions remain quoted evidence and are never executed.
            entry = next((item for key, item in evidence_by_locator.items() if key[0] == first_record.source_id), None)
            if entry:
                facts.append(_new_item("skill_metadata", manifest.get("name", root.name), manifest.get("description", "metadata absent"), (entry,)))
            candidate = AssetCandidateOutput(
                "skill", manifest.get("name", root.name), relative, first_record.source_sha256,
                description=manifest.get("description", ""), version=manifest.get("version"),
                declared_tools=tuple(filter(None, re.split(r"[, ]+", manifest.get("tools", "")))),
                reference_paths=references, script_paths=scripts,
            )
            return candidate, facts, unknowns

        ast_files = [(path, rel, record) for path, rel in sources if path.suffix.casefold() == ".py" for record in records if record.relative_path == rel]
        imports: set[str] = set()
        entrypoints: set[str] = set()
        dependencies: set[str] = set()
        effects: set[str] = set()
        for path, rel, record in ast_files:
            def at_line(line: int) -> tuple[EvidenceRef, ...]:
                found = evidence_by_locator.get((record.source_id, f"line:{line}"))
                return (found,) if found else ()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=rel)
            except (OSError, UnicodeDecodeError, SyntaxError):
                unknowns.append(_new_item("unknown", rel, "Python source could not be parsed into AST.", (), evidence_class="unresolved", uncertainty="syntax or encoding failure"))
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    values = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    for value in values:
                        imports.add(value)
                        dependencies.add(value.split(".")[0])
                        facts.append(_new_item("import", value, value, at_line(node.lineno)))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    name = node.name
                    if name in {"main", "app", "run", "execute"}:
                        entrypoints.add(f"{rel}:{node.lineno}:{name}")
                    facts.append(_new_item(kind, name, f"{kind} {name} defined at line {node.lineno}.", at_line(node.lineno)))
                elif isinstance(node, ast.Call):
                    callee = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else "dynamic_call"
                    facts.append(_new_item("call", callee, f"Call expression at line {getattr(node, 'lineno', 0)}.", at_line(getattr(node, 'lineno', 0))))
                    if callee.casefold() in {"invoke", "execute", "dispatch", "call_tool"}:
                        effects.add("tool_or_delegate_call")
                elif isinstance(node, ast.ExceptHandler):
                    exc_name = ast.unparse(node.type) if node.type is not None else "BaseException"
                    facts.append(_new_item("exception", exc_name, f"Exception handler at line {node.lineno}.", at_line(node.lineno)))
                elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
                    facts.append(_new_item("state_write", "subscript_assignment", f"Mutable state assignment at line {node.lineno}.", at_line(node.lineno)))
                elif isinstance(node, ast.Name) and "cancel" in node.id.casefold():
                    facts.append(_new_item("cancel", node.id, f"Cancellation symbol referenced at line {node.lineno}.", at_line(node.lineno)))
            if rel.endswith(("main.py", "app.py", "__main__.py")):
                entrypoints.add(rel)
            code = path.read_text(encoding="utf-8-sig", errors="replace")
            if re.search(r"\b(open|write_text|write_bytes|unlink|remove)\s*\(", code):
                effects.add("filesystem_operation")
            if re.search(r"\b(subprocess|requests|httpx|socket|urllib)\b", code):
                effects.add("external_process_or_network_import")
        if not ast_files:
            unknowns.append(_new_item("unknown", "python_structure", "No supported Python source was present for AST inspection.", (), evidence_class="unresolved", uncertainty="language-specific structure unavailable"))
        candidate = AssetCandidateOutput(
            "repository", first_path.name if first_path.is_dir() else first_path.stem, relative,
            _sha("\n".join(f"{item.relative_path}:{item.source_sha256}" for item in records).encode("utf-8")),
            declared_tools=tuple(sorted(value for value in imports if any(term in value.casefold() for term in ("tool", "client", "worker")))),
            dependencies=tuple(sorted(dependencies)), entrypoints=tuple(sorted(entrypoints)), effects=tuple(sorted(effects)),
        )
        return candidate, facts, unknowns
