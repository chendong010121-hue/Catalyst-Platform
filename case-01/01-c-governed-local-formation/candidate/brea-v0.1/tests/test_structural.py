"""ST-01..ST-08 — structural / architecture tests.

ST-06 numeric traceability is the local formation/build verification (source-level
semantics), not OBL-03 public semantics (B-01 discipline).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANDIDATE_ROOT))

import brea  # noqa: E402,F401  (import smoke: package importable)
from brea.corpus import case_root, load_corpora, resolve_manifest  # noqa: E402
from brea.identity import BREA_FUNCTION_MAP, OBLIGATIONS, SEAM_MAP  # noqa: E402
from brea.runner import answer  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "requests"


def _run_fixture(name: str, ent: dict):
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    request = data["request"]
    return answer(
        request["request_id"], request["question"], request["project_context"],
        request["regulation_context"], ent,
    )


def test_st01_all_functions_mapped() -> None:
    expected = [f"FN-{index:02d}" for index in range(1, 12)]
    assert sorted(BREA_FUNCTION_MAP) == sorted(expected)
    for fn in expected:
        name, module, status = BREA_FUNCTION_MAP[fn]
        assert name and module and status


def test_st02_seams_explicit() -> None:
    assert set(SEAM_MAP) == {"SEAM-01", "SEAM-02", "SEAM-03"}
    for _seam, (name, owner, functions, module) in SEAM_MAP.items():
        assert name and owner and functions and module


def test_st03_no_provider_semantic_authority() -> None:
    assert not (CANDIDATE_ROOT / "brea" / "provider.py").exists()
    assert not (CANDIDATE_ROOT / "brea" / "providers").exists()


def test_st04_prompt_non_authority() -> None:
    prompt_files = [
        path for path in CANDIDATE_ROOT.rglob("*")
        if path.is_file() and (path.name.lower().endswith((".prompt", ".prompts")) or path.name == "AGENTS.md")
    ]
    assert prompt_files == []


def test_st05_enterprise_orthogonality() -> None:
    base = _run_fixture("T-C02", {"organization_id": "org-a", "user_id": "u-a", "project_id": "p-a"})
    other = _run_fixture("T-C02", {"organization_id": "org-b", "user_id": "u-b", "project_id": "p-b"})
    assert base.conclusion == other.conclusion
    assert base.evidence_items == other.evidence_items
    assert base.implementation_metadata.enterprise_context_attribution != \
        other.implementation_metadata.enterprise_context_attribution


def test_st06_numeric_traceability() -> None:
    _ = load_corpora()  # corpus present + SHA verified (else CorpusIntegrityError)
    for name in ("T-C01", "T-C02"):
        result = _run_fixture(name, {"organization_id": "org-a", "user_id": "u-a"})
        for number in re.findall(r"\d+(?:\.\d+)?(?=\s*(?:m|车位|㎡))", result.conclusion):
            assert any(
                number in re.sub(r"\s+", "", item.evidence_content)
                for item in result.evidence_items
            ), f"numeric value {number} not traceable to evidence ({name})"


def test_st07_corpus_sha_fail_closed() -> None:
    from brea.corpus import Corpus, CorpusIntegrityError, load_manifest_rows

    row = load_manifest_rows(resolve_manifest(case_root()))[0]
    try:
        Corpus(row["corpus_id"], row["file"], row["path"], "0" * 64)
        raise AssertionError("expected CorpusIntegrityError on SHA mismatch")
    except CorpusIntegrityError:
        pass


def test_st08_answer_writes_nothing_without_out_dir() -> None:
    before = {path for path in CANDIDATE_ROOT.rglob("*") if path.is_file()}
    _run_fixture("T-C02", {"organization_id": "org-a", "user_id": "u-a"})
    after = {path for path in CANDIDATE_ROOT.rglob("*") if path.is_file()}
    assert before == after


def run_all() -> int:
    failures = 0
    tests = (
        test_st01_all_functions_mapped,
        test_st02_seams_explicit,
        test_st03_no_provider_semantic_authority,
        test_st04_prompt_non_authority,
        test_st05_enterprise_orthogonality,
        test_st06_numeric_traceability,
        test_st07_corpus_sha_fail_closed,
        test_st08_answer_writes_nothing_without_out_dir,
    )
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    return failures
