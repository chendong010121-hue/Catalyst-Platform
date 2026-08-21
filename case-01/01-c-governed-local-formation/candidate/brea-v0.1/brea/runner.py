"""FN-11 Local Runner / Service Shell (PRIVATE / DEFERRED) + whole-Agent pipeline.

FN-01 intake validation -> FN-02/03/04/05/06/07/08 composition -> RegulationEvidenceResult.
Deterministic; no model; numeric values only from the admitted corpus.
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
from .evidence import (
    assert_verbatim,
    locate_clause,
    locate_table_row,
    make_evidence_item,
    write_artifact,
)
from .facts import FACT_LABELS, missing_facts, normalize_facts
from .identity import AGENT_ID, VERSION
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


def _required_facts(question: str) -> set[str]:
    if "防火间距" in question:
        return {"vehicle_goods_category", "adjacent_building_nature"}
    if ("停车位" in question) or ("配建" in question):
        return {"jurisdiction", "building_category", "floor_area_m2", "city_class"}
    return set()


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
    required = _required_facts(question)
    missing = missing_facts(facts, required)

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
    gb = corpora.get(GB_KEY)
    dbj = corpora.get(DBJ_KEY)
    corpus_sha = {key: value.expected_sha for key, value in corpora.items()}

    # FN-03 — SEAM-02 applicability
    applicability = applicability_for_question(question, facts, dbj)

    # FN-06 — fail closed on missing facts (professional labels, no raw keys)
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
    parser = argparse.ArgumentParser(prog="brea", description="BREA v0.1-candidate runner")
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
