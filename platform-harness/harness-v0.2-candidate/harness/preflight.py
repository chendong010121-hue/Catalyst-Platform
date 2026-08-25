from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .credentials import CredentialResolution, CredentialResolver, CredentialUnavailable
from .policy import ExecutionPolicy


@dataclass(frozen=True)
class ProviderBinding:
    provider_id: str
    model_id: str
    credential_ref: str


@dataclass(frozen=True)
class EnvironmentIdentitySnapshot:
    harness_implementation_version: str
    harness_source_revision: str
    python_version: str
    os_name: str
    os_release_or_platform_family: str
    architecture: str
    workspace_root: str
    provider_id: str
    model_id: str
    credential_source_type: str
    execution_policy_identity: str
    preflight_status: str

    def as_dict(self) -> dict[str, str]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PreflightResult:
    status: str
    reasons: tuple[str, ...]
    identity_snapshot: EnvironmentIdentitySnapshot
    credential_resolution: CredentialResolution | None = field(default=None, repr=False, compare=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "identity_snapshot": self.identity_snapshot.as_dict(),
            "credential": self.credential_resolution.public_dict() if self.credential_resolution else None,
        }


class ExecutionEnvironmentPreflight:
    def __init__(self, *, workspace_root, policy: ExecutionPolicy, provider_binding: ProviderBinding, credential_resolver: CredentialResolver):
        self.workspace_root = Path(workspace_root)
        self.policy = policy
        self.provider_binding = provider_binding
        self.credential_resolver = credential_resolver

    def check(self) -> PreflightResult:
        reasons: list[str] = []
        workspace_valid = self.workspace_root.is_dir()
        if not workspace_valid:
            reasons.append("WORKSPACE_INVALID")
        reasons.extend(self.policy.validate(self.workspace_root))
        if not self.provider_binding.provider_id or not self.provider_binding.model_id or not self.provider_binding.credential_ref:
            reasons.append("PROVIDER_BINDING_INVALID")

        resolution = None
        try:
            resolution = self.credential_resolver.resolve(self.provider_binding.credential_ref)
        except CredentialUnavailable:
            reasons.append("CREDENTIAL_UNAVAILABLE")

        for argv in self.policy.commands.values():
            executable = argv[0] if argv else ""
            if not self._executable_available(executable):
                reasons.append("EXECUTABLE_UNAVAILABLE")

        reasons = list(dict.fromkeys(reasons))
        status = "READY" if not reasons else "BLOCKED"
        identity = EnvironmentIdentitySnapshot(
            harness_implementation_version="0.2-candidate",
            harness_source_revision="UNKNOWN",
            python_version=platform.python_version(),
            os_name=os.name,
            os_release_or_platform_family=platform.system() + " " + platform.release(),
            architecture=platform.machine(),
            workspace_root=str(self.workspace_root.resolve()) if workspace_valid else str(self.workspace_root),
            provider_id=self.provider_binding.provider_id,
            model_id=self.provider_binding.model_id,
            credential_source_type=resolution.source_type.value if resolution else "UNAVAILABLE",
            execution_policy_identity=self.policy.identity,
            preflight_status=status,
        )
        return PreflightResult(status, tuple(reasons), identity, resolution)

    @staticmethod
    def _executable_available(executable: str) -> bool:
        if not executable:
            return False
        path = Path(executable)
        return path.is_file() if path.is_absolute() else shutil.which(executable) is not None
