"""T-C01 / T-C02 / T-C03 — whole-Agent formation cases.

Tests never match hardcoded expected answer text: numeric values are checked
against the verbatim evidence (which itself must be contained in the admitted
corpus), so a wrong-but-consistent extraction cannot pass silently.
"""
from __future__ import annotations

import json
import hashlib
import re
import sys
from pathlib import Path

CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.runner import answer  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "requests"
KR_PATH = CANDIDATE_ROOT.parents[1] / "knowledge" / "KR-001.json"


def _binding() -> dict:
    return {
        "revision_id": "KR-001",
        "path": str(KR_PATH),
        "sha256": hashlib.sha256(KR_PATH.read_bytes()).hexdigest(),
    }


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _run(name: str):
    data = _load(name)
    request = data["request"]
    return answer(
        request["request_id"],
        request["question"],
        request["project_context"],
        request["regulation_context"],
        request["enterprise_context"],
        knowledge_binding=_binding(),
    )


def _first_number(text: str) -> str | None:
    match = re.search(r"\d+(?:\.\d+)?", text)
    return match.group(0) if match else None


def _normative_number(conclusion: str) -> str | None:
    """The normative value immediately after '不应小于' (the conclusion's own value)."""
    match = re.search(r"不应小于\s*(\d+(?:\.\d+)?)", conclusion)
    return match.group(1) if match else None


def _flatten(text: str) -> str:
    return re.sub(r"\s+", "", text)


def test_t_c01_direct_clause() -> None:
    result = _run("T-C01")
    assert result.status == "accepted_with_evidence"
    assert len(result.evidence_items) >= 1
    item = result.evidence_items[0]
    assert item.source_identity == "GB 55037-2022"
    assert "3.1.3" in item.locator
    assert item.evidence_type == "normative_clause"
    assert item.claim_relation == "supports"
    number = _normative_number(result.conclusion)
    assert number is not None
    assert number in _flatten(item.evidence_content)  # numeric safety: value in verbatim evidence
    assert result.uncertainty.level == "low"
    assert result.implementation_metadata.model_used == "none"


def test_t_c02_conditional_table() -> None:
    result = _run("T-C02")
    assert result.status == "accepted_with_evidence"
    assert any("表5.0.1" in item.locator for item in result.evidence_items)
    row_item = next(item for item in result.evidence_items if "表5.0.4" in item.locator)
    assert "大型商业" in row_item.locator
    number = _normative_number(result.conclusion)
    assert number is not None
    assert number in _flatten(row_item.evidence_content)
    attribution = result.implementation_metadata.enterprise_context_attribution
    assert attribution["project_id"] == "proj-commercial-001"


def test_t_c03_fail_closed() -> None:
    result = _run("T-C03")
    assert result.status == "insufficient_context"
    assert not re.search(r"\d", result.conclusion)
    assert "缺失" in result.conclusion
    assert result.evidence_items == ()


def run_all() -> int:
    failures = 0
    for test in (test_t_c01_direct_clause, test_t_c02_conditional_table, test_t_c03_fail_closed):
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    return failures
