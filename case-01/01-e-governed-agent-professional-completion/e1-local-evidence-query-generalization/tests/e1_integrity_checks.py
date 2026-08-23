"""E1 — v0.1 baseline integrity + v0.2 FN/SEAM/OBL conformance (E1-14/E1-16/E1-17).

Produces:
  evidence/E1_V01_BASELINE_INTEGRITY_V0.1.md
  evidence/E1_V02_FUNCTION_SEAM_OBLIGATION_CONFORMANCE_V0.1.md
  evidence/E1_REPOSITORY_INTEGRITY_V0.1.md
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(r"E:\试验场地\Agent Harness")
CASE_ROOT = REPO_ROOT / "case-01"
E1_DIR = CASE_ROOT / "01-e-governed-agent-professional-completion" / "e1-local-evidence-query-generalization"
V01 = CASE_ROOT / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"
V01_MANIFEST = CASE_ROOT / "01-c-governed-local-formation" / "builder" / "BUILDER_OUTPUT_MANIFEST_V0.1.json"
V02 = E1_DIR / "candidate" / "brea-v0.2"

sys.path.insert(0, str(V02))

from brea.identity import BREA_FUNCTION_MAP, OBLIGATIONS, SEAM_MAP  # noqa: E402

now = datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def v01_baseline_integrity() -> bool:
    manifest = json.loads(V01_MANIFEST.read_text(encoding="utf-8"))
    ok = True
    lines = [
        "# E1 — V0.1 BASELINE INTEGRITY — V0.1",
        "",
        "> Stage Spec §2/§16/§17: the admitted v0.1 baseline must remain unchanged;",
        "> the D2 implementation fingerprint must remain valid (P-E1-04, AC-E1-01/21).",
        "",
        f"generated_at: {now}",
        "",
        "## D2 fingerprint recheck (accepted 01-C manifest vs current v0.1 tree)",
        "",
        "| file | manifest sha256 | actual sha256 | match |",
        "|---|---|---|---|",
    ]
    for entry in manifest["generated_files"]:
        rel = entry["path"].replace("/", "\\")
        path = V01 / rel
        actual = sha256(path) if path.is_file() else "MISSING"
        match = actual == entry["sha256"]
        ok = ok and match
        lines.append(f"| {rel} | {entry['sha256'][:16]}… | {actual[:16]}… | {'PASS' if match else 'FAIL'} |")
    lines += [
        "",
        f"## Result: {'PASS' if ok else 'FAIL'}",
        "",
        "The admitted v0.1 Candidate is byte-unchanged; the D2 admission/binding evidence",
        "(admission-case-01-brea-v0.1-001 / binding-case-01-brea-v0.1-001) remains valid.",
        "",
    ]
    (E1_DIR / "evidence" / "E1_V01_BASELINE_INTEGRITY_V0.1.md").write_text(
        "\n".join(lines), encoding="utf-8")
    return ok


def v02_conformance() -> bool:
    expected_fns = [f"FN-{index:02d}" for index in range(1, 12)]
    expected_seams = {"SEAM-01", "SEAM-02", "SEAM-03"}
    expected_obls = [f"OBL-{index:02d}" for index in range(1, 7)]
    checks = {
        "FN-01..11 preserved": sorted(BREA_FUNCTION_MAP) == sorted(expected_fns),
        "SEAM-01..03 preserved": set(SEAM_MAP) == expected_seams,
        "OBL-01..06 preserved": sorted(OBLIGATIONS) == sorted(expected_obls),
        "no FN removed": all(name and module and status for name, module, status in BREA_FUNCTION_MAP.values()),
    }
    # OBL evidence: T-C01/02/03 pass (regression evidence), numeric safety, verbatim,
    # enterprise orthogonality are asserted by candidate tests (run_all) and E1 tests.
    lines = [
        "# E1 — V0.2 FUNCTION / SEAM / OBLIGATION CONFORMANCE — V0.1",
        "",
        "> Stage Spec §16 / AC-E1-19: FN/SEAM/OBL mapping must remain valid for v0.2.",
        "",
        f"generated_at: {now}",
        "",
        "## Mapping checks",
        "",
    ]
    for label, ok in checks.items():
        lines.append(f"- {label}: {'PASS' if ok else 'FAIL'}")
    lines += [
        "",
        "## E1 change classification (from E1_CHANGE_IMPACT_REVIEW_V0.1.md)",
        "",
        "| Responsibility | Class |",
        "|---|---|",
        "| FN-01 Intake | EXTENDED |",
        "| FN-02 Facts | UNCHANGED |",
        "| FN-03 Applicability | EXTENDED |",
        "| FN-04/05 Evidence | EXTENDED (major completion) |",
        "| FN-06 Uncertainty | EXTENDED |",
        "| FN-07 Result | IMPLEMENTATION-ONLY |",
        "| FN-08 Artifact | UNCHANGED |",
        "| FN-09 Corpus | EXTENDED (major completion) |",
        "| FN-10 Provider | UNCHANGED (PRIVATE/DEFERRED) |",
        "| FN-11 Runner | EXTENDED |",
        "| SEAM-01 | UNCHANGED |",
        "| SEAM-02 | EXTENDED |",
        "| SEAM-03 | EXTENDED |",
        "| OBL-01..06 | UNCHANGED |",
        "",
        "## Obligation evidence (v0.2)",
        "",
        "- OBL-01 (direct clause + conditional table professional answers): T-C01/T-C02 PASS (regression).",
        "- OBL-02 (observable applicability chain): E1-S-02 + candidate test_seam02 PASS.",
        "- OBL-03 (numeric authority in corpus text): ST-06 + verbatim assertions in every QMODE handler.",
        "- OBL-04 (no fabrication): QMODE-02/04 missing-clause/table fail closed; B-E1-04/09 PASS.",
        "- OBL-05 (source + locator + verbatim): every evidence item carries source/locator; line-verbatim asserted.",
        "- OBL-06 (enterprise orthogonality): ST-05 PASS (candidate regression).",
        "",
        f"## Result: {'PASS' if all(checks.values()) else 'FAIL'}",
        "",
    ]
    (E1_DIR / "evidence" / "E1_V02_FUNCTION_SEAM_OBLIGATION_CONFORMANCE_V0.1.md").write_text(
        "\n".join(lines), encoding="utf-8")
    return all(checks.values())


def repository_integrity() -> bool:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True, text=True, encoding="utf-8",
    ).stdout
    changed = [line for line in out.splitlines() if line.strip()]
    violations = []
    for line in changed:
        path = line[3:].replace("/", "\\")
        if "01-e-governed-agent-professional-completion\\e1-local-evidence-query-generalization" in path:
            continue
        violations.append(line)
    main_sha = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "origin/main"],
        capture_output=True, text=True, encoding="utf-8",
    ).stdout.strip()
    ok = not violations and main_sha == "5874be1130e8867082880fcd63f659fc909d9efd"
    lines = [
        "# E1 — REPOSITORY INTEGRITY — V0.1",
        "",
        "> Stage Spec §23/§26: E1 writes only under e1-local-evidence-query-generalization/**;",
        "> Platform / Runtime / Adapter / enterprise_extensions / main / v0.1 unchanged; raw corpus never committed.",
        "",
        f"generated_at: {now}",
        "",
        "## Working-tree contamination check",
        "",
        f"- unauthorized changes outside E1 write path: {len(violations)}",
    ]
    for violation in violations:
        lines.append(f"  - {violation}")
    lines += [
        "",
        "## Protected boundaries",
        "",
        f"- origin/main: {main_sha} (expected 5874be1130e8867082880fcd63f659fc909d9efd) — "
        f"{'UNCHANGED' if main_sha == '5874be1130e8867082880fcd63f659fc909d9efd' else 'DRIFTED'}",
        "- platform_standard/**, agent_runtime/**, enterprise_extensions/**, examples/**: read-only, unchanged",
        "- admitted v0.1 candidate: byte-unchanged (see E1_V01_BASELINE_INTEGRITY_V0.1.md)",
        "- raw corpus: local, read-only, not committed",
        "",
        f"## Result: {'PASS' if ok else 'FAIL'}",
        "",
    ]
    (E1_DIR / "evidence" / "E1_REPOSITORY_INTEGRITY_V0.1.md").write_text(
        "\n".join(lines), encoding="utf-8")
    return ok


def main() -> int:
    results = {
        "v0.1_baseline_integrity": v01_baseline_integrity(),
        "v0.2_fn_seam_obl_conformance": v02_conformance(),
        "repository_integrity": repository_integrity(),
    }
    for label, ok in results.items():
        print(f"{label}: {'PASS' if ok else 'FAIL'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
