import unittest

from shared.runner import run_experiment


class RepresentationMinimumExperimentTests(unittest.TestCase):
    def test_both_tracks_use_same_contract_and_cover_pc_01_to_pc_07(self):
        results = run_experiment()

        self.assertEqual(results["comparison"]["shared_result_contract"], True)
        for track in ("A_PRIME", "B_MIN"):
            summary = results["tracks"][track]
            self.assertEqual(set(summary["pc_summary"]), {
                "PC-01", "PC-02", "PC-03", "PC-04", "PC-05", "PC-06", "PC-07"
            })
        self.assertEqual(results["tracks"]["A_PRIME"]["pc_summary"]["PC-06"], "FAIL")
        self.assertEqual(results["tracks"]["A_PRIME"]["pc_summary"]["PC-07"], "PASS")
        self.assertEqual(results["tracks"]["B_MIN"]["pc_summary"]["PC-06"], "PASS")
        self.assertEqual(results["tracks"]["B_MIN"]["pc_summary"]["PC-07"], "PASS")

        self.assertNotEqual(
            results["tracks"]["A_PRIME"]["pc_summary"],
            results["tracks"]["B_MIN"]["pc_summary"],
        )

    def test_b_min_ablation_removes_every_non_base_group_for_a_material_failure(self):
        results = run_experiment()
        ablation = results["b_min_ablation"]

        self.assertEqual(ablation["G-BASE"]["material_failure"], True)
        self.assertEqual(ablation["G-SCOPE"]["material_failure"], True)
        self.assertEqual(ablation["G-CONDITION"]["material_failure"], True)
        self.assertEqual(ablation["G-NUMERIC"]["material_failure"], True)
        self.assertEqual(ablation["retained_groups"], [
            "G-BASE", "G-SCOPE", "G-CONDITION", "G-NUMERIC"
        ])

    def test_same_structure_extension_is_data_only_and_b_min_remains_contract_complete(self):
        results = run_experiment()
        extension = results["same_structure_extension"]

        self.assertTrue(extension["data_only"])
        self.assertTrue(extension["mechanism_code_unchanged"])
        self.assertTrue(extension["schema_unchanged"])
        self.assertFalse(extension["tracks"]["A_PRIME"]["contract_ok"])
        self.assertTrue(extension["tracks"]["B_MIN"]["contract_ok"])

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


if __name__ == "__main__":
    unittest.main()
