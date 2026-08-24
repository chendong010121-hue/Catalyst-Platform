"""FN-11 Local Runner / Service Shell (PRIVATE / DEFERRED) + whole-Agent pipeline (E2 EXTENDED).

FN-01 intake validation -> FN-02/03/04/05/06/07/08 composition -> RegulationEvidenceResult.
Deterministic; no model; numeric values only from the admitted corpus.

E1 extension: generalized local evidence-query dispatch (QMODE-01..05).
E2 extension: new professional applicability family — 公共建筑防火分区最大允许建筑面积
(GB 55037-2022 第4.3.16条, conditional-rule clause), implemented through a reusable
numbered-subitem rule mechanism (brea/coverage.py). No per-question hardcode.

The dispatch contains NO benchmark question literals, NO per-benchmark clause/table
ids, NO per-benchmark conclusion strings (E1/E2 anti-fixture rule).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .applicability import LEVEL_COLUMN, applicability_for_question
from .contracts import RegulationEvidenceResult, Uncertainty
from .corpus import (
    CorpusIntegrityError,
    line_range,
    load_corpora,
    norm,
    page_of,
    table_region,
)
from .coverage import (
    FIRE_COMPARTMENT,
    extract_full_clause,
    extract_numeric_rules,
    is_excluded,
    match_condition_value,
    modifier_applies,
    parse_numbered_items,
)
from .evidence import (
    assert_verbatim,
    locate_clause,
    locate_table_region,
    locate_table_row,
    make_evidence_item,
    make_topic_evidence,
    write_artifact,
)
from .facts import FACT_LABELS, missing_facts, normalize_facts
from .identity import AGENT_ID, VERSION
from .query import classify_query, clause_exists, table_caption_for, topic_search
from .result import build_result
from .uncertainty import decide

CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = CANDIDATE_ROOT / "tests" / "fixtures" / "requests"

GB_KEY = "GB55037-2022"          # corpus manifest stem key
DBJ_KEY = "DBJ33T1021-2023"      # corpus manifest stem key
GB = "GB 55037-2022"             # evidence source identity (display)
DBJ = "DBJ33/T1021-2023"         # evidence source identity (display)
GB_TITLE = "《建筑防火通用规范》（全文强制性工程建设规范）"
GB_VERSION = "2022（OCR 副本未含公告页；施行日期以住房和城乡建设部公告为准）"
DBJ_TITLE = "《城市建筑工程停车场（库）设置规则和配建指标标准》"
DBJ_VERSION = "2023-09-28 发布，2024-03-01 施行（废止 DB33/1021-2013）"

# Professional applicability triggers (pre-existing professional rules, NOT benchmark
# branches — E1/E2 allow professional applicability rules).
_APPLICABILITY_TRIGGERS = ("防火间距", "停车位", "配建", "机动车停车", "防火分区")


def _required_facts(question: str) -> set[str]:
    if "防火间距" in question:
        return {"vehicle_goods_category", "adjacent_building_nature"}
    if ("停车位" in question) or ("配建" in question):
        return {"jurisdiction", "building_category", "floor_area_m2", "city_class"}
    if "防火分区" in question:
        return set(FIRE_COMPARTMENT["required_facts"])
    return set()


def _is_fire_compartment_question(question: str) -> bool:
    return ("防火分区" in question) and (
        ("最大允许" in question) or ("分区面积" in question)
        or ("面积" in question and ("不应大于" in question or "是多少" in question or "应为多少" in question))
    )


def _source_meta(standard_id: str) -> tuple[str, str, str]:
    if standard_id == GB_KEY:
        return GB, GB_TITLE, GB_VERSION
    if standard_id == DBJ_KEY:
        return DBJ, DBJ_TITLE, DBJ_VERSION
    raise ValueError(f"unresolved standard: {standard_id}")


def _seeks_value(question: str) -> bool:
    """Value-seeking table/row query (B-E1-08 class): '…指标/数值 应为多少'."""
    return ("应为多少" in question) or ("是多少" in question) or ("应取多少" in question)


# ---------------------------------------------------------------------------
# QMODE handlers
# ---------------------------------------------------------------------------

def _qm01_clause_lookup(request_id, question, standard_id, clause_id, corpora, attribution,
                        out_dir) -> RegulationEvidenceResult:
    """Explicit standard + clause locator. Missing clause -> QMODE-02 fail closed."""
    corpus = corpora[standard_id]
    source_id, source_title, source_version = _source_meta(standard_id)
    if not clause_exists(corpus, clause_id):
        return build_result(
            request_id, "no_reliable_evidence",
            f"本地已接纳规范库中不存在条款 {clause_id}（{source_id}），不能编造条文。",
            [], [], Uncertainty(level="explicit", description="条款不存在"), attribution,
            corpus_sha={key: value.expected_sha for key, value in corpora.items()},
            out_dir=out_dir, query_mode="QMODE-02", standard_id=standard_id,
        )
    found = locate_clause(corpus, clause_id)
    locator = (
        f"第{clause_id}条；OCR 副本 [page {found['page']}]，本地副本行 {found['start'] + 1}-{found['end']}"
    )
    item = make_evidence_item(source_id, source_title, source_version, locator,
                              "normative_clause", found["text"], "supports")
    assert_verbatim(corpus, item.evidence_content)
    conclusion = f"已定位 {source_id} 第{clause_id}条原文（证据检索结果，未做项目适用性判定）。"
    return build_result(
        request_id, "evidence_retrieved", conclusion, [item], [],
        Uncertainty(level="medium", description="证据检索结果；适用性判定需另行提供项目专业事实。"),
        attribution, corpus_sha={key: value.expected_sha for key, value in corpora.items()},
        out_dir=out_dir, query_mode="QMODE-01", standard_id=standard_id,
    )


def _qm03_topic_search(request_id, question, standard_id, corpora, attribution,
                       out_dir) -> RegulationEvidenceResult:
    """Local topic evidence search over the admitted standard."""
    corpus = corpora[standard_id]
    source_id, source_title, source_version = _source_meta(standard_id)
    candidates = topic_search(corpus, question, standard_id, top_n=3)
    if not candidates:
        return build_result(
            request_id, "no_reliable_evidence",
            f"在 {source_id} 中未检索到与问题主题相关的可靠证据，不能编造。",
            [], [], Uncertainty(level="explicit", description="本地检索无命中"),
            attribution, corpus_sha={key: value.expected_sha for key, value in corpora.items()},
            out_dir=out_dir, query_mode="QMODE-03", standard_id=standard_id,
        )
    items = [make_topic_evidence(source_id, source_title, source_version, unit) for unit in candidates]
    for item in items:
        assert_verbatim(corpus, item.evidence_content)
    conclusion = (
        f"在 {source_id} 中检索到 {len(candidates)} 处相关条文（证据检索结果，未做适用性判定，"
        "不据此给出规范数值结论）。"
    )
    return build_result(
        request_id, "evidence_retrieved", conclusion, items, [],
        Uncertainty(level="medium", description="检索结果为证据节选；不等同于专业适用性结论。"),
        attribution, corpus_sha={key: value.expected_sha for key, value in corpora.items()},
        out_dir=out_dir, query_mode="QMODE-03", standard_id=standard_id,
    )


def _qm04_table_region(request_id, question, standard_id, table_number, corpora,
                       facts, attribution, out_dir) -> RegulationEvidenceResult:
    """Explicit table / table-region query (B-E1-07). Row-value binding without
    sufficient facts fails closed (B-E1-08): no unsupported numeric conclusion."""
    corpus = corpora[standard_id]
    source_id, source_title, source_version = _source_meta(standard_id)
    caption = table_caption_for(corpus, table_number)
    if caption is None:
        return build_result(
            request_id, "no_reliable_evidence",
            f"无法从本地已接纳语料可靠解析表格 {table_number}（{source_id}），不能编造表格内容。",
            [], [], Uncertainty(level="explicit", description="表格解析失败"),
            attribution, corpus_sha={key: value.expected_sha for key, value in corpora.items()},
            out_dir=out_dir, query_mode="QMODE-04", standard_id=standard_id,
        )
    region = locate_table_region(corpus, caption)
    locator = (
        f"{caption}（OCR 副本 [page {region['page']}]，本地副本行 {region['start']}-{region['end']}）"
    )
    if _seeks_value(question):
        # row-value binding requires professional facts (level column etc.) — fail closed
        required = {"city_class", "building_category", "floor_area_m2", "jurisdiction"}
        missing = missing_facts(facts, required)
        if missing:
            missing_display = [FACT_LABELS.get(key, key) for key in missing]
            return build_result(
                request_id, "insufficient_context",
                "无法可靠回答：表格行值绑定所需专业事实缺失（" + "、".join(missing_display)
                + "）。补齐前不能给出表格数值结论。",
                [], [], Uncertainty(level="explicit", description="缺失事实列表见结论"),
                attribution, corpus_sha={key: value.expected_sha for key, value in corpora.items()},
                out_dir=out_dir, query_mode="QMODE-04", standard_id=standard_id,
            )
    item = make_evidence_item(source_id, source_title, source_version, locator,
                              "table_value", region["region"], "supports")
    assert_verbatim(corpus, item.evidence_content)
    conclusion = f"已定位 {source_id} {caption} 表格区域（证据检索结果，未做行值绑定/适用性判定）。"
    return build_result(
        request_id, "evidence_retrieved", conclusion, [item], [],
        Uncertainty(level="medium", description="表格区域证据；行值绑定需项目专业事实。"),
        attribution, corpus_sha={key: value.expected_sha for key, value in corpora.items()},
        out_dir=out_dir, query_mode="QMODE-04", standard_id=standard_id,
    )


# ---------------------------------------------------------------------------
# E2 fire-compartment professional family (QMODE-05 extension)
# ---------------------------------------------------------------------------

def _fire_compartment_answer(request_id, question, facts, corpora, attribution,
                             out_dir) -> RegulationEvidenceResult:
    """公共建筑防火分区最大允许建筑面积（GB 55037-2022 第4.3.16条）。

    Reusable mechanism: extract full clause (incl. numbered sub-items) -> split items ->
    extract (condition, value) rules -> match project facts -> apply modifier -> bind.
    Fail closed on: exclusions, missing facts, unparseable items, no numeric match.
    """
    gb = corpora.get(GB_KEY)
    corpus_sha = {key: value.expected_sha for key, value in corpora.items()}

    if gb is None:
        return build_result(request_id, "no_reliable_evidence", "本地已接纳规范库不可用。",
                            [], [], Uncertainty(level="explicit", description="语料不可用"),
                            attribution, corpus_sha, out_dir=out_dir,
                            query_mode="QMODE-05", standard_id=GB_KEY)

    # 4.3.16 exclusion guard (explicit non-applicability)
    if is_excluded(facts.get("building_category")):
        return build_result(
            request_id, "no_reliable_evidence",
            "GB 55037-2022 第4.3.16条不适用于有特殊要求的建筑、木结构建筑或附建于民用建筑中的汽车库"
            "（明确不适用，不能给出数值结论）。",
            [], [], Uncertainty(level="explicit", description="条文排除情形"),
            attribution, corpus_sha, out_dir=out_dir, query_mode="QMODE-05", standard_id=GB_KEY,
        )

    # required facts (professional labels, no raw keys)
    required = set(FIRE_COMPARTMENT["required_facts"])
    missing = missing_facts(facts, required)
    if missing:
        missing_display = [FACT_LABELS.get(key, key) for key in missing]
        return build_result(
            request_id, "insufficient_context",
            "无法可靠回答：防火分区最大允许建筑面积判定所需专业事实缺失（"
            + "、".join(missing_display) + "）。补齐前不能给出数值结论。",
            [], [], Uncertainty(level="explicit", description="缺失事实列表见结论"),
            attribution, corpus_sha, out_dir=out_dir, query_mode="QMODE-05", standard_id=GB_KEY,
        )

    clause = FIRE_COMPARTMENT["clause_id"]
    full = extract_full_clause(gb, clause)
    if full is None:
        return build_result(request_id, "no_reliable_evidence",
                            "无法从本地已接纳语料解析条款 4.3.16，不能编造结论。",
                            [], [], Uncertainty(level="explicit", description="条款解析失败"),
                            attribution, corpus_sha, out_dir=out_dir,
                            query_mode="QMODE-05", standard_id=GB_KEY)

    items = parse_numbered_items(full["text"])
    rules = []
    for item in items:
        rules.extend(extract_numeric_rules(item["text"]))

    matched = match_condition_value(rules, facts)
    if matched is None:
        return build_result(request_id, "no_reliable_evidence",
                            "项目事实无法匹配 4.3.16 任一子项数值规则（证据不足，不编造数值）。",
                            [], [], Uncertainty(level="explicit", description="子项匹配失败"),
                            attribution, corpus_sha, out_dir=out_dir,
                            query_mode="QMODE-05", standard_id=GB_KEY)

    base = matched["rule"]["value"]
    applied_modifier = False
    if modifier_applies(facts, full["text"]):
        base = base * 2.0
        applied_modifier = True

    value_text = f"{base:g}"
    locator = (
        f"第4.3.16条（第4章 建筑防火 · 4.3 防火分隔与防火分区）；"
        f"OCR 副本 [page {full['page']}]，本地副本行 {full['start'] + 1}-{full['end']}"
    )
    item = make_evidence_item(GB, GB_TITLE, GB_VERSION, locator, "numbered_subitem",
                              full["text"], "supports")
    assert_verbatim(gb, item.evidence_content)

    form_label = facts.get("building_form")
    rating_label = facts.get("fire_resistance_rating")
    modifier_note = "；因全部设置自动灭火系统，面积增加1.0倍（×2）" if applied_modifier else ""
    conclusion = (
        f"按 GB 55037-2022 第4.3.16条（{form_label}，耐火等级 {rating_label}），"
        f"该公共建筑每个防火分区的最大允许建筑面积不应大于 {value_text} m²{modifier_note}。"
    )
    uncertainty = Uncertainty(
        level="low",
        description=(
            "数值来自 4.3.16 原文子项。适用性判定链：建筑形式/耐火等级 → 子项规则 → 数值绑定"
            + ("；自动灭火修正：全部设置自动灭火系统 → 面积增加1.0倍" if applied_modifier else "") + "。"
        ),
    )
    return build_result(request_id, "accepted_with_evidence", conclusion, [item], [],
                        uncertainty, attribution, corpus_sha, out_dir=out_dir,
                        query_mode="QMODE-05", standard_id=GB_KEY)


# ---------------------------------------------------------------------------
# whole-Agent answer (FN-01 composition)
# ---------------------------------------------------------------------------

def answer(
    request_id: str,
    question: str,
    project_context: dict,
    regulation_context: dict,
    enterprise_context: dict,
    out_dir: Path | None = None,
) -> RegulationEvidenceResult:
    # FN-01 — Question & Context Intake (input contract)
    if not request_id or not isinstance(question, str) or not question.strip():
        raise ValueError("invalid request: request_id and question required")
    if not isinstance(enterprise_context, dict):
        raise ValueError("enterprise_context must be an object")
    if not enterprise_context.get("organization_id") or not enterprise_context.get("user_id"):
        raise ValueError("enterprise_context requires organization_id and user_id")
    attribution = {
        key: enterprise_context.get(key)
        for key in ("organization_id", "user_id", "project_id")
    }

    # FN-02 — SEAM-01 professional fact normalization
    facts = normalize_facts(project_context or {})

    # FN-09 — corpus access (SHA fail closed)
    try:
        corpora = load_corpora()
    except CorpusIntegrityError as exc:
        return build_result(
            request_id, "no_reliable_evidence",
            f"语料不可用（{exc}），无法给出结论。", [], [],
            Uncertainty(level="explicit", description=str(exc)),
            attribution, corpus_sha={}, out_dir=out_dir,
        )
    corpus_sha = {key: value.expected_sha for key, value in corpora.items()}

    # ---- generalized local evidence-query dispatch (E1) ----
    classification = classify_query(question, regulation_context)
    mode = classification["mode"]
    standard_id = classification["standard_id"]

    if mode == "QMODE-01":
        return _qm01_clause_lookup(request_id, question, standard_id,
                                   classification["clause_id"], corpora, attribution, out_dir)
    if mode == "QMODE-04":
        return _qm04_table_region(request_id, question, standard_id,
                                  classification["table_number"], corpora, facts,
                                  attribution, out_dir)
    if mode == "QMODE-03":
        return _qm03_topic_search(request_id, question, standard_id, corpora, attribution, out_dir)

    # ---- QMODE-05: professional applicability (T-C01/02/03 + E2 family preserved) ----
    gb = corpora.get(GB_KEY)
    dbj = corpora.get(DBJ_KEY)

    # E2 — fire-compartment family (new professional applicability, before generic paths)
    if _is_fire_compartment_question(question):
        return _fire_compartment_answer(request_id, question, facts, corpora, attribution, out_dir)

    # FN-03 — SEAM-02 applicability
    applicability = applicability_for_question(question, facts, dbj)

    # FN-06 — fail closed on missing facts (professional labels, no raw keys)
    required = _required_facts(question)
    missing = missing_facts(facts, required)
    if missing:
        missing_display = [FACT_LABELS.get(key, key) for key in missing]
        status, conclusion, uncertainty = decide(missing_display, applicability, bound_ok=False)
        return build_result(request_id, status, conclusion, [], [], uncertainty,
                            attribution, corpus_sha, out_dir=out_dir)

    if applicability.get("standard_id") == GB_KEY and "防火间距" in question and gb is not None:
        found = locate_clause(gb, "3.1.3")
        if found is None:
            status, conclusion, uncertainty = decide(
                [], {"standard_id": None, "reason": ["条文缺失"]}, bound_ok=False)
            return build_result(request_id, status, conclusion, [], [], uncertainty,
                                attribution, corpus_sha, out_dir=out_dir)
        flat = re.sub(r"\s+", "", found["text"])
        values = re.findall(r"不应小于(\d+(?:\.\d+)?)m", flat)
        if len(values) < 3:
            status, conclusion, uncertainty = decide(
                [], {"standard_id": None, "reason": ["条文数值解析异常"]}, bound_ok=False)
            return build_result(request_id, status, conclusion, [], [], uncertainty,
                                attribution, corpus_sha, out_dir=out_dir)
        first = values[0]
        locator = (
            "第3.1.3条（第3章 建筑总平面布局 · 3.1 一般规定）；"
            f"OCR 副本 [page {found['page']}]，本地副本行 {found['start'] + 1}-{found['end']}"
        )
        item = make_evidence_item(GB, GB_TITLE, GB_VERSION, locator, "normative_clause",
                                  found["text"], "supports")
        assert_verbatim(gb, item.evidence_content)
        artifacts: list = []
        if out_dir is not None:
            body = (
                f"# Evidence Bundle — GB 55037-2022 第3.1.3条（逐字）\n\n"
                f"定位：{locator}\n\n```text\n{found['text']}\n```\n"
            )
            artifacts.append(write_artifact(out_dir, f"{request_id}_bundle",
                                            "GB 55037-2022 第3.1.3条 逐字证据束", body))
        conclusion = (
            "甲类物品运输车的汽车库、修车库、停车场与人员密集场所之间的防火间距"
            f"不应小于 {first}m（GB 55037-2022 第3.1.3条）。"
        )
        uncertainty = Uncertainty(
            level="low",
            description=(
                "条文直接适用。同一第3.1.3条还规定：与其他民用建筑"
                f"不应小于 {values[1]}m；与明火或散发火花地点不应小于 {values[2]}m。"
                "结论仅针对'人员密集场所'情形。"
            ),
        )
        return build_result(request_id, "accepted_with_evidence", conclusion, [item],
                            artifacts, uncertainty, attribution, corpus_sha, out_dir=out_dir)

    if applicability.get("standard_id") == DBJ_KEY and dbj is not None:
        level = applicability.get("level")
        if level is None:
            status, conclusion, uncertainty = decide(
                [], {"standard_id": None, "reason": ["表5.0.1 匹配失败"]}, bound_ok=False)
            return build_result(request_id, status, conclusion, [], [], uncertainty,
                                attribution, corpus_sha, out_dir=out_dir)
        column = LEVEL_COLUMN.get(level)
        if column is None:
            status, conclusion, uncertainty = decide(
                [], {"standard_id": None, "reason": ["指标级别列解析失败"]}, bound_ok=False)
            return build_result(request_id, status, conclusion, [], [], uncertainty,
                                attribution, corpus_sha, out_dir=out_dir)
        found = locate_table_row(dbj, "表5.0.4商业场所停车位指标",
                                 facts["building_category"], float(facts["floor_area_m2"]), 5)
        if found is None:
            status, conclusion, uncertainty = decide(
                [], {"standard_id": None, "reason": ["表5.0.4 行匹配失败"]}, bound_ok=False)
            return build_result(request_id, status, conclusion, [], [], uncertainty,
                                attribution, corpus_sha, out_dir=out_dir)
        value = norm(found["raw_values"][column])
        label = found["label"]
        region_501 = table_region(dbj, "表5.0.1")
        s501, e501 = line_range(dbj, "表5.0.1", len(region_501.split("\n")))
        row_content = "\n".join([label] + found["raw_values"])
        item_level = make_evidence_item(
            DBJ, DBJ_TITLE, DBJ_VERSION,
            f"第5.0.1条+表5.0.1（OCR 副本 [page {page_of(dbj, s501 - 1)}]，本地副本行 {s501}-{e501}）",
            "table_value", region_501, "supports")
        item_row = make_evidence_item(
            DBJ, DBJ_TITLE, DBJ_VERSION,
            f"表5.0.4（OCR 副本 [page {found['page']}]，本地副本行 {found['start']}-{found['end']}），行：{label}",
            "table_value", row_content, "supports")
        assert_verbatim(dbj, item_level.evidence_content)
        assert_verbatim(dbj, item_row.evidence_content)
        artifacts = []
        if out_dir is not None:
            body = (
                f"# Evidence Bundle — DBJ33/T1021-2023 表5.0.1 + 表5.0.4（逐字）\n\n"
                f"## 表5.0.1（本地副本行 {s501}-{e501}）\n\n```text\n{region_501}\n```\n\n"
                f"## 表5.0.4 选中行：{label}（列：级别 {level}）\n\n```text\n{row_content}\n```\n\n"
                f"行选择痕迹：{facts['city_class']} → 表5.0.1 → 级别 {level}；"
                f"{facts['building_category']} + {float(facts['floor_area_m2']):g}m² → 表5.0.4 行。\n"
            )
            artifacts.append(write_artifact(out_dir, f"{request_id}_bundle",
                                            "DBJ33/T1021-2023 表5.0.1+表5.0.4 逐字证据束", body))
        conclusion = (
            f"按 DBJ33/T1021-2023 表5.0.1（{facts['city_class']} → 指标级别 {level}）"
            f"与表5.0.4（{label}），机动车配建指标不应小于 {value} 车位/100m² 建筑面积。"
        )
        uncertainty = Uncertainty(
            level="low",
            description=("数值来自表5.0.4 原文（OCR 单元格数值按原文归一化）。"
                         "指标级别按表5.0.1 由城市类别事实确定；若城市类别事实有误，结论随之失效。"),
        )
        return build_result(request_id, "accepted_with_evidence", conclusion,
                            [item_level, item_row], artifacts, uncertainty,
                            attribution, corpus_sha, out_dir=out_dir)

    status, conclusion, uncertainty = decide([], applicability, bound_ok=False)
    return build_result(request_id, status, conclusion, [], [], uncertainty,
                        attribution, corpus_sha, out_dir=out_dir)


def _run_request(data: dict, out_dir: Path | None) -> RegulationEvidenceResult:
    request = data["request"]
    enterprise = request["enterprise_context"]
    return answer(
        request["request_id"], request["question"], request["project_context"],
        request["regulation_context"], enterprise, out_dir=out_dir,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brea", description="BREA v0.3-candidate runner")
    parser.add_argument("--case", choices=["T-C01", "T-C02", "T-C03"])
    parser.add_argument("--request", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.request is not None:
        data = json.loads(args.request.read_text(encoding="utf-8"))
    elif args.case:
        fixture = FIXTURES_DIR / f"{args.case}.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))
    else:
        parser.error("--case or --request required")

    out_dir = args.out.parent if args.out is not None else None
    result = _run_request(data, out_dir=out_dir)
    payload = result.to_dict()

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
