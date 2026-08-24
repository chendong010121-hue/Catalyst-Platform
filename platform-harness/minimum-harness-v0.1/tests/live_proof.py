from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MINIMUM_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
for path in (MINIMUM_ROOT, REPOSITORY_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent_runtime.providers.deepseek import DeepSeekModelProvider  # noqa: E402
from harness import HarnessSession, HarnessTask, WorkspaceBoundary  # noqa: E402


FIXTURE = MINIMUM_ROOT / "fixture"
INCORRECT_SOURCE = """def is_valid_identifier(value):
    if not isinstance(value, str):
        return True
    return value.strip() != ""
"""


def run_live_proof() -> dict:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return {
            "available": False,
            "status": "UNAVAILABLE",
            "provider": "DeepSeekModelProvider",
            "reason": "DEEPSEEK_API_KEY is unavailable",
        }

    (FIXTURE / "guard.py").write_text(INCORRECT_SOURCE, encoding="utf-8")
    provider = DeepSeekModelProvider(api_key=key, timeout=30.0)
    task = HarnessTask(
        task_id="fixture-invalid-input-fail-closed-live",
        instruction=(
            "Change guard.py so invalid input fails closed. Do not modify unrelated "
            "behavior, then run the supplied deterministic test."
        ),
        verification_command=(
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            ".",
            "-p",
            "test_*.py",
        ),
    )
    result = HarnessSession(
        task=task,
        workspace=WorkspaceBoundary(FIXTURE),
        model=provider,
        approval=lambda proposal: True,
        max_model_attempts=6,
    ).run()
    return {
        "available": True,
        "status": "PASS" if result.status == "PASS" else "FAILED",
        "provider": "DeepSeekModelProvider",
        "failure_class": result.failure_class.value if result.failure_class else None,
        "model_attempts": result.model_attempts,
        "repair_cycles": result.repair_cycles,
        "result": result.as_dict(),
    }


if __name__ == "__main__":
    print(json.dumps(run_live_proof(), ensure_ascii=False, sort_keys=True))
