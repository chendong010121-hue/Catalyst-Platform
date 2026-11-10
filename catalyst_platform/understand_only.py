"""Bounded Source Analysis Port for explicitly selected local files.

This module produces bounded, source-grounded result objects. It does not own
ProjectWiki persistence, independent semantic evaluation, asset registration,
authorization, or an Agent Runtime loop. The installed strategy files are a
fixed local allowlist; source-provided Skills and scripts are inspected as data only.

The port is assembled from six concern modules (models, sources, manifest, assets,
semantic, verify).  Every name they define is re-exported here, unchanged, so this
module keeps the import surface it has always had: callers and tests that do
``from catalyst_platform.understand_only import X`` do not move.
"""

from __future__ import annotations

import json

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from .understand_models import (
    AssetCandidateOutput,
    CoverageRecord,
    DocumentKnowledgeOutput,
    EvidenceExpansionRequest,
    EvidenceExpansionResult,
    EvidenceRef,
    GroundedItem,
    IntentRoute,
    ResultStatus,
    SelectedSkill,
    SemanticCandidateOutput,
    SemanticCapacityError,
    SemanticContractError,
    SemanticVerificationError,
    SourceRecord,
    StrategyRunReceipt,
    TaskContextOutput,
    UnderstandIntent,
    UnderstandingRequest,
    UnderstandingResult,
    _InvalidEnvelopeAnswer,
    _MalformedJsonAnswer,
    _OversizeAnswer,
    _TextUnit,
    _ToolCallAnswer,
    _TruncatedAnswer,
    _UnreadableAnswer,
    _coverage,
    _jsonable,
    _new_evidence,
    _new_item,
    _sha,
)
from .understand_sources import (
    _ALLOWED,
    _EXCLUDED,
    _MAX_ARCHIVE_MEMBERS,
    _MAX_ARCHIVE_UNCOMPRESSED,
    _MAX_FILE_BYTES,
    _MAX_TEXT_BYTES,
    _MAX_UNITS,
    _SECRET_NAMES,
    _SourceMixin,
    _archive_read,
    _extract,
    _media_type,
    _safe_file,
    _select_relevant_units,
    _walk_sources,
    _xml_text,
)
from .understand_manifest import (
    _FRONTMATTER_BLOCK,
    _FRONTMATTER_FIELD,
    _GENERATOR_METHOD_HEADING,
    _MAX_METHOD_BYTES,
    _SKILL_ROOT,
    _SKILL_STRATEGIES,
    _SkillResolver,
    _frontmatter_body,
    _frontmatter_text,
    _generator_method,
    _parse_frontmatter,
    _skill_plan,
)
from .understand_assets import _AssetMixin
from .understand_semantic import (
    _ABSENCE_FIELDS,
    _CJK_RANGES,
    _MAX_EXTRACTION_UNITS,
    _MAX_KEY_HINTS,
    _MAX_MERGED_ENTITIES,
    _MAX_MERGED_ITEMS,
    _MAX_MERGED_OTHER_ITEMS,
    _MAX_SEMANTIC_ENTITIES,
    _MAX_SEMANTIC_ITEMS,
    _MAX_SEMANTIC_OTHER_ITEMS,
    _MAX_UNIT_ITEMS,
    _SEMANTIC_EXTRACTION_RULES,
    _SemanticMixin,
    _UNIT_ROWS,
    _WORD_SPLIT,
    _entity_name_is_quoted,
    _evidence_units,
    _is_cjk,
    _key_reuse_hint,
    _locator_unit,
    _unquoted_runs,
    stored_evidence_class,
)
from .understand_verify import (
    _MAX_REVISION_ATTEMPTS,
    _MAX_VERIFICATION_BYTES,
    _VERDICT_RANK,
    _VERIFICATION_BATCH_ITEMS,
    _VERIFIER_CONTRACT,
    _VERIFIER_REFERENCE,
    _clamped_verdict,
    _finding_locators,
    _revision_block,
    _verifier_instruction,
    format_understanding_context,
    handoff_external_candidate,
    revision_entries,
    revision_from_findings,
    verification_advisories,
    verification_integrity,
    verification_local_checks,
    verify_candidate,
)


class UnderstandPort(_SourceMixin, _AssetMixin, _SemanticMixin):
    """Analyze only selected local sources and return bounded evidence and coverage to the caller."""

    def __init__(self, *, skill_root: Path | None = None, extraction_mode: str = "single_stage") -> None:
        if extraction_mode not in {"single_stage", "source_local_two_stage"}:
            raise ValueError("unknown Understand extraction mode")
        self._extraction_mode = extraction_mode
        self._resolver = _SkillResolver(skill_root or _SKILL_ROOT)

    def understand(
        self,
        request: UnderstandingRequest,
        *,
        source_root: Path | str,
        recorder: Any | None = None,
        semantic_provider: Any | None = None,
        verifier_provider: Any | None = None,
        source_evidence_scope: Mapping[str, Sequence[str] | None] | None = None,
        concepts: Any | None = None,
        identity_decisions: Sequence[Mapping[str, Any]] | None = None,
    ) -> UnderstandingResult:
        """Read selected local sources into bounded evidence and a typed candidate.

        ``concepts`` is the concept set of the scope this request is read for: the types
        the prompt offers and the types each entity may declare. Omitted, the extraction
        reads against the starter pack of the standard.

        ``identity_decisions`` carries the identity answers a reader already gave, as
        ``{"keys": [alias, kept], "keep": kept}``: the pair is folded into the graph
        instead of being offered for a decision again.
        """
        if not request.request_id or not request.message.strip():
            raise ValueError("request_id and message are required")
        route = route_understand_request(
            request.message,
            requested_intent=request.intent,
            selected_paths=request.source_refs,
            requested_depth=request.requested_depth,
            budget_steps=request.budget_steps,
        )
        root = Path(source_root).expanduser().resolve()
        intent = route.intent
        try:
            selected_sources = _walk_sources(request.source_refs, root)
        except PermissionError as exc:
            return self._empty_result(request, route, "DENIED", "no_result", "source_scope_denied", warnings=(str(exc),))
        except (OSError, ValueError) as exc:
            status = "UNSUPPORTED" if "unsupported" in str(exc).casefold() else "PARTIAL"
            return self._empty_result(request, route, status, "no_result", "source_inventory_failed", warnings=(type(exc).__name__,))
        if not selected_sources:
            return self._empty_result(request, route, "NEEDS_CONTEXT", "no_result", "no_sources_selected")

        skill_ids = _skill_plan(intent, selected_sources, depth=route.requested_depth)
        active_skill_ids = skill_ids[: route.budget_steps]
        skipped_skill_ids = skill_ids[len(active_skill_ids) :]
        progressive = route.requested_depth in {"semantic", "bounded_deep"} or intent is UnderstandIntent.ASSET_INSPECT
        try:
            skills = self._resolver.load(active_skill_ids, progressive=progressive)
        except (OSError, UnicodeDecodeError, ValueError, PermissionError) as exc:
            return self._empty_result(request, route, "UNSUPPORTED", "no_result", "trusted_skill_unavailable", warnings=(type(exc).__name__,))
        skills_by_id = {skill.skill_id: skill for skill in skills}
        if "understand-source-inventory" not in skills_by_id:
            return self._empty_result(request, route, "PARTIAL", "no_result", "strategy_budget_exhausted")

        spans: dict[str, str] = {}
        receipts: list[StrategyRunReceipt] = []
        def begin(skill: SelectedSkill, source_digest: str | None = None) -> None:
            if recorder is not None:
                spans[skill.skill_id] = recorder.start_span(
                    f"understand.strategy.{skill.strategy_id}",
                    kind="CHAIN",
                    component_id=skill.skill_id,
                    component_version=skill.version,
                    manifest_sha256=skill.skill_sha256,
                    source_sha256=source_digest,
                    attributes={
                        "component_id": skill.skill_id,
                        "component_version": skill.version,
                        "manifest_sha256": skill.skill_sha256,
                        "instruction_sha256": skill.instruction_sha256,
                        "instruction_delivery": "result_consumer_context",
                    },
                )

        def end(skill: SelectedSkill, *, status: str, attributes: Mapping[str, Any] | None = None) -> None:
            if recorder is not None and skill.skill_id in spans:
                recorder.end_span(spans[skill.skill_id], status=status, attributes=dict(attributes or {}))

        try:
            inventory_skill = skills_by_id["understand-source-inventory"]
            begin(inventory_skill)
            source_records, unit_records, warnings = self._inventory(
                selected_sources, root, source_evidence_scope,
                require_complete=route.intent is UnderstandIntent.KNOWLEDGE_PROPOSE,
            )
            if semantic_provider is not None and (
                    any(w.startswith("PARTIAL") for w in warnings)
                    or sum(row.locator_count for row in source_records) > len(unit_records)):
                raise ValueError("partial source exceeds semantic extraction bound; admit exact complete units")
            if source_evidence_scope is not None:
                # Host admission selects exact native locators; no business-text
                # rewriting, keyword removal, or derived summary becomes evidence.
                records = {row.relative_path: row.source_id for row in source_records}
                if set(source_evidence_scope) != set(records):
                    raise ValueError("evidence scope must cover exactly the original source manifest")
                admitted = {}
                for relative, locators in source_evidence_scope.items():
                    source_id = records[relative]
                    available = {u.locator for u in unit_records if u.source_id == source_id}
                    if locators is None:
                        admitted[source_id] = available
                    elif (not isinstance(locators, (tuple, list)) or not locators
                          or any(not isinstance(v, str) for v in locators)
                          or not set(locators).issubset(available)):
                        raise ValueError("original source locator missing; no partial extraction permitted")
                    else:
                        admitted[source_id] = set(locators)
                unit_records = [u for u in unit_records if u.locator in admitted[u.source_id]]
                if not unit_records:
                    raise ValueError("admitted source scope contains no readable evidence")
            combined_source_digest = (
                source_records[0].source_sha256
                if len(source_records) == 1
                else _sha("\n".join(item.source_sha256 for item in source_records).encode("utf-8"))
            )
            receipts.append(StrategyRunReceipt(inventory_skill.skill_id, inventory_skill.version, inventory_skill.skill_sha256, inventory_skill.strategy_id, "COMPLETED", len(source_records), "bounded_inventory_complete"))
            end(inventory_skill, status="success" if source_records else "partial", attributes={
                "status": f"inventory;source_count={len(source_records)};source_sha256={combined_source_digest}",
            })

            active_target_ids = [
                skill_id for skill_id in active_skill_ids
                if skill_id not in {"understand-source-inventory", "understand-evidence-coverage"}
            ]
            selected_units = tuple(unit_records)
            if "understand-document" in active_target_ids:
                document_skill = skills_by_id["understand-document"]
                begin(document_skill, combined_source_digest)
                if semantic_provider is not None and intent is UnderstandIntent.KNOWLEDGE_PROPOSE:
                    selected_units = tuple(unit_records)
                    exit_reason = "bounded_semantic_source_extraction"
                elif route.requested_depth in {"semantic", "bounded_deep"}:
                    selected_units, truncated = _select_relevant_units(unit_records, request.message)
                    if not selected_units:
                        selected_units = tuple(unit_records[:180])
                        warnings = tuple((*warnings, "NO_QUERY_MATCH:document evidence retrieval used a bounded source-order fallback"))
                    if truncated:
                        warnings = tuple((*warnings, "PARTIAL_RETRIEVAL:document evidence selection reached its unit limit"))
                    exit_reason = "bounded_query_evidence_retrieval"
                else:
                    selected_units = tuple(unit_records)
                    truncated = False
                    exit_reason = "bounded_full_document_extraction"
                receipts.append(StrategyRunReceipt(
                    document_skill.skill_id, document_skill.version, document_skill.skill_sha256,
                    document_skill.strategy_id, "COMPLETED" if selected_units or not unit_records else "PARTIAL",
                    len(selected_units), exit_reason,
                ))
                end(document_skill, status="success" if selected_units else "partial", attributes={
                    "status": f"query_evidence;selected_units={len(selected_units)};source_sha256={combined_source_digest}",
                })

            evidence = tuple(_new_evidence(unit) for unit in selected_units)
            evidence_by_locator = {(item.source_id, item.locator): item for item in evidence}
            facts: list[GroundedItem] = []
            inferred: list[GroundedItem] = []
            unknowns: list[GroundedItem] = []
            task_context = None
            document_knowledge = None
            semantic_candidate = None
            asset_candidate = None
            wiki_handoff = "NOT_REQUESTED"
            result_type: str
            if not active_target_ids:
                result_type = "SourceInventory"
            elif intent is UnderstandIntent.TASK_USE:
                result_type = "DocumentKnowledge" if route.target == "PROJECT_GROUNDED_CLAIMS" else "TaskContext"
                for unit in selected_units:
                    ref = evidence_by_locator[(unit.source_id, unit.locator)]
                    fact_kind = "grounded_claim" if route.target == "PROJECT_GROUNDED_CLAIMS" else "observed_text"
                    facts.append(_new_item(fact_kind, unit.locator, unit.quote, (ref,)))
                for warning in warnings:
                    if warning.startswith("NEEDS_VISION"):
                        unknowns.append(_new_item("unknown", warning, "Visual meaning was not inspected.", (), evidence_class="unresolved", uncertainty="vision reader unavailable"))
                if route.target == "PROJECT_GROUNDED_CLAIMS":
                    document_knowledge = DocumentKnowledgeOutput(tuple(facts))
                else:
                    task_context = TaskContextOutput(
                        goal=request.message,
                        authority="TASK_ONLY",
                        evidence_ids=tuple(item.evidence_id for item in evidence),
                        unknowns=tuple(item.key for item in unknowns),
                    )
            elif intent is UnderstandIntent.KNOWLEDGE_PROPOSE:
                result_type = "SemanticCandidate"
                semantic_skill = skills_by_id.get("understand-enterprise-semantics")
                if semantic_skill is not None:
                    begin(semantic_skill, combined_source_digest)
                    facts, inferred, unknowns = self._business_items(selected_units, evidence_by_locator)
                    receipts.append(StrategyRunReceipt(semantic_skill.skill_id, semantic_skill.version, semantic_skill.skill_sha256, semantic_skill.strategy_id, "COMPLETED", len(facts) + len(inferred) + len(unknowns), "bounded_candidate_extraction"))
                    end(semantic_skill, status="success", attributes={
                        "status": f"deterministic_candidate_extraction;result_type={result_type};source_sha256={combined_source_digest}",
                    })
                    semantic_candidate = SemanticCandidateOutput(
                        scope_id=request.scope_id,
                        items=tuple([*facts, *inferred, *unknowns]),
                        producer_origin="catalyst_deterministic",
                    )
                    wiki_handoff = "HANDOFF_BLOCKED_BY_PRODUCER_SCHEMA"
            else:
                result_type = "AssetCandidate"
                asset_skills = [skills_by_id[item] for item in active_target_ids if item in {"understand-asset-inspector", "understand-repository-map"}]
                candidates = []
                for asset_skill in asset_skills:
                    if asset_skill.skill_id == "understand-asset-inspector":
                        scoped_sources = [(path, rel) for path, rel in selected_sources if path.name.casefold() == "skill.md"]
                    else:
                        scoped_sources = [(path, rel) for path, rel in selected_sources if path.suffix.casefold() == ".py"]
                    if not scoped_sources:
                        continue
                    scoped_records = tuple(item for item in source_records if any(item.relative_path == rel for _, rel in scoped_sources))
                    scoped_ids = {item.source_id for item in scoped_records}
                    scoped_evidence = {(source_id, locator): ref for (source_id, locator), ref in evidence_by_locator.items() if source_id in scoped_ids}
                    begin(asset_skill, combined_source_digest)
                    candidate, asset_facts, unresolved = self._inspect_asset(scoped_sources, scoped_records, scoped_evidence, root)
                    candidates.append(candidate)
                    facts.extend(asset_facts)
                    unknowns.extend(unresolved)
                    receipts.append(StrategyRunReceipt(asset_skill.skill_id, asset_skill.version, asset_skill.skill_sha256, asset_skill.strategy_id, "COMPLETED", len(asset_facts) + len(unresolved), "bounded_asset_inspection"))
                    end(asset_skill, status="success", attributes={"status": f"asset_type={candidate.asset_type};source_sha256={combined_source_digest}"})
                if not candidates:
                    unknowns.append(_new_item("unknown", "asset_source", "No supported Skill or Python source matched the selected asset strategy.", (), evidence_class="unresolved", uncertainty="unsupported_asset_source"))
                elif len(candidates) == 1:
                    asset_candidate = candidates[0]
                else:
                    asset_candidate = AssetCandidateOutput(
                        "asset_bundle", "selected assets", candidates[0].relative_path,
                        _sha("\n".join(item.source_sha256 for item in candidates).encode("utf-8")),
                        description="Multiple read-only asset inspection strategies were composed.",
                        declared_tools=tuple(sorted({value for item in candidates for value in item.declared_tools})),
                        dependencies=tuple(sorted({value for item in candidates for value in item.dependencies})),
                        entrypoints=tuple(sorted({value for item in candidates for value in item.entrypoints})),
                        effects=tuple(sorted({value for item in candidates for value in item.effects})),
                        reference_paths=tuple(sorted({value for item in candidates for value in item.reference_paths})),
                        script_paths=tuple(sorted({value for item in candidates for value in item.script_paths})),
                    )

            coverage_tested = "understand-evidence-coverage" in skills_by_id
            coverage_skill = skills_by_id.get("understand-evidence-coverage")
            if coverage_skill is not None:
                begin(coverage_skill, combined_source_digest)
            coverage = (
                () if route.requested_depth == "inventory"
                else _coverage(
                    intent,
                    facts,
                    unknowns,
                    warnings,
                    known_evidence_ids={item.evidence_id for item in evidence},
                    tested=coverage_tested,
                )
            )
            if coverage_skill is not None:
                receipts.append(StrategyRunReceipt(coverage_skill.skill_id, coverage_skill.version, coverage_skill.skill_sha256, coverage_skill.strategy_id, "COMPLETED", len(coverage), "evidence_and_relation_coverage"))
            if warnings and not unit_records and all(item.startswith("UNSUPPORTED") for item in warnings):
                status = "UNSUPPORTED"
            else:
                status = "PARTIAL" if skipped_skill_ids or warnings or any(row.status != "ANSWERED" for row in coverage) else "COMPLETE"
            if intent is UnderstandIntent.KNOWLEDGE_PROPOSE and not request.scope_id:
                status = "NEEDS_CONTEXT"
            if coverage_skill is not None:
                end(coverage_skill, status=status.casefold(), attributes={
                "status": (
                    f"result_type={result_type};result_status={status};source_count={len(source_records)};"
                    f"source_sha256={combined_source_digest};"
                    f"coverage_answered={sum(row.status == 'ANSWERED' for row in coverage)};"
                    f"coverage_unresolved={sum(row.status == 'EXPLICITLY_UNRESOLVED' for row in coverage)};"
                    f"coverage_not_tested={sum(row.status == 'NOT_TESTED' for row in coverage)};"
                    f"wiki_handoff={wiki_handoff}"
                ),
                "result_sha256": _sha(json.dumps({
                    "request_id": request.request_id,
                    "result_type": result_type,
                    "status": status,
                    "source_sha256": combined_source_digest,
                    "coverage": [(row.question_id, row.status) for row in coverage],
                }, sort_keys=True).encode("utf-8")),
            })
            for skill_id in skipped_skill_ids:
                strategy_id = _SKILL_STRATEGIES[skill_id][0]
                receipts.append(StrategyRunReceipt(skill_id, "", "", strategy_id, "SKIPPED_BUDGET", 0, "strategy_budget_exhausted"))
            result = UnderstandingResult(
                version="0.2.0",
                request_id=request.request_id,
                intent=intent,
                result_type=result_type,
                status=status,
                route=route,
                source_inventory=source_records,
                evidence_refs=evidence,
                extracted_facts=tuple(facts),
                inferred_items=tuple(inferred),
                unknowns=tuple(unknowns),
                task_context=task_context,
                document_knowledge=document_knowledge,
                semantic_candidate=semantic_candidate,
                asset_candidate=asset_candidate,
                selected_skills=skills,
                coverage_receipt=coverage,
                strategy_run_receipt=tuple(receipts),
                stopping_reason=(
                    "strategy_budget_exhausted" if skipped_skill_ids
                    else "inventory_only_by_request" if route.requested_depth == "inventory"
                    else "source_or_coverage_boundary" if status == "PARTIAL"
                    else "bounded_complete"
                ),
                wiki_handoff=wiki_handoff,
                source_warnings=warnings,
            )
            if semantic_provider is not None and semantic_candidate is not None:
                if skipped_skill_ids or "understand-enterprise-semantics" not in active_skill_ids:
                    raise ValueError("semantic extraction requires the completed bounded method plan")
                if request.revision:
                    if dict(request.revision).get("stopping_reason") == "revision_limit_reached":
                        # The answer was already repaired up to the bound. Asking again
                        # would be a third attempt on the same evidence, so nothing is sent.
                        raise ValueError("the revision limit is reached; no further answer is requested")
                    result = replace(result, revision=dict(request.revision))
                extracted = self._extract_with_provider(result, semantic_provider, source_root=root,
                                                       recorder=recorder, concepts=concepts,
                                                       identity_decisions=identity_decisions)
                if verifier_provider is None:
                    # No verifier ran, so there is no verdict: silence is recorded as N/A
                    # rather than left to be read as approval.
                    return replace(extracted, producer_attribution={
                        **extracted.producer_attribution,
                        "verification": {
                            "status": "NOT_RUN",
                            "verdict": None,
                            "reason": "no independent verifier was supplied",
                            "authority": "review_only_not_evaluation_or_owner_receipt",
                        }})
                # A second reading by a separate model, on the same evidence and with no
                # view of the method or prompt that produced the candidate.
                verification = verify_candidate(extracted, verifier_provider,
                                                goal=request.message, recorder=recorder)
                return replace(extracted, producer_attribution={
                    **extracted.producer_attribution, "independent_verification": verification})
            return result
        except Exception:
            if recorder is not None:
                for skill_id, span_id in spans.items():
                    try:
                        recorder.end_span(span_id, status="failure", attributes={"catalyst.error.code": "understand_strategy_failed"})
                    except (RuntimeError, ValueError):
                        pass
            raise

    def verify_freshness(self, result: UnderstandingResult, *, source_root: Path | str) -> str:
        root = Path(source_root).expanduser().resolve()
        try:
            paths = _walk_sources(tuple(root / item.relative_path for item in result.source_inventory), root)
            current = {relative: _sha(path.read_bytes()) for path, relative in paths}
        except (OSError, PermissionError, ValueError):
            return "STALE"
        expected = {item.relative_path: item.source_sha256 for item in result.source_inventory}
        return "FRESH" if current == expected else "STALE"

    @staticmethod
    def _empty_result(request: UnderstandingRequest, route: IntentRoute, status: str, result_type: str, stopping_reason: str, *, warnings: tuple[str, ...] = ()) -> UnderstandingResult:
        return UnderstandingResult(
            version="0.1.0", request_id=request.request_id, intent=route.intent, result_type=result_type,
            status=status, route=route, stopping_reason=stopping_reason, source_warnings=warnings,
            wiki_handoff="NOT_REQUESTED",
        )

def route_understand_request(
    message: str,
    *,
    requested_intent: UnderstandIntent | str | None = None,
    selected_paths: Sequence[Path | str] = (),
    requested_depth: str | None = None,
    budget_steps: int | None = None,
) -> IntentRoute:
    """Route only the task destination; actor, scope, and permissions come from the host."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be non-empty text")
    if requested_intent is not None:
        intent = UnderstandIntent(requested_intent)
        reason = "host_requested_intent"
    else:
        text = message.casefold()
        asset_ask = any(term in text for term in ("skill", "技能", "agent repo", "代码库", "仓库")) and any(
            term in text for term in ("检查", "分析", "理解", "inspect", "review", "梳理")
        )
        knowledge_ask = any(term in text for term in ("企业知识候选", "沉淀企业知识", "提议企业知识", "企业语义候选"))
        knowledge_ask = knowledge_ask or (
            any(term in text for term in ("组织语义", "企业本体", "ontology", "本体建模"))
            and any(term in text for term in ("整理", "提取", "建立", "形成", "保存", "建模"))
        )
        if asset_ask:
            intent, reason = UnderstandIntent.ASSET_INSPECT, "explicit_asset_inspection_goal"
        elif knowledge_ask:
            intent, reason = UnderstandIntent.KNOWLEDGE_PROPOSE, "explicit_knowledge_proposal_goal"
        else:
            intent, reason = UnderstandIntent.TASK_USE, "default_task_use"
    if intent is UnderstandIntent.KNOWLEDGE_PROPOSE:
        target = "SEMANTIC_CANDIDATE"
    elif intent is UnderstandIntent.ASSET_INSPECT:
        target = "ASSET_CANDIDATE"
    elif any(term in message.casefold() for term in ("项目纪要", "会议纪要", "员工纪要", "任务纪要")):
        target = "PROJECT_GROUNDED_CLAIMS"
    else:
        target = "TASK_CONTEXT" if selected_paths else "TASK_DELIVERY"
    default_depth = "semantic" if intent is UnderstandIntent.KNOWLEDGE_PROPOSE else "targeted"
    depth = _normalize_depth(requested_depth or default_depth)
    budget = 4 if budget_steps is None else budget_steps
    if type(budget) is not int or not 1 <= budget <= 64:
        raise ValueError("budget_steps must be an integer between 1 and 64")
    return IntentRoute(intent, target, reason, depth, budget)

_DEPTH_ALIASES = {
    "inventory_only": "inventory",
    "targeted_structural": "targeted",
    "grounded_semantic": "semantic",
}

_ALLOWED_DEPTHS = {"inventory", "targeted", "semantic", "bounded_deep"}

def _normalize_depth(value: str) -> str:
    depth = _DEPTH_ALIASES.get(str(value).strip().casefold(), str(value).strip().casefold())
    if depth not in _ALLOWED_DEPTHS:
        raise ValueError(f"unsupported Understand depth: {value}")
    return depth
