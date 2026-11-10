"""Thirteen measurements of what an ontology actually models, read from the Wiki.

The score is a read: it writes no state, opens no model, and costs nothing. Every number
comes from what the Workspace already holds - the items of a candidate or of an accepted
version, and the source text the Wiki can still read back. Two rules keep it honest:

* A metric whose denominator is missing (no entities, no unread declared) reports
  ``value: null`` and fails. Absence is not evidence of quality.
* A metric whose item kind the schema cannot store yet reports zero. Conditions,
  exceptions, actions, constraints and metrics only count once they are their own
  entries, because a sentence that mentions a rule is not a rule.

The thresholds are the ones fixed in ``ONTOLOGY_MODELING_STANDARD_V0.2``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .ontology_concepts import resolve_concept_in
from .ontology_types import declared_counts
from .semantic_wiki import SemanticTransitionError
from .wiki import WikiScopeError, WikiUnavailable

SCHEMA = "catalyst.ontology_score.v0.1"
NAME_MAX_CHARS = 40
BASE64_LIKE = re.compile(r"[A-Za-z0-9+/]{24,}")
ACTION_PREDICATES = frozenset({
    "提交", "复核", "审核", "审批", "批准", "驳回", "放行", "签收", "受理", "归档", "上报",
    "submit", "review", "approve", "reject", "release", "sign", "perform", "performs",
})


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _refs(item: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The evidence rows of one item, whichever shape the version gave it."""
    rows = item.get("evidence")
    if isinstance(rows, (list, tuple)):
        return [row for row in rows if isinstance(row, Mapping)]
    if item.get("source_id"):
        return [item]
    return []


def _span(row: Mapping[str, Any]) -> tuple[str, int, int] | None:
    source_id = row.get("source_id")
    start = row.get("line_start")
    end = row.get("line_end", start)
    if isinstance(source_id, str) and type(start) is int:
        return source_id, start, start if type(end) is not int else end
    return None


def _evidenced(item: Mapping[str, Any]) -> bool:
    return any(_span(row) or row.get("span_sha256") for row in _refs(item))


def _identity(item: Mapping[str, Any]) -> str | None:
    for field in ("canonical_id", "canonical_key", "key"):
        value = item.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def _display_name(item: Mapping[str, Any]) -> str:
    value = item.get("display_name") or item.get("meaning") or item.get("key") or ""
    text = str(value).strip()
    for wrapper in ("「", "」", "“", "”", '"', "'"):
        text = text.strip(wrapper)
    return text.strip()


def _readable(text: str) -> bool:
    if not text or len(text) > NAME_MAX_CHARS:
        return False
    if BASE64_LIKE.search(text):
        return False
    return text.count("（") == text.count("）") and text.count("「") == text.count("」")


def _units(snapshots: Mapping[str, str]) -> list[tuple[str, int]]:
    return [(source_id, number) for source_id, content in snapshots.items()
            for number, line in enumerate(content.splitlines(), 1) if line.strip()]


def _metric(number: int, key: str, name: str, formula: str, *, value, threshold: str,
            passed: bool, note: str, unit: str = "ratio", **extra: Any) -> dict[str, Any]:
    return {"id": number, "key": key, "name": name, "formula": formula, "value": value,
            "unit": unit, "threshold": threshold, "passed": bool(passed), "note": note, **extra}


def score_items(entries: Sequence[Mapping[str, Any]], *,
                sources: Mapping[str, str] | None = None,
                target: Mapping[str, Any] | None = None,
                resolve_type: Callable[[object], str | None] | None = None,
                concept_set_version: str | None = None,
                declarations: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Score one version's or one candidate's items against the thirteen measures.

    ``resolve_type`` is the concept set of the scope the entries belong to: a type counts
    when that scope holds it, not when the pack of the standard happens to. A spelling the
    scope has retired still counts, because the entry it types was read under it.

    ``declarations`` is what the scope's concept set declares about its own types
    (``declared_counts``). A declared action, constraint or metric is a modelling decision
    the type layer holds; an instance entry is what a source said. The two are reported
    apart, and a measure that asks whether the ontology models something accepts either,
    because a declared definition is one the reviewer can read without the source text.
    """
    items = [row for row in entries if isinstance(row, Mapping)]
    target = dict(target or {"kind": "candidate", "published": False, "stale": False})
    declared_structure = {
        key: int(declarations[key])
        for key in ("attributes", "relations", "constraints", "actions", "metrics")
        if isinstance(declarations, Mapping) and isinstance(declarations.get(key), int)
    }
    declared_of = lambda key: declared_structure.get(key, 0)  # noqa: E731 - one lookup, two uses
    snapshots = dict(sources or {})
    counts: dict[str, int] = {}
    for row in items:
        counts[str(row.get("kind"))] = counts.get(str(row.get("kind")), 0) + 1
    entities = [row for row in items if row.get("kind") == "entity"]
    relations = [row for row in items if row.get("kind") == "relation"]
    unknown = [row for row in items if row.get("kind") == "unknown"]
    metrics: list[dict[str, Any]] = []

    bound = sum(1 for row in items if _evidenced(row))
    metrics.append(_metric(
        1, "evidence_binding", "证据绑定率", "带证据的条目 / 全部条目",
        value=_ratio(bound, len(items)), threshold="= 100%",
        passed=bool(items) and bound == len(items),
        note=f"{bound}/{len(items)} 条带来源与 span"))

    holding = resolve_type or (
        lambda value: value if isinstance(value, str) and value.strip() else None)
    typed = [row for row in entities if holding(row.get("business_type") or row.get("entity_type"))]
    metrics.append(_metric(
        2, "typed_entities", "类型化率", "带本 scope 概念集内类型的实体 / 实体",
        value=_ratio(len(typed), len(entities)), threshold="≥ 90%",
        passed=bool(entities) and len(typed) / len(entities) >= 0.9,
        note=(f"{len(typed)}/{len(entities)} 个实体带概念集内的 business_type"
              + (f"（概念集 {concept_set_version}）" if concept_set_version else "")
              if entities else "没有实体可评")))

    density = _ratio(len(relations), len(entities))
    metrics.append(_metric(
        3, "relation_density", "关系密度", "关系条目 / 实体条目",
        value=density, threshold="≥ 1.0",
        passed=density is not None and density >= 1.0,
        note=(f"{len(relations)} 条关系 / {len(entities)} 个实体" if entities
              else "没有实体，关系密度无从计算")))

    for number, kind, key, name in (
        (4, "condition", "condition_items", "条件成条"),
        (5, "exception", "exception_items", "例外成条"),
    ):
        rows = [row for row in items if row.get("kind") == kind]
        kept = sum(1 for row in rows if _evidenced(row))
        metrics.append(_metric(
            number, key, name, f"带证据的 {kind} 条目数",
            value=kept, threshold="≥ 1 条", unit="count", passed=kept >= 1,
            note=f"{kept} 条；门槛先要求成条，覆盖率等原文条件句可数时再升级"))

    units = _units(snapshots)
    covered: set[tuple[str, int]] = set()
    for row in items:
        for ref in _refs(row):
            span = _span(ref)
            if span is None:
                continue
            source_id, start, end = span
            if source_id not in snapshots:
                continue
            covered.update((source_id, number) for number in range(start, end + 1))
    covered &= set(units)
    coverage = _ratio(len(covered), len(units))
    metrics.append(_metric(
        6, "unit_coverage", "单元覆盖率", "被条目引用的源行 / 源的非空行",
        value=coverage, threshold="= 100%",
        passed=coverage is not None and coverage >= 1.0,
        note=(f"{len(covered)}/{len(units)} 行有代表；源不可读时为 null"
              if units else "没有可读的源，无法计算")))

    touched: set[str] = set()
    for row in relations:
        for field in ("canonical_subject_id", "canonical_object_id"):
            value = row.get(field)
            if isinstance(value, str) and value:
                touched.add(value)
        for field in ("subject", "object"):
            value = row.get(field)
            if isinstance(value, str) and value:
                touched.add(value)
                touched.add(value.lstrip("@"))
    identities = {_identity(row) for row in entities} - {None}
    orphans = [row for row in entities if _identity(row) not in touched]
    isolated = _ratio(len(orphans), len(entities))
    metrics.append(_metric(
        7, "isolated_entities", "孤立实体率", "无关系触到的实体 / 实体",
        value=isolated, threshold="≤ 30%",
        passed=isolated is not None and isolated <= 0.3,
        note=(f"{len(orphans)}/{len(entities)} 个实体没有任何关系；被关系触到的身份 {len(identities & touched)}"
              if entities else "没有实体可评")))

    declared = [row for row in unknown
                if str(row.get("evidence_class") or "") == "unresolved"
                and str(row.get("meaning") or "").strip()]
    explicit = _ratio(len(declared), len(unknown))
    metrics.append(_metric(
        8, "unread_explicit", "未读显式率", "写明缺什么的 unresolved 条目 / unknown 条目",
        value=explicit, threshold="= 100%",
        passed=explicit is not None and explicit >= 1.0,
        note=f"{len(declared)}/{len(unknown)} 条 unknown 写明缺什么；没有 unknown 时为 null"))

    readable = [row for row in entities if _readable(_display_name(row))]
    names = _ratio(len(readable), len(entities))
    metrics.append(_metric(
        9, "readable_names", "命名可读率", "可读实体名 / 实体",
        value=names, threshold="= 100%",
        passed=names is not None and names >= 1.0,
        note=(f"{len(readable)}/{len(entities)} 个实体名可读（≤ {NAME_MAX_CHARS} 字、无长串编码、括号成对）"
              if entities else "没有实体可评")))

    published = bool(target.get("published"))
    stale = bool(target.get("stale"))
    trace = 1.0 if published and not stale else (0.5 if published else 0.0)
    metrics.append(_metric(
        10, "version_traceability", "版本可追溯", "被评分内容是已接受且当前生效的版本",
        value=trace, threshold="= 1.0",
        passed=trace >= 1.0,
        note=("已接受且处于头部" if trace >= 1.0 else
              ("已接受但已被更新版本取代" if stale else "候选从未发布"))))

    actions = [row for row in items if row.get("kind") == "action"]
    actions += [row for row in relations
                if str(row.get("predicate") or "").strip().casefold() in ACTION_PREDICATES]
    declared_actions = declared_of("actions")
    metrics.append(_metric(
        11, "action_coverage", "动作成条", "动作条目数 + 谓词为动作动词的关系数 + 概念集声明的动作数",
        value=len(actions) + declared_actions, threshold="≥ 1 条", unit="count",
        passed=len(actions) + declared_actions >= 1,
        note=f"{len(actions)} 条实例 + {declared_actions} 条类型声明；动作覆盖率的分母在原文动作句上",
        instance_value=len(actions), declared_value=declared_actions))

    constraints = [row for row in items if row.get("kind") == "constraint"]
    declared_constraints = declared_of("constraints")
    metrics.append(_metric(
        12, "constraints", "约束数", "constraint 条目数 + 概念集声明的约束数",
        value=len(constraints) + declared_constraints, threshold="≥ 5 条", unit="count",
        passed=len(constraints) + declared_constraints >= 5,
        note=f"{len(constraints)} 条实例 + {declared_constraints} 条类型声明；含「必须」的句子不算",
        instance_value=len(constraints), declared_value=declared_constraints))

    definitions = [row for row in items if row.get("kind") == "metric"]
    declared_metrics = declared_of("metrics")
    metrics.append(_metric(
        13, "metric_definitions", "指标定义数", "metric 条目数 + 概念集声明的指标数",
        value=len(definitions) + declared_metrics, threshold="≥ 1 条", unit="count",
        passed=len(definitions) + declared_metrics >= 1,
        note=f"{len(definitions)} 条实例 + {declared_metrics} 条类型声明",
        instance_value=len(definitions), declared_value=declared_metrics))

    passed = [row for row in metrics if row["passed"]]
    return {
        "schema": SCHEMA,
        "target": target,
        "item_counts": dict(sorted(counts.items())),
        "declared_structure": dict(sorted(declared_structure.items())),
        "metric_count": len(metrics),
        "passed": len(passed),
        "failed": [row["id"] for row in metrics if not row["passed"]],
        "score": round(len(passed) / len(metrics), 4) if metrics else 0.0,
        "metrics": metrics,
    }


def _resolve(state: Mapping[str, Any], candidate_id: str | None, version_id: str | None) -> dict[str, Any]:
    accepted = state.get("accepted_versions") or {}
    candidates = state.get("candidates") or {}
    active = state.get("active_version_id")
    if version_id is not None:
        if version_id not in accepted:
            raise SemanticTransitionError("accepted_version_not_found",
                                          "the version to score is not an accepted semantic version")
        return {"kind": "version", "version_id": version_id, "candidate_id": accepted[version_id].get("candidate_id"),
                "active_version_id": active, "published": True, "stale": active != version_id,
                "entries": list((accepted[version_id].get("meanings") or {}).values())}
    if candidate_id is not None:
        if candidate_id not in candidates:
            raise SemanticTransitionError("candidate_not_found", "the candidate to score does not exist")
        return {"kind": "candidate", "candidate_id": candidate_id, "version_id": None,
                "active_version_id": active, "published": False, "stale": False,
                "entries": list(candidates[candidate_id].get("entries") or ())}
    if isinstance(active, str) and active in accepted:
        return _resolve(state, None, active)
    if len(candidates) == 1:
        return _resolve(state, next(iter(candidates)), None)
    if not candidates:
        raise SemanticTransitionError("score_target_missing", "this scope holds no candidate and no accepted version")
    raise SemanticTransitionError(
        "score_target_ambiguous",
        "this scope holds several candidates and no active version; name one with --candidate-id")


def score_wiki(wiki, *, candidate_id: str | None = None, version_id: str | None = None) -> dict[str, Any]:
    """Score the active version, or one named candidate or accepted version."""
    state = wiki.semantic_state()
    resolved = _resolve(state, candidate_id, version_id)
    entries = resolved.pop("entries")
    wanted = {span[0] for row in entries for ref in _refs(row) if (span := _span(ref))}
    snapshots: dict[str, str] = {}
    unreadable: list[str] = []
    for source_id in sorted(wanted):
        try:
            snapshot = wiki.source_snapshot(source_id)
        except (WikiScopeError, WikiUnavailable, OSError):
            unreadable.append(source_id)
            continue
        content = snapshot.get("content")
        if isinstance(content, str):
            snapshots[source_id] = content
    # The scope's own concept set is what "typed" means here: it is read once, and a
    # retired concept still types the entries that were read under it.
    concepts = wiki.concept_set()
    concept_state = wiki.concept_state()
    declarations = declared_counts(concepts.concepts)

    def resolve_type(value: object) -> str | None:
        concept = resolve_concept_in(concept_state, value)
        return concept.concept_id if concept is not None else None

    report = {
        "workspace": str(Path(getattr(wiki, "workspace", ".")).expanduser()),
        "scope_id": getattr(wiki, "scope_id", None),
        "concept_set": {"version_id": concepts.version_id, "origin": concepts.origin,
                        "concept_count": len(concepts.concepts), "declarations": declarations},
        **score_items(entries, sources=snapshots, target=resolved, resolve_type=resolve_type,
                      concept_set_version=concepts.version_id, declarations=declarations),
        "unreadable_sources": unreadable,
    }
    return report


def write_report(report: Mapping[str, Any], path) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n")
    return target
