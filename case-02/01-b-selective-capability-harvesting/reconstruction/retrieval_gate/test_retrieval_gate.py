import json
import unittest
from pathlib import Path


from retrieval_gate import (
    Decision,
    InMemoryMemoryStore,
    RetrievalGate,
    ScriptedDecisionProvider,
)


class RetrievalGateBehaviorTests(unittest.TestCase):
    def test_r01_retrieve_searches_once_propagates_exact_query_and_traces_reason(self):
        provider = ScriptedDecisionProvider([
            Decision("RETRIEVE", "Alex meeting Friday", "turn mentions a plan")
        ])
        store = InMemoryMemoryStore({"Alex meeting Friday": ["Alex meets Friday"]})

        result = RetrievalGate(provider, store).run("When is my meeting with Alex?")

        self.assertEqual(store.searches, ["Alex meeting Friday"])
        self.assertEqual(result.retrieved_material, ["Alex meets Friday"])
        self.assertEqual(result.decision, "RETRIEVE")
        self.assertEqual(result.query, "Alex meeting Friday")
        self.assertEqual(result.trace[0], {
            "decision": "RETRIEVE",
            "query": "Alex meeting Friday",
            "reason": "turn mentions a plan",
            "fallback": False,
        })

    def test_r02_skip_does_not_search_and_returns_no_material(self):
        provider = ScriptedDecisionProvider([
            Decision("SKIP", "", "self-contained request")
        ])
        store = InMemoryMemoryStore({"unused": ["must not be returned"]})

        result = RetrievalGate(provider, store).run("What is 2 + 2?")

        self.assertEqual(store.searches, [])
        self.assertEqual(result.retrieved_material, [])
        self.assertEqual(result.decision, "SKIP")
        self.assertEqual(result.trace[0], {
            "decision": "SKIP",
            "query": "",
            "reason": "self-contained request",
            "fallback": False,
        })

    def test_r03_provider_failure_fails_open_with_original_turn_query(self):
        provider = ScriptedDecisionProvider([RuntimeError("provider unavailable")])
        store = InMemoryMemoryStore({"Who is Alex?": ["Alex is a teammate"]})

        result = RetrievalGate(provider, store).run("Who is Alex?")

        self.assertEqual(store.searches, ["Who is Alex?"])
        self.assertEqual(result.retrieved_material, ["Alex is a teammate"])
        self.assertEqual(result.decision, "RETRIEVE")
        self.assertTrue(result.trace[0]["fallback"])
        self.assertEqual(result.trace[0]["query"], "Who is Alex?")
        self.assertIn("RuntimeError", result.trace[0]["reason"])

    def test_r04_gate_has_no_durable_write_ranking_prompt_loop_or_semantic_owner(self):
        provider = ScriptedDecisionProvider([
            Decision("RETRIEVE", "topic", "needs context")
        ])
        store = InMemoryMemoryStore({"topic": ["one result"]})
        gate = RetrievalGate(provider, store)

        gate.run("turn")

        self.assertEqual(store.writes, 0)
        for forbidden_method in (
            "write",
            "save",
            "rank",
            "assemble_prompt",
            "run_loop",
            "apply_domain_semantics",
            "apply_enterprise_policy",
        ):
            self.assertFalse(hasattr(gate, forbidden_method), forbidden_method)


class ReconstructionEvidenceTests(unittest.TestCase):
    def test_r05_and_r06_results_preserve_lineage_and_unbound_bindings(self):
        path = Path(__file__).parents[2] / "CASE_02_B_RESULTS.json"
        record = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(record["source_asset_id"], "WAKU-A01")
        self.assertEqual(record["source_catalog_id"], "CASE_02_WAKU_ASSET_CATALOG_V0.1")
        self.assertEqual(record["source_agent"], "waku-agent")
        self.assertEqual(record["source_commit"], "8328f567ab52d07921445cb40feed23cbc5ea2ad")
        self.assertEqual(record["reconstruction_type"], "CATALYST_NATIVE_CASE_LOCAL")
        self.assertEqual(record["artifact_status"], "UNBOUND_CASE_LOCAL_MECHANISM")
        self.assertEqual(record["semantic_binding"], "UNBOUND")
        self.assertEqual(record["domain_binding"], "NONE")
        self.assertEqual(record["enterprise_binding"], "NONE")
        self.assertEqual(record["target_agent_binding"], "NONE")
        self.assertEqual(record["proofs"], ["R-01", "R-02", "R-03", "R-04", "R-05", "R-06"])


if __name__ == "__main__":
    unittest.main()
