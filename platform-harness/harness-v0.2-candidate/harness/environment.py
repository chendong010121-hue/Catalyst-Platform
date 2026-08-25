from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Mapping

from .policy import ExecutionPolicy
from .workspace import WorkspaceBoundary


_SAFE_PARENT_ENVIRONMENT = (
    "PATH",
    "PATHEXT",
    "SystemRoot",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "HOME",
    "USERPROFILE",
    "LANG",
    "LC_ALL",
    "PYTHONIOENCODING",
)


class SanitizedToolEnvironment:
    def __init__(self, parent_environment: Mapping[str, str] | None = None):
        self._parent_environment = dict(parent_environment if parent_environment is not None else os.environ)

    def build(self, task_environment: Mapping[str, str]) -> dict[str, str]:
        environment = {
            name: self._parent_environment[name]
            for name in _SAFE_PARENT_ENVIRONMENT
            if name in self._parent_environment
        }
        environment.update(task_environment)
        return environment


@dataclass(frozen=True)
class CommandResult:
    command_id: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class SanitizedCommandRunner:
    def __init__(
        self,
        *,
        workspace: WorkspaceBoundary,
        policy: ExecutionPolicy,
        parent_environment: Mapping[str, str] | None = None,
    ):
        self.workspace = workspace
        self.policy = policy
        self.tool_environment = SanitizedToolEnvironment(parent_environment)

    def run(self, command_id: str) -> CommandResult:
        argv = self.policy.command(command_id)
        if argv is None:
            raise PermissionError("command is not declared by ExecutionPolicy")
        try:
            completed = subprocess.run(
                argv,
                cwd=self.workspace.root,
                env=self.tool_environment.build(self.policy.task_environment),
                capture_output=True,
                text=True,
                timeout=self.policy.command_timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(command_id, -1, str(exc.stdout or ""), str(exc.stderr or ""), True)
        return CommandResult(command_id, completed.returncode, completed.stdout[-4000:], completed.stderr[-4000:])
