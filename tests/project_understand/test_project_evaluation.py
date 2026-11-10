"""Independent project handoff evaluation contracts; no target code execution."""
import copy
import importlib
import json

import pytest

from catalyst_platform.evaluation_adapter import check_health, compare_evaluations
from fixture_data import CONTROL_SOURCES, control_sample


def evaluator():
    return importlib.import_module("catalyst_platform.project_understand_evaluation")


def test_finite_controls_are_independent_and_semantics_are_not_scored():
    module = evaluator()
    for label in CONTROL_SOURCES:
        observation, gold = control_sample(label)
        grade = module.project_grader(observation, gold)
        assert grade["task_success"] is True, (label, grade)
        assert grade["dimensions"]["SOURCE_SUPPORT"]["status"] == "PASS"
        assert grade["dimensions"]["SEMANTIC_QUALITY"]["status"] == "NOT_EVALUATED"
        assert grade["formal_owner_admission"] is False


@pytest.mark.parametrize("mutation,dimension", [
    ("wrong_claim", "SOURCE_SUPPORT"), ("drop_condition", "SOURCE_SUPPORT"),
    ("quote_tamper", "SOURCE_IDENTITY"), ("line_forgery", "SOURCE_IDENTITY"),
    ("source_drift", "SOURCE_IDENTITY"), ("unread_as_read", "COVERAGE_INTEGRITY"),
    ("invented_evidence", "STRUCTURE_VALIDITY"), ("wrong_question", "QUESTION_CLOSURE"),
    ("unknown_critical_ready", "QUESTION_CLOSURE"),
    ("unrelated_valid_quote", "SOURCE_SUPPORT"), ("claims_execution", "SOURCE_SUPPORT"),
    ("missing_critical", "QUESTION_CLOSURE"), ("cancelled", "QUESTION_CLOSURE"),
])
def test_mechanical_and_finite_source_failures_cannot_pass(mutation, dimension):
    module = evaluator()
    observation, gold = control_sample("implicit_global_state")
    analysis = observation["analysis"]
    if mutation == "wrong_claim": analysis["claims"][0]["text"] = "read has no dependencies"
    if mutation == "drop_condition": analysis["claims"][0]["conditions"] = []
    if mutation == "quote_tamper": observation["evidence"][0]["quote"] = "fabricated quote"
    if mutation == "line_forgery": observation["evidence"][0]["start_line"] = 999
    if mutation == "source_drift": observation["source_reads"][0]["sha256"] = "0" * 64
    if mutation == "unread_as_read": observation["source_reads"] = []
    if mutation == "invented_evidence": analysis["claims"][0]["evidence_ids"] = ["invented"]
    if mutation == "wrong_question": analysis["objective"] = "Different task"
    if mutation == "unknown_critical_ready": analysis["questions"][0]["status"] = "EXPLICITLY_UNRESOLVED"
    if mutation == "unrelated_valid_quote":
        import hashlib
        observation["evidence"][0].update(quote="CACHE = {}", start_line=1, end_line=1,
                                          span_sha256=hashlib.sha256(b"CACHE = {}").hexdigest())
    if mutation == "claims_execution": analysis["claims"][0]["support_mode"] = "OBSERVED_RUNTIME"
    if mutation == "missing_critical": analysis["questions"] = []
    if mutation == "cancelled": analysis["analysis_finished"] = False
    grade = module.project_grader(observation, gold)
    assert grade["task_success"] is False
    assert grade["dimensions"][dimension]["status"] == "FAIL"


def test_honest_unresolved_finishes_analysis_but_not_task_success():
    module = evaluator()
    observation, gold = control_sample()
    observation["analysis"]["questions"][0]["status"] = "EXPLICITLY_UNRESOLVED"
    observation["analysis"]["decision_readiness"] = "NEEDS_EVIDENCE"
    grade = module.project_grader(observation, gold)
    assert grade["task_success"] is False
    assert "UNRESOLVED_CRITICAL_QUESTION" in grade["critical_faults"]


def test_real_source_identity_does_not_claim_prose_entailment():
    module = evaluator()
    observation, gold = control_sample()
    gold["basis"] = "INDEPENDENT_SOURCE_IDENTITY_ONLY"
    del gold["claim_support"]
    grade = module.project_grader(observation, gold)
    assert grade["dimensions"]["SOURCE_IDENTITY"]["status"] == "PASS"
    assert grade["dimensions"]["SOURCE_SUPPORT"]["status"] == "NOT_EVALUATED"
    assert grade["claim_checks"][0]["support_status"] == "NOT_EVALUATED"
    assert grade["evidence_checks"][0]["identity_status"] == "PASS"
    assert grade["task_success"] is None
    assert grade["failure_class"] == "SEMANTIC_NOT_EVALUATED"


def test_unknown_oracle_is_rejected_and_health_has_negative_probes():
    module = evaluator()
    observation, gold = control_sample()
    gold["basis"] = "PRODUCER_SELF_SIGNED"
    with pytest.raises(ValueError, match="independent"):
        module.project_grader(observation, gold)
    health = check_health(module.project_profile(), module.project_grader, module.project_health_probes())
    assert health["status"] == "PASS"
    assert len(health["checks"]) == 5


def test_host_provenance_outer_wrapper_overrides_producer_field():
    module = evaluator()
    observation, gold = control_sample()
    observation["source_manifest_sha256"] = observation["analysis"].pop("source_manifest_sha256")
    assert module.project_grader(observation, gold)["task_success"] is True
    observation["source_manifest_sha256"] = "0" * 64
    observation["analysis"]["source_manifest_sha256"] = gold["source_manifest_sha256"]
    grade = module.project_grader(observation, gold)
    assert grade["task_success"] is False
    assert grade["dimensions"]["SOURCE_IDENTITY"]["status"] == "FAIL"


def test_shared_adapter_separates_gold_and_detects_frozen_artifact_tamper(tmp_path):
    module = evaluator()
    observation, gold = control_sample()
    public = {"objective": gold["objective"]}
    case = {"id": "project_control", "split": "val", "critical": True, "public": public, "gold": gold}
    def entry(packet, workspace):
        assert packet == public
        assert "claim_support" not in packet
        return copy.deepcopy(observation)
    result = module.run_project_evaluation([case], entry, tmp_path / "evaluation", target_identity="synthetic-control")
    assert result["rows"][0]["task_success"] is True
    frozen = tmp_path / "evaluation/cases/project_control/observation.json"
    frozen.write_text(json.dumps({"tampered": True}))
    with pytest.raises(ValueError, match="identity"):
        compare_evaluations(tmp_path / "evaluation", tmp_path / "evaluation")
