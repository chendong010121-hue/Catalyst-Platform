from __future__ import annotations

from typing import Any

from shared.model import source_for


def adapt(case: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    source = source_for(case, registry)
    return {
        "track": "A_PRIME",
        "groups": ["G-BASE"],
        "base": source,
        "generic_metadata": {
            "section": source["locator"].split("/")[0],
            "content_kind": source["unit_type"],
            "language": "zh-CN",
        },
        "semantic_fields": {},
    }
