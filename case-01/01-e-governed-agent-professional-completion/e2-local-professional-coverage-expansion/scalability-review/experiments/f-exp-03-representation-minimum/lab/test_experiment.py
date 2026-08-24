import unittest

from shared.runner import run_experiment


class RepresentationMinimumExperimentTests(unittest.TestCase):
    def test_both_tracks_use_same_contract_and_cover_pc_01_to_pc_07(self):
        results = run_experiment()

        self.assertEqual(results["comparison"]["shared_result_contract"], True)
        self.assertEqual(results["comparison"]["shared_semantic_interface"], True)
        for track in ("A_PRIME", "B_MIN"):
            summary = results["tracks"][track]
            self.assertEqual(set(summary["pc_summary"]), {
                "PC-01", "PC-02", "PC-03", "PC-04", "PC-05", "PC-06", "PC-07"
            })
        for a_case, b_case in zip(
            results["tracks"]["A_PRIME"]["cases"],
            results["tracks"]["B_MIN"]["cases"],
        ):
            a_view = a_case["evidence_trace"]["semantic_view"]
            b_view = b_case["evidence_trace"]["semantic_view"]
            self.assertEqual(set(a_view), set(b_view))
            self.assertTrue(a_view["scope"])
            self.assertTrue(a_view["conditions"])

    def test_b_min_numeric_representation_has_no_project_derived_result(self):
        from shared.model import load_lab_data

        case = next(case for case in load_lab_data()["cases"] if case["case_id"] == "RF-05")
        numeric = case["b_min"]["G-NUMERIC"]

        self.assertIn("operands", numeric)
        self.assertIn("modifiers", numeric)
        self.assertIn("advisory_caps", numeric)
        self.assertNotIn("result", numeric)
        self.assertNotIn("formula", numeric)

        results = run_experiment()
        observed = next(case for case in results["tracks"]["B_MIN"]["cases"] if case["case_id"] == "RF-05")
        self.assertEqual(observed["evidence_trace"]["numeric_trace"]["result"], 12)
        self.assertEqual(observed["evidence_trace"]["numeric_trace"]["result"], case["expected"]["numeric_result"])

    def test_rf03_validates_both_source_backed_table_values(self):
        results = run_experiment()
        for track in ("A_PRIME", "B_MIN"):
            observed = next(case for case in results["tracks"][track]["cases"] if case["case_id"] == "RF-03")
            table_values = observed["evidence_trace"]["table_values"]
            self.assertEqual(table_values["机动车"], 0.8)
            self.assertEqual(table_values["非机动车"], 1.1)
            self.assertEqual(observed["evidence_trace"]["table_values_gold_match"], True)

    def test_b_min_ablation_reports_each_field_group_observation(self):
        results = run_experiment()
        ablation = results["b_min_ablation"]

        for group in ("G-BASE", "G-SCOPE", "G-CONDITION", "G-NUMERIC"):
            self.assertIn(ablation[group]["material_failure"], (True, False))
            self.assertEqual(ablation[group]["removed_group"], group)
            self.assertIsInstance(ablation[group]["failed_pcs"], list)
        self.assertEqual(ablation["retained_groups"], [
            "G-BASE", "G-SCOPE", "G-CONDITION", "G-NUMERIC"
        ])

    def test_same_structure_extension_is_data_only_and_b_min_remains_contract_complete(self):
        results = run_experiment()
        extension = results["same_structure_extension"]

        self.assertTrue(extension["data_only"])
        self.assertTrue(extension["mechanism_code_unchanged"])
        self.assertTrue(extension["schema_unchanged"])
        self.assertEqual(set(extension["tracks"]["A_PRIME"]), set(extension["tracks"]["B_MIN"]))

    def test_unsupported_numeric_fails_closed_without_a_numeric_conclusion(self):
        results = run_experiment()
        missing = next(
            case for case in results["tracks"]["B_MIN"]["cases"]
            if case["case_id"] == "RF-05-MISSING-OPERAND"
        )

        self.assertEqual(missing["status"], "FAIL_CLOSED")
        self.assertIsNone(missing["conclusion"])
        self.assertEqual(missing["evidence_trace"]["failure_code"], "unsupported_numeric")

    def test_hidden_knowledge_scan_rejects_family_specific_runtime_knowledge(self):
        results = run_experiment()

        self.assertEqual(results["hidden_knowledge"]["A_PRIME"], "PASS")
        self.assertEqual(results["hidden_knowledge"]["B_MIN"], "PASS")
        self.assertEqual(results["hidden_knowledge"]["shared_validator"], "PASS")
        self.assertEqual(results["hidden_knowledge"]["shared_semantic_derivation"], "PASS")

    def test_decision_candidate_is_derived_from_observed_results(self):
        from shared.runner import decide_from_observations

        results = run_experiment()
        self.assertIn(results["decision_candidate"], {
            "A_PRIME_SUFFICIENT",
            "B_MIN_EVIDENCED",
            "BOTH_INSUFFICIENT",
            "INCONCLUSIVE",
            "EXPERIMENT_INVALID",
        })
        self.assertEqual(results["decision_candidate"], decide_from_observations(results))

    def test_oracle_contains_no_preselected_track_winner(self):
        source = __import__("pathlib").Path(__file__).read_text(encoding="utf-8")

        self.assertNotIn('assertFalse(extension' + '["tracks"]["A_PRIME"]', source)
        self.assertNotIn('assertTrue(extension' + '["tracks"]["B_MIN"]', source)
        self.assertNotIn('assertEqual(results' + '["tracks"]["A_PRIME"]["pc_summary"]', source)
        self.assertNotIn('assertEqual(results' + '["tracks"]["B_MIN"]["pc_summary"]', source)


if __name__ == "__main__":
    unittest.main()
