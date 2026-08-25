from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
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

from agent_runtime.contracts import ModelResponse, ModelToolCall  # noqa: E402
from harness import (  # noqa: E402
    ApprovalPolicy,
    CredentialResolver,
    CredentialSourceType,
    ExecutionEnvironmentPreflight,
    ExecutionPolicy,
    FailureClass,
    HarnessSession,
    HarnessTask,
    ProcessEnvironmentCredentialSource,
    ProviderBinding,
    SanitizedCommandRunner,
    UserLocalCredentialSource,
    WorkspaceBoundary,
    setup_user_local_credential,
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
INSPECT_COMMAND = (
    sys.executable,
    "-c",
    "import json, os; print(json.dumps({'deepseek': bool(os.environ.get('DEEPSEEK_API_KEY')), 'synthetic': bool(os.environ.get('CATALYST_SYNTHETIC_SECRET')), 'path': bool(os.environ.get('PATH'))}))",
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


def tool_call(name: str, arguments: dict, call_id: str) -> ModelResponse:
    return ModelResponse(
        tool_calls=(
            ModelToolCall(
                id=call_id,
                name=name,
                arguments=json.dumps(arguments),
            ),
        ),
        finish_reason="tool_calls",
    )


class ScriptedProvider:
    identity = "scripted-environment-proof"

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("scripted provider exhausted")
        return self.responses.pop(0)


def make_task() -> HarnessTask:
    return HarnessTask(
        task_id="environment-fixture-invalid-input-fail-closed",
        instruction=(
            "Change guard.py so invalid input fails closed. Do not modify unrelated "
            "behavior, then run the supplied deterministic test."
        ),
        verification_command_id="verify",
    )


def make_policy() -> ExecutionPolicy:
    return ExecutionPolicy(
        allowed_read_paths=("TASK.md", "guard.py", "test_guard.py"),
        allowed_write_paths=("guard.py",),
        commands={"verify": VERIFY_COMMAND, "inspect-env": INSPECT_COMMAND},
        command_timeout=10,
        max_model_attempts=6,
        max_repair_cycles=1,
        task_environment={"CATALYST_TASK_MODE": "environment-proof"},
    )


def make_preflight(root, policy, resolver, binding=None):
    return ExecutionEnvironmentPreflight(
        workspace_root=root,
        policy=policy,
        provider_binding=binding
        or ProviderBinding("deepseek", "deepseek-v4-flash", "deepseek.default"),
        credential_resolver=resolver,
    )


def make_session(provider, env=None, approval=lambda proposal: True, root=FIXTURE):
    env = dict(env or {"DEEPSEEK_API_KEY": "synthetic-provider-secret"})
    policy = make_policy()
    resolver = CredentialResolver(
        sources=(
            ProcessEnvironmentCredentialSource(environment=env),
            UserLocalCredentialSource(path=ROOT / "tests" / "missing-credentials.json"),
        )
    )
    preflight = make_preflight(root, policy, resolver)
    return HarnessSession(
        task=make_task(),
        workspace=WorkspaceBoundary(root),
        model=provider,
        approval_policy=ApprovalPolicy(approval),
        execution_policy=policy,
        preflight=preflight,
    )


class EnvironmentInfrastructureTests(unittest.TestCase):
    def setUp(self):
        (FIXTURE / "guard.py").write_text(INCORRECT_SOURCE, encoding="utf-8")

    def test_e01_preflight_ready_without_model_call(self):
        provider = ScriptedProvider([])
        policy = make_policy()
        resolver = CredentialResolver(
            sources=(ProcessEnvironmentCredentialSource({"DEEPSEEK_API_KEY": "synthetic"}),)
        )
        result = make_preflight(FIXTURE, policy, resolver).check()
        self.assertEqual(result.status, "READY")
        self.assertEqual(result.reasons, ())
        self.assertEqual(provider.requests, [])

    def test_e02_preflight_blocked_reasons_are_distinguishable(self):
        policy = make_policy()
        missing = CredentialResolver(
            sources=(ProcessEnvironmentCredentialSource({}),)
        )
        self.assertIn(
            "CREDENTIAL_UNAVAILABLE",
            make_preflight(FIXTURE, policy, missing).check().reasons,
        )
        self.assertIn(
            "WORKSPACE_INVALID",
            make_preflight(ROOT / "missing-workspace", policy, missing).check().reasons,
        )
        invalid_policy = ExecutionPolicy(
            allowed_read_paths=("../outside",),
            allowed_write_paths=("guard.py",),
            commands={"verify": ("missing-executable-for-proof",)},
            command_timeout=10,
            max_model_attempts=6,
            max_repair_cycles=1,
            task_environment={},
        )
        reasons = make_preflight(FIXTURE, invalid_policy, missing).check().reasons
        self.assertTrue({"POLICY_INVALID", "EXECUTABLE_UNAVAILABLE"} & set(reasons))

    def test_e03_user_local_credential_resolves_in_fresh_process_without_env(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Path(temp) / "credentials.json"
            setup_user_local_credential(
                "deepseek.default", path=store, input_function=lambda _: "fresh-secret"
            )
            child_env = dict(os.environ)
            child_env.pop("DEEPSEEK_API_KEY", None)
            completed = subprocess.run(
                [sys.executable, str(ROOT / "tests" / "fresh_credential_probe.py"), str(store)],
                cwd=REPOSITORY_ROOT,
                env=child_env,
                capture_output=True,
                text=True,
                check=True,
            )
            evidence = json.loads(completed.stdout)
            self.assertTrue(evidence["fresh_process"])
            self.assertFalse(evidence["process_env_deepseek_api_key"])
            self.assertEqual(evidence["credential_source_type"], "USER_LOCAL")
            self.assertTrue(evidence["credential_resolved"])
            self.assertNotIn("fresh-secret", completed.stdout)

    def test_e04_process_environment_source_resolves(self):
        resolution = CredentialResolver(
            sources=(ProcessEnvironmentCredentialSource({"DEEPSEEK_API_KEY": "synthetic"}),)
        ).resolve("deepseek.default")
        self.assertEqual(resolution.source_type, CredentialSourceType.PROCESS_ENVIRONMENT)
        self.assertEqual(resolution.value, "synthetic")

    def test_e05_tool_environment_excludes_provider_and_synthetic_secrets(self):
        policy = make_policy()
        parent_environment = dict(os.environ)
        parent_environment.update(
            {
                "DEEPSEEK_API_KEY": "provider-secret",
                "CATALYST_SYNTHETIC_SECRET": "synthetic-secret",
            }
        )
        runner = SanitizedCommandRunner(
            workspace=WorkspaceBoundary(FIXTURE),
            policy=policy,
            parent_environment=parent_environment,
        )
        result = runner.run("inspect-env")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            json.loads(result.stdout),
            {"deepseek": False, "path": True, "synthetic": False},
        )

    def test_e06_approval_cannot_widen_execution_policy(self):
        provider = ScriptedProvider(
            [
                tool_call("write", {"path": "outside.py", "content": "x"}, "write-1"),
                tool_call("command", {"command": "not-declared"}, "command-1"),
            ]
        )
        result = make_session(provider, approval=lambda proposal: True).run()
        self.assertEqual(result.failure_class, FailureClass.EXECUTION_POLICY_DENIED)
        self.assertFalse((FIXTURE / "outside.py").exists())
        self.assertFalse(any(event.get("event") == "approval" for event in result.trace))

        command_result = make_session(
            ScriptedProvider([tool_call("command", {"command": "not-declared"}, "command-1")]),
            approval=lambda proposal: True,
        ).run()
        self.assertEqual(command_result.failure_class, FailureClass.EXECUTION_POLICY_DENIED)
        self.assertFalse(any(event.get("event") == "approval" for event in command_result.trace))

    def test_e06_authorized_verification_command_is_bound_and_executes(self):
        (FIXTURE / "guard.py").write_text(CORRECT_SOURCE, encoding="utf-8")
        provider = ScriptedProvider(
            [
                tool_call("command", {"command": "verify"}, "command-1"),
                tool_call("write", {"path": "guard.py", "content": CORRECT_SOURCE}, "write-1"),
            ]
        )
        result = make_session(provider, approval=lambda proposal: True).run()
        self.assertEqual(result.status, "PASS")
        command_tool = next(tool for tool in provider.requests[0].tools if tool.name == "command")
        self.assertEqual(
            command_tool.parameters["properties"]["command"]["enum"],
            ["verify"],
        )
        self.assertTrue(
            any(
                event.get("event") == "command_result" and event.get("status") == "PASS"
                for event in result.trace
            )
        )

    def test_e07_approval_still_governs_allowed_mutation(self):
        before = (FIXTURE / "guard.py").read_text(encoding="utf-8")
        denied = make_session(
            ScriptedProvider([tool_call("write", {"path": "guard.py", "content": CORRECT_SOURCE}, "write-1")]),
            approval=lambda proposal: False,
        ).run()
        self.assertEqual(denied.failure_class, FailureClass.APPROVAL_DENIED)
        self.assertEqual((FIXTURE / "guard.py").read_text(encoding="utf-8"), before)

        allowed = make_session(
            ScriptedProvider(
                [
                    tool_call("read", {"path": "guard.py"}, "read-1"),
                    tool_call("write", {"path": "guard.py", "content": CORRECT_SOURCE}, "write-1"),
                ]
            ),
            approval=lambda proposal: True,
        ).run()
        self.assertEqual(allowed.status, "PASS")
        self.assertTrue(allowed.verification_passed)

    def test_e08_candidate_preserves_bounded_v01_behavior(self):
        result = make_session(
            ScriptedProvider(
                [
                    tool_call("read", {"path": "guard.py"}, "read-1"),
                    tool_call("write", {"path": "guard.py", "content": INCORRECT_SOURCE}, "write-1"),
                    tool_call("write", {"path": "guard.py", "content": CORRECT_SOURCE}, "write-2"),
                ]
            )
        ).run()
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.repair_cycles, 1)
        self.assertLessEqual(result.model_attempts, 6)
        events = [event["event"] for event in result.trace]
        for required in ("task_start", "model_turn", "tool_proposed", "approval", "verification", "final_result"):
            self.assertIn(required, events)
        self.assertFalse(result.governance_authority)

    def test_e10_identity_is_non_secret_and_has_required_fields(self):
        result = make_session(ScriptedProvider([ModelResponse(content="done", finish_reason="stop")])).run()
        identity = result.identity_snapshot
        for field in (
            "harness_implementation_version",
            "harness_source_revision",
            "python_version",
            "os_name",
            "os_release_or_platform_family",
            "architecture",
            "workspace_root",
            "provider_id",
            "model_id",
            "credential_source_type",
            "execution_policy_identity",
            "preflight_status",
        ):
            self.assertIn(field, identity)
        serialized = json.dumps(result.as_dict(), ensure_ascii=False)
        self.assertNotIn("synthetic-provider-secret", serialized)
        self.assertNotIn("credentials.json", serialized)

    def test_setup_uses_hidden_input_and_prints_only_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                setup_user_local_credential(
                    "deepseek.default",
                    path=Path(temp) / "credentials.json",
                    input_function=lambda _: "hidden-secret",
                )
            self.assertNotIn("hidden-secret", output.getvalue())
            self.assertIn("deepseek.default", output.getvalue())
            self.assertIn("USER_LOCAL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
