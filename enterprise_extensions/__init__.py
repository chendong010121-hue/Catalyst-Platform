"""Enterprise Extension Pilot v0.1 — enterprise semantics layer.

Composes OUTSIDE platform_standard Core and agent_runtime. Adds no Core schema
fields. Extension First. Core Promotion Later.
"""

from .identity import (
    EXTENSION_NAME,
    EnterpriseIdentity,
    EnterpriseIdentityError,
    attribute_trace,
    execute_with_enterprise_identity,
    parse_enterprise_identity,
)

__all__ = [
    "EXTENSION_NAME",
    "EnterpriseIdentity",
    "EnterpriseIdentityError",
    "attribute_trace",
    "execute_with_enterprise_identity",
    "parse_enterprise_identity",
]
