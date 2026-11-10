"""What a reviewer may read besides the daily scope, and what a review may record.

Three things live here, all of them read-mostly and all of them explicit:

* which knowledge scopes this workspace may open, and which of them are read-only;
* a declared run product -- the full modelling candidate one controlled run produced --
  projected for reading, never imported into the daily scope;
* a review disposition ledger: accept / defer / reject with a reason, under a digest the
  reader saw, and a withdrawal that supersedes instead of editing.

Nothing here writes to a Wiki. A disposition is a record of a review, not an acceptance:
the Wiki's own decision path stays the only way a version is created, and it is not
reachable through a read-only scope.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .wiki import ProjectWiki, WikiScopeError

SCOPE_ID = re.compile(r"enterprise:([A-Za-z0-9_-]{1,80})/project:([A-Za-z0-9_-]{1,80})")
SIMPLE_ID = re.compile(r"[A-Za-z0-9_-]{1,80}")
FILE_NAME = re.compile(r"[A-Za-z0-9._-]{1,120}")
DISPOSITION_ACTIONS = ("ACCEPTED", "DEFERRED", "REJECTED", "WITHDRAWN")
DISPOSITION_AUTHORITY = "REVIEW_DISPOSITION_ONLY"
# A rule says why a row did not enter the candidate; it does not say why the evidence is what it
# is. The old one-line translation turned every `evidence_unresolved` row into "the locator could
# not be found", which is one possible cause among several (a duty with no reference, a claim the
# reader itself marked unresolved while its quote sits right there). The rows therefore carry the
# rule and the reference ladder as separate facts, and the page states only those.
RULE_LABELS = {
    "evidence_unresolved": "证据未解决",
    "absence_without_scope": "缺失断言没有指明范围",
}


class ReadingError(ValueError):
    """A scope or a product the workspace may not open, or a review it may not record."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        with open(path, "rb") as stream:
            return json.loads(stream.read().decode("utf-8"))
    except OSError as exc:
        raise ReadingError("declaration_unreadable", f"读不到声明文件：{path.name}", 409) from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReadingError("declaration_invalid", f"声明文件不是合法 JSON：{path.name}", 409) from exc


def _declaration(workspace: Path, name: str) -> Any | None:
    path = Path(workspace) / ".catalyst" / name
    return _read_json(path) if path.is_file() else None


def parse_scope(scope_id: str) -> tuple[str, str]:
    match = SCOPE_ID.fullmatch(scope_id or "")
    if not match:
        raise ReadingError("scope_invalid", "知识范围标识不合法。")
    return match.group(1), match.group(2)


# --------------------------------------------------------------------------- scopes

def registered_scopes(workspace: Path | str, daily_scope: str) -> dict[str, Any]:
    """The daily scope plus every scope the workspace declares, with its store state.

    A declaration names a scope that must already have a store inside this workspace:
    declaring a scope does not create one, and copying another scope's store here would
    not make it this scope -- `ProjectWiki` checks the scope inside the document.
    """
    workspace = Path(workspace)
    rows = [{"scope_id": daily_scope, "label": "日常知识范围", "read_only": False,
             "role": "daily"}]
    declared = _declaration(workspace, "scopes.json")
    if declared is not None:
        items = declared.get("scopes") if isinstance(declared, dict) else None
        if not isinstance(items, list):
            raise ReadingError("declaration_invalid", "scopes.json 需要 {scopes: [...]}。", 409)
        for item in items:
            if not isinstance(item, dict) or set(item) - {"scope_id", "label", "read_only"}:
                raise ReadingError("declaration_invalid", "scopes.json 里有一条声明字段不合法。", 409)
            scope_id = item.get("scope_id")
            enterprise_id, project_id = parse_scope(scope_id)
            if scope_id == daily_scope:
                raise ReadingError("declaration_invalid", "日常范围不能重复声明。", 409)
            label = item.get("label", scope_id)
            if not isinstance(label, str) or not 1 <= len(label) <= 80:
                raise ReadingError("declaration_invalid", "范围标签需要 1..80 个字符。", 409)
            rows.append({"scope_id": scope_id, "label": label,
                         "read_only": bool(item.get("read_only", True)), "role": "declared"})
    for row in rows:
        enterprise_id, project_id = parse_scope(row["scope_id"])
        store = workspace / ".catalyst" / "wiki" / enterprise_id / project_id / "wiki.json"
        row["has_store"] = store.is_file()
        row["store_bytes"] = store.stat().st_size if store.is_file() else 0
    return {"daily": daily_scope, "scopes": rows}


def open_scope(workspace: Path | str, roots: Iterable[Path | str], scope_id: str,
               *, backend: str = "json", read_only: bool) -> ProjectWiki:
    workspace = Path(workspace)
    enterprise_id, project_id = parse_scope(scope_id)
    if read_only:
        store = workspace / ".catalyst" / "wiki" / enterprise_id / project_id / "wiki.json"
        if not store.is_file():
            raise ReadingError("scope_has_no_store",
                               "这个知识范围在本工作区还没有存储；声明不会创建存储。", 404)
    try:
        return ProjectWiki(workspace, list(roots), enterprise_id=enterprise_id,
                           project_id=project_id, backend=backend)
    except WikiScopeError as exc:
        raise ReadingError("scope_invalid", str(exc)) from exc


# --------------------------------------------------------------------- run products

def declared_products(workspace: Path | str) -> list[dict[str, Any]]:
    """Products this workspace declares, validated but not read yet."""
    declared = _declaration(Path(workspace), "run-products.json")
    if declared is None:
        return []
    items = declared.get("products") if isinstance(declared, dict) else None
    if not isinstance(items, list):
        raise ReadingError("declaration_invalid", "run-products.json 需要 {products: [...]}。", 409)
    rows = []
    for item in items:
        if not isinstance(item, dict):
            raise ReadingError("declaration_invalid", "run-products.json 里有一条不是对象。", 409)
        allowed = {"product_id", "label", "root", "scope_id", "candidate_id", "files", "note"}
        if set(item) - allowed:
            raise ReadingError("declaration_invalid", "运行产物声明含未知字段。", 409)
        product_id = item.get("product_id")
        if not isinstance(product_id, str) or not SIMPLE_ID.fullmatch(product_id):
            raise ReadingError("declaration_invalid", "运行产物标识不合法。", 409)
        label = item.get("label", product_id)
        if not isinstance(label, str) or not 1 <= len(label) <= 80:
            raise ReadingError("declaration_invalid", "运行产物标签需要 1..80 个字符。", 409)
        root = Path(str(item.get("root") or ""))
        if not root.is_dir():
            raise ReadingError("product_root_missing", f"运行产物目录不存在：{label}", 409)
        parse_scope(item.get("scope_id"))
        candidate_id = item.get("candidate_id")
        if not isinstance(candidate_id, str) or not re.fullmatch(r"(?:candidate|understand)_[a-f0-9]{24,64}", candidate_id):
            raise ReadingError("declaration_invalid", "运行产物必须指明它属于哪个候选。", 409)
        files = item.get("files") or {}
        if not isinstance(files, dict) or not files or set(files) - {"dropped", "receipt", "typed", "binding"}:
            raise ReadingError("declaration_invalid", "运行产物文件声明不合法。", 409)
        checked = {}
        for role, name in files.items():
            if not isinstance(name, str) or not FILE_NAME.fullmatch(name):
                raise ReadingError("declaration_invalid", "运行产物文件名不合法。", 409)
            path = (root / name).resolve()
            if path.parent != root.resolve():
                raise ReadingError("declaration_invalid", "运行产物文件越出它的目录。", 409)
            if not path.is_file():
                raise ReadingError("product_file_missing", f"运行产物缺少 {name}。", 409)
            checked[role] = {"name": name, "sha256": _sha(path.read_bytes()),
                             "bytes": path.stat().st_size}
        rows.append({"product_id": product_id, "label": label, "root": str(root),
                     "scope_id": item.get("scope_id"), "candidate_id": candidate_id,
                     "note": item.get("note"), "files": checked})
    return rows


def _evidence_ladder(item: Mapping[str, Any], index: Mapping[str, Any]) -> dict[str, Any]:
    """What is actually known about one row's references, one fact per rung.

    record exists -> a quote is recorded -> a location is recorded -> the original can be read.
    Only the first three are answered here: the run records the original's path but not its
    bytes, and this workspace cannot open them, so the last rung says so instead of guessing.
    """
    declared = [ref for ref in (item.get("evidence_refs") or []) if isinstance(ref, str)]
    present = [index.get(ref) for ref in declared]
    found = [row for row in present if isinstance(row, Mapping)]
    return {
        "declared": len(declared),
        "present": len(found),
        "missing": [ref for ref, row in zip(declared, present) if not isinstance(row, Mapping)],
        "with_quote": sum(1 for row in found if str(row.get("quote") or "").strip()),
        "evidence_classes": sorted({str(row.get("evidence_class")) for row in found
                                    if row.get("evidence_class")}),
        "locators": sorted({str(row.get("locator")) for row in found if row.get("locator")})[:8],
        "originals": sorted({str(row.get("relative_path")) for row in found
                             if row.get("relative_path")})[:8],
        "original_readable": False,
        "original_note": "原件不在本工作区可读范围内；这里只给运行记录里的引用与原句。",
    }


def _row_text(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "item_id": item.get("item_id"),
        "kind": item.get("kind"),
        "key": item.get("key"),
        "meaning": (item.get("meaning") or "")[:600],
        "heading": item.get("heading"),
        "line_start": item.get("line_start"),
        "line_end": item.get("line_end"),
        "evidence_class": item.get("evidence_class"),
    }


def product_rows(product: Mapping[str, Any], understanding_result: Mapping[str, Any]) -> dict[str, Any]:
    """The whole modelling candidate, one row per item, with what happened to each.

    The rows are the candidate's own reading. Which of them the hand-off delivered is
    recorded by the run, so it is read from the product instead of being re-derived by
    matching text: a text join between 380 rows and 296 entries left 31 relations
    unmatched, and silently calling those "dropped" would be a wrong count under a
    confident label.
    """
    root = Path(product["root"])
    dropped_path = root / product["files"]["dropped"]["name"]
    dropped_doc = _read_json(dropped_path)
    if not isinstance(dropped_doc, list):
        raise ReadingError("product_invalid", "未收获清单不是一张表。", 409)
    dropped = {}
    for row in dropped_doc:
        if not isinstance(row, dict) or not isinstance(row.get("item_key"), str):
            raise ReadingError("product_invalid", "未收获清单里有一行缺少条目标识。", 409)
        rule = row.get("rule") or "unspecified"
        dropped[row["item_key"]] = rule

    evidence_index: dict[str, Any] = {}
    for ref in understanding_result.get("evidence_refs") or []:
        if isinstance(ref, Mapping) and isinstance(ref.get("evidence_id"), str):
            evidence_index[ref["evidence_id"]] = ref

    rows: list[dict[str, Any]] = []
    for bucket in ("extracted_facts", "inferred_items", "unknowns"):
        for item in understanding_result.get(bucket) or []:
            if not isinstance(item, dict):
                continue
            row = _row_text(item)
            rule = dropped.get(item.get("item_id") or "")
            row["bucket"] = bucket
            row["status"] = "dropped" if rule else "carried"
            row["rule"] = rule
            row["rule_label"] = RULE_LABELS.get(rule, rule) if rule else None
            # Kept as a phrase, never as a diagnosis: what happened to the row, in the run's words.
            row["reason"] = f"{row['rule_label']}（{rule}）" if rule else None
            row["evidence"] = _evidence_ladder(item, evidence_index) if rule else None
            row["digest"] = item_digest(digest_source(row, item))
            rows.append(row)

    seen = {row["item_id"] for row in rows}
    unaccounted = [key for key in dropped if key not in seen]
    carried = sum(1 for row in rows if row["status"] == "carried")
    by_kind: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    ladder: dict[str, int] = {"with_quote": 0, "without_quote": 0, "records_missing": 0}
    for row in rows:
        by_kind[row["kind"] or "unknown"] = by_kind.get(row["kind"] or "unknown", 0) + 1
        if row["rule"]:
            by_rule[row["rule"]] = by_rule.get(row["rule"], 0) + 1
            evidence = row.get("evidence") or {}
            if evidence.get("missing"):
                ladder["records_missing"] += 1
            elif evidence.get("with_quote"):
                ladder["with_quote"] += 1
            else:
                ladder["without_quote"] += 1

    receipt = None
    if "receipt" in product["files"]:
        receipt = _read_json(root / product["files"]["receipt"]["name"])
    return {
        "product_id": product["product_id"], "label": product["label"],
        "root": product["root"], "scope_id": product["scope_id"],
        "candidate_id": product["candidate_id"], "note": product["note"],
        "files": product["files"],
        "counts": {
            "rows": len(rows), "carried": carried, "dropped": len(rows) - carried,
            "dropped_declared": len(dropped), "dropped_unaccounted": len(unaccounted),
            "by_kind": by_kind, "by_rule": by_rule, "dropped_ladder": ladder,
            "receipt_item_count": (receipt or {}).get("item_count"),
        },
        "unaccounted": unaccounted,
        "receipt": receipt,
        "rows": rows,
    }


# --------------------------------------------------------------------- dispositions

class ReviewDispositions:
    """An append-only review ledger, bound to the candidate content a reader saw.

    It cannot accept knowledge. It records what a person decided about a candidate,
    under the digest of that candidate, so a later change shows up as a stale binding
    instead of an approval that silently follows the content.
    """

    def __init__(self, workspace: Path | str) -> None:
        self.path = Path(workspace) / ".catalyst" / "review-dispositions.jsonl"

    def records(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows = []
        with open(self.path, "rb") as stream:
            for index, line in enumerate(stream.read().decode("utf-8").splitlines()):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ReadingError("disposition_unreadable",
                                       f"处置记录第 {index + 1} 行无法解析。", 409) from exc
                if isinstance(row, dict):
                    rows.append(row)
        return rows

    def view(self, *, scope_id: str | None = None, candidate_id: str | None = None) -> dict[str, Any]:
        rows = self.records()
        if scope_id:
            rows = [row for row in rows if row.get("scope_id") == scope_id]
        if candidate_id:
            rows = [row for row in rows if row.get("candidate_id") == candidate_id]
        withdrawn = {row.get("supersedes") for row in rows if row.get("action") == "WITHDRAWN"}
        effective = {}
        for row in rows:
            if row.get("action") == "WITHDRAWN":
                continue
            if row.get("record_id") in withdrawn:
                continue
            effective[row.get("candidate_id")] = row
        return {"items": rows[-200:], "total": len(rows),
                "effective": list(effective.values()),
                "authority": DISPOSITION_AUTHORITY,
                "note": "处置记录只表示审阅意见，不是 Wiki 准入；它不创建版本，也不改变知识范围。"}

    def record(self, *, scope_id: str, candidate_id: str, content_digest: str,
               action: str, reason: str, source_revision: str | None = None) -> dict[str, Any]:
        if action not in DISPOSITION_ACTIONS:
            raise ReadingError("disposition_action_invalid", "处置动作必须是接受、延后、拒绝或撤回。")
        if not isinstance(content_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", content_digest):
            raise ReadingError("disposition_digest_invalid", "处置必须绑定候选内容摘要。")
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 2000:
            raise ReadingError("disposition_reason_required", "处置需要 1..2000 字的理由。")
        parse_scope(scope_id)
        if not isinstance(candidate_id, str) or not re.fullmatch(r"(?:candidate|understand)_[a-f0-9]{24,64}", candidate_id):
            raise ReadingError("disposition_candidate_invalid", "候选标识不合法。")
        payload = {"scope_id": scope_id, "candidate_id": candidate_id,
                   "content_digest": content_digest, "action": action,
                   "reason": reason.strip(), "source_revision": source_revision}
        record_id = "disposition_" + _sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))[:24]
        existing = {row.get("record_id") for row in self.records()}
        if record_id in existing:
            return {"record_id": record_id, "duplicate": True,
                    "receipt": {"record_id": record_id, "candidate_id": candidate_id,
                                "candidate_sha256": content_digest, "action": action}}
        line = {"record_id": record_id, "at": _now(), "authority": DISPOSITION_AUTHORITY,
                "actor": "local-workspace-review", **payload}
        body = (json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        return {"record_id": record_id, "duplicate": False,
                "receipt": {"record_id": record_id, "candidate_id": candidate_id,
                            "candidate_sha256": content_digest, "action": action,
                            "reason": reason.strip(), "scope_id": scope_id,
                            "recorded_at": line["at"], "authority": DISPOSITION_AUTHORITY,
                            "line_sha256": _sha(body)}}

    def withdraw(self, *, record_id: str, reason: str) -> dict[str, Any]:
        rows = self.records()
        target = next((row for row in rows if row.get("record_id") == record_id), None)
        if target is None:
            raise ReadingError("disposition_unknown", "要撤回的处置记录不存在。", 404)
        if target.get("action") == "WITHDRAWN":
            raise ReadingError("disposition_already_withdrawn", "这条记录已经是撤回记录。")
        if any(row.get("action") == "WITHDRAWN" and row.get("supersedes") == record_id for row in rows):
            raise ReadingError("disposition_already_withdrawn", "这条处置已经被撤回。")
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 2000:
            raise ReadingError("disposition_reason_required", "撤回需要 1..2000 字的理由。")
        payload = {"scope_id": target["scope_id"], "candidate_id": target["candidate_id"],
                   "content_digest": target["content_digest"], "action": "WITHDRAWN",
                   "reason": reason.strip(), "supersedes": record_id}
        record_id_new = "withdrawal_" + _sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))[:24]
        line = {"record_id": record_id_new, "at": _now(), "authority": DISPOSITION_AUTHORITY,
                "actor": "local-workspace-review", **payload}
        body = (json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        return {"record_id": record_id_new, "supersedes": record_id,
                "receipt": {"record_id": record_id_new, "candidate_id": target["candidate_id"],
                            "candidate_sha256": target["content_digest"], "action": "WITHDRAWN",
                            "reason": reason.strip(), "scope_id": target["scope_id"],
                            "recorded_at": line["at"], "authority": DISPOSITION_AUTHORITY,
                            "line_sha256": _sha(body)}}


# --------------------------------------------------------------------- item opinions
OPINION_STANCES = ("agree", "question", "reject")
OPINION_LABELS = {"agree": "同意", "question": "存疑", "reject": "驳回"}
OPINION_AUTHORITY = "REVIEW_ITEM_OPINION_ONLY"


ITEM_DIGEST_RULE = "item.v2"
# Everything a reviewer can be judging when they leave an opinion. v1 covered only what a row
# displays, so moving a duty to another holder or changing its qualification left the digest
# unchanged and an old opinion kept covering content nobody had looked at.
_ITEM_DIGEST_FIELDS = (
    "item_id", "kind", "key", "meaning", "heading", "line_start", "line_end", "evidence_class",
    "qualification", "qualification_basis", "verification", "scope_state",
    "holder", "from", "to", "applies_to", "predicate", "rule", "status",
    # The roles a hand-off item was read in. Without these a subject could be swapped and the
    # digest - and the opinion bound to it - would not move.
    "subject", "object",
)


def _canonical_links(value: Any) -> list[Any]:
    """Evidence links in a stable order, flattened to what they assert."""
    rows: list[Any] = []
    for entry in value or []:
        if isinstance(entry, Mapping):
            rows.append({key: entry[key] for key in sorted(entry)
                         if isinstance(entry[key], (str, int, float, bool)) or entry[key] is None})
        elif isinstance(entry, (str, int, float, bool)):
            rows.append(entry)
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))


def item_digest(row: Mapping[str, Any]) -> str:
    """What one item's opinion is bound to: the item and the evidence behind it, not its text."""
    payload = {field: row.get(field) for field in _ITEM_DIGEST_FIELDS}
    # An explicit (even empty) reference list is the item's own evidence; the display ladder is
    # a derived summary and is not what the opinion was given.
    links = row["evidence_refs"] if "evidence_refs" in row else row.get("evidence")
    payload["evidence_links"] = _canonical_links(links)
    return _sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def digest_source(row: Mapping[str, Any], item: Mapping[str, Any]) -> Mapping[str, Any]:
    """The display row plus the judged fields it does not repeat, and the item's own refs.

    ``_row_text`` keeps only what the page shows: seven fields. The fields a reviewer judges -
    the saved holder, the qualification, the roles an item was read in - live on the hand-off
    item, so a row built from the display fields alone would produce the same digest after any
    of them changed. This merges them in without widening what the page displays.
    """
    merged = dict(row)
    for field in _ITEM_DIGEST_FIELDS:
        if field not in merged and item.get(field) is not None:
            merged[field] = item[field]
    merged["evidence_refs"] = list(item.get("evidence_refs") or [])
    return merged


class ReviewItemOpinions:
    """The same append-only rules as a disposition, one item at a time.

    A separate file and a separate identity on purpose: an opinion about one duty is not a
    decision about the candidate, and the coverage counts have to be able to say "left an
    opinion" without that reading as "reviewed". Nothing here creates a version, activates
    one, or touches a qualification; an item whose content changed under its opinion shows
    up as stale instead of carrying the old opinion forward.
    """

    def __init__(self, workspace: Path | str) -> None:
        self.path = Path(workspace) / ".catalyst" / "review-item-opinions.jsonl"

    def records(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows = []
        with open(self.path, "rb") as stream:
            for index, line in enumerate(stream.read().decode("utf-8").splitlines()):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ReadingError("opinion_unreadable",
                                       f"逐条意见第 {index + 1} 行无法解析。", 409) from exc
                if isinstance(row, dict):
                    rows.append(row)
        return rows

    def _effective(self, *, scope_id: str | None = None,
                   candidate_id: str | None = None) -> dict[tuple[str, str], dict[str, Any]]:
        rows = self.records()
        if scope_id:
            rows = [row for row in rows if row.get("scope_id") == scope_id]
        if candidate_id:
            rows = [row for row in rows if row.get("candidate_id") == candidate_id]
        withdrawn = {row.get("supersedes") for row in rows if row.get("action") == "WITHDRAWN"}
        effective: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            if row.get("action") == "WITHDRAWN" or row.get("record_id") in withdrawn:
                continue
            effective[(str(row.get("candidate_id")), str(row.get("item_id")))] = row
        return effective

    def view(self, *, scope_id: str | None = None,
             candidate_id: str | None = None) -> dict[str, Any]:
        rows = self.records()
        if scope_id:
            rows = [row for row in rows if row.get("scope_id") == scope_id]
        if candidate_id:
            rows = [row for row in rows if row.get("candidate_id") == candidate_id]
        return {"items": rows[-200:], "total": len(rows),
                "effective": list(self._effective(scope_id=scope_id,
                                                  candidate_id=candidate_id).values()),
                "stances": dict(OPINION_LABELS),
                "authority": OPINION_AUTHORITY,
                "note": "逐条意见只记录审阅看法，不是 Wiki 准入；它不创建版本，也不改变条目资格。"}

    def coverage(self, *, candidate_id: str, rows: Sequence[Mapping[str, Any]],
                 scope_id: str | None = None) -> dict[str, Any]:
        """Three counts a reviewer needs apart: left an opinion, still questioned, not covered."""
        effective = self._effective(scope_id=scope_id, candidate_id=candidate_id)
        left = questioned = rejected = stale = legacy = 0
        for row in rows:
            record = effective.get((candidate_id, str(row.get("item_id"))))
            if record is None:
                continue
            if record.get("digest_rule") != ITEM_DIGEST_RULE:
                # An opinion saved under an older rule does not cover today's content, and it
                # is not re-signed under the new rule: it has to be read again.
                legacy += 1
                continue
            if record.get("content_digest") != row.get("digest"):
                stale += 1  # the item changed after the opinion: the opinion does not follow it
                continue
            left += 1
            if record.get("stance") == "question":
                questioned += 1
            elif record.get("stance") == "reject":
                rejected += 1
        return {"items": len(rows), "with_opinion": left, "still_question": questioned,
                "rejected": rejected, "stale": stale, "legacy": legacy,
                "uncovered": len(rows) - left, "digest_rule": ITEM_DIGEST_RULE,
                "note": "留过意见不等于审完；整体接受也不代表没有留意见的条目被审过。"
                        "旧规则下的意见需要重新核对，不会自动套到新内容上。"}

    def record(self, *, scope_id: str, candidate_id: str, item_id: str, content_digest: str,
               stance: str, reason: str) -> dict[str, Any]:
        if stance not in OPINION_STANCES:
            raise ReadingError("opinion_stance_invalid", "逐条意见只能是同意、存疑或驳回。")
        if not isinstance(content_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", content_digest):
            raise ReadingError("opinion_digest_invalid", "逐条意见必须绑定条目内容摘要。")
        if not isinstance(item_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", item_id):
            raise ReadingError("opinion_item_invalid", "条目标识不合法。")
        if not isinstance(candidate_id, str) or not re.fullmatch(
                r"(?:candidate|understand)_[a-f0-9]{24,64}", candidate_id):
            raise ReadingError("opinion_candidate_invalid", "候选标识不合法。")
        parse_scope(scope_id)
        text = (reason or "").strip()
        if not 1 <= len(text) <= 2000:
            raise ReadingError("opinion_reason_required", "逐条意见需要 1..2000 字的理由。")
        payload = {"scope_id": scope_id, "candidate_id": candidate_id, "item_id": item_id,
                   "content_digest": content_digest, "digest_rule": ITEM_DIGEST_RULE,
                   "stance": stance, "reason": text}
        record_id = "opinion_" + _sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))[:24]
        if any(row.get("record_id") == record_id for row in self.records()):
            return {"record_id": record_id, "duplicate": True,
                    "receipt": {"record_id": record_id, "candidate_id": candidate_id,
                                "item_id": item_id, "stance": stance}}
        line = {"record_id": record_id, "at": _now(), "authority": OPINION_AUTHORITY,
                "actor": "local-workspace-review", **payload}
        body = (json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        return {"record_id": record_id, "duplicate": False,
                "receipt": {"record_id": record_id, "candidate_id": candidate_id,
                            "item_id": item_id, "content_digest": content_digest,
                            "stance": stance, "reason": text, "scope_id": scope_id,
                            "recorded_at": line["at"], "authority": OPINION_AUTHORITY,
                            "line_sha256": _sha(body)}}

    def withdraw(self, *, record_id: str, reason: str) -> dict[str, Any]:
        rows = self.records()
        target = next((row for row in rows if row.get("record_id") == record_id), None)
        if target is None:
            raise ReadingError("opinion_unknown", "要撤回的逐条意见不存在。", 404)
        if target.get("action") == "WITHDRAWN":
            raise ReadingError("opinion_already_withdrawn", "这条记录已经是撤回记录。")
        if any(row.get("action") == "WITHDRAWN" and row.get("supersedes") == record_id for row in rows):
            raise ReadingError("opinion_already_withdrawn", "这条意见已经被撤回。")
        text = (reason or "").strip()
        if not 1 <= len(text) <= 2000:
            raise ReadingError("opinion_reason_required", "撤回需要 1..2000 字的理由。")
        payload = {"scope_id": target["scope_id"], "candidate_id": target["candidate_id"],
                   "item_id": target["item_id"], "content_digest": target["content_digest"],
                   "action": "WITHDRAWN", "reason": text, "supersedes": record_id}
        record_id_new = "opinion_withdrawal_" + _sha(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))[:24]
        line = {"record_id": record_id_new, "at": _now(), "authority": OPINION_AUTHORITY,
                "actor": "local-workspace-review", **payload}
        body = (json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        return {"record_id": record_id_new, "supersedes": record_id,
                "receipt": {"record_id": record_id_new, "item_id": target["item_id"],
                            "candidate_id": target["candidate_id"], "action": "WITHDRAWN",
                            "reason": text, "recorded_at": line["at"],
                            "authority": OPINION_AUTHORITY, "line_sha256": _sha(body)}}
