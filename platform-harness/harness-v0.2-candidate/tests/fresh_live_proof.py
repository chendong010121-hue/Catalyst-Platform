from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
for path in (ROOT, REPOSITORY_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent_runtime.providers.deepseek import DeepSeekModelProvider  # noqa: E402
from harness import (  # noqa: E402
    ApprovalPolicy,
    CredentialResolver,
    ExecutionEnvironmentPreflight,
    ExecutionPolicy,
    HarnessSession,
    HarnessTask,
    ProviderBinding,
    UserLocalCredentialSource,
    WorkspaceBoundary,
)


FIXTURE = ROOT / "fixture"
VERIFY_COMMAND = (
    sys.executable,
    "-m",
    "unittest",
    "discover",
    "-s",
    ".",
    "-p",
    "test_*.py",
)


def make_policy() -> ExecutionPolicy:
    return ExecutionPolicy(
        allowed_read_paths=("TASK.md", "guard.py", "test_guard.py"),
        allowed_write_paths=("guard.py",),
        commands={"verify": VERIFY_COMMAND},
        command_timeout=10,
        max_model_attempts=6,
        max_repair_cycles=1,
        task_environment={"CATALYST_TASK_MODE": "environment-proof-live"},
    )


def run() -> dict:
    binding = ProviderBinding("deepseek", "deepseek-v4-flash", "deepseek.default")
    policy = make_policy()
    resolver = CredentialResolver(
        sources=(UserLocalCredentialSource(),)
    )
    preflight = ExecutionEnvironmentPreflight(
        workspace_root=FIXTURE,
        policy=policy,
        provider_binding=binding,
        credential_resolver=resolver,
    )
    readiness = preflight.check()
    base = {
        "fresh_process": True,
        "process_env_deepseek_api_key": bool(os.environ.get("DEEPSEEK_API_KEY")),
        "provider": "DeepSeekModelProvider",
        "provider_id": binding.provider_id,
        "model_id": binding.model_id,
        "credential_ref": binding.credential_ref,
        "preflight": readiness.as_dict(),
    }
    if readiness.status != "READY":
        base.update({"status": "BLOCKED", "failure": readiness.reasons})
        return base

    resolution = readiness.credential_resolution
    provider = DeepSeekModelProvider(
        api_key=resolution.value,
        model=binding.model_id,
        timeout=30.0,
    )
    task = HarnessTask(
        task_id="environment-fixture-invalid-input-fail-closed-live",
        instruction=(
            "Change guard.py so invalid input fails closed. Do not modify unrelated "
            "behavior, then run the supplied deterministic test."
        ),
        verification_command_id="verify",
    )
    result = HarnessSession(
        task=task,
        workspace=WorkspaceBoundary(FIXTURE),
        model=provider,
        approval_policy=ApprovalPolicy(lambda proposal: True),
        execution_policy=policy,
        preflight=preflight,
    ).run()
    base.update(
        {
            "status": "PASS" if result.status == "PASS" else "FAILED",
            "model_attempts": result.model_attempts,
            "repair_cycles": result.repair_cycles,
            "result": result.as_dict(),
        }
    )
    return base


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))
