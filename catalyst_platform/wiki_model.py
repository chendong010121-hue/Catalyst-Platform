"""The Workspace Wiki read model: the pages, the links, and the evidence behind every page.

One pure projection over a :class:`ProjectWiki` and its source roots. Nothing here calls a
model, writes to the store, or materializes a page tree: the Workspace renders this dict and
stops. The same store must produce the same model, so the only field that is not derived from
the store is ``meta.read_at``.

What the model adds over the page set alone is the reader's side of the projection:

* every ``## 证据`` line is taken out of the page body and turned into an evidence record, so
  the drawer can open the line the page cites instead of trusting the label;
* a derived proposal's line is a JSON record - the source it actually quotes is read out of it
  as the second hop, because "the store cites a proposal" is not the same claim as "the
  document says this";
* the store's own report is carried along (verify, links, source presence, how much evidence
  the pages cannot carry), because a page that opens is not the same as a copy that holds.
"""
from __future__ import annotations

import hashlib
import html
import json
import re

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .object_view import collect
from .wiki_pages import Page, project

KIND_LABEL = {"entity": "实体", "concept": "概念", "source": "来源", "version": "版本",
              "gaps": "缺口", "overview": "概览", "index": "索引", "log": "操作记录"}
KIND_ORDER = ["overview", "index", "gaps", "log", "entity", "concept", "source", "version"]
MEANING_LABEL = {"entity": "实体", "claim": "断言", "relation": "关系", "alias": "别名",
                 "unknown": "缺失断言", "condition": "条件", "exception": "例外"}
# Where the Wiki line writes one derived proposal beside every document it reads.
DERIVED_SOURCE_DIR = ".catalyst-proposals"
# A cited line can be a whole slide of text; the drawer shows the beginning and says how much.
SNIPPET_LIMIT = 4000

_EVIDENCE_LINE = re.compile(r"^- `(?P<source>[^`]+)` @ `(?P<locator>[^`]+)` \((?P<rest>.+)\)$")
_LINE_SPAN = re.compile(r"^line:(\d+)(?:-(\d+))?$")
_QUOTE = re.compile(r'"quote"\s*:\s*"(?P<quote>(?:[^"\\]|\\.)*)"')
_RAW_PATH = re.compile(r'"relative_path"\s*:\s*"(?P<path>(?:[^"\\]|\\.)*)"')
_LOCATOR = re.compile(r'"locator"\s*:\s*"(?P<locator>(?:[^"\\]|\\.)*)"')


# --------------------------------------------------------------------------- page body
def _wikilink(raw: str, pages_by_title: Mapping[str, str]) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0].strip()
    label = html.escape(raw.split("|")[-1] if "|" in raw else target)
    path = pages_by_title.get(target)
    if path is None:
        return f'<span class="dead" title="没有页叫这个名字">{label}</span>'
    return f'<a class="wikilink" href="#" data-page="{html.escape(path)}">{label}</a>'


def _inline(text: str, pages_by_title: Mapping[str, str]) -> str:
    out = html.escape(text)
    out = re.sub(r"\[\[([^\]\n]+?)\]\]", lambda match: _wikilink(match.group(1), pages_by_title), out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"&lt;(https?://[^&]+?)&gt;", r"\1", out)
    return out


def markdown(text: str, pages_by_title: Mapping[str, str]) -> tuple[str, list[dict[str, str]]]:
    """Render the shapes the projection actually emits; returns the body and its heading list."""
    body: list[str] = []
    toc: list[dict[str, str]] = []
    in_list = False
    in_quote = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            body.append("</ul>")
            in_list = False

    def close_quote() -> None:
        nonlocal in_quote
        if in_quote:
            body.append("</blockquote>")
            in_quote = False

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            close_list()
            close_quote()
            continue
        if line.startswith("# "):
            close_list()
            close_quote()
            continue  # the page header is rendered by the shell
        if line.startswith("## "):
            close_list()
            close_quote()
            anchor = f"s{len(toc)}"
            toc.append({"id": anchor, "text": line[3:]})
            body.append(f'<h2 id="{anchor}">{_inline(line[3:], pages_by_title)}</h2>')
            continue
        if line.startswith("### "):
            close_list()
            close_quote()
            body.append(f"<h3>{_inline(line[4:], pages_by_title)}</h3>")
            continue
        if line.startswith("> "):
            close_list()
            if not in_quote:
                body.append("<blockquote>")
                in_quote = True
            body.append(f"<p>{_inline(line[2:], pages_by_title)}</p>")
            continue
        if line.startswith("  - "):
            close_quote()
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f'<li class="nested">{_inline(line[4:], pages_by_title)}</li>')
            continue
        if line.startswith("- "):
            close_quote()
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline(line[2:], pages_by_title)}</li>")
            continue
        close_list()
        close_quote()
        body.append(f"<p>{_inline(line, pages_by_title)}</p>")
    close_list()
    close_quote()
    return "\n".join(body), toc


def frontmatter(content: str) -> dict[str, Any]:
    """The projection's own frontmatter dialect: quoted strings, JSON arrays, bools, ints."""
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 3)
    if end < 0:
        return {}
    fields: dict[str, Any] = {}
    for line in content[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fields[key.strip()] = ([json.loads(item) for item in re.findall(r'"(?:[^"\\]|\\.)*"', inner)]
                                   if inner else [])
        elif value.startswith('"') and value.endswith('"'):
            fields[key.strip()] = json.loads(value)
        elif value in ("true", "false"):
            fields[key.strip()] = value == "true"
        else:
            try:
                fields[key.strip()] = int(value)
            except ValueError:
                fields[key.strip()] = value
    return fields


# --------------------------------------------------------------------------- evidence
def parse_evidence_line(text: str) -> dict[str, Any] | None:
    """`- `path` @ `locator` (revision .., status, class)` - one citation, as the page wrote it."""
    match = _EVIDENCE_LINE.match(text.strip())
    if not match:
        return None
    locator = match.group("locator")
    span = _LINE_SPAN.match(locator)
    line = int(span.group(1)) if span else None
    line_end = (int(span.group(2)) if span and span.group(2) else line) if span else None
    return {"source": match.group("source"), "locator": locator, "line": line, "line_end": line_end,
            "rest": match.group("rest"), "located_by_line": span is not None}


def _second_hop(snippet: str | None) -> dict[str, Any] | None:
    """A derived proposal's line is a JSON record: pull the source it actually quotes."""
    if not snippet or not snippet.lstrip().startswith("{"):
        return None
    quote, raw, locator = _QUOTE.search(snippet), _RAW_PATH.search(snippet), _LOCATOR.search(snippet)
    if not (quote or raw):
        return None
    return {"quote": quote.group("quote") if quote else None,
            "path": raw.group("path") if raw else None,
            "locator": locator.group("locator") if locator else None}


def _source_path(roots: Sequence[Path], relative: Any) -> Path | None:
    """The file this scope's record names, if one of the configured roots still holds it."""
    if not isinstance(relative, str) or not relative:
        return None
    for root in roots:
        candidate = Path(root) / Path(*relative.split("/"))
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file() and resolved.is_relative_to(Path(root).resolve()):
            return resolved
    return None


class _Reader:
    """Read a cited file once per projection, and never outside the configured roots."""

    def __init__(self, roots: Sequence[Path]) -> None:
        self.roots = tuple(roots)
        self._cache: dict[str, list[str] | None] = {}

    def lines(self, relative: str) -> list[str] | None:
        if relative not in self._cache:
            path = _source_path(self.roots, relative)
            try:
                self._cache[relative] = (path.read_text(encoding="utf-8", errors="replace").splitlines()
                                         if path is not None else None)
            except OSError:
                self._cache[relative] = None
        return self._cache[relative]

    def present(self, relative: Any) -> bool:
        path = _source_path(self.roots, relative)
        return path is not None


def _stored_rows(meanings: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]],
                                                                dict[tuple[Any, Any], dict[str, Any]],
                                                                dict[tuple[Any, Any], dict[str, Any]]]:
    """Every evidence row the store accepted, indexed the two ways a page line can name one."""
    rows: list[dict[str, Any]] = []
    for meaning in meanings:
        for row in meaning.get("evidence") or []:
            if isinstance(row, Mapping):
                rows.append({**row, "meaning_id": meaning.get("meaning_id")})
    by_locator: dict[tuple[Any, Any], dict[str, Any]] = {}
    by_line: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in rows:
        by_locator.setdefault((row.get("source_id"), row.get("locator")), row)
        by_line.setdefault((row.get("source_id"), row.get("line_start")), row)
    return rows, by_locator, by_line


def acceptance_basis_summary(basis: Any) -> dict[str, Any] | None:
    """The stored owner-acceptance receipt, field by field, or None when there is none.

    The reader shows this to say *who admitted the version and under which class*. It is
    copied, never completed: a version that saved no basis stays None, and a `test_only`
    receipt is not turned into a business approval.
    """
    if not isinstance(basis, Mapping):
        return None
    return {key: basis.get(key) for key in (
        "receipt_id", "receipt_type", "issuer_id", "authority_class", "issued_at", "expires_at")
        if basis.get(key) is not None}


def _evidence_record(identity: str, page: Page, parsed: Mapping[str, Any], *, source_id: str | None,
                     stored: Mapping[str, Any] | None, reader: _Reader) -> dict[str, Any]:
    relative = str(parsed["source"])
    lines = reader.lines(relative)
    snippet: str | None = None
    line = parsed["line"]
    if lines is not None and isinstance(line, int) and 0 < line <= len(lines):
        snippet = lines[line - 1]
    expected = (stored or {}).get("span_sha256")
    verified = (snippet is not None and isinstance(expected, str)
                and hashlib.sha256(snippet.encode("utf-8")).hexdigest() == expected)
    return {
        "id": identity,
        "page": page.path,
        "source": relative,
        "source_id": source_id,
        "locator": parsed["locator"],
        "located_by_line": parsed["located_by_line"],
        "line": line,
        "line_end": parsed["line_end"],
        "derived": relative.startswith(DERIVED_SOURCE_DIR + "/"),
        "source_label": "原件" if lines is not None else "缺失",
        "snippet": snippet,
        "snippet_truncated": bool(snippet and len(snippet) > SNIPPET_LIMIT),
        "chain": _second_hop(snippet),
        "verified": verified,
        "status_text": parsed["rest"],
        "freshness": (stored or {}).get("freshness_status"),
        "evidence_class": (stored or {}).get("evidence_class"),
        "meaning_id": (stored or {}).get("meaning_id"),
        "span_sha256": expected,
        "revision": (stored or {}).get("source_revision"),
    }


def _page_body(content: str) -> tuple[dict[str, Any], str]:
    fields = frontmatter(content)
    return fields, content.split("\n---\n", 1)[-1].lstrip("\n")


# --------------------------------------------------------------------------- model
def build(wiki: Any) -> dict[str, Any]:
    """Project one Wiki into the Workspace read model: ``{meta, pages, evidence}``."""
    digest = wiki.index_digest() if callable(getattr(wiki, "index_digest", None)) else None
    page_set = project(wiki)
    pages: tuple[Page, ...] = page_set.pages
    by_title = {page.title.strip(): page.path for page in pages}
    links = dict(page_set.stats.get("links") or {})
    backlinks: dict[str, list[str]] = defaultdict(list)
    for edge in links.get("resolved") or []:
        backlinks[edge["path"]].append(edge["from"])

    accepted = wiki.accepted_meanings()
    meanings = list(accepted.get("meanings") or ())
    rows, by_locator, by_line = _stored_rows(meanings)

    source_path: dict[str, str] = {}
    withdrawn = 0
    for source in wiki.sources():
        source_id = str(source.get("source_id"))
        if source.get("status") == "WITHDRAWN":
            withdrawn += 1
            continue
        try:
            record = wiki.source_record(source_id)
        except Exception:  # noqa: BLE001 - a record the store cannot name stays unnamed
            continue
        source_path[source_id] = str(record.get("relative_path") or "")
    path_to_source = {path: source_id for source_id, path in source_path.items() if path}

    reader = _Reader(getattr(wiki, "roots", ()) or ())
    # The objects a page can show are the ones a saved role points at: a duty belongs to its
    # holder's page, an event to both of its sides. Nothing is attached by resemblance.
    entity_map: dict[str, tuple[str, str]] = {}
    for page in pages:
        if page.kind != "entity":
            continue
        declared = frontmatter(page.content)
        for key in (declared.get("canonical_key"), declared.get("canonical_id")):
            if isinstance(key, str) and key:
                entity_map.setdefault(key, (page.title, page.path))
    objects_by_page: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for view in collect(meanings, entities=entity_map, titles=source_path):
        for role in view.roles:
            if role.page:
                objects_by_page[role.page].append(view.to_dict())

    out_pages: list[dict[str, Any]] = []
    evidence_bank: dict[str, dict[str, Any]] = {}
    for page in pages:
        fields, body_md = _page_body(page.content)
        kept: list[str] = []
        page_evidence: list[str] = []
        unparsed = 0
        in_evidence = False
        for line in body_md.splitlines():
            if line.startswith("## "):
                in_evidence = line.strip() == "## 证据"
                if in_evidence:
                    continue  # this section is the evidence drawer, not prose
            if in_evidence and line.startswith("- "):
                parsed = parse_evidence_line(line)
                if parsed is None:
                    unparsed += 1
                    continue
                cited = path_to_source.get(str(parsed["source"]))
                stored = (by_locator.get((cited, parsed["locator"]))
                          or (by_line.get((cited, parsed["line"]))
                              if parsed["line"] is not None else None))
                identity = f"{page.path}#{len(page_evidence)}"
                evidence_bank[identity] = _evidence_record(identity, page, parsed, source_id=cited,
                                                           stored=stored, reader=reader)
                page_evidence.append(identity)
                continue
            kept.append(line)
        body_html, toc = markdown("\n".join(kept), by_title)
        out_pages.append({
            "path": page.path,
            "kind": page.kind,
            "kind_label": KIND_LABEL.get(page.kind, page.kind),
            "title": page.title,
            "fields": fields,
            "html": body_html,
            "toc": toc,
            "evidence": page_evidence,
            "evidence_unparsed": unparsed,
            "backlinks": sorted(set(backlinks.get(page.path, []))),
            "objects": objects_by_page.get(page.path, []),
            "text": re.sub(r"<[^>]+>", " ", body_html),
        })

    verify: dict[str, Any] = {}
    try:
        verify = dict(wiki.verify())
    except Exception:  # noqa: BLE001 - an unreadable store is reported as unknown, not hidden
        verify = {}
    try:
        store_after = wiki.index_digest() if callable(getattr(wiki, "index_digest", None)) else digest
    except Exception:  # noqa: BLE001
        store_after = digest

    counts: dict[str, int] = defaultdict(int)
    for row in out_pages:
        counts[str(row["kind"])] += 1
    meaning_kinds: dict[str, int] = defaultdict(int)
    rows_by_kind: dict[str, int] = defaultdict(int)
    for meaning in meanings:
        kind = str(meaning.get("kind") or "?")
        meaning_kinds[kind] += 1
        rows_by_kind[kind] += len(meaning.get("evidence") or [])
    off_page = {kind: total for kind, total in sorted(rows_by_kind.items()) if kind != "entity"}
    present = [source_id for source_id, relative in source_path.items() if reader.present(relative)]
    absent = [source_id for source_id, relative in source_path.items() if not reader.present(relative)]
    derived_missing = [source_id for source_id in absent
                       if source_path[source_id].startswith(DERIVED_SOURCE_DIR + "/")]
    page_identity: Mapping[str, Any] = (page_set.identity
                                        if isinstance(page_set.identity, Mapping) else {})
    # Which class admitted the active version, and the basis the version saved for it.
    # This is a separate fact from "the store has accepted meanings": a test admission
    # must not read as a business one, and an empty basis is reported as empty.
    ledger = wiki.semantic_state() if callable(getattr(wiki, "semantic_state", None)) else {}
    versions = ledger.get("accepted_versions") if isinstance(ledger, Mapping) else {}
    active_version_id = (page_identity.get("active_version_id")
                         or accepted.get("active_version_id"))
    active_version = (versions.get(active_version_id)
                      if isinstance(versions, Mapping) and isinstance(active_version_id, str)
                      else None)
    active_version = active_version if isinstance(active_version, Mapping) else {}
    basis = active_version.get("owner_acceptance_basis")
    meta = {
        "scope": getattr(wiki, "scope_id", None) or accepted.get("scope_id"),
        "read_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "store_index_sha256": digest,
        "index_stable": digest == store_after,
        "active_version_id": active_version_id,
        "authority": {
            "version_id": active_version_id,
            "authority_class": active_version.get("authority_class"),
            "acceptance_basis_state": "recorded" if isinstance(basis, Mapping) else "missing",
            "acceptance_basis": acceptance_basis_summary(basis),
        },
        "concept_version": page_identity.get("concept_set_version"),
        "pages": len(out_pages),
        "counts": dict(counts),
        "kind_order": [kind for kind in KIND_ORDER if counts.get(kind)],
        "verify": {"status": verify.get("status", "UNKNOWN"),
                   "artifact_count": verify.get("artifact_count", 0),
                   "orphans": len(verify.get("orphans") or []),
                   "problems": len(verify.get("problems") or [])},
        "links": {"links": links.get("links", 0),
                  "unresolved": len(links.get("unresolved") or []),
                  "ambiguous": len(links.get("ambiguous") or []),
                  "duplicate_titles": len(links.get("duplicate_titles") or {})},
        "sources": {"recorded": len(source_path), "present": len(present), "missing": len(absent),
                    "missing_ids": absent, "derived_missing": len(derived_missing),
                    "withdrawn": withdrawn},
        "meanings": dict(sorted(meaning_kinds.items(), key=lambda item: (-item[1], item[0]))),
        "meanings_total": len(meanings),
        "evidence": {
            "rows": len(rows),
            "on_pages": len(evidence_bank),
            "off_pages": max(0, len(rows) - len(evidence_bank)),
            "off_page_kinds": off_page,
            "verified": sum(1 for row in evidence_bank.values() if row["verified"]),
            "missing": sum(1 for row in evidence_bank.values() if row["source_label"] == "缺失"),
            "derived": sum(1 for row in evidence_bank.values() if row["derived"]),
            "unlocated": sum(1 for row in evidence_bank.values() if not row["located_by_line"]),
        },
    }
    return {"meta": meta, "pages": out_pages, "evidence": evidence_bank}


def payload(wiki: Any) -> bytes:
    """The model as the one JSON body the Workspace serves."""
    return json.dumps(build(wiki), ensure_ascii=False).replace("</", "<\\/").encode("utf-8")
