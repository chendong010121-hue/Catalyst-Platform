"""D2 — D2-T01..T16 test suite (Stage Spec §12). Stdlib only.

Runs as: python tests/run_d2_tests.py [--regression-detail <text>]
Writes evidence/D2_TEST_RESULTS.log (+ .txt committed twin).
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(r"E:\试验场地\Agent Harness")
D2_ROOT = REPO_ROOT / "case-01" / "01-d-governed-agent-admission-binding" / "d2-local-admission-binding"
CANDIDATE = REPO_ROOT / "case-01" / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"
FIXTURES = CANDIDATE / "tests" / "fixtures" / "requests"

for p in (str(REPO_ROOT), str(D2_ROOT / "implementation"), str(CANDIDATE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import d2_pipeline as P  # noqa: E402
from governance_agent import (  # noqa: E402
    EXTENSION_NAME,
    GovernanceAgentError,
    attribute_trace,
    parse_governance_agent,
    validate_against_records,
)
from platform_standard.models import Result, TraceEvent  # noqa: E402

RESULTS: list[dict] = []


def report(test_id: str, description: str, passed: bool, detail: str) -> None:
    RESULTS.append({
        "test_id": test_id,
        "description": description,
        "passed": bool(passed),
        "detail": detail,
    })
    print(f"[{'PASS' if passed else 'FAIL'}] {test_id} — {description}\n    {detail}")


def expect_raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except (GovernanceAgentError, ValueError):
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def load_fixture(case: str) -> dict:
    data = json.loads((FIXTURES / f"{case}.json").read_text(encoding="utf-8"))
    return data["request"]


# ---------------------------------------------------------------------------
# D2-T01 valid gates -> Admission Record ADMITTED
# ---------------------------------------------------------------------------

def test_t01(regression_detail: str) -> None:
    gates = P.evaluate_gates(regression_ok=True, regression_detail=regression_detail)
    record = P.build_admission_record(gates)
    ok = gates["all_pass"] and record["admission_status"] == "ADMITTED"
    report("D2-T01",
        "valid gates -> Admission Record ADMITTED",
        ok,
        f"all_pass={gates['all_pass']} admission_status={record['admission_status']}",
    )


# ---------------------------------------------------------------------------
# D2-T02 wrong Governed Definition SHA -> REJECTED
# ---------------------------------------------------------------------------

def test_t02(tmp: Path) -> None:
    bad_definition = tmp / "BAD_DEFINITION.md"
    bad_definition.write_text("not the accepted definition", encoding="utf-8")
    gates = P.evaluate_gates(
        regression_ok=True, definition=bad_definition,
    )
    record = P.build_admission_record(gates)
    ok = gates["G-A01"]["status"] == "FAIL" and record["admission_status"] == "REJECTED"
    report("D2-T02",
        "wrong Governed Definition SHA -> REJECTED",
        ok,
        f"G-A01={gates['G-A01']['status']} admission_status={record['admission_status']}",
    )


# ---------------------------------------------------------------------------
# D2-T03 missing required Formation Evidence -> REJECTED
# ---------------------------------------------------------------------------

def test_t03(tmp: Path) -> None:
    empty_evidence = tmp / "empty_evidence"
    empty_evidence.mkdir()
    gates = P.evaluate_gates(regression_ok=True, evidence_dir=empty_evidence)
    record = P.build_admission_record(gates)
    ok = gates["G-A02"]["status"] == "FAIL" and record["admission_status"] == "REJECTED"
    report("D2-T03",
        "missing required Formation Evidence -> REJECTED",
        ok,
        f"G-A02={gates['G-A02']['status']} admission_status={record['admission_status']}",
    )


# ---------------------------------------------------------------------------
# D2-T04 implementation fingerprint mismatch -> binding rejected
# ---------------------------------------------------------------------------

def test_t04(admission: dict, fingerprint: dict) -> None:
    bad = dict(fingerprint)
    bad["candidate_tree_sha256"] = "0" * 64
    binding = P.build_binding_record(admission, bad)
    rejected = expect_raises(P.validate_binding, binding, admission, fingerprint)
    report("D2-T04",
        "implementation fingerprint mismatch -> binding rejected",
        rejected,
        "validate_binding raised on candidate_tree_sha256 mismatch" if rejected else "validate_binding did NOT fail closed",
    )


# ---------------------------------------------------------------------------
# D2-T05 unknown Agent version -> no binding / fail closed
# ---------------------------------------------------------------------------

def test_t05(admission: dict, binding: dict) -> None:
    payload = {
        "agent_id": P.AGENT_ID,
        "agent_version": "0.9-unknown",
        "admission_ref": admission["admission_ref"],
        "binding_ref": binding["binding_id"],
    }
    ok = expect_raises(validate_against_records, payload, admission, binding)
    report("D2-T05",
        "unknown Agent version -> no binding / fail closed",
        ok,
        "validate_against_records raised on unknown agent_version" if ok else "unknown agent_version was accepted",
    )


# ---------------------------------------------------------------------------
# D2-T06 missing governance.agent on governed execution -> fail closed
# ---------------------------------------------------------------------------

def test_t06() -> None:
    invocation = P.make_governed_invocation(load_fixture("T-C01"), include_governance=False)
    ok = expect_raises(parse_governance_agent, invocation)
    report("D2-T06",
        "missing governance.agent on governed execution -> fail closed",
        ok,
        "parse_governance_agent raised" if ok else "missing governance.agent accepted",
    )


# ---------------------------------------------------------------------------
# D2-T07 governance.agent payload mismatches Admission/Binding -> fail closed
# ---------------------------------------------------------------------------

def test_t07(admission: dict, binding: dict) -> None:
    payload = {
        "agent_id": "case-01.other",
        "agent_version": P.AGENT_VERSION,
        "admission_ref": admission["admission_ref"],
        "binding_ref": binding["binding_id"],
    }
    ok = expect_raises(validate_against_records, payload, admission, binding)
    report("D2-T07",
        "governance.agent payload mismatches Admission/Binding -> fail closed",
        ok,
        "validate_against_records raised on agent_id mismatch" if ok else "payload mismatch accepted",
    )


# ---------------------------------------------------------------------------
# D2-T08 governance.agent in Invocation.context.extensions -> fail closed
# ---------------------------------------------------------------------------

def test_t08() -> None:
    invocation = P.make_governed_invocation(load_fixture("T-C01"), governance_in_context=True)
    ok = expect_raises(parse_governance_agent, invocation)
    report("D2-T08",
        "governance.agent in Invocation.context.extensions -> fail closed (ambiguous authority)",
        ok,
        "parse_governance_agent raised on context.extensions presence" if ok else "context.extensions governance.agent accepted",
    )


# ---------------------------------------------------------------------------
# D2-T09 agent_id != execution_capability_id, explicit semantic mapping
# ---------------------------------------------------------------------------

def test_t09(admission: dict, binding: dict) -> None:
    distinct = P.AGENT_ID != P.EXECUTION_CAPABILITY_ID
    binding_maps = (
        binding["execution_capability_id"] == P.EXECUTION_CAPABILITY_ID
        and binding["agent_id"] == P.AGENT_ID
    )
    report("D2-T09",
        "agent_id != execution_capability_id and semantic mapping is explicit",
        distinct and binding_maps,
        f"agent={P.AGENT_ID} != execution_capability={P.EXECUTION_CAPABILITY_ID}; binding documents both ({binding_maps})",
    )


# ---------------------------------------------------------------------------
# D2-T10 wrong execution capability binding -> fail closed
# ---------------------------------------------------------------------------

def test_t10(admission: dict, fingerprint: dict) -> None:
    binding = P.build_binding_record(admission, fingerprint)
    binding["execution_capability_id"] = "case-01.brea.run"
    ok = expect_raises(P.validate_binding, binding, admission, fingerprint)
    report("D2-T10",
        "wrong execution capability binding -> fail closed",
        ok,
        "validate_binding raised on wrong execution_capability_id" if ok else "wrong execution capability accepted",
    )


# ---------------------------------------------------------------------------
# D2-T11 conflicting TraceEvent governance.agent attribution -> fail closed
# ---------------------------------------------------------------------------

def test_t11() -> None:
    event = TraceEvent(
        id="ev_conflict", trace_id="t", event_type="invocation.started",
        timestamp="2026-01-01T00:00:00Z", subject_id="s",
        extensions={EXTENSION_NAME: {"version": "0.1", "required": False,
                                     "payload": {"agent_id": "case-01.other", "agent_version": "x",
                                                 "admission_ref": "a", "binding_ref": "b"}}},
    )
    payload = {"agent_id": P.AGENT_ID, "agent_version": P.AGENT_VERSION,
               "admission_ref": "a", "binding_ref": "b"}
    ok = expect_raises(attribute_trace, (event,), payload)
    report("D2-T11",
        "conflicting TraceEvent governance.agent attribution -> fail closed",
        ok,
        "attribute_trace raised on conflicting trace attribution" if ok else "conflicting attribution overwritten",
    )


# ---------------------------------------------------------------------------
# D2-T12 result/trace/artifact provenance cannot be linked -> fail closed
# ---------------------------------------------------------------------------

def test_t12(admission: dict, binding: dict) -> None:
    payload = {
        "agent_id": P.AGENT_ID,
        "agent_version": P.AGENT_VERSION,
        "admission_ref": admission["admission_ref"],
        "binding_ref": binding["binding_id"],
    }
    broken_result = Result(
        id="r_broken", invocation_id="inv_OTHER", status="success",
        output={"request_id": "T-C01"}, artifacts=(),
    )
    events = (
        TraceEvent(id="e1", trace_id="trace_x", event_type="invocation.started",
                   timestamp="2026-01-01T00:00:00Z", subject_id="inv_x",
                   extensions={EXTENSION_NAME: {"version": "0.1", "required": False, "payload": payload}}),
    )
    class _Inv:  # minimal stand-in with the fields verify_provenance needs
        id = "inv_x"
        capability_id = P.EXECUTION_CAPABILITY_ID
        capability_version = P.EXECUTION_CAPABILITY_VERSION
        trace_id = "trace_x"
    ok = expect_raises(P.verify_provenance, _Inv(), broken_result, events, payload, admission, binding)
    report("D2-T12",
        "result/trace/artifact provenance cannot be linked -> fail closed",
        ok,
        "verify_provenance raised on unlinked invocation_id" if ok else "unlinked provenance accepted",
    )


# ---------------------------------------------------------------------------
# D2-T13 enterprise.identity conflicts admitted enterprise context -> fail closed
# ---------------------------------------------------------------------------

def test_t13(admission: dict, binding: dict, adapter) -> None:
    invocation = P.make_governed_invocation(
        load_fixture("T-C01"),
        include_enterprise_identity=True,
        enterprise_payload={"organization_id": "org-other-999", "user_id": "user-pilot-001"},
    )
    ok = expect_raises(P.execute_governed, invocation, admission, binding, adapter)
    report("D2-T13",
        "enterprise.identity conflicts admitted enterprise context -> fail closed",
        ok,
        "execute_governed raised on enterprise.identity conflict" if ok else "conflicting enterprise.identity accepted",
    )


# ---------------------------------------------------------------------------
# D2-T14/T15/T16 Platform-bound whole-Agent cases (T-C01/02/03)
# ---------------------------------------------------------------------------

def platform_bound_case(case: str, admission: dict, binding: dict, adapter) -> dict:
    request = load_fixture(case)
    invocation = P.make_governed_invocation(
        request,
        invocation_id=f"inv_d2_{case}",
        trace_id=f"trace_d2_{case}",
    )
    result, events, provenance = P.execute_governed(invocation, admission, binding, adapter)
    return {
        "case": case,
        "invocation_id": invocation.id,
        "trace_id": invocation.trace_id,
        "result_id": result.id,
        "result_invocation_id": result.invocation_id,
        "result_status": result.status,
        "output_status": (result.output or {}).get("status"),
        "conclusion": (result.output or {}).get("conclusion"),
        "evidence_items": (result.output or {}).get("evidence_items", []),
        "artifacts": [a.to_dict() for a in result.artifacts],
        "trace_events": [e.to_dict() for e in events],
        "provenance": provenance,
    }


def test_t14(admission: dict, binding: dict, adapter) -> None:
    out = platform_bound_case("T-C01", admission, binding, adapter)
    ok = (
        out["result_status"] == "success"
        and out["output_status"] == "accepted_with_evidence"
        and out["conclusion"] is not None
        and "不应小于 50m" in out["conclusion"]
        and len(out["evidence_items"]) >= 1
        and out["provenance"]["verification"] == "PASS"
        and out["provenance"]["resolved_to"]["agent_id"] == P.AGENT_ID
        and out["provenance"]["resolved_to"]["binding_ref"] == binding["binding_id"]
    )
    report("D2-T14",
        "Platform-bound T-C01 direct clause -> professional behavior preserved + exact Agent attribution",
        ok,
        f"result_status={out['result_status']} output_status={out['output_status']} "
        f"conclusion_ok={'不应小于 50m' in (out['conclusion'] or '')} provenance={out['provenance']['verification']}",
    )


def test_t15(admission: dict, binding: dict, adapter) -> None:
    out = platform_bound_case("T-C02", admission, binding, adapter)
    ok = (
        out["result_status"] == "success"
        and out["output_status"] == "accepted_with_evidence"
        and out["conclusion"] is not None
        and "车位/100m²" in out["conclusion"]
        and len(out["evidence_items"]) >= 2
        and out["provenance"]["verification"] == "PASS"
    )
    report("D2-T15",
        "Platform-bound T-C02 conditional table -> professional behavior preserved + exact Agent attribution",
        ok,
        f"result_status={out['result_status']} output_status={out['output_status']} "
        f"evidence_items={len(out['evidence_items'])} provenance={out['provenance']['verification']}",
    )


def test_t16(admission: dict, binding: dict, adapter) -> None:
    out = platform_bound_case("T-C03", admission, binding, adapter)
    ok = (
        out["result_status"] == "success"
        and out["output_status"] == "insufficient_context"
        and out["conclusion"] is not None
        and "无法可靠回答" in out["conclusion"]
        and len(out["evidence_items"]) == 0
        and out["provenance"]["verification"] == "PASS"
    )
    report("D2-T16",
        "Platform-bound T-C03 insufficient-context fail closed -> professional fail-closed preserved + exact Agent attribution",
        ok,
        f"result_status={out['result_status']} output_status={out['output_status']} "
        f"evidence_items={len(out['evidence_items'])} provenance={out['provenance']['verification']}",
    )


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def run_all(regression_detail: str = "") -> tuple[int, int]:
    import tempfile

    RESULTS.clear()
    print("== D2 TESTS (D2-T01..T16) ==")
    with tempfile.TemporaryDirectory(prefix="d2_test_") as tmpdir:
        tmp = Path(tmpdir)

        # shared real artifacts
        gates = P.evaluate_gates(regression_ok=True, regression_detail=regression_detail)
        fingerprint = gates["G-A03"].get("fingerprint")
        admission = P.build_admission_record(gates)
        binding = P.build_binding_record(admission, fingerprint)
        registry, adapter = P.make_adapter()

        test_t01(regression_detail)
        test_t02(tmp)
        test_t03(tmp)
        test_t04(admission, fingerprint)
        test_t05(admission, binding)
        test_t06()
        test_t07(admission, binding)
        test_t08()
        test_t09(admission, binding)
        test_t10(admission, fingerprint)
        test_t11()
        test_t12(admission, binding)
        test_t13(admission, binding, adapter)
        test_t14(admission, binding, adapter)
        test_t15(admission, binding, adapter)
        test_t16(admission, binding, adapter)

    passed = sum(1 for r in RESULTS if r["passed"])
    failed = len(RESULTS) - passed
    print(f"== D2 RESULT: {passed}/{len(RESULTS)} PASS ==")
    return passed, failed


def write_log() -> Path:
    out = D2_ROOT / "evidence" / "D2_TEST_RESULTS.log"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "== D2 TEST RESULTS — CASE 01-D / D2 ==",
        f"generated_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
    ]
    for r in RESULTS:
        lines.append(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['test_id']} — {r['description']}")
        lines.append(f"    {r['detail']}")
    passed = sum(1 for r in RESULTS if r["passed"])
    lines.append("")
    lines.append(f"== D2 RESULT: {passed}/{len(RESULTS)} PASS ==")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regression-detail", default="")
    parser.add_argument("--write-log", action="store_true")
    args = parser.parse_args()
    try:
        passed, failed = run_all(args.regression_detail)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 1
    if args.write_log:
        log = write_log()
        print(f"log written: {log}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

