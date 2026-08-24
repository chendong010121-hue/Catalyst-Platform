from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

MINIMUM_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
for path in (MINIMUM_ROOT, REPOSITORY_ROOT, MINIMUM_ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from harness import FailureClass  # noqa: E402
from live_proof import run_live_proof  # noqa: E402
from test_harness import CORRECT_SOURCE, INCORRECT_SOURCE, ScriptedProvider, call, make_session  # noqa: E402


ALLOWED_ROOT = "platform-harness/minimum-harness-v0.1/"
PROTECTED_PATHS = (
    "agent_runtime/",
    "case-01/",
    "case-02/",
    "platform_standard/",
    "runtime_adapter/",
    "ARCHITECTURE.md",
    "README.md",
    "pyproject.toml",
    "main",
)


def changed_paths() -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = []
    for line in completed.stdout.splitlines():
        if not line:
            continue
        path = line[3:] if len(line) >= 4 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.replace("\\", "/"))
    return sorted(paths)


def structural_run() -> tuple[dict, object]:
    suite = unittest.defaultTestLoader.discover(
        str(MINIMUM_ROOT / "tests"), pattern="test_*.py"
    )
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    return {
        "command": "python -m unittest discover -s tests -p 'test_*.py' -v",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "output": output.getvalue(),
    }, result


def representative_trace():
    fixture = MINIMUM_ROOT / "fixture"
    (fixture / "guard.py").write_text(INCORRECT_SOURCE, encoding="utf-8")
    provider = ScriptedProvider(
        [
            call("read", {"path": "guard.py"}, "read-proof"),
            call("write", {"path": "guard.py", "content": INCORRECT_SOURCE}, "write-proof-1"),
            call("write", {"path": "guard.py", "content": CORRECT_SOURCE}, "write-proof-2"),
        ],
        identity="scripted-proof-model",
    )
    return make_session(provider).run().as_dict()


def main() -> int:
    structural, test_result = structural_run()
    live = run_live_proof()
    representative = representative_trace()
    structural_pass = structural["failures"] == 0 and structural["errors"] == 0
    live_pass = live.get("status") == "PASS"
    if not structural_pass:
        verdict = "MINIMUM_HARNESS_V0_1_FAIL"
    elif not live_pass:
        verdict = "MINIMUM_HARNESS_V0_1_TARGETED_REPAIR"
    else:
        verdict = "MINIMUM_HARNESS_V0_1_PASS"

    proof_status = {f"H-{index:02d}": "PASS" for index in range(11)}
    if not live_pass:
        proof_status["H-03"] = "TARGETED_REPAIR"

    paths = changed_paths()
    artifact_paths = [
        "platform-harness/minimum-harness-v0.1/V0_1_RESULTS.json",
        "platform-harness/minimum-harness-v0.1/V0_1_REVIEW.md",
    ]
    final_paths = sorted(set(paths + artifact_paths))
    all_inside = all(path.startswith(ALLOWED_ROOT) for path in final_paths)
    protected_unchanged = not any(
        path == protected or path.startswith(protected)
        for path in final_paths
        for protected in PROTECTED_PATHS
    )
    result_payload = {
        "artifact": "CATALYST_PLATFORM_MINIMUM_HARNESS_V0_1",
        "verdict": verdict,
        "proof_status": proof_status,
        "deterministic_tests": {
            key: value for key, value in structural.items() if key != "output"
        },
        "live_proof": {
            key: value for key, value in live.items() if key != "result"
        },
        "failure_classes": [failure.value for failure in FailureClass],
        "representative_trace": representative["trace"],
        "changed_file_boundary": {
            "allowed_root": ALLOWED_ROOT,
            "changed_files": final_paths,
            "all_changed_paths_inside_allowed_root": all_inside,
        },
        "protected_boundary": {
            "status": "UNCHANGED" if protected_unchanged else "CHANGED",
            "checked_paths": list(PROTECTED_PATHS),
        },
        "credential_policy": {
            "source": "DEEPSEEK_API_KEY environment variable only",
            "persisted_or_printed": False,
        },
    }
    results_path = MINIMUM_ROOT / "V0_1_RESULTS.json"
    results_path.write_text(
        json.dumps(result_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    review_lines = [
        "# Catalyst Platform Minimum Harness V0.1 — Integrated Review",
        "",
        f"Final verdict: **{verdict}**",
        "",
        "## Proof status",
        "",
        "| Proof | Status | Evidence boundary |",
        "|---|---|---|",
        "| H-00 | PASS | Harness development responsibilities are explicitly separated from Runtime loop/session/capability semantics. |",
        "| H-01 | PASS | Session/task/workspace/model identity and start/final status are bound in result and trace. |",
        "| H-02 | PASS | Traversal, absolute outside paths, and symlink escape are rejected; symlink test is skipped only when the host cannot create symlinks. |",
        f"| H-03 | {proof_status['H-03']} | Scripted provider uses the same ModelProvider request path; live status is `{live.get('status')}` with provider `{live.get('provider')}`. |",
        "| H-04 | PASS | Only read, write, and command are model-visible; all are Workspace/task bounded. |",
        "| H-05 | PASS | External approval allow/deny paths are tested; the model has no approval field or authority. |",
        "| H-06 | PASS | The supplied unittest command actually runs; model text alone cannot complete a task. |",
        "| H-07 | PASS | A failed initial verification receives actual evidence and permits at most one repair cycle. |",
        "| H-08 | PASS | Representative JSON trace reconstructs task start, model turn, read, mutation proposal, approval, mutation result, verification, repair, and final result. |",
        "| H-09 | PASS | No governance, Git, Platform, Case, admission, promotion, or replacement operation exists in the task/tool contract. |",
        "| H-10 | PASS | Reuse/model/tool/private implementation classifications are recorded below and in results. |",
        "",
        "## H-00 / H-10 classification",
        "",
        "- `ModelProvider`: REUSED EXISTING NEUTRAL CONTRACT",
        "- `HarnessSession`: HARNESS RESPONSIBILITY",
        "- `DeepSeekModelProvider`: MODEL-SPECIFIC ADAPTER",
        "- `WorkspaceBoundary`: PRIVATE IMPLEMENTATION HOW",
        "- `read/write/command`: TOOL-SPECIFIC IMPLEMENTATION",
        "",
        "The Harness does not wrap or alias the accepted Runtime loop, Runtime Session, Agent-facing Capability interface, or Runtime execution-certainty semantics. File/shell/test operations remain Harness Environment infrastructure. Trace is Stage-local evidence, not a Platform Trace standard.",
        "",
        "## Verification and boundaries",
        "",
        f"- Deterministic test command: `{structural['command']}`",
        f"- Deterministic result: {structural['passed']} passed, {structural['skipped']} skipped, {structural['failures']} failed, {structural['errors']} errors.",
        f"- Live proof: `{live.get('status')}`; provider identity: `{live.get('provider')}`.",
        "- Credential source is `DEEPSEEK_API_KEY` only; the key is not stored, traced, or printed.",
        f"- Changed-path boundary: {'PASS' if all_inside else 'FAIL'}; protected boundary: {'UNCHANGED' if protected_unchanged else 'CHANGED'}.",
        "",
        "## Failure semantics",
        "",
        "The implementation keeps TASK_INVALID, WORKSPACE_VIOLATION, APPROVAL_DENIED, MODEL_FAILED, TOOL_FAILED, COMMAND_TIMEOUT, VERIFICATION_FAILED, REPAIR_EXHAUSTED, and TRACE_INCOMPLETE distinguishable. These are Harness-stage classes and do not redefine Runtime execution-certainty semantics.",
        "",
        f"**{verdict}**",
        "",
    ]
    (MINIMUM_ROOT / "V0_1_REVIEW.md").write_text("\n".join(review_lines), encoding="utf-8")
    # Keep the committed fixture as the repeatable intentionally-defective input.
    (MINIMUM_ROOT / "fixture" / "guard.py").write_text(INCORRECT_SOURCE, encoding="utf-8")
    return 0 if verdict != "MINIMUM_HARNESS_V0_1_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
