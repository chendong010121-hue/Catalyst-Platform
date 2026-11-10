"""Stage one explicit local document into Wiki and leave it as a candidate.

This is the product entry for "a single document enters Wiki": the bytes and their
identity are recorded first, Understand then proposes structure from the same file,
and the proposal is submitted as a candidate that nobody has accepted yet. The
document never becomes source text or an accepted version by being staged.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .components import ComponentError
from .gateway import CatalystGateway
from .knowledge_novelty import LINK_ONLY, SKIP, UNREAD, assess_novelty, write_receipt
from .ontology_types import concept_set_identity
from .semantic_method import SEMANTIC_COMPONENT, run_semantic_method
from .semantic_wiki import SemanticTransitionError, SemanticWiki
from .understand_only import UnderstandPort, UnderstandingRequest
from .understand_sources import extract_with_report
from .understand_wiki import UnderstandWikiAdapter
from .wiki import ProjectWiki, WikiError
from .wiki_mentions import EntityIndex

SUPPORTED_SOURCE_SUFFIXES = (".md", ".docx", ".pptx", ".pdf", ".xlsx")

# The component store saying "nothing is enabled here", in the two shapes it says it.
_METHOD_NOT_ENABLED = ("method has no active version", "component has no admitted versions")


class KnowledgeIntakeError(RuntimeError):
    """One explicit local document could not enter Wiki as a candidate."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def stage_and_scan(
    wiki: ProjectWiki,
    path: Path | str,
) -> dict[str, Any]:
    """Record one document's identity and what extraction could read; never calls a model.

    This is the free half of intake: bytes, revision, units and completeness. Anything
    that would call a model happens only after a caller decides the document is new.
    """
    selected = Path(path)
    if selected.suffix.casefold() not in SUPPORTED_SOURCE_SUFFIXES:
        raise KnowledgeIntakeError(
            "source_format_unsupported",
            "only Markdown, Word, PowerPoint, Excel or PDF files can enter Wiki",
        )
    try:
        staged = (
            wiki.stage_markdown(selected)
            if selected.suffix.casefold() == ".md"
            else wiki.stage_native_source(selected)
        )
    except WikiError as exc:
        raise KnowledgeIntakeError("source_not_stageable", str(exc)) from exc

    if staged.get("status") == "no_op" and wiki.source_record(staged["source_id"]).get("status") == "WITHDRAWN":
        # Registering a withdrawn document again is an explicit change of mind.
        staged = wiki.restore_source(staged["source_id"])

    record = wiki.source_record(staged["source_id"])
    try:
        units, report = extract_with_report(
            selected,
            str(record.get("relative_path") or selected.name),
            staged["source_id"],
            staged["revision"],
            raw=selected.read_bytes(),
        )
    except (ValueError, OSError) as exc:
        # A document that cannot be read still keeps its identity, and says why.
        extraction = {
            "status": "no_text",
            "unit_count": 0,
            "locator_count": 0,
            "truncated": False,
            "part_errors": [],
            "vision_missing": [],
            "warnings": [f"EXTRACTION_REFUSED:{type(exc).__name__}:{str(exc)[:160]}"],
            "recorded_at": "",
        }
        recorded = wiki.record_extraction(staged["source_id"], extraction)
        return {"source": staged, "extraction": recorded["extraction"], "unit_count": 0, "units": []}

    recorded = wiki.record_extraction(staged["source_id"], report.to_dict())
    return {
        "source": staged,
        "extraction": recorded["extraction"],
        "unit_count": len(units),
        "units": units,
    }


def _read(request: UnderstandingRequest, *, source_root: Path | str,
          concepts: Any, semantic_provider: Any | None, verifier_provider: Any | None,
          methods: Any | None, method_component: str, extraction_mode: str, label: str,
          record_dir: Path | str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read one staged document, and say which assembly read it.

    Two assemblies exist and they are not interchangeable. A workspace with an active
    method reads under that method's lease, and the record names the package. A workspace
    with none reads the product's own Skill tree; that is a supported reading, but it is
    not the registered method and the result says which one it was instead of leaving a
    reader to assume the better case.
    """
    if methods is None:
        extra: dict[str, Any] = {}
        if semantic_provider is not None:
            extra["semantic_provider"] = semantic_provider
            extra["concepts"] = concepts
        if verifier_provider is not None:
            extra["verifier_provider"] = verifier_provider
        result = UnderstandPort().understand(request, source_root=source_root, **extra)
        return result.to_dict(), {
            "kind": "builtin_skill",
            "reason": "no component store was supplied: the product's own Skill tree read this",
            "concepts": concept_set_identity(concepts),
        }
    try:
        run = run_semantic_method(methods, request, source_root=source_root,
                                  provider=semantic_provider, extraction_mode=extraction_mode,
                                  label=label, component_id=method_component,
                                  concepts=concepts, verifier_provider=verifier_provider,
                                  record_dir=record_dir)
    except ComponentError as exc:
        # Two messages mean "this workspace has not enabled the method": nothing is
        # admitted, or nothing is activated. Every other refusal (busy, digest, an
        # unreadable package) is a broken assembly and must not be read around.
        if str(exc) not in _METHOD_NOT_ENABLED:
            raise
        state = "admitted" if "admitted versions" in str(exc) else "activated"
        # Nothing is activated in this workspace. The document still enters Wiki; what it
        # must not do is claim the registered method read it.
        extra: dict[str, Any] = {}
        if semantic_provider is not None:
            extra["semantic_provider"] = semantic_provider
            extra["concepts"] = concepts
        if verifier_provider is not None:
            extra["verifier_provider"] = verifier_provider
        result = UnderstandPort().understand(request, source_root=source_root, **extra)
        return result.to_dict(), {
            "kind": "builtin_skill",
            "reason": (f"no version of {method_component} is {state} in this workspace: "
                       "the product's own Skill tree read this"),
            "concepts": concept_set_identity(concepts),
        }
    return run.result.to_dict(), {
        "kind": "registered_method",
        "method": dict(run.identity.get("method") or {}),
        "concepts": dict(run.identity.get("concepts") or {}),
        "implementation": dict(run.identity.get("implementation") or {}).get("sha256"),
        "extraction_mode": run.identity.get("extraction_mode"),
        "lease": dict(run.lease),
        "validation": dict(run.validation),
    }


def intake_source(
    wiki: ProjectWiki,
    path: Path | str,
    *,
    source_root: Path | str | None = None,
    actor_origin: str = "local_workspace_user",
    intent: str = "KNOWLEDGE_PROPOSE",
    rejudge: bool = False,
    semantic_provider: Any | None = None,
    verifier_provider: Any | None = None,
    methods: Any | None = None,
    method_component: str = SEMANTIC_COMPONENT,
    extraction_mode: str = "single_stage",
    label: str = "wiki-intake",
    record_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Record one document's identity, then propose its structure as a candidate.

    ``rejudge`` re-reads a shelf decision for bytes that never changed: a document staged
    while nobody had named its material must not stay unmodelled forever because its
    revision is stable. ``semantic_provider`` is an already-authorized model provider; the
    caller owns the money it spends, exactly as it does for every other proposal.

    ``methods`` is the workbench's component store. When a method is admitted **and**
    activated there, the reading is bound to it for the whole run through
    :func:`run_semantic_method`: the result names the package, the concept set, the
    extraction mode, the repairs and the sources. When nothing is active the reading is
    the product's own Skill tree and says so -- merging code is not enabling a method.
    """
    selected = Path(path)
    scanned = stage_and_scan(wiki, selected)
    staged = scanned["source"]
    extraction = scanned["extraction"]

    record = wiki.source_record(staged["source_id"])
    # What the shelf already holds, by name and by how far its reading got: an outline
    # may only be covered by a sibling that was read whole.
    siblings = {
        str(row.get("relative_path")): str(row.get("content_status") or "NOT_PARSED")
        for row in wiki.sources()
        if row.get("status") != "WITHDRAWN" and row.get("source_id") != staged.get("source_id")
    }
    # Whether these bytes were ever proposed decides whether re-judging may pay again.
    already_proposed = any(
        row.get("source_id") == staged.get("source_id")
        and row.get("source_revision") == staged.get("revision")
        for row in (wiki.semantic_state().get("candidates") or {}).values()
    )
    verdict = assess_novelty(
        index=EntityIndex.build(wiki),
        units=scanned["units"],
        source_id=staged.get("source_id"),
        source_revision=staged.get("revision"),
        source_name=str(record.get("relative_path") or ""),
        siblings=siblings,
        revision_changed=staged.get("status") != "no_op",
        dialect_claims=int(staged.get("claim_count") or 0),
        truncated=bool(extraction.get("truncated")),
        unread_locators=max(
            0, int(extraction.get("locator_count") or 0) - int(extraction.get("unit_count") or 0)
        ),
        rejudge=rejudge,
        already_proposed=already_proposed,
    )
    receipt = write_receipt(wiki.workspace, verdict)
    if not verdict.spends_money:
        # Nothing here is new: the mentions can be read from the source at any time,
        # and no model needs to speak about a document that says what we already know.
        return {
            "status": {SKIP: "SKIPPED", UNREAD: "DEFERRED_UNREAD", LINK_ONLY: "LINKED_ONLY"}[verdict.tier],
            "authority": "CANDIDATE_ONLY",
            "scope_id": wiki.scope_id,
            "source": staged,
            "extraction": extraction,
            "novelty": verdict.to_dict(),
            "novelty_receipt": str(receipt),
            "candidate": None,
            "understand_status": "not_called",
            "evidence_count": 0,
        }

    root = source_root
    if root is None:
        if len(wiki.roots) != 1:
            raise KnowledgeIntakeError(
                "source_root_required",
                "a source root is required when the Wiki declares several roots",
            )
        root = wiki.roots[0]

    # A provider is handed in by a caller that already owns the budget; without one this
    # stays the deterministic reading and costs nothing.
    request = UnderstandingRequest(
        request_id="intake_" + uuid.uuid4().hex,
        message=f"stage {selected.name} as a candidate",
        source_refs=(selected,),
        intent=intent,
        scope_id=wiki.scope_id,
        requested_depth="semantic",
        budget_steps=16,
    )
    concepts = wiki.concept_set()
    result, assembly = _read(
        request, source_root=root, concepts=concepts,
        semantic_provider=semantic_provider, verifier_provider=verifier_provider,
        methods=methods, method_component=method_component,
        extraction_mode=extraction_mode, label=label, record_dir=record_dir)

    evidence = result.get("evidence_refs") or []
    summary: dict[str, Any] = {
        "assembly": assembly,
        "authority": "CANDIDATE_ONLY",
        "scope_id": wiki.scope_id,
        "source": staged,
        "extraction": extraction,
        "novelty": verdict.to_dict(),
        "novelty_receipt": str(receipt),
        "understand_status": result.get("status"),
        "evidence_count": len(evidence),
        "candidate": None,
    }
    if not evidence:
        # A document with no extractable text still belongs to Wiki as identity
        # only; proposing structure from nothing would be invention.
        summary["status"] = "STAGED_WITHOUT_CANDIDATE"
        summary["reason"] = "NO_EXTRACTABLE_EVIDENCE"
        summary["warnings"] = result.get("warnings")
        return summary

    gateway = CatalystGateway(wiki.workspace)

    def submit(recorder):
        return UnderstandWikiAdapter(wiki, SemanticWiki(wiki, recorder=recorder), root).submit(
            result, declared_scope_id=wiki.scope_id
        )

    try:
        outcome = gateway.semantic_operation(
            operation="understand.candidate.submit",
            scope_id=wiki.scope_id,
            actor_origin=actor_origin,
            input_value={
                "contract_version": "catalyst.understand_handoff.v1",
                "source_id": staged.get("source_id"),
                "source_revision": staged.get("revision"),
            },
            action=submit,
        )
    except SemanticTransitionError as exc:
        raise KnowledgeIntakeError(getattr(exc, "code", "candidate_rejected"), str(exc)) from exc

    receipt = outcome.get("result") if isinstance(outcome.get("result"), dict) else {}
    summary["candidate"] = receipt
    summary["run_id"] = outcome.get("run_id")
    summary["status"] = "CANDIDATE_STAGED"
    if receipt.get("mapping_status") != "COMPLETE":
        summary["status"] = "CANDIDATE_INCOMPLETE"
    return summary
