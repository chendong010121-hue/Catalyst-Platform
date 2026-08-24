"""PRIVATE — E2 conditional-rule coverage mechanism (FN-09/FN-04/FN-05 extension).

Deterministic parser for "numbered-subitem conditional rule" clauses (e.g. GB 55037-2022
第4.3.16条: "1对于高层建筑，不应大于1500m² … 4当防火分区全部设置自动灭火系统时…").

Reusable, data-driven: the parser is generic (any clause with numbered sub-items and
`不应大于N m²` value forms); the professional rule data for the selected E2 family
(fire-compartment max area) is declared separately as DOMAIN rule data. NO benchmark
question strings, NO per-question branches, NO per-question values (E2 anti-hardcode).

This module is PRIVATE HOW inside FN-09/FN-04/FN-05; it does not create a Governed Seam.
"""
from __future__ import annotations

import re

from .corpus import Corpus, norm

_CLAUSE_START_RE = re.compile(r"^(\d+\.\d+\.\d+)(.*)$")
_SECTION_RE = re.compile(r"^\d+(\.\d+)?[^\d.]")
_SUBITEM_RE = re.compile(r"^(\d{1,2})[、.．) ]?(?=\D)")
_ENUM_INTRODUCER = ("应符合下列规定", "应符合下列要求", "应满足下列")
_VALUE_RE = re.compile(r"不应大于\s*(\d+(?:\.\d+)?)\s*m\s*(?:²|2)?")
_PAGE_RE = re.compile(r"^\[page (\d+)\]$")
_FOOTER_RE = re.compile(r"^[·.\s]*\d+[·.\s]*$")


def extract_full_clause(corpus: Corpus, clause_id: str) -> dict | None:
    """Extract a clause INCLUDING numbered sub-items (generic).

    v0.2 clause_index stops at the first `N…` sub-item line; this extractor keeps
    sub-items inside the clause while still stopping at the next clause id / section
    heading. Sub-item continuation is enabled only after an enumeration introducer
    (e.g. "应符合下列规定："), which distinguishes "1对于高层建筑…" from a section
    heading like "4.4其他工程".
    """
    start = None
    for index, line in enumerate(corpus.lines):
        match = _CLAUSE_START_RE.match(line)
        if match and match.group(1) == clause_id:
            start = index
            break
    if start is None:
        return None

    buf: list[str] = []
    lines: list[tuple[int, str]] = []
    for index in range(start, len(corpus.lines)):
        line = corpus.lines[index]
        stripped = line.strip()
        if index > start:
            if _PAGE_RE.match(stripped) or _FOOTER_RE.match(stripped):
                continue
            clause_match = _CLAUSE_START_RE.match(stripped)
            if clause_match and clause_match.group(1) != clause_id:
                break
            # stop at a section heading (e.g. "4.4其他工程") but keep numbered
            # sub-items (e.g. "1对于高层建筑…", "27对于…") inside the clause
            if _SECTION_RE.match(stripped) and not _SUBITEM_RE.match(stripped):
                break
        buf.append(line)
        lines.append((index, line))

    text = "\n".join(line.rstrip("\r\n") for _idx, line in lines)
    return {
        "clause_id": clause_id,
        "text": text,
        "start": lines[0][0],
        "end": lines[-1][0],
        "page": _page_of(corpus, lines[0][0]),
    }


def _page_of(corpus: Corpus, line_index: int) -> int:
    for index in range(line_index, -1, -1):
        match = _PAGE_RE.match(corpus.lines[index].strip())
        if match:
            return int(match.group(1))
    return 0


def parse_numbered_items(clause_text: str) -> list[dict]:
    """Generic numbered-subitem splitter.

    Returns items like {"index": "1", "text": "对于高层建筑，不应大于1500m²"}.
    Sub-item text is the clause text AFTER the introducer, split on leading numbers.
    """
    intro_pos = -1
    for introducer in _ENUM_INTRODUCER:
        pos = clause_text.find(introducer)
        if pos != -1:
            intro_pos = pos
            break
    if intro_pos == -1:
        return []
    body = clause_text[intro_pos + 4:]
    items: list[dict] = []
    current: list[str] = []
    current_index: str | None = None
    seen_first = False
    for raw_line in body.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = _SUBITEM_RE.match(line)
        if match:
            if seen_first and current_index is not None and current:
                items.append({"index": current_index, "text": "\n".join(current).strip()})
            seen_first = True
            current_index = match.group(1)
            current = [line[match.end():].strip()]
        else:
            current.append(line)
    if current_index is not None and current:
        items.append({"index": current_index, "text": "\n".join(current).strip()})
    return items


def extract_numeric_rules(item_text: str) -> list[dict]:
    """Extract (condition, value) pairs from sub-item text.

    Splits on Chinese sentence separators and matches `不应大于N m²` forms.
    Returns [{"condition": "...", "value": 1500.0}].
    """
    rules: list[dict] = []
    for segment in re.split(r"[；;。]", item_text):
        match = _VALUE_RE.search(segment)
        if not match:
            continue
        condition = segment[:match.start()].strip()
        rules.append({"condition": condition, "value": float(match.group(1))})
    return rules


# ---------------------------------------------------------------------------
# E2 selected family rule data (DOMAIN, from GB 55037-2022 第4.3.16条)
# ---------------------------------------------------------------------------

FIRE_COMPARTMENT = {
    "clause_id": "4.3.16",
    "family": "fire_compartment_max_area",
    "control_item": "防火分区最大允许建筑面积",
    "required_facts": ("building_form", "fire_resistance_rating", "auto_extinguishing_system"),
    "exclusions": ("特殊要求的建筑", "木结构建筑", "附建于民用建筑中的汽车库"),
    "condition_facts": {
        # fact key -> (condition keywords, in order of specificity)
        "building_form": (("高层建筑", "高层"), ("单、多层建筑", "单多层", "多层"), ("地下",)),
        "fire_resistance_rating": (("一、二级耐火等级", "一级", "二级"),
                                   ("三级耐火等级", "三级"), ("四级耐火等级", "四级")),
    },
    "modifier_rule": {
        "condition": "全部设置自动灭火系统",
        "action": "double",  # "上述面积可以增加1.0倍" → ×2
    },
}


def match_condition_value(rules: list[dict], facts: dict) -> dict | None:
    """Match project facts to extracted (condition, value) rules.

    A rule wins when its condition text contains a keyword for EVERY matched fact
    dimension the Candidate has. Returns {"rule": ..., "matched": [...]} or None.
    """
    fact_keys = ("building_form", "fire_resistance_rating")
    best = None
    best_score = -1
    for rule in rules:
        matched: list[str] = []
        score = 0
        for key in fact_keys:
            value = str(facts.get(key) or "")
            if not value:
                continue
            for keywords in FIRE_COMPARTMENT["condition_facts"][key]:
                if any(kw in rule["condition"] for kw in keywords) and any(kw in value for kw in keywords):
                    matched.append(key)
                    score += 1
                    break
        # building_form must match for a public building compartment rule
        if "building_form" not in matched:
            continue
        if score > best_score:
            best_score = score
            best = {"rule": rule, "matched": matched}
    return best


def modifier_applies(facts: dict, item_text: str) -> bool:
    value = str(facts.get("auto_extinguishing_system") or "")
    return ("全部" in value) and (FIRE_COMPARTMENT["modifier_rule"]["condition"] in item_text)


def is_excluded(building_category: str | None) -> bool:
    return any(token in str(building_category or "") for token in FIRE_COMPARTMENT["exclusions"])
