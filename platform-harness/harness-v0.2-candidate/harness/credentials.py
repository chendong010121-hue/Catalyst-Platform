from __future__ import annotations

import getpass
import json
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping


class CredentialSourceType(str, Enum):
    PROCESS_ENVIRONMENT = "PROCESS_ENVIRONMENT"
    USER_LOCAL = "USER_LOCAL"


class CredentialUnavailable(RuntimeError):
    """A credential reference cannot be resolved by one source."""


@dataclass(frozen=True)
class CredentialResolution:
    credential_ref: str
    source_type: CredentialSourceType
    value: str

    def public_dict(self) -> dict[str, str]:
        return {
            "credential_ref": self.credential_ref,
            "credential_source_type": self.source_type.value,
            "credential_resolved": True,
        }


def _environment_name(credential_ref: str) -> str:
    if credential_ref == "deepseek.default":
        return "DEEPSEEK_API_KEY"
    raise CredentialUnavailable("unsupported credential reference")


class ProcessEnvironmentCredentialSource:
    source_type = CredentialSourceType.PROCESS_ENVIRONMENT

    def __init__(self, environment: Mapping[str, str] | None = None):
        self._environment = dict(environment if environment is not None else os.environ)

    def resolve(self, credential_ref: str) -> CredentialResolution:
        name = _environment_name(credential_ref)
        value = self._environment.get(name)
        if not value:
            raise CredentialUnavailable("process credential is unavailable")
        return CredentialResolution(credential_ref, self.source_type, value)


class UserLocalCredentialSource:
    source_type = CredentialSourceType.USER_LOCAL

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path is not None else default_user_local_path()

    def resolve(self, credential_ref: str) -> CredentialResolution:
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CredentialUnavailable("user-local credential store is unavailable") from exc
        if not isinstance(document, dict) or not isinstance(document.get(credential_ref), str):
            raise CredentialUnavailable("credential reference is absent from user-local store")
        value = document[credential_ref]
        if not value:
            raise CredentialUnavailable("user-local credential is empty")
        return CredentialResolution(credential_ref, self.source_type, value)


class CredentialResolver:
    """Resolve a reference through replaceable source implementations."""

    def __init__(self, sources=None):
        self._sources = tuple(
            sources
            if sources is not None
            else (
                ProcessEnvironmentCredentialSource(),
                UserLocalCredentialSource(),
            )
        )

    def resolve(self, credential_ref: str) -> CredentialResolution:
        for source in self._sources:
            try:
                return source.resolve(credential_ref)
            except CredentialUnavailable:
                continue
        raise CredentialUnavailable("credential reference is unavailable")


def default_user_local_path() -> Path:
    profile = os.environ.get("USERPROFILE") or os.environ.get("HOME") or str(Path.home())
    return Path(profile) / ".catalyst" / "credentials.json"


def setup_user_local_credential(
    credential_ref: str,
    *,
    path: str | Path | None = None,
    input_function: Callable[[str], str] | None = None,
) -> None:
    """Human-only hidden-input setup; never exposes the value to callers/output."""

    prompt = input_function or getpass.getpass
    value = prompt(f"Enter credential for {credential_ref}: ")
    if not value:
        raise ValueError("credential cannot be empty")
    target = Path(path) if path is not None else default_user_local_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, str] = {}
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                document = {str(key): str(item) for key, item in existing.items()}
        except (OSError, UnicodeError, json.JSONDecodeError):
            document = {}
    document[credential_ref] = value
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    print(f"Configured {credential_ref} from {CredentialSourceType.USER_LOCAL.value}.")
