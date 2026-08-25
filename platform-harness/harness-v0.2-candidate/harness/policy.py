from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping


class PolicyInvalid(ValueError):
    """ExecutionPolicy is not a safe Stage-local policy."""


@dataclass(frozen=True)
class ActionProposal:
    name: str
    arguments: Mapping[str, Any]
    call_id: str


@dataclass(frozen=True)
class ExecutionPolicy:
    allowed_read_paths: tuple[str, ...]
    allowed_write_paths: tuple[str, ...]
    commands: Mapping[str, tuple[str, ...]]
    command_timeout: float
    max_model_attempts: int
    max_repair_cycles: int
    task_environment: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_read_paths", tuple(self.allowed_read_paths))
        object.__setattr__(self, "allowed_write_paths", tuple(self.allowed_write_paths))
        object.__setattr__(self, "commands", {str(key): tuple(value) for key, value in self.commands.items()})
        object.__setattr__(self, "task_environment", dict(self.task_environment))

    def validate(self, workspace_root: str | Path) -> tuple[str, ...]:
        reasons: list[str] = []
        root = Path(workspace_root)
        for path in (*self.allowed_read_paths, *self.allowed_write_paths):
            candidate = Path(path)
            if candidate.is_absolute() or ".." in candidate.parts:
                reasons.append("POLICY_INVALID")
        if self.command_timeout <= 0 or self.max_model_attempts < 1 or self.max_model_attempts > 6:
            reasons.append("POLICY_INVALID")
        if self.max_repair_cycles != 1:
            reasons.append("POLICY_INVALID")
        if not root.exists() and not root.parent.exists():
            reasons.append("WORKSPACE_INVALID")
        for name, argv in self.commands.items():
            if not name or not argv or not all(isinstance(part, str) and part for part in argv):
                reasons.append("POLICY_INVALID")
        for name, value in self.task_environment.items():
            if not isinstance(name, str) or not isinstance(value, str):
                reasons.append("POLICY_INVALID")
            if any(marker in name.upper() for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
                reasons.append("POLICY_INVALID")
        return tuple(dict.fromkeys(reasons))

    @property
    def identity(self) -> str:
        payload = {
            "reads": self.allowed_read_paths,
            "writes": self.allowed_write_paths,
            "commands": self.commands,
            "timeout": self.command_timeout,
            "model_attempts": self.max_model_attempts,
            "repair_cycles": self.max_repair_cycles,
            "task_environment": self.task_environment,
        }
        return "execution-policy:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=list).encode("utf-8")
        ).hexdigest()[:16]

    def allows_read(self, path: str) -> bool:
        return path in self.allowed_read_paths

    def allows_write(self, path: str) -> bool:
        return path in self.allowed_write_paths

    def command(self, command_id: str) -> tuple[str, ...] | None:
        return self.commands.get(command_id)


@dataclass(frozen=True)
class ApprovalPolicy:
    decide_function: Callable[[ActionProposal], bool]

    def decide(self, proposal: ActionProposal) -> bool:
        try:
            return bool(self.decide_function(proposal))
        except Exception:
            return False
