from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from agent_runtime.contracts import Message, ModelResponse, ModelToolCall  # noqa: E402
from harness import (  # noqa: E402
    FailureClass,
    HarnessSession,
    HarnessTask,
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

CORRECT_SOURCE = """def is_valid_identifier(value):
    if not isinstance(value, str):
        return False
    return value.strip() != ""
"""
INCORRECT_SOURCE = """def is_valid_identifier(value):
    if not isinstance(value, str):
        return True
    return value.strip() != ""
"""


def call(name: str, arguments: dict, call_id: str) -> ModelResponse:
    return ModelResponse(
        tool_calls=(
            ModelToolCall(
                id=call_id,
                name=name,
                arguments=__import__("json").dumps(arguments),
            ),
        ),
        finish_reason="tool_calls",
    )


class ScriptedProvider:
    def __init__(self, responses, identity="scripted-test-model"):
        self.responses = list(responses)
        self.identity = identity
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("scripted provider exhausted")
        response = self.responses.pop(0)
        if callable(response):
            return response(request)
        return response


def task() -> HarnessTask:
    return HarnessTask(
        task_id="fixture-invalid-input-fail-closed",
        instruction=(
            "Change guard.py so invalid input fails closed. Do not modify unrelated "
            "behavior, then run the supplied deterministic test."
        ),
        verification_command=VERIFY_COMMAND,
    )


def make_session(provider, approval=lambda proposal: True, root=FIXTURE):
    return HarnessSession(
        task=task(),
        workspace=WorkspaceBoundary(root),
        model=provider,
        approval=approval,
        max_model_attempts=6,
    )


class HarnessProofTests(unittest.TestCase):
    def setUp(self):
        (FIXTURE / "guard.py").write_text(INCORRECT_SOURCE, encoding="utf-8")

    def test_bounded_task_passes_after_one_repair_with_actual_verification(self):
        provider = ScriptedProvider(
            [
                call("read", {"path": "guard.py"}, "read-1"),
                call("write", {"path": "guard.py", "content": INCORRECT_SOURCE}, "write-1"),
                call("write", {"path": "guard.py", "content": CORRECT_SOURCE}, "write-2"),
            ]
        )
        result = make_session(provider).run()

        self.assertEqual(result.status, "PASS")
        self.assertIsNone(result.failure_class)
        self.assertTrue(result.verification_passed)
        self.assertEqual(result.repair_cycles, 1)
        self.assertEqual(result.model_attempts, 3)
        self.assertLessEqual(result.repair_cycles, 1)
        self.assertIn("verification", [event["event"] for event in result.trace])
        self.assertEqual(result.session_id, result.trace[0]["session_id"])
        self.assertEqual(result.task_id, "fixture-invalid-input-fail-closed")
        self.assertEqual(result.workspace_root, str(FIXTURE.resolve()))
        self.assertEqual(result.model_identity, "scripted-test-model")
        assistant_messages = [
            message
            for message in provider.requests[1].messages
            if message.role == "assistant"
        ]
        self.assertEqual(assistant_messages[0].tool_calls[0].id, "read-1")
        approvals = [event for event in result.trace if event["event"] == "approval"]
        self.assertTrue(any(event["decision"] == "ALLOW" for event in approvals))

    def test_approval_deny_prevents_mutation(self):
        before = (FIXTURE / "guard.py").read_text(encoding="utf-8")
        provider = ScriptedProvider(
            [
                call("read", {"path": "guard.py"}, "read-1"),
                call("write", {"path": "guard.py", "content": CORRECT_SOURCE}, "write-1"),
            ]
        )
        result = make_session(provider, approval=lambda proposal: False).run()

        self.assertEqual(result.failure_class, FailureClass.APPROVAL_DENIED)
        self.assertEqual((FIXTURE / "guard.py").read_text(encoding="utf-8"), before)
        approvals = [event for event in result.trace if event["event"] == "approval"]
        self.assertEqual(approvals[-1]["decision"], "DENY")

    def test_workspace_rejects_traversal_and_absolute_outside_path(self):
        boundary = WorkspaceBoundary(FIXTURE)
        with self.assertRaises(Exception):
            boundary.read("../CATALYST_PLATFORM_MINIMUM_HARNESS_V0.1_STAGE_SPEC.md")
        with self.assertRaises(Exception):
            boundary.read(str((ROOT.parent / "outside.txt").resolve()))

    def test_workspace_rejects_symlink_escape_when_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "workspace"
            outside = Path(temp) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "secret.txt").write_text("secret", encoding="utf-8")
            link = root / "link"
            try:
                os.symlink(outside, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is not supported")
            with self.assertRaises(Exception):
                WorkspaceBoundary(root).read("link/secret.txt")

    def test_tool_boundary_is_minimal_and_workspace_bound(self):
        provider = ScriptedProvider([call("git", {}, "git-1")])
        result = make_session(provider).run()
        self.assertEqual(result.failure_class, FailureClass.TOOL_FAILED)
        self.assertEqual(result.available_tools, ("read", "write", "command"))
        self.assertNotIn("git", result.available_tools)

    def test_model_statement_is_not_verification(self):
        provider = ScriptedProvider([ModelResponse(content="I am done", finish_reason="stop")])
        result = make_session(provider).run()
        self.assertEqual(result.failure_class, FailureClass.MODEL_FAILED)
        self.assertFalse(result.verification_passed)
        self.assertNotIn("verification", [event["event"] for event in result.trace])

    def test_repair_exhaustion_is_explicit_and_never_unbounded(self):
        provider = ScriptedProvider(
            [
                call("read", {"path": "guard.py"}, "read-1"),
                call("write", {"path": "guard.py", "content": INCORRECT_SOURCE}, "write-1"),
                ModelResponse(content="I am done", finish_reason="stop"),
            ]
        )
        result = make_session(provider).run()
        self.assertEqual(result.failure_class, FailureClass.REPAIR_EXHAUSTED)
        self.assertEqual(result.repair_cycles, 1)
        self.assertLessEqual(result.model_attempts, 6)

    def test_h00_and_h10_classification_are_explicit(self):
        provider = ScriptedProvider([call("read", {"path": "guard.py"}, "read-1")])
        result = make_session(provider).run()
        self.assertEqual(result.responsibility_classification["ModelProvider"], "REUSED EXISTING NEUTRAL CONTRACT")
        self.assertEqual(result.responsibility_classification["HarnessSession"], "HARNESS RESPONSIBILITY")
        self.assertEqual(result.responsibility_classification["DeepSeekModelProvider"], "MODEL-SPECIFIC ADAPTER")
        self.assertEqual(result.responsibility_classification["WorkspaceBoundary"], "PRIVATE IMPLEMENTATION HOW")
        self.assertEqual(result.responsibility_classification["read/write/command"], "TOOL-SPECIFIC IMPLEMENTATION")
        self.assertFalse(result.governance_authority)

    def test_failure_classes_remain_distinguishable(self):
        expected = {
            "TASK_INVALID",
            "WORKSPACE_VIOLATION",
            "APPROVAL_DENIED",
            "MODEL_FAILED",
            "TOOL_FAILED",
            "COMMAND_TIMEOUT",
            "VERIFICATION_FAILED",
            "REPAIR_EXHAUSTED",
            "TRACE_INCOMPLETE",
        }
        self.assertEqual({failure.value for failure in FailureClass}, expected)


if __name__ == "__main__":
    unittest.main()
