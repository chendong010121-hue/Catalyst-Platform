from __future__ import annotations

import re
from typing import Any


SEMANTIC_INTERFACE_KEYS = ("scope", "conditions", "numeric")
_CJK_NUMBER_PAIR = re.compile(r"([\u4e00-\u9fff]{1,12})\s+([0-9]+(?:\.[0-9]+)?)")
_PERCENT = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*%")
_CAP = re.compile(r"(?:不宜|不得|不应|不超过)[^0-9]{0,12}([0-9]+(?:\.[0-9]+)?)\s*个")


def _exception_segment(raw: str) -> str:
    if "除" not in raw or "外" not in raw:
        return ""
    segment = raw.split("除", 1)[1]
    return segment.split("外", 1)[0]


def _scope(facts: dict[str, Any], descriptors: dict[str, Any], raw: str) -> dict[str, Any]:
    positive_scope: list[dict[str, Any]] = []
    for fact, value in facts.items():
        if not isinstance(value, str):
            continue
        terms = descriptors.get(fact, {}).get("scope_terms", [])
        for term in terms:
            if term not in raw:
                continue
            if term == value or term in value or value in term:
                positive_scope.append({"fact": fact, "op": "equals", "value": value})
            else:
                positive_scope.append({"fact": fact, "op": "exists"})
            break
    if not positive_scope and "建筑" in raw:
        for fact, value in facts.items():
            if isinstance(value, str) and descriptors.get(fact, {}).get("scope_terms"):
                positive_scope.append({"fact": fact, "op": "exists"})
                break
    return {"subject": "generic textual subject", "positive_scope": positive_scope, "exceptions": []}


def _conditions(facts: dict[str, Any], descriptors: dict[str, Any], raw: str) -> dict[str, Any]:
    exception_text = _exception_segment(raw)
    main_text = raw.replace(exception_text, "", 1) if exception_text else raw
    exceptions: list[dict[str, Any]] = []
    predicates: list[dict[str, Any]] = []
    for fact, descriptor in descriptors.items():
        value = facts.get(fact)
        terms = descriptor.get("true_terms", [])
        if any(term in exception_text for term in terms):
            exceptions.append({"fact": fact, "op": "equals", "value": True})
        elif isinstance(value, bool) and any(term in main_text for term in terms):
            predicates.append({"fact": fact, "op": "equals", "value": value})
    return {
        "rules": [{"all": predicates}],
        "seam02": {"owner": "applicability", "path": ["scope", "conditions", "exceptions"]},
        "derived_exceptions": exceptions,
    }


def _outcome(raw: str) -> dict[str, str] | None:
    markers = (("不应小于", "minimum"), ("不得", "prohibit"), ("不应", "prohibit"), ("应至少", "requirement"), ("应设置", "requirement"), ("应设在", "requirement"), ("应", "requirement"))
    for marker, effect in markers:
        if marker not in raw:
            continue
        target = raw.split(marker, 1)[1].split("，", 1)[0].split("。", 1)[0].strip()
        return {"effect": effect, "target": target}
    return None


def _numeric(facts: dict[str, Any], descriptors: dict[str, Any], raw: str) -> dict[str, Any] | None:
    operands: list[dict[str, Any]] = []
    for fact, descriptor in descriptors.items():
        if any(term in raw for term in descriptor.get("operand_terms", [])):
            operands.append({"name": fact, "fact": fact})
    ratio = _PERCENT.search(raw)
    if operands and ratio:
        modifiers = [{"name": "percentage", "value": float(ratio.group(1)) / 100, "operator": "multiply"}]
        cap = _CAP.search(raw)
        return {
            "operands": operands,
            "modifiers": modifiers,
            "advisory_caps": ([{"value": float(cap.group(1)), "meaning": "not_preferably_over"}] if cap else []),
        }
    return None


def _table_values(raw: str) -> dict[str, float]:
    return {label: float(value) for label, value in _CJK_NUMBER_PAIR.findall(raw)}


def derive_semantic_view(
    facts: dict[str, Any],
    descriptors: dict[str, Any],
    raw: str,
    unit_type: str,
) -> dict[str, Any]:
    scope = _scope(facts, descriptors, raw)
    conditions = _conditions(facts, descriptors, raw)
    conditions["rules"][0]["outcome"] = _outcome(raw)
    conditions["rules"][0]["values"] = _table_values(raw) if unit_type == "table_rule" else {}
    scope["exceptions"] = conditions.pop("derived_exceptions")
    return {"scope": scope, "conditions": conditions, "numeric": _numeric(facts, descriptors, raw)}
