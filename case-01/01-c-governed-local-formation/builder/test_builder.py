"""Builder proof tests BT-01..BT-10 (C-01..C-05 closure, definition-driven proof)."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

BUILDER_DIR = Path(__file__).resolve().parent
WS01C = BUILDER_DIR.parent
CASE_ROOT = WS01C.parent
sys.path.insert(0, str(BUILDER_DIR))

import definition_parser as dp  # noqa: E402
import run_builder as rb  # noqa: E402

DEFINITION_PATH = CASE_ROOT / "01-b-governed-agent-definition" / "builder" / "BUILDER_CONSUMABLE_DEFINITION_V0.1.md"


def _parsed() -> dict:
    return dp.parse_definition(DEFINITION_PATH.read_text(encoding="utf-8"))


def test_bt01_accepted_sha_passes() -> None:
    rb.check_definition_sha(DEFINITION_PATH, dp.EXPECTED_DEFINITION_SHA)


def test_bt02_wrong_sha_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        modified = Path(tmp) / "modified-definition.md"
        modified.write_text(
            DEFINITION_PATH.read_text(encoding="utf-8") + "\n<!-- tampered -->\n",
            encoding="utf-8",
        )
        try:
            rb.check_definition_sha(modified, dp.EXPECTED_DEFINITION_SHA)
            raise AssertionError("expected DefinitionShaMismatch")
        except rb.DefinitionShaMismatch:
            pass


def test_bt03_fn_set_parsed() -> None:
    parsed = _parsed()
    expected = {f"FN-{index:02d}" for index in range(1, 12)}
    assert set(parsed["functions"]) == expected
    for fn, info in parsed["functions"].items():
        assert info["name"] and info["governance"]


def test_bt04_seam_set_parsed() -> None:
    parsed = _parsed()
    assert set(parsed["seams"]) == {"SEAM-01", "SEAM-02", "SEAM-03"}
    for seam, info in parsed["seams"].items():
        assert info["owner"] and info["functions"]


def test_bt05_obligations_parsed() -> None:
    parsed = _parsed()
    assert parsed["obligations"] == {f"OBL-{index:02d}" for index in range(1, 7)}


def test_bt06_request_cannot_override_architecture() -> None:
    try:
        rb.validate_request({"functions": [{"fn": "FN-01", "governance": "INVENTED"}]})
        raise AssertionError("expected RequestArchitectureDuplication")
    except rb.RequestArchitectureDuplication:
        pass
    rb.validate_request({"candidate_id": "brea-v0.1", "target_directory": "x"})


def test_bt07_generated_candidate_matches_definition() -> None:
    parsed = _parsed()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "brea-v0.1"
        rb.generate(target, rb.TEMPLATES_DIR)
        rb.validate_generated_candidate(target, parsed)


def test_bt08_obligation_refs_exist() -> None:
    parsed = _parsed()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "brea-v0.1"
        rb.generate(target, rb.TEMPLATES_DIR)
        rb.validate_obligation_refs(target, rb.OBLIGATION_MAPPING)
        assert set(rb.OBLIGATION_MAPPING) == parsed["obligations"]


def test_bt09_non_empty_target_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "brea-v0.1"
        target.mkdir()
        (target / "stale.txt").write_text("x", encoding="utf-8")
        try:
            rb.generate(target, rb.TEMPLATES_DIR)
            raise AssertionError("expected CleanTargetViolation")
        except rb.CleanTargetViolation:
            pass


def test_bt10_raw_corpus_not_copied() -> None:
    parsed = _parsed()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "brea-v0.1"
        rb.generate(target, rb.TEMPLATES_DIR)
        names = {path.name for path in target.rglob("*") if path.is_file()}
        assert "GB55037-2022.md" not in names
        assert "DBJ33T1021-2023.md" not in names
        for path in target.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "不应小于 50m" not in text.replace(" ", "").replace("\n", "")


def run_all() -> int:
    failures = 0
    tests = (
        test_bt01_accepted_sha_passes,
        test_bt02_wrong_sha_fails_closed,
        test_bt03_fn_set_parsed,
        test_bt04_seam_set_parsed,
        test_bt05_obligations_parsed,
        test_bt06_request_cannot_override_architecture,
        test_bt07_generated_candidate_matches_definition,
        test_bt08_obligation_refs_exist,
        test_bt09_non_empty_target_fails_closed,
        test_bt10_raw_corpus_not_copied,
    )
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    return failures
