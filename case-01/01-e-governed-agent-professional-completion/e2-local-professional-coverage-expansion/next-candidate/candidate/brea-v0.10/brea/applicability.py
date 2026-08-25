"""SEAM-02 — Regulation Applicability (DOMAIN-OWNED MEANING; FN-03).

Standard identity / edition / jurisdiction / level resolution. The applicability
chain is observable (OBL-02) and traced from the admitted corpus (Table 5.0.1).
"""
from __future__ import annotations

import unicodedata

from .corpus import Corpus, extract_level_scope, norm
from .domain_data import match_route, routes

# Local parking table column order: three level columns followed by internal/external columns.
LEVEL_COLUMN: dict[str, int] = {"I": 0, "II": 1, "Ⅲ": 2, "ⅢI": 2, "III": 2}


def resolve_level(dbj: Corpus, city_class: str, knowledge: dict, caption: str | None = None) -> str | None:
    caption = caption or next(
        route["level_resolution"]["caption"]
        for route in routes(knowledge)
        if route.get("level_resolution", {}).get("caption")
    )
    for label, scope in extract_level_scope(dbj, caption):
        if norm(scope) == norm(city_class):
            return label
    return None


def level_column(dbj: Corpus, level: str, caption: str) -> int | None:
    """Return the source-table column index for a level label."""
    labels = [label for label, _scope in extract_level_scope(dbj, caption)]
    try:
        return labels.index(level)
    except ValueError:
        return None


def canonical_level_label(level: str) -> str:
    """Normalize a source label without changing its source-derived meaning."""
    return unicodedata.normalize("NFKC", level)


def applicability_for_question(
    question: str,
    facts: dict,
    dbj: Corpus | dict | None,
    knowledge: dict,
    regulation_context: dict | None = None,
) -> dict:
    """Observable applicability chain. Domain meaning; never numeric authority."""
    chain: dict = {"standard_id": None, "reason": [], "level": None}
    matched = match_route(question, facts, dbj, knowledge, regulation_context)
    if matched is not None and matched.get("route") is not None:
        route = matched["route"]
        chain.update({
            "standard_id": matched["standard_id"],
            "route": route,
            "kind": route["kind"],
            "locator": route["locator"],
            "required_facts": route.get("required_facts", []),
            "level": matched.get("level"),
        })
        if matched["standard_id"] is None:
            chain["reason"].append("声明式法域条件未匹配已接纳规范")
        elif route.get("level_resolution") and matched.get("level") is None:
            chain["reason"].append("声明式级别条件无法从源表解析")
        else:
            chain["reason"].append("声明式专业路由已解析")
        return chain
    if matched and matched.get("ambiguous"):
        chain["reason"].append("多个声明式专业路由同分，拒绝任意选择")
    else:
        chain["reason"].append("未能识别控制事项")
    return chain


def _predicate(facts: dict, predicate: dict) -> bool | None:
    fact = predicate["fact"]
    op = predicate["op"]
    if op == "exists":
        return fact in facts and facts[fact] not in (None, "")
    if fact not in facts or facts[fact] in (None, ""):
        return None
    actual = facts[fact]
    expected = predicate.get("value")
    if op == "contains":
        return str(expected) in str(actual)
    if op == "in":
        return any(str(actual) == str(value) or str(value) in str(actual) for value in expected)
    if op == "between":
        if not isinstance(actual, (int, float)):
            return False
        minimum = predicate.get("min")
        maximum = predicate.get("max")
        if minimum is None or maximum is None:
            return False
        return minimum <= actual <= maximum
    if op == "equals":
        return actual == expected
    if op == "not_equals":
        return actual != expected
    raise ValueError(f"unsupported SEAM-02 predicate operator: {op}")


def _all(facts: dict, predicates: list[dict]) -> bool | None:
    unresolved = False
    for predicate in predicates:
        result = _predicate(facts, predicate)
        if result is False:
            return False
        if result is None:
            unresolved = True
    return None if unresolved else True


def resolve_semantic_applicability(semantic_view: dict, facts: dict) -> dict:
    """SEAM-02 owner for the ephemeral semantic view."""
    scope = semantic_view.get("scope") or {}
    conditions = semantic_view.get("conditions") or {}
    positive = _all(facts, scope.get("positive_scope", []))
    if positive is not True:
        return {"state": "unresolved" if positive is None else "not_applicable",
                "owner": "SEAM-02", "reason": "positive scope unresolved or mismatched"}
    for exception in scope.get("exceptions", []):
        result = _predicate(facts, exception)
        if result is True:
            return {"state": "excluded", "owner": "SEAM-02", "reason": "explicit exception applies"}
        if result is None:
            return {"state": "unresolved", "owner": "SEAM-02", "reason": "exception unresolved"}

    matched = None
    for rule in conditions.get("rules", []):
        result = _all(facts, rule.get("all", []))
        if result is True:
            matched = rule
            break
        if result is None:
            return {"state": "unresolved", "owner": "SEAM-02", "reason": "material condition unresolved"}
    if matched is None:
        return {"state": "not_applicable", "owner": "SEAM-02", "reason": "no material condition matched"}
    modifiers: list[dict] = []
    for modifier_rule in conditions.get("modifier_rules", []):
        result = _all(facts, modifier_rule.get("all", []))
        if result is None:
            return {"state": "unresolved", "owner": "SEAM-02", "reason": "modifier condition unresolved"}
        if result is True:
            modifiers.extend(modifier_rule.get("modifiers", []))
    seam02 = conditions.get("seam02", {})
    if seam02.get("owner") != "SEAM-02":
        return {"state": "unresolved", "owner": "SEAM-02", "reason": "semantic view ownership mismatch"}
    return {
        "state": "applicable",
        "owner": "SEAM-02",
        "reason": "positive scope, conditions, and exceptions resolved",
        "rule": matched,
        "modifiers": modifiers,
        "basis": {
            "scope": scope.get("positive_scope", []),
            "exceptions": scope.get("exceptions", []),
            "conditions": matched.get("all", []),
            "seam": "SEAM-02",
        },
    }
