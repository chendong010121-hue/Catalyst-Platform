"""Schema & Descriptor Integrity Hardening 测试。"""

from __future__ import annotations

from agent_runtime.capability_executor import (
    DefaultCapabilityExecutor,
    validate_against_schema,
)
from agent_runtime.contracts import Action, CapabilityDescriptor, Failure, Success
from agent_runtime.errors import CapabilityContractError
from agent_runtime.snapshot import snapshot_value


class MutatingSchemaCapability:
    """持有可变 input_schema，注册后可能被外部修改。"""

    def __init__(self):
        self._schema = {
            "type": "object",
            "properties": {"a": {"type": "integer"}},
            "required": ["a"],
        }

    def describe(self):
        return CapabilityDescriptor(
            id="ms", name="ms", description="mutating schema", input_schema=self._schema
        )

    def invoke(self, parameters):
        return Success(42)


# ---------------------------------------------------------------------------
# Descriptor integrity
# ---------------------------------------------------------------------------

def test_a_capability_mutates_original_schema():
    cap = MutatingSchemaCapability()
    executor = DefaultCapabilityExecutor({"ms": cap})

    # 注册之后修改原始 input_schema
    cap._schema["properties"]["a"]["type"] = "string"

    # runtime 仍用注册时的 integer schema
    obs = executor.execute(Action("ms", {"a": "not an int"}))
    assert isinstance(obs, Failure)
    assert "expected integer" in obs.error

    # 合法的 integer 仍通过
    assert isinstance(executor.execute(Action("ms", {"a": 5})), Success)


def test_b_caller_mutates_descriptors_return():
    cap = MutatingSchemaCapability()
    executor = DefaultCapabilityExecutor({"ms": cap})

    descs = executor.descriptors()
    # 修改返回 descriptor 的 nested input_schema
    descs[0].input_schema["properties"]["a"]["type"] = "string"

    # executor runtime validation 不变
    obs = executor.execute(Action("ms", {"a": "not an int"}))
    assert isinstance(obs, Failure)
    assert "expected integer" in obs.error


# ---------------------------------------------------------------------------
# JSON / Python 类型语义
# ---------------------------------------------------------------------------

def test_integer_rejects_bool():
    assert validate_against_schema({"type": "integer"}, True) is not None
    assert validate_against_schema({"type": "integer"}, False) is not None
    assert validate_against_schema({"type": "integer"}, 1) is None


def test_number_rejects_bool():
    assert validate_against_schema({"type": "number"}, True) is not None
    assert validate_against_schema({"type": "number"}, False) is not None
    assert validate_against_schema({"type": "number"}, 1) is None
    assert validate_against_schema({"type": "number"}, 1.5) is None


def test_enum_distinguishes_bool_from_number():
    # enum [1] 不应因 Python True == 1 而接受 True
    assert validate_against_schema({"enum": [1]}, True) is not None
    assert validate_against_schema({"enum": [1]}, 1) is None
    # 反向：enum [True] 不应接受 1
    assert validate_against_schema({"enum": [True]}, 1) is not None


def test_non_finite_float_rejected():
    for bad in (float("nan"), float("inf"), float("-inf")):
        try:
            snapshot_value(bad)
        except CapabilityContractError:
            continue
        raise AssertionError(f"expected CapabilityContractError for {bad!r}")

    # 通过 executor 的 observation 路径同样被拒绝
    class NanCapability:
        def describe(self):
            return CapabilityDescriptor(id="nan", name="nan", description="nan")

        def invoke(self, parameters):
            return Success(float("nan"))

    executor = DefaultCapabilityExecutor({"nan": NanCapability()})
    try:
        executor.execute(Action("nan", {}))
    except CapabilityContractError:
        return
    raise AssertionError("expected CapabilityContractError for NaN observation")


def main() -> None:
    tests = [
        ("A capability 注册后修改原始 schema", test_a_capability_mutates_original_schema),
        ("B 调用方修改 descriptors() 返回值", test_b_caller_mutates_descriptors_return),
        ("integer 不接受 bool", test_integer_rejects_bool),
        ("number 不接受 bool", test_number_rejects_bool),
        ("enum [1] 不接受 True", test_enum_distinguishes_bool_from_number),
        ("NaN / Infinity 拒绝", test_non_finite_float_rejected),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED: {name}")
        except AssertionError as exc:
            failed.append(name)
            print(f"FAILED: {name} -> {exc}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"ERROR : {name} -> {type(exc).__name__}: {exc}")

    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        raise SystemExit(1)
    print("\nALL SCHEMA INTEGRITY TESTS PASSED")


if __name__ == "__main__":
    main()
