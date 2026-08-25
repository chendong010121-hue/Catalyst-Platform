from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
NEXT_CANDIDATE = CANDIDATE_ROOT.parents[1]
KR2_PATH = NEXT_CANDIDATE / "knowledge" / "KR-002.json"
KR3_PATH = NEXT_CANDIDATE / "knowledge" / "KR-003.json"

sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.identity import BREA_FUNCTION_MAP, LINEAGE_PARENT, OBLIGATIONS, SEAM_MAP, VERSION  # noqa: E402
from brea.runner import answer, implementation_fingerprint  # noqa: E402
from knowledge_binding_support import canonical_binding, canonical_knowledge_sha  # noqa: E402


def _sha(path: Path) -> str:
    return canonical_knowledge_sha(path)


def _binding(path: Path) -> dict:
    return canonical_binding(path)


BASE_FACTS = {
    "jurisdiction": "杭州市区",
    "land_use_nature": "单一性质的城镇住宅用地（0701）",
    "planning_special_area_status": "无特殊区域另行确定指标",
}


def _run(request_id: str, question: str, facts: dict | None = None):
    return answer(
        request_id,
        question,
        facts or BASE_FACTS,
        {},
        {"organization_id": "v08-test", "user_id": "executor"},
        knowledge_binding=_binding(KR3_PATH),
    )


def _question() -> str:
    return "杭州市区单一性质城镇住宅用地（0701）住宅平均层数对应的容积率和建筑密度最大值是多少？"


class V08ResidentialSliceTests(unittest.TestCase):
    def test_p01_low_band_returns_source_backed_outputs(self):
        result = _run("P-01", _question(), {**BASE_FACTS, "residential_average_storeys": 2})
        self.assertEqual(result.status, "accepted_with_evidence")
        self.assertIn("1.2", result.conclusion)
        self.assertIn("43", result.conclusion)
        self.assertEqual(result.implementation_metadata.knowledge_revision_id, "KR-003")
        contract = result.implementation_metadata.professional_trace["professional_contract"]
        self.assertEqual(set(contract), {f"PC-{i:02d}" for i in range(1, 8)})
        self.assertTrue(all(value == "PASS" for value in contract.values()))

    def test_p02_middle_band_returns_source_backed_outputs(self):
        result = _run("P-02", _question(), {**BASE_FACTS, "residential_average_storeys": 6})
        self.assertEqual(result.status, "accepted_with_evidence")
        self.assertIn("2", result.conclusion)
        self.assertIn("35", result.conclusion)

    def test_p03_upper_band_returns_source_backed_outputs(self):
        result = _run("P-03", _question(), {**BASE_FACTS, "residential_average_storeys": 12})
        self.assertEqual(result.status, "accepted_with_evidence")
        self.assertIn("3", result.conclusion)
        self.assertIn("30", result.conclusion)

    def test_p04_missing_average_storeys_fails_closed(self):
        result = _run("P-04", _question(), BASE_FACTS)
        self.assertNotEqual(result.status, "accepted_with_evidence")
        self.assertNotRegex(result.conclusion, r"(?:1\.2|2\.0|3\.0|43|35|30)")

    def test_p05_wrong_land_use_scope_has_no_project_result(self):
        result = _run("P-05", _question(), {**BASE_FACTS, "land_use_nature": "混合性质用地"})
        self.assertNotEqual(result.status, "accepted_with_evidence")

    def test_p06_special_area_unknown_or_override_fails_closed(self):
        for status in ("未知", "特殊区域另行确定指标"):
            result = _run("P-06", _question(), {**BASE_FACTS, "planning_special_area_status": status})
            self.assertNotEqual(result.status, "accepted_with_evidence")

    def test_p07_out_of_range_storeys_do_not_extrapolate(self):
        for storeys in (0, 27):
            result = _run("P-07", _question(), {**BASE_FACTS, "residential_average_storeys": storeys})
            self.assertNotEqual(result.status, "accepted_with_evidence")
            self.assertNotRegex(result.conclusion, r"(?:1\.2|2\.0|3\.0|43|35|30)")

    def test_p08_native_table_row_and_height_note_are_evidence_bound(self):
        result = _run("P-08", _question(), {**BASE_FACTS, "residential_average_storeys": 6})
        content = "\n".join(item.evidence_content for item in result.evidence_items)
        locators = "\n".join(item.locator for item in result.evidence_items)
        self.assertIn("表（2-3）", locators)
        self.assertIn("（4—9层）", content)
        self.assertIn("2.0", content)
        self.assertIn("35%", content)
        self.assertIn("住宅建筑高度不大于", content)
        self.assertIn("未据此判定完整项目合规性", result.conclusion)
        full = _run(
            "P-08-full-compliance",
            "杭州市区单一性质城镇住宅用地（0701）住宅平均层数对应的指标并判断住宅建筑高度完整项目合规性",
            {**BASE_FACTS, "residential_average_storeys": 6},
        )
        self.assertNotEqual(full.status, "accepted_with_evidence")

    def test_p09_paraphrase_resolves_same_generic_route(self):
        result = _run(
            "P-09",
            "杭州市区0701单一性质住宅用地，平均层数为6层时，容量控制上限如何取？",
            {**BASE_FACTS, "residential_average_storeys": 6},
        )
        self.assertEqual(result.status, "accepted_with_evidence")
        self.assertIn("2", result.conclusion)
        self.assertIn("35", result.conclusion)

    def test_kr003_inherits_kr002_and_adds_only_bounded_declaration(self):
        kr2 = json.loads(KR2_PATH.read_text(encoding="utf-8"))
        kr3 = json.loads(KR3_PATH.read_text(encoding="utf-8"))
        self.assertEqual(kr3["knowledge_revision_id"], "KR-003")
        self.assertEqual(kr3["sources"], kr2["sources"])
        self.assertEqual(kr3["standards"], kr2["standards"])
        self.assertEqual(kr3["routes"][: len(kr2["routes"])], kr2["routes"])
        self.assertEqual(kr3["fact_descriptors"].keys() - kr2["fact_descriptors"].keys(), {
            "land_use_nature", "residential_average_storeys", "planning_special_area_status",
        })
        self.assertEqual(len(kr3["routes"]), len(kr2["routes"]) + 1)
        route = kr3["routes"][-1]
        self.assertEqual(route["kind"], "numeric_banded_table")
        self.assertEqual(route["table_caption"].split("城镇")[0], "表（2-3）")
        self.assertNotIn("表（3-2）", json.dumps(route, ensure_ascii=False))

    def test_numeric_fact_and_invalid_numeric_fail_closed(self):
        invalid = _run("P-04-invalid", _question(), {**BASE_FACTS, "residential_average_storeys": "6"})
        self.assertNotEqual(invalid.status, "accepted_with_evidence")

    def test_identity_regression_and_anti_hardcode(self):
        self.assertEqual(VERSION, "v0.9-candidate")
        self.assertEqual(LINEAGE_PARENT, "case-01.brea@0.8-candidate")
        self.assertEqual(set(BREA_FUNCTION_MAP), {f"FN-{i:02d}" for i in range(1, 12)})
        self.assertEqual(set(SEAM_MAP), {"SEAM-01", "SEAM-02", "SEAM-03"})
        self.assertEqual(set(OBLIGATIONS), {f"OBL-{i:02d}" for i in range(1, 7)})
        self.assertRegex(implementation_fingerprint(), r"^[0-9a-f]{64}$")
        source = "\n".join(path.read_text(encoding="utf-8") for path in (CANDIDATE_ROOT / "brea").glob("*.py"))
        forbidden = (
            "CORPUS-03", "HZ-PLANNING-TECH-2026", "表（2-3）", "表（3-2）",
            "容积率", "建筑密度", "1.2", "43%", "2.0", "35%", "3.0", "30%",
            "80米", "residential_far_density",
        )
        self.assertFalse(any(token in source for token in forbidden))
        self.assertNotIn("road_width_m", source)
        self.assertNotIn("Q semantics", source)


if __name__ == "__main__":
    unittest.main()
