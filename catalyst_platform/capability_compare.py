"""Compare two capability claims field by field, without deciding which is better.

The comparator produces a *relation hypothesis*: are these the same capability,
two implementations of one responsibility, two different duties, or two halves
of one job?  It never produces "better".  ``SUPERSEDES`` is deliberately absent
from its output vocabulary: superiority is a behavioural property and may only
come from an actual evaluation on a shared basis.

Everything here is deterministic: the same two claims give the same result and
the same digest, with no model, no network and no writes.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable, Mapping

from .capability_state import (
    COMPLEMENTARY,
    DISTINCT,
    IGNORE_DUPLICATE,
    KEEP_BOTH,
    NEEDS_HUMAN_REVIEW,
    REPLACE,
    SAME,
    SIMILAR,
    EVALUATE_IN_DEVELOPMENT,
    COMPARISON_UNKNOWN,
)
from .capability_claim import BEHAVIOURAL, comparability_for, validate_claim

# A duty found in one claim counts as covered by the other at or above this
# bigram overlap.  Fixed, documented and testable rather than tuned per case.
MATCH_THRESHOLD = 0.7

_ITEM_GROUPS = (
    ("what.obligations", ("what", "obligations")),
    ("what.inputs", ("what", "inputs")),
    ("what.outputs", ("what", "outputs")),
    ("what.applicability.include", ("what", "applicability", "include")),
    ("what.applicability.exclude", ("what", "applicability", "exclude")),
    ("what.known_limits", ("what", "known_limits")),
    ("what.failure_modes", ("what", "failure_modes")),
    ("how.side_effects", ("how", "side_effects")),
    ("how.permissions", ("how", "permissions")),
)


def normalize(text: str) -> str:
    """Case-fold, unify, and drop punctuation and whitespace (CJK safe)."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[^\w]+", "", folded, flags=re.UNICODE)


def bigrams(text: str) -> set[str]:
    value = normalize(text)
    if len(value) < 2:
        return {value} if value else set()
    return {value[index:index + 2] for index in range(len(value) - 1)}


def similarity(left: str, right: str) -> float:
    """Character-bigram Jaccard; language-agnostic and stable."""
    a, b = bigrams(left), bigrams(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 4)


def _items(claim: Mapping[str, Any], path: tuple[str, ...]) -> list[str]:
    value: Any = claim
    for key in path:
        if not isinstance(value, Mapping):
            return []
        value = value.get(key)
    if not isinstance(value, list):
        return []
    return [item.get("statement", "") for item in value if isinstance(item, Mapping)]


def _match(left: list[str], right: list[str]) -> tuple[list[tuple[int, int, float]], list[int], list[int]]:
    """Greedy best-match of left items onto right items, above the threshold."""
    pairs: list[tuple[int, int, float]] = []
    used: set[int] = set()
    for left_index, left_text in enumerate(left):
        best_index, best_score = -1, 0.0
        for right_index, right_text in enumerate(right):
            if right_index in used:
                continue
            score = similarity(left_text, right_text)
            if score > best_score:
                best_index, best_score = right_index, score
        if best_index >= 0 and best_score >= MATCH_THRESHOLD:
            used.add(best_index)
            pairs.append((left_index, best_index, best_score))
    matched_left = {index for index, _, _ in pairs}
    left_only = [index for index in range(len(left)) if index not in matched_left]
    right_only = [index for index in range(len(right)) if index not in used]
    return pairs, left_only, right_only


def _field_rows(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Per-field comparison rows; behavioural fields are never compared."""
    rows: list[dict[str, Any]] = []

    def add(path: str, left_value: Any, right_value: Any) -> None:
        level = comparability_for(path)
        row = {
            "field": path,
            "comparability": level,
            "left_present": left_value is not None,
            "right_present": right_value is not None,
        }
        if level == BEHAVIOURAL:
            row["comparable"] = False
            row["note"] = "behaviour is measured, never compared from text"
        else:
            row["comparable"] = True
            row["same"] = normalize(str(left_value)) == normalize(str(right_value)) if left_value is not None and right_value is not None else None
        rows.append(row)

    add("capability.id", left["capability"]["id"], right["capability"]["id"])
    add("capability.responsibility_key", left["capability"]["responsibility_key"], right["capability"]["responsibility_key"])
    add("capability.version", left["capability"]["version"], right["capability"]["version"])
    add("capability.kind", left["capability"]["kind"], right["capability"]["kind"])
    add("capability.statement", left["capability"]["statement"], right["capability"]["statement"])
    add("how.interface", left["how"]["interface"], right["how"]["interface"])
    add("how.entry", left["how"]["entry"], right["how"]["entry"])
    add("quick_start", left["quick_start"], right["quick_start"])

    for name, path in _ITEM_GROUPS:
        left_items, right_items = _items(left, path), _items(right, path)
        pairs, left_only, right_only = _match(left_items, right_items)
        rows.append({
            "field": name,
            "comparability": comparability_for(name),
            "comparable": True,
            "left_count": len(left_items),
            "right_count": len(right_items),
            "matched": [{"left": left_items[a], "right": right_items[b], "similarity": score} for a, b, score in pairs],
            "left_only": [left_items[index] for index in left_only],
            "right_only": [right_items[index] for index in right_only],
        })
    return rows


def _relation(left: Mapping[str, Any], right: Mapping[str, Any], rows: list[dict[str, Any]]) -> tuple[str, str]:
    by_field = {row["field"]: row for row in rows}
    same_key = by_field["capability.responsibility_key"]["same"]
    same_id = by_field["capability.id"]["same"]
    same_kind = by_field["capability.kind"]["same"]
    same_interface = by_field["how.interface"]["same"]

    if same_id and not same_key:
        return COMPARISON_UNKNOWN, "同一能力 id 挂着两个不同的职责键：元数据自相矛盾"
    if not same_key:
        return DISTINCT, "职责键不同：两者不构成竞争组"
    if same_id:
        return SAME, "同一 id 与职责键：这是版本问题，不是竞争"
    boundary = _boundary(left, right)
    if boundary is not None:
        return COMPLEMENTARY, boundary
    if same_kind and same_interface:
        return SIMILAR, "同职责、同形态与接口：属于竞争实现"
    if not same_kind:
        return COMPLEMENTARY, "同一职责的两种形态；各管一段，靠适用边界区分"
    return COMPARISON_UNKNOWN, "同职责同形态但接口不同：需要人判断"


def _statements(claim: Mapping[str, Any], section: str) -> list[str]:
    """The declared applicability statements of one side, or nothing at all."""
    items = (claim.get("what") or {}).get("applicability") or {}
    values = items.get(section) if isinstance(items, Mapping) else None
    if not isinstance(values, list):
        return []
    return [item.get("statement", "") for item in values if isinstance(item, Mapping)]


def _mentions(statement: str, capability_id: str) -> bool:
    """A hand-off names the other capability; the id is what identifies it."""
    target = normalize(capability_id)
    return bool(target) and target in normalize(statement)


def _boundary(left: Mapping[str, Any], right: Mapping[str, Any]) -> str | None:
    """An explicitly declared split of the job, which no evaluation has to settle.

    Two capabilities may share a responsibility key and still never be
    alternatives for the same request.  Only a *declared* boundary counts, and it
    must be declared on both sides:

    * each names the other in what it does not cover (a stated hand-off), or
    * both declare where they apply and no declared scope matches the other.

    Empty or unknown applicability is not a boundary: silence is compared as
    silence, and the pair falls through to the form-based rules.
    """
    left_id, right_id = left["capability"]["id"], right["capability"]["id"]
    left_excludes, right_excludes = _statements(left, "exclude"), _statements(right, "exclude")
    if any(_mentions(statement, right_id) for statement in left_excludes) and any(
        _mentions(statement, left_id) for statement in right_excludes
    ):
        return "两侧都在不适用范围里点名对方：这是分工，不是竞争"
    left_includes, right_includes = _statements(left, "include"), _statements(right, "include")
    if left_includes and right_includes and not _match(left_includes, right_includes)[0]:
        return "两侧都声明了适用范围且互不相交：这是分工，不是竞争"
    return None


def _questions(left: Mapping[str, Any], right: Mapping[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    """Turn uncovered duties into evaluation questions, never into verdicts."""
    obligations = next((row for row in rows if row["field"] == "what.obligations"), {})
    questions: list[str] = []
    for statement in obligations.get("left_only", [])[:2]:
        questions.append(f"右侧（{right['capability']['id']}）的声明未覆盖「{statement}」：在同一输入下它是否也会满足？")
    for statement in obligations.get("right_only", [])[:2]:
        questions.append(f"左侧（{left['capability']['id']}）的声明未覆盖「{statement}」：在同一输入下它是否也会满足？")
    return questions[:5]


def _action(relation: str, left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    from .capability_state import compare_action

    if relation == SAME:
        identical = left["capability"]["version"] == right["capability"]["version"]
        return IGNORE_DUPLICATE if identical else REPLACE
    return compare_action(relation)


def _digest(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    from .capability_claim import canonical

    payload = b"|".join(sorted([canonical(left), canonical(right)]))
    return hashlib.sha256(payload).hexdigest()


def compare_claims(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two validated claims; returns a relation hypothesis and its basis."""
    for label, claim in (("left", left), ("right", right)):
        violations = validate_claim(claim)
        if violations:
            raise ValueError(f"{label} claim is not valid: {violations[0]}")

    rows = _field_rows(left, right)
    relation, reason = _relation(left, right, rows)
    action = _action(relation, left, right)
    questions = _questions(left, right, rows) if relation in (SIMILAR, COMPARISON_UNKNOWN) else []

    blocked: list[str] = ["no measurement on a shared basis: superiority is not decidable from claims"]
    if relation == SAME:
        blocked = []
    return {
        "relation": relation,
        "action": action,
        "reason": reason,
        "requires_owner_confirmation": action in (REPLACE, EVALUATE_IN_DEVELOPMENT),
        "blocked": blocked,
        "evaluation_questions": questions,
        "fields": rows,
        "left": {"id": left["capability"]["id"], "version": left["capability"]["version"]},
        "right": {"id": right["capability"]["id"], "version": right["capability"]["version"]},
        "input_digest": _digest(left, right),
    }


def compare_many(candidate: Mapping[str, Any], library: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Compare one incoming claim against every library claim, nearest first."""
    results = [compare_claims(candidate, other) for other in library]
    order = {SAME: 0, SIMILAR: 1, COMPLEMENTARY: 2, COMPARISON_UNKNOWN: 3, DISTINCT: 4}
    return sorted(results, key=lambda item: (order.get(item["relation"], 9), item["input_digest"]))
