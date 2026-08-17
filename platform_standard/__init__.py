"""Platform Standard Core v0.1 — stable shared language above the Agent Runtime.

This package is deliberately small and enterprise-free / domain-free. Future
governance/enterprise/domain variation enters through Extensions first.
"""

from .extensions import (
    Extension,
    RESERVED_NAMESPACES,
    RESULT_STATUSES,
    SUPPORTED_EVENT_TYPES,
    SUPPORTED_SIDE_EFFECTS,
    validate_extensions,
)
from .models import (
    ArtifactRef,
    CapabilityDescriptor,
    Invocation,
    Producer,
    Result,
    TraceEvent,
)
from .registry import DuplicateDescriptorError, InMemoryDescriptorRegistry
from .runtime_adapter import DirectedReasoner, RuntimeAdapter
from .validation import PlatformValidator, ValidationError

__all__ = [
    "ArtifactRef",
    "CapabilityDescriptor",
    "DirectedReasoner",
    "DuplicateDescriptorError",
    "Extension",
    "InMemoryDescriptorRegistry",
    "Invocation",
    "PlatformValidator",
    "Producer",
    "RESERVED_NAMESPACES",
    "RESULT_STATUSES",
    "Result",
    "RuntimeAdapter",
    "SUPPORTED_EVENT_TYPES",
    "SUPPORTED_SIDE_EFFECTS",
    "TraceEvent",
    "ValidationError",
    "validate_extensions",
]
