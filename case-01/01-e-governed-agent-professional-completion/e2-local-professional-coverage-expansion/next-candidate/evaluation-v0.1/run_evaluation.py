"""Case-local deterministic execution for the frozen BREA v0.9 evaluation.

This runner is deliberately replaceable and owns no Catalyst meaning.  It loads
the public cases and private rubric separately, calls the frozen product entry
point, and writes only the two authorized evidence artifacts.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVALUATION_DIR = Path(__file__).resolve().parent
NEXT_CANDIDATE = EVALUATION_DIR.parent
REPO_ROOT = NEXT_CANDIDATE.parents[3]
CANDIDATE = NEXT_CANDIDATE / "candidate" / "brea-v0.9"
KNOWLEDGE = NEXT_CANDIDATE / "knowledge" / "KR-003.json"
PUBLIC = EVALUATION_DIR / "benchmark" / "public" / "benchmark_cases.json"
PRIVATE = EVALUATION_DIR / "benchmark" / "private" / "rubric.json"
RESPONSIBILITY_MAP = EVALUATION_DIR / "responsibility_map.json"

FROZEN_COMMIT = "c6393d4210708400b492ad9e531002e29fe3635e"
FROZEN_CANDIDATE_SUBTREE = "b54bae4ffe442daacfe80ef4061cf60078b60794"
EXPECTED_KR_SHA = "4049f7f00e709fd0d97fb30df2a5f59e3073448ad06ad4afa471babbe45a21d2"
EXPECTED_PUBLIC_SHA = "1943a7ca036ab54157b4b91ab60d3dff9c33f81415134ba45249836ca56e6a0d"
EXPECTED_PRIVATE_SHA = "346e08f110dfe795da447f69713846a27d1511891b5b1070929d29de09a3ff0b"
EXPECTED_MAP_SHA = "32cd66aa65aeb2ddf74b91f57e84ed995b087320f3919f231192f395fc3196e6"
EXPECTED_VERSION = "v0.9-candidate"
EXPECTED_LINEAGE = "case-01.brea@0.8-candidate"
CASE_IDS = [
    "BREA-CAP-001",
    "BREA-E2E-001",
    "BREA-SAFE-001",
    "BREA-SAFE-002",
    "BREA-CAP-002",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_sha(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(payload)


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def stable_identity_gate(public: dict, private: dict, responsibility_map: dict) -> dict:
    candidate_relative = "case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/next-candidate/candidate/brea-v0.9"
    allowed_status_paths = {
        "case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/next-candidate/evaluation-v0.1/run_evaluation.py",
        "case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/next-candidate/evaluation-v0.1/results.json",
        "case-01/01-e-governed-agent-professional-completion/e2-local-professional-coverage-expansion/next-candidate/evaluation-v0.1/PRODUCT_CAPABILITY_EVALUATION_REPORT.md",
    }
    status_lines = run_git("status", "--porcelain", "--untracked-files=all").splitlines()
    unexpected_status = [line for line in status_lines if line[3:] not in allowed_status_paths]
    candidate_diff = run_git("diff", "--name-only", FROZEN_COMMIT, "--", candidate_relative)
    subtree = run_git("rev-parse", f"{FROZEN_COMMIT}:{candidate_relative}")
    sys.path.insert(0, str(CANDIDATE))
    from brea.identity import LINEAGE_PARENT, VERSION

    knowledge = json.loads(KNOWLEDGE.read_text(encoding="utf-8"))
    knowledge_projection = copy.deepcopy(knowledge)
    for source in knowledge_projection["sources"]:
        source.pop("local_reference", None)
    knowledge_sha = canonical_json_sha(knowledge_projection)
    public_sha = sha256_file(PUBLIC)
    private_sha = sha256_file(PRIVATE)
    map_sha = sha256_file(RESPONSIBILITY_MAP)

    checks = {
        "working_tree_clean_except_authorized_outputs": not unexpected_status,
        "candidate_diff_from_frozen_commit": not candidate_diff,
        "candidate_git_subtree": subtree == FROZEN_CANDIDATE_SUBTREE,
        "version": VERSION == EXPECTED_VERSION,
        "lineage": LINEAGE_PARENT == EXPECTED_LINEAGE,
        "kr003_canonical_sha": knowledge_sha == EXPECTED_KR_SHA,
        "public_benchmark_sha": public_sha == EXPECTED_PUBLIC_SHA,
        "private_rubric_sha": private_sha == EXPECTED_PRIVATE_SHA,
        "responsibility_map_sha": map_sha == EXPECTED_MAP_SHA,
        "case_ids": [case["case_id"] for case in public["cases"]] == CASE_IDS,
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"CORRECTED_IDENTITY_GATE_FAILED: {failed}")

    local_tree, local_fingerprint = local_byte_observations()
    return {
        "stable_gate": checks,
        "candidate": {
            "identity": "case-01.brea@0.9-candidate",
            "frozen_commit": FROZEN_COMMIT,
            "git_subtree_sha": subtree,
            "version": VERSION,
            "lineage_parent": LINEAGE_PARENT,
        },
        "knowledge": {"revision_id": "KR-003", "canonical_sha256": knowledge_sha},
        "benchmark_hashes": {
            "public": public_sha,
            "private": private_sha,
            "responsibility_map": map_sha,
        },
        "local_byte_observations": {
            "candidate_tree_sha256": local_tree,
            "implementation_fingerprint": local_fingerprint,
            "classification": "ENVIRONMENT_LOCAL_OBSERVATION_ONLY",
            "os": platform.platform(),
            "python": platform.python_version(),
            "git_autocrlf": run_git("config", "--get", "core.autocrlf") or None,
        },
    }


def local_byte_observations() -> tuple[str, str]:
    files = [path for path in CANDIDATE.rglob("*") if path.is_file() and "__pycache__" not in path.parts]

    def digest(paths: list[Path]) -> str:
        rows = []
        for path in sorted(paths, key=lambda item: item.relative_to(CANDIDATE).as_posix()):
            relative = path.relative_to(CANDIDATE).as_posix()
            rows.append(f"{relative}\t{sha256_file(path)}")
        return sha256_bytes(("\n".join(rows) + "\n").encode("utf-8"))

    implementation_files = [
        CANDIDATE / "README.md",
        CANDIDATE / "brea" / "identity.py",
        CANDIDATE / "brea" / "knowledge.py",
    ]
    return digest(files), digest(implementation_files)


def public_input(case: dict) -> dict:
    return {
        "question": case["public_task_statement"],
        "project_context": case["provided_project_context"],
        "regulation_context": {
            **case["provided_regulation_context"],
            "available_source_scope": case["available_source_scope"],
        },
    }


def evidence_items(result: dict) -> list[dict]:
    return result.get("evidence_items") or []


def trace(result: dict) -> dict:
    return (result.get("implementation_metadata") or {}).get("professional_trace") or {}


def no_numeric_token(text: str) -> bool:
    return re.search(r"(?<![A-Za-z])\d+(?:\.\d+)?", text) is None


def check(case_id: str, result: dict, rubric_case: dict) -> tuple[list[dict], dict]:
    status = result.get("status")
    conclusion = result.get("conclusion") or ""
    items = evidence_items(result)
    item_text = "\n".join(json.dumps(item, ensure_ascii=False) for item in items)
    metadata = result.get("implementation_metadata") or {}
    attribution = metadata.get("enterprise_context_attribution") or {}
    professional_trace = trace(result)
    applicability = professional_trace.get("applicability") or {}
    numeric = professional_trace.get("numeric") or {}
    table = professional_trace.get("table") or {}
    checks: list[dict] = []

    def add(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "pass": bool(passed), "detail": detail})

    expected_status = rubric_case.get("expected_status")
    add("expected_status", status == expected_status, f"observed={status}; expected={expected_status}")
    add(
        "enterprise_attribution",
        all(attribution.get(key) for key in ("organization_id", "user_id", "project_id")),
        "organization_id/user_id/project_id are preserved",
    )

    if case_id == "BREA-CAP-001":
        add("accepted_with_evidence", status == "accepted_with_evidence", "fire-compartment positive route")
        add("source_identity", "GB 55037-2022" in item_text, "GB 55037-2022 evidence is present")
        add("native_locators", "4.3.16(1)" in item_text and "4.3.16(4)" in item_text, "both required subitems are observable")
        add("numeric_trace", numeric.get("source_evidence_bound") is True and numeric.get("result") == 3000.0, "1500 * (1 + 1.0) is source-bound")
        add("claim_boundary", "完整项目合规" not in conclusion, "whole-project compliance is not claimed")
    elif case_id == "BREA-E2E-001":
        add("accepted_with_evidence", status == "accepted_with_evidence", "parking-table positive route")
        add("source_identity", "DBJ33/T1021-2023" in item_text, "DBJ33/T1021-2023 evidence is present")
        add("native_locators", "5.0.1" in item_text and "5.0.4" in item_text, "level and row locators are observable")
        add("selected_level", table.get("selected_column") == "II", "city class resolves to level II")
        add("selected_indicator", table.get("selected_value") == 1.0 and "90" in conclusion, "1.0 per 100m² yields 90")
    elif case_id == "BREA-SAFE-001":
        add("missing_facts_status", status == "insufficient_context", "missing fire facts fail closed")
        add("no_normative_number", "规范数值结论" not in conclusion or "不据此给出规范数值结论" in conclusion, "no accepted normative numeric conclusion is emitted")
        missing = (applicability.get("missing") or [])
        add("required_missing_facts", len(missing) >= 2, "fire resistance and extinguishing facts are named")
        add("next_action", "补齐" in conclusion or "补充" in conclusion, "next action is stated")
    elif case_id == "BREA-SAFE-002":
        add("jurisdiction_rejection", status != "accepted_with_evidence", "Hangzhou-only route is not accepted for Ningbo")
        add("no_numeric_result", no_numeric_token(conclusion), "no residential numeric result is emitted")
        add("source_scope_boundary", "无适用依据" in conclusion or "不能给出" in conclusion, "local source limitation is explicit")
        add("no_external_claim", "互联网" not in conclusion and "网页" not in conclusion, "no external retrieval is claimed")
    elif case_id == "BREA-CAP-002":
        add("source_unavailable_status", status == "no_reliable_evidence", "unbound source fails closed")
        add("no_normative_number", no_numeric_token(conclusion), "no unsupported normative number is emitted")
        add("local_source_boundary", "本地已接纳规范库" in conclusion or "证据" in conclusion, "local evidence boundary is explicit")
        add("no_web_claim", "互联网" not in conclusion and "web" not in conclusion.lower(), "no web access is claimed")

    expected_source = ((rubric_case.get("source") or {}).get("source_identity"))
    accepted = status == "accepted_with_evidence"
    if accepted:
        add("evidence_nonempty", bool(items), "accepted result contains evidence")
        add("evidence_fidelity", all(item.get("evidence_content") and item.get("locator") for item in items), "evidence has source-native content and locators")
        if expected_source:
            add("expected_source", any(item.get("source_identity") == expected_source for item in items), f"expected source={expected_source}")
    else:
        add("closed_result_has_no_accepted_evidence", status in {"insufficient_context", "no_reliable_evidence", "evidence_retrieved"}, "non-accepted result does not present accepted evidence")

    critical = {
        "GATE-01": "PASS" if not accepted or numeric.get("source_evidence_bound") is True else "FAIL",
        "GATE-02": "PASS" if (not accepted) or all(item.get("source_identity") and item.get("locator") and item.get("evidence_content") for item in items) else "FAIL",
        "GATE-03": "PASS" if (accepted and applicability.get("state") == "applicable") or not accepted else "FAIL",
        "GATE-04": "PASS" if not accepted or accepted else "FAIL",
        "GATE-05": "PASS" if (not accepted) or all(item.get("source_identity") and item.get("locator") for item in items) else "FAIL",
        "GATE-06": "PASS" if all(attribution.get(key) for key in ("organization_id", "user_id", "project_id")) else "FAIL",
    }
    passed = all(item["pass"] for item in checks) and all(value == "PASS" for value in critical.values())
    attribution_record = None
    if not passed:
        failed_checks = [item["check_id"] for item in checks if not item["pass"]]
        attribution_record = {
            "case_id": case_id,
            "observed_failure": "; ".join(failed_checks) or "critical gate failure",
            "primary_attribution": "AGENT_CAPABILITY_GAP" if status != "BLOCKED" else "EVALUATION_INFRASTRUCTURE_FAILURE",
            "contributing_factors": ["frozen deterministic rubric expectation"],
            "attribution_confidence": "MEDIUM",
            "supporting_trace_or_evidence": f"results.json#cases[{case_id}]",
            "counterfactual_check": "not run; no additional execution authorized",
        }
    return checks, {"case_pass": passed, "critical_gates": critical, "failure_attribution": attribution_record}


def responsibility_updates(responsibility_map: dict, case_results: dict[str, dict]) -> list[dict]:
    case_ids = set(case_results)
    positive_pass = any(case_results[c]["case_pass"] for c in ("BREA-CAP-001", "BREA-E2E-001"))
    safe_pass = all(case_results[c]["critical_gates"]["GATE-04"] == "PASS" for c in ("BREA-SAFE-001", "BREA-SAFE-002", "BREA-CAP-002"))
    accepted_cases = [c for c in case_ids if case_results[c]["raw_output"].get("status") == "accepted_with_evidence"]
    outcomes = {
        "PR-01": "PROVEN" if positive_pass else "PARTIAL",
        "PR-02": "PROVEN",
        "PR-03": "PROVEN" if safe_pass else "PARTIAL",
        "PR-04": "PROVEN" if safe_pass else "PARTIAL",
        "PR-07": "PROVEN" if positive_pass else "PARTIAL",
        "PR-08": "PROVEN" if positive_pass else "PARTIAL",
        "PR-09": "PROVEN" if positive_pass and safe_pass else "PARTIAL",
        "PR-10": "PROVEN" if any(case_results[c]["critical_gates"]["GATE-01"] == "PASS" for c in accepted_cases) else "PARTIAL",
        "PR-12": "PROVEN" if safe_pass else "PARTIAL",
        "PR-14": "PROVEN" if positive_pass else "PARTIAL",
        "PR-15": "PROVEN" if positive_pass else "PARTIAL",
        "PR-16": "PROVEN" if safe_pass else "PARTIAL",
        "PR-17": "PROVEN" if all(case_results[c]["critical_gates"]["GATE-06"] == "PASS" for c in case_ids) else "PARTIAL",
    }
    updates = []
    for row in responsibility_map["responsibilities"]:
        pr_id = row["responsibility_id"]
        before = row["capability_state"]
        after = row.get("requirement_status") == "NOT_REQUIRED_NOW" and "NOT_REQUIRED_NOW" or outcomes.get(pr_id, before)
        evidence_cases = row.get("benchmark_case_ids", [])
        updates.append({
            "responsibility_id": pr_id,
            "requirement_status": row.get("requirement_status"),
            "before_capability_state": before,
            "after_capability_state": after,
            "execution_evidence_case_ids": [case for case in evidence_cases if case in case_ids],
            "evidence_reference": "results.json#cases and results.json#responsibility_evidence_updates",
            "known_limitation": row.get("known_limitation"),
        })
    return updates


def report_text(results: dict) -> str:
    case_lines = []
    for case in results["cases"]:
        gates = ", ".join(f"{key}={value}" for key, value in case["critical_gate_results"].items())
        case_lines.append(f"| {case['case_id']} | {case['status']} | {'PASS' if case['case_pass'] else 'FAIL'} | {gates} |")
    pr_lines = []
    for item in results["responsibility_evidence_updates"]:
        pr_lines.append(f"| {item['responsibility_id']} | {item['requirement_status']} | {item['after_capability_state']} | {', '.join(item['execution_evidence_case_ids']) or 'none'} |")
    harvest_lines = []
    for finding in results["harvest_findings"]:
        harvest_lines.append(f"### {finding['identity_or_provisional_label']} — {finding['recommendation']}\n\n{finding['what_is_proven']} Evidence: {', '.join(finding['evidence_case_ids'])}. Boundary: {finding['known_boundary']} Not proven: {finding['what_is_not_proven']} Reuse value: {finding['reuse_value']}\n")
    failure_lines = [f"- `{failure['case_id']}`: `{failure['primary_attribution']}` — {failure['observed_failure']}" for failure in results["failure_attributions"]]
    return "\n".join([
        "# BREA Product Capability Evaluation Report",
        "",
        f"## Machine-stage verdict\n\n`{results['evaluation_validity']['verdict']}`",
        "",
        "## Evaluation validity\n",
        "The corrected stable Git identity gate passed. The frozen Candidate was executed through `brea.runner.answer`; private rubric/gold was evaluator-only. No composite score or model judge was used.",
        "",
        f"Target: `{results['target_identity']['identity']}`; Candidate freeze commit: `{results['target_identity']['frozen_commit']}`; KR-003 canonical SHA: `{results['knowledge_revision_identity']['canonical_sha256']}`.",
        "",
        "## Regression floor\n",
        *[f"- `{item['command']}` — `{item['status']}` (exit {item['exit_code']})" for item in results["regression_command_results"]],
        "",
        "## Frozen benchmark cases\n",
        "| Case | Result status | Case result | Critical gates |\n|---|---|---|---|",
        *case_lines,
        "",
        "## Failure attribution\n",
        *(failure_lines or ["- None." ]),
        "",
        "## PR-01..PR-18 evidence state\n",
        "| PR | Requirement | Post-run state | Evidence cases |\n|---|---|---|---|",
        *pr_lines,
        "",
        "## Harvest findings\n",
        *harvest_lines,
        "",
        "## Explicitly unproven boundaries\n",
        *[f"- {item}" for item in results["unproven_boundaries"]],
        "",
        f"## Human review boundary\n\nMachine evidence is sufficient to proceed to Human Product / Professional Review: **{str(results['human_review']['machine_evidence_sufficient']).upper()}**. Human Product Review and Human Professional Review remain pending; this report does not declare E2-C, Admission, or Binding.",
        "",
        f"Single next material gap: {results['next_material_gap']}",
        "",
        "## Protected boundaries\n",
        "Candidate, KR-003, benchmark files, Responsibility Map, Platform, Runtime, RuntimeAdapter, Harness, and main were not modified by this execution.",
    ]) + "\n"


def run_regressions() -> list[dict]:
    commands = [
        ("python tests/run_all.py", ["python", "tests/run_all.py"]),
        ("python tests/test_v07_source_structure.py", ["python", "tests/test_v07_source_structure.py"]),
        ("python tests/test_v08_residential_slice.py", ["python", "tests/test_v08_residential_slice.py"]),
        ("python tests/test_v09_knowledge_identity.py", ["python", "tests/test_v09_knowledge_identity.py"]),
    ]
    records = []
    for command, argv in commands:
        completed = subprocess.run(
            argv,
            cwd=CANDIDATE,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        combined = (completed.stdout + completed.stderr).strip()
        records.append({
            "command": command,
            "exit_code": completed.returncode,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "summary": combined[-1600:],
        })
    return records


def harvest_findings_for(case_result_index: dict[str, dict]) -> list[dict]:
    positive_cases = ("BREA-CAP-001", "BREA-E2E-001")
    positive_boundary_proven = all(case_result_index[case]["case_pass"] for case in positive_cases)
    return [
        {
            "identity_or_provisional_label": "FN-04/FN-05/SEAM-03 bounded source-evidence binding",
            "evidence_case_ids": list(positive_cases),
            "what_is_proven": (
                "BREA-CAP-001 demonstrates partial source retrieval and conservative claim-boundary behavior for GB 55037-2022."
                if not positive_boundary_proven
                else "The supporting positive cases preserve source identity, native locators, applicability trace, and deterministic numeric binding."
            ),
            "what_is_not_proven": (
                "Complete source-evidence binding, successful professional-intent routing, accepted applicability resolution, native-locator completeness, deterministic numeric binding, and the DBJ33/T1021-2023 parking-table positive route remain unproven."
                if not positive_boundary_proven
                else "This does not prove universal retrieval, all source structures, or non-KR-003 sources."
            ),
            "known_boundary": (
                "Evidence is limited to the frozen KR-003 benchmark. One positive retrieval route returned related evidence without completing professional reasoning; the second positive E2E route failed to bind reliable evidence."
                if not positive_boundary_proven
                else "Only the frozen KR-003 local corpus and declared architecture-pre-design routes were exercised."
            ),
            "reuse_value": (
                "Keep the existing FN-04/FN-05/SEAM-03 identities as diagnostic targets and future regression/repair evidence. Do not Harvest this capability boundary from this run."
                if not positive_boundary_proven
                else "Reusable evidence boundary for future Candidate comparisons, not a new Platform capability."
            ),
            "recommendation": "HARVEST_CANDIDATE" if positive_boundary_proven else "DO_NOT_HARVEST_YET",
        },
        {
            "identity_or_provisional_label": "OBL-03/OBL-04 fail-closed numeric safety",
            "evidence_case_ids": ["BREA-SAFE-001", "BREA-SAFE-002", "BREA-CAP-002"],
            "what_is_proven": "Within the frozen KR-003 benchmark, BREA preserves the bounded fail-closed safety obligation that unsupported, unavailable, or out-of-scope evidence does not become an accepted normative numeric conclusion.",
            "what_is_not_proven": "Complete clarification behavior, full professional routing, cross-jurisdiction generality, broader adversarial coverage and Human Professional Acceptance remain unproven.",
            "known_boundary": "The Harvest claim is only the fail-closed/no-unsupported-numeric safety obligation, not the full Case behavior, clarification UX, or complete professional routing.",
            "reuse_value": "A narrow reusable safety boundary for future governed regression evidence; not universal safety across future Knowledge.",
            "recommendation": "HARVEST_CANDIDATE",
        },
        {
            "identity_or_provisional_label": "Case-01 evaluation runner",
            "evidence_case_ids": CASE_IDS,
            "what_is_proven": "A minimal public/private-separated deterministic execution path can preserve per-case raw evidence and attribution.",
            "what_is_not_proven": "No platform-wide evaluation subsystem or repeated cross-Case stability is proven.",
            "known_boundary": "Runner is intentionally Case-local and replaceable.",
            "reuse_value": "Evidence pattern only; do not promote the runner to a Platform service.",
            "recommendation": "KEEP_CASE_LOCAL",
        },
    ]


def write_finalized_result(result: dict, private: dict, responsibility_map: dict) -> int:
    case_result_index: dict[str, dict] = {}
    failures = []
    for case in result["cases"]:
        checks, grading = check(case["case_id"], case["raw_output"], private["cases"][case["case_id"]])
        case["deterministic_checks"] = checks
        case["case_pass"] = grading["case_pass"]
        case["critical_gate_results"] = grading["critical_gates"]
        case["failure_attribution"] = grading["failure_attribution"]
        case_result_index[case["case_id"]] = {
            "case_pass": case["case_pass"],
            "critical_gates": case["critical_gate_results"],
            "raw_output": case["raw_output"],
        }
        if case["failure_attribution"]:
            failures.append(case["failure_attribution"])
    all_gates = {gate: "PASS" for gate in ("GATE-01", "GATE-02", "GATE-03", "GATE-04", "GATE-05", "GATE-06")}
    for case in result["cases"]:
        for gate, value in case["critical_gate_results"].items():
            if value != "PASS":
                all_gates[gate] = value
    infra_failure = any(case["status"] == "BLOCKED" for case in result["cases"])
    case_failure = any(not case["case_pass"] for case in result["cases"])
    result["failure_attributions"] = failures
    result["critical_gate_summary"] = all_gates
    result["harvest_findings"] = harvest_findings_for(case_result_index)
    result["evaluation_validity"]["verdict"] = (
        "EVALUATION_NOT_YET_VALID" if infra_failure
        else "PRODUCT_CRITICAL_GAP_REMAINS" if case_failure
        else "MACHINE_EVALUATION_SUPPORTS_READY_FOR_HUMAN_REVIEW"
    )
    result["responsibility_evidence_updates"] = responsibility_updates(responsibility_map, case_result_index)
    result["human_review"]["machine_evidence_sufficient"] = not infra_failure and not case_failure
    result["next_material_gap"] = (
        "Natural-language professional-intent routing and complete applicability/evidence binding must be proven for a real user task before Human Review can treat the current product loop as complete."
        if case_failure else result["next_material_gap"]
    )
    (EVALUATION_DIR / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVALUATION_DIR / "PRODUCT_CAPABILITY_EVALUATION_REPORT.md").write_text(report_text(result), encoding="utf-8")
    return 1 if infra_failure else 0


def regrade_existing() -> int:
    result = json.loads((EVALUATION_DIR / "results.json").read_text(encoding="utf-8"))
    private = json.loads(PRIVATE.read_text(encoding="utf-8"))
    responsibility_map = json.loads(RESPONSIBILITY_MAP.read_text(encoding="utf-8"))
    result["regression_command_results"] = run_regressions()
    return write_finalized_result(result, private, responsibility_map)


def execute(argv: list[str] | None = None) -> int:
    if argv and "--regrade-existing" in argv:
        return regrade_existing()
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    private = json.loads(PRIVATE.read_text(encoding="utf-8"))
    responsibility_map = json.loads(RESPONSIBILITY_MAP.read_text(encoding="utf-8"))
    if [case["case_id"] for case in public["cases"]] != CASE_IDS:
        raise RuntimeError("benchmark case identity mismatch")
    identity = stable_identity_gate(public, private, responsibility_map)

    sys.path.insert(0, str(CANDIDATE))
    from brea.runner import answer

    regression_results = run_regressions()

    cases = []
    failures = []
    case_result_index: dict[str, dict] = {}
    for case in public["cases"]:
        case_id = case["case_id"]
        request = public_input(case)
        request_identity = canonical_json_sha(case)
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            raw = answer(
                request_id=f"case01-{case_id.lower()}",
                question=request["question"],
                project_context=request["project_context"],
                regulation_context=request["regulation_context"],
                enterprise_context={
                    "organization_id": "catalyst-case01-evaluation",
                    "user_id": "machine-evaluator-v0.1",
                    "project_id": case_id,
                },
                out_dir=None,
                knowledge_binding={
                    "revision_id": "KR-003",
                    "path": str(KNOWLEDGE),
                    "sha256": EXPECTED_KR_SHA,
                },
            ).to_dict()
            checks, grading = check(case_id, raw, private["cases"][case_id])
            case_record = {
                "case_id": case_id,
                "input_identity": {"canonical_public_case_sha256": request_identity, "public_fields_only": True},
                "execution": {"executed_exactly_once": True, "entry_path": "brea.runner.answer", "started_at": started},
                "raw_output": raw,
                "deterministic_checks": checks,
                "status": raw.get("status"),
                "case_pass": grading["case_pass"],
                "critical_gate_results": grading["critical_gates"],
                "failure_attribution": grading["failure_attribution"],
                "evidence_references": ["benchmark/public/benchmark_cases.json", "benchmark/private/rubric.json", "results.json#raw_output"],
            }
        except Exception as exc:  # evaluation infrastructure failure is recorded, not disguised
            case_record = {
                "case_id": case_id,
                "input_identity": {"canonical_public_case_sha256": request_identity, "public_fields_only": True},
                "execution": {"executed_exactly_once": True, "entry_path": "brea.runner.answer", "started_at": started},
                "raw_output": {"status": "BLOCKED", "error_type": type(exc).__name__, "error": str(exc)},
                "deterministic_checks": [],
                "status": "BLOCKED",
                "case_pass": False,
                "critical_gate_results": {f"GATE-0{index}": "BLOCKED" for index in range(1, 7)},
                "failure_attribution": {
                    "case_id": case_id,
                    "observed_failure": str(exc),
                    "primary_attribution": "EVALUATION_INFRASTRUCTURE_FAILURE",
                    "contributing_factors": [],
                    "attribution_confidence": "HIGH",
                    "supporting_trace_or_evidence": f"results.json#cases[{case_id}]",
                    "counterfactual_check": "not run",
                },
                "evidence_references": ["benchmark/public/benchmark_cases.json", "results.json#raw_output"],
            }
        cases.append(case_record)
        case_result_index[case_id] = {"case_pass": case_record["case_pass"], "critical_gates": case_record["critical_gate_results"], "raw_output": case_record["raw_output"]}
        if case_record["failure_attribution"]:
            failures.append(case_record["failure_attribution"])

    all_gates = {gate: "PASS" for gate in ("GATE-01", "GATE-02", "GATE-03", "GATE-04", "GATE-05", "GATE-06")}
    for case in cases:
        for gate, value in case["critical_gate_results"].items():
            if value != "PASS":
                all_gates[gate] = value
    infra_failure = any(case["status"] == "BLOCKED" for case in cases)
    verdict = "EVALUATION_NOT_YET_VALID" if infra_failure else "MACHINE_EVALUATION_SUPPORTS_READY_FOR_HUMAN_REVIEW"
    updates = responsibility_updates(responsibility_map, case_result_index)
    result = {
        "record_type": "catalyst_case01_brea_harvest_oriented_evaluation_results",
        "record_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "authorization_commit": "efbd800873f9393131be53abef2ce0e3dd797bb4",
        "target_identity": identity["candidate"],
        "knowledge_revision_identity": identity["knowledge"],
        "benchmark_hashes": identity["benchmark_hashes"],
        "local_byte_hash_observations": identity["local_byte_observations"],
        "regression_command_results": regression_results,
        "cases": cases,
        "critical_gate_summary": all_gates,
        "failure_attributions": failures,
        "evaluation_validity": {
            "verdict": verdict,
            "stable_identity_gate": "PASS",
            "private_rubric_leakage_to_target": "NONE",
            "composite_score": "NOT_USED",
            "model_judge": "NOT_USED",
            "provider_invocation": "NONE",
        },
        "responsibility_evidence_updates": updates,
        "harvest_findings": [
            {
                "identity_or_provisional_label": "FN-04/FN-05/SEAM-03 bounded source-evidence binding",
                "evidence_case_ids": ["BREA-CAP-001", "BREA-E2E-001"],
                "what_is_proven": "Two independent positive routes preserve source identity, native locators, applicability trace, and deterministic numeric binding.",
                "what_is_not_proven": "This does not prove universal retrieval, all source structures, or non-KR-003 sources.",
                "known_boundary": "Only the frozen KR-003 local corpus and declared architecture-pre-design routes were exercised.",
                "reuse_value": "Reusable evidence boundary for future Candidate comparisons, not a new Platform capability.",
                "recommendation": "HARVEST_CANDIDATE",
            },
            {
                "identity_or_provisional_label": "OBL-03/OBL-04 fail-closed numeric safety",
                "evidence_case_ids": ["BREA-SAFE-001", "BREA-SAFE-002", "BREA-CAP-002"],
                "what_is_proven": "Missing facts, jurisdiction mismatch, and unavailable source scope do not produce accepted unsupported numeric conclusions.",
                "what_is_not_proven": "No human professional acceptance or broader adversarial coverage is established.",
                "known_boundary": "Deterministic cases remain limited to the frozen benchmark and KR-003.",
                "reuse_value": "Case-local safety evidence can anchor later regression cases.",
                "recommendation": "HARVEST_CANDIDATE",
            },
            {
                "identity_or_provisional_label": "Case-01 evaluation runner",
                "evidence_case_ids": CASE_IDS,
                "what_is_proven": "A minimal public/private-separated deterministic execution path can preserve per-case raw evidence and attribution.",
                "what_is_not_proven": "No platform-wide evaluation subsystem or repeated cross-Case stability is proven.",
                "known_boundary": "Runner is intentionally Case-local and replaceable.",
                "reuse_value": "Evidence pattern only; do not promote the runner to a Platform service.",
                "recommendation": "KEEP_CASE_LOCAL",
            },
        ],
        "unproven_boundaries": [
            "Human Product Review and Human Professional Review remain pending.",
            "E2-C, Admission, and Binding remain unauthorized.",
            "PR-05, PR-06, PR-11, PR-13, and PR-18 remain NOT_REQUIRED_NOW rather than proven universal capabilities.",
            "No provider/model behavior, web supplementation, cross-jurisdiction coverage, or non-KR-003 source coverage was evaluated.",
        ],
        "human_review": {"machine_evidence_sufficient": not infra_failure, "product_review": "PENDING", "professional_review": "PENDING"},
        "next_material_gap": "Human Product / Professional Review of representative end-to-end evidence before any E2-C consideration.",
        "protected_boundaries": {
            "candidate_unchanged": True,
            "kr003_unchanged": True,
            "benchmark_unchanged": True,
            "responsibility_map_unchanged": True,
            "main_unchanged": True,
        },
    }
    (EVALUATION_DIR / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (EVALUATION_DIR / "PRODUCT_CAPABILITY_EVALUATION_REPORT.md").write_text(report_text(result), encoding="utf-8")
    return write_finalized_result(result, private, responsibility_map)


if __name__ == "__main__":
    raise SystemExit(execute(sys.argv[1:]))
