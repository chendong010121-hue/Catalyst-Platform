"""Deterministic mention linking: which known entity a line actually names.

This layer never calls a model and never decides meaning. It answers one narrow
question — "does this text contain a surface we already accepted as an entity?" —
and it answers it the same way every time, with an offset the page layer can show.

Two honest limits are built in rather than hidden:

* A surface that is short or generic (``总部``) matches anything that contains it,
  so it is recorded as ``ambiguous`` instead of being treated as an identification.
* Coverage is bounded by the accepting side: an entity nobody accepted yet cannot
  be matched, and no heuristic here invents it.
"""

from __future__ import annotations

import unicodedata

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .understand_models import _TextUnit

# A two-character Chinese surface inside a longer phrase is a mention, not an
# identification: "总部与分子公司关系" in a consulting framework is not the
# client's 总部 node. These stay out of automatic linking until a reviewer says so.
GENERIC_SURFACES = frozenset({
    "总部", "中心", "公司", "集团", "部门", "机关", "集团总部", "分公司", "子公司",
})

AMBIGUOUS_MAX_CJK = 2

_WHITESPACE = frozenset(" \t\r\n\u3000")

# A card writes a name with quoting punctuation around it ("「农委」"); the
# punctuation belongs to the sentence, not to the name.
_EDGE_PUNCTUATION = "\"'`「」『』《》〈〉（）()[]【】 "


def _is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _cjk_count(text: str) -> int:
    return sum(1 for char in text if _is_cjk(char))


def normalize_surface(value: str) -> str:
    """One spelling per thing: compatibility form, case-folded, no spacing or quotes.

    Spacing is dropped because a card and the sentence quoting it disagree about it
    constantly ("「客 户」" in a card, "客户" in a slide); a boundary that depended on a
    space would miss every such mention.
    """
    folded = unicodedata.normalize("NFKC", value).casefold().strip(_EDGE_PUNCTUATION)
    return "".join(char for char in folded if char not in _WHITESPACE)


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Normalize text and remember, for every normalized index, the original offset."""
    chars: list[str] = []
    offsets: list[int] = []
    for index, char in enumerate(text):
        for item in unicodedata.normalize("NFKC", char).casefold():
            if item in _WHITESPACE:
                continue
            chars.append(item)
            offsets.append(index)
    return "".join(chars), offsets


@dataclass(frozen=True)
class EntityEntry:
    """One accepted surface and the identity it resolves to."""

    surface: str
    canonical_key: str
    canonical_id: str
    kind: str
    business_type: str | None = None

    @property
    def normalized(self) -> str:
        return normalize_surface(self.surface)

    @property
    def ambiguous(self) -> bool:
        normalized = self.normalized
        return normalized in GENERIC_SURFACES or _cjk_count(normalized) <= AMBIGUOUS_MAX_CJK


@dataclass(frozen=True)
class Mention:
    """One accepted surface found at one offset of one text."""

    surface: str
    canonical_key: str
    canonical_id: str
    kind: str
    offset: int
    ambiguous: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "canonical_key": self.canonical_key,
            "canonical_id": self.canonical_id,
            "kind": self.kind,
            "offset": self.offset,
            "ambiguous": self.ambiguous,
        }


@dataclass(frozen=True)
class MentionScan:
    """The mentions of one text plus what the scan could and could not resolve."""

    mentions: tuple[Mention, ...] = ()
    distinct_surfaces: tuple[str, ...] = ()
    ambiguous_surfaces: tuple[str, ...] = ()

    def __len__(self) -> int:
        return len(self.mentions)

    @property
    def canonical_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.canonical_key for item in self.mentions))

    def to_dict(self) -> dict[str, Any]:
        return {
            "mention_count": len(self.mentions),
            "distinct_surfaces": list(self.distinct_surfaces),
            "ambiguous_surfaces": list(self.ambiguous_surfaces),
            "canonical_keys": list(self.canonical_keys),
        }


@dataclass
class EntityIndex:
    """A trie over the accepted surfaces; matching is longest-first and deterministic."""

    entries: dict[str, tuple[EntityEntry, ...]] = field(default_factory=dict)
    _trie: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        trie: dict[str, Any] = {}
        for normalized in self.entries:
            node = trie
            for char in normalized:
                node = node.setdefault(char, {})
            node[""] = normalized
        self._trie = trie

    @classmethod
    def from_entries(cls, entries: Iterable[EntityEntry]) -> EntityIndex:
        grouped: dict[str, list[EntityEntry]] = {}
        for entry in entries:
            normalized = entry.normalized
            if len(normalized) < 2:
                continue
            grouped.setdefault(normalized, []).append(entry)
        return cls(entries={key: tuple(value) for key, value in grouped.items()})

    @classmethod
    def from_meanings(cls, meanings: Iterable[Mapping[str, Any]]) -> EntityIndex:
        """Build from accepted meaning rows (``ProjectWiki.accepted_meanings``)."""
        rows = [row for row in meanings if isinstance(row, Mapping)]
        canonical_keys = {
            row["canonical_id"]: row.get("canonical_key") or row.get("key")
            for row in rows
            if row.get("kind") == "entity" and isinstance(row.get("canonical_id"), str)
        }
        entries: list[EntityEntry] = []
        for row in rows:
            if row.get("kind") not in {"entity", "alias"}:
                continue
            canonical_id = row.get("canonical_id")
            surface = row.get("meaning")
            if not isinstance(canonical_id, str) or not isinstance(surface, str):
                continue
            key = canonical_keys.get(canonical_id) or row.get("canonical_key") or row.get("key")
            if not isinstance(key, str):
                continue
            entries.append(EntityEntry(
                surface=surface,
                canonical_key=key,
                canonical_id=canonical_id,
                kind=str(row.get("kind")),
                business_type=row.get("business_type") if isinstance(row.get("business_type"), str) else None,
            ))
        return cls.from_entries(entries)

    @classmethod
    def from_semantic_state(cls, state: Mapping[str, Any]) -> EntityIndex:
        """Build only from an accepted version; a candidate is not something to link to."""
        active = state.get("active_version_id") if isinstance(state, Mapping) else None
        versions = state.get("accepted_versions") if isinstance(state, Mapping) else None
        if not isinstance(versions, Mapping) or not isinstance(active, str):
            return cls()
        version = versions.get(active)
        meanings = version.get("meanings") if isinstance(version, Mapping) else None
        if not isinstance(meanings, Mapping):
            return cls()
        canonical_keys: dict[str, str] = {}
        entries: list[EntityEntry] = []
        for row in meanings.values():
            if not isinstance(row, Mapping):
                continue
            canonical_id = row.get("canonical_id")
            if row.get("kind") == "entity":
                key = row.get("canonical_key") or row.get("key")
                if isinstance(key, str) and isinstance(canonical_id, str):
                    canonical_keys[canonical_id] = key
        for row in meanings.values():
            if not isinstance(row, Mapping) or row.get("kind") not in {"entity", "alias"}:
                continue
            canonical_id = row.get("canonical_id")
            if not isinstance(canonical_id, str):
                continue
            key = canonical_keys.get(canonical_id) or row.get("canonical_key") or row.get("key")
            surface = row.get("meaning") if row.get("kind") == "entity" else row.get("meaning")
            if not isinstance(key, str) or not isinstance(surface, str):
                continue
            entries.append(EntityEntry(
                surface=surface,
                canonical_key=key,
                canonical_id=canonical_id,
                kind=str(row.get("kind")),
                business_type=row.get("business_type") if isinstance(row.get("business_type"), str) else None,
            ))
        return cls.from_entries(entries)

    @classmethod
    def build(cls, wiki: Any) -> EntityIndex:
        return cls.from_semantic_state(wiki.semantic_state())

    def __len__(self) -> int:
        return len(self.entries)

    @property
    def surfaces(self) -> tuple[str, ...]:
        return tuple(sorted(self.entries, key=lambda item: (-len(item), item)))

    def match(self, text: str) -> MentionScan:
        """Longest-first match at every offset; one surface may match repeatedly."""
        if not text or not self._trie:
            return MentionScan()
        normalized, offsets = normalize_with_map(text)
        found: list[Mention] = []
        position = 0
        length = len(normalized)
        while position < length:
            node = self._trie
            cursor = position
            hit: str | None = None
            while cursor < length:
                node = node.get(normalized[cursor])
                if node is None:
                    break
                cursor += 1
                if "" in node:
                    hit = node[""]
            if hit is None:
                position += 1
                continue
            entry = self.entries[hit][0]
            if self._boundary_holds(text, offsets, position, position + len(hit), entry):
                found.append(Mention(
                    surface=entry.surface,
                    canonical_key=entry.canonical_key,
                    canonical_id=entry.canonical_id,
                    kind=entry.kind,
                    offset=offsets[position],
                    ambiguous=entry.ambiguous,
                ))
            position += len(hit)
        surfaces = tuple(dict.fromkeys(item.surface for item in found))
        ambiguous = tuple(dict.fromkeys(item.surface for item in found if item.ambiguous))
        return MentionScan(mentions=tuple(found), distinct_surfaces=surfaces, ambiguous_surfaces=ambiguous)

    @staticmethod
    def _boundary_holds(
        original: str,
        offsets: Sequence[int],
        start: int,
        end: int,
        entry: EntityEntry,
    ) -> bool:
        """A Latin surface must not be a fragment of a longer Latin word.

        The check reads the original text, not the normalized one: normalization drops
        spacing, so "and marketing center" would otherwise look like "…andmarketingcenter".
        """
        if _cjk_count(entry.normalized):
            return True
        first = offsets[start]
        last = offsets[end - 1] if end - 1 < len(offsets) else first
        before = original[first - 1] if first > 0 else ""
        after = original[last + 1] if last + 1 < len(original) else ""
        for char in (before, after):
            if char and (char.isalnum() or char == "_"):
                return False
        return True


def scan_units(index: EntityIndex, units: Sequence[_TextUnit]) -> dict[str, Any]:
    """Scan many units at once: per-unit mentions plus one aggregate for the source.

    Confident and ambiguous mentions are counted apart. A generic surface such as
    ``分公司`` matches hundreds of lines and identifies none of them, so it must not
    inflate how much of a document we claim to already know.
    """
    rows = []
    per_canonical: dict[str, int] = {}
    per_confident: dict[str, int] = {}
    ambiguous_total = 0
    units_with_confident = 0
    for unit in units:
        scan = index.match(unit.quote or "")
        if not scan.mentions:
            continue
        if any(not item.ambiguous for item in scan.mentions):
            units_with_confident += 1
        for mention in scan.mentions:
            per_canonical[mention.canonical_key] = per_canonical.get(mention.canonical_key, 0) + 1
            if not mention.ambiguous:
                per_confident[mention.canonical_key] = per_confident.get(mention.canonical_key, 0) + 1
        ambiguous_total += sum(1 for item in scan.mentions if item.ambiguous)
        rows.append({
            "locator": unit.locator,
            "mentions": [item.to_dict() for item in scan.mentions],
        })
    mention_count = sum(len(row["mentions"]) for row in rows)
    return {
        "units_scanned": len(units),
        "units_with_mentions": len(rows),
        "units_with_confident": units_with_confident,
        "mention_count": mention_count,
        "confident_mention_count": mention_count - ambiguous_total,
        "ambiguous_count": ambiguous_total,
        "distinct_canonical": len(per_canonical),
        "distinct_confident": len(per_confident),
        "per_canonical": dict(sorted(per_canonical.items(), key=lambda item: (-item[1], item[0]))),
        "per_confident": dict(sorted(per_confident.items(), key=lambda item: (-item[1], item[0]))),
        "rows": rows,
    }
