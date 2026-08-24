from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from agent_runtime.contracts import Message, ModelRequest, ModelToolDefinition

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


@dataclass(frozen=True)
class HarnessTask:
    task_id: str
    instruction: str
    verification_command: tuple[str, ...]
    allowed_read_paths: tuple[str, ...] = ("TASK.md", "guard.py", "test_guard.py")
    allowed_write_paths: tuple[str, ...] = ("guard.py",)
    max_repair_cycles: int = 1

    def __post_init__(self) -> None:
        if not self.task_id or not isinstance(self.task_id, str):
            raise ValueError("task_id must be a non-empty string")
        if not self.instruction or not isinstance(self.instruction, str):
            raise ValueError("instruction must be a non-empty string")
        if not self.verification_command or not all(
            isinstance(part, str) and part for part in self.verification_command
        ):
            raise ValueError("verification_command must be a non-empty argv")
        if self.max_repair_cycles != 1:
            raise ValueError("V0.1 permits exactly one repair cycle")


@dataclass(frozen=True)
class ToolProposal:
    name: str
    arguments: Mapping[str, Any]
    call_id: str


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
    responsibility_classification: dict[str, str]
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
            "responsibility_classification": self.responsibility_classification,
            "trace": self.trace,
        }


H00_CLASSIFICATION = {
    "ModelProvider": "REUSED EXISTING NEUTRAL CONTRACT",
    "HarnessSession": "HARNESS RESPONSIBILITY",
    "DeepSeekModelProvider": "MODEL-SPECIFIC ADAPTER",
    "WorkspaceBoundary": "PRIVATE IMPLEMENTATION HOW",
    "read/write/command": "TOOL-SPECIFIC IMPLEMENTATION",
}

_TOOLS = (
    ModelToolDefinition(
        name="read",
        description="Read one authorized UTF-8 text file in the Workspace.",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    ),
    ModelToolDefinition(
        name="write",
        description="Propose replacement text for one authorized file; external approval is required.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    ),
    ModelToolDefinition(
        name="command",
        description="Run only the already-authorized deterministic verification command; external approval is required.",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string", "enum": ["verify"]}},
            "required": ["command"],
            "additionalProperties": False,
        },
    ),
)


class HarnessSession:
    """One bounded development task; deliberately distinct from Runtime Session."""

    def __init__(
        self,
        *,
        task: HarnessTask,
        workspace: WorkspaceBoundary,
        model,
        approval: Callable[[ToolProposal], bool],
        max_model_attempts: int = 6,
    ) -> None:
        if not callable(getattr(model, "request", None)):
            raise TypeError("model must satisfy the existing ModelProvider contract")
        if not callable(approval):
            raise TypeError("approval must be callable")
        if max_model_attempts < 1 or max_model_attempts > 6:
            raise ValueError("V0.1 model attempts must be between 1 and 6")
        self.task = task
        self.workspace = workspace
        self.model = model
        self.approval = approval
        self.max_model_attempts = max_model_attempts
        self.session_id = uuid.uuid4().hex
        self.model_identity = str(
            getattr(model, "identity", type(model).__name__)
        )

    @property
    def available_tools(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in _TOOLS)

    def run(self) -> HarnessResult:
        trace: list[dict[str, Any]] = []
        attempts = 0
        repair_cycles = 0
        verification_passed = False
        last_failure: FailureClass | None = None
        messages = [
            Message(
                role="system",
                content=(
                    "You are a bounded development model. Use only the supplied tools. "
                    "Never claim completion without a successful verification result."
                ),
            ),
            Message(
                role="user",
                content=(
                    f"Authorized task {self.task.task_id}: {self.task.instruction}\n"
                    "Read the relevant file, propose the smallest approved change, and "
                    "use the supplied verification evidence to repair at most once."
                ),
            ),
        ]
        self._event(trace, "task_start", status="RUNNING")

        while attempts < self.max_model_attempts:
            attempts += 1
            try:
                response = self.model.request(
                    ModelRequest(messages=tuple(messages), tools=_TOOLS, tool_choice="auto")
                )
            except Exception:
                last_failure = FailureClass.MODEL_FAILED
                self._event(trace, "model_turn", attempt=attempts, status="FAILED")
                break

            self._event(
                trace,
                "model_turn",
                attempt=attempts,
                status="RECEIVED",
                tool_calls=len(response.tool_calls),
            )
            if len(response.tool_calls) != 1:
                if repair_cycles:
                    last_failure = FailureClass.REPAIR_EXHAUSTED
                else:
                    last_failure = FailureClass.MODEL_FAILED
                break

            call = response.tool_calls[0]
            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=tuple(response.tool_calls),
                )
            )
            try:
                arguments = json.loads(call.arguments)
            except (TypeError, json.JSONDecodeError):
                last_failure = FailureClass.MODEL_FAILED
                break
            if not isinstance(arguments, dict):
                last_failure = FailureClass.MODEL_FAILED
                break

            proposal = ToolProposal(call.name, arguments, call.id)
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
                messages.append(
                    Message(
                        role="user",
                        content=self._verification_evidence(verification),
                    )
                )
                if failure:
                    if repair_cycles >= self.task.max_repair_cycles:
                        last_failure = FailureClass.REPAIR_EXHAUSTED
                        break
                    repair_cycles += 1
                    self._event(
                        trace,
                        "repair_requested",
                        cycle=repair_cycles,
                        evidence=self._verification_evidence(verification),
                    )
                    last_failure = FailureClass.VERIFICATION_FAILED
                    continue
                verification_passed = True
                return self._finish(
                    trace,
                    attempts,
                    repair_cycles,
                    verification_passed,
                    None,
                )

            if call.name == "command":
                verification, failure = self._verify(trace, proposal=proposal)
                messages.extend(self._tool_messages(call, verification))
                if failure:
                    last_failure = failure
                continue

            last_failure = FailureClass.TOOL_FAILED
            self._event(trace, "tool_result", tool=call.name, status="FAILED")
            break

        if last_failure is None:
            last_failure = FailureClass.MODEL_FAILED
        return self._finish(
            trace,
            attempts,
            repair_cycles,
            verification_passed,
            last_failure,
        )

    def _read(self, arguments, trace):
        path = arguments.get("path")
        if path not in self.task.allowed_read_paths:
            self._event(trace, "tool_result", tool="read", status="FAILED")
            return None, FailureClass.WORKSPACE_VIOLATION
        try:
            content = self.workspace.read(path)
        except WorkspaceViolation:
            self._event(trace, "tool_result", tool="read", status="FAILED")
            return None, FailureClass.WORKSPACE_VIOLATION
        self._event(trace, "tool_result", tool="read", status="PASS", path=path)
        return {"path": path, "content": content}, None

    def _write(self, proposal: ToolProposal, trace):
        path = proposal.arguments.get("path")
        content = proposal.arguments.get("content")
        if path not in self.task.allowed_write_paths:
            self._event(trace, "mutation_result", status="FAILED")
            return None, FailureClass.WORKSPACE_VIOLATION
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

    def _verify(self, trace, proposal: ToolProposal | None = None):
        proposal = proposal or ToolProposal(
            "command", {"command": "verify", "purpose": "harness_verification"}, "verify"
        )
        if proposal.arguments.get("command") != "verify":
            self._event(trace, "verification", status="FAILED", failure=FailureClass.TOOL_FAILED.value)
            return {"status": "not_run"}, FailureClass.TOOL_FAILED
        if not self._approve(proposal, trace):
            self._event(trace, "verification", status="DENIED", failure=FailureClass.APPROVAL_DENIED.value)
            return {"status": "not_run"}, FailureClass.APPROVAL_DENIED
        try:
            completed = subprocess.run(
                self.task.verification_command,
                cwd=self.workspace.root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            self._event(trace, "verification", status="TIMEOUT", failure=FailureClass.COMMAND_TIMEOUT.value)
            return {"status": "timeout"}, FailureClass.COMMAND_TIMEOUT
        evidence = {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
        self._event(trace, "verification", **evidence)
        if completed.returncode != 0:
            return evidence, FailureClass.VERIFICATION_FAILED
        return evidence, None

    @staticmethod
    def _verification_evidence(evidence: Mapping[str, Any]) -> str:
        return "Actual deterministic verification evidence:\n" + json.dumps(
            evidence, ensure_ascii=False, sort_keys=True
        )

    @staticmethod
    def _tool_messages(call, outcome):
        return [
            Message(
                role="tool",
                tool_call_id=call.id,
                content=json.dumps(outcome, ensure_ascii=False, sort_keys=True),
            )
        ]

    def _approve(self, proposal: ToolProposal, trace: list[dict[str, Any]]) -> bool:
        try:
            decision = bool(self.approval(proposal))
        except Exception:
            decision = False
        self._event(
            trace,
            "approval",
            tool=proposal.name,
            call_id=proposal.call_id,
            decision="ALLOW" if decision else "DENY",
        )
        return decision

    def _finish(self, trace, attempts, repair_cycles, verification_passed, failure):
        status = "PASS" if failure is None and verification_passed else "FAIL"
        final = self._event(
            trace,
            "final_result",
            status=status,
            failure_class=failure.value if failure else None,
        )
        if not final or trace[0]["event"] != "task_start":
            failure = FailureClass.TRACE_INCOMPLETE
            status = "FAIL"
        return HarnessResult(
            status=status,
            session_id=self.session_id,
            task_id=self.task.task_id,
            workspace_root=str(self.workspace.root),
            model_identity=self.model_identity,
            start_status="RUNNING",
            final_status=status,
            failure_class=failure,
            verification_passed=verification_passed,
            repair_cycles=repair_cycles,
            model_attempts=attempts,
            available_tools=self.available_tools,
            governance_authority=False,
            responsibility_classification=dict(H00_CLASSIFICATION),
            trace=trace,
        )

    def _event(self, trace, event: str, **fields):
        record = {
            "event": event,
            "session_id": self.session_id,
            "task_id": self.task.task_id,
        }
        record.update(fields)
        trace.append(record)
        return record
