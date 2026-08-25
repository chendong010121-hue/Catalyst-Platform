from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
NEXT_CANDIDATE = HERE.parent
CANDIDATE_ROOT = NEXT_CANDIDATE / "candidate" / "brea-v0.8"
KR3_PATH = NEXT_CANDIDATE / "knowledge" / "KR-003.json"
REPO_ROOT = Path(__file__).resolve().parents[5]
CANDIDATE_REPO_PATH = (
    "case-01/01-e-governed-agent-professional-completion/"
    "e2-local-professional-coverage-expansion/next-candidate/candidate/brea-v0.8"
)
KNOWLEDGE_REPO_PATH = CANDIDATE_REPO_PATH + "/brea/knowledge.py"

if str(CANDIDATE_ROOT) not in sys.path:
    sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.corpus import Corpus, CorpusIntegrityError  # noqa: E402
from brea.knowledge import KnowledgeBindingError, load_knowledge_binding  # noqa: E402


def _reject_non_standard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def _strict_loads(text: str) -> Any:
    return json.loads(text, parse_constant=_reject_non_standard_constant)


def _read_original() -> dict[str, Any]:
    document = _strict_loads(KR3_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise AssertionError("KR-003 must be a JSON object")
    return document


def _identity_projection(document: dict[str, Any]) -> dict[str, Any]:
    projection = copy.deepcopy(document)
    sources = projection.get("sources")
    if not isinstance(sources, list):
        raise ValueError("sources must be a list")
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("each source record must be an object")
        source.pop("local_reference", None)
    return projection


def _oracle_sha(document: dict[str, Any]) -> str:
    projection = _identity_projection(document)
    payload = json.dumps(
        projection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _binding(path: Path, sha256: str, *, revision_id: str = "KR-003") -> dict[str, str]:
    return {"revision_id": revision_id, "path": str(path), "sha256": sha256}


def _write_text(path: Path, text: str, *, newline_bytes: bool = False) -> None:
    if newline_bytes:
        path.write_bytes(text.encode("utf-8"))
    else:
        path.write_text(text, encoding="utf-8", newline="")


def _reverse_object_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _reverse_object_keys(value[key]) for key in reversed(list(value.keys()))}
    if isinstance(value, list):
        return [_reverse_object_keys(item) for item in value]
    return value


def _load(path: Path, sha256: str, *, revision_id: str = "KR-003") -> tuple[dict, dict]:
    return load_knowledge_binding(_binding(path, sha256, revision_id=revision_id))


class KnowledgeHashHardeningContract(unittest.TestCase):
    def setUp(self) -> None:
        self.original = _read_original()
        self.expected_sha = _oracle_sha(self.original)

    def test_h01_indentation_is_identity_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compact = root / "compact.json"
            pretty = root / "pretty.json"
            _write_text(compact, json.dumps(self.original, ensure_ascii=False, separators=(",", ":")))
            _write_text(pretty, json.dumps(self.original, ensure_ascii=False, indent=4) + "\n")
            for path in (compact, pretty):
                knowledge, metadata = _load(path, self.expected_sha)
                self.assertEqual(knowledge, self.original)
                self.assertEqual(metadata["sha256"], self.expected_sha)

    def test_h02_object_key_order_is_identity_stable(self):
        reordered = _reverse_object_keys(self.original)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reordered.json"
            _write_text(path, json.dumps(reordered, ensure_ascii=False, indent=2) + "\n")
            knowledge, metadata = _load(path, self.expected_sha)
            self.assertEqual(knowledge, self.original)
            self.assertEqual(metadata["sha256"], self.expected_sha)

    def test_h03_line_endings_are_identity_stable(self):
        text = json.dumps(self.original, ensure_ascii=False, indent=2) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lf = root / "lf.json"
            crlf = root / "crlf.json"
            _write_text(lf, text, newline_bytes=True)
            _write_text(crlf, text.replace("\n", "\r\n"), newline_bytes=True)
            for path in (lf, crlf):
                knowledge, metadata = _load(path, self.expected_sha)
                self.assertEqual(knowledge, self.original)
                self.assertEqual(metadata["sha256"], self.expected_sha)

    def test_h04_local_reference_is_not_knowledge_identity(self):
        variant = copy.deepcopy(self.original)
        for index, source in enumerate(variant["sources"], start=1):
            source["local_reference"] = f"Z:/machine-b/corpus-{index}.txt"
        self.assertEqual(_oracle_sha(variant), self.expected_sha)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local-reference-variant.json"
            _write_text(path, json.dumps(variant, ensure_ascii=False, indent=2) + "\n")
            knowledge, metadata = _load(path, self.expected_sha)
            self.assertEqual(knowledge, variant)
            self.assertEqual(metadata["sha256"], self.expected_sha)

    def test_h05_source_sha_is_knowledge_identity(self):
        variant = copy.deepcopy(self.original)
        variant["sources"][0]["sha256"] = "0" * 64
        changed_sha = _oracle_sha(variant)
        self.assertNotEqual(changed_sha, self.expected_sha)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source-sha-change.json"
            _write_text(path, json.dumps(variant, ensure_ascii=False, indent=2) + "\n")
            with self.assertRaises(KnowledgeBindingError):
                _load(path, self.expected_sha)
            knowledge, metadata = _load(path, changed_sha)
            self.assertEqual(knowledge, variant)
            self.assertEqual(metadata["sha256"], changed_sha)

    def test_h06_route_and_fact_changes_change_identity(self):
        mutations: list[dict[str, Any]] = []
        route_variant = copy.deepcopy(self.original)
        route_variant["routes"][0]["subject"] = route_variant["routes"][0]["subject"] + " changed"
        mutations.append(route_variant)
        fact_variant = copy.deepcopy(self.original)
        fact_variant["fact_descriptors"]["residential_average_storeys"]["description"] += " changed"
        mutations.append(fact_variant)
        for index, variant in enumerate(mutations, start=1):
            changed_sha = _oracle_sha(variant)
            self.assertNotEqual(changed_sha, self.expected_sha)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / f"knowledge-change-{index}.json"
                _write_text(path, json.dumps(variant, ensure_ascii=False, indent=2) + "\n")
                with self.assertRaises(KnowledgeBindingError):
                    _load(path, self.expected_sha)
                knowledge, metadata = _load(path, changed_sha)
                self.assertEqual(knowledge, variant)
                self.assertEqual(metadata["sha256"], changed_sha)

    def test_h07_original_canonical_binding_is_accepted(self):
        knowledge, metadata = _load(KR3_PATH, self.expected_sha)
        self.assertEqual(knowledge, self.original)
        self.assertEqual(metadata, {"revision_id": "KR-003", "sha256": self.expected_sha})

    def test_h08_wrong_expected_canonical_sha_fails_closed(self):
        with self.assertRaises(KnowledgeBindingError):
            _load(KR3_PATH, "f" * 64)

    def test_h09_malformed_identity_mismatch_and_non_standard_numbers_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            malformed = root / "malformed.json"
            malformed_bytes = b'{"knowledge_revision_id": "KR-003",'
            malformed.write_bytes(malformed_bytes)
            malformed_raw_sha = hashlib.sha256(malformed_bytes).hexdigest()
            with self.assertRaises(KnowledgeBindingError):
                _load(malformed, malformed_raw_sha)

            with self.assertRaises(KnowledgeBindingError):
                _load(KR3_PATH, self.expected_sha, revision_id="KR-999")

            original_text = KR3_PATH.read_text(encoding="utf-8")
            non_standard = root / "non-standard-number.json"
            injected = original_text.replace("{", '{"non_standard_number": NaN,', 1)
            non_standard_bytes = injected.encode("utf-8")
            non_standard.write_bytes(non_standard_bytes)
            raw_sha = hashlib.sha256(non_standard_bytes).hexdigest()
            with self.assertRaises(KnowledgeBindingError):
                _load(non_standard, raw_sha)

    def test_h10_source_content_sha_verification_remains_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.txt"
            path.write_bytes(b"tampered source bytes")
            expected_sha = hashlib.sha256(b"different authoritative bytes").hexdigest()
            with self.assertRaises(CorpusIntegrityError):
                Corpus("TEST-CORPUS", "source.txt", str(path), expected_sha)

    def test_h11_relevant_v08_regression_boundary_is_preserved(self):
        base_sha = os.environ.get("CATALYST_TRIAL_BASE_SHA")
        self.assertTrue(base_sha, "CATALYST_TRIAL_BASE_SHA is required by the frozen verifier")
        changed = subprocess.run(
            ["git", "diff", "--name-only", base_sha, "--", CANDIDATE_REPO_PATH],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        normalized = [path.replace("\\", "/") for path in changed if path.strip()]
        self.assertEqual(normalized, [KNOWLEDGE_REPO_PATH])

        knowledge, metadata = _load(KR3_PATH, self.expected_sha)
        self.assertEqual(knowledge, self.original)
        self.assertEqual(knowledge["knowledge_revision_id"], "KR-003")
        self.assertEqual(metadata["sha256"], self.expected_sha)


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(KnowledgeHashHardeningContract)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {
        "contract": "CASE_01_HARNESS_TRIAL_01_KNOWLEDGE_HASH_HARDENING_V0.1",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "status": "PASS" if result.wasSuccessful() else "FAIL",
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
