"""Run Builder proof tests BT-01..BT-10 (stdlib only)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_builder  # noqa: E402


def main() -> int:
    print("== CASE 01-C Builder proof tests (BT-01..BT-10) ==")
    failures = test_builder.run_all()
    print(f"== RESULT: {'PASS' if failures == 0 else f'FAIL ({failures})'} ==")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
