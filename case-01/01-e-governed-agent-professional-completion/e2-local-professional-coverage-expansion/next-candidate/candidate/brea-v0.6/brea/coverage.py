"""Generic numbered-subitem and numeric-rule parsing helpers.

These helpers know only the textual shape of a rule unit. Professional terms and
source locators are supplied by the local descriptor data, not by this module.
"""
from __future__ import annotations

import re

from .corpus import Corpus


_CLAUSE_START_RE = re.compile(r"^(\d+\.\d+\.\d+)(.*)$")
_SECTION_RE = re.compile(r"^\d+(\.\d+)?[^\d.]")
_SUBITEM_RE = re.compile(r"^(\d{1,2})[、.．) ]?(?=\D)")
_ENUM_INTRODUCER = ("应符合下列规定", "应符合下列要求", "应满足下列")
_VALUE_RE = re.compile(r"不应大于\s*(\d+(?:\.\d+)?)\s*m\s*(?:²|2)?")
_PAGE_RE = re.compile(r"^\[page (\d+)\]$")
_FOOTER_RE = re.compile(r"^[·.\s]*\d+[·.\s]*$")


def extract_full_clause(corpus: Corpus, clause_id: str) -> dict | None:
    start = None
    for index, line in enumerate(corpus.lines):
        match = _CLAUSE_START_RE.match(line)
        if match and match.group(1) == clause_id:
            start = index
            break
    if start is None:
        return None
    lines: list[tuple[int, str]] = []
    for index in range(start, len(corpus.lines)):
        stripped = corpus.lines[index].strip()
        if index > start:
            if _PAGE_RE.match(stripped) or _FOOTER_RE.match(stripped):
                continue
            clause_match = _CLAUSE_START_RE.match(stripped)
            if clause_match and clause_match.group(1) != clause_id:
                break
            if _SECTION_RE.match(stripped) and not _SUBITEM_RE.match(stripped):
                break
        lines.append((index, corpus.lines[index]))
    text = "\n".join(line.rstrip("\r\n") for _index, line in lines)
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
    intro_pos = -1
    intro_length = 0
    for introducer in _ENUM_INTRODUCER:
        position = clause_text.find(introducer)
        if position != -1:
            intro_pos = position
            intro_length = len(introducer)
            break
    if intro_pos == -1:
        return []
    items: list[dict] = []
    current: list[str] = []
    current_index: str | None = None
    for raw_line in clause_text[intro_pos + intro_length:].split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = _SUBITEM_RE.match(line)
        if match:
            if current_index is not None and current:
                items.append({"index": current_index, "text": "\n".join(current).strip()})
            current_index = match.group(1)
            current = [line[match.end():].strip()]
        else:
            current.append(line)
    if current_index is not None and current:
        items.append({"index": current_index, "text": "\n".join(current).strip()})
    return items


def extract_numeric_rules(item_text: str) -> list[dict]:
    rules: list[dict] = []
    for segment in re.split(r"[；;。]", item_text):
        match = _VALUE_RE.search(segment)
        if match:
            rules.append({"condition": segment[:match.start()].strip(), "value": float(match.group(1))})
    return rules
