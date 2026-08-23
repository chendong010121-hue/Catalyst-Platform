"""D2 — orchestrator: full Stage Spec execution sequence (D2-0..D2-19).

Produces the evidence output package under d2-local-admission-binding/:
  admission/BREA_V0_1_ADMISSION_RECORD.json
  binding/BREA_V0_1_EXECUTION_BINDING.json
  evidence/D2_CANDIDATE_REGRESSION_RESULTS.log (.txt twin committed)
  evidence/D2_TEST_RESULTS.log (.txt twin committed)
  evidence/D2_PLATFORM_BOUND_CASE_RESULTS.log (.txt twin committed)
  evidence/D2_PROVENANCE_CHAIN_V0.1.json / .md
  evidence/D2_EVIDENCE_INDEX_V0.1.md
  evidence/D2_REPOSITORY_INTEGRITY_V0.1.md
  evidence/PLATFORM_GAP_UPDATE_D2_V0.1.md
  review/CASE_01_D_D2_EXECUTION_REPORT_V0.1.md
  review/CASE_01_E_ENTRY_BOUNDARY_V0.1.md
  scripts/implementation_fingerprint.json

No modification of Platform/Runtime/Adapter/enterprise_extensions/Candidate/main.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(r"E:\试验场地\Agent Harness")
D2_ROOT = REPO_ROOT / "case-01" / "01-d-governed-agent-admission-binding" / "d2-local-admission-binding"
CANDIDATE = REPO_ROOT / "case-01" / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"

for p in (str(REPO_ROOT), str(D2_ROOT / "implementation"), str(CANDIDATE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import d2_pipeline as P  # noqa: E402

now = datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    import os
    env["PATH"] = os.environ.get("PATH", "")
    return subprocess.run(
        argv, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )


def run_candidate_regression() -> tuple[bool, str]:
    """D2-6 — rerun accepted Candidate test/self-check surface unchanged (15/15 + T-C01/02/03)."""
    lines: list[str] = [
        "== CANDIDATE REGRESSION — CASE 01-D / D2 ==",
        f"candidate: case-01/01-c-governed-local-formation/candidate/brea-v0.1 (read-only)",
        f"generated_at: {now}",
        "",
    ]

    # 15/15 self-check (run as script: tests/run_all.py imports top-level test modules)
    proc = _run([sys.executable, "tests/run_all.py"], CANDIDATE)
    lines.append("-- 15/15 self-check (tests.run_all) --")
    lines.append(proc.stdout.strip())
    if proc.stderr.strip():
        lines.append("STDERR:")
        lines.append(proc.stderr.strip())
    selfcheck_ok = "RESULT: PASS" in proc.stdout and "FAIL" not in proc.stdout

    # T-C01 / T-C02 / T-C03
    case_ok = True
    for case in ("T-C01", "T-C02", "T-C03"):
        proc = _run([sys.executable, "-m", "brea.runner", "--case", case], CANDIDATE)
        lines.append(f"-- {case} --")
        try:
            payload = json.loads(proc.stdout)
            lines.append(f"status={payload.get('status')} conclusion={payload.get('conclusion')}")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"PARSE ERROR: {exc}")
            lines.append(proc.stdout[:500])
            case_ok = False
        if proc.returncode != 0:
            case_ok = False
            lines.append(f"exit code {proc.returncode}")

    lines.append("")
    overall = selfcheck_ok and case_ok
    lines.append(f"== CANDIDATE REGRESSION RESULT: {'PASS' if overall else 'FAIL'} ==")

    log = D2_ROOT / "evidence" / "D2_CANDIDATE_REGRESSION_RESULTS.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    log.write_text(text, encoding="utf-8")
    (log.with_suffix(".log.txt")).write_text(text, encoding="utf-8")
    return overall, text


def run_d2_tests(regression_detail: str) -> tuple[bool, str]:
    """D2-14 — run D2-T01..T16."""
    sys.path.insert(0, str(D2_ROOT / "tests"))
    import run_d2_tests

    passed, failed = run_d2_tests.run_all(regression_detail)
    log = run_d2_tests.write_log()
    text = log.read_text(encoding="utf-8")
    (log.with_suffix(".log.txt")).write_text(text, encoding="utf-8")
    return failed == 0, text


def run_platform_bound_cases(admission: dict, binding: dict, adapter) -> tuple[bool, list, str]:
    """D2-15 — Platform-bound T-C01/02/03 (whole Agent through D2 binding path)."""
    sys.path.insert(0, str(D2_ROOT / "tests"))
    import run_d2_tests

    outputs = []
    for case in ("T-C01", "T-C02", "T-C03"):
        outputs.append(run_d2_tests.platform_bound_case(case, admission, binding, adapter))
    all_ok = all(
        o["provenance"]["verification"] == "PASS"
        and o["result_status"] == "success"
        for o in outputs
    )
    lines = [
        "== PLATFORM-BOUND CASE RESULTS — CASE 01-D / D2 ==",
        f"generated_at: {now}",
        "",
    ]
    for o in outputs:
        lines.append(f"-- {o['case']} --")
        lines.append(json.dumps(o, ensure_ascii=False, indent=2))
    lines.append("")
    lines.append(f"== PLATFORM-BOUND RESULT: {'PASS' if all_ok else 'FAIL'} ==")
    text = "\n".join(lines)
    log = D2_ROOT / "evidence" / "D2_PLATFORM_BOUND_CASE_RESULTS.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(text, encoding="utf-8")
    (log.with_suffix(".log.txt")).write_text(text, encoding="utf-8")
    return all_ok, outputs, text


def build_provenance_chain(admission: dict, binding: dict, fingerprint: dict, case_outputs: list) -> dict:
    """D2-16/17 — machine-readable provenance chain + verification."""
    chain = {
        "provenance_chain": {
            "version": "0.1",
            "admission_record": {
                "ref": "admission/BREA_V0_1_ADMISSION_RECORD.json",
                "admission_ref": admission["admission_ref"],
                "agent_id": admission["agent_id"],
                "agent_version": admission["agent_version"],
                "admission_status": admission["admission_status"],
            },
            "binding_record": {
                "ref": "binding/BREA_V0_1_EXECUTION_BINDING.json",
                "binding_id": binding["binding_id"],
                "agent_id": binding["agent_id"],
                "agent_version": binding["agent_version"],
                "admission_ref": binding["admission_ref"],
                "binding_status": binding["binding_status"],
            },
            "invocation_governance_agent": {
                "canonical_location": "Invocation.extensions['governance.agent']",
                "payload": {
                    "agent_id": P.AGENT_ID,
                    "agent_version": P.AGENT_VERSION,
                    "admission_ref": admission["admission_ref"],
                    "binding_ref": binding["binding_id"],
                },
            },
            "execution_routing_identity": {
                "capability_id": P.EXECUTION_CAPABILITY_ID,
                "capability_version": P.EXECUTION_CAPABILITY_VERSION,
            },
            "implementation_fingerprint": fingerprint,
            "platform_path": "PlatformValidator -> InMemoryDescriptorRegistry -> RuntimeAdapter -> Runtime (unchanged)",
            "case_executions": [],
        },
        "verification": {},
    }
    for o in case_outputs:
        chain["provenance_chain"]["case_executions"].append({
            "case": o["case"],
            "invocation_id": o["invocation_id"],
            "trace_id": o["trace_id"],
            "result_id": o.get("result_id"),
            "result_invocation_id": o.get("result_invocation_id"),
            "artifacts": [
                {"id": a["id"], "producer": a.get("producer", {})} for a in o["artifacts"]
            ],
            "trace_events": [
                {
                    "id": e["id"],
                    "trace_id": e["trace_id"],
                    "subject_id": e["subject_id"],
                    "event_type": e["event_type"],
                    "governance_agent": (e.get("extensions") or {}).get("governance.agent"),
                }
                for e in o["trace_events"]
            ],
            "resolved_to": o["provenance"]["resolved_to"],
        })
    # independent verification
    checks = {}
    checks["admission_resolves_agent"] = (
        chain["provenance_chain"]["admission_record"]["agent_id"] == P.AGENT_ID
        and chain["provenance_chain"]["admission_record"]["agent_version"] == P.AGENT_VERSION
        and chain["provenance_chain"]["admission_record"]["admission_status"] == "ADMITTED"
    )
    checks["binding_resolves_admission"] = (
        chain["provenance_chain"]["binding_record"]["admission_ref"] == admission["admission_ref"]
        and chain["provenance_chain"]["binding_record"]["binding_status"] == "BOUND"
    )
    checks["governance_payload_resolves"] = all(
        chain["provenance_chain"]["invocation_governance_agent"]["payload"][k]
        == chain["provenance_chain"]["admission_record"][k] if k in ("agent_id", "agent_version")
        else chain["provenance_chain"]["invocation_governance_agent"]["payload"][k] == v
        for k, v in {
            "admission_ref": admission["admission_ref"],
            "binding_ref": binding["binding_id"],
        }.items()
    )
    checks["fingerprint_matches_binding"] = (
        chain["provenance_chain"]["implementation_fingerprint"]["candidate_tree_sha256"]
        == binding["implementation_fingerprint"]["candidate_tree_sha256"]
    )
    checks["all_cases_linked"] = all(
        chain["provenance_chain"]["case_executions"] and
        all(
            e["trace_id"] == o["trace_id"]
            and ((e.get("extensions") or {}).get("governance.agent") or {}).get("payload")
            == chain["provenance_chain"]["invocation_governance_agent"]["payload"]
            for e in o["trace_events"]
        )
        and o["provenance"]["resolved_to"]["agent_id"] == P.AGENT_ID
        and o["provenance"]["resolved_to"]["binding_ref"] == binding["binding_id"]
        for o in case_outputs
    )
    checks["artifacts_producer_linked"] = all(
        all(a.get("producer", {}).get("capability_id") == P.EXECUTION_CAPABILITY_ID for a in o["artifacts"])
        for o in case_outputs
    )
    chain["verification"] = {
        "result": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }
    out = D2_ROOT / "evidence" / "D2_PROVENANCE_CHAIN_V0.1.json"
    out.write_text(json.dumps(chain, ensure_ascii=False, indent=2), encoding="utf-8")
    return chain


def write_provenance_md(chain: dict) -> None:
    c = chain["provenance_chain"]
    lines = [
        "# D2 PROVENANCE CHAIN — V0.1",
        "",
        f"**Verification:** `{chain['verification']['result']}`",
        "",
        "## Chain (spec §11)",
        "",
        "```text",
        f"Admission Record  ->  admission/BREA_V0_1_ADMISSION_RECORD.json (admission_ref={c['admission_record']['admission_ref']})",
        f"Binding Record    ->  binding/BREA_V0_1_EXECUTION_BINDING.json (binding_id={c['binding_record']['binding_id']})",
        "Invocation.extensions['governance.agent'] (canonical source)",
        "Platform Invocation (id/trace_id)",
        f"execution routing identity = {P.EXECUTION_CAPABILITY_ID} @ {P.EXECUTION_CAPABILITY_VERSION}",
        "RuntimeAdapter / Runtime (unchanged)",
        "Result.invocation_id",
        "TraceEvent.trace_id + subject_id",
        "TraceEvent.extensions['governance.agent']",
        "ArtifactRef.producer.invocation_id",
        "```",
        "",
        "## Resolved identifiers",
        "",
        f"- agent_id = `{c['admission_record']['agent_id']}`",
        f"- agent_version = `{c['admission_record']['agent_version']}`",
        f"- admission_ref = `{c['admission_record']['admission_ref']}`",
        f"- binding_ref = `{c['binding_record']['binding_id']}`",
        f"- candidate_tree_sha256 = `{c['implementation_fingerprint']['candidate_tree_sha256']}`",
        f"- builder_output_manifest_sha256 = `{c['implementation_fingerprint']['builder_output_manifest_sha256']}`",
        "",
        "## Executions",
        "",
    ]
    for o in c["case_executions"]:
        lines.append(f"### {o['case']}")
        lines.append(f"- invocation_id: `{o['invocation_id']}`  trace_id: `{o['trace_id']}`")
        lines.append(f"- resolved_to: `{json.dumps(o['resolved_to'], ensure_ascii=False)}`")
        lines.append(f"- trace events: {len(o['trace_events'])} (all carry exact governance.agent)")
        lines.append(f"- artifacts: {len(o['artifacts'])} (producer capability_id = {P.EXECUTION_CAPABILITY_ID})")
        lines.append("")
    lines.append("## Verification checks")
    lines.append("")
    for k, v in chain["verification"]["checks"].items():
        lines.append(f"- {k}: `{'PASS' if v else 'FAIL'}`")
    out = D2_ROOT / "evidence" / "D2_PROVENANCE_CHAIN_V0.1.md"
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print("== D2 EXECUTION ==")
    # D2-0 preflight
    head = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True, encoding="utf-8").stdout.strip()
    branch = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True, encoding="utf-8").stdout.strip()
    assert branch == "case-01", f"branch != case-01 ({branch})"
    print(f"preflight: branch={branch} HEAD={head}")

    # D2-6 regression (real)
    regression_ok, regression_text = run_candidate_regression()
    print(f"candidate regression: {'PASS' if regression_ok else 'FAIL'}")

    # D2-7 evaluate gates -> D2-9 admission record
    gates = P.evaluate_gates(
        regression_ok=regression_ok,
        regression_detail="candidate regression PASS (evidence/D2_CANDIDATE_REGRESSION_RESULTS.log)",
    )
    fingerprint = gates["G-A03"].get("fingerprint", {})
    fp_out = D2_ROOT / "scripts" / "implementation_fingerprint.json"
    fp_out.write_text(json.dumps(fingerprint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"gates all_pass={gates['all_pass']}")
    for gid, g in gates.items():
        if isinstance(g, dict):
            print(f"  {gid}: {g['status']}")

    if not gates["all_pass"]:
        admission = P.build_admission_record(gates)
        P.write_admission_record(admission)
        print("ADMISSION REJECTED — stopping (failure evidence written)")
        return 1

    admission = P.build_admission_record(gates)
    admission_path = P.write_admission_record(admission)
    print(f"admission record written: {admission_path} status={admission['admission_status']}")

    # D2-10 binding record
    binding = P.build_binding_record(admission, fingerprint)
    P.validate_binding(binding, admission, fingerprint)
    binding_path = P.write_binding_record(binding)
    print(f"binding record written: {binding_path} status={binding['binding_status']}")

    # D2-11/12/13 stack + adapter
    registry, adapter = P.make_adapter()

    # D2-14 D2 tests
    tests_ok, tests_text = run_d2_tests("candidate regression PASS (evidence/D2_CANDIDATE_REGRESSION_RESULTS.log)")
    print(f"D2 tests: {'PASS' if tests_ok else 'FAIL'}")

    # D2-15 platform-bound cases
    cases_ok, case_outputs, cases_text = run_platform_bound_cases(admission, binding, adapter)
    print(f"platform-bound cases: {'PASS' if cases_ok else 'FAIL'}")

    # D2-16/17 provenance chain
    chain = build_provenance_chain(admission, binding, fingerprint, case_outputs)
    write_provenance_md(chain)
    print(f"provenance chain verification: {chain['verification']['result']}")

    return 0 if (regression_ok and tests_ok and cases_ok
                 and chain["verification"]["result"] == "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
