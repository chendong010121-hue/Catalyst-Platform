"""FN-09 Corpus access & parsing — PRIVATE IMPLEMENTATION (E1 EXTENDED).

Reads local source references supplied by an explicit Knowledge Revision binding.
SHA-256 verified; mismatch fails closed (CorpusIntegrityError). Raw corpus is never
written into this repository (upstream = FORBIDDEN).

E1 extension (FN-09 major implementation completion):
  - clause_index(): generic clause-id -> {text, start, end, page}
  - table_captions(): generic caption index for reliable OCR table captions
  - resolve_table_caption(): caption lookup by table number
  - search_units(): normalized text units for deterministic topic retrieval

All lookups are data-driven from the admitted corpus text; no clause/table id is
hardcoded into the mechanism (E1 anti-fixture rule, spec §4/§15).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

class CorpusIntegrityError(RuntimeError):
    """Corpus missing / SHA mismatch / manifest missing — fail closed."""


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Corpus:
    def __init__(self, corpus_id: str, file_name: str, path: str, expected_sha: str):
        self.corpus_id = corpus_id
        self.file_name = file_name
        self.path = Path(path)
        self.expected_sha = expected_sha
        self.verify()
        self.raw = self.path.read_text(encoding="utf-8")
        self.lines = [line.rstrip("\r\n") for line in self.raw.split("\n")]

    def verify(self) -> None:
        if not self.path.is_file():
            raise CorpusIntegrityError(f"corpus file missing: {self.path}")
        actual = _sha256(self.path)
        if actual != self.expected_sha:
            raise CorpusIntegrityError(
                f"{self.corpus_id} SHA mismatch: expected {self.expected_sha}, got {actual}"
            )

    def contains(self, text: str) -> bool:
        return norm(text) in norm(self.raw)


def load_corpora(source_records: list[dict]) -> dict[str, Corpus]:
    if not isinstance(source_records, list) or not source_records:
        raise CorpusIntegrityError("knowledge revision contains no source records")
    corpora: dict[str, Corpus] = {}
    for row in source_records:
        try:
            source_id = row["source_id"]
            file_name = row["file_name"]
            local_reference = row["local_reference"]
            sha256 = row["sha256"]
        except (KeyError, TypeError) as exc:
            raise CorpusIntegrityError("knowledge source record is incomplete") from exc
        corpus = Corpus(source_id, file_name, local_reference, sha256)
        corpora[source_id] = corpus
        corpora[Path(file_name).stem] = corpus
    return corpora


# ---- private parsing helpers (implementation HOW) ----
_PAGE_RE = re.compile(r"^\[page (\d+)\]$")
_CLAUSE_RE = re.compile(r"^(\d+\.\d+\.\d+)(.*)$")
_SECTION_RE = re.compile(r"^\d+(\.\d+)?[^\d.]")
_FOOTER_RE = re.compile(r"^[·.\s]*\d+[·.\s]*$")
_TABLE_CAPTION_RE = re.compile(r"^表(\d+(?:\.\d+)+)(?:-(\d+))?([^\d].*)?$")
_VALUE_RE = re.compile(r"^\d[\s.]*\d?$")
_HEADER_TOKENS = {
    "项目", "机动车", "非机动车", "（车位/100m²", "建筑面积)",
    "I", "Ⅱ", "Ⅲ", "ⅢI", "内部", "外部", "指标级别", "适用范围",
}


def page_of(corpus: Corpus, line_index: int) -> int:
    for i in range(line_index, -1, -1):
        match = _PAGE_RE.match(corpus.lines[i])
        if match:
            return int(match.group(1))
    return 0


def extract_clauses(corpus: Corpus) -> dict[str, str]:
    clauses: dict[str, list[str]] = {}
    current: str | None = None
    for line in corpus.lines:
        if _PAGE_RE.match(line):
            continue
        match = _CLAUSE_RE.match(line)
        if match:
            current = match.group(1)
            clauses[current] = [match.group(2)]
            continue
        if _SECTION_RE.match(line):
            current = None
            continue
        if current is None:
            continue
        if _FOOTER_RE.match(line):
            continue
        clauses[current].append(line)
    return {key: "\n".join(value) for key, value in clauses.items()}


def clause_index(corpus: Corpus) -> dict[str, dict]:
    """Generic clause index: clause_id -> {text, start, end, page}.

    Data-driven: every `X.Y.Z`-style clause line in the admitted corpus becomes an
    index entry. No clause id is special-cased.
    """
    index: dict[str, dict] = {}
    current: str | None = None
    buf: list[str] = []
    start = 0
    for i, line in enumerate(corpus.lines):
        if _PAGE_RE.match(line) or _FOOTER_RE.match(line):
            continue
        match = _CLAUSE_RE.match(line)
        if match:
            if current is not None:
                index[current] = {
                    "text": "\n".join(buf).strip(),
                    "start": start, "end": i - 1,
                    "page": page_of(corpus, start),
                }
            current = match.group(1)
            buf = [match.group(2)]
            start = i
            continue
        if _SECTION_RE.match(line):
            if current is not None:
                index[current] = {
                    "text": "\n".join(buf).strip(),
                    "start": start, "end": i - 1,
                    "page": page_of(corpus, start),
                }
            current = None
            buf = []
            continue
        if current is not None:
            buf.append(line)
    if current is not None:
        index[current] = {
            "text": "\n".join(buf).strip(),
            "start": start, "end": len(corpus.lines) - 1,
            "page": page_of(corpus, start),
        }
    return index


def _is_caption(line: str) -> bool:
    """General OCR caption filter for this source format (spec §15 allowed: table
    structure knowledge general to that source format).

    A caption line starts with `表N.M(.K)(-L)` and the trailing text (if any) is a
    title, NOT a sentence continuation such as 规定，且… (prose cross-references).
    """
    stripped = line.strip()
    match = _TABLE_CAPTION_RE.match(stripped)
    if not match:
        return False
    rest = match.group(3) or ""
    if not rest:
        return True  # bare numbered caption
    # title-like continuation (ends with a noun/unit), not prose continuation
    if rest.startswith(("规定", "中", "的", "为", "应", "见", "按", "（含", "所", "且")):
        return False
    return True


def table_captions(corpus: Corpus) -> list[str]:
    """All reliable table captions in the admitted corpus (data-driven)."""
    return [line.strip() for line in corpus.lines if _is_caption(line)]


def resolve_table_caption(corpus: Corpus, table_number: str) -> str | None:
    """Resolve `表X.Y.Z` (or `表X.Y.Z-L`) to the full caption line.

    table_number is a normalized table locator. Matching is by normalized caption
    prefix — the caption index, not a hardcoded table list.
    """
    target = norm(f"表{table_number}")
    for caption in table_captions(corpus):
        if norm(caption).startswith(target):
            return caption
    return None


def table_region(corpus: Corpus, caption: str) -> str:
    start = next(i for i, line in enumerate(corpus.lines) if line.strip().startswith(caption))
    region: list[str] = []
    for line in corpus.lines[start:]:
        if line is not corpus.lines[start] and (
            line.startswith("[page ") or re.match(r"^\d+\.\d+\.\d+", line)
        ):
            break
        region.append(line)
    return "\n".join(region)


def line_range(corpus: Corpus, caption: str, nlines: int) -> tuple[int, int]:
    start = next(i for i, line in enumerate(corpus.lines) if line.strip().startswith(caption))
    return start + 1, start + nlines


def search_units(corpus: Corpus) -> list[dict]:
    """Deterministic retrieval units: one per clause (id + normalized text + locator).

    Units are built from the generic clause index; used by the topic search.
    """
    units = []
    for clause_id, info in clause_index(corpus).items():
        text = info["text"]
        if not text:
            continue
        units.append({
            "unit_id": clause_id,
            "kind": "clause",
            "text": text,
            "norm": norm(text),
            "locator": f"第{clause_id}条（OCR 副本 [page {info['page']}]，本地副本行 {info['start'] + 1}-{info['end']}）",
        })
    return units


def extract_table(corpus: Corpus, caption: str, ncols: int) -> list[tuple[str, list[str]]]:
    start = next(i for i, line in enumerate(corpus.lines) if line.strip().startswith(caption))
    rows: list[tuple[str, list[str]]] = []
    label: list[str] = []
    values: list[str] = []
    for line in corpus.lines[start + 1:]:
        if line.startswith("[page ") or re.match(r"^\d+\.\d+\.\d+", line):
            break
        match = _VALUE_RE.match(line.strip())
        if match and len(values) < ncols:
            values.append(line.strip())
            if len(values) == ncols:
                rows.append(("".join(label).strip(), values))
                label, values = [], []
        elif match:
            rows.append(("".join(label).strip(), values))
            label, values = [], [line.strip()]
        else:
            if norm(line.strip()) in _HEADER_TOKENS:
                continue
            label.append(line.strip())
    if values and len(values) == ncols:
        rows.append(("".join(label).strip(), values))
    return rows


def extract_level_scope(corpus: Corpus, caption: str) -> list[tuple[str, str]]:
    start = next(i for i, line in enumerate(corpus.lines) if line.strip().startswith(caption))
    out: list[tuple[str, str]] = []
    current: str | None = None
    for line in corpus.lines[start + 1:]:
        if line.startswith("[page ") or re.match(r"^\d+\.\d+\.\d+", line):
            break
        value = line.strip()
        if value in ("I", "Ⅱ", "Ⅲ", "ⅢI"):
            current = value
            continue
        if current is not None and value:
            out.append((current, value))
            current = None
    return out
