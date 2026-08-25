"""BREA v0.8 deterministic product runner.

The QMODE-01..04 retrieval paths remain the v0.2 generalized local-query
behavior. QMODE-05 has one professional orchestration path; its applicability
meaning is delegated to SEAM-02 and its private semantic view is ephemeral.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .contracts import RegulationEvidenceResult, Uncertainty
from .corpus import CorpusIntegrityError, line_range, load_corpora, norm, page_of, table_region
from .evidence import (
    assert_verbatim,
    locate_clause,
    locate_table_region,
    make_evidence_item,
    make_topic_evidence,
    write_artifact,
)
from .facts import FACT_LABELS, missing_facts, normalize_facts
from .domain_data import standard_meta
from .knowledge import KnowledgeBindingError, load_knowledge_binding
from .professional import answer_professional
from .query import classify_query, clause_exists, table_caption_for, topic_search
from .result import build_result
from .uncertainty import decide


CANDIDATE_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = CANDIDATE_ROOT / "tests" / "fixtures" / "requests"
def implementation_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted((CANDIDATE_ROOT / "brea").glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _source_meta(knowledge: dict, standard_id: str) -> tuple[str, str, str]:
    return standard_meta(knowledge, standard_id)


def _qm01_clause_lookup(request_id, standard_id, clause_id, corpora, attribution, out_dir, knowledge, knowledge_info):
    corpus = corpora[standard_id]
    source_id, title, version = _source_meta(knowledge, standard_id)
    if not clause_exists(corpus, clause_id):
        return build_result(
            request_id, "no_reliable_evidence",
            f"本地已接纳规范库中不存在条款 {clause_id}（{source_id}），不能编造条文。",
            [], [], Uncertainty(level="explicit", description="条款不存在"), attribution,
            {key: value.expected_sha for key, value in corpora.items()}, out_dir=out_dir,
            query_mode="QMODE-02", standard_id=standard_id,
            knowledge_info=knowledge_info,
        )
    found = locate_clause(corpus, clause_id)
    locator = f"第{clause_id}条；OCR 副本 [page {found['page']}]，本地副本行 {found['start'] + 1}-{found['end']}"
    item = make_evidence_item(source_id, title, version, locator, "normative_clause", found["text"], "supports")
    assert_verbatim(corpus, item.evidence_content)
    return build_result(
        request_id, "evidence_retrieved",
        f"已定位 {source_id} 第{clause_id}条原文（证据检索结果，未做项目适用性判定）。",
        [item], [], Uncertainty(level="medium", description="证据检索结果；适用性判定需项目专业事实。"),
        attribution, {key: value.expected_sha for key, value in corpora.items()}, out_dir=out_dir,
        query_mode="QMODE-01", standard_id=standard_id,
        knowledge_info=knowledge_info,
    )


def _qm03_topic_search(request_id, question, standard_id, corpora, attribution, out_dir, knowledge, knowledge_info):
    corpus = corpora[standard_id]
    source_id, title, version = _source_meta(knowledge, standard_id)
    candidates = topic_search(corpus, question, standard_id, knowledge, top_n=3)
    if not candidates:
        return build_result(
            request_id, "no_reliable_evidence", f"在 {source_id} 中未检索到与问题主题相关的可靠证据，不能编造。",
            [], [], Uncertainty(level="explicit", description="本地检索无命中"), attribution,
            {key: value.expected_sha for key, value in corpora.items()}, out_dir=out_dir,
            query_mode="QMODE-03", standard_id=standard_id,
            knowledge_info=knowledge_info,
        )
    items = [make_topic_evidence(source_id, title, version, unit) for unit in candidates]
    for item in items:
        assert_verbatim(corpus, item.evidence_content)
    return build_result(
        request_id, "evidence_retrieved",
        f"在 {source_id} 中检索到 {len(candidates)} 处相关条文（证据检索结果，未做适用性判定，不据此给出规范数值结论）。",
        items, [], Uncertainty(level="medium", description="检索结果为证据节选；不等同于专业适用性结论。"),
        attribution, {key: value.expected_sha for key, value in corpora.items()}, out_dir=out_dir,
        query_mode="QMODE-03", standard_id=standard_id,
        knowledge_info=knowledge_info,
    )


def _seeks_value(question: str) -> bool:
    return any(marker in question for marker in ("应为多少", "是多少", "应取多少"))


def _qm04_table_region(request_id, question, standard_id, table_number, corpora, facts, attribution, out_dir, knowledge, knowledge_info):
    corpus = corpora[standard_id]
    source_id, title, version = _source_meta(knowledge, standard_id)
    caption = table_caption_for(corpus, table_number)
    if caption is None:
        return build_result(
            request_id, "no_reliable_evidence", f"无法从本地已接纳语料可靠解析表格 {table_number}（{source_id}），不能编造表格内容。",
            [], [], Uncertainty(level="explicit", description="表格解析失败"), attribution,
            {key: value.expected_sha for key, value in corpora.items()}, out_dir=out_dir,
            query_mode="QMODE-04", standard_id=standard_id,
            knowledge_info=knowledge_info,
        )
    region = locate_table_region(corpus, caption)
    if _seeks_value(question):
        required = {"city_class", "building_category", "floor_area_m2", "jurisdiction"}
        missing = missing_facts(facts, required)
        if missing:
            labels = [FACT_LABELS.get(key, key) for key in missing]
            return build_result(
                request_id, "insufficient_context", "无法可靠回答：表格行值绑定所需专业事实缺失（" + "、".join(labels) + "）。",
                [], [], Uncertainty(level="explicit", description="缺失事实列表见结论"), attribution,
                {key: value.expected_sha for key, value in corpora.items()}, out_dir=out_dir,
                query_mode="QMODE-04", standard_id=standard_id,
                knowledge_info=knowledge_info,
            )
    locator = f"{caption}（OCR 副本 [page {region['page']}]，本地副本行 {region['start']}-{region['end']}）"
    item = make_evidence_item(source_id, title, version, locator, "table_value", region["region"], "supports")
    assert_verbatim(corpus, item.evidence_content)
    return build_result(
        request_id, "evidence_retrieved", f"已定位 {source_id} {caption} 表格区域（证据检索结果，未做行值绑定/适用性判定）。",
        [item], [], Uncertainty(level="medium", description="表格区域证据；行值绑定需项目专业事实。"), attribution,
        {key: value.expected_sha for key, value in corpora.items()}, out_dir=out_dir,
        query_mode="QMODE-04", standard_id=standard_id,
        knowledge_info=knowledge_info,
    )


def answer(
    request_id: str,
    question: str,
    project_context: dict,
    regulation_context: dict,
    enterprise_context: dict,
    out_dir: Path | None = None,
    knowledge_binding: dict | None = None,
) -> RegulationEvidenceResult:
    if not request_id or not isinstance(question, str) or not question.strip():
        raise ValueError("invalid request: request_id and question required")
    if not isinstance(enterprise_context, dict):
        raise ValueError("enterprise_context must be an object")
    if not enterprise_context.get("organization_id") or not enterprise_context.get("user_id"):
        raise ValueError("enterprise_context requires organization_id and user_id")
    attribution = {key: enterprise_context.get(key) for key in ("organization_id", "user_id", "project_id")}
    try:
        knowledge, knowledge_info = load_knowledge_binding(knowledge_binding)
    except KnowledgeBindingError as exc:
        trace = {
            "path": "knowledge_binding",
            "knowledge_revision_id": None,
            "knowledge_revision_sha256": None,
            "knowledge": {"state": "invalid_binding", "reason": str(exc)},
        }
        return build_result(
            request_id, "no_reliable_evidence", "知识版本绑定无效，不能给出结论。", [], [],
            Uncertainty(level="explicit", description=str(exc)), attribution, {}, out_dir=out_dir,
            query_mode="QMODE-05", professional_trace=trace,
        )
    try:
        facts = normalize_facts(project_context or {})
    except ValueError as exc:
        return build_result(
            request_id,
            "no_reliable_evidence",
            "项目事实格式无效，不能给出结论。",
            [],
            [],
            Uncertainty(level="explicit", description=str(exc)),
            attribution,
            {},
            out_dir=out_dir,
            query_mode="QMODE-05",
            professional_trace={
                "path": "fact_normalization",
                "knowledge_revision_id": knowledge_info["revision_id"],
                "knowledge_revision_sha256": knowledge_info["sha256"],
                "reason": "invalid numeric fact",
            },
            knowledge_info=knowledge_info,
        )
    try:
        corpora = load_corpora(knowledge["sources"])
    except CorpusIntegrityError as exc:
        return build_result(
            request_id, "no_reliable_evidence", f"语料不可用（{exc}），无法给出结论。", [], [],
            Uncertainty(level="explicit", description=str(exc)), attribution, {}, out_dir=out_dir,
            professional_trace={
                "path": "knowledge_binding",
                "knowledge_revision_id": knowledge_info["revision_id"],
                "knowledge_revision_sha256": knowledge_info["sha256"],
                "knowledge": {"state": "source_load_failed", "reason": str(exc)},
            }, knowledge_info=knowledge_info,
        )
    classification = classify_query(question, regulation_context, knowledge)
    mode = classification["mode"]
    if mode == "QMODE-01":
        return _qm01_clause_lookup(request_id, classification["standard_id"], classification["clause_id"], corpora, attribution, out_dir, knowledge, knowledge_info)
    if mode == "QMODE-04":
        return _qm04_table_region(request_id, question, classification["standard_id"], classification["table_number"], corpora, facts, attribution, out_dir, knowledge, knowledge_info)
    if mode == "QMODE-03":
        return _qm03_topic_search(request_id, question, classification["standard_id"], corpora, attribution, out_dir, knowledge, knowledge_info)
    return answer_professional(
        request_id, question, facts, corpora, attribution,
        {key: value.expected_sha for key, value in corpora.items()}, out_dir, knowledge, knowledge_info,
        regulation_context,
    )


def _run_request(data: dict, out_dir: Path | None, knowledge_binding: dict | None) -> RegulationEvidenceResult:
    request = data["request"]
    return answer(
        request["request_id"], request["question"], request["project_context"],
        request["regulation_context"], request["enterprise_context"], out_dir=out_dir,
        knowledge_binding=knowledge_binding,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brea", description="BREA v0.8-candidate runner")
    parser.add_argument("--case", choices=["T-C01", "T-C02", "T-C03"])
    parser.add_argument("--request", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--knowledge", type=Path, required=True)
    parser.add_argument("--knowledge-id", required=True)
    parser.add_argument("--knowledge-sha256", required=True)
    args = parser.parse_args(argv)
    if args.request is not None:
        data = json.loads(args.request.read_text(encoding="utf-8"))
    elif args.case is not None:
        data = json.loads((FIXTURES_DIR / f"{args.case}.json").read_text(encoding="utf-8"))
    else:
        parser.error("provide --case or --request")
    binding = {"revision_id": args.knowledge_id, "path": str(args.knowledge), "sha256": args.knowledge_sha256}
    print(json.dumps(_run_request(data, args.out, binding).to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
