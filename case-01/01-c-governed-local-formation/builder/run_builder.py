"""CASE 01-C minimum Case-scoped Builder — REPAIRED V0.2 (C-01..C-05 closure).

The ACCEPTED BUILDER_CONSUMABLE_DEFINITION is the authoritative architecture input:
- SHA enforced (fail closed BEFORE generation; C-02);
- identity/purpose/FN/SEAM/OBL/assets/corpus/freedom extracted and validated (C-01);
- BUILDER_REQUEST carries EXECUTION parameters only — architecture duplication rejected (C-01);
- generated Candidate maps validated against the parsed definition (C-01);
- obligation mapping references real, validated test functions (C-03).
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import definition_parser as dp

BUILDER_DIR = Path(__file__).resolve().parent
WS01C = BUILDER_DIR.parent
CASE_ROOT = WS01C.parent

REQUEST_PATH = BUILDER_DIR / "BUILDER_REQUEST_V0.1.json"
DEFINITION_PATH = CASE_ROOT / "01-b-governed-agent-definition" / "builder" / "BUILDER_CONSUMABLE_DEFINITION_V0.1.md"
TEMPLATES_DIR = BUILDER_DIR / "templates"
TARGET_REL = Path("candidate") / "brea-v0.1"

# Canonical obligation -> real test/evidence references (C-03). BT-08 validates every ref exists.
OBLIGATION_MAPPING: dict[str, list[str]] = {
    "OBL-01": [
        "tests/test_cases.py::test_t_c01_direct_clause",
        "tests/test_cases.py::test_t_c02_conditional_table",
    ],
    "OBL-02": [
        "tests/test_seams.py::test_seam02_applicability",
        "tests/test_cases.py::test_t_c02_conditional_table",
    ],
    "OBL-03": [
        "tests/test_structural.py::test_st06_numeric_traceability",
        "tests/test_cases.py::test_t_c01_direct_clause",
        "tests/test_cases.py::test_t_c02_conditional_table",
    ],
    "OBL-04": [
        "tests/test_cases.py::test_t_c03_fail_closed",
    ],
    "OBL-05": [
        "tests/test_cases.py::test_t_c01_direct_clause",
        "tests/test_cases.py::test_t_c02_conditional_table",
        "tests/test_seams.py::test_seam03_evidence",
    ],
    "OBL-06": [
        "tests/test_structural.py::test_st05_enterprise_orthogonality",
        "tests/test_cases.py::test_t_c02_conditional_table",
    ],
}

ARCHITECTURE_REQUEST_KEYS = (
    "functions", "seams", "obligations", "allowed_asset_manifest",
    "private_implementation_freedom",
)


class DefinitionShaMismatch(RuntimeError):
    pass


class RequestArchitectureDuplication(RuntimeError):
    pass


class CleanTargetViolation(RuntimeError):
    pass


class CandidateMappingMismatch(RuntimeError):
    pass


class ObligationRefMissing(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def check_definition_sha(path: Path, expected: str) -> str:
    """C-02: actual SHA != accepted SHA -> fail closed."""
    if not path.is_file():
        raise DefinitionShaMismatch(f"definition missing: {path}")
    actual = sha256(path)
    if actual.lower() != expected.lower():
        raise DefinitionShaMismatch(
            f"definition SHA mismatch: expected {expected}, got {actual}"
        )
    return actual


def validate_request(request: dict) -> None:
    """C-01: architecture fields must not be duplicated in the request."""
    for key in ARCHITECTURE_REQUEST_KEYS:
        if key in request:
            raise RequestArchitectureDuplication(
                f"architecture field '{key}' must come from the governed definition"
            )


def generate(target: Path, templates_dir: Path) -> list[dict]:
    """C-01/§14: clean-target generation. Non-empty target fails closed."""
    if target.exists() and any(target.iterdir()):
        raise CleanTargetViolation(f"target not clean: {target} (no auto-delete)")
    target.mkdir(parents=True, exist_ok=True)
    generated: list[dict] = []
    for template in sorted(templates_dir.rglob("*")):
        if template.is_dir():
            continue
        rel = template.relative_to(templates_dir)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(template.read_bytes())
        generated.append({
            "path": str(rel).replace("\\", "/"),
            "sha256": sha256(dest),
            "source_template": str(template.relative_to(BUILDER_DIR)).replace("\\", "/"),
        })
    return generated


def _fresh_identity(target: Path):
    for module in list(sys.modules):
        if module == "brea" or module.startswith("brea."):
            del sys.modules[module]
    sys.path.insert(0, str(target))
    import brea.identity  # noqa: PLC0415
    return brea.identity


def _expand_fns(value: str) -> list[str]:
    parts = value.replace("FN-", "").split("/")
    return [f"FN-{int(part):02d}" for part in parts if part.strip()]


def validate_generated_candidate(target: Path, parsed: dict) -> None:
    """C-01: generated Candidate maps must match the parsed accepted definition."""
    identity = _fresh_identity(target)

    parsed_fns = set(parsed["functions"])
    candidate_fns = set(identity.BREA_FUNCTION_MAP)
    if candidate_fns != parsed_fns:
        raise CandidateMappingMismatch(f"FN set mismatch: {sorted(candidate_fns ^ parsed_fns)}")

    for fn, info in parsed["functions"].items():
        candidate_name, _module, candidate_status = identity.BREA_FUNCTION_MAP[fn]
        if info["name"].strip().lower() != candidate_name.strip().lower():
            raise CandidateMappingMismatch(f"{fn} name mismatch")
        governance = info["governance"]
        if "SEAM-" in governance:
            marker = governance.strip()
            if marker not in candidate_status:
                raise CandidateMappingMismatch(f"{fn} seam marker mismatch: {marker} vs {candidate_status}")
        elif "DECLARED" in governance:
            if "DECLARED" not in candidate_status:
                raise CandidateMappingMismatch(f"{fn} declared-boundary mismatch")
        else:
            if "PRIVATE" not in candidate_status:
                raise CandidateMappingMismatch(f"{fn} private marker mismatch")

    parsed_seams = set(parsed["seams"])
    candidate_seams = set(identity.SEAM_MAP)
    if candidate_seams != parsed_seams:
        raise CandidateMappingMismatch(f"SEAM set mismatch: {sorted(candidate_seams ^ parsed_seams)}")
    for seam, info in parsed["seams"].items():
        candidate_owner, candidate_fns = identity.SEAM_MAP[seam][1], identity.SEAM_MAP[seam][2]
        for token in ("Domain", "Agent", "Enterprise"):
            if token in info["owner"] and token not in candidate_owner:
                raise CandidateMappingMismatch(f"{seam} owner token '{token}' missing")
        if set(candidate_fns) != set(_expand_fns(info["functions"])):
            raise CandidateMappingMismatch(f"{seam} function membership mismatch")

    if set(identity.OBLIGATIONS) != parsed["obligations"]:
        raise CandidateMappingMismatch("OBLIGATIONS mismatch")


def validate_obligation_refs(target: Path, mapping: dict[str, list[str]]) -> None:
    """C-03: every obligation test reference must exist."""
    for obligation, refs in mapping.items():
        if obligation not in mapping:
            continue
        for ref in refs:
            file_part, _, func = ref.partition("::")
            path = target / file_part
            if not path.is_file():
                raise ObligationRefMissing(f"{obligation} -> missing file {ref}")
            if f"def {func}" not in path.read_text(encoding="utf-8"):
                raise ObligationRefMissing(f"{obligation} -> missing function {ref}")


def main(argv: list[str] | None = None) -> int:
    try:
        actual_sha = check_definition_sha(DEFINITION_PATH, dp.EXPECTED_DEFINITION_SHA)
        parsed = dp.parse_definition(DEFINITION_PATH.read_text(encoding="utf-8"))
        dp.validate_architecture(parsed)
        request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
        validate_request(request)
        target = (WS01C / TARGET_REL).resolve()
        generated = generate(target, TEMPLATES_DIR)
        validate_generated_candidate(target, parsed)
        validate_obligation_refs(target, OBLIGATION_MAPPING)

        # import probe
        import_ok = False
        probe_error = None
        try:
            _fresh_identity(target)
            importlib.import_module("brea")
            import_ok = True
        except Exception as exc:  # noqa: BLE001
            probe_error = str(exc)

        manifest = {
            "builder": "case-scoped-minimum-builder-v0.2 (definition-driven, C-01..C-05 repaired)",
            "candidate_id": request.get("candidate_id"),
            "candidate_version": request.get("candidate_version"),
            "builder_input": {
                "definition_path": str(DEFINITION_PATH),
                "accepted_sha": dp.EXPECTED_DEFINITION_SHA,
                "verified_sha": actual_sha,
                "sha_enforced": True,
            },
            "definition_parsed_architecture": {
                "identity": parsed["identity"],
                "purpose": parsed["purpose"][:80] + ("…" if len(parsed["purpose"]) > 80 else ""),
                "functions": {fn: info["governance"] for fn, info in parsed["functions"].items()},
                "seams": {seam: {"owner": info["owner"], "functions": info["functions"]}
                          for seam, info in parsed["seams"].items()},
                "obligations": sorted(parsed["obligations"]),
                "selected_legacy_adaptation_assets": sorted(parsed["selected_assets"]),
                "deferred_legacy_assets": sorted(parsed["deferred_assets"]),
                "corpus_manifest_referenced": parsed["corpus_manifest_referenced"],
                "private_freedom": parsed["private_freedom"],
            },
            "request": request,
            "target_directory": str(target),
            "generated_files": generated,
            "obligation_mapping": OBLIGATION_MAPPING,
            "validation": {
                "definition_sha": "PASS",
                "architecture_validation": "PASS",
                "request_architecture_duplication": "REJECTED (no architecture keys)",
                "generated_candidate_mapping": "PASS",
                "obligation_refs": "PASS",
                "import_probe": "PASS" if import_ok else f"FAIL: {probe_error}",
                "clean_target": True,
            },
            "generated_at": utcnow(),
        }
        (BUILDER_DIR / "BUILDER_OUTPUT_MANIFEST_V0.1.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        report = (
            "# BUILDER RUN REPORT — V0.2 (CASE 01-C targeted builder proof repair)\n\n"
            f"- base implementation commit: a0b03e1d23512f401a8ddb96efdb1f710383ff93\n"
            f"- candidate: {request.get('candidate_id')} ({request.get('candidate_version')})\n"
            f"- builder input (accepted definition): {DEFINITION_PATH.name}\n"
            f"- definition SHA enforced: {dp.EXPECTED_DEFINITION_SHA} (actual {actual_sha})\n"
            f"- definition semantic consumption: PASS (identity/purpose/FN/SEAM/OBL/assets/corpus/freedom parsed + validated)\n"
            f"- request architecture duplication: REJECTED (execution parameters only)\n"
            f"- generated candidate mapping validation: PASS\n"
            f"- obligation mapping refs validated: PASS\n"
            f"- clean target: {target}\n"
            f"- generated files: {len(generated)}\n"
            f"- import probe: {'PASS' if import_ok else 'FAIL'}\n"
            "- repairs closed: C-01 (definition-driven projection), C-02 (SHA enforced), "
            "C-03 (obligation mapping real refs), C-04 (evidence log), C-05 (gap status reconciled)\n"
            "- prior formation-run bounded repairs: R-01..R-05 (see earlier report; architecture unchanged)\n"
            f"- generated_at: {manifest['generated_at']}\n\n"
            "See BUILDER_OUTPUT_MANIFEST_V0.1.json for the full mapping.\n"
        )
        (BUILDER_DIR / "BUILDER_RUN_REPORT_V0.1.md").write_text(report, encoding="utf-8")

        print(f"BUILDER OK (definition-driven): {len(generated)} files generated into {target}")
        print(f"definition SHA enforced: {actual_sha}")
        print(f"import probe: {'PASS' if import_ok else 'FAIL'}")
        return 0 if import_ok else 1
    except (DefinitionShaMismatch, RequestArchitectureDuplication, CleanTargetViolation,
            CandidateMappingMismatch, ObligationRefMissing, ValueError) as exc:
        print(f"BUILDER FAIL CLOSED: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"BUILDER FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
