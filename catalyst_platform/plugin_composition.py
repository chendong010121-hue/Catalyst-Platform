"""Small local composition host for statically shipped Harness plugins.

This module is deliberately limited to source-controlled plugin definitions and
named service injection. It is not a downloader, package loader, marketplace,
or replacement for CapabilityCatalog / LocalComponentLifecycle / Agent Runtime.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence


_PLUGIN_ID = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_PLUGIN_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")


class PluginCompositionError(RuntimeError):
    """A static plugin composition cannot be safely applied or withdrawn."""


@dataclass(frozen=True)
class PluginEffect:
    """Services made available by one plugin and the effect that withdraws them."""

    services: Mapping[str, Any] = field(default_factory=dict)
    revoke: Callable[[], None] = lambda: None


@dataclass(frozen=True)
class PluginDefinition:
    """Source-controlled identity, service contract, and apply function."""

    plugin_id: str
    version: str
    provides: tuple[str, ...]
    requires: tuple[str, ...]
    apply: Callable[["PluginContext"], PluginEffect]


class PluginContext:
    """Read-only view of host services and already applied plugin services."""

    def __init__(self, services: Mapping[str, Any]) -> None:
        self.services = MappingProxyType(dict(services))

    def require(self, name: str) -> Any:
        try:
            return self.services[name]
        except KeyError as exc:
            raise PluginCompositionError(f"required service {name!r} is unavailable") from exc

    def optional(self, name: str, default: Any = None) -> Any:
        return self.services.get(name, default)


@dataclass
class _ActivePlugin:
    definition: PluginDefinition
    effect: PluginEffect


class PluginComposer:
    """Apply an allowlisted profile of source-controlled plugins to host services."""

    def __init__(
        self,
        *,
        definitions: Sequence[PluginDefinition],
        profiles: Mapping[str, Sequence[str]],
        host_services: Mapping[str, Any] | None = None,
    ) -> None:
        by_id: dict[str, PluginDefinition] = {}
        for definition in definitions:
            self._validate_definition(definition)
            if definition.plugin_id in by_id:
                raise PluginCompositionError(f"duplicate plugin ID {definition.plugin_id!r}")
            by_id[definition.plugin_id] = definition
        if not profiles:
            raise PluginCompositionError("at least one static plugin profile is required")
        normalized_profiles: dict[str, tuple[str, ...]] = {}
        for name, plugin_ids in profiles.items():
            if not isinstance(name, str) or not name.strip():
                raise PluginCompositionError("plugin profile names must be non-empty strings")
            ids = tuple(plugin_ids)
            if len(ids) != len(set(ids)):
                raise PluginCompositionError(f"plugin profile {name!r} contains a duplicate plugin ID")
            unknown = [plugin_id for plugin_id in ids if plugin_id not in by_id]
            if unknown:
                raise PluginCompositionError(
                    f"plugin profile {name!r} references unknown plugin ID {unknown[0]!r}"
                )
            normalized_profiles[name] = ids
        host = dict(host_services or {})
        if any(not self._valid_service_name(name) for name in host):
            raise PluginCompositionError("host service names must be non-empty dotted identifiers")
        self._definitions = by_id
        self._profiles = normalized_profiles
        self._host_services = host
        self._services = dict(host)
        self._active: dict[str, _ActivePlugin] = {}
        self._activation_order: list[str] = []

    @staticmethod
    def _valid_service_name(value: Any) -> bool:
        return (
            isinstance(value, str)
            and bool(value.strip())
            and all(part and part.replace("_", "").replace("-", "").isalnum() for part in value.split("."))
        )

    @classmethod
    def _validate_definition(cls, definition: PluginDefinition) -> None:
        if not isinstance(definition, PluginDefinition):
            raise PluginCompositionError("plugin definitions must use PluginDefinition")
        if not isinstance(definition.plugin_id, str) or not _PLUGIN_ID.fullmatch(definition.plugin_id):
            raise PluginCompositionError("plugin ID is invalid")
        if not isinstance(definition.version, str) or not _PLUGIN_VERSION.fullmatch(definition.version):
            raise PluginCompositionError(f"plugin {definition.plugin_id!r} version is invalid")
        if not callable(definition.apply):
            raise PluginCompositionError(f"plugin {definition.plugin_id!r} has no apply function")
        for label, values in (("provided", definition.provides), ("required", definition.requires)):
            if not isinstance(values, tuple) or any(not cls._valid_service_name(value) for value in values):
                raise PluginCompositionError(
                    f"plugin {definition.plugin_id!r} has invalid {label} service names"
                )
            if len(values) != len(set(values)):
                raise PluginCompositionError(
                    f"plugin {definition.plugin_id!r} repeats a {label} service"
                )

    @property
    def active_plugins(self) -> tuple[str, ...]:
        return tuple(self._activation_order)

    def service(self, name: str, default: Any = None) -> Any:
        return self._services.get(name, default)

    def compose(self, profile: str) -> tuple[str, ...]:
        if not isinstance(profile, str) or profile not in self._profiles:
            raise PluginCompositionError(f"unknown plugin profile {profile!r}")
        if self._active:
            raise PluginCompositionError("a plugin profile is already active")
        ordered = self._resolve_order(self._profiles[profile])
        applied: list[str] = []
        try:
            for definition in ordered:
                if definition.plugin_id in self._active:
                    raise PluginCompositionError(
                        f"plugin {definition.plugin_id!r} is already active"
                    )
                effect = definition.apply(PluginContext(self._services))
                if not isinstance(effect, PluginEffect):
                    raise PluginCompositionError(
                        f"plugin {definition.plugin_id!r} apply() must return PluginEffect"
                    )
                try:
                    service_names = set(effect.services)
                    if service_names != set(definition.provides):
                        raise PluginCompositionError(
                            f"plugin {definition.plugin_id!r} effect services do not match declared services"
                        )
                    if service_names.intersection(self._services):
                        collision = sorted(service_names.intersection(self._services))[0]
                        raise PluginCompositionError(
                            f"service {collision!r} is already provided by the host or another plugin"
                        )
                except Exception as exc:
                    try:
                        effect.revoke()
                    except Exception as cleanup_exc:
                        raise PluginCompositionError(
                            f"plugin {definition.plugin_id!r} effect was rejected and its cleanup also failed"
                        ) from cleanup_exc
                    raise
                self._services.update(effect.services)
                self._active[definition.plugin_id] = _ActivePlugin(definition, effect)
                self._activation_order.append(definition.plugin_id)
                applied.append(definition.plugin_id)
        except Exception as exc:
            cleanup_errors = self._revoke_many(reversed(applied))
            if cleanup_errors:
                error = PluginCompositionError(
                    f"plugin profile activation failed and {len(cleanup_errors)} cleanup effect(s) also failed"
                )
                raise error from exc
            raise
        return tuple(self._activation_order)

    def _resolve_order(self, plugin_ids: Sequence[str]) -> tuple[PluginDefinition, ...]:
        definitions = [self._definitions[plugin_id] for plugin_id in plugin_ids]
        provider_by_service: dict[str, str] = {}
        for definition in definitions:
            for service_name in definition.provides:
                if service_name in self._services:
                    raise PluginCompositionError(
                        f"service {service_name!r} is already provided by the host"
                    )
                previous = provider_by_service.get(service_name)
                if previous is not None:
                    raise PluginCompositionError(
                        f"multiple plugins provide service {service_name!r}: {previous!r} and {definition.plugin_id!r}"
                    )
                provider_by_service[service_name] = definition.plugin_id
        for definition in definitions:
            for service_name in definition.requires:
                if service_name not in self._services and service_name not in provider_by_service:
                    raise PluginCompositionError(
                        f"plugin {definition.plugin_id!r} is missing required service {service_name!r}"
                    )
        remaining = list(definitions)
        ordered: list[PluginDefinition] = []
        available = set(self._services)
        while remaining:
            ready = next(
                (definition for definition in remaining if set(definition.requires).issubset(available)),
                None,
            )
            if ready is None:
                raise PluginCompositionError("plugin service dependencies contain a cycle")
            ordered.append(ready)
            available.update(ready.provides)
            remaining.remove(ready)
        return tuple(ordered)

    def unload(self, plugin_id: str) -> None:
        active = self._active.get(plugin_id)
        if active is None:
            raise PluginCompositionError(f"plugin {plugin_id!r} is not active")
        provided = set(active.definition.provides)
        dependents = [
            other_id
            for other_id, other in self._active.items()
            if other_id != plugin_id and provided.intersection(other.definition.requires)
        ]
        if dependents:
            raise PluginCompositionError(
                f"plugin {plugin_id!r} is required by active plugin {dependents[0]!r}"
            )
        cleanup_error = self._revoke_one(plugin_id)
        if cleanup_error is not None:
            raise PluginCompositionError(
                f"plugin {plugin_id!r} was withdrawn but its cleanup effect failed"
            ) from cleanup_error

    def close(self) -> None:
        errors = self._revoke_many(reversed(self._activation_order))
        if errors:
            raise PluginCompositionError(f"{len(errors)} plugin cleanup effect(s) failed") from errors[0]

    def _revoke_many(self, plugin_ids) -> list[Exception]:
        errors = []
        for plugin_id in tuple(plugin_ids):
            error = self._revoke_one(plugin_id)
            if error is not None:
                errors.append(error)
        return errors

    def _revoke_one(self, plugin_id: str) -> Exception | None:
        active = self._active.pop(plugin_id, None)
        if active is None:
            return None
        cleanup_error = None
        try:
            active.effect.revoke()
        except Exception as exc:  # cleanup must not leave the service visible
            cleanup_error = exc
        for service_name in active.definition.provides:
            self._services.pop(service_name, None)
        self._activation_order.remove(plugin_id)
        return cleanup_error
