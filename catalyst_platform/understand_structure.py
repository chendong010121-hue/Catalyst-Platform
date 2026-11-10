"""Reading an organisation out of the drawing, and refusing to read one out of the prose.

An org-chart page states its structure twice: in the words of its boxes, and in the
connections it draws between them. The words alone cannot say which box is above which —
"财务管理部" and "后台部门" sit next to each other, and only the line between them, or its
absence, decides whether one belongs to the other. This module reads the connections the
reading surface recorded (``unit_kind == "structure"``) and turns them into claims that
name the line they rest on.

Three things it deliberately does not do:

* It never guesses an edge from two labels being near each other. A pair the page did not
  connect is a question for the Owner, not a relation.
* It never lets a category band be an organisation's superior. "中台部门" is a column
  heading and "经理层" is a management layer: a unit belongs to the nearest unit outside
  those layers, and the steps it walked through are recorded on the claim.
* It never lets a page that does not say which state it shows speak for the current state.
  A page headed "整体组织架构示意" states a picture, not a fact about today.

The two vocabularies below are declared, not inferred from geometry: an Owner may edit
them, and changing either changes what the reading asserts, so each carries a version.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

BAND_VERSION = "bands.v1"
# Column headings that group units by function. Not organisations.
BAND_LABELS = frozenset({
    "中台部门", "后台部门", "前台部门(分公司)", "对外投资单位",
    "水利集团分公司", "水利集团子公司", "水利集团专业化子公司",
    "水利集团区域化的分公司架构",
})
# Bodies and management layers that are units in their own right, but are not an
# organisation a department belongs to by management line.
GOVERNANCE_LABELS = frozenset({"董事会", "监事会", "经理层", "党委会", "股东会"})

# A label that names a post rather than a unit. A line drawn between two posts is a
# reporting line; "隶属" would flatten it into membership of the unit, which the drawing
# does not say.
POSITION_HINTS = ("经理", "工程师", "员工", "主管", "专员", "岗", "主任", "部长")

_CURRENT_WORDS = ("现有", "现状", "当前")
_TARGET_WORDS = ("优化后", "调整后", "未来", "建议", "拟")


def _flat(text: str) -> str:
    text = re.sub(r"[\s\u3000]+", "", str(text or ""))
    return text.replace("（", "(").replace("）", ")")


def _canon(text: str) -> str:
    """The thing's own name, without the alias its bracket also carries."""
    return split_alias(text)[0]


def split_alias(text: str) -> tuple[str, str | None]:
    """A label that carries a second name in brackets: "技术研发中心（质量技术部）".

    The product's candidate names the thing; the bracket is the alias the source also
    uses for it. One entity with two names, never two entities.
    """
    flat = _flat(text)
    match = re.fullmatch(r"([^()]+)\(([^()]+)\)", flat)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return flat, None


@dataclass(frozen=True)
class DrawnEdge:
    """One connection the page draws, with the address a reader can go and look at."""
    slide: str
    locator: str
    upper: str
    lower: str
    upper_locator: str | None
    lower_locator: str | None
    basis: str

    @property
    def usable(self) -> bool:
        return self.basis == "page_vertical" and bool(self.upper) and bool(self.lower)


@dataclass(frozen=True)
class Claim:
    """An edge the drawing supports, after the stepping-through of bands is recorded."""
    child: str
    parent: str
    slide: str
    locators: tuple[str, ...]
    path: tuple[str, ...]
    state: str | None
    # The two boxes themselves, so a row read from this claim can cite the boxes as
    # well as the lines: a reader checking the claim starts at the boxes.
    endpoints: tuple[str, ...] = ()

    @property
    def direct(self) -> bool:
        return len(self.path) == 2 and not is_band(self.path[1]) and not is_governance(self.path[1])


@dataclass(frozen=True)
class Finding:
    """What the structure channel can say about one candidate relation."""
    item_id: str
    subject: str
    object: str
    verdict: str
    question: str | None
    locators: tuple[str, ...]
    why: str


def is_structure_cell(unit: Any) -> bool:
    """A cell the reader addressed as part of the drawing, not as a piece of prose."""
    if getattr(unit, "unit_kind", "") == "structure":
        return True
    locator = getattr(unit, "locator", "")
    return "#cxn:" in locator or locator.endswith("#state")


def structure_units(units: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(unit for unit in units if is_structure_cell(unit))


def drawn_edges(units: Iterable[Any]) -> tuple[DrawnEdge, ...]:
    edges = []
    for unit in structure_units(units):
        if "#cxn:" not in getattr(unit, "locator", ""):
            continue
        try:
            body = json.loads(unit.quote)
        except (TypeError, ValueError):
            continue
        ends = body.get("ends") or []
        if len(ends) != 2:
            ends = [{}, {}]
        parent = body.get("parent")
        upper = ends[parent] if parent in (0, 1) else {}
        lower = ends[1 - parent] if parent in (0, 1) else {}
        edges.append(DrawnEdge(
            slide=unit.locator.split("#")[0], locator=unit.locator,
            upper=str(upper.get("text") or ""), lower=str(lower.get("text") or ""),
            upper_locator=upper.get("locator"), lower_locator=lower.get("locator"),
            basis=str(body.get("basis") or "no_endpoint")))
    return tuple(edges)


def slide_state(title: str | None) -> str | None:
    """Which state a page declares, in its own title words, or nothing at all."""
    text = _flat(title or "")
    if not text:
        return None
    if any(word in text for word in _CURRENT_WORDS):
        return "current"
    if any(word in text for word in _TARGET_WORDS):
        return "target"
    return None


def page_states(units: Iterable[Any]) -> dict[str, str | None]:
    """Which state each page declares, read from the cell the reader wrote for it.

    The reading surface states it once per page (``#state``), so every later stage reads
    the same sentence instead of re-deciding from a title it may not have seen.
    """
    states: dict[str, str | None] = {}
    for unit in units:
        if "#state" not in getattr(unit, "locator", ""):
            continue
        try:
            body = json.loads(getattr(unit, "quote", ""))
        except (TypeError, ValueError):
            continue
        if isinstance(body, dict) and "declares" in body:
            states[unit.locator.split("#")[0]] = body.get("declares") or None
    return states


def is_band(label: str) -> bool:
    """A column heading, including the short form a second page may use for it."""
    flat = _flat(label)
    return flat in BAND_LABELS or any(band.split("(")[0] == flat for band in BAND_LABELS)


def is_governance(label: str) -> bool:
    return _flat(label) in GOVERNANCE_LABELS


def is_position(label: str) -> bool:
    flat = _flat(label)
    return any(flat.endswith(hint) or hint in flat for hint in POSITION_HINTS) and not is_band(flat)


def _stepped(label: str) -> bool:
    return is_band(label) or is_governance(label)


def claims(edges: Sequence[DrawnEdge], states: Mapping[str, str | None] | None = None) -> tuple[Claim, ...]:
    """Every hierarchy edge the drawing supports, with the steps it stepped through.

    A department drawn into the 中台部门 column belongs to whatever that column belongs
    to; the column is a category and the management layer is a layer, so the claim lands
    on the nearest unit outside both and records the whole path a reader can check.
    """
    table: dict[tuple[str, str], set[str]] = {}
    via: dict[tuple[str, str, str], DrawnEdge] = {}
    for edge in edges:
        if not edge.usable:
            continue
        lower, upper = _flat(edge.lower), _flat(edge.upper)
        table.setdefault((lower, edge.slide), set()).add(upper)
        via.setdefault((lower, upper, edge.slide), edge)
    out: list[Claim] = []
    seen: set[tuple[str, str, str]] = set()

    def walk(anchor: str, node: str, slide: str, path: tuple[str, ...],
             locators: tuple[str, ...], endpoints: tuple[str, ...] = ()) -> None:
        for parent in sorted(table.get((node, slide), ())):
            if parent in path:
                continue
            edge = via.get((node, parent, slide))
            step = locators + ((edge.locator,) if edge else ())
            ends = tuple(item for item in ((edge.lower_locator, edge.upper_locator) if edge else ()) if item)
            if _stepped(parent):
                if (parent, slide) in table:
                    walk(anchor, parent, slide, path + (parent,), step, ends or endpoints)
                # A band or a management layer with nothing above it is a step with no
                # unit at the end: the claim stops here and the Finding asks instead.
                continue
            key = (_canon(anchor), _canon(parent), slide)
            if key in seen:
                continue
            seen.add(key)
            out.append(Claim(child=_canon(anchor), parent=_canon(parent), slide=slide,
                             locators=tuple(item for item in step if item),
                             path=path + (parent,), state=(states or {}).get(slide),
                             endpoints=ends or endpoints))

    for child, slide in sorted(table):
        walk(child, child, slide, (child,), ())
    return tuple(out)


def assertable_claims(units: Iterable[Any]) -> tuple[Claim, ...]:
    """The claims a candidate may state: drawn, on a page that declares its state, between
    two units — not a band, not a governance body, not two posts on a reporting line."""
    units = tuple(units)
    out = []
    for claim in claims(drawn_edges(units), page_states(units)):
        if claim.state is None:
            continue
        if any(_stepped(name) for name in (claim.child, claim.parent)):
            continue
        if is_position(claim.child) or is_position(claim.parent):
            continue
        out.append(claim)
    return tuple(out)


def _page_locators(item: Mapping[str, Any], locators: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(locators[ref] for ref in item.get("evidence_refs") or () if ref in locators)


def relation_findings(
    items: Sequence[Mapping[str, Any]],
    units: Iterable[Any],
    *,
    names: Mapping[str, str],
    locators: Mapping[str, str],
) -> tuple[Finding, ...]:
    """Judge every candidate relation against the drawing, and say what is missing."""
    units = tuple(units)
    edges = drawn_edges(units)
    states = page_states(units)
    stated = claims(edges, states)
    index = {(_canon(claim.child), _canon(claim.parent)): claim for claim in stated}
    out: list[Finding] = []
    for item in items:
        if item.get("kind") != "relation":
            continue
        subject = _canon(names.get(item.get("subject") or "", item.get("subject") or ""))
        obj = _canon(names.get(item.get("object") or "", item.get("object") or ""))
        if not subject or not obj:
            continue
        seen = _page_locators(item, locators)
        claim = index.get((subject, obj))
        if is_band(obj):
            out.append(Finding(
                item_id=str(item.get("item_id") or ""), subject=subject, object=obj,
                verdict="band_parent", locators=seen,
                why=f"{obj} 是分类列标题（{BAND_VERSION}），不是可以被隶属的单位",
                question=f"{subject} 属于「{obj}」这一分类；它的直接上级单位是哪一个？"))
        elif is_governance(subject) or is_governance(obj):
            out.append(Finding(
                item_id=str(item.get("item_id") or ""), subject=subject, object=obj,
                verdict="governance_edge", locators=seen + (claim.locators if claim else ()),
                why=f"{subject}/{obj} 是治理层，原文画了连线，但「隶属」不是治理关系的说法",
                question=f"{subject} 与 {obj} 之间是治理关系（谁对谁负责决策），不是管理隶属：请给出记录口径？"))
        elif claim is None:
            out.append(Finding(
                item_id=str(item.get("item_id") or ""), subject=subject, object=obj,
                verdict="undrawn", locators=seen,
                why="原文任何一页都没有把这两个盒子连起来",
                question=f"{subject} 与 {obj} 之间的隶属关系在原文里没有画出连线，请确认：{subject} 的直接上级是不是 {obj}？"))
        elif is_position(obj) or is_position(subject):
            out.append(Finding(
                item_id=str(item.get("item_id") or ""), subject=subject, object=obj,
                verdict="reports_to", locators=seen + claim.locators,
                why=f"{claim.slide}：{' → '.join(claim.path)} 是两个岗位之间的汇报线",
                question=f"{subject} 画在 {obj} 之下，这是汇报线；它该记成「隶属 {obj}」还是「隶属于所在单位」？"))
        elif claim.state is None:
            out.append(Finding(
                item_id=str(item.get("item_id") or ""), subject=subject, object=obj,
                verdict="unstated_state", locators=seen + claim.locators,
                why=f"{claim.slide} 没有说自己画的是现状还是调整后",
                question=f"{subject} 隶属 {obj} 画在 {claim.slide}，但这一页没说属于哪一态，请确认按现状还是按调整后记录？"))
        else:
            out.append(Finding(
                item_id=str(item.get("item_id") or ""), subject=subject, object=obj,
                verdict="drawn" if claim.direct else "drawn_through",
                locators=seen + claim.locators,
                why=f"{claim.slide}：{' → '.join(claim.path)}",
                question=None if claim.direct else
                f"{subject} 隶属 {obj} 是通过「{'→'.join(claim.path[1:-1])}」折到 {obj} 的，"
                f"请确认是否按这一压平口径记录？"))
    return tuple(out)


def summary(findings: Sequence[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.verdict] = counts.get(finding.verdict, 0) + 1
    return counts
