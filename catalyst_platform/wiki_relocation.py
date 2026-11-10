"""Where an accepted citation went when its source changed, without a model or a new version.

An accepted evidence row is anchored to a source revision and the sha256 of one line. Change
that source by a single line and every anchor in it goes stale at once — on the real corpus
that was 294 of 294 evidence rows and 92 of 103 pages from a three line edit at the top of a
file. Until now the only thing that could restore those anchors was paying a model to read
the whole document again.

This module recomputes *where the same text is now*. It hashes every line of the current
revision and maps an old anchor only onto a line with the **identical** hash; near-identical
text is not accepted, because a citation that points at the wrong line is worse than one that
says it went stale.

Three things it deliberately never does:

* it never writes the store, so an accepted version is never rewritten by an edit on disk;
* it never creates an accepted version — relocation is not knowledge, and re-accepting a
  revision still goes through submit / evaluate / decide / activate;
* it never takes part in a decision. `evaluate` keeps checking the candidate's own revision;
  the overlay is read by the page projection and by nothing else.
"""

from __future__ import annotations

import hashlib
import json

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

CONTRACT = "catalyst.relocation.v1"
RELOCATED = "relocated"
STALE = "stale"
METHOD = "line_sha256_exact"

# How many overlays one source may keep. An edit older than this is not worth tracking: by
# then re-reading the document (or re-accepting a revision) is the honest answer.
MAX_OVERLAYS_PER_SOURCE = 5


def overlay_root(workspace: Path | str) -> Path:
    """Where derived relocations live: beside the store, never inside it."""
    return Path(workspace).expanduser().resolve() / ".catalyst" / "relocation"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def line_index(content: str) -> dict[str, list[int]]:
    """Every line of one revision keyed by its own hash; line numbers are 1-based."""
    index: dict[str, list[int]] = {}
    for number, line in enumerate(content.splitlines(), start=1):
        index.setdefault(_digest(line), []).append(number)
    return index


def map_spans(spans: Iterable[tuple[int, int, str]], content: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Map old ``(line_start, line_end, span_sha256)`` anchors onto the current revision.

    A span moves only when a line of the new revision has exactly the old line's hash. When
    the same line occurs several times the nearest one wins, and the entry says so
    (``exact_nearest``) so a reader can tell a unique anchor from a plausible one.
    """
    index = line_index(content)
    moved: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []
    for line_start, line_end, span_sha256 in spans:
        candidates = index.get(span_sha256) or []
        if not candidates:
            unmapped.append({
                "line_start": line_start, "line_end": line_end,
                "span_sha256": span_sha256, "reason": "span_absent",
            })
            continue
        nearest = min(candidates, key=lambda number: (abs(number - line_start), number))
        shift = nearest - line_start
        moved.append({
            "line_start": line_start, "line_end": line_end,
            "new_line_start": nearest, "new_line_end": line_end + shift,
            "span_sha256": span_sha256,
            "confidence": "exact" if len(candidates) == 1 else "exact_nearest",
            "candidates": len(candidates),
        })
    return moved, unmapped


def stale_spans(meanings: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[tuple[int, int, str]]]:
    """The anchors that need relocating, grouped by the source revision they still cite."""
    grouped: dict[tuple[str, str], set[tuple[int, int, str]]] = {}
    for row in meanings:
        for evidence in row.get("evidence") or []:
            if evidence.get("freshness_status") != STALE:
                continue
            source_id = str(evidence.get("source_id") or "")
            revision = str(evidence.get("source_revision") or "")
            start = evidence.get("line_start")
            sha = evidence.get("span_sha256")
            if not source_id or not revision or not isinstance(start, int) or not isinstance(sha, str):
                continue
            end = evidence.get("line_end")
            grouped.setdefault((source_id, revision), set()).add(
                (start, end if isinstance(end, int) else start, sha))
    return {key: sorted(value) for key, value in grouped.items()}


def _overlay_path(workspace: Path | str, source_id: str, old_revision: str, new_revision: str) -> Path:
    return overlay_root(workspace) / source_id / f"{old_revision[:12]}-{new_revision[:12]}.json"


def _write_overlay(workspace: Path | str, payload: Mapping[str, Any]) -> Path:
    path = _overlay_path(workspace, str(payload["source_id"]),
                         str(payload["old_revision"]), str(payload["new_revision"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    _prune(workspace, str(payload["source_id"]))
    return path


def _prune(workspace: Path | str, source_id: str) -> list[str]:
    folder = overlay_root(workspace) / source_id
    files = sorted(folder.glob("*.json"))
    if len(files) <= MAX_OVERLAYS_PER_SOURCE:
        return []
    removed = []
    for path in files[:len(files) - MAX_OVERLAYS_PER_SOURCE]:
        path.unlink()
        removed.append(str(path))
    return removed


def relocate(wiki: Any, *, source_ids: Sequence[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Write one overlay per source that has stale anchors, and say what it found.

    ``wiki`` is the store, but only its read surface is used: accepted meanings (which carry
    freshness) and the current snapshot of each source. Nothing is written back.
    """
    accepted = wiki.accepted_meanings()
    pending = stale_spans(accepted["meanings"])
    report: dict[str, Any] = {
        "contract_version": CONTRACT, "method": METHOD, "dry_run": dry_run,
        "sources": 0, "moved": 0, "unmapped": 0, "overlays": [], "skipped": [], "details": [],
    }
    wanted = set(source_ids) if source_ids else None
    for (source_id, old_revision), spans in sorted(pending.items()):
        if wanted is not None and source_id not in wanted:
            continue
        try:
            snapshot = wiki.source_snapshot(source_id)
        except Exception:  # a source whose file is gone has nothing to relocate against
            report["skipped"].append({"source_id": source_id, "reason": "source_unavailable"})
            continue
        current_revision = str(snapshot.get("current_revision") or "")
        if not current_revision or current_revision == old_revision:
            report["skipped"].append({"source_id": source_id, "reason": "revision_unchanged"})
            continue
        moved, unmapped = map_spans(spans, str(snapshot.get("content") or ""))
        payload = {
            "contract_version": CONTRACT,
            "source_id": source_id,
            "old_revision": old_revision,
            "new_revision": current_revision,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "method": METHOD,
            "moved": moved,
            "unmapped": unmapped,
        }
        path = None if dry_run else _write_overlay(wiki.workspace, payload)
        report["sources"] += 1
        report["moved"] += len(moved)
        report["unmapped"] += len(unmapped)
        if path is not None:
            report["overlays"].append(str(path))
        report["details"].append({
            "source_id": source_id, "old_revision": old_revision[:12],
            "new_revision": current_revision[:12],
            "moved": len(moved), "unmapped": len(unmapped),
            "overlay": str(path) if path is not None else None,
        })
    return report


def load_overlays(workspace: Path | str) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Every stored overlay, keyed by (source, old revision, new revision)."""
    root = overlay_root(workspace)
    overlays: dict[tuple[str, str, str], dict[str, Any]] = {}
    if not root.is_dir():
        return overlays
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        key = (str(payload.get("source_id")), str(payload.get("old_revision")),
               str(payload.get("new_revision")))
        overlays[key] = payload
    return overlays


@dataclass
class RelocationResolver:
    """Answers "where is this stale citation now?" or nothing at all.

    Resolution is always against the *current* revision, so overlays never have to be chained:
    an anchor cited at an older revision is looked up in the overlay that leads straight from
    that revision to today's.
    """

    wiki: Any
    overlays: Mapping[tuple[str, str, str], Mapping[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.overlays is None:
            self.overlays = load_overlays(getattr(self.wiki, "workspace", ""))
        self._current: dict[str, str] = {}

    def current_revision(self, source_id: str) -> str:
        if source_id not in self._current:
            try:
                self._current[source_id] = str(self.wiki.source_snapshot(source_id).get("current_revision") or "")
            except Exception:
                self._current[source_id] = ""
        return self._current[source_id]

    def __call__(self, evidence: Mapping[str, Any]) -> dict[str, Any] | None:
        source_id = str(evidence.get("source_id") or "")
        old_revision = str(evidence.get("source_revision") or "")
        start = evidence.get("line_start")
        if not source_id or not old_revision or not isinstance(start, int):
            return None
        current_revision = self.current_revision(source_id)
        if not current_revision or current_revision == old_revision:
            return None
        overlay = (self.overlays or {}).get((source_id, old_revision, current_revision))
        if overlay is None:
            return None
        for row in overlay.get("moved") or []:
            if row.get("line_start") != start or row.get("span_sha256") != evidence.get("span_sha256"):
                continue
            end = evidence.get("line_end")
            shift = int(row["new_line_start"]) - start
            return {
                "target_revision": current_revision,
                "old_revision": old_revision,
                "old_line_start": start,
                "new_line_start": int(row["new_line_start"]),
                "new_line_end": (end if isinstance(end, int) else start) + shift,
                "confidence": str(row.get("confidence") or "exact"),
            }
        return None


def _aggregate(values: Sequence[str]) -> str:
    """The same rule the store uses: one stale anchor makes the meaning stale."""
    if not values:
        return "unknown"
    if set(values) == {"fresh"}:
        return "fresh"
    if any(value == "fresh" for value in values):
        return "partial"
    if any(value in {"stale", RELOCATED} for value in values):
        return "stale" if any(value == "stale" for value in values) else RELOCATED
    return "unknown"


def apply_relocations(meanings: Sequence[Mapping[str, Any]],
                      resolver: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None) -> list[dict[str, Any]]:
    """Return meanings whose *stale* citations now point at today's line, marked relocated.

    Only stale evidence is touched, only new dictionaries are produced, and the accepted
    version in the store is never mutated: this is a rendering view of the same knowledge.
    """
    if resolver is None:
        return [dict(row) for row in meanings]
    out: list[dict[str, Any]] = []
    for row in meanings:
        evidence_out = []
        for evidence in row.get("evidence") or []:
            item = dict(evidence)
            if item.get("freshness_status") == STALE:
                note = resolver(item)
                if note is not None:
                    item["freshness_status"] = RELOCATED
                    item["line_start"] = note["new_line_start"]
                    item["line_end"] = note["new_line_end"]
                    item["relocated_from_revision"] = note["old_revision"]
                    item["relocated_from_line"] = note["old_line_start"]
                    item["target_revision"] = note["target_revision"]
                    item["relocation_confidence"] = note["confidence"]
            evidence_out.append(item)
        entry = dict(row)
        entry["evidence"] = evidence_out
        entry["freshness_status"] = _aggregate([str(item.get("freshness_status") or "unknown")
                                                for item in evidence_out])
        out.append(entry)
    return out
