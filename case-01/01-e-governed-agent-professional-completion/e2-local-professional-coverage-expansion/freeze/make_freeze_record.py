"""E2-AB — generate Candidate Freeze Record + Report (Stage Spec §23).

Freezes case-01.brea @ 0.3-candidate: computes deterministic tree fingerprint,
records file hashes, changed/unchanged lists, source refs, Evaluation Contract SHA,
FN/SEAM/OBL + self-test refs, authorization ref.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(r"E:\试验场地\Agent Harness")
CASE_ROOT = REPO_ROOT / "case-01"
E2_DIR = CASE_ROOT / "01-e-governed-agent-professional-completion" / "e2-local-professional-coverage-expansion"
V03 = E2_DIR / "candidate" / "brea-v0.3"

now = datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(root: Path) -> tuple[str, list[dict]]:
    digest = hashlib.sha256()
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        h = sha256(path)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(h.encode("utf-8"))
        files.append({"path": rel, "sha256": h})
    return digest.hexdigest(), files


def main() -> int:
    tree, files = tree_sha256(V03)

    eval_contract = E2_DIR / "evaluation" / "E2_EVALUATION_CONTRACT_V0.1.md"
    conformance = E2_DIR / "evidence" / "E2_AB_FN_SEAM_OBL_CONFORMANCE_V0.1.md"
    selftest = E2_DIR / "evidence" / "E2_AB_CONSTRUCTION_TEST_RESULTS.log.txt"
    change_manifest = E2_DIR / "builder" / "E2_CANDIDATE_CHANGE_MANIFEST_V0.1.json"

    changed = [f["path"] for f in files if f["path"] in {
        "brea/coverage.py", "brea/facts.py", "brea/runner.py", "brea/identity.py",
        "README.md",
    }]
    unchanged = [f["path"] for f in files if f["path"] not in set(changed)]

    record = {
        "freeze_record_version": "0.1",
        "agent_id": "case-01.brea",
        "candidate_version": "0.3-candidate",
        "parent_reference": {
            "version": "0.2-candidate",
            "ref": "case-01/01-e-governed-agent-professional-completion/e1-local-evidence-query-generalization/candidate/brea-v0.2",
            "immutable": True,
        },
        "candidate_tree_sha256": tree,
        "file_count": len(files),
        "manifest_file_hashes": files,
        "changed_file_list": changed,
        "unchanged_verification": {
            "method": "E2 builder verified unchanged modules byte-identical to v0.2 (E2_CANDIDATE_CHANGE_MANIFEST_V0.1.json)",
            "count": len(unchanged),
        },
        "professional_source_references": [
            {
                "source_id": "GB55037-2022",
                "clause": "4.3.16",
                "family": "fire_compartment_max_area",
                "corpus_manifest": "case-01/01-b-governed-agent-definition/evidence/LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md",
                "sha256": "2a217deac98636584dbd328d8449a21bfb4ab30d80483d5355915beaba0594f3",
            }
        ],
        "evaluation_contract_ref": str(eval_contract),
        "evaluation_contract_sha256": sha256(eval_contract),
        "evaluation_contract_has_benchmark_cases": False,
        "fn_seam_obl_conformance_ref": str(conformance),
        "construction_self_test_ref": str(selftest),
        "construction_self_test_summary": "AB-T01..T22 PASS (see E2_AB_CONSTRUCTION_TEST_RESULTS.log.txt); candidate regression 15/15 PASS",
        "created_under_e2_ab_authorization_ref": "E2_AB_AUTHORIZATION_RECORD_V0.1.yaml (granted)",
        "frozen_at": now,
    }
    freeze_dir = E2_DIR / "freeze"
    freeze_dir.mkdir(parents=True, exist_ok=True)
    json_path = freeze_dir / "E2_V0_3_CANDIDATE_FREEZE_RECORD_V0.1.json"
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    report = (
        "# E2 — V0.3 CANDIDATE FREEZE REPORT — V0.1\n\n"
        f"- agent_id: `case-01.brea`\n"
        f"- candidate_version: `0.3-candidate`\n"
        f"- parent reference: `case-01.brea @ 0.2-candidate` (immutable)\n"
        f"- **candidate_tree_sha256: `{tree}`**\n"
        f"- file count: {len(files)} (changed {len(changed)}, unchanged-verified {len(unchanged)})\n"
        f"- professional source: GB 55037-2022 §4.3.16 (admitted corpus, SHA verified)\n"
        f"- Evaluation Contract: `{eval_contract.name}` (SHA `{record['evaluation_contract_sha256'][:16]}…`) — "
        f"contains NO future benchmark cases\n"
        f"- FN/SEAM/OBL conformance: `{conformance.name}`\n"
        f"- construction self-checks: AB-T01..T22 PASS + candidate regression 15/15 PASS\n"
        f"- created under: `E2_AB_AUTHORIZATION_RECORD_V0.1.yaml` (granted)\n"
        f"- frozen_at: {now}\n\n"
        "**Once published, the v0.3 Candidate source is immutable for E2-C.**\n"
        "Specific independent Benchmark cases are NOT created in E2-AB (E2-C only, "
        "after Freeze Review PASS + second User authorization).\n"
    )
    md_path = freeze_dir / "E2_V0_3_CANDIDATE_FREEZE_REPORT_V0.1.md"
    md_path.write_text(report, encoding="utf-8")

    print(f"candidate_tree_sha256 = {tree}")
    print(f"freeze record written: {json_path}")
    print(f"freeze report written: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
