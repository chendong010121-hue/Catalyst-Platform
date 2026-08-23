"""D2 — deterministic implementation fingerprint (G-A03).

For each Candidate file DECLARED by the accepted 01-C BUILDER_OUTPUT_MANIFEST:
    relative_path + SHA256(file bytes)
sorted by relative_path -> canonical list -> aggregate SHA256(canonical list).
Also SHA256(BUILDER_OUTPUT_MANIFEST_V0.1.json).
Excludes __pycache__ / logs / raw corpus (not declared as Candidate implementation files).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CASE_ROOT = Path(r"E:\试验场地\Agent Harness\case-01")
MANIFEST = CASE_ROOT / "01-c-governed-local-formation" / "builder" / "BUILDER_OUTPUT_MANIFEST_V0.1.json"
CANDIDATE = CASE_ROOT / "01-c-governed-local-formation" / "candidate" / "brea-v0.1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    declared = []
    for entry in manifest["generated_files"]:
        rel = entry["path"].replace("/", "\\")
        path = CANDIDATE / rel
        if not path.is_file():
            print(f"DECLARED CANDIDATE FILE MISSING: {rel}")
            return 1
        actual = sha256_file(path)
        recorded = entry["sha256"].lower()
        if actual != recorded:
            print(f"CANDIDATE FILE CHANGED vs manifest: {rel} (actual {actual} != recorded {recorded})")
            return 1
        declared.append((rel.replace("\\", "/"), actual))
    declared.sort(key=lambda pair: pair[0])
    canonical = "\n".join(f"{rel}\t{h}" for rel, h in declared)
    tree_sha = sha256_bytes(canonical.encode("utf-8"))
    manifest_sha = sha256_file(MANIFEST)
    out = {
        "candidate_tree_sha256": tree_sha,
        "builder_output_manifest_sha256": manifest_sha,
        "declared_file_count": len(declared),
        "declared_files": [{"path": rel, "sha256": h} for rel, h in declared],
        "method": "sorted(relative_path+SHA256(bytes)) -> canonical list -> aggregate SHA256; plus SHA256(manifest)",
    }
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else CASE_ROOT / "01-d-governed-agent-admission-binding" / "d2-local-admission-binding" / "scripts" / "implementation_fingerprint.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"candidate_tree_sha256 = {tree_sha}")
    print(f"builder_output_manifest_sha256 = {manifest_sha}")
    print(f"declared files = {len(declared)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
