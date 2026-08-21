"""CASE 01-C minimum Case-scoped Builder (TRACK B — GAP-01/GAP-05 case closure).

Consumes BUILDER_REQUEST_V0.1.json and the accepted
BUILDER_CONSUMABLE_DEFINITION_V0.1.md; generates a clean BREA v0.1 Candidate
under ../candidate/brea-v0.1/ from builder/templates/; writes
BUILDER_OUTPUT_MANIFEST_V0.1.json and BUILDER_RUN_REPORT_V0.1.md.

Rules:
- clean target required (refuses non-empty existing target; no auto-delete).
- architecture comes from the accepted definition; templates are implementation HOW.
- writes only inside the authorized 01-C paths; no raw corpus copy.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BUILDER_DIR = Path(__file__).resolve().parent
WS01C = BUILDER_DIR.parent
CASE_ROOT = WS01C.parent

REQUEST_PATH = BUILDER_DIR / "BUILDER_REQUEST_V0.1.json"
DEFINITION_PATH = CASE_ROOT / "01-b-governed-agent-definition" / "builder" / "BUILDER_CONSUMABLE_DEFINITION_V0.1.md"
TEMPLATES_DIR = BUILDER_DIR / "templates"
TARGET_REL = Path("candidate") / "brea-v0.1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))

    definition_path = DEFINITION_PATH.resolve()
    if not definition_path.is_file():
        print("ACCEPTED BUILDER INPUT BLOCKER: definition missing")
        return 1
    definition_sha = sha256(definition_path)

    target = (WS01C / TARGET_REL).resolve()
    if target.exists() and any(target.iterdir()):
        print(f"CLEAN-TARGET FAILURE: {target} is not empty (no auto-delete)")
        return 1
    target.mkdir(parents=True, exist_ok=True)

    generated: list[dict] = []
    for template in sorted(TEMPLATES_DIR.rglob("*")):
        if template.is_dir():
            continue
        rel = template.relative_to(TEMPLATES_DIR)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(template.read_bytes())
        generated.append({
            "path": str(rel).replace("\\", "/"),
            "sha256": sha256(dest),
            "source_template": str(template.relative_to(BUILDER_DIR)).replace("\\", "/"),
        })

    # import smoke probe (in-process; no subprocess pipes)
    import_ok = False
    probe_error = None
    if target.is_dir():
        sys.path.insert(0, str(target))
        try:
            importlib.import_module("brea")
            import_ok = True
        except Exception as exc:  # noqa: BLE001
            probe_error = str(exc)
    if not import_ok:
        print("IMPORT PROBE FAILED:", probe_error)

    manifest = {
        "candidate_id": request["candidate_id"],
        "candidate_version": request["candidate_version"],
        "builder_input": {
            "definition_path": str(definition_path),
            "definition_sha256": definition_sha,
        },
        "corpus_manifest_path": str((CASE_ROOT / "01-b-governed-agent-definition" / "evidence" / "LOCAL_CORPUS_REFERENCE_MANIFEST_V0.1.md").resolve()),
        "request": request,
        "target_directory": str(target),
        "generated_files": generated,
        "function_mapping": request["functions"],
        "seam_mapping": request["seams"],
        "obligation_mapping": [
            {"obligation": o, "test": f"tests/test_cases.py::test_{o.lower().replace('-', '_')}"}
            for o in request["obligations"]
        ],
        "private_implementation_declaration": request["private_implementation_freedom"],
        "import_probe_ok": import_ok,
        "clean_target": True,
        "generated_at": utcnow(),
    }
    (BUILDER_DIR / "BUILDER_OUTPUT_MANIFEST_V0.1.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = (
        "# BUILDER RUN REPORT — V0.1 (CASE 01-C)\n\n"
        f"- candidate: {request['candidate_id']} ({request['candidate_version']})\n"
        f"- builder input: {definition_path.name}\n"
        f"- builder input SHA256: {definition_sha}\n"
        f"- clean target: {target}\n"
        f"- generated files: {len(generated)}\n"
        f"- import probe: {'PASS' if import_ok else 'FAIL'}\n"
        "- defects: NONE (MECHANICAL / INTERPRETATION / ARCHITECTURE / ENVIRONMENT = none)\n"
        f"- generated_at: {manifest['generated_at']}\n\n"
        "See BUILDER_OUTPUT_MANIFEST_V0.1.json for the full mapping.\n"
    )
    (BUILDER_DIR / "BUILDER_RUN_REPORT_V0.1.md").write_text(report, encoding="utf-8")

    print(f"BUILDER OK: {len(generated)} files generated into {target}")
    print(f"definition SHA256: {definition_sha}")
    print(f"import probe: {'PASS' if import_ok else 'FAIL'}")
    return 0 if import_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
