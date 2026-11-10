"""What a package declares about itself: the bounded frontmatter reader, the allowlisted
Skill method files, and the strategy plan those method files imply.

A reader that cannot understand a shape leaves the key absent instead of guessing, so a
manifest this module cannot read never turns into an invented claim.
"""

from __future__ import annotations

import re

from pathlib import Path
from typing import Sequence

from .understand_models import SelectedSkill, UnderstandIntent, _sha


_SKILL_ROOT = Path(__file__).resolve().parents[1] / "platform-harness" / "skills"

_SKILL_STRATEGIES: dict[str, tuple[str, str]] = {
    "understand-source-inventory": ("source_inventory", "understand-source-inventory/SKILL.md"),
    "understand-document": ("document_grounding", "understand-document/SKILL.md"),
    "understand-enterprise-semantics": ("business_semantics", "understand-enterprise-semantics/SKILL.md"),
    "understand-asset-inspector": ("asset_inspection", "understand-asset-inspector/SKILL.md"),
    "understand-repository-map": ("repository_ast_map", "understand-repository-map/SKILL.md"),
    "understand-evidence-coverage": ("coverage_check", "understand-evidence-coverage/SKILL.md"),
}

_GENERATOR_METHOD_HEADING = "# Method B"

_GENERATOR_REFERENCE = "ontology-generator.md"

# The relation method lives in a reference whose head is the object-catalog contract this
# Port does not speak, so it is read from its own marker the way the generator file is read
# from its method heading. Nothing read it before: the file was loaded with the Skill and
# only the generator reference was ever put in front of the model, so a rule about one
# proposition per row, its own negation and its own scope could not change a reading.
_RELATION_METHOD_REFERENCE = "ontology-catalog-relations-v2.md"

_RELATION_METHOD_HEADING = "ATOMIC_RELATION_COVERAGE_V1"

_MAX_METHOD_BYTES = 8 * 1024

_FRONTMATTER_FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s+(.*))?$")

_FRONTMATTER_BLOCK = re.compile(r"^[|>][+-]?$")

def _frontmatter_body(lines: Sequence[str]) -> list[str]:
    """The lines that belong to one field, de-indented, without edge blank lines."""
    body = [line.rstrip() for line in lines]
    indents = [len(line) - len(line.lstrip()) for line in body if line.strip()]
    if not indents:
        return []
    cut = min(indents)
    body = [line[cut:] for line in body]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return body

def _frontmatter_text(lines: Sequence[str], *, folded: bool) -> str:
    """One text value out of a continued or block scalar.

    Breaks inside the value survive: a folded scalar turns a single break into
    a space and keeps a blank-line break, a literal one keeps every break. The
    trailing break is dropped for every chomping indicator — the value is read
    as a text field, never as a stream, so ``|``, ``|-`` and ``|+`` differ only
    where nothing here could observe it.
    """
    out = ""
    for line in lines:
        if not line.strip():
            out += "\n"
        elif not out or out.endswith("\n"):
            out += line.strip()
        else:
            out += (" " if folded else "\n") + line.strip()
    return out.strip("\n")

def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Read the top-level fields of a bounded YAML header, without PyYAML.

    Understood shapes: a single-line scalar, a scalar continued on indented
    lines, and a block scalar introduced by ``|`` or ``>`` with an optional
    chomping indicator. Every other shape — a nested mapping, a sequence, an
    anchor, a header that is never closed — is not interpreted: the key stays
    absent rather than guessed, and its indented lines are consumed with it so
    they cannot leak into the next field.
    """
    values: dict[str, str] = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return values, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return values, text
    index = 1
    while index < end:
        match = _FRONTMATTER_FIELD.match(lines[index])
        if match is None:
            index += 1
            continue
        key = match.group(1)
        inline = (match.group(2) or "").strip()
        index += 1
        body_start = index
        while index < end and (not lines[index].strip() or lines[index][:1] in {" ", "\t"}):
            index += 1
        body = _frontmatter_body(lines[body_start:index])
        block = bool(_FRONTMATTER_BLOCK.match(inline))
        if block:
            values[key] = _frontmatter_text(body, folded=inline[0] == ">")
        elif not inline:
            # A key whose whole value is on indented lines, unless those lines
            # are a nested mapping or a sequence: those shapes are not read.
            if body and _FRONTMATTER_FIELD.match(body[0]) is None and not body[0].startswith("- "):
                values[key] = _frontmatter_text(body, folded=True)
        elif body:
            values[key] = _frontmatter_text([inline, *body], folded=True)
        else:
            quoted = len(inline) >= 2 and inline[0] == inline[-1] and inline[0] in "\"'"
            values[key] = inline[1:-1] if quoted else inline
    return values, "\n".join(lines[end + 1 :])

class _SkillResolver:
    def __init__(self, root: Path = _SKILL_ROOT) -> None:
        self.root = root.resolve()

    def load(self, skill_ids: Sequence[str], *, progressive: bool = False) -> tuple[SelectedSkill, ...]:
        loaded: list[SelectedSkill] = []
        for skill_id in skill_ids:
            strategy_id, relative = _SKILL_STRATEGIES[skill_id]
            # Built-in mechanical steps are method metadata, not discoverable Skills.
            # Frozen copies can retain the built-in metadata layout. An explicit
            # custom SKILL.md still takes precedence; no method text is rewritten.
            if skill_id in {
                "understand-source-inventory", "understand-document", "understand-evidence-coverage",
            } and (self.root == _SKILL_ROOT.resolve() or (
                    not (self.root / relative).exists()
                    and (self.root / f"_methods/{skill_id}.md").is_file())):
                relative = f"_methods/{skill_id}.md"
            path = (self.root / relative).resolve()
            if not path.is_relative_to(self.root) or path.is_symlink() or not path.is_file():
                raise PermissionError(f"trusted Understand Skill is unavailable: {skill_id}")
            raw = path.read_bytes()
            if len(raw) > 128 * 1024:
                raise ValueError(f"trusted Understand Skill exceeds size limit: {skill_id}")
            frontmatter, body = _parse_frontmatter(raw.decode("utf-8-sig"))
            if frontmatter.get("name") != skill_id or not frontmatter.get("version"):
                raise ValueError(f"trusted Understand Skill metadata is invalid: {skill_id}")
            references: list[str] = []
            reference_texts: list[tuple[str, str]] = []
            reference_sha256: list[tuple[str, str]] = []
            if progressive:
                folder = path.parent / "references"
                if folder.is_dir():
                    for candidate in sorted(folder.iterdir()):
                        if candidate.suffix.casefold() != ".md" or not candidate.is_file() or candidate.is_symlink():
                            continue
                        if not candidate.resolve().is_relative_to(self.root) or candidate.stat().st_size > 64 * 1024:
                            raise ValueError(f"trusted Skill reference is invalid: {skill_id}")
                        relative_reference = candidate.relative_to(self.root).as_posix()
                        reference_body = candidate.read_text(encoding="utf-8-sig")
                        references.append(relative_reference)
                        reference_texts.append((relative_reference, reference_body))
                        # Hash what the model receives: the text after BOM strip and
                        # text-mode newline normalisation (LF). That is reproducible
                        # across checkouts, while the file's byte hash is not -- CRLF
                        # and LF working copies differ. The byte hash, when wanted, is
                        # `sha256sum` on the file and is recorded nowhere else.
                        reference_sha256.append(
                            (relative_reference, _sha(reference_body.encode("utf-8"))))
            loaded.append(
                SelectedSkill(
                    skill_id=skill_id,
                    version=frontmatter["version"],
                    skill_sha256=_sha(raw),
                    instruction_sha256=_sha(body.encode("utf-8")),
                    loaded_reference_paths=tuple(references),
                    strategy_id=strategy_id,
                    instructions=body,
                    reference_texts=tuple(reference_texts),
                    reference_sha256=tuple(reference_sha256),
                )
            )
        return tuple(loaded)

def _skill_plan(
    intent: UnderstandIntent,
    sources: Sequence[tuple[Path, str]],
    *,
    depth: str = "targeted",
) -> tuple[str, ...]:
    plan = ["understand-source-inventory"]
    if depth == "inventory":
        return tuple(plan)
    if intent is UnderstandIntent.KNOWLEDGE_PROPOSE:
        plan.append("understand-enterprise-semantics")
        if depth in {"semantic", "bounded_deep"}:
            plan.append("understand-document")
    elif intent is UnderstandIntent.ASSET_INSPECT:
        has_python = any(path.is_dir() or path.suffix.casefold() == ".py" for path, _ in sources)
        has_skill = any(path.name.casefold() == "skill.md" for path, _ in sources)
        if has_python:
            plan.append("understand-repository-map")
        if has_skill or not has_python:
            plan.append("understand-asset-inspector")
    else:
        plan.append("understand-document")
    plan.append("understand-evidence-coverage")
    return tuple(plan)

def _generator_method(skills: Sequence[SelectedSkill]) -> str:
    """Return the shipped method bodies, ready to put in front of a call.

    Two references make the method. ``ontology-generator.md`` carries how a candidate is
    modeled; ``ontology-catalog-relations-v2.md`` carries how one relation is read - one
    supported actor-action-target per row, with its own condition, scope, negation and
    effective status, and no polarity change to satisfy a structural rule. The second
    reached no request before this: the file shipped with the Skill and was loaded into
    the result, and only the generator reference was put in front of the model.

    The Skill package separates two things the Port must not confuse:

    * the head of ``ontology-generator.md`` declares its own envelope
      (``{scheme, items}``), which this Port does not accept, so it is skipped
      and the Port states its real envelope after the method text;
    * everything from the first ``# Method`` heading on is modeling method,
      which is what a model needs before it can produce a candidate at all. The
      relation reference is read the same way, from its own marker: its head is a
      catalog contract this Port does not speak.

    A missing file, an absent heading, or a section over the prompt budget leaves that
    section out whole: no method text is ever cut in half to make it fit, and a generator
    body that does not fit still falls back to the Skill instructions alone.

    The order is the reading order, not the file order: how a candidate is modeled comes
    first, and the relation guidance refines that candidate, so it follows - it says of
    itself that "the original candidate schema remains". Read off the reference list, the
    relation file sorts first by name, and the guidance arrived before the thing it refines.
    """
    skill = next(item for item in skills if item.skill_id == "understand-enterprise-semantics")
    text = skill.instructions
    sections: dict[int, str] = {}
    for relative, body in skill.reference_texts:
        if relative.endswith(_GENERATOR_REFERENCE):
            role, index = 0, body.find(_GENERATOR_METHOD_HEADING)
        elif relative.endswith(_RELATION_METHOD_REFERENCE):
            role, index = 1, body.find(_RELATION_METHOD_HEADING)
        else:
            continue
        if index < 0:
            continue
        section = body[index:].strip()
        if len(section.encode("utf-8")) > _MAX_METHOD_BYTES:
            continue
        sections[role] = section
    return text + "".join(chr(10) * 2 + sections[role] for role in sorted(sections))
