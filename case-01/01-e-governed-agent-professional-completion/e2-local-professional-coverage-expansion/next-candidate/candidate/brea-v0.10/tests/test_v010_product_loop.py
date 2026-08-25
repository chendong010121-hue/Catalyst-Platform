from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
NEXT_CANDIDATE = CANDIDATE_ROOT.parents[1]
KR3_PATH = NEXT_CANDIDATE / "knowledge" / "KR-003.json"
sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.runner import answer  # noqa: E402
from brea.applicability import applicability_for_question  # noqa: E402
from brea.corpus import load_corpora  # noqa: E402
from knowledge_binding_support import canonical_binding  # noqa: E402


def _binding() -> dict[str, str]:
    return canonical_binding(KR3_PATH)


def _run(request_id: str, question: str, facts: dict, regulation: dict | None = None):
    return answer(
        request_id,
        question,
        facts,
        regulation or {},
        {"organization_id": "v010-test", "user_id": "executor", "project_id": "product-loop"},
        knowledge_binding=_binding(),
    )


class V010ProductLoopTests(unittest.TestCase):
    def test_professional_outcome_outranks_incidental_evidence_words(self):
        result = _run(
            "V010-FIRE-PRECEDENCE",
            "公共建筑按一级耐火等级且全设自动灭火系统时，一个防火分区最多能做到多大？请把依据条款一起说明。",
            {
                "building_category": "公共建筑",
                "building_form": "高层建筑",
                "fire_resistance_rating": "一级",
                "auto_extinguishing_system": "全部设置自动灭火系统",
            },
            {"standard_hint": "GB 55037-2022"},
        )
        self.assertEqual(result.implementation_metadata.query_mode, "QMODE-05")

    def test_retrieval_only_intent_remains_qmode03(self):
        result = _run(
            "V010-RETRIEVAL-ONLY",
            "请在 GB 55037-2022 原文中查找哪里提到人员密集场所？",
            {},
            {"standard_hint": "GB 55037-2022"},
        )
        self.assertEqual(result.implementation_metadata.query_mode, "QMODE-03")
        self.assertEqual(result.status, "evidence_retrieved")

    def test_explicit_clause_and_table_lookup_remain_retrieval_modes(self):
        clause = _run(
            "V010-RETRIEVAL-CLAUSE",
            "请给出 GB 55037-2022 第3.1.3条原文。",
            {},
            {"standard_hint": "GB55037-2022"},
        )
        table = _run(
            "V010-RETRIEVAL-TABLE",
            "请给出 DBJ33/T1021-2023 表5.0.4原文内容。",
            {},
            {"standard_hint": "DBJ33/T1021-2023"},
        )
        self.assertEqual(clause.implementation_metadata.query_mode, "QMODE-01")
        self.assertEqual(table.implementation_metadata.query_mode, "QMODE-04")

    def test_ambiguous_declarative_routes_fail_closed(self):
        knowledge = json.loads(KR3_PATH.read_text(encoding="utf-8"))
        duplicate = copy.deepcopy(next(route for route in knowledge["routes"] if route["name"] == "fire_compartment"))
        duplicate["name"] = "fire_compartment_duplicate"
        knowledge["routes"].append(duplicate)
        corpora = load_corpora(knowledge["sources"])
        chain = applicability_for_question(
            "防火分区最大允许建筑面积",
            {"building_category": "公共建筑"},
            corpora,
            knowledge,
            {"standard_hint": "GB55037-2022"},
        )
        self.assertIsNone(chain["standard_id"])
        self.assertIn("拒绝任意选择", chain["reason"][-1])

    def test_fire_complete_paraphrase_binds_source_numeric_result(self):
        result = _run(
            "V010-FIRE-COMPLETE",
            "高层公共建筑采用一级耐火等级并全部配置自动灭火系统时，单个防火分区的面积上限是多少？请说明条款依据。",
            {
                "building_category": "公共建筑",
                "building_form": "高层建筑",
                "fire_resistance_rating": "一级",
                "auto_extinguishing_system": "全部设置自动灭火系统",
            },
            {"standard_hint": "GB55037-2022"},
        )
        self.assertEqual(result.status, "accepted_with_evidence")
        self.assertEqual(result.implementation_metadata.query_mode, "QMODE-05")
        self.assertEqual(result.implementation_metadata.standard_id, "GB55037-2022")
        trace = result.implementation_metadata.professional_trace
        self.assertTrue(trace["numeric"]["source_evidence_bound"])
        self.assertTrue(any("4.3.16" in item.locator for item in result.evidence_items))
        source_operand = trace["numeric"]["source_operand"]["value"]
        self.assertTrue(any(str(int(source_operand)) in item.evidence_content for item in result.evidence_items))
        self.assertTrue(any("增加" in item.evidence_content for item in result.evidence_items))
        self.assertEqual(
            result.implementation_metadata.enterprise_context_attribution["organization_id"],
            "v010-test",
        )

    def test_fire_missing_facts_stays_professional_and_fail_closed(self):
        result = _run(
            "V010-FIRE-MISSING",
            "这个高层公共建筑的防火分区最大允许建筑面积是多少？请标明依据条款。",
            {"building_category": "公共建筑", "building_form": "高层建筑"},
            {"standard_hint": "GB55037-2022"},
        )
        self.assertEqual(result.implementation_metadata.query_mode, "QMODE-05")
        self.assertEqual(result.implementation_metadata.standard_id, "GB55037-2022")
        self.assertEqual(result.status, "insufficient_context")
        self.assertIn("耐火等级", result.conclusion)
        self.assertIn("自动灭火系统", result.conclusion)
        self.assertIsNone(re.search(r"\d", result.conclusion))

    def test_parking_complete_paraphrase_binds_source_level_and_row(self):
        result = _run(
            "V010-PARKING-COMPLETE",
            "杭州这个9000平商业综合体按浙江配建标准要配多少机动车位？把指标来源和计算过程一起说明。",
            {
                "jurisdiction": "浙江省·杭州市",
                "building_category": "商业综合体",
                "floor_area_m2": 9000,
                "city_class": "规划人口大于20万人、不大于50万人的城市",
            },
            {"standard_hint": "DBJ33/T1021-2023"},
        )
        self.assertEqual(result.status, "accepted_with_evidence")
        self.assertEqual(result.implementation_metadata.query_mode, "QMODE-05")
        self.assertEqual(result.implementation_metadata.standard_id, "DBJ33T1021-2023")
        trace = result.implementation_metadata.professional_trace
        self.assertTrue(trace["numeric"])
        self.assertTrue(trace["numeric"]["source_evidence_bound"])
        self.assertTrue(trace["table"]["selected_column"])
        self.assertTrue(trace["table"]["row_label"])
        self.assertTrue(any(trace["table"]["source_level_label"] in item.evidence_content for item in result.evidence_items))
        self.assertTrue(any(trace["table"]["row_label"] in item.locator for item in result.evidence_items))
        self.assertTrue(all(item.locator for item in result.evidence_items))

    def test_out_of_jurisdiction_residential_remains_fail_closed(self):
        result = _run(
            "V010-RESIDENTIAL-SAFETY",
            "宁波市区住宅用地的容积率和建筑密度控制上限是多少？",
            {
                "jurisdiction": "宁波市区",
                "land_use_nature": "单一性质的城镇住宅用地（0701）",
                "residential_average_storeys": 6,
                "planning_special_area_status": "无特殊区域另行确定指标",
            },
        )
        self.assertEqual(result.status, "insufficient_context")
        self.assertNotRegex(result.conclusion, r"\d")

    def test_unavailable_web_source_remains_fail_closed(self):
        result = _run(
            "V010-WEB-SAFETY",
            "请联网查找 KR-003 没有收录的最新地方停车规范并给出机动车位指标。",
            {"jurisdiction": "浙江省·杭州市", "building_category": "商业综合体", "floor_area_m2": 9000},
            {"standard_hint": "未在 KR-003 绑定范围内的现行规范"},
        )
        self.assertEqual(result.status, "no_reliable_evidence")
        self.assertNotRegex(result.conclusion, r"访问网页|联网成功|已检索网络|上游规范服务")


if __name__ == "__main__":
    unittest.main()
