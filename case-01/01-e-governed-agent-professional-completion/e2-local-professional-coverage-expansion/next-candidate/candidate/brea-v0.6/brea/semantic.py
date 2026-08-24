"""Private, ephemeral professional semantic view.

The view is derived from the retrieved evidence unit and local descriptors. It is
never persisted as a RegulationUnit and it contains no answer-specific Gold value.
"""
from __future__ import annotations

import re
from typing import Any

from .coverage import extract_numeric_rules, parse_numbered_items


SEMANTIC_VIEW_KEYS = ("scope", "conditions", "numeric")
_EXCEPTION_RE = re.compile(r"除(.{0,160}?)外")
_NUMBER_RE = re.compile(r"(\d+(?:\s*\.\s*\d+)?)")
_VALUE_RE = re.compile(r"(\d+(?:\s*\.\s*\d+)?)\s*m(?:²|2)?")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MULTIPLIER_RE = re.compile(r"(增加|提高|按)\s*(\d+(?:\s*\.\s*\d+)?)\s*倍")


def _clean_number(value: str) -> float:
    return float(value.replace(" ", ""))


def _matches(actual: Any, expected: str) -> bool:
    value = str(actual or "")
    return expected in value or value in expected


def _predicates_for_text(
    text: str,
    facts: dict[str, Any],
    descriptors: dict[str, Any],
    fact_names: list[str],
) -> list[dict[str, Any]]:
    text = re.sub(r"\s+", "", text)
    predicates: list[dict[str, Any]] = []
    for fact in fact_names:
        actual = facts.get(fact)
        if actual in (None, ""):
            continue
        values = descriptors.get(fact, {}).get("value_terms", {})
        raw_matched = [
            value for value, terms in values.items()
            if any(term in text for term in terms)
        ]
        matched = [
            value for value in raw_matched
            if _matches(actual, value)
        ] or raw_matched
        if not matched:
            continue
        if len(matched) == 1:
            predicates.append({"fact": fact, "op": "contains", "value": matched[0]})
        else:
            predicates.append({"fact": fact, "op": "in", "value": matched})
    return predicates


def _scope(
    raw: str,
    facts: dict[str, Any],
    route: dict[str, Any],
    descriptors: dict[str, Any],
) -> dict[str, Any]:
    raw = re.sub(r"\s+", "", raw)
    positive: list[dict[str, Any]] = []
    for fact, terms in route.get("scope_terms", {}).items():
        actual = facts.get(fact)
        if actual in (None, "") or not any(term in raw for term in terms):
            continue
        values = descriptors.get(fact, {}).get("value_terms", {})
        matched = [value for value in values if _matches(actual, value) and any(term in raw for term in values[value])]
        if matched:
            positive.append({"fact": fact, "op": "contains", "value": matched[0]})
        elif values:
            raw_values = [value for value in values if any(term in raw for term in values[value])]
            positive.append({"fact": fact, "op": "contains", "value": raw_values[0] if raw_values else terms[0]})
        else:
            positive.append({"fact": fact, "op": "exists"})

    exceptions: list[dict[str, Any]] = []
    exception_text = _EXCEPTION_RE.search(raw)
    if exception_text:
        segment = exception_text.group(1)
        for fact, terms in route.get("exception_terms", {}).items():
            values = descriptors.get(fact, {}).get("value_terms", {})
            for value, value_terms in values.items():
                linked = any(
                    term in segment and (_matches(value, term) or any(term in item for item in value_terms))
                    for term in terms
                )
                if linked and _matches(facts.get(fact), value):
                    exceptions.append({"fact": fact, "op": "contains", "value": value})
    return {
        "subject": route.get("subject", "professional regulation subject"),
        "positive_scope": positive,
        "exceptions": exceptions,
    }


def _direct_outcome(raw: str) -> dict[str, Any] | None:
    raw = re.sub(r"\s+", "", raw)
    marker_effects = (
        ("不应小于", "minimum"),
        ("不应大于", "maximum"),
        ("不得", "prohibit"),
        ("应设置", "requirement"),
        ("应至少", "requirement"),
    )
    for marker, effect in marker_effects:
        position = raw.find(marker)
        if position < 0:
            continue
        prefix = re.split(r"[。；\n]", raw[:position])[-1].strip(" ：:，,")
        tail = re.split(r"[。；\n]", raw[position + len(marker):], maxsplit=1)[0].strip(" ：:，,")
        value_match = _VALUE_RE.search(tail)
        if value_match:
            value = _clean_number(value_match.group(1))
            unit = "m"
            target = prefix or tail[:value_match.start()].strip(" ：:，,")
            return {"effect": effect, "target": target, "value": value, "unit": unit}
        return {"effect": effect, "target": tail or prefix}
    return None


def _conditional_rules(
    raw: str,
    facts: dict[str, Any],
    route: dict[str, Any],
    descriptors: dict[str, Any],
) -> list[dict[str, Any]]:
    items = parse_numbered_items(raw)
    rules: list[dict[str, Any]] = []
    for item in items:
        for extracted in extract_numeric_rules(item["text"]):
            predicates = _predicates_for_text(
                extracted["condition"], facts, descriptors, route.get("condition_facts", [])
            )
            if not predicates:
                continue
            rules.append({
                "all": predicates,
                "outcome": {
                    "effect": "maximum",
                    "target": route.get("subject", "professional regulation subject"),
                    "value": extracted["value"],
                    "unit": "m²",
                    "source_rule": extracted["condition"],
                },
            })
    return rules


def _table_values(raw: str) -> dict[str, Any]:
    raw_values = re.findall(r"\d+\s*\.\s*\d+", raw)
    return {
        "raw_values": raw_values,
        "numeric_values": [_clean_number(value) for value in raw_values],
    }


def _modifier_rules(
    raw: str,
    facts: dict[str, Any],
    route: dict[str, Any],
    descriptors: dict[str, Any],
) -> list[dict[str, Any]]:
    compact = re.sub(r"\s+", "", raw)
    matches = list(_MULTIPLIER_RE.finditer(compact))
    percent_matches = list(_PERCENT_RE.finditer(compact))
    output: list[dict[str, Any]] = []
    fact_names = route.get("modifier_condition_facts", [])
    for match in matches + percent_matches:
        start = max((compact.rfind(mark, 0, match.start()) for mark in ("。", "；", ";", "\n")), default=-1)
        end_candidates = [compact.find(mark, match.end()) for mark in ("。", "；", ";", "\n")]
        end = min((value for value in end_candidates if value >= 0), default=len(compact))
        segment = compact[start + 1:end]
        predicates = _predicates_for_text(segment, facts, descriptors, fact_names)
        if match in matches:
            amount = _clean_number(match.group(2))
            operator = "multiply"
            value = 1.0 + amount
        else:
            prefix = segment[:segment.find(match.group(0))]
            amount = _clean_number(match.group(1)) / 100.0
            operator = "multiply"
            value = amount if prefix.endswith("按") else 1.0 + amount
        output.append({
            "all": predicates,
            "modifiers": [{"operator": operator, "value": value, "source": match.group(0)}],
        })
    return output


def _numeric(
    raw: str,
    route: dict[str, Any],
    rules: list[dict[str, Any]],
    modifier_rules: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if route.get("kind") == "conditional_rule" and rules:
        return {
            "operands": [{"kind": "source_rule_value", "rule": "matched_condition"}],
            "modifier_rules": modifier_rules,
            "advisory_caps": [],
        }
    operand_terms = route.get("operand_terms", {})
    for fact, terms in operand_terms.items():
        if fact in facts and any(term in raw for term in terms):
            ratio = _PERCENT_RE.search(raw)
            if ratio:
                return {
                    "operands": [{"kind": "fact", "fact": fact}],
                    "modifier_rules": modifier_rules,
                    "advisory_caps": [],
                }
    return None


def derive_semantic_view(
    facts: dict[str, Any],
    raw: str,
    unit_type: str,
    route: dict[str, Any],
    descriptors: dict[str, Any],
) -> dict[str, Any]:
    scope = _scope(raw, facts, route, descriptors)
    rules = _conditional_rules(raw, facts, route, descriptors) if unit_type == "conditional_rule" else []
    if not rules:
        predicates = _predicates_for_text(raw, facts, descriptors, route.get("condition_facts", []))
        for fact in route.get("condition_facts", []):
            if fact in facts and not any(predicate["fact"] == fact for predicate in predicates):
                predicates.append({"fact": fact, "op": "exists"})
        rules = [{"all": predicates, "outcome": _direct_outcome(raw)}]

    if unit_type == "table_rule":
        rules[0]["table_values"] = _table_values(raw)
    modifier_rules = _modifier_rules(raw, facts, route, descriptors)

    return {
        "scope": scope,
        "conditions": {
            "rules": rules,
            "seam02": {"owner": "SEAM-02", "path": ["scope", "conditions", "exceptions"]},
            "source_unit_type": unit_type,
            "modifier_rules": modifier_rules,
        },
        "numeric": _numeric(raw, route, rules, modifier_rules),
    }
