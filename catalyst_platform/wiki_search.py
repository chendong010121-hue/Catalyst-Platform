"""Read-only search adapter for a Host-supplied Wiki export."""

import json
from pathlib import Path
from typing import Callable

from agent_runtime.contracts import CapabilityDescriptor, Failure, Success

from .plugin_composition import PluginDefinition, PluginEffect


TOOL_ID = "wiki_search"
SERVICE = "wiki.search"


class WikiSearch:
    def __init__(self, search: Callable):
        self._search = search

    def describe(self):
        return CapabilityDescriptor(
            id=TOOL_ID,
            name="Wiki search",
            description="Find excerpts and source locators in the authorized local Wiki export.",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
        )

    def invoke(self, parameters, context):
        query = parameters.get("query")
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
            return Failure("Wiki search requires a query of 1 to 200 characters.")
        return Success(self._search(query.strip()))


def definition(search: Callable) -> PluginDefinition:
    return PluginDefinition(
        plugin_id="evo-wiki-search",
        version="1.0.0",
        provides=(SERVICE,),
        requires=(),
        apply=lambda context: PluginEffect(services={SERVICE: WikiSearch(search)}),
    )


def load_export(path: Path) -> Callable:
    """Load only the explicitly selected export. Locators are labels, never opened."""
    with path.open("rb") as stream:
        raw = stream.read(256 * 1024 + 1)
    if len(raw) > 256 * 1024:
        raise ValueError("Wiki export exceeds 256 KiB.")
    rows = json.loads(raw)
    limits = {"title": 160, "excerpt": 2000, "source": 400}
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("Wiki export must contain up to 1000 entries.")
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(limits) or any(
            not isinstance(row[key], str) or not 1 <= len(row[key].strip()) <= limit
            for key, limit in limits.items()
        ):
            raise ValueError("Each Wiki entry requires bounded title, excerpt and source strings.")

    def search(query):
        needle = query.casefold()
        matches = [
            dict(row) for row in rows
            if needle in (row["title"] + "\n" + row["excerpt"]).casefold()
        ][:5]
        return {"status": "FOUND" if matches else "NOT_FOUND", "matches": matches}

    return search
