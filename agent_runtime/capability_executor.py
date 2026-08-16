"""CapabilityExecutor：resolve / validate / invoke / normalize 的执行 seam。

不做 reasoning、policy、session lifecycle、retry、approval、sandbox、model calls。
"""

from __future__ import annotations

import time
from typing import Mapping

from .contracts import (
    Action,
    Capability,
    CapabilityDescriptor,
    Failure,
    Observation,
    Success,
)
from .errors import (
    CapabilityContractError,
    CapabilityExecutionError,
    CapabilityRegistrationError,
    CapabilityTimeoutUncertainError,
    ExecutionCancelled,
    RuntimeConfigurationError,
)
from .execution import (
    ExecutionControlPlane,
    ExecutionTimeoutConfig,
    ThreadedExecutionRunner,
)
from .snapshot import snapshot_observation, snapshot_value


# ---------------------------------------------------------------------------
# Schema 校验（v0.1 有限 subset；不支持 ≠ 忽略）
# ---------------------------------------------------------------------------

SUPPORTED_TYPES = ("object", "array", "string", "number", "integer", "boolean", "null")
SUPPORTED_KEYWORDS = ("type", "properties", "required", "additionalProperties", "items", "enum")


class _SchemaError(Exception):
    """schema 声明了 executor 不支持/无法执行的约束。"""


def _validate_schema_supported(schema, path: str = "$") -> None:
    """注册阶段：schema 只能使用支持的 keyword/type，否则抛 _SchemaError。"""
    if not isinstance(schema, dict):
        raise _SchemaError(f"{path}: schema must be an object")

    for key in schema:
        if key not in SUPPORTED_KEYWORDS:
            raise _SchemaError(f"{path}: unsupported keyword {key!r}")

    if "type" in schema and schema["type"] not in SUPPORTED_TYPES:
        raise _SchemaError(f"{path}: unsupported type {schema['type']!r}")

    if "properties" in schema:
        props = schema["properties"]
        if not isinstance(props, dict):
            raise _SchemaError(f"{path}.properties: must be an object")
        for name, subschema in props.items():
            if not isinstance(name, str):
                raise _SchemaError(
                    f"{path}.properties: keys must be strings, got {type(name).__name__}"
                )
            _validate_schema_supported(subschema, f"{path}.properties.{name}")

    if "items" in schema:
        _validate_schema_supported(schema["items"], f"{path}.items")

    if "required" in schema:
        req = schema["required"]
        if not isinstance(req, list) or not all(isinstance(x, str) for x in req):
            raise _SchemaError(f"{path}.required: must be an array of strings")

    # v0.1 只支持布尔形式 additionalProperties（true/false）
    if "additionalProperties" in schema and not isinstance(
        schema["additionalProperties"], bool
    ):
        raise _SchemaError(f"{path}.additionalProperties: only boolean supported in v0.1")

    if "enum" in schema and not isinstance(schema["enum"], list):
        raise _SchemaError(f"{path}.enum: must be an array")


def _type_matches(expected: str, value) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _value_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _json_kind(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return None


def _enum_contains(enum_values, value) -> bool:
    """JSON 语义的 enum 比较：boolean 与 number 不同 kind，不因 Python True==1 而相等。"""
    kind = _json_kind(value)
    for candidate in enum_values:
        if _json_kind(candidate) == kind and candidate == value:
            return True
    return False


def validate_against_schema(schema, value, path: str = "$"):
    """运行时校验：返回错误字符串（含定位路径）或 None 表示通过。"""
    if "type" in schema and not _type_matches(schema["type"], value):
        return f"{path}: expected {schema['type']}, got {_value_type(value)}"

    if "enum" in schema and not _enum_contains(schema["enum"], value):
        return f"{path}: not one of {schema['enum']!r}"

    if any(k in schema for k in ("properties", "required", "additionalProperties")):
        if not isinstance(value, dict):
            return f"{path}: expected object, got {_value_type(value)}"
        return _validate_object(schema, value, path)

    if "items" in schema:
        if not isinstance(value, list):
            return f"{path}: expected array, got {_value_type(value)}"
        return _validate_array(schema, value, path)

    return None


def _validate_object(schema, value, path):
    if "required" in schema:
        for key in schema["required"]:
            if key not in value:
                return f"{path}: missing required property {key!r}"

    if "properties" in schema:
        for key, subschema in schema["properties"].items():
            if key in value:
                err = validate_against_schema(subschema, value[key], f"{path}.{key}")
                if err is not None:
                    return err

    if schema.get("additionalProperties") is False:
        allowed = set(schema.get("properties", {}).keys())
        for key in value:
            if key not in allowed:
                return f"{path}: unexpected property {key!r}"

    return None


def _validate_array(schema, value, path):
    if "items" in schema:
        for i, item in enumerate(value):
            err = validate_against_schema(schema["items"], item, f"{path}[{i}]")
            if err is not None:
                return err
    return None


def _snapshot_descriptor(descriptor: CapabilityDescriptor) -> CapabilityDescriptor:
    """defensive snapshot：不持有 capability 返回对象中的 mutable schema 引用。"""
    try:
        return CapabilityDescriptor(
            id=descriptor.id,
            name=descriptor.name,
            description=descriptor.description,
            input_schema=snapshot_value(descriptor.input_schema),
            output_schema=snapshot_value(descriptor.output_schema),
        )
    except CapabilityContractError as exc:
        raise CapabilityRegistrationError(
            f"capability {descriptor.id!r} has non-durable descriptor schema: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# DefaultCapabilityExecutor
# ---------------------------------------------------------------------------

class DefaultCapabilityExecutor:
    """按固定顺序执行：snapshot → resolve → validate → invoke → normalize。"""

    def __init__(
        self,
        capabilities: Mapping[str, Capability],
        *,
        execution_runner: ThreadedExecutionRunner | None = None,
        timeout_config: ExecutionTimeoutConfig | None = None,
        control_plane: ExecutionControlPlane | None = None,
        clock=None,
    ) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._descriptors: dict[str, CapabilityDescriptor] = {}
        self._timeout_config = timeout_config or ExecutionTimeoutConfig()
        # 下层直接组合的 fail-closed：timeout 会产生 live background worker，
        # 因此必须属于一个 execution control domain，否则无法跨组合共享 live guard。
        if (
            self._timeout_config.timeout_seconds is not None
            and control_plane is None
        ):
            raise RuntimeConfigurationError(
                "timeout-enabled DefaultCapabilityExecutor requires an execution "
                "control plane (control_plane=...); construct through RuntimeDomain + Runtime"
            )
        self._control_plane = control_plane
        self._runner = execution_runner or ThreadedExecutionRunner(
            control_plane=control_plane,
            clock=clock if clock is not None else time.monotonic,
        )
        for key, capability in dict(capabilities).items():
            self._register(key, capability)

    def _register(self, key, capability: Capability) -> None:
        if not isinstance(key, str) or not key:
            raise CapabilityRegistrationError("capability key must be a non-empty str")
        try:
            descriptor = capability.describe()
        except ValueError as exc:
            # CapabilityDescriptor.__post_init__ 拒绝非 portable id / 非 str name/description
            raise CapabilityRegistrationError(
                f"capability under key {key!r} returned invalid descriptor: {exc}"
            ) from exc
        if not isinstance(descriptor, CapabilityDescriptor):
            raise CapabilityRegistrationError(
                f"capability under key {key!r} returned non-CapabilityDescriptor: "
                f"{type(descriptor).__name__}"
            )
        if not descriptor.id:
            raise CapabilityRegistrationError(
                f"capability under key {key!r} has empty descriptor.id"
            )
        if key != descriptor.id:
            raise CapabilityRegistrationError(
                f"capability key {key!r} != descriptor.id {descriptor.id!r}"
            )
        try:
            _validate_schema_supported(descriptor.input_schema, "$")
        except _SchemaError as exc:
            raise CapabilityRegistrationError(
                f"capability {descriptor.id!r} has unsupported input_schema: {exc}"
            ) from exc
        self._capabilities[key] = capability
        # defensive snapshot：后续 capability 改动原始 schema 不影响 runtime
        self._descriptors[key] = _snapshot_descriptor(descriptor)

    def descriptors(self) -> tuple[CapabilityDescriptor, ...]:
        """model-visible descriptors，stable order（insertion），id 与 lookup 一致。

        返回 defensive snapshot：调用方修改返回的 schema 不影响 executor 内部。
        """
        return tuple(_snapshot_descriptor(d) for d in self._descriptors.values())

    def execute(self, action: Action, *, execution_id: str, session_id: str) -> Observation:
        # 1. snapshot / validate Action（根必须是 object）
        parameters = action.parameters
        if not isinstance(parameters, dict):
            return Failure("invalid capability parameters: expected object")
        parameters = snapshot_value(parameters)

        # 2. resolve
        capability = self._capabilities.get(action.capability_id)
        if capability is None:
            return Failure(f"unknown capability: {action.capability_id}")
        descriptor = self._descriptors[action.capability_id]

        # 3. validate parameters against descriptor.input_schema
        err = validate_against_schema(descriptor.input_schema, parameters, "$")
        if err is not None:
            return Failure(f"invalid capability parameters at {err}")

        # 4. invoke via execution runner（cooperative cancellation / deadline）
        # capability body 抛普通异常 = outcome uncertain → CapabilityExecutionError（unresolved）。
        # 明确 cooperative ExecutionCancelled → authoritative Failure("execution cancelled")。
        # deadline 未确认 quiesce → CapabilityTimeoutUncertainError（unresolved）。
        try:
            result = self._runner.run(
                capability,
                snapshot_value(parameters),
                execution_id=execution_id,
                session_id=session_id,
                timeout_seconds=self._timeout_config.timeout_seconds,
                grace_seconds=self._timeout_config.cancellation_grace_seconds,
            )
        except ExecutionCancelled:
            return Failure("execution cancelled")
        except CapabilityExecutionError:
            raise
        except CapabilityTimeoutUncertainError:
            raise
        except CapabilityContractError:
            # 例如 spurious ExecutionCancelled（无 cancel request）——contract violation，unresolved
            raise
        except Exception as exc:  # noqa: BLE001
            raise CapabilityExecutionError(capability_id=action.capability_id) from exc

        # 5. normalize return contract
        if not isinstance(result, (Success, Failure)):
            raise CapabilityContractError(
                f"capability {action.capability_id} returned invalid observation: "
                f"{type(result).__name__}"
            )

        # 6. snapshot durable Observation
        return snapshot_observation(result)
