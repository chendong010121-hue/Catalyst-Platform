"""Build a comparable capability claim from a Skill package, deterministically.

This is a mapping layer over the existing Understand port, not a second
understanding engine:

* :class:`UnderstandPort` inventories the package and produces line-level
  evidence — source id, locator, verbatim quote, span digest, content revision;
* this module only *selects and classifies* those evidence lines into claim
  fields.  It never opens the package itself, never rewrites a quote, never
  calls a model and never executes anything;
* every field the package does not declare becomes a ``why.unknowns`` entry.
  A package that cannot satisfy the schema minimums (no description text, no
  declared obligation) is refused rather than filled in;
* which form a directory is comes from its declared markers
  (``SOURCE_PLANS`` / :func:`detect_kind`), not from a guess: a form whose
  decoder is not wired yet is named and refused, never read as a Skill.

What the selector treats as declared is fixed and inspectable (``_SECTIONS``,
``_OBLIGATION_MARKER``): a heading names a claim field, list items under that
heading carry it, a numbered heading is a procedure step, and an obligation is
either such an item or a line that states a rule in the imperative.  Every
selected line is quoted back with its exact locus, so a reviewer can trim the
claim without re-reading the package.
"""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .capability_claim import claim_digest, validate_claim
from .understand_only import (
    EvidenceRef,
    SourceRecord,
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
    UnderstandingResult,
)

BUILDER_VERSION = "0.1"

# A claim longer than this stops being readable and comparable; the receipt says
# when the cut happened, so a truncated claim is never silently complete.
OBLIGATION_LIMIT = 40
MAX_REFERENCE_FILES = 24
MAX_REFERENCE_BYTES = 1024 * 1024

CLAIM_BUILT = "CLAIM_BUILT"
INSUFFICIENT_SOURCE = "INSUFFICIENT_SOURCE"
UNSUPPORTED_PACKAGE = "UNSUPPORTED_PACKAGE"
NEEDS_RESPONSIBILITY_KEY = "NEEDS_RESPONSIBILITY_KEY"
INVALID_CLAIM = "INVALID_CLAIM"

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_KEY = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_KINDS = ("skill", "workflow", "agent", "plugin", "code", "document-set")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_FENCE = re.compile(r"^\s*(?:```|~~~)")
_LIST_ITEM = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
_LABELED = re.compile(r"^(?:`[^`]+`|\*\*[^*]+\*\*)[:：]")
_LINE_LOCATOR = re.compile(r"^line:(\d+)$")
_FIELD_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s+(.*))?$")
_BLOCK_SCALAR = re.compile(r"^[|>][+-]?$")

# What each package form declares itself to be, and whether a decoder for it is
# wired.  Detection reads declared markers only — the file the ecosystem itself
# uses to say "this is a skill / a plugin / an agent" — so a wrong answer means a
# missing marker, never a guess from a folder's contents.
SOURCE_PLANS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("skill", ("SKILL.md",), "READY"),
    ("plugin", (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"), "PLANNED"),
    ("agent", ("agent_state/AGENTS.md",), "PLANNED"),
)

# Headings that name a claim field.  Ordered: the first match wins.
_SECTIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("obligations", re.compile(
        r"^(?:rules?|hard rules?|safety|safety rules?|requirements?|constraints?|guardrails?"
        r"|polic(?:y|ies)|mandatory|before you start|getting started|procedure|steps?"
        r"|workflow|checklist|how to use|规则|要求|安全|约束|禁止|义务|规范|前置|准备工作|步骤|流程)", re.I)),
    ("quick_start", re.compile(
        r"^(?:quick ?start|quickstart|usage|example|examples|快速开始|用法|示例|怎么用)", re.I)),
    ("inputs", re.compile(
        r"^(?:inputs?|required inputs?|you (?:will )?need|prerequisites?|输入|所需输入|前置输入|前置条件)", re.I)),
    ("outputs", re.compile(
        r"^(?:outputs?|deliverables?|results?|输出|产物|交付物|结果)", re.I)),
    ("include", re.compile(
        r"^(?:when to use|use when|applicability|applies to|适用范围|适用场景|何时使用|什么时候用)", re.I)),
    ("exclude", re.compile(
        r"^(?:when not to use|not for|do not use|does not apply|不适用|排除|不用于)", re.I)),
    ("known_limits", re.compile(
        r"^(?:known limits?|limits?|limitations?|caveats?|known issues|boundaries"
        r"|限制|局限|边界|已知问题)", re.I)),
    ("failure_modes", re.compile(
        r"^(?:failures?|when it fails|failure modes?|errors?|失败|失败情形|出错)", re.I)),
)

# A line that imposes a duty.  A heading alone never does, a fenced block is an
# example of a tool, and a table row is a specification to read, not an
# instruction to the reader.  Strong modals hold anywhere; weak ones only in a
# line that is already a list item.
_STRONG_MARKER = re.compile(
    r"\b(?:must|must not|never|refuse|cannot|may not|do not|don't)\b|必须|不得|禁止|严禁|务必",
    re.I,
)
_WEAK_MARKER = re.compile(
    r"\b(?:always|required|non-negotiable|only one)\b|不要|只能|一律",
    re.I,
)

# A hand-off states where this capability stops: it names the skill to use
# instead.  That sentence is the declared boundary the comparator needs, so it
# becomes an exclusion rather than being dropped as prose.
_HANDOFF = re.compile(r"`([a-z0-9][a-z0-9-]*)`\s+skill|(?:the\s+)?([a-z0-9][a-z0-9-]*)\s+skill\b", re.I)
_HANDOFF_MARKER = re.compile(r"\binstead\b|改用|转用|而不是", re.I)

# Fields no static reader can observe.  A claim states them as unknown and names
# why, so nobody mistakes silence for a measurement.
_BEHAVIOURAL_UNKNOWNS: tuple[tuple[str, str], ...] = (
    ("what.performance", "包内没有性能声明，构建器也没有实测数据"),
    ("what.cost", "包内没有成本声明，构建器也没有实测数据"),
    ("what.quality", "质量没有实测数据；静态构建不评价优劣"),
    ("what.robustness", "稳健性没有实测数据"),
    ("capability.license", "构建器只读包内文件，未读取仓库级许可证信息"),
)

_FIELD_UNKNOWN_REASONS = {
    "inputs": "源文件没有输入声明（无 Inputs / 输入 类小节）",
    "outputs": "源文件没有输出声明（无 Outputs / 输出 类小节）",
    "include": "源文件没有适用范围声明（无 When to use / 适用范围 类小节）",
    "exclude": "源文件没有不适用声明（无 When not to use / 不适用 类小节）",
    "known_limits": "源文件没有限制声明（无 Limits / 限制 类小节）",
    "failure_modes": "源文件没有失效模式声明（无 Failure / 失败 类小节）",
}


@dataclass(frozen=True)
class _Line:
    """One inventory line, with the structure it sits in."""

    ref: EvidenceRef
    number: int
    kind: str  # "text" | "heading" | "fence"
    section: str | None


@dataclass(frozen=True)
class ClaimBuildResult:
    """A built claim, or an explicit refusal to build one."""

    status: str
    reason: str
    claim: Mapping[str, Any] | None = None
    receipt: Mapping[str, Any] = field(default_factory=dict)
    violations: tuple[str, ...] = ()

    @property
    def built(self) -> bool:
        return self.status == CLAIM_BUILT and self.claim is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "claim": dict(self.claim) if self.claim is not None else None,
            "receipt": dict(self.receipt),
            "violations": list(self.violations),
        }


def _sha(text: str | bytes) -> str:
    raw = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(raw).hexdigest()


def _section_of(heading_text: str) -> str | None:
    text = heading_text.strip().strip("*`_ ").rstrip(":：").strip()
    for key, pattern in _SECTIONS:
        if pattern.search(text):
            return key
    return None


def _lines(evidence: Iterable[EvidenceRef]) -> tuple[_Line, ...]:
    """Order evidence into lines and attach the heading each line sits under."""
    rows: list[tuple[int, EvidenceRef]] = []
    for ref in evidence:
        match = _LINE_LOCATOR.match(ref.locator)
        if match:
            rows.append((int(match.group(1)), ref))
    rows.sort(key=lambda row: (row[1].relative_path.casefold(), row[0]))
    out: list[_Line] = []
    stack: list[tuple[int, str]] = []
    fenced = False
    current_path: str | None = None
    for number, ref in rows:
        if ref.relative_path != current_path:
            current_path, stack, fenced = ref.relative_path, [], False
        text = ref.quote
        section = stack[-1][1] if stack else None
        if _FENCE.match(text):
            fenced = not fenced
            out.append(_Line(ref, number, "fence", section))
            continue
        if fenced:
            out.append(_Line(ref, number, "fence", section))
            continue
        heading = _HEADING.match(text.strip())
        if heading:
            level = len(heading.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            found = _section_of(heading.group(2))
            if found is not None:
                stack.append((level, found))
            out.append(_Line(ref, number, "heading", stack[-1][1] if stack else None))
            continue
        out.append(_Line(ref, number, "text", section))
    return tuple(out)


def _clean(statement: str) -> str:
    text = _LIST_ITEM.sub("", statement.strip()).replace("**", "")
    return re.sub(r"\s+", " ", text).strip()


def _section_items(lines: Sequence[_Line], section: str) -> list[_Line]:
    return [
        row for row in lines
        if row.kind == "text" and row.section == section and _LIST_ITEM.match(row.ref.quote.strip())
    ]


def _section_first_text(lines: Sequence[_Line], section: str) -> _Line | None:
    return next(
        (row for row in lines if row.kind == "text" and row.section == section and row.ref.quote.strip()),
        None,
    )


def _obligation_lines(lines: Sequence[_Line], limit: int) -> tuple[list[_Line], bool]:
    selected: list[_Line] = []
    seen: set[str] = set()
    for row in lines:
        if row.kind != "text":
            continue
        text = row.ref.quote.strip()
        if not text or text.startswith("|"):
            continue
        item = bool(_LIST_ITEM.match(text))
        statement = _clean(text)
        if _LABELED.match(statement) and not _STRONG_MARKER.search(text):
            # "- `path`: what it is" is a definition, not a duty.
            continue
        duty = (
            (item and row.section == "obligations")
            or bool(_STRONG_MARKER.search(text))
            or (item and bool(_WEAK_MARKER.search(text)))
        )
        if not duty:
            continue
        if not statement or statement.casefold() in seen:
            continue
        seen.add(statement.casefold())
        selected.append(row)
    return selected[:limit], len(selected) > limit


def _handoff_lines(lines: Sequence[_Line], own_id: str) -> list[_Line]:
    """Lines that send the reader to another skill: a declared applicability boundary."""
    found: list[_Line] = []
    for row in lines:
        if row.kind != "text":
            continue
        text = row.ref.quote.strip()
        if not _HANDOFF_MARKER.search(text):
            continue
        match = _HANDOFF.search(text)
        if match is None:
            continue
        target = (match.group(1) or match.group(2) or "").casefold()
        if target and target != own_id.casefold():
            found.append(row)
    return found


def _handoff_sentence(text: str) -> str:
    """The sentence that carries the hand-off, quoted out of a longer line."""
    for sentence in re.split(r"(?<=[.!?。！？])\s*", text.strip()):
        if _HANDOFF_MARKER.search(sentence) and _HANDOFF.search(sentence):
            return _clean(sentence)
    return _clean(text)


def _frontmatter_value(value: str | None) -> str | None:
    """A field's text on one line, or ``None`` when it declares no text at all.

    A block marker on its own (``description: >-`` with nothing indented under
    it) is not a value: quoting the marker would put ``>-`` in the claim as if
    the package had said it.
    """
    text = re.sub(r"\s+", " ", (value or "").strip()).strip("\"'")
    if not text or _BLOCK_SCALAR.match(text):
        return None
    return text


def _frontmatter_line(lines: Sequence[_Line], key: str) -> _Line | None:
    """The line that carries a frontmatter field's text.

    For a block scalar the marker line carries no text, so the evidence is the
    first line under it — the first thing the field actually says, quoted
    verbatim instead of the ``>-`` that introduced it.
    """
    text_rows = sorted(
        (row for row in lines if row.kind == "text"),
        key=lambda row: (row.ref.relative_path.casefold(), row.number),
    )
    for index, row in enumerate(text_rows):
        match = _FIELD_LINE.match(row.ref.quote.strip())
        if match is None or match.group(1) != key:
            continue
        if not _BLOCK_SCALAR.match((match.group(2) or "").strip()):
            return row
        for follower in text_rows[index + 1:]:
            return follower if follower.ref.relative_path == row.ref.relative_path else None
        return None
    return None


def detect_kind(directory: Path) -> tuple[str, str]:
    """Name the container a package directory declares itself to be.

    Returns ``(kind, reason)``; the reason names the marker that decided it, so a
    refusal can say what was seen rather than only what was missing.  A form
    whose plan is not ``READY`` is still identified — the caller refuses instead
    of reading it with the decoder of another form.
    """
    if not directory.is_dir():
        return "repository", "包目录不存在，没有可识别的资产标记"
    for kind, markers, _ in SOURCE_PLANS:
        for marker in markers:
            if (directory / marker).is_file():
                return kind, f"存在 {marker}"
    manifest = directory / "package.json"
    if manifest.is_file() and not manifest.is_symlink():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, ValueError):
            data = None
        if isinstance(data, Mapping) and "penguin" in data:
            return "plugin", "package.json 声明了 penguin 字段"
    try:
        files = [path for path in directory.iterdir() if path.is_file()]
    except OSError:
        files = []
    if files and all(path.suffix.casefold() == ".py" for path in files):
        return "code", "目录里只有 Python 源码"
    return "repository", "没有技能 / 插件 / Agent 的标记文件"


def _sections_found(lines: Sequence[_Line]) -> list[str]:
    return sorted({row.section for row in lines if row.kind == "heading" and row.section is not None})


class CapabilityClaimBuilder:
    """Turn one Skill package into one comparable claim, or refuse in writing."""

    def __init__(self, *, port: UnderstandPort | None = None, obligation_limit: int = OBLIGATION_LIMIT) -> None:
        if type(obligation_limit) is not int or obligation_limit < 1:
            raise ValueError("obligation_limit must be a positive integer")
        self._port = port or UnderstandPort()
        self._limit = obligation_limit

    def build(
        self,
        *,
        source_root: str | Path,
        package: str | Path,
        responsibility_key: str | None,
        claim_id: str | None = None,
        version: str | None = None,
        kind: str | None = None,
        interface_id: str | None = None,
        interface_version: str = "1",
    ) -> ClaimBuildResult:
        if responsibility_key is None:
            return ClaimBuildResult(
                NEEDS_RESPONSIBILITY_KEY,
                "库内分组键由审阅人按职责指定，构建器不代填（填了什么，比较就按什么分组）",
            )
        if not _KEY.match(responsibility_key):
            return ClaimBuildResult(
                NEEDS_RESPONSIBILITY_KEY,
                f"responsibility_key 不合形状（小写字母/数字/连字符）：{responsibility_key}",
            )
        if kind is not None and kind not in _KINDS:
            raise ValueError(f"unsupported capability kind: {kind}")
        if interface_id is not None and not _ID.match(interface_id):
            raise ValueError(f"unsupported interface id: {interface_id}")

        root = Path(source_root).expanduser().resolve()
        directory = Path(package).expanduser()
        directory = (directory if directory.is_absolute() else root / directory).resolve()
        name = claim_id or directory.name
        receipt: dict[str, Any] = {
            "builder": {"name": "capability_claim_build", "version": BUILDER_VERSION},
            "source_root": root.as_posix(),
            "package": directory.as_posix(),
            "claim_id": name,
            "responsibility_key": responsibility_key,
        }
        if not _ID.match(name):
            return ClaimBuildResult(
                UNSUPPORTED_PACKAGE,
                f"包名不是合法的 claim id（字母/数字/下划线/连字符）：{name}",
                receipt=receipt,
            )
        detected, detected_reason = detect_kind(directory)
        plan = next((status for kind, _, status in SOURCE_PLANS if kind == detected), "PLANNED")
        receipt["detection"] = {"kind": detected, "reason": detected_reason, "decoder": plan}
        if plan != "READY":
            return ClaimBuildResult(
                UNSUPPORTED_PACKAGE,
                f"识别为 {detected}（{detected_reason}）：该形态的解码器尚未接入，目前只构建技能包声明",
                receipt=receipt,
            )
        manifest = directory / "SKILL.md"

        primary = self._understand(root, manifest, f"claim-build:{name}:{_sha(manifest.read_bytes())[:12]}", name)
        receipt["understand"] = {
            "request_id": primary.request_id,
            "status": primary.status,
            "stopping_reason": primary.stopping_reason,
            "coverage": [[row.question_id, row.status] for row in primary.coverage_receipt],
            "source_warnings": list(primary.source_warnings),
        }
        candidate = primary.asset_candidate
        if primary.status in {"DENIED", "UNSUPPORTED"} or candidate is None:
            return ClaimBuildResult(
                UNSUPPORTED_PACKAGE,
                "Understand 拒绝或无法读取这个包，未构建声明",
                receipt=receipt,
            )
        if candidate.asset_type != "skill":
            return ClaimBuildResult(
                UNSUPPORTED_PACKAGE,
                f"Understand 把这个包识别为 {candidate.asset_type}，不是技能包",
                receipt=receipt,
            )

        secondary = self._reference_run(root, candidate.reference_paths, name, receipt)
        evidence: dict[tuple[str, str], EvidenceRef] = {
            (ref.relative_path, ref.locator): ref
            for ref in (*primary.evidence_refs, *(secondary.evidence_refs if secondary else ()))
        }
        inventory: tuple[SourceRecord, ...] = (*primary.source_inventory, *(secondary.source_inventory if secondary else ()))
        lines = _lines(evidence.values())
        prefix = posixpath.dirname(primary.source_inventory[0].relative_path)
        receipt["scope"] = sorted({row.ref.relative_path for row in lines})
        receipt["sources"] = [
            {"path": row.relative_path, "sha256": row.source_sha256, "locators": row.locator_count}
            for row in inventory
        ]
        receipt["evidence_truncated"] = (
            sum(row.locator_count for row in inventory)
            > len(primary.evidence_refs) + len(secondary.evidence_refs if secondary else ())
        )

        description = _frontmatter_value(candidate.description)
        if description is None:
            return ClaimBuildResult(
                INSUFFICIENT_SOURCE,
                "frontmatter 的 description 缺失、为空，或只有块标量标记（>- / |）而没有缩进内容；职责陈述不代填",
                receipt=receipt,
            )
        description_line = _frontmatter_line(lines, "description")
        if description_line is None:
            return ClaimBuildResult(
                INSUFFICIENT_SOURCE,
                "description 这一行没有出现在 Understand 的行级证据里，无法给出可追责的职责陈述",
                receipt=receipt,
            )

        obligations, obligations_cut = _obligation_lines(lines, self._limit)
        if not obligations:
            return ClaimBuildResult(
                INSUFFICIENT_SOURCE,
                "包内没有可识别的义务句（无规则类小节，也无 must/never/必须 类陈述）：声明达不到 schema 最小要求，拒绝代填",
                receipt={**receipt, "sections_found": _sections_found(lines)},
            )

        uses: dict[tuple[str, int, str], str] = {}
        rows_by_id: dict[str, _Line] = {}

        def use(line: _Line, path: str) -> str:
            key = (line.ref.relative_path, line.number, path)
            if key not in uses:
                identifier = f"e{len(uses) + 1}"
                uses[key] = identifier
                rows_by_id[identifier] = line
            return uses[key]

        what: dict[str, Any] = {
            "obligations": [
                {
                    "statement": _clean(row.ref.quote),
                    "evidence": [use(row, f"what.obligations[{index}]")],
                    "evidence_class": "EXPLICIT",
                }
                for index, row in enumerate(obligations)
            ],
            "inputs": [],
            "outputs": [],
            "applicability": {"include": [], "exclude": []},
            "known_limits": [],
            "failure_modes": [],
        }
        unknowns: list[dict[str, str]] = []
        section_map = (
            ("inputs", "inputs", "what.inputs"),
            ("outputs", "outputs", "what.outputs"),
            ("include", "include", "what.applicability.include"),
            ("exclude", "exclude", "what.applicability.exclude"),
            ("known_limits", "known_limits", "what.known_limits"),
            ("failure_modes", "failure_modes", "what.failure_modes"),
        )
        for key, section, path in section_map:
            rows = _section_items(lines, section)
            if not rows:
                single = _section_first_text(lines, section)
                rows = [single] if single is not None else []
            entries = [(row, _clean(row.ref.quote)) for row in rows]
            if key == "exclude":
                seen = {statement for _, statement in entries}
                for row in _handoff_lines(lines, name):
                    statement = _handoff_sentence(row.ref.quote)
                    if statement not in seen:
                        entries.append((row, statement))
                        seen.add(statement)
            if not entries:
                unknowns.append({"field": path, "reason": _FIELD_UNKNOWN_REASONS[key]})
                continue
            target = what["applicability"] if key in {"include", "exclude"} else what
            for index, (row, statement) in enumerate(entries):
                target[key].append({
                    "statement": statement,
                    "evidence": [use(row, f"{path}[{index}]")],
                    "evidence_class": "EXPLICIT",
                })

        permissions: list[dict[str, Any]] = []
        tools_line = _frontmatter_line(lines, "tools")
        if candidate.declared_tools and tools_line is not None:
            for index, tool in enumerate(candidate.declared_tools):
                permissions.append({
                    "statement": f"声明使用工具 {tool}",
                    "evidence": [use(tools_line, f"how.permissions[{index}]")],
                    "evidence_class": "EXPLICIT",
                })
        else:
            unknowns.append({
                "field": "how.permissions",
                "reason": "frontmatter 没有 tools 字段，正文也没有权限声明",
            })

        unknowns.append({
            "field": "how.side_effects",
            "reason": "源文件未声明运行副作用；静态构建不推断写行为",
        })
        unknowns.extend({"field": path, "reason": reason} for path, reason in _BEHAVIOURAL_UNKNOWNS)

        quick_start, quick_start_source = self._quick_start(lines, name, description)
        content_revision = _sha("\n".join(sorted({f"{row.relative_path}:{row.source_sha256}" for row in inventory})))[:12]
        claim: dict[str, Any] = {
            "claim_version": 1,
            "capability": {
                "id": name,
                "responsibility_key": responsibility_key,
                "version": version or candidate.version or f"content-{content_revision}",
                "kind": kind or "skill",
                "statement": description,
                "evidence": [use(description_line, "capability.statement")],
            },
            "what": what,
            "how": {
                "entry": primary.source_inventory[0].relative_path,
                "interface": {"id": interface_id or "agent-skill", "version": interface_version},
                "side_effects": [],
                "permissions": permissions,
            },
            "why": {"evidence": [], "unknowns": unknowns},
            "quick_start": quick_start,
        }
        claim["why"]["evidence"] = [
            {
                "id": identifier,
                "source_id": f"pkg:{name}",
                "revision": rows_by_id[identifier].ref.source_revision,
                "locator": _claim_locator(rows_by_id[identifier].ref.relative_path, prefix, rows_by_id[identifier].number),
                "quote": rows_by_id[identifier].ref.quote,
                "span_sha256": rows_by_id[identifier].ref.span_sha256,
                "strength": "DIRECT_QUOTE",
                "field": path_key[2],
            }
            for path_key, identifier in sorted(uses.items(), key=lambda item: int(item[1][1:]))
        ]

        violations = tuple(validate_claim(claim))
        receipt.update({
            "version": {
                "value": claim["capability"]["version"],
                "from": "argument" if version else "frontmatter" if candidate.version else "content-digest",
            },
            "classification": {
                "kind": {"value": claim["capability"]["kind"], "from": "argument" if kind else "package"},
                "interface": {
                    "value": claim["how"]["interface"],
                    "from": "argument" if interface_id else "host-format",
                },
            },
            "obligations": {"selected": len(obligations), "limit": self._limit, "truncated": obligations_cut},
            "sections_found": _sections_found(lines),
            "claim_locator_base": prefix or ".",
            "evidence_used": len(claim["why"]["evidence"]),
            "files_read": receipt["scope"],
            "unknowns": [row["field"] for row in unknowns],
            "quick_start_source": quick_start_source,
            "claim_digest": claim_digest(claim),
        })
        if violations:
            return ClaimBuildResult(
                INVALID_CLAIM,
                "构建出的声明没有通过校验，拒绝输出",
                receipt=receipt,
                violations=violations,
            )
        return ClaimBuildResult(
            CLAIM_BUILT,
            f"从 {len(receipt['scope'])} 个文件构建出 {len(obligations)} 条义务",
            claim=claim,
            receipt=receipt,
        )

    def _understand(self, root: Path, manifest: Path, request_id: str, name: str) -> UnderstandingResult:
        return self._port.understand(
            UnderstandingRequest(
                request_id=request_id,
                message=f"检查 skill 包 {name}",
                source_refs=(manifest,),
                intent=UnderstandIntent.ASSET_INSPECT,
                requested_depth="targeted",
                budget_steps=4,
            ),
            source_root=root,
        )

    def _reference_run(
        self,
        root: Path,
        paths: Sequence[str],
        name: str,
        receipt: dict[str, Any],
    ) -> UnderstandingResult | None:
        """Inventory referenced text files too: rules often live there, not in SKILL.md."""
        selected: list[Path] = []
        for relative in paths:
            path = root / relative
            if path.suffix.casefold() not in {".md", ".markdown", ".txt", ".rst"}:
                continue
            if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_REFERENCE_BYTES:
                continue
            selected.append(path)
        selected.sort(key=lambda path: path.as_posix().casefold())
        selected = selected[:MAX_REFERENCE_FILES]
        receipt["references"] = {
            "declared": list(paths),
            "read": [path.relative_to(root).as_posix() for path in selected],
        }
        if not selected:
            return None
        return self._port.understand(
            UnderstandingRequest(
                request_id=f"claim-build-references:{name}",
                message=f"检查 skill 包 {name} 的参考文件",
                source_refs=tuple(selected),
                intent=UnderstandIntent.ASSET_INSPECT,
                requested_depth="targeted",
                budget_steps=4,
            ),
            source_root=root,
        )

    @staticmethod
    def _quick_start(lines: Sequence[_Line], name: str, description: str) -> tuple[dict[str, Any], str]:
        declared = _section_first_text(lines, "quick_start")
        expected = _clean(declared.ref.quote) if declared is not None else description
        return (
            {
                "prompt": f"use {name} skill",
                "expected": expected,
                "observable": False,
                "limitation": "静态构建：没有执行过一次真实调用，observable 未验证；expected 取自包内声明，不是观测结果",
                "cost": "unknown",
            },
            "declared-section" if declared is not None else "description",
        )


def _claim_locator(relative_path: str, package_prefix: str, number: int) -> str:
    """Package-relative path plus line, so a reviewer can open the quote."""
    inner = relative_path[len(package_prefix) + 1:] if package_prefix and relative_path.startswith(package_prefix + "/") else relative_path
    return f"{inner}:L{number}"


def build_claim(
    *,
    source_root: str | Path,
    package: str | Path,
    responsibility_key: str | None,
    claim_id: str | None = None,
    version: str | None = None,
    kind: str | None = None,
    interface_id: str | None = None,
    interface_version: str = "1",
    obligation_limit: int = OBLIGATION_LIMIT,
) -> ClaimBuildResult:
    """Convenience wrapper around :class:`CapabilityClaimBuilder`."""
    return CapabilityClaimBuilder(obligation_limit=obligation_limit).build(
        source_root=source_root,
        package=package,
        responsibility_key=responsibility_key,
        claim_id=claim_id,
        version=version,
        kind=kind,
        interface_id=interface_id,
        interface_version=interface_version,
    )


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Build a capability claim from a Skill package (read-only).")
    parser.add_argument("--source-root", required=True, help="trusted root the package lives under")
    parser.add_argument("--package", required=True, help="package directory, absolute or relative to the root")
    parser.add_argument("--responsibility-key", required=True, help="competing-group key, decided by the reviewer")
    parser.add_argument("--id", dest="claim_id", default=None, help="claim id (default: package directory name)")
    parser.add_argument("--version", default=None)
    parser.add_argument("--kind", default=None, choices=_KINDS, help="default: detected from the package markers")
    parser.add_argument("--interface-id", default=None, help="default: agent-skill")
    parser.add_argument("--interface-version", default="1")
    parser.add_argument("--obligation-limit", type=int, default=OBLIGATION_LIMIT)
    parser.add_argument("--out", default=None, help="write the claim here (default: <root>/.catalyst/capability-claims/<id>.claim.json)")
    parser.add_argument("--dry-run", action="store_true", help="print the receipt and write nothing")
    args = parser.parse_args(argv)

    result = build_claim(
        source_root=args.source_root,
        package=args.package,
        responsibility_key=args.responsibility_key,
        claim_id=args.claim_id,
        version=args.version,
        kind=args.kind,
        interface_id=args.interface_id,
        interface_version=args.interface_version,
        obligation_limit=args.obligation_limit,
    )
    print(json.dumps(
        {"status": result.status, "reason": result.reason, "receipt": result.receipt, "violations": list(result.violations)},
        ensure_ascii=False,
        indent=2,
    ))
    if not result.built:
        return 2
    target = Path(args.out) if args.out else Path(args.source_root) / ".catalyst" / "capability-claims" / f"{result.claim['capability']['id']}.claim.json"
    if not args.dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.claim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target.as_posix()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
