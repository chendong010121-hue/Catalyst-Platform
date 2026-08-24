"""SEAM-03 — Regulation Evidence (DOMAIN numeric authority + AGENT binding; FN-04/05/08).

FN-04 locate/extract verbatim evidence; FN-05 bind claim<->evidence + numeric safety;
FN-08 artifact / provenance preservation. Numeric authority always stays in the
admitted corpus text — no implementation-generated numeric authority (OBL-03).

E1 extension (FN-04/FN-05 major implementation completion):
  - generic clause lookup by ANY clause locator (clause_index, no special-casing)
  - generic table-caption resolution + table-region evidence
  - deterministic topic-window extraction for local evidence search
All data-driven from the admitted corpus; no clause/table id hardcoded (spec §4).
"""
from __future__ import annotations

import re
from pathlib import Path

from .contracts import ArtifactRef, EvidenceItem
from .corpus import (
    Corpus,
    clause_index,
    extract_table,
    line_range,
    norm,
    page_of,
    resolve_table_caption,
    table_captions,
    table_region,
)

_AREA_COND = re.compile(r"建筑面积\s*([<>≤≥])\s*(\d+)\s*m")


def locate_clause(corpus: Corpus, clause_id: str) -> dict | None:
    """Generic clause lookup by locator (QMODE-01/02). No clause id is special-cased."""
    return clause_index(corpus).get(clause_id)


def all_clause_ids(corpus: Corpus) -> list[str]:
    """Data-driven clause id list (used for 'does clause exist' checks)."""
    return sorted(clause_index(corpus))


def resolve_caption(corpus: Corpus, table_number: str) -> str | None:
    """Resolve `表X.Y.Z` -> full caption, or None if the table is not reliably parseable."""
    return resolve_table_caption(corpus, table_number)


def locate_table_region(corpus: Corpus, caption: str) -> dict | None:
    """Return {caption, region, start, end, page} for a resolved caption (QMODE-04)."""
    if caption not in table_captions(corpus):
        return None
    region = table_region(corpus, caption)
    s, e = line_range(corpus, caption, len(region.split("\n")))
    return {
        "caption": caption,
        "region": region,
        "start": s,
        "end": e,
        "page": page_of(corpus, s - 1),
    }


def locate_table_row(
    corpus: Corpus,
    caption: str,
    category: str,
    floor_area: float,
    ncols: int,
) -> dict | None:
    rows = extract_table(corpus, caption, ncols)
    for label, raw_values in rows:
        if category not in label:
            continue
        match = _AREA_COND.search(label)
        if floor_area is not None and match:
            operator, threshold = match.group(1), float(match.group(2))
            ok = {
                "<": floor_area < threshold,
                ">": floor_area > threshold,
                "≤": floor_area <= threshold,
                "≥": floor_area >= threshold,
            }[operator]
            if not ok:
                continue
        region = table_region(corpus, caption)
        s, e = line_range(corpus, caption, len(region.split("\n")))
        return {
            "label": label,
            "raw_values": raw_values,
            "region": region,
            "start": s,
            "end": e,
            "page": page_of(corpus, s - 1),
        }
    return None


def make_evidence_item(
    source_identity: str,
    source_title: str,
    source_version_or_date: str,
    locator: str,
    evidence_type: str,
    evidence_content: str,
    claim_relation: str,
) -> EvidenceItem:
    return EvidenceItem(
        source_identity=source_identity,
        source_title=source_title,
        source_version_or_date=source_version_or_date,
        locator=locator,
        evidence_type=evidence_type,
        evidence_content=evidence_content,
        claim_relation=claim_relation,
    )


def make_topic_evidence(
    source_identity: str,
    source_title: str,
    source_version_or_date: str,
    unit: dict,
    claim_relation: str = "related",
) -> EvidenceItem:
    """Evidence item for a topic-search unit (verbatim excerpt + locator)."""
    return make_evidence_item(
        source_identity,
        source_title,
        source_version_or_date,
        unit["locator"],
        "topic_excerpt",
        unit["text"],
        claim_relation,
    )


def assert_verbatim(corpus: Corpus, evidence_content: str) -> None:
    """FN-05 numeric/evidence safety: evidence content must be verbatim in the corpus.

    Verbatim is checked at LINE level (normalized): every non-empty line of the
    evidence content must appear inside some admitted corpus line. This is exactly
    what the extractors preserve — clause bodies are copied verbatim from corpus
    lines (the first body line may lack the leading `X.Y.Z` clause-id prefix, and
    clauses/tables may span OCR `[page N]` markers, so whole-string containment of
    multi-page text is not the right check).
    """
    corpus_line_norms = [norm(line) for line in corpus.lines]
    missing = []
    for line in evidence_content.splitlines():
        if not line.strip():
            continue
        needle = norm(line)
        if not any(needle in candidate for candidate in corpus_line_norms):
            missing.append(needle)
    if missing:
        raise AssertionError(
            f"evidence_content is not verbatim in the admitted corpus ({len(missing)} lines)"
        )


def write_artifact(out_dir: Path, artifact_id: str, title: str, body: str) -> ArtifactRef:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{artifact_id}.md"
    path.write_text(body, encoding="utf-8")
    return ArtifactRef(artifact_id=artifact_id, title=title, path=str(path), kind="verbatim_evidence_bundle")
