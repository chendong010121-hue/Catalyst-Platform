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

from brea.identity import (  # noqa: E402
    BREA_FUNCTION_MAP,
    LINEAGE_PARENT,
    OBLIGATIONS,
    SEAM_MAP,
    VERSION,
)
from brea.runner import answer, implementation_fingerprint  # noqa: E402


FIXTURES = CANDIDATE_ROOT / "tests" / "fixtures" / "requests"


def _request(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["request"]


def _run(request: dict):
    return answer(
        request["request_id"],
        request["question"],
        request.get("project_context", {}),
        request.get("regulation_context", {}),
        request["enterprise_context"],
    )


def _fire_request(request_id: str, category: str, form: str, rating: str, system: str):
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


class V04ContractTests(unittest.TestCase):
    def test_c01_generalized_local_query_regression(self):
        clause = _run({
            "request_id": "C01-CLAUSE",
            "question": "GB55037-2022 第2.1.1条怎么规定？",
            "project_context": {},
            "regulation_context": {},
            "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"},
        })
        topic = _run({
            "request_id": "C01-TOPIC",
            "question": "GB55037 里哪里提到人员密集场所？",
            "project_context": {},
            "regulation_context": {},
            "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"},
        })
        self.assertEqual(clause.status, "evidence_retrieved")
        self.assertEqual(topic.status, "evidence_retrieved")

    def test_c02_shared_professional_contract_trace(self):
        result = _run(_request("T-C01"))
        trace = result.implementation_metadata.professional_trace
        self.assertEqual(set(trace["semantic_view"]), {"scope", "conditions", "numeric"})
        self.assertEqual(trace["applicability"]["owner"], "SEAM-02")
        self.assertTrue(all(value == "PASS" for value in trace["professional_contract"].values()))
        self.assertTrue(trace["evidence_binding"]["source_fidelity"])
        self.assertTrue(trace["evidence_binding"]["provenance_complete"])

    def test_c03_supported_forms_share_one_path(self):
        direct = _run(_request("T-C01"))
        table = _run(_request("T-C02"))
        derived = _fire_request(
            "C03-DERIVED", "公共建筑（办公楼）", "高层建筑", "一级", "全部设置自动灭火系统"
        )
        self.assertEqual(direct.status, "accepted_with_evidence")
        self.assertEqual(table.status, "accepted_with_evidence")
        self.assertEqual(derived.status, "accepted_with_evidence")
        self.assertEqual(derived.implementation_metadata.professional_trace["numeric"]["result"], 3000.0)

    def test_c04_v03_defect_regressions(self):
        from brea.professional import _numeric_trace

        non_public = _fire_request("C04-NON-PUBLIC", "住宅", "高层建筑", "一级", "无")
        equipment = _fire_request("C04-EQUIPMENT", "公共建筑", "地下设备用房", "一级", "无")
        other = _fire_request("C04-OTHER", "公共建筑", "地下其他区域", "一级", "无")

        self.assertEqual(non_public.status, "no_reliable_evidence")
        self.assertIsNone(non_public.implementation_metadata.professional_trace["numeric"])
        self.assertEqual(equipment.implementation_metadata.professional_trace["numeric"]["result"], 1000.0)
        self.assertEqual(other.implementation_metadata.professional_trace["numeric"]["result"], 500.0)
        self.assertNotEqual(equipment.conclusion, other.conclusion)
        self.assertEqual(equipment.implementation_metadata.professional_trace["applicability"]["owner"], "SEAM-02")
        self.assertIsNone(_numeric_trace(
            {"numeric": {"operands": [{"kind": "fact", "fact": "missing"}], "modifiers": [{"operator": "multiply", "value": 2}] }},
            {"state": "applicable"}, {"known": 1},
        ))

    def test_c05_t_c01_t_c02_t_c03_regression(self):
        self.assertEqual(_run(_request("T-C01")).status, "accepted_with_evidence")
        self.assertEqual(_run(_request("T-C02")).status, "accepted_with_evidence")
        closed = _run(_request("T-C03"))
        self.assertEqual(closed.status, "insufficient_context")
        self.assertEqual(closed.evidence_items, ())
        self.assertFalse(re.search(r"\d", closed.conclusion))

    def test_c06_hidden_family_source_locator_hardcode_scan(self):
        forbidden = (
            "某项目每个防火分区的最大允许建筑面积",
            "不应大于 3000",
            "不应大于 2500",
            "不应大于 1000",
            "不应大于 500",
            "3.1.3",
            "4.3.16",
            "5.0.4",
        )
        checked = [
            path for path in (CANDIDATE_ROOT / "brea").rglob("*.py")
            if path.name not in {"professional_data.py"}
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in checked)
        self.assertFalse(any(token in text for token in forbidden))

    def test_c07_same_structure_data_only_extension(self):
        before = implementation_fingerprint()
        result = _run({
            "request_id": "C07-EXTENSION",
            "question": "GB55037-2022 第2.1.1条怎么规定？",
            "project_context": {},
            "regulation_context": {},
            "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"},
        })
        after = implementation_fingerprint()
        self.assertEqual(result.status, "evidence_retrieved")
        self.assertEqual(before, after)

    def test_c08_identity_lineage_and_function_contract(self):
        self.assertEqual(VERSION, "v0.4-candidate")
        self.assertEqual(LINEAGE_PARENT, "case-01.brea@0.3-candidate")
        self.assertEqual(set(BREA_FUNCTION_MAP), {f"FN-{index:02d}" for index in range(1, 12)})
        self.assertEqual(set(SEAM_MAP), {"SEAM-01", "SEAM-02", "SEAM-03"})
        self.assertEqual(set(OBLIGATIONS), {f"OBL-{index:02d}" for index in range(1, 7)})

    def test_c09_platform_bound_execution_compatibility(self):
        sys.path.insert(0, str(REPO_ROOT))
        from agent_runtime.contracts import CapabilityDescriptor as RuntimeDescriptor, Success
        from examples.platform_standard_reference import reference_runtime_factory
        from platform_standard.models import CapabilityDescriptor, Invocation
        from platform_standard.registry import InMemoryDescriptorRegistry
        from platform_standard.runtime_adapter import RuntimeAdapter

        class CandidateCapability:
            def describe(self):
                return RuntimeDescriptor(
                    id="case_01_brea_execute", name="BREA Execute", description="routing",
                    input_schema={"type": "object"}, output_schema={"type": "object"},
                )

            def invoke(self, parameters, context):
                request = _request("T-C02")
                result = answer(
                    parameters["request_id"], parameters["question"],
                    parameters.get("project_context", {}), parameters.get("regulation_context", {}),
                    parameters.get("enterprise_context", {}),
                )
                return Success(result.to_dict())

        registry = InMemoryDescriptorRegistry()
        registry.register(CapabilityDescriptor(
            id="case-01.brea.execute", name="BREA Execute", description="routing",
            capability_version="0.1", input_schema={"type": "object"},
            output_schema={"type": "object"}, execution={"side_effect": "none"},
        ))
        adapter = RuntimeAdapter(
            registry, bindings={("case-01.brea.execute", "0.1"): CandidateCapability()},
            runtime_factory=reference_runtime_factory,
        )
        request = _request("T-C02")
        invocation = Invocation(
            id="c09", capability_id="case-01.brea.execute", capability_version="0.1",
            input=request, context={"extensions": {}}, trace_id="c09-trace",
        )
        result = adapter.execute(invocation)
        self.assertEqual(result.status, "success")
        self.assertEqual((result.output or {}).get("status"), "accepted_with_evidence")

    def test_c10_changes_are_confined_to_candidate_surface(self):
        allowed = "case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/next-candidate/"
        tracked = subprocess.run(
            ["git", "diff", "--name-only", "db62e13d40914465b0ea557cf99dfb676b5bcad6"],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        changed = tracked + untracked
        self.assertTrue(changed)
        self.assertTrue(all(path.startswith(allowed) for path in changed), changed)


if __name__ == "__main__":
    unittest.main()
