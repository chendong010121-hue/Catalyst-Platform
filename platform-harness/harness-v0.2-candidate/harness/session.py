from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from agent_runtime.contracts import Message, ModelRequest, ModelToolDefinition

from .environment import SanitizedCommandRunner
from .policy import ActionProposal, ApprovalPolicy, ExecutionPolicy
from .preflight import ExecutionEnvironmentPreflight, ProviderBinding
from .workspace import WorkspaceBoundary, WorkspaceViolation


class FailureClass(str, Enum):
    TASK_INVALID = "TASK_INVALID"
    WORKSPACE_VIOLATION = "WORKSPACE_VIOLATION"
    APPROVAL_DENIED = "APPROVAL_DENIED"
    MODEL_FAILED = "MODEL_FAILED"
    TOOL_FAILED = "TOOL_FAILED"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REPAIR_EXHAUSTED = "REPAIR_EXHAUSTED"
    TRACE_INCOMPLETE = "TRACE_INCOMPLETE"
    PRECHECK_BLOCKED = "PRECHECK_BLOCKED"
    EXECUTION_POLICY_DENIED = "EXECUTION_POLICY_DENIED"


@dataclass(frozen=True)
class HarnessTask:
    task_id: str
    instruction: str
    verification_command_id: str


@dataclass
class HarnessResult:
    status: str
    session_id: str
    task_id: str
    workspace_root: str
    model_identity: str
    start_status: str
    final_status: str
    failure_class: FailureClass | None
    verification_passed: bool
    repair_cycles: int
    model_attempts: int
    available_tools: tuple[str, ...]
    governance_authority: bool
    identity_snapshot: dict[str, str]
    preflight: dict[str, Any]
    trace: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "workspace_root": self.workspace_root,
            "model_identity": self.model_identity,
            "start_status": self.start_status,
            "final_status": self.final_status,
            "verification_passed": self.verification_passed,
            "repair_cycles": self.repair_cycles,
            "model_attempts": self.model_attempts,
            "available_tools": list(self.available_tools),
            "governance_authority": self.governance_authority,
            "identity_snapshot": self.identity_snapshot,
            "preflight": self.preflight,
            "trace": self.trace,
        }


_READ_TOOL = ModelToolDefinition(
    name="read",
    description="Read one authorized UTF-8 text file in the Workspace.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    },
)

_WRITE_TOOL = ModelToolDefinition(
    name="write",
    description="Propose replacement text for one ExecutionPolicy-authorized file; external approval is required.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
)


def _tools_for_verification(verification_command_id: str) -> tuple[ModelToolDefinition, ...]:
    return (
        _READ_TOOL,
        _WRITE_TOOL,
        ModelToolDefinition(
            name="command",
            description=(
                "Run the fixed Stage-declared verification command identity only; "
                "external approval is required."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": [verification_command_id],
                    }
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        ),
    )


class HarnessSession:
    """Environment-complete bounded development task, distinct from Runtime Session."""

    def __init__(
        self,
        *,
        task: HarnessTask,
        workspace: WorkspaceBoundary,
        model,
        approval_policy: ApprovalPolicy,
        execution_policy: ExecutionPolicy,
        preflight: ExecutionEnvironmentPreflight,
        provider_binding: ProviderBinding | None = None,
        parent_environment: Mapping[str, str] | None = None,
    ) -> None:
        if not callable(getattr(model, "request", None)):
            raise TypeError("model must satisfy the existing ModelProvider contract")
        self.task = task
        self.workspace = workspace
        self.model = model
        self.approval_policy = approval_policy
        self.execution_policy = execution_policy
        self.preflight = preflight
        self.provider_binding = provider_binding or preflight.provider_binding
        self._tools = _tools_for_verification(task.verification_command_id)
        self.runner = SanitizedCommandRunner(
            workspace=workspace,
            policy=execution_policy,
            parent_environment=parent_environment,
        )
        self.session_id = uuid.uuid4().hex
        self.model_identity = str(getattr(model, "identity", type(model).__name__))

    @property
    def available_tools(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self._tools)

    def run(self) -> HarnessResult:
        trace: list[dict[str, Any]] = []
        preflight = self.preflight.check()
        self._event(trace, "task_start", status=preflight.status)
        if preflight.status != "READY":
            return self._finish(
                trace,
                attempts=0,
                repair_cycles=0,
                verification_passed=False,
                failure=FailureClass.PRECHECK_BLOCKED,
                preflight=preflight,
            )

        attempts = 0
        repair_cycles = 0
        verification_passed = False
        last_failure: FailureClass | None = None
        messages = [
            Message(
                role="system",
                content=(
                    "You are a bounded development model. Use only the supplied tools. "
                    "Never claim completion without successful deterministic verification."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Authorized task {self.task.task_id}: {self.task.instruction}\n"
                    "Use only authorized files and declared commands. One repair cycle is permitted."
                ),
            ),
        ]

        while attempts < self.execution_policy.max_model_attempts:
            attempts += 1
            try:
                response = self.model.request(
                    ModelRequest(messages=tuple(messages), tools=self._tools, tool_choice="auto")
                )
            except Exception:
                last_failure = FailureClass.MODEL_FAILED
                self._event(trace, "model_turn", attempt=attempts, status="FAILED")
                break
            self._event(trace, "model_turn", attempt=attempts, status="RECEIVED", tool_calls=len(response.tool_calls))
            if len(response.tool_calls) != 1:
                last_failure = FailureClass.REPAIR_EXHAUSTED if repair_cycles else FailureClass.MODEL_FAILED
                break
            call = response.tool_calls[0]
            messages.append(Message(role="assistant", content=response.content, tool_calls=tuple(response.tool_calls)))
            try:
                arguments = json.loads(call.arguments)
            except (TypeError, json.JSONDecodeError):
                last_failure = FailureClass.MODEL_FAILED
                break
            if not isinstance(arguments, dict):
                last_failure = FailureClass.MODEL_FAILED
                break
            proposal = ActionProposal(call.name, arguments, call.id)
            self._event(trace, "tool_proposed", tool=call.name, call_id=call.id)

            if call.name == "read":
                outcome, failure = self._read(arguments, trace)
                if failure:
                    last_failure = failure
                    break
                messages.extend(self._tool_messages(call, outcome))
                continue
            if call.name == "write":
                outcome, failure = self._write(proposal, trace)
                if failure:
                    last_failure = failure
                    break
                messages.extend(self._tool_messages(call, outcome))
                verification, failure = self._verify(trace)
                messages.append(Message(role="user", content=self._verification_evidence(verification)))
                if failure:
                    if repair_cycles >= self.execution_policy.max_repair_cycles:
                        last_failure = FailureClass.REPAIR_EXHAUSTED
                        break
                    repair_cycles += 1
                    self._event(trace, "repair_requested", cycle=repair_cycles, evidence=self._verification_evidence(verification))
                    last_failure = FailureClass.VERIFICATION_FAILED
                    continue
                verification_passed = True
                return self._finish(trace, attempts, repair_cycles, verification_passed, None, preflight)
            if call.name == "command":
                verification, failure = self._run_model_command(proposal, trace)
                messages.extend(self._tool_messages(call, verification))
                if failure:
                    last_failure = failure
                    break
                continue
            last_failure = FailureClass.TOOL_FAILED
            self._event(trace, "tool_result", tool=call.name, status="FAILED")
            break

        return self._finish(trace, attempts, repair_cycles, verification_passed, last_failure or FailureClass.MODEL_FAILED, preflight)

    def _read(self, arguments, trace):
        path = arguments.get("path")
        if not isinstance(path, str) or not self.execution_policy.allows_read(path):
            self._event(trace, "tool_result", tool="read", status="POLICY_DENIED")
            return None, FailureClass.EXECUTION_POLICY_DENIED
        try:
            content = self.workspace.read(path)
        except WorkspaceViolation:
            self._event(trace, "tool_result", tool="read", status="FAILED")
            return None, FailureClass.WORKSPACE_VIOLATION
        self._event(trace, "tool_result", tool="read", status="PASS", path=path)
        return {"path": path, "content": content}, None

    def _write(self, proposal: ActionProposal, trace):
        path = proposal.arguments.get("path")
        content = proposal.arguments.get("content")
        if not isinstance(path, str) or not self.execution_policy.allows_write(path):
            self._event(trace, "mutation_result", status="POLICY_DENIED")
            return None, FailureClass.EXECUTION_POLICY_DENIED
        self._event(trace, "mutation_proposed", path=path)
        if not self._approve(proposal, trace):
            self._event(trace, "mutation_result", status="DENIED", path=path)
            return None, FailureClass.APPROVAL_DENIED
        try:
            self.workspace.write(path, content)
        except WorkspaceViolation:
            self._event(trace, "mutation_result", status="FAILED", path=path)
            return None, FailureClass.WORKSPACE_VIOLATION
        self._event(trace, "mutation_result", status="PASS", path=path)
        return {"status": "written", "path": path}, None

    def _run_model_command(self, proposal: ActionProposal, trace):
        command_id = proposal.arguments.get("command")
        if not isinstance(command_id, str) or self.execution_policy.command(command_id) is None:
            self._event(trace, "command_result", status="POLICY_DENIED")
            return {"status": "policy_denied"}, FailureClass.EXECUTION_POLICY_DENIED
        if not self._approve(proposal, trace):
            self._event(trace, "command_result", status="DENIED")
            return {"status": "denied"}, FailureClass.APPROVAL_DENIED
        result = self.runner.run(command_id)
        return self._command_evidence(result, trace, event_name="command_result")

    def _verify(self, trace):
        proposal = ActionProposal(
            "command",
            {"command": self.task.verification_command_id, "purpose": "deterministic_verification"},
            "verify",
        )
        if self.execution_policy.command(self.task.verification_command_id) is None:
            self._event(trace, "verification", status="POLICY_DENIED", failure=FailureClass.EXECUTION_POLICY_DENIED.value)
            return {"status": "policy_denied"}, FailureClass.EXECUTION_POLICY_DENIED
        if not self._approve(proposal, trace):
            self._event(trace, "verification", status="DENIED", failure=FailureClass.APPROVAL_DENIED.value)
            return {"status": "not_run"}, FailureClass.APPROVAL_DENIED
        result = self.runner.run(self.task.verification_command_id)
        evidence, failure = self._command_evidence(result, trace, event_name="verification")
        if failure is None and result.exit_code != 0:
            return evidence, FailureClass.VERIFICATION_FAILED
        return evidence, failure

    def _command_evidence(self, result, trace, *, event_name):
        if result.timed_out:
            evidence = {"status": "TIMEOUT", "exit_code": result.exit_code}
            self._event(trace, event_name, **evidence, failure=FailureClass.COMMAND_TIMEOUT.value)
            return evidence, FailureClass.COMMAND_TIMEOUT
        evidence = {
            "status": "PASS" if result.exit_code == 0 else "FAIL",
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        self._event(trace, event_name, **evidence)
        return evidence, None if result.exit_code == 0 else FailureClass.VERIFICATION_FAILED

    def _approve(self, proposal: ActionProposal, trace):
        decision = self.approval_policy.decide(proposal)
        self._event(trace, "approval", tool=proposal.name, call_id=proposal.call_id, decision="ALLOW" if decision else "DENY")
        return decision

    @staticmethod
    def _verification_evidence(evidence: Mapping[str, Any]) -> str:
        return "Actual deterministic verification evidence:\n" + json.dumps(evidence, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _tool_messages(call, outcome):
        return [Message(role="tool", tool_call_id=call.id, content=json.dumps(outcome, ensure_ascii=False, sort_keys=True))]

    def _finish(self, trace, attempts, repair_cycles, verification_passed, failure, preflight):
        status = "PASS" if failure is None and verification_passed else "FAIL"
        self._event(trace, "final_result", status=status, failure_class=failure.value if failure else None)
        return HarnessResult(
            status=status,
            session_id=self.session_id,
            task_id=self.task.task_id,
            workspace_root=str(self.workspace.root),
            model_identity=self.model_identity,
            start_status=trace[0]["status"],
            final_status=status,
            failure_class=failure,
            verification_passed=verification_passed,
            repair_cycles=repair_cycles,
            model_attempts=attempts,
            available_tools=self.available_tools,
            governance_authority=False,
            identity_snapshot=preflight.identity_snapshot.as_dict(),
            preflight=preflight.as_dict(),
            trace=trace,
        )

    def _event(self, trace, event: str, **fields):
        record = {"event": event, "session_id": self.session_id, "task_id": self.task.task_id}
        record.update(fields)
        trace.append(record)
        return record
