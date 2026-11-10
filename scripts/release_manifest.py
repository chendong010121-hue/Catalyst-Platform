"""Write or check the release identity of this capability line. Zero API, zero model.

    PYTHONUTF8=1 python scripts/release_manifest.py --write
    PYTHONUTF8=1 python scripts/release_manifest.py --check

`--write` recomputes every field from bytes in this tree and writes the JSON.
`--check` recomputes and compares; it exits 1 and prints every difference, so a file that
no longer describes the tree beside it cannot pass as the release.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from catalyst_platform.capability_release import differences, manifest  # noqa: E402

TARGET = ROOT / "docs" / "engineering" / "CAPABILITY_RELEASE_20261103.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write the release JSON")
    parser.add_argument("--check", action="store_true", help="compare the file with the tree")
    parser.add_argument("--path", type=Path, default=TARGET)
    args = parser.parse_args(argv)
    if args.write == args.check:
        parser.error("name exactly one of --write / --check")

    current = manifest(ROOT)
    if args.write:
        args.path.parent.mkdir(parents=True, exist_ok=True)
        args.path.write_bytes(
            (json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        print(f"wrote {args.path.relative_to(ROOT)}")
        return 0

    if not args.path.is_file():
        print(f"missing {args.path}", file=sys.stderr)
        return 1
    stored = json.loads(args.path.read_text(encoding="utf-8"))
    diff = differences(stored, current)
    if diff:
        print(f"{args.path.name} no longer describes this tree:", file=sys.stderr)
        for line in diff[:40]:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"{args.path.name} matches this tree ({current['product']['implementation_sha256'][:12]}"
          f", method {current['method']['package_sha256'][:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
