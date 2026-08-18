"""Platform Standard Core v0.1 — reference implementations.

Reference Runtime Capabilities (implementing the existing agent_runtime
Capability Protocol) plus their Standard descriptors and a stack-assembly
helper. This is the "necessary reference implementation" for the vertical
slice; it is NOT a plugin framework or production registry.
"""

from __future__ import annotations

import uuid

from agent_runtime.contracts import (
    CapabilityDescriptor as RuntimeCapabilityDescriptor,
    Success,
)

from platform_standard.models import (
    ArtifactRef,
    CapabilityDescriptor,
    Invocation,
    Producer,
)
from platform_standard.registry import InMemoryDescriptorRegistry
from platform_standard.runtime_adapter import RuntimeAdapter


class ComposeReportCapability:
    """Existing-Runtime capability: compose a markdown report from structured input."""

    def describe(self) -> RuntimeCapabilityDescriptor:
        return RuntimeCapabilityDescriptor(
            id="compose_report",
            name="Compose Report",
            description="Create a report from structured input.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "sections": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title"],
                "additionalProperties": False,
            },
            # Direct-binding reference path: Runtime-local declared public
            # output contract matches the Platform Capability contract.
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context) -> Success:
        title = parameters["title"]
        sections = parameters.get("sections", [])
        body = "\n\n".join(sections)
        report = f"# {title}\n\n{body}".strip()
        return Success(
            {
                "report_text": report,
                "artifact_uri": f"file:///outputs/report_{title.replace(' ', '_')}.md",
            }
        )


class CountWordsCapability:
    """A meaningfully different capability: count words in a text."""

    def describe(self) -> RuntimeCapabilityDescriptor:
        return RuntimeCapabilityDescriptor(
            id="count_words",
            name="Count Words",
            description="Count the number of words in a text.",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
            # Same current direct-binding rule as compose_report.
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context) -> Success:
        return Success({"word_count": len(str(parameters["text"]).split())})


def compose_report_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id="compose_report",
        name="Compose Report",
        description="Create a report from structured input.",
        capability_version="1.0.0",
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "sections": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title"],
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        execution={"side_effect": "none"},
    )


def count_words_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id="count_words",
        name="Count Words",
        description="Count the number of words in a text.",
        capability_version="1.0.0",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        execution={"side_effect": "none"},
    )


def make_report_invocation(input_: dict, *, invocation_id: str = "inv_001", trace_id: str = "trace_001") -> Invocation:
    return Invocation(
        id=invocation_id,
        capability_id="compose_report",
        capability_version="1.0.0",
        input=input_,
        context={"extensions": {}},
        trace_id=trace_id,
    )


def reference_runtime_factory(capabilities, reasoner):
    """Reference-only Runtime composition.

    Policy / StateStore are chosen HERE (reference vertical-slice config), not
    inside the generic RuntimeAdapter.
    """
    from agent_runtime.runtime import Runtime
    from examples.fakes import AllowAllPolicy, InMemoryStateStore

    return Runtime(reasoner, capabilities, AllowAllPolicy(), InMemoryStateStore())


def compose_report_artifact_mapper(output, invocation):
    """Adapter-local artifact mapping for compose_report.

    Business semantics (artifact_type="report") live in this reference mapper,
    NOT in the generic RuntimeAdapter.
    """
    uri = output.get("artifact_uri") if isinstance(output, dict) else None
    if isinstance(uri, str) and uri:
        return (
            ArtifactRef(
                id=f"artifact_{uuid.uuid4().hex[:12]}",
                artifact_type="report",
                artifact_version="1",
                uri=uri,
                producer=Producer(
                    capability_id=invocation.capability_id,
                    invocation_id=invocation.id,
                ),
            ),
        )
    return ()


def make_stack():
    """Assemble the reference stack: registry + bindings + adapter."""
    registry = InMemoryDescriptorRegistry()
    registry.register(compose_report_descriptor())
    adapter = RuntimeAdapter(
        registry,
        bindings={("compose_report", "1.0.0"): ComposeReportCapability()},
        runtime_factory=reference_runtime_factory,
        artifact_mappers={("compose_report", "1.0.0"): compose_report_artifact_mapper},
    )
    return registry, adapter


__all__ = [
    "ComposeReportCapability",
    "CountWordsCapability",
    "compose_report_descriptor",
    "count_words_descriptor",
    "make_report_invocation",
    "make_stack",
]
