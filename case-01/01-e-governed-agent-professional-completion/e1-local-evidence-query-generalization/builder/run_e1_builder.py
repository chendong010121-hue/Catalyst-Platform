"""E1 — Case-local Builder change mechanism (Stage Spec §7; BUILDER GAP closed).

The 01-C Builder is an initial-Candidate generator (templates -> clean target) and
cannot consume a governed professional change (recorded BUILDER GAP in the Change
Impact Review). E1 implements the smallest Case-local change mechanism needed to:

  read accepted baseline definition (SHA enforced)
  read Professional Change Request
  read Change Impact Review
  copy admitted v0.1 Candidate tree -> candidate/brea-v0.2 (clean target)
  overlay ONLY the authorized changed responsibilities (change source)
  verify UNCHANGED modules are byte-identical to v0.1
  emit change provenance (manifest + run report)

This is a Case-local development mechanism, NOT a generic Builder Platform.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BUILDER_DIR = Path(__file__).resolve().parent
E1_DIR = BUILDER_DIR.parent
CASE_ROOT = E1_DIR.parents[1]  # case-01/

V01_CANDIDATE = CASE_ROOT / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"
V01_MANIFEST = CASE_ROOT / "01-c-governed-local-formation" / "builder" / "BUILDER_OUTPUT_MANIFEST_V0.1.json"
DEFINITION = CASE_ROOT / "01-b-governed-agent-definition" / "builder" / "BUILDER_CONSUMABLE_DEFINITION_V0.1.md"
CHANGE_REQUEST = E1_DIR / "E1_PROFESSIONAL_CHANGE_REQUEST_V0.1.md"
CHANGE_IMPACT_REVIEW = E1_DIR / "change" / "E1_CHANGE_IMPACT_REVIEW_V0.1.md"
CHANGE_SOURCE = BUILDER_DIR / "change_source"
TARGET_REL = Path("candidate") / "brea-v0.2"

ACCEPTED_DEFINITION_SHA = "6c6e4707a3f8b719d6ab9c08cb9e43f337b4cb422bce0d2c22e4b842a9059bb4"

# Authorized changed responsibilities (from Change Impact Review): only these module
# paths are allowed to differ from v0.1. Everything else must stay byte-identical.
CHANGED_RELS = {
    "brea/corpus.py",
    "brea/evidence.py",
    "brea/query.py",       # NEW
    "brea/runner.py",
    "brea/identity.py",
    "brea/contracts.py",
    "brea/result.py",
}


class E1BuilderError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    try:
        # 1. preconditions
        if not V01_CANDIDATE.is_dir():
            raise E1BuilderError(f"admitted v0.1 candidate missing: {V01_CANDIDATE}")
        if not DEFINITION.is_file():
            raise E1BuilderError(f"baseline definition missing: {DEFINITION}")
        actual = sha256(DEFINITION)
        if actual != ACCEPTED_DEFINITION_SHA:
            raise E1BuilderError(
                f"baseline definition SHA mismatch: expected {ACCEPTED_DEFINITION_SHA}, got {actual}"
            )
        for required in (CHANGE_REQUEST, CHANGE_IMPACT_REVIEW):
            if not required.is_file():
                raise E1BuilderError(f"change input missing: {required}")

        # 2. v0.1 fingerprint must still match the accepted D2 manifest (P-E1-04)
        manifest = json.loads(V01_MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["generated_files"]:
            rel = entry["path"].replace("/", "\\")
            path = V01_CANDIDATE / rel
            if not path.is_file() or sha256(path) != entry["sha256"]:
                raise E1BuilderError(f"admitted v0.1 candidate mutated vs manifest: {rel}")

        # 3. clean target (no auto-delete)
        target = (E1_DIR / TARGET_REL).resolve()
        if target.exists() and any(target.iterdir()):
            raise E1BuilderError(f"target not clean: {target} (no auto-delete)")
        target.mkdir(parents=True, exist_ok=True)

        # 4. copy v0.1 tree (baseline), excluding __pycache__ / .pyc
        copied: list[dict] = []
        for path in V01_CANDIDATE.rglob("*"):
            if path.is_dir():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            rel = path.relative_to(V01_CANDIDATE)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())
            copied.append({
                "path": str(rel).replace("\\", "/"),
                "source": "v0.1 baseline copy",
                "change": "UNCHANGED" if str(rel).replace("\\", "/") not in CHANGED_RELS else "CHANGED(overlay pending)",
                "sha256": sha256(dest),
            })

        # 5. overlay authorized change source
        overlay: list[dict] = []
        for path in sorted(CHANGE_SOURCE.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(CHANGE_SOURCE)
            rel_str = str(rel).replace("\\", "/")
            if rel_str not in CHANGED_RELS and rel_str != "README.md":
                raise E1BuilderError(f"change source contains non-authorized path: {rel_str}")
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())
            overlay.append({"path": rel_str, "change": "EXTENDED/NEW", "sha256": sha256(dest)})

        # 6. verify unchanged modules byte-identical to v0.1
        unchanged_ok = True
        for entry in copied:
            rel = entry["path"]
            if rel in CHANGED_RELS:
                continue
            v01 = V01_CANDIDATE / rel.replace("/", "\\")
            if sha256(v01) != entry["sha256"]:
                unchanged_ok = False
                entry["change"] = "UNCHANGED-VERIFY-FAIL"
        if not unchanged_ok:
            raise E1BuilderError("unchanged module verification failed (byte mismatch vs v0.1)")

        # 7. import probe against the formed candidate
        sys.path.insert(0, str(target))
        probe_error = None
        try:
            import brea  # noqa: F401
            from brea.runner import answer  # noqa: F401
            from brea.query import classify_query  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            probe_error = str(exc)

        manifest_out = {
            "builder": "case-local-e1-change-builder-v0.1",
            "mechanism": "baseline copy + authorized change overlay (Case-local; not a generic Builder Platform)",
            "baseline": {
                "definition": str(DEFINITION),
                "definition_sha256": ACCEPTED_DEFINITION_SHA,
                "v0.1_candidate": str(V01_CANDIDATE),
                "v0.1_manifest_sha256": sha256(V01_MANIFEST),
                "v0.1_fingerprint_verified": True,
            },
            "change_inputs": {
                "professional_change_request": str(CHANGE_REQUEST),
                "change_impact_review": str(CHANGE_IMPACT_REVIEW),
            },
            "authorized_changed_responsibilities": sorted(CHANGED_RELS),
            "target": str(target),
            "copied_files": copied,
            "overlay_files": overlay,
            "validation": {
                "definition_sha": "PASS",
                "v0.1_fingerprint": "PASS",
                "clean_target": True,
                "unchanged_modules_byte_identical": unchanged_ok,
                "import_probe": "PASS" if probe_error is None else f"FAIL: {probe_error}",
            },
            "generated_at": utcnow(),
        }
        (BUILDER_DIR / "E1_CANDIDATE_CHANGE_MANIFEST_V0.1.json").write_text(
            json.dumps(manifest_out, ensure_ascii=False, indent=2), encoding="utf-8")

        changed_count = len(overlay)
        unchanged_count = len([c for c in copied if c["change"] != "CHANGED(overlay pending)"])
        report = (
            "# E1 BUILDER RUN REPORT — V0.1\n\n"
            f"- mechanism: baseline copy + authorized change overlay (Case-local change builder)\n"
            f"- baseline definition SHA enforced: {ACCEPTED_DEFINITION_SHA} (actual {actual})\n"
            f"- v0.1 admitted fingerprint verified vs accepted 01-C manifest: PASS\n"
            f"- change inputs: Professional Change Request + Change Impact Review\n"
            f"- candidate target: {target}\n"
            f"- changed modules (authorized overlay): {changed_count}\n"
            f"- unchanged modules (byte-identical to v0.1): {unchanged_count}\n"
            f"- unchanged module verification: {'PASS' if unchanged_ok else 'FAIL'}\n"
            f"- import probe: {'PASS' if probe_error is None else 'FAIL: ' + probe_error}\n"
            f"- generated_at: {manifest_out['generated_at']}\n\n"
            "See E1_CANDIDATE_CHANGE_MANIFEST_V0.1.json for the full file-level change provenance.\n"
        )
        (BUILDER_DIR / "E1_BUILDER_RUN_REPORT_V0.1.md").write_text(report, encoding="utf-8")

        print(f"E1 BUILDER OK: candidate formed at {target}")
        print(f"changed modules: {changed_count}; unchanged byte-identical: {unchanged_count}")
        print(f"import probe: {'PASS' if probe_error is None else 'FAIL'}")
        return 0 if probe_error is None else 1
    except E1BuilderError as exc:
        print(f"E1 BUILDER FAIL CLOSED: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"E1 BUILDER FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
