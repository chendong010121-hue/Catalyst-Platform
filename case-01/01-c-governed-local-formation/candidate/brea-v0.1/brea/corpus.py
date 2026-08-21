"""FN-09 Corpus access & parsing — PRIVATE IMPLEMENTATION.

Reads the admitted local corpus through the CASE 01-B reference manifest
(case-01/01-b-governed-agent-definition/evidence/LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md).
SHA-256 verified; mismatch fails closed (CorpusIntegrityError). Raw corpus is never
written into this repository (upstream = FORBIDDEN).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

_CASE_ROOT = Path(__file__).resolve().parents[4]  # case-01/
MANIFEST_REL = Path("01-b-governed-agent-definition") / "evidence" / "LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md"


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


def case_root() -> Path:
    return _CASE_ROOT


def resolve_manifest(case_root_path: Path) -> Path:
    return case_root_path / MANIFEST_REL


def load_manifest_rows(manifest: Path) -> list[dict]:
    if not manifest.is_file():
        raise CorpusIntegrityError(f"corpus manifest missing: {manifest}")
    rows: list[dict] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|") or "CORPUS-" not in line:
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) >= 4 and cells[0].startswith("CORPUS-"):
            rows.append({
                "corpus_id": cells[0],
                "file": cells[1],
                "path": cells[2],
                "sha": cells[3].lower(),
            })
    if not rows:
        raise CorpusIntegrityError("corpus manifest contains no CORPUS rows")
    return rows


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


def load_corpora(case_root_path: Path | None = None) -> dict[str, Corpus]:
    root = case_root_path or _CASE_ROOT
    manifest = resolve_manifest(root)
    corpora: dict[str, Corpus] = {}
    for row in load_manifest_rows(manifest):
        corpus = Corpus(row["corpus_id"], row["file"], row["path"], row["sha"])
        corpora[row["corpus_id"]] = corpus
        corpora[Path(row["file"]).stem] = corpus  # also key by standard id (e.g. GB55037-2022)
    return corpora


# ---- private parsing helpers (implementation HOW) ----
_PAGE_RE = re.compile(r"^\[page (\d+)\]$")
_CLAUSE_RE = re.compile(r"^(\d+\.\d+\.\d+)(.*)$")
_SECTION_RE = re.compile(r"^\d+(\.\d+)?[^\d.]")
_FOOTER_RE = re.compile(r"^[·.\s]*\d+[·.\s]*$")
_VALUE_RE = re.compile(r"^\d[\s.]*\d?$")
_HEADER_TOKENS = {
    "项目", "机动车", "非机动车", "（车位/100m²", "建筑面积)",
    "I", "Ⅱ", "Ⅲ", "ⅢI", "内部", "外部", "指标级别", "适用范围",
    "配建指标级别及适用范围",
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
