"""Reading a selected local source, bounded and without executing it: what may be opened,
what is refused, how many units a file becomes, and how evidence is re-read when a caller
asks for a wider span.
"""

from __future__ import annotations

import io
import json
import os
import posixpath
import re
import tomllib
import xml.etree.ElementTree as ET
import zipfile

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .understand_structure import slide_state
from .understand_models import (
    EvidenceExpansionRequest,
    EvidenceExpansionResult,
    EvidenceRef,
    SemanticCapacityError,
    SourceRecord,
    _TextUnit,
    _new_evidence,
    _sha,
)


# A real deck in this workspace is 34.5 MiB on disk and only 1.17 MiB of text:
# refusing it for its byte size refused the text, not a risk.
_MAX_FILE_BYTES = 128 * 1024 * 1024

# One parsed part (a slide, a worksheet, one document.xml). A slide of a real
# training deck is 2.07 MiB of text, so a 2 MiB bound cut a legitimate slide.
_MAX_TEXT_BYTES = 8 * 1024 * 1024

# One real deck carries 1,304 members: images, notes, media, an embedded workbook.
_MAX_ARCHIVE_MEMBERS = 4096

# Budgeted over the parts actually parsed, never over images and embedded objects.
_MAX_ARCHIVE_UNCOMPRESSED = 256 * 1024 * 1024

# How many units may reach a caller that will act on them (a model request, an evidence
# expansion). Unchanged by the reading bound below: a caller's budget is its own.
_MAX_UNITS = 500

# `.catalyst-proposals` is where Understand writes its own derived evidence package back
# into the materials root. Reading it as a source would make the second card over the same
# materials read the first card's output as if the Owner had supplied it, so it is not a
# source: the storage step must never become evidence for itself.
_EXCLUDED = {".git", ".catalyst", ".catalyst-proposals", ".venv", "venv", "node_modules",
             "__pycache__", ".pytest_cache"}

# How much of one document may become evidence. Measured over the real corpus: the widest
# deck is 2,370 locators and the whole 34-file directory is 12,132, so 500 cut the seven
# largest documents in half. Reading more costs parsing time the reader already paid
# (units are collected and then sliced), and every unit stays inside the document.
_MAX_EXTRACT_UNITS = 5000

# The harness gates (session routing and the semantic acceptance manifest) admit exactly
# these types: the ones Understand can split into addressed units. They read one list
# because three copies drifting apart is how a document is accepted by one gate and
# refused by the next, with nothing failing in between.
SOURCE_SUFFIXES = frozenset({".txt", ".md", ".pptx", ".docx", ".pdf", ".xlsx"})

# Understand itself reads more than the harness admits: structured text files are sources
# for an explicit file list, not for the demo gates.
_ALLOWED = SOURCE_SUFFIXES | {".markdown", ".rst", ".json", ".py", ".toml", ".yaml", ".yml", ".xml"}

_SECRET_NAMES = {".env", "credentials", "secrets.json"}

def _safe_file(path: Path | str, root: Path) -> tuple[Path, str]:
    raw_path = Path(path).expanduser()
    root = root.resolve()
    raw_absolute = Path(os.path.abspath(raw_path))
    try:
        raw_relative = raw_absolute.relative_to(root)
    except ValueError as exc:
        raise PermissionError("source is outside the explicit trusted root") from exc
    current = root
    for part in raw_relative.parts:
        current = current / part
        if current.is_symlink():
            raise PermissionError("symbolic-link sources are not accepted")
    if raw_path.is_symlink():
        raise PermissionError("symbolic-link sources are not accepted")
    selected = raw_path.resolve()
    if not selected.is_relative_to(root):
        raise PermissionError("source is outside the explicit trusted root")
    relative = selected.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise PermissionError("symbolic-link sources are not accepted")
    if not selected.is_file():
        raise ValueError("source is not a regular file")
    if selected.name.casefold() in _SECRET_NAMES or selected.suffix.casefold() in {".pem", ".key", ".p12", ".pfx"}:
        raise PermissionError("credential-like source is excluded")
    if selected.suffix.casefold() not in _ALLOWED:
        raise ValueError("source type is unsupported")
    return selected, relative.as_posix()

def _walk_sources(paths: Sequence[Path | str], root: Path) -> tuple[tuple[Path, str], ...]:
    root = root.resolve()
    found: dict[str, tuple[Path, str]] = {}
    for value in paths:
        raw = Path(value).expanduser()
        if raw.is_symlink():
            raise PermissionError("symbolic-link sources are not accepted")
        selected = raw.resolve()
        if not selected.is_relative_to(root):
            raise PermissionError("source is outside the explicit trusted root")
        if selected.is_file():
            checked, relative = _safe_file(selected, root)
            found[relative] = (checked, relative)
        elif selected.is_dir():
            for item in sorted(selected.rglob("*")):
                if any(part.casefold() in _EXCLUDED for part in item.relative_to(selected).parts):
                    continue
                if item.is_symlink() or not item.is_file() or item.name.casefold() in _SECRET_NAMES:
                    continue
                if item.suffix.casefold() in {".pem", ".key", ".p12", ".pfx"} or item.suffix.casefold() not in _ALLOWED:
                    continue
                checked, relative = _safe_file(item, root)
                found[relative] = (checked, relative)
        else:
            raise ValueError("source reference does not exist")
    return tuple(found[key] for key in sorted(found))

def _media_type(path: Path) -> str:
    return {
        ".md": "markdown", ".markdown": "markdown", ".txt": "plain_text", ".rst": "restructured_text",
        ".json": "json", ".py": "python", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
        ".xml": "xml", ".pptx": "presentation", ".docx": "word_document", ".pdf": "pdf_document", ".xlsx": "spreadsheet",
    }[path.suffix.casefold()]

def _archive_read(raw: bytes, selected_member: str) -> bytes:
    if len(raw) > _MAX_FILE_BYTES:
        raise ValueError("document exceeds the bounded source size")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as package:
            members = [info for info in package.infolist() if not info.is_dir()]
            if len(members) > _MAX_ARCHIVE_MEMBERS:
                raise ValueError("document archive exceeds the bounded member count")
            member = package.getinfo(selected_member)
            if member.file_size > _MAX_TEXT_BYTES:
                raise ValueError("document content part exceeds the bounded inspection limit")
            return package.read(member)
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("document package is damaged or missing its content part") from exc

def _xml_text(element: ET.Element) -> str:
    return " ".join(part.strip() for part in element.itertext() if part and part.strip())

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_NUMBERED_HEADING = re.compile(r"^(?:[一二三四五六七八九十百]+、|第[一二三四五六七八九十百]+[章节部分])")
_SUBHEADING = re.compile(r"^（[一二三四五六七八九十百]+）")

def _lines(element: ET.Element) -> list[str]:
    """One line of text per paragraph, runs inside a line joined with nothing between them.

    A run breaks where the formatting changes, not where a word ends: joining runs with a
    separator turns one name into two pieces ("市场" + "副经理").
    """
    lines = []
    for paragraph in element.iter(_A + "p"):
        lines.append("".join(node.text or "" for node in paragraph.iter(_A + "t")))
    return lines

def _shape_role(shape: ET.Element) -> tuple[str, int | None]:
    """title / heading / body, from the placeholder the slide declares."""
    for placeholder in shape.iter(_P + "ph"):
        kind = (placeholder.get("type") or "body").casefold()
        if kind in {"title", "ctrtitle"}:
            return "title", 1
        if kind == "subtitle":
            return "heading", 2
        return "body", None
    return "body", None

def _shape_id(shape: ET.Element) -> str:
    node = shape.find(f".//{_P}cNvPr")
    return node.get("id", "") if node is not None else ""

def _shape_box(shape: ET.Element) -> tuple[int, int, int, int] | None:
    """The box on the page, in hundredths of a millimetre, or None when it has no place.

    A page's vertical order is what tells a superior from a subordinate: an author draws
    the connector either way round, and only the page agrees with every author.
    """
    node = shape.find(f".//{_A}xfrm")
    if node is None:
        return None
    off, ext = node.find(_A + "off"), node.find(_A + "ext")
    if off is None or ext is None:
        return None
    try:
        return (int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy")))
    except (TypeError, ValueError):
        return None

def _connector_cell(connector: ET.Element, shapes: Mapping[str, dict]) -> dict:
    """One drawn connection, as the cell a relation can point at.

    ``parent`` is which end sits higher on the page (``0`` or ``1``); ``None`` when the
    two ends share a row and the drawing therefore says nothing about which is above
    which. An end with no words is kept and named ``unnamed``, and a line that declares
    no ends at all is kept and named ``no_endpoint``: a connection the reading cannot
    resolve is a question, never a silently missing edge.
    """
    start = connector.find(f".//{_A}stCxn")
    end = connector.find(f".//{_A}endCxn")
    name = connector.find(f".//{_P}cNvPr")
    named = (name.get("name") if name is not None else "") or ""
    if start is None or end is None:
        return {"quote": json.dumps({"connector": named, "ends": [], "parent": None,
                                     "basis": "no_endpoint"}, ensure_ascii=False, separators=(",", ":")),
                "basis": "no_endpoint", "parent": None}
    ends = [shapes.get(start.get("id", ""), {}), shapes.get(end.get("id", ""), {})]
    boxes = [item.get("box") for item in ends]
    parent = None
    basis = "no_box"
    if all(boxes):
        centres = [box[1] + box[3] / 2 for box in boxes]
        shortest = min(boxes[0][3], boxes[1][3])
        if abs(centres[0] - centres[1]) >= shortest / 2:
            parent = 0 if centres[0] < centres[1] else 1
            basis = "page_vertical"
        else:
            basis = "same_row"
    if any(not item.get("text") for item in ends):
        basis = "unnamed_end"
        parent = None
    quote = json.dumps({
        "connector": named,
        "ends": [{"locator": item.get("locator"), "text": item.get("text", "")} for item in ends],
        "parent": parent,
        "basis": basis,
    }, ensure_ascii=False, separators=(",", ":"))
    return {"quote": quote, "basis": basis, "parent": parent}

def _docx_outline_levels(raw: bytes) -> dict[str, int]:
    """styleId -> heading level, as the document's own styles declare it (1-based)."""
    try:
        styles = ET.fromstring(_archive_read(raw, "word/styles.xml"))
    except (ValueError, ET.ParseError):
        return {}
    levels: dict[str, int] = {}
    for style in styles.iter(_W + "style"):
        style_id = style.get(_W + "styleId")
        node = style.find(f"{_W}pPr/{_W}outlineLvl")
        if not style_id or node is None:
            continue
        value = node.get(_W + "val") or ""
        if value.isdigit() and 0 <= int(value) <= 8:
            levels[style_id] = int(value) + 1
    return levels

def _docx_paragraph_text(paragraph: ET.Element) -> tuple[str, bool, int]:
    """The paragraph as a reader sees it, plus whether it carries a field code.

    A Word run breaks where the formatting changes, not where a word ends, so a separator
    between two runs turns one name into two pieces ("市场" + "副经理"). Runs are therefore
    joined with nothing between them; a tab or a line break inside the paragraph is a real
    space and becomes one. ``instrText`` is the field instruction behind a table of
    contents or a page reference — the reader never sees those words, and quoting them as
    prose would put the document's machinery into the candidate.
    """
    parts: list[str] = []
    runs = 0
    apparatus = False
    for node in paragraph.iter():
        tag = node.tag
        if tag == _W + "t":
            parts.append(node.text or "")
            runs += 1
        elif tag in {_W + "tab", _W + "br", _W + "cr"}:
            parts.append(" ")
        elif tag == _W + "instrText":
            apparatus = True
        elif tag == _W + "delText":
            continue  # deleted text is not reader text and is not machinery either
    return "".join(parts), apparatus, runs

def _docx_role(paragraph: ET.Element, text: str, styles: Mapping[str, int]) -> tuple[str | None, int | None, str | None, str | None]:
    """The cell's role as the file declares it, and only failing that, by its shape.

    ``outlineLvl`` is the document saying "this is a heading at level N"; the L2 fallback
    reads the numbering a Chinese document uses for the same purpose and says so, because
    an inferred role that does not announce itself is a guess dressed as a fact.
    """
    properties = paragraph.find(_W + "pPr")
    level = None
    style_id = None
    if properties is not None:
        node = properties.find(_W + "outlineLvl")
        value = (node.get(_W + "val") if node is not None else None) or ""
        style = properties.find(_W + "pStyle")
        style_id = style.get(_W + "val") if style is not None else None
        if value.isdigit() and 0 <= int(value) <= 8:
            level = int(value) + 1
        elif style_id:
            level = styles.get(style_id)
    if level and text.strip():
        return ("title" if (style_id or "").casefold() == "title" else "heading"), level, "format", None
    if _NUMBERED_HEADING.match(text):
        return "heading", 1, "inferred", "numbered heading: the file declares no outline level"
    if _SUBHEADING.match(text):
        return "heading", 2, "inferred", "parenthesised numbering: the file declares no outline level"
    # No outline level and no numbering: the file says this cell is not a heading,
    # which is a statement about the cell, not a missing one.
    return "body", None, "format", None

def _extract(
    path: Path,
    relative: str,
    source_id: str,
    revision: str,
    *,
    raw: bytes | None = None,
    unit_limit: int = _MAX_UNITS,
    locator_scope: Sequence[str] | None = None,
    report_sink: dict[str, Any] | None = None,
) -> tuple[list[_TextUnit], tuple[str, ...]]:
    if type(unit_limit) is not int or not 1 <= unit_limit <= 5000:
        raise ValueError("extraction unit limit must be between 1 and 5000")
    suffix = path.suffix.casefold()
    raw = path.read_bytes() if raw is None else raw
    if len(raw) > _MAX_FILE_BYTES:
        raise ValueError("document exceeds the bounded source size")
    warnings: list[str] = []
    part_errors: list[str] = []
    units: list[_TextUnit] = []
    def add(locator: str, quote: str, *, role: str | None = None, level: int | None = None,
            path: tuple[str, ...] = (), role_source: str | None = None,
            reason: str | None = None, unit_kind: str = "format",
            witness: bool = False) -> None:
        if locator_scope is not None and locator not in locator_scope:
            return
        quote = " ".join(quote.split())
        if quote:
            if len(quote) > 4000:
                warnings.append(f"PARTIAL_TEXT_UNIT_4000:{locator}")
            units.append(_TextUnit(
                source_id, relative, revision, revision, locator, quote[:4000],
                unit_kind=unit_kind, role=role, level=level, path=path,
                role_source=role_source, reason=reason,
                # The whole cell a name was assembled from. A name may rest on this; a
                # fact still needs a quote that can be found in the source on its own.
                witness={"text": quote, "locator": locator} if witness else None))

    def finish():
        truncated = len(units) > unit_limit
        if truncated:
            warnings.append(f"PARTIAL_LOCATOR_LIMIT_{unit_limit}")
        if report_sink is not None:
            report_sink.update({
                "locator_count": len(units),
                "truncated": truncated,
                "part_errors": tuple(part_errors),
            })
        return units[:unit_limit], tuple(dict.fromkeys(warnings))

    if suffix == ".xlsx":
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        relns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        workbook = ET.fromstring(_archive_read(raw, "xl/workbook.xml"))
        relationships = ET.fromstring(_archive_read(raw, "xl/_rels/workbook.xml.rels"))
        targets = {item.get("Id"): item for item in relationships}
        with zipfile.ZipFile(io.BytesIO(raw)) as package:
            names = set(package.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            strings = ET.fromstring(_archive_read(raw, "xl/sharedStrings.xml"))
            shared = [_xml_text(item) for item in strings if item.tag == ns + "si"]
        warnings.append("SPREADSHEET_FORMATTING_NOT_INTERPRETED")
        for sheet_no, sheet in enumerate(workbook.iter(ns + "sheet"), 1):
            relationship = targets.get(sheet.get(relns + "id"))
            if relationship is None or relationship.get("TargetMode") == "External":
                raise ValueError("worksheet relationship is missing or external")
            target = relationship.get("Target", "")
            member = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
            if not re.fullmatch(r"xl/worksheets/[^/]+\.xml", member):
                raise ValueError("worksheet relationship escapes the bounded workbook")
            document = ET.fromstring(_archive_read(raw, member))
            sheet_name = sheet.get("name", "")
            add(f"{member}#sheet:{sheet_no}:metadata", json.dumps({
                "sheet": sheet_name, "state": sheet.get("state", "visible"),
                "hierarchy": "NOT_INFERRED_FROM_BLANK_OR_MERGED_CELLS"}, ensure_ascii=False))
            merges = [item.get("ref", "") for item in document.iter(ns + "mergeCell")]
            if len(merges) > 5000 or any(not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*", ref) for ref in merges):
                raise ValueError("worksheet merge ranges are invalid or exceed bounds")
            for row in document.iter(ns + "row"):
                row_id = row.get("r", "")
                if not row_id.isdigit() or not 1 <= int(row_id) <= 1048576:
                    raise ValueError("worksheet row has no bounded position")
                cells = {}
                for cell in row.findall(ns + "c"):
                    address = cell.get("r", "")
                    if not re.fullmatch(r"[A-Z]{1,3}" + row_id, address) or address in cells:
                        raise ValueError("worksheet cell has invalid or duplicated coordinates")
                    value = cell.findtext(ns + "v", default="")
                    kind = cell.get("t", "n")
                    if kind == "s":
                        if not value.isdigit() or int(value) >= len(shared):
                            raise ValueError("worksheet shared string index is invalid")
                        value = shared[int(value)]
                    elif kind == "inlineStr":
                        content = cell.find(ns + "is")
                        value = _xml_text(content) if content is not None else ""
                    formula = cell.find(ns + "f")
                    if formula is not None:
                        warnings.append("FORMULA_NOT_RECALCULATED")
                        value = f"FORMULA_NOT_RECALCULATED({formula.text or ''}); CACHED_UNVERIFIED({value})"
                    if value:
                        cells[address] = value
                touching = [ref for ref in merges if int(re.search(r"[0-9]+", ref).group()) <= int(row_id) <= int(re.search(r"[0-9]+$", ref).group())]
                if cells or touching:
                    add(f"{member}#sheet:{sheet_no}:row:{row_id}", json.dumps({
                        "sheet": sheet_name, "row": int(row_id), "cells": cells,
                        "merged_ranges": touching}, ensure_ascii=False, separators=(",", ":")))
        return finish()

    if suffix == ".pptx":
        with zipfile.ZipFile(io.BytesIO(raw)) as package:
            members = [item for item in package.infolist() if not item.is_dir()]
            if len(members) > _MAX_ARCHIVE_MEMBERS:
                raise ValueError("presentation exceeds bounded package limits")
            slides = sorted(
                (item.filename for item in members if re.fullmatch(r"ppt/slides/slide\d+\.xml", item.filename)),
                key=lambda name: int(re.search(r"slide(\d+)", name).group(1)),
            )
            slide_set = set(slides)
            parsed_budget = sum(item.file_size for item in members if item.filename in slide_set)
            if parsed_budget > _MAX_ARCHIVE_UNCOMPRESSED:
                raise ValueError("presentation text exceeds bounded package limits")
            for slide_name in slides:
                try:
                    node = ET.fromstring(package.read(slide_name))
                except (ET.ParseError, KeyError, zipfile.BadZipFile, OSError) as exc:
                    part_errors.append(f"{slide_name}:{type(exc).__name__}")
                    continue
                # One pass in document order: a slide reads as it is laid out, and a
                # cell's place in the prompt is its place on the page.
                ordered = list(node.iter())
                # Addresses first: a drawn connection names its two ends, and an end is
                # the text box's own address, which is its number among the page's boxes.
                boxes: dict[str, dict] = {}
                located: dict[int, dict] = {}
                shape_no = 0
                for element in ordered:
                    if element.tag != _P + "sp":
                        continue
                    body = element.find(_P + "txBody")
                    lines = [line for line in _lines(body) if line.strip()] if body is not None else []
                    if not lines:
                        continue
                    shape_no += 1
                    cell = {"locator": f"{slide_name}#shape:{shape_no}",
                            "text": " ".join(lines), "lines": len(lines), "box": _shape_box(element)}
                    located[id(element)] = cell
                    if _shape_id(element):
                        boxes[_shape_id(element)] = cell
                cells: list[tuple[int, str, str, str | None, int | None, bool, str]] = []
                table_index = 0
                connector_no = 0
                for order, element in enumerate(ordered):
                    if element.tag == _P + "sp":
                        # A text box is the cell a reader sees. An org-chart box carries
                        # its label on two lines — "市场" over "副经理" — so cutting per
                        # run or per line splits one name into pieces no quote can rejoin.
                        cell = located.get(id(element))
                        if cell is None:
                            continue
                        role, level = _shape_role(element)
                        cells.append((order, cell["locator"], cell["text"], role, level,
                                      cell["lines"] > 1, "format"))
                    elif element.tag == _P + "cxnSp":
                        # The page draws the tree: a connection that names both of its
                        # ends is a relation the source carries, and the one thing the
                        # text of two neighbouring labels can never say.
                        connector_no += 1
                        drawn = _connector_cell(element, boxes)
                        cells.append((order, f"{slide_name}#cxn:{connector_no}", drawn["quote"],
                                      "connector", None, False, "structure"))
                    elif element.tag.endswith("}tbl"):
                        table_index += 1
                        for row_no, row in enumerate((child for child in element if child.tag.endswith("}tr")), 1):
                            for col_no, cell in enumerate((child for child in row if child.tag.endswith("}tc")), 1):
                                # Lines inside one cell are separate lines on the page; one
                                # space between them is the reader's line break, not a word.
                                cells.append((order, f"{slide_name}#table:{table_index}:r{row_no}:c{col_no}",
                                              " ".join(line for line in _lines(cell) if line.strip()),
                                              "table_cell", None, False, "format"))
                # Which state the page declares, said once, in the page's own title
                # words. A later stage reads this cell instead of deciding again.
                title = next((quote for _, _, quote, role, _, _, _ in cells if role == "title"), None)
                if title is not None:
                    cells.append((len(ordered) + 1, f"{slide_name}#state",
                                  json.dumps({"title": title, "declares": slide_state(title)},
                                             ensure_ascii=False, separators=(",", ":")),
                                  "state", None, False, "structure"))
                for _, locator, quote, role, level, witness, unit_kind in cells:
                    add(locator, quote, role=role, level=level, role_source="format",
                        witness=witness, unit_kind=unit_kind)
                # A table frame is read cell by cell above; only a visual that carries
                # text we cannot reach (a picture, a chart) is genuinely unread.
                unread_visual = any(
                    item.tag.endswith("}pic")
                    or (
                        item.tag.endswith("}graphicFrame")
                        and not any(child.tag.endswith("}tbl") for child in item.iter())
                    )
                    for item in node.iter()
                )
                if unread_visual:
                    warnings.append(f"NEEDS_VISION:{slide_name}")
                if not any(f"{slide_name}#" in unit.locator for unit in units):
                    warnings.append(f"NEEDS_VISION:{slide_name}")
        return finish()
    if suffix == ".docx":
        document = ET.fromstring(_archive_read(raw, "word/document.xml"))
        body = next((item for item in document.iter() if item.tag.endswith("}body")), document)
        styles = _docx_outline_levels(raw)
        # The headings seen so far, outermost first: every cell says which section it
        # sits under, so a semantic layer never has to infer the chain from text order.
        stack: list[tuple[int, str]] = []
        paragraph_no = 0
        table_no = 0
        for child in body:
            if child.tag.endswith("}p"):
                # Numbered before the skip: a locator must not move because an empty
                # paragraph or a field code was dropped.
                paragraph_no += 1
                locator = f"word/document.xml#paragraph:{paragraph_no}"
                text, apparatus, runs = _docx_paragraph_text(child)
                if apparatus:
                    # A table of contents, a page reference: the document's machinery.
                    # Counted where a reader would see a page number, never quoted.
                    warnings.append(f"APPARATUS:field_code:{locator}")
                    continue
                if not text.strip():
                    continue
                role, level, role_source, reason = _docx_role(child, text, styles)
                add(locator, text, role=role, level=level, path=tuple(name for _, name in stack),
                    role_source=role_source, reason=reason, witness=runs > 1)
                if role in {"heading", "title"} and level:
                    while stack and stack[-1][0] >= level:
                        stack.pop()
                    stack.append((level, " ".join(text.split())))
            elif child.tag.endswith("}tbl"):
                table_no += 1
                for row_no, row in enumerate((item for item in child if item.tag.endswith("}tr")), 1):
                    for col_no, cell in enumerate((item for item in row if item.tag.endswith("}tc")), 1):
                        # A cell's paragraphs are separate lines on the page; one space
                        # between them is the reader's spacing, not an invented word break.
                        text = " ".join(part for part in
                                        (_docx_paragraph_text(item)[0] for item in cell if item.tag.endswith("}p"))
                                        if part.strip())
                        add(f"word/document.xml#table:{table_no}:r{row_no}:c{col_no}", text,
                            role="table_cell", role_source="format",
                            path=tuple(name for _, name in stack))
        return finish()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return [], ("UNSUPPORTED_PDF_READER_UNAVAILABLE",)
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            return [], ("UNSUPPORTED_ENCRYPTED_PDF",)
        if len(reader.pages) > 250:
            raise ValueError("PDF exceeds bounded page count")
        for page_no, page in enumerate(reader.pages, 1):
            content = page.extract_text() or ""
            if not content.strip():
                warnings.append(f"NEEDS_VISION:page:{page_no}")
                continue
            for line_no, line in enumerate(content.splitlines(), 1):
                add(f"page:{page_no}#line:{line_no}", line)
        return finish()
    if len(raw) > _MAX_TEXT_BYTES:
        raise ValueError("text source exceeds bounded extraction size")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("text source is not UTF-8") from exc
    for line_no, line in enumerate(content.splitlines(), 1):
        add(f"line:{line_no}", line)
    return finish()

@dataclass(frozen=True)
class ExtractionReport:
    """What one extraction read, and — just as important — what it could not read."""

    unit_count: int
    locator_count: int
    truncated: bool
    part_errors: tuple[str, ...]
    vision_missing: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def status(self) -> str:
        if not self.unit_count:
            return "no_text"
        if self.truncated:
            return "truncated"
        if self.part_errors or self.vision_missing:
            return "partial"
        return "complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_count": self.unit_count,
            "locator_count": self.locator_count,
            "truncated": self.truncated,
            "part_errors": list(self.part_errors),
            "vision_missing": list(self.vision_missing),
            "status": self.status,
            "warnings": list(self.warnings),
        }


def extract_with_report(
    path: Path,
    relative: str,
    source_id: str,
    revision: str,
    *,
    raw: bytes | None = None,
    unit_limit: int = _MAX_EXTRACT_UNITS,
    locator_scope: Sequence[str] | None = None,
) -> tuple[list[_TextUnit], ExtractionReport]:
    """Read one source and report its completeness; never a silent half-read."""
    sink: dict[str, Any] = {}
    units, warnings = _extract(
        path, relative, source_id, revision,
        raw=raw, unit_limit=unit_limit, locator_scope=locator_scope, report_sink=sink,
    )
    return units, ExtractionReport(
        unit_count=len(units),
        locator_count=max(int(sink.get("locator_count", len(units))), len(units)),
        truncated=bool(sink.get("truncated", False)),
        part_errors=tuple(sink.get("part_errors", ())),
        vision_missing=tuple(item for item in warnings if item.startswith("NEEDS_VISION")),
        warnings=tuple(warnings),
    )


def _select_relevant_units(units: Sequence[_TextUnit], query: str, *, limit: int = 180) -> tuple[tuple[_TextUnit, ...], bool]:
    """Return a deterministic, bounded evidence slice for the selected query."""
    words = set(re.findall(r"[a-z0-9_]{2,}", query.casefold()))
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", query))
    words.update(cjk[index:index + 2] for index in range(max(0, len(cjk) - 1)))
    words.difference_update({"我们", "你们", "根据", "建立", "分析", "整理", "理解", "材料", "这些", "相关", "一个", "进行"})
    ranked = []
    for index, unit in enumerate(units):
        quote = unit.quote.casefold()
        score = sum(1 for word in words if word and word in quote)
        if score:
            ranked.append((score, index, unit))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    selected = [row[2] for row in ranked[:limit]]
    selected.sort(key=lambda unit: (unit.relative_path.casefold(), unit.locator))
    return tuple(selected), len(ranked) > limit

class _SourceMixin:
    """Methods of :class:`UnderstandPort` that belong to this concern."""

    def expand_evidence(
        self,
        source_inventory: Sequence[SourceRecord],
        existing_evidence_refs: Sequence[EvidenceRef],
        request: EvidenceExpansionRequest,
        *,
        source_root: Path | str,
        recorder: Any | None = None,
    ) -> EvidenceExpansionResult:
        """Search only already inventoried sources for additional source evidence.

        The returned map diagnostic is deliberately separate from any semantic
        answer or producer scoring object. This method performs no model calls.
        """
        if not isinstance(request.request_id, str) or not request.request_id.strip() or len(request.request_id) > 256:
            raise ValueError("request_id must contain between 1 and 256 characters")
        if not isinstance(request.query, str) or not request.query.strip() or len(request.query) > 2048:
            raise ValueError("query must contain between 1 and 2048 characters")
        if not 0 <= request.max_steps <= 8:
            raise ValueError("max_steps must be between 0 and the hard cap 8")
        if not 0 <= request.max_additional_refs <= 32:
            raise ValueError("max_additional_refs must be between 0 and the hard cap 32")
        if not 0 <= request.max_bytes <= _MAX_FILE_BYTES:
            raise ValueError(f"max_bytes must be between 0 and the hard cap {_MAX_FILE_BYTES}")
        if len(request.allowed_source_ids) > 32 or any(not isinstance(item, str) for item in request.allowed_source_ids):
            raise ValueError("allowed_source_ids exceeds the hard cap or contains invalid entries")
        if len(set(request.allowed_source_ids)) != len(request.allowed_source_ids):
            raise ValueError("allowed_source_ids contains duplicates")
        if len(request.known_evidence_ids) > _MAX_UNITS or any(not isinstance(item, str) for item in request.known_evidence_ids):
            raise ValueError("known_evidence_ids exceeds the hard cap or contains invalid entries")
        if len(set(request.known_evidence_ids)) != len(request.known_evidence_ids):
            raise ValueError("known_evidence_ids contains duplicates")
        if len(request.locator_hints) > 64 or any(not isinstance(item, str) or len(item) > 512 for item in request.locator_hints):
            raise ValueError("locator_hints exceeds the hard cap")
        if any(not isinstance(item, str) or not item.startswith("src_") for item in request.allowed_source_ids):
            raise ValueError("allowed_source_ids contains an invalid source identifier")
        if any(not isinstance(item, str) or not item.startswith("ev_") for item in request.known_evidence_ids):
            raise ValueError("known_evidence_ids contains an invalid evidence identifier")
        if len(source_inventory) > _MAX_UNITS or len(existing_evidence_refs) > _MAX_UNITS:
            raise ValueError("prepared inventory or evidence list exceeds the hard cap")

        root = Path(source_root).expanduser().resolve()
        request_digest = _sha(request.request_id.encode("utf-8"))
        query_digest = _sha(request.query.encode("utf-8"))
        allowed_digest = _sha("\n".join(sorted(request.allowed_source_ids)).encode("utf-8"))
        span = None
        if recorder is not None:
            span = recorder.start_span(
                "understand.evidence_expansion",
                kind="CHAIN",
                component_id="understand_port",
                component_version="0.1.0",
            )

        evidence_out: list[EvidenceRef] = []
        scanned: list[str] = []
        steps_used = 0
        bytes_read = 0
        stopping_reason = "no_matching_evidence"
        status = "NO_MATCH"

        def finish(final_status: str, reason: str) -> EvidenceExpansionResult:
            if recorder is not None and span is not None:
                map_status = "EVIDENCE_NOT_MAPPED" if final_status == "NO_MATCH" else final_status
                summary = (
                    f"status={final_status};map_status={map_status};request_sha256={request_digest};"
                    f"query_sha256={query_digest};allowed_source_set_sha256={allowed_digest};"
                    f"scanned_source_set_sha256={_sha(chr(10).join(sorted(scanned)).encode('utf-8'))};"
                    f"steps={steps_used}/{request.max_steps};bytes={bytes_read}/{request.max_bytes};"
                    f"refs={len(evidence_out)}/{request.max_additional_refs};"
                    f"remaining_steps={max(0, request.max_steps - steps_used)};"
                    f"remaining_bytes={max(0, request.max_bytes - bytes_read)};"
                    f"stop={reason};model_calls=0;source_text=excluded"
                )
                recorder.end_span(
                    span,
                    status="success" if final_status in {"EXPANDED", "NO_MATCH"} else "error",
                    attributes={"status": summary},
                )
            return EvidenceExpansionResult(
                request_id=request.request_id,
                status=final_status,
                map_status="EVIDENCE_NOT_MAPPED" if final_status == "NO_MATCH" else final_status,
                evidence_refs=tuple(evidence_out),
                source_ids_scanned=tuple(scanned),
                steps_used=steps_used,
                bytes_read=bytes_read,
                remaining_steps=max(0, request.max_steps - steps_used),
                remaining_refs=max(0, request.max_additional_refs - len(evidence_out)),
                remaining_bytes=max(0, request.max_bytes - bytes_read),
                stopping_reason=reason,
            )

        records_by_id: dict[str, SourceRecord] = {}
        records_by_path: dict[str, SourceRecord] = {}
        for record in source_inventory:
            if record.source_id in records_by_id or record.relative_path in records_by_path:
                return finish("DENIED", "ambiguous_prepared_inventory")
            records_by_id[record.source_id] = record
            records_by_path[record.relative_path] = record
        allowed_ids = set(request.allowed_source_ids)
        if not allowed_ids or not allowed_ids.issubset(records_by_id):
            return finish("DENIED", "source_not_in_prepared_inventory")
        if request.max_steps == 0 or request.max_additional_refs == 0 or request.max_bytes == 0:
            return finish("BUDGET_EXHAUSTED", "zero_expansion_budget")

        refs_by_id: dict[str, EvidenceRef] = {}
        for evidence in existing_evidence_refs:
            record = records_by_id.get(evidence.source_id)
            if record is None:
                return finish("DENIED", "evidence_source_not_in_prepared_inventory")
            expected_id = "ev_" + _sha(f"{evidence.source_id}\0{evidence.locator}\0{evidence.quote}".encode("utf-8"))[:24]
            if (
                evidence.evidence_id != expected_id
                or evidence.relative_path != record.relative_path
                or evidence.source_revision != record.source_revision
                or evidence.source_sha256 != record.source_sha256
                or evidence.span_sha256 != _sha(evidence.quote.encode("utf-8"))
                or evidence.evidence_id in refs_by_id
            ):
                return finish("DENIED", "prepared_evidence_integrity_failed")
            refs_by_id[evidence.evidence_id] = evidence
        if not set(request.known_evidence_ids).issubset(refs_by_id):
            return finish("DENIED", "known_evidence_not_in_prepared_result")
        known_ids = set(request.known_evidence_ids)
        locator_hints = set(request.locator_hints)

        for source_id in request.allowed_source_ids:
            if steps_used >= request.max_steps:
                status, stopping_reason = "BUDGET_EXHAUSTED", "step_budget_exhausted"
                break
            record = records_by_id[source_id]
            try:
                selected, relative = _safe_file(root / record.relative_path, root)
            except (OSError, PermissionError, ValueError):
                return finish("DENIED", "source_scope_or_type_denied")
            expected_source_id = "src_" + _sha(f"{root}\0{relative}".encode("utf-8"))[:20]
            if (
                relative != record.relative_path
                or expected_source_id != record.source_id
                or _media_type(selected) != record.media_type
                or record.source_revision != record.source_sha256
            ):
                return finish("DENIED", "prepared_source_identity_mismatch")
            try:
                size_before = selected.stat().st_size
            except OSError:
                return finish("STALE_SOURCE", "source_stat_failed")
            if size_before != record.byte_size or size_before > _MAX_FILE_BYTES:
                return finish("STALE_SOURCE", "source_size_changed_since_prepare")
            remaining_bytes = request.max_bytes - bytes_read
            if size_before > remaining_bytes:
                status, stopping_reason = "BUDGET_EXHAUSTED", "byte_budget_exhausted_before_read"
                break
            steps_used += 1
            try:
                with selected.open("rb") as source_file:
                    raw = source_file.read(size_before)
                bytes_read += len(raw)
                size_after = selected.stat().st_size
            except OSError:
                return finish("STALE_SOURCE", "source_read_failed")
            if len(raw) != size_before or size_after != size_before:
                return finish("STALE_SOURCE", "source_changed_during_read")
            current_digest = _sha(raw)
            if current_digest != record.source_sha256:
                return finish("STALE_SOURCE", "source_revision_changed_since_prepare")
            scanned.append(source_id)
            try:
                units, _warnings = _extract(selected, relative, source_id, current_digest, raw=raw)
            except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, tomllib.TOMLDecodeError):
                status, stopping_reason = "UNSUPPORTED", "source_extraction_failed"
                continue

            unseen = [unit for unit in units if _new_evidence(unit).evidence_id not in known_ids]
            hinted = [unit for unit in unseen if unit.locator in locator_hints]
            selected_by_query, _truncated = _select_relevant_units(unseen, request.query, limit=request.max_additional_refs)
            combined: list[_TextUnit] = []
            seen_ids: set[str] = set()
            for unit in (*hinted, *selected_by_query):
                evidence_id = _new_evidence(unit).evidence_id
                if evidence_id not in seen_ids:
                    combined.append(unit)
                    seen_ids.add(evidence_id)
            for unit in combined:
                if len(evidence_out) >= request.max_additional_refs:
                    status, stopping_reason = "EXPANDED", "additional_reference_budget_exhausted"
                    break
                evidence_out.append(_new_evidence(unit))
            if len(evidence_out) >= request.max_additional_refs:
                break

        if evidence_out:
            status = "EXPANDED"
            if stopping_reason == "no_matching_evidence":
                stopping_reason = "bounded_evidence_slice_returned"
        elif status not in {"BUDGET_EXHAUSTED", "UNSUPPORTED"}:
            status = "NO_MATCH"
            stopping_reason = "no_unmapped_unit_matched_query_or_locator"
        return finish(status, stopping_reason)

    @staticmethod
    def _inventory(sources: Sequence[tuple[Path, str]], root: Path,
                   source_evidence_scope: Mapping[str, Sequence[str] | None] | None = None,
                   require_complete: bool = False) -> tuple[tuple[SourceRecord, ...], tuple[_TextUnit, ...], tuple[str, ...]]:
        records: list[SourceRecord] = []
        units: list[_TextUnit] = []
        warnings: list[str] = []
        for path, relative in sources:
            raw = path.read_bytes()
            if len(raw) > _MAX_FILE_BYTES:
                warnings.append(f"UNSUPPORTED_OVERSIZE:{relative}")
                continue
            digest = _sha(raw)
            source_id = "src_" + _sha(f"{root.resolve()}\0{relative}".encode("utf-8"))[:20]
            try:
                extracted, item_warnings = _extract(path, relative, source_id, digest, raw=raw,
                    locator_scope=source_evidence_scope.get(relative) if source_evidence_scope is not None else None)
            except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, tomllib.TOMLDecodeError) as exc:
                extracted, item_warnings = [], (f"UNSUPPORTED_EXTRACTION:{type(exc).__name__}",)
            units.extend(extracted)
            warnings.extend(f"{warning}:{relative}" for warning in item_warnings)
            records.append(SourceRecord(
                source_id=source_id, relative_path=relative, media_type=_media_type(path),
                source_revision=digest, source_sha256=digest, byte_size=len(raw),
                extracted_text_sha256=_sha("\n".join(item.quote for item in extracted).encode("utf-8")),
                locator_count=len(extracted),
                extraction_status="PARTIAL" if item_warnings else "COMPLETE",
            ))
        if len(units) > _MAX_UNITS:
            # Ontology modeling must see the whole inventory: a truncated view
            # would cap what a candidate can ever contain while looking complete.
            if require_complete:
                raise SemanticCapacityError(_MAX_UNITS, len(units), what="source units")
            warnings.append(f"UNITS_TRUNCATED:{len(units)} units were inventoried and only the first {_MAX_UNITS} reach the caller")
        return tuple(records), tuple(units[:_MAX_UNITS]), tuple(warnings)
