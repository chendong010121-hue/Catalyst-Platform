from __future__ import annotations

import copy
import json
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path

CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
NEXT_CANDIDATE = CANDIDATE_ROOT.parents[1]
KR3_PATH = NEXT_CANDIDATE / "knowledge" / "KR-003.json"

import sys

sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.corpus import Corpus, CorpusIntegrityError  # noqa: E402
from brea.knowledge import KnowledgeBindingError, load_knowledge_binding  # noqa: E402
from knowledge_binding_support import (  # noqa: E402
    canonical_binding,
    canonical_knowledge_sha,
    load_revision,
    raw_file_sha,
)


def _write_json(path: Path, value: dict, *, indent: int | None = 2, newline: str = "\n") -> None:
    text = json.dumps(value, ensure_ascii=False, indent=indent)
    path.write_bytes((text + newline).encode("utf-8"))


def _reverse_keys(value):
    if isinstance(value, dict):
        return OrderedDict((key, _reverse_keys(value[key])) for key in reversed(list(value)))
    if isinstance(value, list):
        return [_reverse_keys(item) for item in value]
    return value


class V09KnowledgeIdentityTests(unittest.TestCase):
    def test_v9_h01_indentation_and_whitespace_are_stable(self):
        document = load_revision(KR3_PATH)
        with tempfile.TemporaryDirectory() as temp:
            compact = Path(temp) / "compact.json"
            formatted = Path(temp) / "formatted.json"
            _write_json(compact, document, indent=None)
            _write_json(formatted, document, indent=4)
            self.assertEqual(canonical_knowledge_sha(compact), canonical_knowledge_sha(formatted))

    def test_v9_h02_object_key_order_is_stable(self):
        document = _reverse_keys(load_revision(KR3_PATH))
        with tempfile.TemporaryDirectory() as temp:
            variant = Path(temp) / "reordered.json"
            _write_json(variant, document)
            self.assertEqual(canonical_knowledge_sha(KR3_PATH), canonical_knowledge_sha(variant))

    def test_v9_h03_lf_and_crlf_are_stable(self):
        document = load_revision(KR3_PATH)
        with tempfile.TemporaryDirectory() as temp:
            lf = Path(temp) / "lf.json"
            crlf = Path(temp) / "crlf.json"
            _write_json(lf, document, newline="\n")
            _write_json(crlf, document, newline="\r\n")
            self.assertEqual(canonical_knowledge_sha(lf), canonical_knowledge_sha(crlf))

    def test_v9_h04_local_reference_only_relocation_is_stable(self):
        document = copy.deepcopy(load_revision(KR3_PATH))
        for index, source in enumerate(document["sources"]):
            source["local_reference"] = f"C:/machine-{index}/same-sha-source"
        with tempfile.TemporaryDirectory() as temp:
            relocated = Path(temp) / "relocated.json"
            _write_json(relocated, document)
            self.assertEqual(canonical_knowledge_sha(KR3_PATH), canonical_knowledge_sha(relocated))

    def test_v9_h05_source_sha_change_changes_identity(self):
        document = copy.deepcopy(load_revision(KR3_PATH))
        document["sources"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / "changed.json"
            _write_json(changed, document)
            self.assertNotEqual(canonical_knowledge_sha(KR3_PATH), canonical_knowledge_sha(changed))

    def test_v9_h06_route_change_changes_identity(self):
        document = copy.deepcopy(load_revision(KR3_PATH))
        document["routes"][0]["kind"] = document["routes"][0].get("kind", "") + "-changed"
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / "changed.json"
            _write_json(changed, document)
            self.assertNotEqual(canonical_knowledge_sha(KR3_PATH), canonical_knowledge_sha(changed))

    def test_v9_h07_canonical_kr003_binding_is_accepted(self):
        knowledge, metadata = load_knowledge_binding(canonical_binding(KR3_PATH))
        self.assertEqual(knowledge["knowledge_revision_id"], "KR-003")
        self.assertEqual(metadata["sha256"], canonical_knowledge_sha(KR3_PATH))

    def test_v9_h08_historical_raw_byte_sha_is_rejected(self):
        self.assertNotEqual(raw_file_sha(KR3_PATH), canonical_knowledge_sha(KR3_PATH))
        with self.assertRaises(KnowledgeBindingError):
            load_knowledge_binding(
                {
                    "revision_id": "KR-003",
                    "path": str(KR3_PATH),
                    "sha256": raw_file_sha(KR3_PATH),
                }
            )

    def test_v9_h09_malformed_identity_mismatch_nan_and_infinity_fail_closed(self):
        document = load_revision(KR3_PATH)
        with tempfile.TemporaryDirectory() as temp:
            malformed = Path(temp) / "malformed.json"
            malformed.write_text("{not-json", encoding="utf-8")
            mismatch = Path(temp) / "mismatch.json"
            mismatch_document = copy.deepcopy(document)
            mismatch_document["knowledge_revision_id"] = "KR-003-mismatch"
            _write_json(mismatch, mismatch_document)
            for name, raw in (("nan.json", "NaN"), ("infinity.json", "Infinity")):
                numeric = Path(temp) / name
                numeric.write_text(
                    '{"knowledge_revision_id":"KR-003","sources":[],"standards":[],"routes":[],"fact_descriptors":{},"value":'
                    + raw
                    + "}",
                    encoding="utf-8",
                )
            for path in (malformed, mismatch, Path(temp) / "nan.json", Path(temp) / "infinity.json"):
                with self.assertRaises(KnowledgeBindingError):
                    load_knowledge_binding({"revision_id": "KR-003", "path": str(path), "sha256": "0" * 64})

    def test_v9_h10_source_content_sha_integrity_remains_independent(self):
        source = load_revision(KR3_PATH)["sources"][0]
        with self.assertRaises(CorpusIntegrityError):
            Corpus(source["source_id"], source["file_name"], source["local_reference"], "0" * 64)


if __name__ == "__main__":
    unittest.main()
