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
KR_PATH = NEXT_CANDIDATE / "knowledge" / "KR-001.json"
sys.path.insert(0, str(CANDIDATE_ROOT))

from brea.identity import BREA_FUNCTION_MAP, LINEAGE_PARENT, OBLIGATIONS, SEAM_MAP, VERSION  # noqa: E402
from brea.runner import answer, implementation_fingerprint  # noqa: E402


FIXTURES = CANDIDATE_ROOT / "tests" / "fixtures" / "requests"


def _request(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["request"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding() -> dict:
    revision = json.loads(KR_PATH.read_text(encoding="utf-8"))
    return {"revision_id": revision["knowledge_revision_id"], "path": str(KR_PATH), "sha256": _sha(KR_PATH)}


def _run(request: dict, binding: dict | None = None):
    return answer(
        request["request_id"], request["question"], request.get("project_context", {}),
        request.get("regulation_context", {}), request["enterprise_context"],
        knowledge_binding=binding,
    )


class V06KnowledgeLifecycleTests(unittest.TestCase):
    def test_k01_explicit_kr001_binding(self):
        result = _run(_request("T-C01"), _binding())
        self.assertEqual(result.status, "accepted_with_evidence")
        self.assertEqual(result.implementation_metadata.knowledge_revision_id, "KR-001")
        self.assertEqual(result.implementation_metadata.knowledge_revision_sha256, _sha(KR_PATH))

    def test_k02_no_historical_manifest_hard_binding(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in (CANDIDATE_ROOT / "brea").glob("*.py"))
        self.assertNotIn("LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md", source)
        self.assertNotIn("MANIFEST_REL", source)

    def test_k03_no_candidate_local_professional_data_ownership(self):
        self.assertFalse((CANDIDATE_ROOT / "brea" / "professional_data.json").exists())
        source = "\n".join(path.read_text(encoding="utf-8") for path in (CANDIDATE_ROOT / "brea").glob("*.py"))
        self.assertNotIn("professional_data.json", source)

    def test_k04_missing_or_invalid_binding_fails_closed(self):
        missing = _run(_request("T-C01"), None)
        invalid = _run(_request("T-C01"), {"revision_id": "KR-001", "path": str(KR_PATH), "sha256": "0" * 64})
        for result in (missing, invalid):
            self.assertEqual(result.status, "no_reliable_evidence")
            self.assertEqual(result.evidence_items, ())
            self.assertIn("knowledge", result.implementation_metadata.professional_trace)

    def test_k05_result_and_trace_record_knowledge_identity(self):
        result = _run(_request("T-C02"), _binding())
        trace = result.implementation_metadata.professional_trace
        expected = _sha(KR_PATH)
        self.assertEqual(trace["knowledge_revision_id"], "KR-001")
        self.assertEqual(trace["knowledge_revision_sha256"], expected)
        self.assertEqual(result.implementation_metadata.knowledge_revision_sha256, expected)

    def test_k06_v05_professional_regression(self):
        self.assertEqual(_run(_request("T-C01"), _binding()).status, "accepted_with_evidence")
        self.assertEqual(_run(_request("T-C02"), _binding()).status, "accepted_with_evidence")
        self.assertEqual(_run(_request("T-C03"), _binding()).status, "insufficient_context")

    def test_k07_e1_and_tc_regression(self):
        binding = _binding()
        clause = _run({"request_id": "K07-CLAUSE", "question": "GB55037-2022 第2.1.1条怎么规定？",
                       "project_context": {}, "regulation_context": {},
                       "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"}}, binding)
        topic = _run({"request_id": "K07-TOPIC", "question": "GB55037 里哪里提到人员密集场所？",
                      "project_context": {}, "regulation_context": {},
                      "enterprise_context": {"organization_id": "org-test", "user_id": "user-test"}}, binding)
        self.assertEqual(clause.status, "evidence_retrieved")
        self.assertEqual(topic.status, "evidence_retrieved")
        self.assertEqual(_run(_request("T-C01"), binding).status, "accepted_with_evidence")
        self.assertEqual(_run(_request("T-C02"), binding).status, "accepted_with_evidence")
        self.assertEqual(_run(_request("T-C03"), binding).status, "insufficient_context")

    def test_k08_identity_lineage_fingerprint_and_boundaries(self):
        self.assertEqual(VERSION, "v0.6-candidate")
        self.assertEqual(LINEAGE_PARENT, "case-01.brea@0.5-candidate")
        self.assertEqual(set(BREA_FUNCTION_MAP), {f"FN-{i:02d}" for i in range(1, 12)})
        self.assertEqual(set(SEAM_MAP), {"SEAM-01", "SEAM-02", "SEAM-03"})
        self.assertEqual(set(OBLIGATIONS), {f"OBL-{i:02d}" for i in range(1, 7)})
        self.assertRegex(implementation_fingerprint(), r"^[0-9a-f]{64}$")
        allowed = "case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/next-candidate/"
        changed = subprocess.run(["git", "diff", "--name-only", "1f8560a1d644163ec10bd097dfcb287d233ca4e9"], cwd=REPO_ROOT,
                                 check=True, capture_output=True, text=True).stdout.splitlines()
        changed += subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=REPO_ROOT,
                                  check=True, capture_output=True, text=True).stdout.splitlines()
        self.assertTrue(changed)
        self.assertTrue(all(path.startswith(allowed) for path in changed), changed)
        self.assertFalse(any("candidate/brea-v0.5" in path for path in changed), changed)

    def test_k09_platform_bound_compatibility(self):
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
                result = _run(_request("T-C02"), _binding())
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
            id="k09", capability_id="case-01.brea.execute", capability_version="0.1",
            input=_request("T-C02"), context={"extensions": {}}, trace_id="k09-trace",
        ))
        self.assertEqual(result.status, "success")
        self.assertEqual((result.output or {}).get("status"), "accepted_with_evidence")


if __name__ == "__main__":
    unittest.main()
