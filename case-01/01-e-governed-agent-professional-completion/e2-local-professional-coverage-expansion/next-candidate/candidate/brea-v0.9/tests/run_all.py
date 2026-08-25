"""Run all candidate tests without pytest (stdlib only)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import test_cases  # noqa: E402
import test_seams  # noqa: E402
import test_structural  # noqa: E402


def main() -> int:
    failures = 0
    print("== BREA v0.9-candidate retained regression ==")
    for module in (test_structural, test_seams, test_cases):
        print(f"-- {module.__name__} --")
        failures += module.run_all()
    print(f"== RESULT: {'PASS' if failures == 0 else f'FAIL ({failures})'} ==")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
