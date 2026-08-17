"""Platform Standard Core v0.1 — InMemory Descriptor Registry (Spec §11).

Required operations:

    register(descriptor)
    get(capability_id, capability_version)
    list()
    reject duplicate id/version

It stores Standard descriptors only and is NOT the future production Registry
Service.
"""

from __future__ import annotations

from .models import CapabilityDescriptor


class DuplicateDescriptorError(Exception):
    """Same (capability_id, capability_version) registered twice."""


class InMemoryDescriptorRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[tuple[str, str], CapabilityDescriptor] = {}

    def register(self, descriptor: CapabilityDescriptor) -> None:
        key = (descriptor.id, descriptor.capability_version)
        if key in self._descriptors:
            raise DuplicateDescriptorError(
                f"descriptor {descriptor.id!r} version {descriptor.capability_version!r} already registered"
            )
        self._descriptors[key] = descriptor

    def get(self, capability_id: str, capability_version: str) -> CapabilityDescriptor | None:
        return self._descriptors.get((capability_id, capability_version))

    def list(self) -> tuple[CapabilityDescriptor, ...]:
        return tuple(self._descriptors.values())


__all__ = ["DuplicateDescriptorError", "InMemoryDescriptorRegistry"]
