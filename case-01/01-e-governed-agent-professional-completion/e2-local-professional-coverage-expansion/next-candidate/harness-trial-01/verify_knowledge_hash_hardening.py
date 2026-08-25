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
FIXTURE_REQUESTS = CANDIDATE_ROOT / "tests" / "fixtures" / "requests"
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
from brea.runner import answer  # noqa: E402


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
    payload = json.dumps(
        _identity_projection(document),
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


def _answer(request_id: str, question: str, project_context: dict[str, Any], expected_sha: str):
    return answer(
        request_id,
        question,
        project_context,
        {},
        {"organization_id": "trial-01", "user_id": "governance-verifier"},
        knowledge_binding=_binding(KR3_PATH, expected_sha),
    )


def _fixture_request(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_REQUESTS / f"{name}.json").read_text(encoding="utf-8"))["request"]


BASE_FACTS = {
    "jurisdiction": "杭州市区",
    "land_use_nature": "单一性质的城镇住宅用地（0701）",
    "planning_special_area_status": "无特殊区域另行确定指标",
}

RESIDENTIAL_QUESTION = "杭州市区单一性质城镇住宅用地（0701）住宅平均层数对应的容积率和建筑密度最大值是多少？"


class KnowledgeHashHardeningContract(unittest.TestCase):
    def setUp(self) -> None:
        self.original = _read_original()
        self.expected_sha = _oracle_sha(self.original)

    def test_h01_indentation_is_identity_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            variants = (
                (root / "compact.json", json.dumps(self.original, ensure_ascii=False, separators=(",", ":"))),
                (root / "pretty.json", json.dumps(self.original, ensure_ascii=False, indent=4) + "\n"),
            )
            for path, text in variants:
                _write_text(path, text)
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
            variants = ((root / "lf.json", text), (root / "crlf.json", text.replace("\n", "\r\n")))
            for path, serialized in variants:
                _write_text(path, serialized, newline_bytes=True)
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
        route_variant = copy.deepcopy(self.original)
        route_variant["routes"][0]["subject"] += " changed"
        fact_variant = copy.deepcopy(self.original)
        fact_variant["fact_descriptors"]["residential_average_storeys"]["description"] += " changed"
        for index, variant in enumerate((route_variant, fact_variant), start=1):
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
            with self.assertRaises(KnowledgeBindingError):
                _load(malformed, hashlib.sha256(malformed_bytes).hexdigest())

            with self.assertRaises(KnowledgeBindingError):
                _load(KR3_PATH, self.expected_sha, revision_id="KR-999")

            non_standard = root / "non-standard-number.json"
            injected = KR3_PATH.read_text(encoding="utf-8").replace("{", '{"non_standard_number": NaN,', 1)
            non_standard_bytes = injected.encode("utf-8")
            non_standard.write_bytes(non_standard_bytes)
            with self.assertRaises(KnowledgeBindingError):
                _load(non_standard, hashlib.sha256(non_standard_bytes).hexdigest())

    def test_h10_source_content_sha_verification_remains_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.txt"
            path.write_bytes(b"tampered source bytes")
            expected_sha = hashlib.sha256(b"different authoritative bytes").hexdigest()
            with self.assertRaises(CorpusIntegrityError):
                Corpus("TEST-CORPUS", "source.txt", str(path), expected_sha)

    def test_h11_candidate_diff_and_representative_v08_behavior_are_preserved(self):
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

        # Representative positive residential bands remain source-backed.
        expected = ((2, "1.2", "43"), (6, "2", "35"), (12, "3", "30"))
        for storeys, far_token, density_token in expected:
            result = _answer(
                f"H11-P-{storeys}",
                RESIDENTIAL_QUESTION,
                {**BASE_FACTS, "residential_average_storeys": storeys},
                self.expected_sha,
            )
            self.assertEqual(result.status, "accepted_with_evidence")
            self.assertIn(far_token, result.conclusion)
            self.assertIn(density_token, result.conclusion)
            self.assertEqual(result.implementation_metadata.knowledge_revision_sha256, self.expected_sha)

        # Representative fail-closed boundaries remain fail-closed.
        missing_selector = _answer("H11-MISSING", RESIDENTIAL_QUESTION, BASE_FACTS, self.expected_sha)
        wrong_scope = _answer(
            "H11-WRONG-SCOPE",
            RESIDENTIAL_QUESTION,
            {**BASE_FACTS, "land_use_nature": "混合性质用地", "residential_average_storeys": 6},
            self.expected_sha,
        )
        self.assertNotEqual(missing_selector.status, "accepted_with_evidence")
        self.assertNotEqual(wrong_scope.status, "accepted_with_evidence")

        # Existing T-C01 / T-C02 / T-C03 professional paths remain representative regressions.
        expected_status = {
            "T-C01": "accepted_with_evidence",
            "T-C02": "accepted_with_evidence",
            "T-C03": "insufficient_context",
        }
        for name, status in expected_status.items():
            request = _fixture_request(name)
            result = answer(
                request["request_id"],
                request["question"],
                request.get("project_context", {}),
                request.get("regulation_context", {}),
                request["enterprise_context"],
                knowledge_binding=_binding(KR3_PATH, self.expected_sha),
            )
            self.assertEqual(result.status, status)
            self.assertEqual(result.implementation_metadata.knowledge_revision_sha256, self.expected_sha)


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
