from __future__ import annotations

from typing import Any


def _predicate(facts: dict[str, Any], condition: dict[str, Any]) -> bool | None:
    fact = condition["fact"]
    op = condition["op"]
    if op == "exists":
        return fact in facts
    if fact not in facts:
        return None
    actual = facts[fact]
    expected = condition.get("value")
    if op == "equals":
        return actual == expected
    if op == "not_equals":
        return actual != expected
    if op == "greater_than":
        return actual > expected
    if op == "less_equal":
        return actual <= expected
    raise ValueError(f"unsupported generic predicate operator: {op}")


def _all(facts: dict[str, Any], predicates: list[dict[str, Any]]) -> bool | None:
    unresolved = False
    for predicate in predicates:
        result = _predicate(facts, predicate)
        if result is False:
            return False
        if result is None:
            unresolved = True
    return None if unresolved else True


def _base_ok(base: dict[str, Any] | None, case: dict[str, Any]) -> bool:
    if base is None:
        return False
    source = case["source"]
    return all(
        [
            base.get("id") == source["id"],
            base.get("locator") == source["locator"],
            base.get("raw_evidence") == source["raw_evidence"],
            bool(base.get("sha256")),
        ]
    )


def _applicability(rep: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    scope = rep.get("scope")
    conditions = rep.get("conditions")
    if not scope or not conditions:
        return {"state": "unresolved", "reason": "typed scope or condition representation is absent"}

    scope_match = _all(facts, scope.get("positive_scope", []))
    if scope_match is not True:
        return {"state": "unresolved", "reason": "positive applicability scope is missing, mismatched, or unresolved"}

    for exception in scope.get("exceptions", []):
        exception_match = _predicate(facts, exception)
        if exception_match is True:
            return {"state": "excluded", "reason": "an explicit exception applies"}
        if exception_match is None:
            return {"state": "unresolved", "reason": "exception applicability is unresolved"}

    matched_rule = None
    for rule in conditions.get("rules", []):
        rule_match = _all(facts, rule.get("all", []))
        if rule_match is True:
            matched_rule = rule
            break
        if rule_match is None:
            return {"state": "unresolved", "reason": "material condition is unresolved"}
    if matched_rule is None:
        return {"state": "not_applicable", "reason": "no declarative condition matched"}
    seam02 = conditions.get("seam02", {})
    if seam02.get("owner") != "applicability":
        return {"state": "unresolved", "reason": "SEAM-02 applicability ownership is absent"}
    return {
        "state": "applicable",
        "reason": "positive scope, conditions, exceptions, and SEAM-02 owner resolved",
        "rule": matched_rule,
        "basis": {
            "scope": scope.get("positive_scope", []),
            "exceptions": scope.get("exceptions", []),
            "conditions": matched_rule.get("all", []),
            "seam02": seam02,
        },
    }


def _numeric(rep: dict[str, Any], facts: dict[str, Any], applicable: dict[str, Any]) -> dict[str, Any]:
    numeric = rep.get("numeric")
    if not numeric:
        return {"state": "not_applicable", "trace": None}
    operands = numeric.get("operands", [])
    modifiers = numeric.get("modifiers", [])
    if not operands or not modifiers:
        return {"state": "unsupported", "code": "unsupported_numeric", "trace": None}
    operand = operands[0]
    if operand.get("fact") not in facts:
        return {"state": "unsupported", "code": "unsupported_numeric", "trace": None}
    modifier = modifiers[0]
    if modifier.get("operator") != "multiply":
        return {"state": "unsupported", "code": "unsupported_numeric", "trace": None}
    result = facts[operand["fact"]] * modifier["value"]
    if result != numeric.get("result"):
        return {"state": "invalid", "code": "numeric_trace_mismatch", "trace": None}
    return {
        "state": "supported",
        "trace": {
            "operands": [{"fact": operand["fact"], "value": facts[operand["fact"]]}],
            "modifiers": modifiers,
            "formula": numeric.get("formula"),
            "result": result,
            "advisory_caps": numeric.get("advisory_caps", []),
        },
    }


def validate(case: dict[str, Any], representation: dict[str, Any]) -> dict[str, Any]:
    facts = case["facts"]
    expected = case["expected"]
    base_ok = _base_ok(representation.get("base"), case)
    applicability = _applicability(representation, facts)
    numeric = _numeric(representation, facts, applicability)
    fail_code = None
    conclusion = None
    if applicability["state"] == "applicable":
        conclusion = applicability["rule"].get("outcome")
        if numeric["state"] == "unsupported":
            fail_code = numeric["code"]
            conclusion = None
        elif numeric["state"] == "invalid":
            fail_code = numeric["code"]
            conclusion = None
    elif applicability["state"] == "unresolved":
        fail_code = "unresolved_applicability"

    status = "PASS" if fail_code is None and applicability["state"] == "applicable" else "FAIL_CLOSED"
    if expected.get("status") == "PASS" and status == "PASS" and conclusion != expected.get("outcome"):
        fail_code = "outcome_mismatch"
        status = "FAIL_CLOSED"

    has_scope = bool(representation.get("scope") and representation["scope"].get("positive_scope"))
    has_conditions = bool(representation.get("conditions") and representation["conditions"].get("rules"))
    has_seam02 = bool(
        representation.get("conditions", {}).get("seam02", {}).get("owner") == "applicability"
        if representation.get("conditions")
        else False
    )
    negative_expected = expected.get("status") == "FAIL_CLOSED"
    pc = {
        "PC-01": ("PASS" if (applicability["state"] == "applicable" or (negative_expected and has_scope)) else "FAIL", "positive scope resolved or explicitly represented for closure"),
        "PC-02": ("PASS" if (applicability["state"] == "applicable" or (negative_expected and has_conditions)) else "FAIL", "material conditions resolved or explicitly represented for closure"),
        "PC-03": ("PASS" if (has_seam02 and (applicability["state"] == "applicable" or negative_expected)) else "FAIL", "SEAM-02 applicability ownership observed"),
        "PC-04": ("PASS" if expected.get("numeric_result") is None else "FAIL", "not applicable"),
        "PC-05": ("PASS" if base_ok and has_scope and has_conditions else "FAIL", "evidence is separated from applicability"),
        "PC-06": ("PASS" if ((expected.get("fail_code") == "unsupported_numeric" and fail_code == "unsupported_numeric") or expected.get("fail_code") != "unsupported_numeric") else "FAIL", "unsupported numeric fails closed"),
        "PC-07": ("PASS" if (status == "FAIL_CLOSED" or applicability["state"] == "applicable") else "FAIL", "unresolved applicability or evidence fails closed"),
    }
    if expected.get("numeric_result") is not None:
        pc["PC-04"] = ("PASS" if numeric["state"] == "supported" and numeric["trace"] is not None else "FAIL", "operand, modifier, formula, and result are traced")
    if not base_ok:
        pc["PC-07"] = ("FAIL", "source identity, locator, evidence, or SHA is absent")

    contract_ok = all(value[0] == "PASS" for value in pc.values()) and (
        expected.get("status") == status and (expected.get("outcome") in (None, conclusion))
    )
    return {
        "case_id": case["case_id"],
        "track": representation["track"],
        "status": status,
        "contract_ok": contract_ok,
        "conclusion": conclusion,
        "evidence_trace": {
            "source_id": case["source"]["id"] if base_ok else None,
            "source_sha256": representation.get("base", {}).get("sha256") if base_ok else None,
            "locator": case["source"]["locator"] if base_ok else None,
            "raw_evidence": case["source"]["raw_evidence"] if base_ok else None,
            "applicability_basis": applicability.get("basis"),
            "numeric_trace": numeric.get("trace"),
            "failure_code": fail_code,
        },
        "pc_results": [
            {"id": pc_id, "status": result[0], "reason": result[1]}
            for pc_id, result in pc.items()
        ],
        "diagnostics": {
            "representation_groups": representation.get("groups", []),
            "hidden_knowledge": "not_checked_here",
            "data_only_extension": False,
        },
    }
