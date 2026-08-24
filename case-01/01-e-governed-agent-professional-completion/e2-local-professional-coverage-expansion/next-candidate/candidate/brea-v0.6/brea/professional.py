from __future__ import annotations

from pathlib import Path
from typing import Any

from .applicability import LEVEL_COLUMN, applicability_for_question, resolve_semantic_applicability
from .corpus import line_range, norm, page_of, table_region
from .coverage import extract_full_clause
from .domain_data import fact_descriptors, standard_meta
from .evidence import assert_verbatim, locate_clause, locate_table_row, make_evidence_item
from .facts import FACT_LABELS, missing_facts
from .result import build_result
from .semantic import derive_semantic_view
from .uncertainty import Uncertainty, decide


def _source_meta(knowledge: dict, standard_id: str) -> tuple[str, str, str]:
    return standard_meta(knowledge, standard_id)


def _trace(
    semantic_view: dict | None = None,
    applicability: dict | None = None,
    numeric: dict | None = None,
    table: dict | None = None,
    source_fidelity: bool = False,
    provenance_complete: bool = False,
    contract: dict[str, str] | None = None,
    knowledge_info: dict | None = None,
) -> dict[str, Any]:
    knowledge_info = knowledge_info or {}
    return {
        "path": "generic_professional",
        "knowledge_revision_id": knowledge_info.get("revision_id"),
        "knowledge_revision_sha256": knowledge_info.get("sha256"),
        "semantic_view": semantic_view or {"scope": {}, "conditions": {}, "numeric": None},
        "applicability": applicability or {"owner": "SEAM-02", "state": "unresolved"},
        "numeric": numeric,
        "table": table or {},
        "evidence_binding": {
            "source_fidelity": source_fidelity,
            "provenance_complete": provenance_complete,
        },
        "professional_contract": contract or {
            f"PC-{index:02d}": "PASS" for index in range(1, 8)
        },
    }


def _closed(
    request_id: str,
    status: str,
    conclusion: str,
    uncertainty: Uncertainty,
    attribution: dict,
    corpus_sha: dict,
    trace: dict,
    out_dir: Path | None,
    standard_id: str | None = None,
    knowledge_info: dict | None = None,
) -> Any:
    return build_result(
        request_id, status, conclusion, [], [], uncertainty, attribution, corpus_sha,
        out_dir=out_dir, query_mode="QMODE-05", standard_id=standard_id,
        professional_trace=trace, knowledge_info=knowledge_info,
    )


def _retrieve_clause(route: dict, corpora: dict, knowledge: dict) -> tuple[list, str, dict] | None:
    corpus = corpora.get(route["standard_id"])
    if corpus is None:
        return None
    if route["kind"] == "conditional_rule":
        found = extract_full_clause(corpus, route["locator"])
        evidence_type = "numbered_subitem"
    else:
        found = locate_clause(corpus, route["locator"])
        evidence_type = "normative_clause"
    if found is None:
        return None
    source_id, title, version = _source_meta(knowledge, route["standard_id"])
    locator = (
        f"第{route['locator']}条（OCR 副本 [page {found['page']}]，"
        f"本地副本行 {found['start'] + 1}-{found['end']}）"
    )
    item = make_evidence_item(source_id, title, version, locator, evidence_type, found["text"], "supports")
    assert_verbatim(corpus, item.evidence_content)
    return [item], found["text"], {"source_id": source_id, "locator": locator, "raw": found["text"]}


def _retrieve_table(route: dict, corpora: dict, facts: dict, chain: dict, knowledge: dict) -> tuple[list, str, dict] | None:
    corpus = corpora.get(route["standard_id"])
    level = chain.get("level")
    if corpus is None or level is None:
        return None
    caption = route["table_caption"]
    found = locate_table_row(corpus, caption, facts.get("building_category"),
                             float(facts["floor_area_m2"]), 5)
    if found is None:
        return None
    column = LEVEL_COLUMN.get(level)
    if column is None or column >= len(found["raw_values"]):
        return None
    source_id, title, version = _source_meta(knowledge, route["standard_id"])
    level_caption = route["level_resolution"]["caption"]
    region = table_region(corpus, level_caption)
    start, end = line_range(corpus, level_caption, len(region.split("\n")))
    row_content = "\n".join([found["label"]] + found["raw_values"])
    item_level = make_evidence_item(
        source_id, title, version,
        f"{level_caption}（OCR 副本 [page {page_of(corpus, start - 1)}]，本地副本行 {start}-{end}）",
        "table_value", region, "supports",
    )
    item_row = make_evidence_item(
        source_id, title, version,
        f"{caption}（OCR 副本 [page {found['page']}]，本地副本行 {found['start']}-{found['end']}），行：{found['label']}",
        "table_value", row_content, "supports",
    )
    assert_verbatim(corpus, item_level.evidence_content)
    assert_verbatim(corpus, item_row.evidence_content)
    raw = region + "\n" + row_content
    selected = norm(found["raw_values"][column])
    return [item_level, item_row], raw, {
        "source_id": source_id,
        "locator": item_row.locator,
        "raw": raw,
        "raw_row_values": found["raw_values"],
        "normalized_row_values": [norm(value) for value in found["raw_values"]],
        "selected_value": float(selected),
        "selected_column": level,
    }


def _numeric_trace(view: dict, applicability: dict, facts: dict) -> dict | None:
    numeric = view.get("numeric")
    if not numeric:
        return None
    operands = numeric.get("operands", [])
    modifiers = applicability.get("modifiers", [])
    if not operands:
        return None
    operand = operands[0]
    if operand.get("kind") == "source_rule_value":
        outcome = (applicability.get("rule") or {}).get("outcome") or {}
        base = outcome.get("value")
        if base is None:
            return None
        formula = str(base)
        result = float(base)
        for modifier in modifiers:
            if modifier.get("operator") != "multiply":
                return None
            result *= float(modifier["value"])
            formula += f" * {modifier['value']}"
        return {
            "source_operand": {"kind": "source_rule_value", "value": base, "source_rule": outcome.get("source_rule")},
            "source_modifiers": modifiers,
            "formula": formula,
            "result": result,
            "source_evidence_bound": True,
        }
    if operand.get("kind") == "fact":
        fact = operand.get("fact")
        if fact not in facts:
            return None
        result = float(facts[fact])
        formula = fact
        for modifier in modifiers:
            if modifier.get("operator") != "multiply":
                return None
            result *= float(modifier["value"])
            formula += f" * {modifier['value']}"
        return {
            "source_operand": {"kind": "fact", "fact": fact, "value": facts[fact]},
            "source_modifiers": modifiers,
            "formula": formula,
            "result": result,
            "source_evidence_bound": True,
        }
    return None


def _conclusion(route: dict, applicability: dict, numeric: dict | None, table: dict) -> str:
    outcome = (applicability.get("rule") or {}).get("outcome") or {}
    if route["kind"] == "table_rule":
        return (
            f"按 {table['source_id']} {route['level_resolution']['caption']}"
            f"（城市类别 → 指标级别 {table['selected_column']}）与源表行，"
            f"{route['conclusion_subject']}不应小于 {table['selected_value']:g} {route['conclusion_unit']}。"
        )
    value = numeric["result"] if numeric else outcome.get("value")
    if outcome.get("effect") == "minimum":
        return f"{route['subject']}不应小于 {value:g}m。"
    if outcome.get("effect") == "maximum":
        return f"{route['subject']}不应大于 {value:g} m²。"
    return f"{route['subject']}：{outcome.get('target', '')}。"


def answer_professional(
    request_id: str,
    question: str,
    facts: dict,
    corpora: dict,
    attribution: dict,
    corpus_sha: dict,
    out_dir: Path | None,
    knowledge: dict,
    knowledge_info: dict,
) -> Any:
    chain = applicability_for_question(question, facts, corpora, knowledge)
    route = chain.get("route")
    if route is not None:
        required = set(chain.get("required_facts") or route.get("required_facts", []))
        missing = missing_facts(facts, required)
        if missing:
            labels = [FACT_LABELS.get(key, key) for key in missing]
            status, conclusion, uncertainty = decide(labels, chain, bound_ok=False)
            return _closed(request_id, status, conclusion, uncertainty, attribution, corpus_sha,
                           _trace(applicability={"owner": "SEAM-02", "state": "unresolved", "missing": labels}, knowledge_info=knowledge_info),
                           out_dir, chain.get("standard_id"), knowledge_info)
    if route is None or not chain.get("standard_id"):
        status, conclusion, uncertainty = decide([], chain, bound_ok=False)
        return _closed(request_id, status, conclusion, uncertainty, attribution, corpus_sha,
                       _trace(applicability={"owner": "SEAM-02", "state": "unresolved"}, knowledge_info=knowledge_info), out_dir,
                       knowledge_info=knowledge_info)

    retrieved = _retrieve_table(route, corpora, facts, chain, knowledge) if route["kind"] == "table_rule" else _retrieve_clause(route, corpora, knowledge)
    if retrieved is None:
        return _closed(request_id, "no_reliable_evidence", "无法从本地已接纳语料可靠绑定证据，不能给出结论。",
                       Uncertainty(level="explicit", description="证据检索或定位失败"), attribution, corpus_sha,
                       _trace(applicability={"owner": "SEAM-02", "state": "unresolved"}, knowledge_info=knowledge_info), out_dir,
                       chain.get("standard_id"), knowledge_info)

    evidence_items, raw, source = retrieved
    descriptors = fact_descriptors(knowledge)
    semantic_view = derive_semantic_view(facts, raw, route["unit_type"], route, descriptors)
    resolved = resolve_semantic_applicability(semantic_view, facts)
    table = source if route["kind"] == "table_rule" else {}
    numeric = _numeric_trace(semantic_view, resolved, facts) if resolved.get("state") == "applicable" else None
    contract = {
        "PC-01": "PASS" if semantic_view["scope"].get("positive_scope") else "FAIL",
        "PC-02": "PASS" if semantic_view["conditions"].get("rules") else "FAIL",
        "PC-03": "PASS" if resolved.get("owner") == "SEAM-02" else "FAIL",
        "PC-04": "PASS" if semantic_view.get("numeric") is None or numeric is not None else "FAIL",
        "PC-05": "PASS" if source.get("raw") else "FAIL",
        "PC-06": "PASS" if numeric is not None or semantic_view.get("numeric") is None else "FAIL",
        "PC-07": "PASS" if source.get("source_id") and source.get("locator") else "FAIL",
    }
    trace = _trace(
        semantic_view=semantic_view,
        applicability=resolved,
        numeric=numeric,
        table=table,
        source_fidelity=True,
        provenance_complete=all(source.get(key) for key in ("source_id", "locator", "raw")),
        contract=contract,
        knowledge_info=knowledge_info,
    )
    if resolved.get("state") != "applicable":
        return _closed(
            request_id, "no_reliable_evidence",
            "项目事实未能建立该证据单元的正向适用性，不能给出结论或数值。",
            Uncertainty(level="explicit", description=resolved.get("reason", "适用性未解析")),
            attribution, corpus_sha, trace, out_dir, chain.get("standard_id"),
            knowledge_info,
        )
    if semantic_view.get("numeric") is not None and numeric is None:
        return _closed(
            request_id, "no_reliable_evidence", "数值推导所需的源操作数或修正项无法可靠支持，不能给出数值结论。",
            Uncertainty(level="explicit", description="unsupported numeric"), attribution, corpus_sha, trace, out_dir,
            chain.get("standard_id"), knowledge_info,
        )

    conclusion = _conclusion(route, resolved, numeric, table)
    uncertainty = Uncertainty(level="low", description="适用性、证据绑定与专业语义均已解析")
    return build_result(
        request_id, "accepted_with_evidence", conclusion, evidence_items, [], uncertainty,
        attribution, corpus_sha, out_dir=out_dir, query_mode="QMODE-05",
        standard_id=chain.get("standard_id"), professional_trace=trace,
        engine="brea-deterministic-v0.6",
        knowledge_info=knowledge_info,
    )
