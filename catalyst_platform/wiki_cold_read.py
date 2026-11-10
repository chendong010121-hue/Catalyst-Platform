"""Read a copied Wiki and its page tree, and say what a cold reader would find.

This is the recovery-side counterpart of ``wiki verify``. ``verify`` asks whether a store is
internally consistent; this asks whether *this copy* still contains everything the product
needs - the sources it names, the artifacts its index points at, the accepted versions, the
active pointer, the concept set, the pages that were published from it, the pages a person
changed, and whether the links between those pages lead anywhere - and it answers by
reading the copy only. Nothing here writes, migrates, repairs or "fixes" what it finds:
a cold reader is exactly the reader an auditor can be.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from .wiki import ProjectWiki, WikiError, WikiUnavailable
from .wiki_pages import MANIFEST_NAME, OBSOLETE_DIR, _read_manifest, project

# Errors block a cold read; notes are things a reader should know but that are not a failure.
_ERROR = "error"
_NOTE = "note"
# Where the Wiki line writes one derived proposal beside every document it reads.
DERIVED_SOURCE_DIR = ".catalyst-proposals"


def _core_identity(identity: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The part of a projection identity that says *which store generation*, not *which build*."""
    if not isinstance(identity, Mapping):
        return None
    return {key: identity.get(key) for key in (
        "scope_id", "backend", "store_index_sha256", "active_version_id", "concept_set_version")}


def cold_read(*, workspace: Path | str, enterprise_id: str, project_id: str,
              roots: Sequence[Path | str], pages_root: Path | str,
              backend: str = "json") -> dict[str, Any]:
    """Read one copy of a Wiki and its pages; every input is on the copy, never the original."""
    wiki = ProjectWiki(workspace, roots, enterprise_id=enterprise_id, project_id=project_id,
                       backend=backend)
    tree = Path(pages_root).expanduser().resolve()
    report: dict[str, Any] = {
        "wiki_action": "cold-read",
        "status": "OK",
        "workspace": str(wiki.workspace),
        "pages_root": str(tree),
        "source_roots": [str(root) for root in wiki.roots],
        "backend": wiki.backend,
        "problems": [],
        "links": {},
    }

    def failed(code: str, detail: str, severity: str = _ERROR, **extra: Any) -> None:
        report["problems"].append({"code": code, "severity": severity, "detail": detail, **extra})

    # --- the store itself ---------------------------------------------------------------
    store = wiki.verify()
    report["store"] = {
        "status": store.get("status"),
        "index_sha256": wiki.index_digest(),
        "artifact_count": store.get("artifact_count", 0),
        "orphans": store.get("orphans", []),
        "problems": store.get("problems", []),
    }
    if store.get("status") == "EMPTY":
        report["status"] = "EMPTY"
        failed("store_empty", "the copied store holds nothing for this scope")
        return report
    if store.get("status") != "OK":
        failed("store_broken", "the copied store does not verify", problems=store.get("problems", []))

    # --- versions and the active pointer ------------------------------------------------
    state: dict[str, Any] = {}
    try:
        state = wiki.semantic_state()
    except WikiUnavailable as exc:
        failed("semantic_unreadable", str(exc))
    raw_versions = state.get("accepted_versions")
    versions: dict[str, Any] = raw_versions if isinstance(raw_versions, dict) else {}
    active = state.get("active_version_id")
    active_ok = active is None or active in versions
    if not active_ok:
        failed("active_pointer_missing", f"the active version {active!r} is not among the accepted versions")
    report["versions"] = {
        "count": len(versions),
        "active_version_id": active,
        "active_pointer_ok": active_ok,
    }

    # --- the concept set ----------------------------------------------------------------
    concepts: dict[str, Any] = {"version_id": None, "count": 0}
    try:
        concept_set = wiki.concept_set()
        concepts = {
            "version_id": getattr(concept_set, "version_id", None),
            "count": len(tuple(getattr(concept_set, "concepts", ()) or ())),
        }
    except WikiError as exc:
        failed("concepts_unreadable", str(exc))
    report["concepts"] = concepts

    # --- every source the store names ---------------------------------------------------
    #
    # By bytes, not by text: the store keeps decks and spreadsheets as well as Markdown, and a
    # cold read that could only vouch for `.md` would report a healthy corpus as half missing.
    recorded: list[dict[str, Any]] = []
    try:
        recorded = [row for row in wiki.sources() if row.get("status") != "WITHDRAWN"]
    except WikiError as exc:
        failed("sources_unreadable", str(exc))
    verified: list[str] = []
    missing: list[str] = []
    changed: list[str] = []
    ambiguous: list[str] = []
    derived_missing: list[str] = []
    for row in recorded:
        source_id = str(row.get("source_id"))
        try:
            record = wiki.source_record(source_id)
        except WikiError as exc:
            missing.append(source_id)
            failed("missing_source", str(exc), source_id=source_id)
            continue
        relative_path = record.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path:
            missing.append(source_id)
            failed("missing_source", "the source record names no file", source_id=source_id)
            continue
        relative = Path(*relative_path.split("/"))
        candidates = [root / relative for root in wiki.roots if (root / relative).is_file()]
        if not candidates:
            # A proposal the Wiki line writes beside a document is derived, not an input: its
            # absence is worth naming, but it is not a user document that went missing.
            if relative.parts and relative.parts[0] == DERIVED_SOURCE_DIR:
                derived_missing.append(source_id)
                failed("derived_source_missing",
                       f"the derived proposal for {source_id} is not in the copy",
                       source_id=source_id, relative_path=relative_path, severity=_NOTE)
            else:
                missing.append(source_id)
                failed("missing_source",
                       f"no file for {source_id} under the given source roots", source_id=source_id,
                       relative_path=relative_path)
            continue
        if len(candidates) > 1:
            ambiguous.append(source_id)
            failed("source_ambiguous",
                   f"more than one root holds {relative_path}", source_id=source_id,
                   relative_path=relative_path)
            continue
        try:
            digest = hashlib.sha256(candidates[0].read_bytes()).hexdigest()
        except OSError as exc:
            missing.append(source_id)
            failed("missing_source", f"{relative_path} could not be read: {exc}", source_id=source_id)
            continue
        if digest != record.get("revision"):
            changed.append(source_id)
            failed("source_changed",
                   f"the bytes of {relative_path} no longer match the revision the store recorded",
                   source_id=source_id)
            continue
        verified.append(source_id)
    report["sources"] = {
        "recorded": len(recorded),
        "verified": len(verified),
        "missing": sorted(missing),
        "changed": sorted(changed),
        "ambiguous": sorted(ambiguous),
        "derived_missing": sorted(derived_missing),
    }

    # --- the page tree this store was projected into ------------------------------------
    pages: dict[str, Any] = {
        "projected": 0, "on_disk": 0, "recorded": 0,
        "human_edited": [], "stale_record": [], "missing": [],
        "unrecorded": [], "obsolete_present": [], "unknown_files": [], "archived": 0,
        "tree_identity_present": False, "identity_match": False,
        "tree_identity": None, "projection_identity": None,
    }
    manifest = _read_manifest(tree)
    on_disk = {
        path.relative_to(tree).as_posix(): path
        for path in tree.rglob("*.md")
        if path.is_file() and OBSOLETE_DIR not in path.relative_to(tree).parts
    } if tree.is_dir() else {}
    pages["on_disk"] = len(on_disk)
    pages["recorded"] = len(manifest.pages)
    pages["archived"] = sum(1 for path in (tree / OBSOLETE_DIR).rglob("*.md")
                            if path.is_file()) if (tree / OBSOLETE_DIR).is_dir() else 0
    if not manifest.pages:
        failed("no_manifest", "the copied page tree has no readable manifest", severity=_ERROR)
    try:
        projection = project(wiki, root=tree)
    except WikiError as exc:
        projection = None
        failed("projection_failed", str(exc))
    if projection is not None:
        pages["projected"] = len(projection.pages)
        pages["projection_identity"] = projection.identity
        pages["tree_identity"] = manifest.identity
        pages["tree_identity_present"] = manifest.identity is not None
        if manifest.identity is None:
            failed("tree_identity_missing",
                   "the page tree does not say which store generation it came from",
                   severity=_NOTE)
        else:
            pages["identity_match"] = _core_identity(manifest.identity) == _core_identity(projection.identity)
            if not pages["identity_match"]:
                failed("identity_mismatch",
                       "the page tree was projected from a different store generation than this copy")
        for page in projection.pages:
            target = on_disk.get(page.path)
            if target is None:
                pages["missing"].append(page.path)
                failed("page_missing", "a page this store projects is not in the copied tree", path=page.path)
                continue
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            expected = manifest.pages.get(page.path)
            if expected is None:
                pages["unrecorded"].append(page.path)
                failed("page_unrecorded", "the manifest does not record this page", path=page.path,
                       severity=_NOTE)
            elif digest != expected:
                if digest == page.sha256:
                    pages["stale_record"].append(page.path)
                    failed("page_stale_record",
                           "the page holds the projected bytes but the manifest is behind it",
                           path=page.path, severity=_NOTE)
                else:
                    pages["human_edited"].append(page.path)
                    failed("page_human_edited",
                           "the page was changed by a person after it was published",
                           path=page.path, severity=_NOTE)
        projected_paths = {page.path for page in projection.pages}
        pages["obsolete_present"] = sorted(path for path in manifest.pages if path not in projected_paths)
        for path in pages["obsolete_present"]:
            failed("obsolete_page_present",
                   "the tree still holds a page this store no longer produces", path=path,
                   severity=_NOTE)
        pages["unknown_files"] = sorted(
            path for path in on_disk if path not in manifest.pages and path not in projected_paths)
        for path in pages["unknown_files"]:
            failed("page_unknown", "a file in the page tree belongs to neither the tree nor the store",
                   path=path, severity=_NOTE)
        # A page that links to a title no page carries is a dead end a cold reader walks into;
        # a title two pages share cannot be resolved by name at all. Both are reported as the
        # copy's own defects, because the projection already wrote these links itself.
        links = dict(projection.stats.get("links") or {})
        report["links"] = links
        if links.get("unresolved"):
            failed("link_unresolved", "a page links to a title no page in this tree carries",
                   targets=links["unresolved"])
        if links.get("ambiguous"):
            failed("link_ambiguous", "a page links to a title more than one page carries",
                   targets=links["ambiguous"])
        for title, paths in sorted((links.get("duplicate_titles") or {}).items()):
            failed("page_title_duplicate", f"{title!r} is the title of more than one page",
                   title=title, paths=paths, severity=_NOTE)
    report["pages"] = pages

    errors = [row for row in report["problems"] if row["severity"] == _ERROR]
    if errors:
        report["status"] = "BROKEN"
    elif report["status"] != "EMPTY":
        report["status"] = "OK"
    report["manifest_present"] = (tree / MANIFEST_NAME).is_file()
    return report
