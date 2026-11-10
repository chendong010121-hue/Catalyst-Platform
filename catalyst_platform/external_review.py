"""Hand the material and the candidate to a reviewer that has no history with either.

An independent review is worth as much as the independence of its context. This module
packages the original source bytes and the exact candidate meanings with the locators
they were taken from, so a reviewer on another provider — no history, no house model, no
sight of the extraction — can judge what the evidence says. The answer comes back as a
file; what is signed afterwards binds the package that went out and the answer that came
back, so a receipt can be checked against both.

The signature is local custody, not the reviewer's: a chat model cannot hold a secret. The
receipt therefore says which package and which answer it covers, and names the evaluator;
it does not pretend the signature proves who wrote the answer.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .semantic_wiki import SemanticTransitionError, _candidate_content_digest, _digest

SCHEMA = "catalyst.review_package.v0.1"
PACKAGE_FILE = "package.json"
RUBRIC = "name-in-evidence; meaning-restates-source; evidence-is-enough"
VERDICTS = {"REVIEWABLE": "ACCEPT", "REVISE": "REVISE", "REJECT": "REJECT"}

INSTRUCTIONS = (
    "You are reviewing one candidate enterprise-ontology reading against the material it was "
    "taken from. You have not seen how it was produced and you cannot change it. For every "
    "meaning, ask only: do the quoted lines support this meaning, is every name in it present "
    "in its evidence, and does the evidence say enough for the claim. Report one finding per "
    "item that fails, with the item_key and the evidence_id you looked at. Missing material is "
    "UNKNOWN, not a reason to invent. Reply with one JSON object and nothing else: "
    '{"verdict": "REVIEWABLE" | "REVISE" | "REJECT", "findings": [{"id": "f1", '
    '"severity": "hard_stop" | "major" | "minor", "item_keys": ["..."], '
    '"evidence_refs": ["..."], "reason": "..."}]}'
)


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _source_rows(wiki, candidate) -> list[dict]:
    snapshot = wiki.source_snapshot(candidate["source_id"])
    if snapshot["current_revision"] != candidate["source_revision"]:
        raise SemanticTransitionError(
            "source_revision_changed",
            "the material changed after this candidate was proposed; propose it again before reviewing")
    relative = snapshot["source"]["relative_path"]
    content = snapshot["content"]
    return [{
        "relative_path": relative,
        "source_revision": candidate["source_revision"],
        "bundle_file": f"sources/{relative}",
        "bundle_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
    }]


def _item_rows(candidate, source_row) -> list[dict]:
    lines = source_row["content"].splitlines()
    rows = []
    for entry in candidate.get("entries", []):
        start = entry.get("line_start")
        end = entry.get("line_end") or start
        quote = None
        if type(start) is int and type(end) is int and 1 <= start <= end <= len(lines):
            quote = "\n".join(lines[start - 1:end])
        rows.append({
            "item_key": entry.get("key") or entry.get("meaning_id"),
            "meaning_id": entry.get("meaning_id"),
            "kind": entry.get("kind"),
            "meaning": entry.get("meaning"),
            "evidence": [{
                "source_id": entry.get("source_id"),
                "line_start": start,
                "line_end": end,
                "span_sha256": entry.get("span_sha256"),
                "quote": quote,
            }],
        })
    return rows


def write_package(wiki, candidate_id: str, out_dir, *, question: str | None = None) -> dict:
    """Write the package a reviewer on another provider can read, and return its digest."""
    out = Path(out_dir).expanduser()
    state = wiki.semantic_state()
    candidate = state["candidates"].get(candidate_id)
    if candidate is None:
        raise SemanticTransitionError("candidate_not_found", f"no candidate {candidate_id!r} in this scope")
    sources = _source_rows(wiki, candidate)
    package = {
        "schema": SCHEMA,
        "created_at": int(time.time()),
        "scope_id": wiki.scope_id,
        "candidate_id": candidate_id,
        "candidate_sha256": _candidate_content_digest(candidate),
        "source_id": candidate["source_id"],
        "source_revision": candidate["source_revision"],
        "question": question or "Does every meaning hold against the material it was taken from?",
        "rubric": RUBRIC,
        "instructions": INSTRUCTIONS,
        "sources": [{key: value for key, value in row.items() if key != "content"} for row in sources],
        "items": _item_rows(candidate, sources[0]),
    }
    package["package_sha256"] = _digest(_canonical(package))
    (out / "sources").mkdir(parents=True, exist_ok=True)
    for row in sources:
        target = out / row["bundle_file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(row["content"], encoding="utf-8", newline="")
    (out / PACKAGE_FILE).write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return package


def load_package(package_dir) -> dict:
    """Read a package back and check it was not edited after it was written."""
    path = Path(package_dir).expanduser()
    if not path.is_dir():
        raise SemanticTransitionError("review_package_missing", f"{str(path)!r} is not a review package")
    raw = path / PACKAGE_FILE
    if not raw.is_file():
        raise SemanticTransitionError("review_package_missing", f"{str(raw)!r} does not exist")
    try:
        package = json.loads(raw.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticTransitionError("review_package_invalid", "the review package is not valid JSON") from exc
    if not isinstance(package, dict) or package.get("schema") != SCHEMA:
        raise SemanticTransitionError("review_package_invalid", "the review package has an unknown schema")
    recorded = package.get("package_sha256")
    unsigned = {key: value for key, value in package.items() if key != "package_sha256"}
    if not isinstance(recorded, str) or _digest(_canonical(unsigned)) != recorded:
        raise SemanticTransitionError("review_package_tampered", "the review package changed after it was written")
    for row in package.get("sources", []):
        bundled = path / row["bundle_file"]
        if not bundled.is_file() or _digest(bundled.read_bytes()) != row["bundle_sha256"]:
            raise SemanticTransitionError("review_package_source_changed",
                                          "a bundled source no longer matches the package")
    return package


def read_response(path) -> tuple[dict, str]:
    """The reviewer's answer, and the digest of the exact bytes that carry it."""
    target = Path(path).expanduser()
    if not target.is_file():
        raise SemanticTransitionError("review_response_missing", f"{str(target)!r} does not exist")
    raw = target.read_bytes()
    try:
        response = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticTransitionError("review_response_invalid", "the review answer is not valid JSON") from exc
    if not isinstance(response, dict) or response.get("verdict") not in VERDICTS:
        raise SemanticTransitionError("review_response_invalid",
                                      f"the review answer needs a verdict in {sorted(VERDICTS)}")
    findings = response.get("findings", [])
    if not isinstance(findings, list) or any(not isinstance(row, dict) for row in findings):
        raise SemanticTransitionError("review_response_invalid", "findings must be a list of objects")
    return response, hashlib.sha256(raw).hexdigest()
