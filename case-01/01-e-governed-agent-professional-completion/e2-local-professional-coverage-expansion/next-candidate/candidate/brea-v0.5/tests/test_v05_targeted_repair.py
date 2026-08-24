from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CANDIDATE_ROOT.parents[5]
sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.applicability import applicability_for_question  # noqa: E402
from brea.domain_data import fact_descriptors, routes  # noqa: E402
from brea.identity import (  # noqa: E402
    BREA_FUNCTION_MAP,
    LINEAGE_PARENT,
    OBLIGATIONS,
    SEAM_MAP,
    VERSION,
)
from brea.runner import answer, implementation_fingerprint  # noqa: E402
from brea.semantic import derive_semantic_view  # noqa: E402


FIXTURES = CANDIDATE_ROOT / "tests" / "fixtures" / "requests"


def _request(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["request"]


def _run(request: dict):
    return answer(
        request["request_id"], request["question"], request.get("project_context", {}),
        request.get("regulation_context", {}), request["enterprise_context"],
    )


def _fire(request_id: str, category: str, form: str, rating: str, system: str):
    return _run({
        "request_id": request_id,
        "question": "某项目每个防火分区的最大允许建筑面积应为多少？",
        "project_context": {
            "building_category": category,
            "building_form": form,
            "fire_resistance_rating": rating,
            "auto_extinguishing_system": system,
        },
        "regulation_context": {},
        "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"},
    })


class V05TargetedRepairTests(unittest.TestCase):
    def test_t01_generic_modifier_extraction(self):
        route = next(item for item in routes() if item["kind"] == "conditional_rule")
        view = derive_semantic_view(
            {"building_form": "高层建筑", "fire_resistance_rating": "一级",
             "auto_extinguishing_system": "全部设置自动灭火系统"},
            "当全部设置自动灭火系统时，上述面积可以增加1.0倍；提高30%。",
            route["unit_type"], route, fact_descriptors(),
        )
        modifiers = [modifier for rule in view["conditions"]["modifier_rules"] for modifier in rule["modifiers"]]
        self.assertEqual(modifiers[0]["operator"], "multiply")
        self.assertEqual(modifiers[0]["value"], 2.0)
        self.assertEqual(modifiers[1]["operator"], "multiply")
        self.assertEqual(modifiers[1]["value"], 1.3)
        self.assertEqual(view["numeric"]["operands"][0]["kind"], "source_rule_value")

    def test_t02_declarative_route_resolution(self):
        facts = {"jurisdiction": "浙江省·杭州市", "city_class": "规划人口大于50万的城市",
                 "building_category": "大型商业", "floor_area_m2": 15000.0}
        questions = (
            "某项目与人员密集场所的最小防火间距是多少？",
            "某大型商业项目机动车配建停车位指标应为多少？",
            "某项目每个防火分区的最大允许建筑面积应为多少？",
        )
        for question in questions:
            chain = applicability_for_question(question, facts, None)
            self.assertIsInstance(chain.get("route"), dict)
            self.assertIn(chain["route"], list(routes()))

    def test_t03_anti_hardcode_boundary(self):
        data = json.loads((CANDIDATE_ROOT / "brea" / "professional_data.json").read_text(encoding="utf-8"))
        domain_values = set()
        for route in data["routes"]:
            domain_values.update((route.get("name"), route.get("standard_id"), route.get("locator")))
            domain_values.update(route.get("intent_terms", []))
            domain_values.add(route.get("table_caption"))
        domain_values.update({"增加1.0倍", "3000", "2500", "1000", "500", "0.8", "1.1"})
        execution_files = [
            path for path in (CANDIDATE_ROOT / "brea").glob("*.py")
            if path.name not in {"domain_data.py"}
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in execution_files)
        leaked = sorted(token for token in domain_values if token and token in text)
        self.assertEqual(leaked, [])
        self.assertNotRegex(text, r"if\s+.*(?:fire_compartment|防火间距|停车位|配建)")

    def test_t04_five_forms_share_coherent_path(self):
        direct = _run(_request("T-C01"))
        table = _run(_request("T-C02"))
        conditional = _fire("T04-CONDITIONAL", "公共建筑（办公楼）", "高层建筑", "一级", "无")
        excluded = _fire("T04-EXCLUDED", "公共建筑（木结构建筑）", "高层建筑", "一级", "无")
        derived = _fire("T04-DERIVED", "公共建筑（办公楼）", "高层建筑", "一级", "全部设置自动灭火系统")
        results = (direct, table, conditional, excluded, derived)
        self.assertTrue(all(result.implementation_metadata.professional_trace["path"] == "generic_professional" for result in results))
        self.assertEqual(direct.status, "accepted_with_evidence")
        self.assertEqual(table.status, "accepted_with_evidence")
        self.assertEqual(conditional.status, "accepted_with_evidence")
        self.assertEqual(excluded.status, "no_reliable_evidence")
        self.assertEqual(excluded.implementation_metadata.professional_trace["applicability"]["state"], "excluded")
        self.assertEqual(derived.status, "accepted_with_evidence")
        self.assertEqual(derived.implementation_metadata.professional_trace["numeric"]["result"], 3000.0)

    def test_t05_pc_contract(self):
        for result in (_run(_request("T-C01")), _run(_request("T-C02")),
                       _fire("T05-PC", "公共建筑（办公楼）", "高层建筑", "一级", "全部设置自动灭火系统")):
            trace = result.implementation_metadata.professional_trace
            self.assertEqual(set(trace["professional_contract"]), {f"PC-{i:02d}" for i in range(1, 8)})
            self.assertTrue(all(value == "PASS" for value in trace["professional_contract"].values()))
            self.assertEqual(trace["applicability"]["owner"], "SEAM-02")

    def test_t06_e1_and_formation_regression(self):
        clause = _run({"request_id": "T06-CLAUSE", "question": "GB55037-2022 第2.1.1条怎么规定？",
                       "project_context": {}, "regulation_context": {},
                       "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"}})
        topic = _run({"request_id": "T06-TOPIC", "question": "GB55037 里哪里提到人员密集场所？",
                      "project_context": {}, "regulation_context": {},
                      "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"}})
        self.assertEqual(clause.status, "evidence_retrieved")
        self.assertEqual(topic.status, "evidence_retrieved")
        self.assertEqual(_run(_request("T-C01")).status, "accepted_with_evidence")
        self.assertEqual(_run(_request("T-C02")).status, "accepted_with_evidence")
        closed = _run(_request("T-C03"))
        self.assertEqual(closed.status, "insufficient_context")
        self.assertEqual(closed.evidence_items, ())
        self.assertFalse(re.search(r"\d", closed.conclusion))

    def test_t07_identity_lineage_and_fingerprint(self):
        self.assertEqual(VERSION, "v0.5-candidate")
        self.assertEqual(LINEAGE_PARENT, "case-01.brea@0.4-candidate")
        self.assertEqual(set(BREA_FUNCTION_MAP), {f"FN-{i:02d}" for i in range(1, 12)})
        self.assertEqual(set(SEAM_MAP), {"SEAM-01", "SEAM-02", "SEAM-03"})
        self.assertEqual(set(OBLIGATIONS), {f"OBL-{i:02d}" for i in range(1, 7)})
        self.assertRegex(implementation_fingerprint(), r"^[0-9a-f]{64}$")

    def test_t08_platform_bound_compatibility(self):
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
                request = _request("T-C02")
                result = _run(request)
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
        request = _request("T-C02")
        result = adapter.execute(Invocation(
            id="t08", capability_id="case-01.brea.execute", capability_version="0.1",
            input=request, context={"extensions": {}}, trace_id="t08-trace",
        ))
        self.assertEqual(result.status, "success")
        self.assertEqual((result.output or {}).get("status"), "accepted_with_evidence")

    def test_t09_protected_boundaries(self):
        allowed = "case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/next-candidate/"
        changed = subprocess.run(["git", "diff", "--name-only", "48b48c16c1ea83409f044c923d26277a5d835718"],
                                 cwd=REPO_ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
        changed += subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=REPO_ROOT,
                                  check=True, capture_output=True, text=True).stdout.splitlines()
        self.assertTrue(changed)
        self.assertTrue(all(path.startswith(allowed) for path in changed), changed)


if __name__ == "__main__":
    unittest.main()
