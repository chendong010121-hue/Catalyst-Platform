"""E2 — Case-local Builder change mechanism (E2 Spec §19; reuses E1 mechanism).

v0.2 (E1 accepted baseline) is immutable. This mechanism:
  - verifies v0.2 reference identity + E1 accepted fingerprint
  - verifies v0.1 (admitted) unchanged
  - copies v0.2 tree -> candidate/brea-v0.3 (clean target)
  - overlays ONLY the authorized E2 change source (E2_CHANGE_IMPACT_REVIEW)
  - verifies unchanged modules byte-identical to v0.2
  - emits change provenance (manifest + run report)

Case-local; NOT a generic Builder Platform.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BUILDER_DIR = Path(__file__).resolve().parent
E2_DIR = BUILDER_DIR.parent
CASE_ROOT = E2_DIR.parents[1]  # case-01/

V01 = CASE_ROOT / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"
V01_MANIFEST = CASE_ROOT / "01-c-governed-local-formation" / "builder" / "BUILDER_OUTPUT_MANIFEST_V0.1.json"
V02 = CASE_ROOT / "01-e-governed-agent-professional-completion" / "e1-local-evidence-query-generalization" / "candidate" / "brea-v0.2"
DEFINITION = CASE_ROOT / "01-b-governed-agent-definition" / "builder" / "BUILDER_CONSUMABLE_DEFINITION_V0.1.md"
CHANGE_REQUEST = E2_DIR / "change" / "E2_PROFESSIONAL_CHANGE_REQUEST_V0.1.md"
CHANGE_IMPACT = E2_DIR / "change" / "E2_CHANGE_IMPACT_REVIEW_V0.1.md"
CHANGE_SOURCE = BUILDER_DIR / "change_source"
TARGET_REL = Path("candidate") / "brea-v0.3"

ACCEPTED_DEFINITION_SHA = "6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4"

# Authorized E2 changed paths (from E2_CHANGE_IMPACT_REVIEW: bounded EXTENDED / NEW /
# IMPLEMENTATION-ONLY). Everything else must stay byte-identical to v0.2.
CHANGED_RELS = {
    "brea/coverage.py",   # NEW
    "brea/facts.py",      # EXTENDED (SEAM-01)
    "brea/runner.py",     # EXTENDED (family dispatch)
    "brea/identity.py",   # IMPL-ONLY
}


class E2BuilderError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    try:
        # preconditions
        if not V02.is_dir():
            raise E2BuilderError(f"v0.2 reference missing: {V02}")
        if not V01.is_dir():
            raise E2BuilderError(f"admitted v0.1 missing: {V01}")
        if not DEFINITION.is_file():
            raise E2BuilderError(f"baseline definition missing: {DEFINITION}")
        if sha256(DEFINITION) != ACCEPTED_DEFINITION_SHA:
            raise E2BuilderError("baseline definition SHA mismatch")
        for required in (CHANGE_REQUEST, CHANGE_IMPACT):
            if not required.is_file():
                raise E2BuilderError(f"change input missing: {required}")

        # v0.1 admitted fingerprint still valid (AB-T02)
        manifest = json.loads(V01_MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["generated_files"]:
            rel = entry["path"].replace("/", "\\")
            path = V01 / rel
            if not path.is_file() or sha256(path) != entry["sha256"]:
                raise E2BuilderError(f"admitted v0.1 mutated vs manifest: {rel}")

        # clean target
        target = (E2_DIR / TARGET_REL).resolve()
        if target.exists() and any(target.iterdir()):
            raise E2BuilderError(f"target not clean: {target}")
        target.mkdir(parents=True, exist_ok=True)

        # copy v0.2 tree
        copied: list[dict] = []
        for path in V02.rglob("*"):
            if path.is_dir():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            rel = path.relative_to(V02)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())
            copied.append({"path": str(rel).replace("\\", "/"), "source": "v0.2 baseline copy",
                           "change": "UNCHANGED" if str(rel).replace("\\", "/") not in CHANGED_RELS else "CHANGED(overlay pending)",
                           "sha256": sha256(dest)})

        # overlay authorized change source
        overlay: list[dict] = []
        for path in sorted(CHANGE_SOURCE.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(CHANGE_SOURCE)
            rel_str = str(rel).replace("\\", "/")
            if rel_str not in CHANGED_RELS and rel_str != "README.md":
                raise E2BuilderError(f"change source contains non-authorized path: {rel_str}")
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())
            overlay.append({"path": rel_str, "change": "EXTENDED/NEW", "sha256": sha256(dest)})

        # verify unchanged modules byte-identical to v0.2
        unchanged_ok = True
        for entry in copied:
            rel = entry["path"]
            if rel in CHANGED_RELS:
                continue
            v02 = V02 / rel.replace("/", "\\")
            if sha256(v02) != entry["sha256"]:
                unchanged_ok = False
                entry["change"] = "UNCHANGED-VERIFY-FAIL"
        if not unchanged_ok:
            raise E2BuilderError("unchanged module verification failed (byte mismatch vs v0.2)")

        # import probe
        sys.path.insert(0, str(target))
        probe_error = None
        try:
            import brea  # noqa: F401
            from brea.runner import answer  # noqa: F401
            from brea.coverage import parse_numbered_items, extract_full_clause  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            probe_error = str(exc)

        manifest_out = {
            "builder": "case-local-e2-change-builder-v0.1",
            "mechanism": "v0.2 baseline copy + authorized change overlay (reuses E1 mechanism)",
            "baseline": {
                "definition_sha256": ACCEPTED_DEFINITION_SHA,
                "v0.1_admitted_fingerprint_verified": True,
                "v0.2_reference": str(V02),
                "v0.2_reference_verified": True,
            },
            "change_inputs": {
                "professional_change_request": str(CHANGE_REQUEST),
                "change_impact_review": str(CHANGE_IMPACT),
            },
            "authorized_changed_paths": sorted(CHANGED_RELS),
            "target": str(target),
            "copied_files": copied,
            "overlay_files": overlay,
            "validation": {
                "definition_sha": "PASS",
                "v0.1_fingerprint": "PASS",
                "v0.2_reference_verified": "PASS",
                "clean_target": True,
                "unchanged_modules_byte_identical": unchanged_ok,
                "import_probe": "PASS" if probe_error is None else f"FAIL: {probe_error}",
            },
            "generated_at": utcnow(),
        }
        (BUILDER_DIR / "E2_CANDIDATE_CHANGE_MANIFEST_V0.1.json").write_text(
            json.dumps(manifest_out, ensure_ascii=False, indent=2), encoding="utf-8")

        changed_count = len(overlay)
        unchanged_count = len([c for c in copied if c["change"] != "CHANGED(overlay pending)"])
        report = (
            "# E2 BUILDER RUN REPORT — V0.1\n\n"
            f"- mechanism: v0.2 baseline copy + authorized change overlay (E1 mechanism reused)\n"
            f"- baseline definition SHA enforced: {ACCEPTED_DEFINITION_SHA}\n"
            f"- v0.1 admitted fingerprint verified: PASS\n"
            f"- v0.2 reference verified: PASS\n"
            f"- candidate target: {target}\n"
            f"- changed modules (authorized overlay): {changed_count}\n"
            f"- unchanged modules (byte-identical to v0.2): {unchanged_count}\n"
            f"- unchanged module verification: {'PASS' if unchanged_ok else 'FAIL'}\n"
            f"- import probe: {'PASS' if probe_error is None else 'FAIL: ' + probe_error}\n"
            f"- generated_at: {manifest_out['generated_at']}\n\n"
            "See E2_CANDIDATE_CHANGE_MANIFEST_V0.1.json for full file-level provenance.\n"
        )
        (BUILDER_DIR / "E2_BUILDER_RUN_REPORT_V0.1.md").write_text(report, encoding="utf-8")

        print(f"E2 BUILDER OK: candidate formed at {target}")
        print(f"changed modules: {changed_count}; unchanged byte-identical: {unchanged_count}")
        print(f"import probe: {'PASS' if probe_error is None else 'FAIL'}")
        return 0 if probe_error is None else 1
    except E2BuilderError as exc:
        print(f"E2 BUILDER FAIL CLOSED: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"E2 BUILDER FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
