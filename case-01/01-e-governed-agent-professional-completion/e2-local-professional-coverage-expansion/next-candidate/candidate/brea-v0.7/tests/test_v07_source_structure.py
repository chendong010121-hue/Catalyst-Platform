from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
NEXT_CANDIDATE = CANDIDATE_ROOT.parents[1]
REPO_ROOT = CANDIDATE_ROOT.parents[5]
KR1_PATH = NEXT_CANDIDATE / "knowledge" / "KR-001.json"
KR2_PATH = NEXT_CANDIDATE / "knowledge" / "KR-002.json"
FIXTURES = CANDIDATE_ROOT / "tests" / "fixtures" / "requests"

sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.identity import BREA_FUNCTION_MAP, LINEAGE_PARENT, OBLIGATIONS, SEAM_MAP, VERSION  # noqa: E402
from brea.runner import answer, implementation_fingerprint  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(path: Path) -> dict:
    revision = json.loads(path.read_text(encoding="utf-8"))
    return {"revision_id": revision["knowledge_revision_id"], "path": str(path), "sha256": _sha(path)}


def _run(request_id: str, question: str, binding: dict):
    return answer(
        request_id,
        question,
        {},
        {},
        {"organization_id": "v07-test", "user_id": "executor"},
        knowledge_binding=binding,
    )


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["request"]


class V07SourceStructureTests(unittest.TestCase):
    def test_s01_effective_date_is_retrievable_with_native_section_locator(self):
        result = _run("S-01", "HZ-PLANNING-TECH-2026 施行日期原文内容", _binding(KR2_PATH))
        self.assertEqual(result.status, "evidence_retrieved")
        self.assertTrue(any("2026" in item.evidence_content and "施行" in item.evidence_content for item in result.evidence_items))
        self.assertTrue(any("六、附则" in item.locator for item in result.evidence_items))
        self.assertTrue(all("第6.1.1条" not in item.locator for item in result.evidence_items))

    def test_s02_wall_height_is_retrieved_verbatim(self):
        result = _run("S-02", "HZ-PLANNING-TECH-2026 围墙高度原文内容", _binding(KR2_PATH))
        self.assertEqual(result.status, "evidence_retrieved")
        self.assertTrue(any("2.2米" in item.evidence_content for item in result.evidence_items))
        self.assertTrue(all("第" not in item.locator for item in result.evidence_items))

    def test_s03_underground_connection_values_are_retrieved_verbatim(self):
        result = _run("S-03", "HZ-PLANNING-TECH-2026 地下步行连通道净宽净高原文内容", _binding(KR2_PATH))
        self.assertEqual(result.status, "evidence_retrieved")
        content = "\n".join(item.evidence_content for item in result.evidence_items)
        self.assertIn("4米", content)
        self.assertIn("2.5米", content)

    def test_s04_parenthesized_table_returns_native_caption_and_values(self):
        result = _run("S-04", "HZ-PLANNING-TECH-2026 表（2-3）城镇住宅用地容积率建筑密度原文内容", _binding(KR2_PATH))
        self.assertEqual(result.status, "evidence_retrieved")
        content = "\n".join(item.evidence_content for item in result.evidence_items)
        self.assertIn("表（2-3）", content)
        self.assertIn("1.2", content)
        self.assertIn("43%", content)
        self.assertTrue(any("表（2-3）" in item.locator for item in result.evidence_items))
        self.assertTrue(all("表2.3" not in item.locator for item in result.evidence_items))

    def test_s05_parenthesized_table_locator_is_explicitly_resolved(self):
        result = _run("S-05", "HZ-PLANNING-TECH-2026 表（2-3）原文", _binding(KR2_PATH))
        self.assertEqual(result.status, "evidence_retrieved")
        self.assertEqual(result.implementation_metadata.query_mode, "QMODE-04")
        self.assertTrue(any("表（2-3）" in item.locator for item in result.evidence_items))

    def test_generic_source_native_structure_grammar(self):
        from brea.corpus import evidence_units, load_corpora

        revision = json.loads(KR2_PATH.read_text(encoding="utf-8"))
        corpus = load_corpora(revision["sources"])["CORPUS-03"]
        locators = "\n".join(unit["source_locator"] for unit in evidence_units(corpus))
        for native_locator in ("六、附则", "（一）", "1.", "（1）", "表（2-3）", "表（3-2）"):
            self.assertIn(native_locator, locators)
        self.assertNotIn("第6.1.1条", locators)
        self.assertNotIn("表2.3", locators)

    def test_legacy_clause_table_and_e1_regressions(self):
        kr1 = _binding(KR1_PATH)
        clause = _run("R-01", "GB55037-2022 第3.1.3条怎么规定？", kr1)
        table = _run("R-02", "DBJ33T1021-2023 表5.0.4原文内容", kr1)
        topic = _run("R-03", "GB55037 里哪里提到人员密集场所？", kr1)
        self.assertEqual(clause.status, "evidence_retrieved")
        self.assertTrue(any("第3.1.3条" in item.locator for item in clause.evidence_items))
        self.assertEqual(table.status, "evidence_retrieved")
        self.assertTrue(any("表5.0.4" in item.locator for item in table.evidence_items))
        self.assertEqual(topic.status, "evidence_retrieved")

    def test_professional_and_binding_regressions(self):
        for name, expected in (("T-C01", "accepted_with_evidence"), ("T-C02", "accepted_with_evidence"), ("T-C03", "insufficient_context")):
            request = _fixture(name)
            result = answer(
                request["request_id"], request["question"], request.get("project_context", {}),
                request.get("regulation_context", {}), request["enterprise_context"],
                knowledge_binding=_binding(KR1_PATH),
            )
            self.assertEqual(result.status, expected)
            self.assertEqual(result.implementation_metadata.knowledge_revision_id, "KR-001")

        result = _run("R-06", "HZ-PLANNING-TECH-2026 施行日期原文内容", _binding(KR2_PATH))
        self.assertEqual(result.implementation_metadata.knowledge_revision_id, "KR-002")
        self.assertEqual(result.implementation_metadata.knowledge_revision_sha256, _sha(KR2_PATH))

    def test_identity_boundaries_and_anti_hardcode(self):
        self.assertEqual(VERSION, "v0.7-candidate")
        self.assertEqual(LINEAGE_PARENT, "case-01.brea@0.6-candidate")
        self.assertEqual(set(BREA_FUNCTION_MAP), {f"FN-{i:02d}" for i in range(1, 12)})
        self.assertEqual(set(SEAM_MAP), {"SEAM-01", "SEAM-02", "SEAM-03"})
        self.assertEqual(set(OBLIGATIONS), {f"OBL-{i:02d}" for i in range(1, 7)})
        self.assertRegex(implementation_fingerprint(), r"^[0-9a-f]{64}$")
        source = "\n".join(path.read_text(encoding="utf-8") for path in (CANDIDATE_ROOT / "brea").glob("*.py"))
        forbidden = ("CORPUS-03", "HZ-PLANNING-TECH-2026", "杭州市城市规划管理技术规定", "围墙", "地下步行", "容积率", "建筑密度", "道路宽度", "2.2米", "4米", "2.5米", "表（2-3）", "表（3-2）")
        self.assertFalse(any(token in source for token in forbidden))
        self.assertNotIn("professional_data.json", source)
        self.assertFalse((CANDIDATE_ROOT / "brea" / "professional_data.json").exists())

    def test_platform_bound_compatibility(self):
        sys.path.insert(0, str(REPO_ROOT))
        from agent_runtime.contracts import CapabilityDescriptor as RuntimeDescriptor, Success
        from examples.platform_standard_reference import reference_runtime_factory
        from platform_standard.models import CapabilityDescriptor, Invocation
        from platform_standard.registry import InMemoryDescriptorRegistry
        from platform_standard.runtime_adapter import RuntimeAdapter

        class CandidateCapability:
            def describe(self):
                return RuntimeDescriptor(id="case_01_brea_execute", name="BREA Execute", description="routing",
                                         input_schema={"type": "object"}, output_schema={"type": "object"})

            def invoke(self, parameters, context):
                request = _fixture("T-C02")
                result = answer(request["request_id"], request["question"], request["project_context"],
                                request["regulation_context"], request["enterprise_context"],
                                knowledge_binding=_binding(KR1_PATH))
                return Success(result.to_dict())

        registry = InMemoryDescriptorRegistry()
        registry.register(CapabilityDescriptor(
            id="case-01.brea.execute", name="BREA Execute", description="routing",
            capability_version="0.1", input_schema={"type": "object"}, output_schema={"type": "object"},
            execution={"side_effect": "none"},
        ))
        adapter = RuntimeAdapter(
            registry, bindings={("case-01.brea.execute", "0.1"): CandidateCapability()},
            runtime_factory=reference_runtime_factory,
        )
        result = adapter.execute(Invocation(
            id="r10", capability_id="case-01.brea.execute", capability_version="0.1",
            input=_fixture("T-C02"), context={"extensions": {}}, trace_id="r10-trace",
        ))
        self.assertEqual(result.status, "success")
        self.assertEqual((result.output or {}).get("status"), "accepted_with_evidence")


if __name__ == "__main__":
    unittest.main()
