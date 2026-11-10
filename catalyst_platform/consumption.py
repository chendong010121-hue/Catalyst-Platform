"""The local ledger of what was asked of the active version and what answered.

A Run trace keeps only digests of the question and the answering meanings, because a
consumer question can carry anything a person typed. The ledger is the product's own
local record: plaintext question, the meanings that answered it, the version that was
active, and whether the answer was fresh. A question that matched nothing is a row too —
a miss is what tells an owner that an accepted version does not cover the work.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

LEDGER = Path(".catalyst") / "consumption.jsonl"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ledger_path(workspace) -> Path:
    return Path(workspace) / LEDGER


def record(workspace, *, query: str, result: dict, read_mode: str,
           actor_origin: str, run_id: str | None = None) -> dict:
    """Append one answered-or-unanswered question to the workspace ledger."""
    meanings = [
        {"meaning_id": row["meaning_id"], "kind": row.get("kind"), "meaning": row.get("meaning")}
        for row in result.get("meanings", [])
    ]
    row = {
        "recorded_at": int(time.time()),
        "run_id": run_id,
        "query": query,
        "query_sha256": _digest(query),
        "read_mode": read_mode,
        "actor_origin": actor_origin,
        "version_id": result.get("version_id"),
        "active_version_id": result.get("active_version_id"),
        "knowledge_status": result.get("knowledge_status"),
        "freshness_status": result.get("freshness_status"),
        "hit": bool(meanings),
        "meaning_ids": [meaning["meaning_id"] for meaning in meanings],
        "meanings": meanings,
    }
    path = ledger_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def rows(workspace, *, since: int | None = None) -> list[dict]:
    path = ledger_path(workspace)
    if not path.is_file():
        return []
    read = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if since is not None and row.get("recorded_at", 0) < since:
            continue
        read.append(row)
    return read


def summarize(workspace, *, since: int | None = None) -> dict:
    """Group the ledger by question: what answered it, which versions, and how fresh."""
    entries = rows(workspace, since=since)
    questions: dict[str, dict] = {}
    for row in entries:
        question = questions.setdefault(row["query"], {
            "query": row["query"],
            "reads": 0,
            "hits": 0,
            "misses": 0,
            "meaning_ids": [],
            "version_ids": [],
            "freshness_status": [],
        })
        question["reads"] += 1
        question["hits" if row.get("hit") else "misses"] += 1
        question["meaning_ids"] = sorted(set(question["meaning_ids"]) | set(row.get("meaning_ids", [])))
        if row.get("version_id"):
            question["version_ids"] = sorted(set(question["version_ids"]) | {row["version_id"]})
        if row.get("freshness_status"):
            question["freshness_status"] = sorted(
                set(question["freshness_status"]) | {row["freshness_status"]})
    ordered = [questions[key] for key in questions]
    return {
        "schema": "catalyst.consumption.v0.1",
        "workspace": str(Path(workspace).expanduser()),
        "ledger": str(ledger_path(workspace)),
        "reads": len(entries),
        "hit_reads": sum(1 for row in entries if row.get("hit")),
        "miss_reads": sum(1 for row in entries if not row.get("hit")),
        "asked_meaning_ids": sorted({meaning_id for row in entries for meaning_id in row.get("meaning_ids", [])}),
        "questions": ordered,
        "entries": entries,
    }
