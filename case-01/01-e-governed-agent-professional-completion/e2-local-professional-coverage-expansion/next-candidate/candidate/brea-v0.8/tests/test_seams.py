"""SEAM-01 / SEAM-02 / SEAM-03 unit-level tests + corpus fail-closed."""
from __future__ import annotations

import sys
import hashlib
import json
from pathlib import Path

CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANDIDATE_ROOT))
KR_PATH = CANDIDATE_ROOT.parents[1] / "knowledge" / "KR-001.json"


def _knowledge() -> dict:
    return json.loads(KR_PATH.read_text(encoding="utf-8"))


def _binding() -> dict:
    return {"revision_id": "KR-001", "path": str(KR_PATH),
            "sha256": hashlib.sha256(KR_PATH.read_bytes()).hexdigest()}

from brea.applicability import applicability_for_question, resolve_level  # noqa: E402
from brea.corpus import (  # noqa: E402
    Corpus,
    CorpusIntegrityError,
    load_corpora,
)
from brea.evidence import assert_verbatim, locate_clause, locate_table_row  # noqa: E402
from brea.facts import missing_facts, normalize_facts  # noqa: E402


def test_seam01_facts() -> None:
    facts = normalize_facts({"Building Category": "大型商业", "Floor Area m2": 15000})
    assert facts == {"building_category": "大型商业", "floor_area_m2": 15000.0}
    assert "jurisdiction" in missing_facts(facts)
    try:
        normalize_facts({"floor_area_m2": "abc"})
        raise AssertionError("expected ValueError for non-numeric floor area")
    except ValueError:
        pass


def test_seam02_applicability() -> None:
    knowledge = _knowledge()
    corpora = load_corpora(knowledge["sources"])
    dbj = corpora["DBJ33T1021-2023"]
    level = resolve_level(dbj, "规划人口大于50万的城市", knowledge)
    assert level is not None
    facts = {"jurisdiction": "浙江省·杭州市", "city_class": "规划人口大于50万的城市"}
    chain = applicability_for_question("某项目机动车配建停车位指标应为多少？", facts, dbj, knowledge)
    assert chain["standard_id"] == "DBJ33T1021-2023"
    assert chain["level"] is not None


def test_seam03_evidence() -> None:
    corpora = load_corpora(_knowledge()["sources"])
    gb = corpora["GB55037-2022"]
    dbj = corpora["DBJ33T1021-2023"]
    found = locate_clause(gb, "3.1.3")
    assert found is not None
    assert_verbatim(gb, found["text"])
    row = locate_table_row(dbj, "表5.0.4商业场所停车位指标", "大型商业", 15000.0, 5)
    assert row is not None
    assert "大型商业" in row["label"]


def test_corpus_fail_closed() -> None:
    row = _knowledge()["sources"][0]
    try:
        Corpus(row["source_id"], row["file_name"], row["local_reference"], "0" * 64)
        raise AssertionError("expected CorpusIntegrityError on SHA mismatch")
    except CorpusIntegrityError:
        pass


def run_all() -> int:
    failures = 0
    tests = (test_seam01_facts, test_seam02_applicability, test_seam03_evidence,
             test_corpus_fail_closed)
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    return failures
