from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixture"
INCORRECT_SOURCE = """def is_valid_identifier(value):
    if not isinstance(value, str):
        return True
    return value.strip() != ""
"""


def run_live_proof() -> dict:
    (FIXTURE / "guard.py").write_text(INCORRECT_SOURCE, encoding="utf-8")
    child_environment = dict(os.environ)
    child_environment.pop("DEEPSEEK_API_KEY", None)
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tests" / "fresh_live_proof.py")],
            cwd=REPOSITORY_ROOT,
            env=child_environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return {"status": "FAILED", "failure": "fresh proof process failed"}
        return json.loads(completed.stdout)
    finally:
        (FIXTURE / "guard.py").write_text(INCORRECT_SOURCE, encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run_live_proof(), ensure_ascii=False, sort_keys=True))
