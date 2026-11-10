"""Explicit, hash-pinned local Tool components over the existing CapabilityCatalog."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from jsonschema.validators import validator_for

from agent_runtime.capability_executor import _SchemaError as NativeInputSchemaError
from agent_runtime.capability_executor import _validate_schema_supported as validate_native_input_schema
from agent_runtime.contracts import CapabilityDescriptor as RuntimeCapabilityDescriptor
from platform_standard.models import CapabilityDescriptor
from platform_standard.validation import PlatformValidator


class ComponentError(RuntimeError):
    """A local component package failed validation, admission, or lifecycle checks."""


_COMPONENT_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
_ENTRYPOINT = re.compile(r"^([A-Za-z0-9_-]+\.py):([A-Za-z_][A-Za-z0-9_]*)$")
_MANIFEST_FIELDS = {
    "manifest_version",
    "component_id",
    "resource_type",
    "version",
    "source",
    "binding",
    "model_policy",
    "llm_visibility",
}
_BINDING_FIELDS = {
    "capability_id",
    "capability_version",
    "name",
    "description",
    "input_schema",
    "output_schema",
    "execution",
}
_SCHEMA_KEYS = {"type", "properties", "required", "additionalProperties", "items", "enum"}
_SOURCE_KEYS = {"kind", "entrypoint", "sha256"}
_POLICY_KEYS = {"mode", "path_parameter", "max_calls"}


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ComponentError("component manifest contains a duplicate JSON key")
        result[key] = value
    return result


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ComponentError("component manifest is not canonical JSON data") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class ComponentCandidate:
    package_dir: Path
    manifest: dict[str, Any]
    manifest_bytes: bytes
    source_path: Path
    source_bytes: bytes
    package_sha256: str
    manifest_sha256: str
    source_sha256: str

    @property
    def component_id(self) -> str:
        return self.manifest["component_id"]

    @property
    def version(self) -> str:
        return self.manifest["version"]

    @property
    def binding(self) -> dict[str, Any]:
        return self.manifest["binding"]

    @property
    def model_policy(self) -> dict[str, Any]:
        return self.manifest["model_policy"]

    def public_record(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "resource_type": self.manifest["resource_type"],
            "version": self.version,
            "capability_id": self.binding["capability_id"],
            "capability_version": self.binding["capability_version"],
            "source_kind": self.manifest["source"]["kind"],
            "llm_visibility": self.manifest["llm_visibility"],
            "side_effect": self.binding["execution"]["side_effect"],
        }


class _LoadedLocalTool:
    """Own one imported component module for exactly one active registration."""

    def __init__(self, implementation: Any, module_name: str, module: Any) -> None:
        self._implementation = implementation
        self._module_name = module_name
        self._module = module
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def __getattr__(self, name: str) -> Any:
        implementation = self._implementation
        if implementation is None:
            raise AttributeError(name)
        return getattr(implementation, name)

    def invoke(self, parameters: Mapping[str, Any], context: Any) -> Any:
        implementation = self._implementation
        if implementation is None:
            raise ComponentError("the local Tool component has been cleaned up")
        return implementation.invoke(parameters, context)

    def close(self) -> None:
        implementation = self._implementation
        if implementation is None:
            return
        try:
            closer = getattr(implementation, "close", None)
            if callable(closer):
                closer()
        finally:
            if sys.modules.get(self._module_name) is self._module:
                sys.modules.pop(self._module_name, None)
            self._implementation = None
            self._module = None
            self._closed = True


def discover_local_component(source_dir: Path | str) -> ComponentCandidate:
    """Validate only the manifest and bytes. This never imports component code."""
    package_dir = Path(source_dir).expanduser().resolve(strict=True)
    if not package_dir.is_dir() or Path(source_dir).is_symlink():
        raise ComponentError("component source must be a real local directory")
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ComponentError("component source must contain a regular manifest.json")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_no_duplicate_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ComponentError("component manifest contains a non-finite number")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ComponentError("component manifest is unreadable JSON") from exc
    if isinstance(manifest, dict) and manifest.get("resource_type") == "method_data":
        from .method_bundle import validate_method_bundle
        return validate_method_bundle(Path(source_dir).expanduser().absolute(), manifest, manifest_bytes)
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_FIELDS:
        raise ComponentError("component manifest has missing or unsupported fields")
    if type(manifest["manifest_version"]) is not int or manifest["manifest_version"] != 1:
        raise ComponentError("component manifest version is unsupported")
    component_id = manifest["component_id"]
    version = manifest["version"]
    if not isinstance(component_id, str) or not _COMPONENT_ID.fullmatch(component_id):
        raise ComponentError("component_id must be a portable lower-case identifier")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ComponentError("component version must be an exact semantic version")
    if manifest["resource_type"] != "tool":
        raise ComponentError("this admission path supports executable Tool resources only")
    source_info = manifest["source"]
    if not isinstance(source_info, dict) or set(source_info) != _SOURCE_KEYS:
        raise ComponentError("component source declaration has missing or unsupported fields")
    if source_info["kind"] != "local_python":
        raise ComponentError("component source kind must be local_python")
    entrypoint = source_info["entrypoint"]
    match = _ENTRYPOINT.fullmatch(entrypoint) if isinstance(entrypoint, str) else None
    if match is None:
        raise ComponentError("component entrypoint must be one package-local Python file and class")
    filename, class_name = match.groups()
    if filename == "manifest.py":
        raise ComponentError("manifest.py cannot be used as a component entrypoint")
    source_path = package_dir / filename
    if not source_path.is_file() or source_path.is_symlink() or source_path.resolve().parent != package_dir:
        raise ComponentError("component entrypoint must be a regular file inside its package")
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        raise ComponentError("component source file is unreadable") from exc
    source_sha256 = _sha256(source_bytes)
    if not isinstance(source_info["sha256"], str) or source_info["sha256"] != source_sha256:
        raise ComponentError("component source SHA-256 does not match its manifest")

    binding = manifest["binding"]
    if not isinstance(binding, dict) or set(binding) != _BINDING_FIELDS:
        raise ComponentError("component binding has missing or unsupported fields")
    if binding["capability_version"] != version:
        raise ComponentError("component and exact Capability binding versions must match")
    if not isinstance(binding["execution"], dict) or binding["execution"] != {"side_effect": "none"}:
        raise ComponentError("R5 local Tool admission permits only declared read-only bindings")
    if not isinstance(binding["input_schema"], dict) or not isinstance(binding["output_schema"], dict):
        raise ComponentError("component input and output schemas must be objects")
    model_policy = manifest["model_policy"]
    if not isinstance(model_policy, dict) or set(model_policy) != _POLICY_KEYS:
        raise ComponentError("component model policy has missing or unsupported fields")
    path_parameter = model_policy["path_parameter"]
    if (
        model_policy["mode"] != "selected_file_path"
        or model_policy["max_calls"] != 1
        or type(model_policy["max_calls"]) is not int
        or not isinstance(path_parameter, str)
    ):
        raise ComponentError("R5 external Tool policy must bind one user-selected local file")
    properties = binding["input_schema"].get("properties")
    if not isinstance(properties, dict) or not isinstance(properties.get(path_parameter), dict):
        raise ComponentError("model policy path parameter must exist in the binding input schema")
    if properties[path_parameter].get("type") != "string":
        raise ComponentError("model policy path parameter must have a string input schema")
    if manifest["llm_visibility"] != "explicit":
        raise ComponentError("external Tool visibility must require an explicit request allowlist")

    descriptor = CapabilityDescriptor(
        id=binding["capability_id"],
        name=binding["name"],
        description=binding["description"],
        capability_version=binding["capability_version"],
        input_schema=binding["input_schema"],
        output_schema=binding["output_schema"],
        execution=binding["execution"],
    )
    validator = PlatformValidator()
    try:
        validator.validate_capability(descriptor)
        validator_for(descriptor.input_schema).check_schema(descriptor.input_schema)
        validator_for(descriptor.output_schema).check_schema(descriptor.output_schema)
        validate_native_input_schema(descriptor.input_schema)
    except (ValueError, TypeError, NativeInputSchemaError) as exc:
        raise ComponentError("component binding contract failed Platform/Runtime validation") from exc
    manifest_sha256 = _sha256(_canonical_json(manifest))
    package_sha256 = _sha256(
        b"catalyst-local-tool-v1\0"
        + _canonical_json(manifest)
        + b"\0"
        + source_bytes
    )
    return ComponentCandidate(
        package_dir,
        manifest,
        manifest_bytes,
        source_path,
        source_bytes,
        package_sha256,
        manifest_sha256,
        source_sha256,
    )


class LocalComponentLifecycle:
    """Validate and admit local component packages, then manage their exact Catalog bindings."""

    def __init__(
        self,
        workspace: Path,
        state_path: Path,
        catalog: Any,
        read_state: Callable[[], dict[str, Any]],
        write_state: Callable[[Path, dict[str, Any]], None],
    ) -> None:
        self.workspace = workspace.resolve()
        self.state_path = state_path
        self.catalog = catalog
        self._read_state = read_state
        self._write_state = write_state
        self._load_failures: dict[tuple[str, str], str] = {}
        self._load_lock = __import__("threading").RLock()
        self._method_leases: dict[str, int] = {}
        from .asset_records import AssetRecords
        self.assets = AssetRecords(self.workspace, catalog, write_state)

    @property
    def installed_root(self) -> Path:
        return self.workspace / ".catalyst" / "components"

    def discover(self, source_dir: Path | str) -> dict[str, Any]:
        candidate = discover_local_component(source_dir)
        return {
            "phase": "validated",
            "component": candidate.public_record(),
            "manifest_sha256": candidate.manifest_sha256,
            "source_sha256": candidate.source_sha256,
            "package_sha256": candidate.package_sha256,
        }

    def admit(self, source_dir: Path | str, expected_sha256: str) -> dict[str, Any]:
        with self._load_lock:
            return self._admit(source_dir, expected_sha256)

    def _admit(self, source_dir: Path | str, expected_sha256: str) -> dict[str, Any]:
        candidate = discover_local_component(source_dir)
        if not isinstance(expected_sha256, str) or expected_sha256 != candidate.package_sha256:
            raise ComponentError("component package SHA-256 did not match the explicit admission value")
        state = self._read_state()
        components = state.setdefault("components", {})
        component = components.setdefault(
            candidate.component_id,
            {"active_version": None, "versions": {}},
        )
        if not isinstance(component, dict) or not isinstance(component.get("versions"), dict):
            raise ComponentError("component lifecycle state is malformed; it was not changed")
        versions = component["versions"]
        existing = versions.get(candidate.version)
        if existing is not None:
            if existing.get("package_sha256") != candidate.package_sha256:
                raise ComponentError("this component version is already admitted with a different source identity")
            return self._public_state(candidate.component_id, component, candidate.version, transition="no-op")
        if any(record.get("resource_type", "tool") != candidate.manifest["resource_type"]
               for record in versions.values()):
            raise ComponentError("component resource type cannot change between versions")

        target = self.installed_root / candidate.component_id / candidate.version
        if not target.resolve().is_relative_to(self.workspace):
            raise ComponentError("component installation path escapes the configured workspace")
        if target.exists():
            installed = discover_local_component(target)
            if installed.package_sha256 != candidate.package_sha256:
                raise ComponentError("component installation directory already contains different source bytes")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = target.parent / f".{candidate.version}.{uuid.uuid4().hex}.tmp"
            try:
                stage.mkdir()
                (stage / "manifest.json").write_bytes(candidate.manifest_bytes)
                if candidate.manifest["resource_type"] == "method_data":
                    for name, data in candidate.files.items():
                        destination = stage / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(data)
                else:
                    (stage / candidate.source_path.name).write_bytes(candidate.source_bytes)
                os.replace(stage, target)
            finally:
                if stage.exists():
                    shutil.rmtree(stage)

        previous_active = component.get("active_version")
        identity = ({"resource_type": "method_data", "skill_name": candidate.manifest["skill_name"],
                     "required_product_interface": candidate.manifest["required_product_interface"],
                     "provides": candidate.manifest["provides"], "requires": candidate.manifest["requires"]}
                    if candidate.manifest["resource_type"] == "method_data" else
                    {"capability_id": candidate.binding["capability_id"],
                     "capability_version": candidate.binding["capability_version"]})
        versions[candidate.version] = {
            "package_sha256": candidate.package_sha256,
            "manifest_sha256": candidate.manifest_sha256,
            "source_sha256": candidate.source_sha256,
            "package_path": str(target.relative_to(self.workspace)),
            **identity,
            "admitted_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        self._write_state(self.state_path, state)
        return {
            **self._public_state(candidate.component_id, component, candidate.version, transition="admitted"),
            "source_sha256": candidate.source_sha256,
            "package_sha256": candidate.package_sha256,
            "previous_version": previous_active,
        }

    def load_active(self) -> None:
        """Load only active, admitted versions. Discovery/admission never imports code."""
        with self._load_lock:
            state = self._read_state()
            for component_id, component in state.get("components", {}).items():
                if not isinstance(component, dict):
                    continue
                version = component.get("active_version")
                if not isinstance(version, str):
                    continue
                key = (component_id, version)
                try:
                    record = component.get("versions", {}).get(version, {})
                    if record.get("resource_type") == "method_data":
                        self._validate_admitted_method(component_id, version, component)
                        self._load_failures.pop(key, None)
                        continue
                    candidate, record, implementation = self._load_admitted(component_id, version, component)
                    self._register(candidate, record, implementation, activate=True)
                except Exception as exc:
                    self._load_failures[key] = type(exc).__name__

    def close_loaded(self, recorder: Any | None = None) -> None:
        """Release this Workbench's imported modules without changing persisted activation."""
        for descriptor in self.catalog.list():
            registration = self.catalog.get(
                descriptor.id, descriptor.capability_version
            )
            if registration is None or not isinstance(
                registration.metadata.get("component_id"), str
            ):
                continue
            retired = self.catalog.deactivate(
                descriptor.id, descriptor.capability_version
            )
            if (
                recorder is not None
                and not recorder.is_finished
                and retired is not None
                and retired.cleanup_error_type
            ):
                recorder.event(
                    "component.cleanup.failed",
                    component_id=retired.metadata.get("component_id"),
                    component_version=retired.metadata.get("component_version"),
                    capability_id=retired.descriptor.id,
                    capability_version=retired.descriptor.capability_version,
                    error_type=retired.cleanup_error_type,
                )

    def activate(self, component_id: str, version: str) -> dict[str, Any]:
        with self._load_lock:
            return self._activate(component_id, version)

    def _activate(self, component_id: str, version: str) -> dict[str, Any]:
        state = self._read_state()
        component = self._component_state(state, component_id)
        previous = component.get("active_version")
        if component["versions"].get(version, {}).get("resource_type") == "method_data":
            if previous == version:
                return self._public_state(component_id, component, version, transition="no-op")
            if self._method_leases.get(component_id, 0):
                raise ComponentError("method_update_busy")
            candidate = self._validate_admitted_method(component_id, version, component)
            record = component["versions"][version]
            restored = bool(record.get("activation_count", 0))
            component["active_version"] = version
            record["activation_count"] = int(record.get("activation_count", 0)) + 1
            record["last_activated_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            self._write_state(self.state_path, state)
            self._load_failures.pop((component_id, version), None)
            return {**self._public_state(component_id, component, version,
                        transition="restored" if restored else "activated" if previous is None else "replaced"),
                    "previous_version": previous, "manifest_sha256": candidate.manifest_sha256,
                    "source_sha256": candidate.source_sha256, "package_sha256": candidate.package_sha256}
        if previous == version and self.catalog.is_active(
            component["versions"].get(version, {}).get("capability_id"), version
        ):
            return self._public_state(component_id, component, version, transition="no-op")
        candidate, record, implementation = self._load_admitted(component_id, version, component)
        target_record = component["versions"].get(version)
        previously_activated = bool(target_record.get("activation_count", 0))
        self._register(candidate, record, implementation, activate=False)
        component["active_version"] = version
        target_record["activation_count"] = int(target_record.get("activation_count", 0)) + 1
        target_record["last_activated_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        self._write_state(self.state_path, state)
        if isinstance(previous, str):
            previous_record = component["versions"].get(previous, {})
            previous_capability_id = previous_record.get("capability_id")
            if isinstance(previous_capability_id, str):
                self.catalog.deactivate(previous_capability_id, previous)
        self.catalog.activate(candidate.binding["capability_id"], version)
        self._load_failures.pop((component_id, version), None)
        transition = (
            "activated"
            if previous is None and not previously_activated
            else "restored"
            if previously_activated
            else "replaced"
        )
        return {
            **self._public_state(component_id, component, version, transition=transition),
            "previous_version": previous,
            "manifest_sha256": candidate.manifest_sha256,
            "source_sha256": candidate.source_sha256,
            "package_sha256": candidate.package_sha256,
        }

    def deactivate(self, component_id: str) -> dict[str, Any]:
        with self._load_lock:
            if self._method_leases.get(component_id, 0):
                raise ComponentError("method_update_busy")
            return self._deactivate(component_id)

    def _deactivate(self, component_id: str) -> dict[str, Any]:
        state = self._read_state()
        component = self._component_state(state, component_id)
        previous = component.get("active_version")
        if not isinstance(previous, str):
            return self._public_state(component_id, component, None, transition="no-op")
        record = component["versions"].get(previous, {})
        capability_id = record.get("capability_id")
        component["active_version"] = None
        self._write_state(self.state_path, state)
        cleanup_status = "not_required"
        if isinstance(capability_id, str):
            registration = self.catalog.deactivate(capability_id, previous)
            if registration is not None:
                cleanup_status = (
                    "deferred"
                    if registration._run_leases
                    else "failed"
                    if registration.cleanup_error_type
                    else "completed"
                )
        return {
            **self._public_state(component_id, component, None, transition="deactivated"),
            "previous_version": previous,
            "manifest_sha256": record.get("manifest_sha256"),
            "source_sha256": record.get("source_sha256"),
            "package_sha256": record.get("package_sha256"),
            "cleanup_status": cleanup_status,
        }

    def list_components(self) -> list[dict[str, Any]]:
        state = self._read_state()
        values = []
        for component_id, component in sorted(state.get("components", {}).items()):
            if not isinstance(component, dict) or not isinstance(component.get("versions"), dict):
                continue
            versions = []
            for version, record in sorted(component["versions"].items()):
                if not isinstance(record, dict):
                    continue
                versions.append(
                    {
                        "version": version,
                        "resource_type": record.get("resource_type", "tool"),
                        **({key: record.get(key) for key in ("skill_name", "required_product_interface", "provides", "requires")}
                           if record.get("resource_type") == "method_data" else {}),
                        "capability_id": record.get("capability_id"),
                        "capability_version": record.get("capability_version"),
                        "source_sha256": record.get("source_sha256"),
                        "package_sha256": record.get("package_sha256"),
                        "admitted": True,
                        "active": component.get("active_version") == version,
                        "load_error_type": self._load_failures.get((component_id, version)),
                    }
                )
            values.append(
                {
                    "component_id": component_id,
                    "resource_type": next((r.get("resource_type", "tool") for r in component["versions"].values()), "tool"),
                    "active_version": component.get("active_version"),
                    "llm_visibility": "explicit",
                    "versions": versions,
                }
            )
        return values

    def load_failure(self, capability_id: str, version: str) -> str | None:
        for (component_id, component_version), error_type in self._load_failures.items():
            state = self._read_state().get("components", {}).get(component_id, {})
            record = state.get("versions", {}).get(component_version, {}) if isinstance(state, dict) else {}
            if record.get("capability_id") == capability_id and component_version == version:
                return error_type
        return None

    @staticmethod
    def _public_state(component_id: str, component: dict[str, Any], version: str | None, *, transition: str) -> dict[str, Any]:
        record = component.get("versions", {}).get(version, {}) if version else {}
        return {
            "component": {
                "component_id": component_id,
                "resource_type": record.get("resource_type", next((r.get("resource_type", "tool") for r in component.get("versions", {}).values()), "tool")),
                "component_version": version,
                "capability_id": record.get("capability_id"),
                "capability_version": record.get("capability_version"),
                "active_version": component.get("active_version"),
                "admitted": bool(record),
                "llm_visibility": "explicit",
            },
            "transition": transition,
        }

    def _component_state(self, state: dict[str, Any], component_id: str) -> dict[str, Any]:
        if not isinstance(component_id, str) or not _COMPONENT_ID.fullmatch(component_id):
            raise ComponentError("component_id is invalid")
        component = state.get("components", {}).get(component_id)
        if not isinstance(component, dict) or not isinstance(component.get("versions"), dict):
            raise ComponentError("component has no admitted versions")
        return component

    def _validate_admitted_method(self, component_id: str, version: str, component: Mapping[str, Any]) -> Any:
        if not isinstance(version, str) or not _VERSION.fullmatch(version):
            raise ComponentError("component version is invalid")
        record = component.get("versions", {}).get(version)
        if not isinstance(record, dict) or record.get("resource_type") != "method_data":
            raise ComponentError("method version is not admitted")
        package_path = self.workspace / str(record.get("package_path", ""))
        if not package_path.resolve().is_relative_to(self.installed_root.resolve()):
            raise ComponentError("admitted method path escapes its local install root")
        candidate = discover_local_component(package_path)
        if (candidate.manifest["resource_type"] != "method_data" or candidate.component_id != component_id
            or candidate.version != version):
            raise ComponentError("installed method identity differs from its admitted version")
        for field in ("package_sha256", "manifest_sha256", "source_sha256"):
            if record.get(field) != getattr(candidate, field):
                raise ComponentError(f"admitted method {field} changed after admission")
        return candidate

    @contextmanager
    def acquire_method(self, component_id: str = "project-understand") -> Any:
        """Freeze an admitted method for the complete run; updates require idle."""
        with self._load_lock:
            component = self._component_state(self._read_state(), component_id)
            version = component.get("active_version")
            if not isinstance(version, str):
                raise ComponentError("method has no active version")
            candidate = self._validate_admitted_method(component_id, version, component)
            snapshot = candidate.snapshot()
            self._method_leases[component_id] = self._method_leases.get(component_id, 0) + 1
        try:
            yield snapshot
        finally:
            with self._load_lock:
                self._method_leases[component_id] -= 1

    def _load_admitted(
        self, component_id: str, version: str, component: Mapping[str, Any]
    ) -> tuple[ComponentCandidate, dict[str, Any], Any]:
        if not isinstance(version, str) or not _VERSION.fullmatch(version):
            raise ComponentError("component version is invalid")
        record = component.get("versions", {}).get(version)
        if not isinstance(record, dict):
            raise ComponentError("component version is not admitted")
        package_path = self.workspace / str(record.get("package_path", ""))
        if not package_path.resolve().is_relative_to(self.installed_root.resolve()):
            raise ComponentError("admitted component path escapes its local install root")
        candidate = discover_local_component(package_path)
        if candidate.component_id != component_id or candidate.version != version:
            raise ComponentError("installed manifest identity differs from its admitted version")
        for field, candidate_value in (
            ("package_sha256", candidate.package_sha256),
            ("manifest_sha256", candidate.manifest_sha256),
            ("source_sha256", candidate.source_sha256),
        ):
            if record.get(field) != candidate_value:
                raise ComponentError(f"admitted component {field} changed after admission")
        filename, class_name = _ENTRYPOINT.fullmatch(candidate.manifest["source"]["entrypoint"]).groups()
        module_name = f"_catalyst_component_{candidate.source_sha256}"
        spec = importlib.util.spec_from_file_location(module_name, candidate.package_dir / filename)
        if spec is None or spec.loader is None:
            raise ComponentError("component Python entrypoint could not be loaded")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            implementation_type = getattr(module, class_name, None)
            if not isinstance(implementation_type, type):
                raise ComponentError("component entrypoint class is missing")
            implementation = implementation_type()
        except ComponentError:
            if sys.modules.get(module_name) is module:
                sys.modules.pop(module_name, None)
            raise
        except Exception as exc:
            if sys.modules.get(module_name) is module:
                sys.modules.pop(module_name, None)
            raise ComponentError(f"component entrypoint failed during activation: {type(exc).__name__}") from exc
        try:
            described = implementation.describe() if callable(getattr(implementation, "describe", None)) else None
            expected = candidate.binding
            if not isinstance(described, RuntimeCapabilityDescriptor):
                raise ComponentError("component must implement describe() using the Catalyst Capability contract")
            normalized = {
                "capability_id": described.id,
                "name": described.name,
                "description": described.description,
                "input_schema": dict(described.input_schema),
                "output_schema": dict(described.output_schema),
            }
            if normalized != {
                "capability_id": expected["capability_id"],
                "name": expected["name"],
                "description": expected["description"],
                "input_schema": expected["input_schema"],
                "output_schema": expected["output_schema"],
            }:
                raise ComponentError("component describe() does not match its admitted Manifest binding")
            if not callable(getattr(implementation, "invoke", None)):
                raise ComponentError("component must implement invoke(parameters, context)")
        except Exception:
            closer = getattr(implementation, "close", None)
            if callable(closer):
                try:
                    closer()
                except Exception:
                    pass
            if sys.modules.get(module_name) is module:
                sys.modules.pop(module_name, None)
            raise
        return candidate, record, _LoadedLocalTool(implementation, module_name, module)

    def _register(self, candidate: ComponentCandidate, record: Mapping[str, Any], implementation: Any, *, activate: bool) -> None:
        binding = candidate.binding
        self.catalog.register(
            implementation,
            capability_version=binding["capability_version"],
            execution=binding["execution"],
            metadata={
                "implementation": "admitted-local-component",
                "component_id": candidate.component_id,
                "component_version": candidate.version,
                "resource_type": candidate.manifest["resource_type"],
                "manifest_sha256": candidate.manifest_sha256,
                "source_sha256": candidate.source_sha256,
                "package_sha256": candidate.package_sha256,
                "model_policy": candidate.model_policy,
                "llm_visibility": "explicit",
            },
            activate=activate,
        )
