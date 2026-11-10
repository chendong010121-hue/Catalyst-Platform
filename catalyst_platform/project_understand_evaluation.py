"""Bounded project-result profile on the existing Evaluation adapter and Gate.

Source bytes, locators, read receipts, closure and finite synthetic assertions
are separate measurements. Quoting actual code never proves prose entailment.
No model, executor, registry, enterprise Gold or activation authority lives here.
"""
from __future__ import annotations

import copy
import hashlib

from .evaluation_adapter import OWNER_BLOB, check_health, run_evaluation

DIMENSIONS = ["STRUCTURE_VALIDITY", "SOURCE_IDENTITY", "SOURCE_SUPPORT",
              "QUESTION_CLOSURE", "COVERAGE_INTEGRITY", "SEMANTIC_QUALITY", "TASK_SUCCESS"]
QUESTION_STATUSES = {"SUPPORTED", "PARTIALLY_SUPPORTED", "CONDITIONAL", "EXPLICITLY_UNRESOLVED"}


def project_profile():
    """A method-local profile, retaining the unchanged adapter/Gate owner."""
    return {"id": "project-understand-offline", "version": "0.1.0",
            "owner": "capability-evaluation-v3", "owner_blob": OWNER_BLOB,
            "dimensions": list(DIMENSIONS), "objective": "TASK_SUCCESS",
            "hard_dimensions": [d for d in DIMENSIONS if d != "SEMANTIC_QUALITY"],
            "scope": "Independent finite synthetic controls and source identity; real semantic quality NOT_EVALUATED"}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dimension(ok):
    return {"status": "PASS" if ok is True else "FAIL" if ok is False else "NOT_EVALUATED",
            "value": None if ok is None else float(ok)}


def _rows(value):
    return value if isinstance(value, list) else []


def _index(rows, key, faults):
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(key), str) or not row[key] or row[key] in result:
            faults.append("MISSING_OR_DUPLICATE_" + key.upper())
        else:
            result[row[key]] = row
    return result


def _strings(value):
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value) and len(set(value)) == len(value)


def project_grader(observation, gold):
    """Consume an independently frozen packet; never repair the producer result.

    gold.sources contains UTF-8 texts and their independently pinned SHA-256.
    Optional gold.read_source_ids pins actual Host read receipts independently.
    Only INDEPENDENT_PROJECT_SYNTHETIC enables exact finite claim assertions.
    INDEPENDENT_SOURCE_IDENTITY_ONLY deliberately leaves support unmeasured.
    """
    finite = gold.get("basis") == "INDEPENDENT_PROJECT_SYNTHETIC"
    if not finite and gold.get("basis") != "INDEPENDENT_SOURCE_IDENTITY_ONLY":
        raise ValueError("No independent project evaluation basis")
    structure, identity, support, closure, coverage = [], [], [], [], []
    analysis = observation.get("analysis")
    if not isinstance(analysis, dict):
        analysis = {}
        structure.append("MISSING_ANALYSIS")
    for key in ("questions", "claims", "dependencies", "reuse_suggestions", "unknowns"):
        if not isinstance(analysis.get(key), list):
            structure.append("MISSING_" + key.upper())
    if analysis.get("schema_version") != "project-understanding.v1":
        structure.append("UNKNOWN_SCHEMA")
    if type(analysis.get("analysis_finished")) is not bool:
        structure.append("INVALID_FINISHED_FLAG")
    if analysis.get("decision_readiness") not in {"READY_FOR_REVIEW", "NEEDS_EVIDENCE", "BLOCKED"}:
        structure.append("INVALID_READINESS")
    for key in ("requested_depth", "achieved_depth"):
        if type(analysis.get(key)) is not int or not 0 <= analysis[key] <= 3:
            structure.append("INVALID_DEPTH")
    if not structure and analysis["achieved_depth"] > analysis["requested_depth"]:
        structure.append("DEPTH_EXCEEDS_REQUEST")
    for key in ("objective", "object_type", "requested_depth"):
        if key in gold and analysis.get(key) != gold[key]:
            closure.append("WRONG_" + key.upper())
    for key in ("source_manifest_sha256", "method_identity"):
        if key in gold and observation.get(key, analysis.get(key)) != gold[key]:
            identity.append("WRONG_" + key.upper())
    sources = _index(_rows(gold.get("sources")), "source_id", identity)
    for source in sources.values():
        if not isinstance(source.get("text"), str) or _sha(source["text"]) != source.get("sha256"):
            raise ValueError("Independent source corpus identity mismatch")
    if not sources:
        identity.append("NO_INDEPENDENT_SOURCES")
    evidence = _index(_rows(observation.get("evidence")), "evidence_id", structure)
    reads = _index(_rows(observation.get("source_reads")), "source_id", coverage)
    for source_id, receipt in reads.items():
        if source_id not in sources or receipt.get("sha256") != sources[source_id]["sha256"]:
            identity.append("READ_SOURCE_IDENTITY_MISMATCH")
    if "read_source_ids" in gold and set(reads) != set(gold["read_source_ids"]):
        coverage.append("INDEPENDENT_READ_RECEIPT_MISMATCH")
    evidence_checks = []
    for evidence_id, item in evidence.items():
        source = sources.get(item.get("source_id"))
        quote, start, end = item.get("quote"), item.get("start_line"), item.get("end_line")
        valid = source is not None and isinstance(quote, str) and bool(quote)
        valid = valid and item.get("source_sha256") == source["sha256"] and item.get("span_sha256") == _sha(quote)
        if source:
            lines = source["text"].splitlines(keepends=True)
            valid = valid and type(start) is int and type(end) is int and 1 <= start <= end <= len(lines)
            if valid:
                valid = quote in "".join(lines[start - 1:end])
        if not valid:
            identity.append("SOURCE_OR_LOCATOR_OR_QUOTE_MISMATCH")
        if item.get("source_id") not in reads:
            coverage.append("EVIDENCE_FROM_UNREAD_SOURCE")
        evidence_checks.append({"evidence_id": evidence_id, "source_id": item.get("source_id"),
                                "identity_status": "PASS" if valid else "FAIL",
                                "has_read_receipt": item.get("source_id") in reads})
    declared_coverage = analysis.get("coverage")
    if not isinstance(declared_coverage, dict):
        coverage.append("MISSING_COVERAGE")
        declared_coverage = {}
    read_ids = declared_coverage.get("read_source_ids")
    unread_ids = declared_coverage.get("unread_source_ids")
    if not _strings(read_ids) or not _strings(unread_ids):
        coverage.append("INVALID_COVERAGE_IDS")
    elif set(read_ids) != set(reads) or set(unread_ids) != set(sources) - set(reads) or set(read_ids) & set(unread_ids):
        coverage.append("COVERAGE_DOES_NOT_MATCH_READ_RECEIPTS")
    claims = _index(_rows(analysis.get("claims")), "claim_id", structure)
    for claim in claims.values():
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            structure.append("EMPTY_CLAIM")
        refs = claim.get("evidence_ids")
        if not _strings(refs) or any(ref not in evidence for ref in refs):
            structure.append("UNKNOWN_CLAIM_EVIDENCE")
        if not isinstance(claim.get("conditions"), list) or not isinstance(claim.get("exceptions"), list) or not claim.get("support_mode"):
            structure.append("MISSING_CLAIM_QUALIFIERS")
    questions = _index(_rows(analysis.get("questions")), "question_id", structure)
    required = set(gold.get("critical_question_ids", []))
    if required - set(questions):
        closure.append("MISSING_CRITICAL_QUESTION")
    for question_id, question in questions.items():
        if type(question.get("critical")) is not bool or question.get("status") not in QUESTION_STATUSES:
            structure.append("INVALID_QUESTION")
        if question_id in required and question.get("critical") is not True:
            closure.append("CRITICAL_QUESTION_DOWNGRADED")
        refs = question.get("claim_ids")
        if not _strings(refs) or any(ref not in claims for ref in refs):
            structure.append("UNKNOWN_QUESTION_CLAIM")
        if question.get("status") == "SUPPORTED" and (not refs or any(not claims.get(ref, {}).get("evidence_ids") for ref in refs)):
            closure.append("SUPPORTED_QUESTION_WITHOUT_EVIDENCE")
        if (question.get("critical") or question_id in required) and question.get("status") != "SUPPORTED":
            closure.append("UNRESOLVED_CRITICAL_QUESTION")
    if analysis.get("analysis_finished") is not True:
        closure.append("ANALYSIS_NOT_FINISHED")
    if analysis.get("decision_readiness") != "READY_FOR_REVIEW":
        closure.append("DECISION_NOT_READY")
    claim_checks = []
    if finite:
        expected = gold.get("claim_support", {})
        if not expected:
            raise ValueError("Finite independent claim support contract absent")
        if set(claims) != set(expected):
            support.append("FINITE_CLAIM_SET_DIFFERS")
        for claim_id, contract in expected.items():
            before = len(support)
            claim = claims.get(claim_id, {})
            for key in ("text", "evidence_ids", "conditions", "exceptions", "support_mode"):
                if claim.get(key) != contract.get(key):
                    support.append("FINITE_CLAIM_" + key.upper() + "_DIFFERS")
            spans = contract.get("evidence_spans", {})
            if set(spans) != set(contract.get("evidence_ids", [])):
                raise ValueError("Finite independent source-span contract absent")
            for evidence_id, span in spans.items():
                if any(evidence.get(evidence_id, {}).get(key) != span.get(key)
                       for key in ("source_id", "start_line", "end_line", "quote")):
                    support.append("FINITE_CLAIM_SOURCE_SPAN_DIFFERS")
            claim_checks.append({"claim_id": claim_id, "support_status": "FAIL" if len(support) != before else "PASS",
                                 "basis": "EXACT_FINITE_SYNTHETIC_ASSERTION", "faults": support[before:],
                                 "evidence_ids": claim.get("evidence_ids", [])})
        for claim_id in set(claims) - set(expected):
            claim_checks.append({"claim_id": claim_id, "support_status": "FAIL", "basis": "NO_INDEPENDENT_FINITE_ASSERTION"})
    else:
        claim_checks = [{"claim_id": claim_id, "support_status": "NOT_EVALUATED",
                         "basis": "NO_INDEPENDENT_PROSE_ENTAILMENT_ORACLE", "evidence_ids": claim.get("evidence_ids", [])}
                        for claim_id, claim in claims.items()]
    faults = list(dict.fromkeys(structure + identity + support + closure + coverage))
    success = False if faults else True if finite else None
    dimensions = {"STRUCTURE_VALIDITY": _dimension(not structure), "SOURCE_IDENTITY": _dimension(not identity),
                  "SOURCE_SUPPORT": _dimension(not support if finite else None), "QUESTION_CLOSURE": _dimension(not closure),
                  "COVERAGE_INTEGRITY": _dimension(not coverage), "SEMANTIC_QUALITY": _dimension(None),
                  "TASK_SUCCESS": _dimension(success)}
    return {"task_success": success, "dimensions": dimensions, "critical_faults": faults,
            "failure_class": "PROJECT_CONTRACT_FAILURE" if faults else None if finite else "SEMANTIC_NOT_EVALUATED",
            "measurement_scope": "Mechanical identity/closure and explicitly finite synthetic assertions; source presence is not entailment",
            "source_support_basis": gold["basis"], "claim_checks": claim_checks, "evidence_checks": evidence_checks,
            "semantic_status": "NOT_EVALUATED", "formal_owner_admission": False}


def project_health_probes():
    """Private exact synthetic health controls, never supplied to a producer."""
    text = "def increment(n):\n    return n + 1\n"
    sha = _sha(text)
    claim = {"claim_id": "health-c", "text": "increment returns n + 1", "evidence_ids": ["health-e"],
             "conditions": [], "exceptions": [], "support_mode": "SOURCE_EXPLICIT"}
    analysis = {"schema_version": "project-understanding.v1", "objective": "Inspect increment", "object_type": "Tool",
                "requested_depth": 1, "achieved_depth": 1, "analysis_finished": True, "decision_readiness": "READY_FOR_REVIEW",
                "questions": [{"question_id": "health-q", "critical": True, "status": "SUPPORTED", "claim_ids": ["health-c"]}],
                "claims": [claim], "dependencies": [], "reuse_suggestions": [], "unknowns": [],
                "coverage": {"read_source_ids": ["health-s"], "unread_source_ids": []}}
    good = {"analysis": analysis, "source_reads": [{"source_id": "health-s", "sha256": sha}],
            "evidence": [{"evidence_id": "health-e", "source_id": "health-s", "source_sha256": sha,
                          "start_line": 1, "end_line": 2, "quote": text, "span_sha256": sha}]}
    gold = {"basis": "INDEPENDENT_PROJECT_SYNTHETIC", "objective": analysis["objective"], "critical_question_ids": ["health-q"],
            "sources": [{"source_id": "health-s", "sha256": sha, "text": text}], "read_source_ids": ["health-s"],
            "claim_support": {"health-c": {**{k: claim[k] for k in ("text", "evidence_ids", "conditions", "exceptions", "support_mode")},
                "evidence_spans": {"health-e": {k: good["evidence"][0][k] for k in ("source_id", "start_line", "end_line", "quote")}}}}}
    bad = copy.deepcopy(good)
    bad["evidence"][0]["quote"] = "tampered"
    wrong = copy.deepcopy(good)
    wrong["analysis"]["questions"][0]["status"] = "EXPLICITLY_UNRESOLVED"
    return [{"id": name, "basis": "INDEPENDENT", "observation": packet, "gold": copy.deepcopy(gold), "expected": expected}
            for name, packet, expected in [("KNOWN_GOOD", good, True), ("KNOWN_BAD", bad, False), ("NULL", {}, False),
                                           ("WRONG_QUESTION_CONFIDENT", wrong, False),
                                           ("BROKEN_TASK_OR_INFRA_ERROR", {"execution_error": "CONTROL_UNAVAILABLE"}, "INFRASTRUCTURE_ERROR")]]


def run_project_evaluation(cases, entry, destination, *, target_identity, mode="BENCHMARK_CASE"):
    """Use the existing frozen-artifact/health path; entry receives public only."""
    profile = project_profile()
    health = check_health(profile, project_grader, project_health_probes())
    return run_evaluation(profile, cases, entry, project_grader, destination, health=health,
                          target_identity=target_identity, mode=mode)
