"""Capability Contract Conformance Pilot v0.1 — focused CC gates.

Run: python tests/test_capability_contract_conformance_pilot.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runtime.contracts import (
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Success,
)
from examples.platform_standard_reference import (
    ComposeReportCapability,
    compose_report_descriptor,
    make_report_invocation,
    reference_runtime_factory,
)
from platform_standard.models import CapabilityDescriptor
from platform_standard.registry import InMemoryDescriptorRegistry
from platform_standard.runtime_adapter import (
    AdapterConfigurationError,
    RuntimeAdapter,
)


class IncompatibleInputCapability:
    invoked = False

    def describe(self):
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Wrong Input",
            description="Deliberately incompatible direct binding.",
            input_schema={
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        type(self).invoked = True
        return Success({})


class IncompatibleOutputCapability:
    invoked = False

    def describe(self):
        d = compose_report_descriptor()
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Wrong Output",
            description="Deliberately incompatible direct binding.",
            input_schema=d.input_schema,
            output_schema={"type": "string"},
        )

    def invoke(self, parameters, context):
        type(self).invoked = True
        return Success("wrong")


class ReorderedSchemaCapability:
    """Same structural contract with ordinary mapping key order changed."""

    def describe(self):
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Reordered",
            description="Equivalent map ordering.",
            input_schema={
                "additionalProperties": False,
                "required": ["title"],
                "properties": {
                    "sections": {"items": {"type": "string"}, "type": "array"},
                    "title": {"type": "string"},
                },
                "type": "object",
            },
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        return Success({"report_text": "ok"})


class DescriptorFlipCapability:
    """Would expose a different contract on a second describe() call."""

    def __init__(self):
        self.describe_calls = 0

    def describe(self):
        self.describe_calls += 1
        if self.describe_calls == 1:
            d = compose_report_descriptor()
            return RuntimeCapabilityDescriptor(
                id="compose_report",
                name="Stable first descriptor",
                description="Conforming preflight descriptor.",
                input_schema=d.input_schema,
                output_schema=d.output_schema,
            )
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Changed descriptor",
            description="Would be incompatible if re-read during registration.",
            input_schema={"type": "string"},
            output_schema={"type": "string"},
        )

    def invoke(self, parameters, context):
        return Success({"report_text": "stable"})


def _registry():
    registry = InMemoryDescriptorRegistry()
    registry.register(compose_report_descriptor())
    return registry


def _assert_binding_rejected(impl):
    try:
        RuntimeAdapter(
            _registry(),
            {("compose_report", "1.0.0"): impl},
            runtime_factory=reference_runtime_factory,
        )
    except AdapterConfigurationError as exc:
        assert "direct-binding schemas are not structurally equivalent" in str(exc)
        return
    raise AssertionError("expected direct-binding conformance rejection")


def test_cc1_conforming_reference_binding_accepted():
    adapter = RuntimeAdapter(
        _registry(),
        {("compose_report", "1.0.0"): ComposeReportCapability()},
        runtime_factory=reference_runtime_factory,
    )
    result = adapter.execute(
        make_report_invocation(
            {"title": "Conformance", "sections": []},
            invocation_id="inv_cc1",
            trace_id="tr_cc1",
        )
    )
    assert result.status == "success"


def test_cc4_incompatible_input_rejected_before_execution():
    IncompatibleInputCapability.invoked = False
    _assert_binding_rejected(IncompatibleInputCapability())
    assert IncompatibleInputCapability.invoked is False


def test_cc5_incompatible_output_rejected_before_execution():
    IncompatibleOutputCapability.invoked = False
    _assert_binding_rejected(IncompatibleOutputCapability())
    assert IncompatibleOutputCapability.invoked is False


def test_cc6_mapping_key_order_does_not_create_false_mismatch():
    adapter = RuntimeAdapter(
        _registry(),
        {("compose_report", "1.0.0"): ReorderedSchemaCapability()},
        runtime_factory=reference_runtime_factory,
    )
    result = adapter.execute(
        make_report_invocation(
            {"title": "Ordering", "sections": []},
            invocation_id="inv_cc6",
            trace_id="tr_cc6",
        )
    )
    assert result.status == "success"


def test_cc7_conformance_logic_is_adapter_local():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    adapter_source = open(
        os.path.join(repo, "platform_standard", "runtime_adapter.py"),
        encoding="utf-8",
    ).read()
    assert "_checked_direct_binding_descriptor" in adapter_source
    runtime_source = open(
        os.path.join(repo, "agent_runtime", "capability_executor.py"),
        encoding="utf-8",
    ).read()
    assert "_checked_direct_binding_descriptor" not in runtime_source


def test_cc8_checked_descriptor_is_reused_for_runtime_registration():
    impl = DescriptorFlipCapability()
    adapter = RuntimeAdapter(
        _registry(),
        {("compose_report", "1.0.0"): impl},
        runtime_factory=reference_runtime_factory,
    )
    assert impl.describe_calls == 1
    result = adapter.execute(
        make_report_invocation(
            {"title": "Frozen", "sections": []},
            invocation_id="inv_cc8",
            trace_id="tr_cc8",
        )
    )
    assert result.status == "success"
    assert impl.describe_calls == 1


def test_cc9_platform_capability_object_not_expanded():
    fields = tuple(CapabilityDescriptor.__dataclass_fields__)
    assert fields == (
        "standard_version",
        "kind",
        "id",
        "extensions",
        "name",
        "description",
        "capability_version",
        "input_schema",
        "output_schema",
        "execution",
    )


def test_cc12_reference_rule_is_explicitly_non_universal():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = open(
        os.path.join(repo, "platform_standard", "runtime_adapter.py"),
        encoding="utf-8",
    ).read()
    assert "not a universal requirement for future mapping Adapters" in source
    assert "future mapping Adapter" in source


def main() -> None:
    tests = [
        ("CC-1 conforming reference binding accepted", test_cc1_conforming_reference_binding_accepted),
        ("CC-4 incompatible input rejected before execution", test_cc4_incompatible_input_rejected_before_execution),
        ("CC-5 incompatible output rejected before execution", test_cc5_incompatible_output_rejected_before_execution),
        ("CC-6 map ordering normalized", test_cc6_mapping_key_order_does_not_create_false_mismatch),
        ("CC-7 conformance is Adapter-local", test_cc7_conformance_logic_is_adapter_local),
        ("CC-8 checked descriptor reused", test_cc8_checked_descriptor_is_reused_for_runtime_registration),
        ("CC-9 Platform object set unchanged", test_cc9_platform_capability_object_not_expanded),
        ("CC-12 direct-binding rule documented as non-universal", test_cc12_reference_rule_is_explicitly_non_universal),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASSED: {name}")
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            print(f"FAILED: {name} -> {type(exc).__name__}: {exc}")
    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        raise SystemExit(1)
    print("\nALL CAPABILITY CONTRACT CONFORMANCE PILOT TESTS PASSED")


if __name__ == "__main__":
    main()
