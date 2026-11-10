"""Decide, without a model, whether a document is worth understanding at all.

Every paid call in this system starts from the verdict this module returns, and the
verdict is written to disk with its reasons, so "why did this file cost nothing?" is
a question with a stored answer rather than a claim.

The tiers are deliberately blunt:

``SKIP``       the bytes are unchanged, or nothing was extractable — no work exists.
``UNREAD``     reading stopped early, so "nothing here is new" cannot be concluded from
               what was read; it stays free and waits for a complete read.
``LINK_ONLY``  every name in it is already accepted and it carries neither a rule dialect
               nor prose — or it is an outline whose own material is already read whole.
``PROPOSE``    something in it is not represented yet; this is where money is spent.
``FULL``       a reviewer asked for a full reading of this exact source.

Only ``PROPOSE`` and ``FULL`` reach a model. Every detector here is a bounded heuristic and
is reported as such: it decides whether to spend, never what is true. Because that is the
whole claim of this layer, a document that was only partly read is never called "nothing
new": three of the signals below are positive evidence (an unknown name, rule language, a
page of prose), and the absence of positive evidence in an unread part proves nothing.
"""

from __future__ import annotations

import hashlib
import json
import re

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .understand_models import _TextUnit
from .wiki_mentions import EntityIndex, normalize_surface

SKIP = "SKIP"
UNREAD = "UNREAD"
LINK_ONLY = "LINK_ONLY"
PROPOSE = "PROPOSE"
FULL = "FULL"

TIERS = (SKIP, UNREAD, LINK_ONLY, PROPOSE, FULL)

_RECEIPT_VERSION = "catalyst.novelty.v1"
_UNKNOWN_LIMIT = 40

# Organisation-shaped Chinese surfaces. This is a proposal filter, not a dictionary:
# it decides whether to look for a model answer, and every candidate it raises is
# shown to the reviewer with the line it came from.
_ORG_SUFFIXES = (
    "委员会", "办公室", "分公司", "子公司", "事业部", "研究院", "指挥部",
    "中心", "公司", "集团", "部门", "处", "科", "室", "部",
)
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,64}")
_LATIN_NAME = re.compile(r"\b(?:[A-Z][A-Za-z0-9&.\-]*\s+){1,4}[A-Z][A-Za-z0-9&.\-]*\b")

# A run of Han characters is not a word boundary, so a name is cut out of it: first
# at a connective, then by dropping the leading verb a sentence put in front of it.
_CONNECTIVES = "与和及或兼并且"
_NAME_PREFIXES = (
    "新设", "增设", "设立", "成立", "组建", "撤销", "合并", "划归", "会同", "包括",
    "涉及", "负责", "分管", "隶属", "归属", "归口", "下属", "下设", "派驻",
    "将", "把", "由", "经", "在", "对", "向", "为", "即", "并", "的",
)

# A name with a verb in the middle is a sentence that happens to end in 部 or 中心.
# 到 joined this set on 2026-10-31: an outside audit of 40 unknown surfaces found two of
# them were "企管转到办公室" and "找到主责部门" — a preposition inside the cut, never a name.
_SENTENCE_CHARS = frozenset("的了是在等由经对向并或及把被将为与和就都也还又再很会能要可该此其之即如到")

# Nobody names a department with a paragraph. Ten, not twelve: the only 11-12 character
# surfaces the corpus produced were sentences ("组织机构改革建议考虑部门").
_MAX_NAME_LENGTH = 10

# A suffix alone is never a name, and a name made only of these words is not either.
_EMPTY_NAMES = frozenset({
    "中心", "公司", "集团", "部门", "机关", "总部", "各部", "各部门", "各部门负责人",
    "相关部门", "有关部门", "下属单位", "分子公司", "所属单位",
    # words that merely end with a suffix character
    "内部", "外部", "全部", "部分", "大部分", "局部", "北部", "南部", "东部", "西部",
    "中部", "上部", "下部", "干部", "支部", "干部部", "会议室", "教室", "档案室",
    "学科", "本科", "专科", "理科", "文科", "内科", "外科", "各处", "处处", "好处",
    "坏处", "长处", "短处", "办公室", "代表处", "办事处", "筹备处",
    # generic organisation types, never one organisation
    "项目部", "分公司", "子公司", "中台部门", "后台部门", "中后台部门", "总部部门",
    "业务部门", "职能部门", "下属公司", "成员单位",
    # a company name cut before its own suffix
    "有限公司", "有限责任公司", "股份有限公司",
})

# How a document refers to an organisation is not its name. These are the words a sentence
# puts around one: a role ("主责部门"), a time ("上半年公司"), a verb ("看外部"). An outside
# audit judged 40 surfaces the index could not resolve (2026-10-31): 21 were real names, and
# 19 were exactly these shapes. Filtering them costs a little recall and saves a lot of prompt
# space, so the rules here are deliberately conservative — only what cannot be a name.
_ROLE_PHRASES = frozenset({
    "主责部门", "责任部门", "承办部门", "协办部门", "牵头部门", "配合部门", "主管部门",
    "管理部门", "相关部门", "有关部门", "运营部门", "支持部门", "支撑部门",
    "分部门", "子部门", "部门内部", "部门外部", "部门之间", "各部门", "各分公司",
    "公司本部", "集团本部", "本部", "本单位", "本单位部门", "内设机构", "下设机构",
    "各单位", "下属部门", "上级部门", "同级部门", "基层单位", "成员单位",
})
_LEADING_NOISE = (
    # verb-first: the sentence says what to do with the organisation, not what it is called
    "看", "做", "找", "说", "想", "查", "用", "抓", "推", "审视", "看到", "找到", "查找",
    "明确", "建立", "形成", "梳理", "总结", "描述", "了解", "掌握", "考虑", "推动", "推进",
    "加强", "实现", "确保", "提升", "提高", "优化", "完善", "完成", "开展", "参与", "制定",
    "落实", "打通", "解决", "评估", "识别", "聚焦", "关注", "投资", "独自", "自主",
    "全面", "整体", "深入", "逐步", "持续",
    # filled in from the same corpus after the first pass: each one starts a clause, and
    # the next word is what the clause is about, never the name of an organisation.
    "获评", "下放", "上报", "严格", "最后", "建议", "分别", "集中", "及时", "积极", "主动",
    "有效", "充分", "认真", "尽快", "需要", "应当", "要求", "通过", "按照", "根据", "关于",
    "针对", "围绕", "结合", "依托", "借助", "保证", "维护", "面向", "对应", "涉及", "包括",
    "打造", "对标", "构建", "培育", "塑造", "引导",
)
# An anonymous type: a size or a quality in front of the generic word for an organisation
# ("大型投资集团", "专业化子公司") describes a class of organisations, not one of them.
_GENERIC_TYPED = re.compile(
    r"^(?:大型|中型|小型|新型|传统|[^，。]{2,4}化)[^，。]{0,4}(?:子公司|分公司|公司|集团)$"
)
# A time phrase says *when*; the name after it is what matters.
_TIME_PREFIX = re.compile(
    r"^(?:上半年|下半年|本年度|上年度|全年度|今年|去年|明年|当年|次年|全年|半年|季度|"
    r"第[一二三四五六七八九十\d]+[个次季度年])"
)
# A name made of a role word plus a suffix is still a role: 责任中心, 承办单位.
_ROLE_STEMS = frozenset({
    "主责", "责任", "承办", "协办", "牵头", "配合", "主管", "分管", "相关", "有关",
    "本", "该", "各", "每", "其他", "部分", "上级", "下级", "同级", "外部", "内部",
})
_ROLE_TAILS = ("部门", "单位", "机构", "公司", "中心", "部", "处", "室")


def _looks_like_a_name(name: str) -> bool:
    """Whether a surface cut out of a sentence is shaped like a name, not like a sentence.

    Conservative on purpose: every rule here answers "this cannot be a name", never
    "this is a name". A missed name costs one unmodelled document; a kept sentence costs
    prompt space on every document, and teaches the model to invent entities.
    """
    if name in _EMPTY_NAMES or name in _ROLE_PHRASES:
        return False
    if any(char in _SENTENCE_CHARS for char in name):
        return False
    if name.startswith(_LEADING_NOISE):
        return False
    if _TIME_PREFIX.match(name):
        return False
    if _GENERIC_TYPED.match(name):
        return False
    for tail in _ROLE_TAILS:
        if name.endswith(tail) and name[:-len(tail)] in _ROLE_STEMS:
            return False
    return True


def _trim_prefix(name: str) -> str:
    """Drop the leading verb a sentence wrote in front of the name: 新设X中心 -> X中心."""
    changed = True
    while changed and len(name) > 2:
        changed = False
        for prefix in _NAME_PREFIXES:
            if name.startswith(prefix) and len(name) - len(prefix) >= 3:
                name = name[len(prefix):]
                changed = True
                break
    return name


# --- prose, rule language, and outlines -------------------------------------
#
# A name list is not knowledge, and knowledge is not always a name. Measured over the real
# consulting corpus (34 files): decks and tables of contents sit at 0.06-0.23 prose density,
# while outlines and framework documents sit at 0.48-0.82, and the one directory file that
# should never cost anything sits at 0.16 with five prose units in it.
_PROSE_DENSITY = 0.35
_PROSE_MIN_UNITS = 8
_PROSE_MIN_HAN = 12
_PROSE_MIN_WORDS = 8

# One unit of rule language is a turn of phrase ("不得", "须", "负责", "不低于 30%"); a
# document with a handful is prose that happens to name a rule, a document with eight or
# more teaches one. The training deck in the corpus reads 11 in its first 500 units.
_RULE_MIN_UNITS = 8

_LIST_MARK = re.compile(r"^\s*(?:[-*•]|\d+[.、)]|[（(]\d+[)）]|[一二三四五六七八九十]+[、.])\s*")
_PATHLIKE = re.compile(r"`[^`]*[\\/][^`]*`|[\w\-]+/[\w\-]+/")
_HAN = re.compile(r"[\u4e00-\u9fff]")
_CLAUSE = re.compile(r"[，。；：,;:]")
_WORD = re.compile(r"[A-Za-z][A-Za-z']+")
_RULE_LANGUAGE = re.compile(
    r"(?:负责|牵头|主责|归口|分管|主管|下辖|隶属|下设|并入|统筹"
    r"|不得|禁止|必须|应当|须|超过|不低于|不少于|不高于|不超过|以内|以上|以下"
    r"|截止|前完成|每月|每季|每年|每周|按月|按季|万元|亿元|％|%|≥|≤"
    r"|\b(?:shall|must|may not|is responsible for|reports? to|no later than|at least|at most)\b)",
    re.IGNORECASE,
)
_QUANTITY = re.compile(r"\d+(?:\.\d+)?\s*(?:万元|亿元|%|％|天|个工作日|人|次|项|个|小时|页)")

# A line that names a file is a reference to material, not a statement about the
# organisation: a table of contents repeats every name in the corpus and asserts none
# of them. Measured: it was the only reason the directory file was ever proposed.
_FILE_REFERENCE = re.compile(r"\.(?:md|markdown|docx?|pptx?|pdf|xlsx?|csv|txt)\b", re.IGNORECASE)

# An outline is only ever the outline of a document beside it; the prefix says so.
_OUTLINE_PREFIXES = ("大纲_", "大纲-", "大纲 ")
_PAIR_NOISE = re.compile(r"[\s_\-—·、,，。()（）\[\]【】]+")
_TRAILING_DIGITS = re.compile(r"\d+$")


def _prose_quote(quote: str) -> bool:
    """One unit that states something, as opposed to a label, a path or a heading."""
    text = _LIST_MARK.sub("", quote or "").strip()
    if len(text) < 6 or _PATHLIKE.search(text):
        return False
    if len(_HAN.findall(text)) >= _PROSE_MIN_HAN and _CLAUSE.search(text):
        return True
    return len(_WORD.findall(text)) >= _PROSE_MIN_WORDS and _CLAUSE.search(text) is not None


def prose_units(units: Sequence[_TextUnit]) -> int:
    return sum(1 for unit in units if _prose_quote(unit.quote or ""))


def rule_units(units: Sequence[_TextUnit]) -> int:
    return sum(
        1 for unit in units
        if len(unit.quote or "") >= 6
        and (_RULE_LANGUAGE.search(unit.quote or "") or _QUANTITY.search(unit.quote or ""))
    )


def _pair_key(text: str) -> str:
    """What is left of a document name once the version, date and decoration are gone."""
    return _TRAILING_DIGITS.sub("", _PAIR_NOISE.sub("", text).casefold())


def outline_stem(name: str) -> str | None:
    """The material an outline claims to outline, or None when the name is not an outline."""
    stem = Path(str(name)).stem
    for prefix in _OUTLINE_PREFIXES:
        if stem.startswith(prefix):
            rest = stem[len(prefix):]
            return _pair_key(rest) or None
    return None


def covering_sibling(name: str | None, siblings: Mapping[str, str] | None) -> str | None:
    """The already-read source whose content this outline only restates.

    Only a name that says it is an outline (``大纲_X``) may be covered, and only by a
    source whose name starts with the same material name and which was actually read —
    an unread source cannot stand in for anything, and an outline states nothing its own
    material does not. The point is to spend once on the material rather than twice, the
    second time on its own table of contents.
    """
    if not name or not siblings:
        return None
    key = outline_stem(name)
    if not key:
        return None
    best: tuple[int, str] | None = None
    for other, status in siblings.items():
        if other == name or not str(status).startswith("PARSED"):
            continue
        other_key = _pair_key(Path(str(other)).stem)
        if other_key == key or other_key.startswith(key):
            candidate = (len(other_key), other)
            if best is None or candidate[0] < best[0]:
                best = candidate
    return best[1] if best else None


def _names_in(run: str):
    """Every organisation-shaped name inside one Han run, cut at connectives."""
    for piece in re.split(f"[{_CONNECTIVES}]", run):
        if len(piece) < 3:
            continue
        # A clause that opens with a verb or a time is about an organisation; it is not
        # named after one. Checked on the untrimmed piece, because 对标大型投资集团 trims
        # to 标大型投资集团 and would otherwise look like a name.
        if piece.startswith(_LEADING_NOISE) or _TIME_PREFIX.match(piece):
            continue
        for suffix in _ORG_SUFFIXES:
            if piece.endswith(suffix):
                name = _trim_prefix(piece)
                if len(name) <= len(suffix) or len(name) > _MAX_NAME_LENGTH:
                    break
                if any(char in _SENTENCE_CHARS for char in name):
                    break
                yield name
                break


@dataclass(frozen=True)
class NoveltyVerdict:
    """One stored decision about one source revision."""

    tier: str
    reason: str
    source_id: str | None
    source_revision: str | None
    known_ratio: float
    unknown_surfaces: tuple[str, ...]
    dialect_claims: int
    unit_count: int
    mention_count: int
    prose_unit_count: int = 0
    prose_density: float = 0.0
    rule_unit_count: int = 0
    truncated: bool = False
    unread_locators: int = 0
    covered_by: str | None = None

    @property
    def spends_money(self) -> bool:
        return self.tier in {PROPOSE, FULL}

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": _RECEIPT_VERSION,
            "tier": self.tier,
            "reason": self.reason,
            "spends_money": self.spends_money,
            "source_id": self.source_id,
            "source_revision": self.source_revision,
            "known_ratio": round(self.known_ratio, 6),
            "unit_count": self.unit_count,
            "mention_count": self.mention_count,
            "dialect_claims": self.dialect_claims,
            "unknown_surfaces": list(self.unknown_surfaces),
            "prose_unit_count": self.prose_unit_count,
            "prose_density": round(self.prose_density, 6),
            "rule_unit_count": self.rule_unit_count,
            "truncated": self.truncated,
            "unread_locators": self.unread_locators,
            "covered_by": self.covered_by,
        }


def candidate_surfaces(units: Sequence[_TextUnit], index: EntityIndex) -> tuple[str, ...]:
    """Names in this text that the accepted index cannot resolve.

    Bounded and deterministic: at most :data:`_UNKNOWN_LIMIT` surfaces, longest first,
    each one having appeared at least once in the source's own units.
    """
    known = {normalized for normalized in index.entries}
    seen: dict[str, list] = {}
    for unit in units:
        quote = unit.quote or ""
        if _FILE_REFERENCE.search(quote):
            continue
        for run in _CJK_RUN.findall(quote):
            for name in _names_in(run):
                normalized = normalize_surface(name)
                if normalized in _EMPTY_NAMES or normalized in known:
                    continue
                if not _looks_like_a_name(normalized):
                    continue
                # A phrase built around an accepted name ("现市场营销中心") is a
                # rewording, and the mention layer already reports that name.
                if any(item in normalized for item in known):
                    continue
                row = seen.setdefault(normalized, [name, 0])
                row[1] += 1
        for latin in _LATIN_NAME.findall(quote):
            normalized = normalize_surface(latin)
            if normalized in _EMPTY_NAMES or normalized in known:
                continue
            if not _looks_like_a_name(normalized):
                continue
            if any(item in normalized for item in known):
                continue
            row = seen.setdefault(normalized, [latin, 0])
            row[1] += 1
    ordered = sorted(seen.items(), key=lambda item: (-item[1][1], -len(item[0]), item[0]))
    return tuple(row[0] for _, row in ordered[:_UNKNOWN_LIMIT])


def assess_novelty(
    *,
    index: EntityIndex,
    units: Sequence[_TextUnit],
    source_id: str | None = None,
    source_revision: str | None = None,
    source_name: str | None = None,
    siblings: Mapping[str, str] | None = None,
    revision_changed: bool = True,
    dialect_claims: int = 0,
    truncated: bool = False,
    unread_locators: int = 0,
    force_full: bool = False,
    rejudge: bool = False,
    already_proposed: bool = False,
) -> NoveltyVerdict:
    """Classify one revision; the default is to spend nothing.

    ``rejudge`` is the caller saying "the shelf or the rules moved since I staged this, look
    again": unchanged bytes then get a fresh verdict instead of the old one standing in for
    a decision nobody ever made. ``already_proposed`` says a proposal already exists for
    these exact bytes, so re-judging may re-decide but never re-pays.
    """
    from .wiki_mentions import scan_units

    scan = scan_units(index, units)
    mention_count = int(scan["mention_count"])
    # Coverage is "how much of this document we can already name", never a count:
    # a unit either carries a confident mention or it does not.
    ratio = (int(scan["units_with_confident"]) / len(units)) if units else 0.0
    prose = prose_units(units)
    density = (prose / len(units)) if units else 0.0
    rules = rule_units(units)

    def verdict(tier: str, reason: str, unknown: Sequence[str] = (),
                covered_by: str | None = None) -> NoveltyVerdict:
        return NoveltyVerdict(
            tier=tier,
            reason=reason,
            source_id=source_id,
            source_revision=source_revision,
            known_ratio=ratio,
            unknown_surfaces=tuple(unknown),
            dialect_claims=dialect_claims,
            unit_count=len(units),
            mention_count=mention_count,
            prose_unit_count=prose,
            prose_density=density,
            rule_unit_count=rules,
            truncated=truncated,
            unread_locators=unread_locators,
            covered_by=covered_by,
        )

    if force_full:
        return verdict(FULL, "reviewer_requested_full_reading")
    if not revision_changed and not rejudge:
        return verdict(SKIP, "source_revision_unchanged")
    if not revision_changed and already_proposed:
        # The bytes never changed and a proposal for them already exists: re-deciding is
        # allowed, paying a model a second time for the same text is not.
        return verdict(SKIP, "candidate_already_staged")
    if not units:
        return verdict(SKIP, "no_extractable_text")

    # An outline of material the wiki already read whole adds no knowledge of its own; the
    # source it summarises is the thing that will be modelled, once.
    covered = covering_sibling(source_name, siblings)
    if covered:
        return verdict(LINK_ONLY, f"covered_by_sibling:{covered}", covered_by=covered)

    unknown = candidate_surfaces(units, index)
    if unknown:
        return verdict(PROPOSE, "unresolved_entity_names", unknown)
    if dialect_claims > 0:
        return verdict(PROPOSE, "rule_dialect_present_without_accepted_claim")
    if rules >= _RULE_MIN_UNITS:
        # No new name, but the text states duties, thresholds or deadlines: a model has
        # something to type out, and a name index will never see it.
        return verdict(PROPOSE, "rule_language_present")
    if prose >= _PROSE_MIN_UNITS and density >= _PROSE_DENSITY:
        return verdict(PROPOSE, "prose_without_unresolved_names")
    if truncated:
        # Nothing new was found in what was read, and part of the document was not read.
        # That is not evidence of "nothing new", so the answer is "not yet".
        return verdict(UNREAD, "unread_part_cannot_be_judged")
    return verdict(LINK_ONLY, "every_name_resolved_and_no_rule_dialect")


def receipt_root(workspace: Path | str) -> Path:
    return Path(workspace).expanduser().resolve() / ".catalyst" / "novelty"


def write_receipt(workspace: Path | str, verdict: NoveltyVerdict) -> Path:
    """Store the verdict next to the scope, keyed by source revision; never in the store."""
    root = receipt_root(workspace)
    root.mkdir(parents=True, exist_ok=True)
    payload = verdict.to_dict()
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    identity = f"{verdict.source_id}\0{verdict.source_revision}"
    name = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    path = root / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_receipts(workspace: Path | str) -> list[dict[str, Any]]:
    root = receipt_root(workspace)
    if not root.is_dir():
        return []
    rows = []
    for path in sorted(root.glob("*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return rows


def summarize(verdicts: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """How much work a batch did not do, counted by tier."""
    counts = {tier: 0 for tier in TIERS}
    for row in verdicts:
        tier = row.get("tier")
        if tier in counts:
            counts[tier] += 1
    return counts
