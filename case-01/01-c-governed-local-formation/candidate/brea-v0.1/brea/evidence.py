"""SEAM-03 — Regulation Evidence (DOMAIN numeric authority + AGENT binding; FN-04/05/08).

FN-04 locate/extract verbatim evidence; FN-05 bind claim<->evidence + numeric safety;
FN-08 artifact / provenance preservation. Numeric authority always stays in the
admitted corpus text — no implementation-generated numeric authority (OBL-03).
"""
from __future__ import annotations

import re
from pathlib import Path

from .contracts import ArtifactRef, EvidenceItem
from .corpus import (
    Corpus,
    extract_clauses,
    extract_table,
    line_range,
    norm,
    page_of,
    table_region,
)

_AREA_COND = re.compile(r"建筑面积\s*([<>≤≥])\s*(\d+)\s*m")


def locate_clause(corpus: Corpus, clause_id: str) -> dict | None:
    text = extract_clauses(corpus).get(clause_id)
    if text is None:
        return None
    start = next(i for i, line in enumerate(corpus.lines) if line.startswith(clause_id))
    end = start + len(text.split("\n"))
    return {"text": text, "start": start, "end": end, "page": page_of(corpus, start)}


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


def assert_verbatim(corpus: Corpus, evidence_content: str) -> None:
    """FN-05 numeric/evidence safety: evidence content must be verbatim in the corpus."""
    if not corpus.contains(evidence_content):
        raise AssertionError("evidence_content is not verbatim in the admitted corpus")


def write_artifact(out_dir: Path, artifact_id: str, title: str, body: str) -> ArtifactRef:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{artifact_id}.md"
    path.write_text(body, encoding="utf-8")
    return ArtifactRef(artifact_id=artifact_id, title=title, path=str(path), kind="verbatim_evidence_bundle")
