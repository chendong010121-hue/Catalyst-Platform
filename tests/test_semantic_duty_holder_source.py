"""A duty sentence that prints its own holder owns the work; the cell beside it does not.

V6 prints 「分公司其他员工：负责分公司项目具体执行」 beside 「项目经理及各级员工」. The model declared
the neighbouring cell as an entity, hung this duty on it, and wrote an UNKNOWN in the same answer
saying the two groups might not be the same - so it had the doubt and bound anyway. The row's
holder is now checked against the name the sentence prints: a holder that comes from anywhere
else is kept as an unresolved row that names the group it could not bind, never as a fact about
somebody the page did not name.

A colon is read two ways and only two: as the group that owns the work, or as a column heading
that owns nothing (「服务：」「管理+赋能：」). The heading list is declared, not guessed, because
"every prefix is an entity" is the mistake this file exists to stop.
"""
from __future__ import annotations

import json

from agent_runtime.contracts import ModelResponse

from catalyst_platform.understand_only import (
    UnderstandIntent,
    UnderstandPort,
    UnderstandingRequest,
)

TEXT = ("分公司经理全面负责分公司经营，主抓市场营销。\n"
        "项目经理及各级员工\n"
        "分公司其他员工：负责分公司项目具体执行\n"
        "总工程师（技术副经理）\n"
        "总工程师：负责分公司技术、质量、研发工作\n"
        "中台职能部门\n"
        "分公司\n"
        "分公司负责工程业务，保障公司基本盘。\n"
        "服务：专业能力建设，服务一线，风险管控\n")

NAMES = {"xiangmu_jingli_ji_geji_yuangong": "项目经理及各级员工",
         "zong_gongchengshi": "总工程师（技术副经理）",
         "zhongtai_zhineng_bumen": "中台职能部门",
         "fengongsi": "分公司"}


class _Answer:
    model = "stub-holder-source"
    structured_output_token_limit = 4096

    def __init__(self, build):
        self._build = build

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"]
        return ModelResponse(content=json.dumps({"items": self._build(evidence)}, ensure_ascii=False),
                             finish_reason="stop")


def _evidence(evidence, name):
    return next(item["evidence_id"] for item in evidence if name in item["quote"])


def _entity(key, evidence):
    return {"kind": "entity", "key": key, "meaning": NAMES[key], "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [_evidence(evidence, NAMES[key])]}


def _duty(key, holder, meaning, evidence, quote_name):
    return {"kind": "duty", "key": key, "subject": holder, "meaning": meaning,
            "evidence_class": "SOURCE_DIRECT",
            "evidence_refs": [_evidence(evidence, quote_name)]}


def _run(tmp_path, build):
    source = tmp_path / "deck.md"
    source.write_text(TEXT, encoding="utf-8")
    return UnderstandPort().understand(
        UnderstandingRequest("holder-source", "整理组织", source_refs=(source,),
                             intent=UnderstandIntent.KNOWLEDGE_PROPOSE,
                             scope_id="scope_holder_source",
                             requested_depth="semantic", budget_steps=4),
        source_root=tmp_path, semantic_provider=_Answer(build))


def _by_key(result):
    return {item.key: item for item in result.semantic_candidate.items}


def test_a_named_group_is_not_replaced_by_the_cell_beside_it(tmp_path):
    """The sentence names 分公司其他员工; 项目经理及各级员工 is the cell beside it, not this group."""
    def build(evidence):
        return [_entity("xiangmu_jingli_ji_geji_yuangong", evidence),
                _duty("duty_qita_yuangong", "xiangmu_jingli_ji_geji_yuangong",
                      "分公司其他员工：负责分公司项目具体执行", evidence, "分公司其他员工")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_qita_yuangong"]
    assert duty.kind == "duty"
    assert duty.evidence_class == "unresolved"
    assert duty.uncertainty == "degraded:duty_holder_names_another_group:分公司其他员工"


def test_the_refused_row_keeps_the_work_item_it_could_not_place(tmp_path):
    """A row that cannot be bound is still the page's work item, named and reviewable."""
    def build(evidence):
        return [_entity("xiangmu_jingli_ji_geji_yuangong", evidence),
                _duty("duty_qita_yuangong", "xiangmu_jingli_ji_geji_yuangong",
                      "分公司其他员工：负责分公司项目具体执行", evidence, "分公司其他员工")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_qita_yuangong"]
    assert duty.meaning == "分公司其他员工：负责分公司项目具体执行"
    assert duty.evidence_refs


def test_a_named_group_bound_to_its_own_row_is_a_duty(tmp_path):
    """「总工程师（技术副经理）」 is the name the sentence prints, brackets and all."""
    def build(evidence):
        return [_entity("zong_gongchengshi", evidence),
                _duty("duty_zong_gongchengshi", "zong_gongchengshi",
                      "总工程师：负责分公司技术、质量、研发工作", evidence, "总工程师：")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_zong_gongchengshi"]
    assert duty.kind == "duty"
    assert duty.evidence_class == "observed_from_source"
    assert duty.uncertainty is None


def test_a_column_heading_is_not_a_holder_and_does_not_refuse_the_row(tmp_path):
    """「服务：」 labels a column; the department the layout puts beside it still owns the work."""
    def build(evidence):
        return [_entity("zhongtai_zhineng_bumen", evidence),
                _duty("duty_fuwu", "zhongtai_zhineng_bumen",
                      "服务：专业能力建设，服务一线，风险管控", evidence, "服务：")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_fuwu"]
    assert duty.kind == "duty"
    assert duty.uncertainty is None


def test_a_sentence_without_a_colon_is_read_as_before(tmp_path):
    def build(evidence):
        return [_entity("fengongsi", evidence),
                _duty("duty_gongcheng", "fengongsi", "分公司负责工程业务，保障公司基本盘", evidence,
                      "负责工程业务")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_gongcheng"]
    assert duty.kind == "duty"
    assert duty.uncertainty is None


def test_a_wider_declared_name_is_still_another_group(tmp_path):
    """分公司 is not 分公司其他员工: a name that merely starts the same way is a different group."""
    def build(evidence):
        return [_entity("fengongsi", evidence),
                _duty("duty_qita_yuangong", "fengongsi",
                      "分公司其他员工：负责分公司项目具体执行", evidence, "分公司其他员工")]

    result = _run(tmp_path, build)
    duty = _by_key(result)["duty_qita_yuangong"]
    assert duty.kind == "duty"
    assert duty.evidence_class == "unresolved"
    assert duty.uncertainty == "degraded:duty_holder_names_another_group:分公司其他员工"


def _quoted_run(tmp_path, meaning, holder, quote_name, key="duty_q"):
    def build(evidence):
        return [_entity(holder, evidence), _duty(key, holder, meaning, evidence, quote_name)]

    return _by_key(_run(tmp_path, build))[key]


def test_a_sentence_wrapped_in_quotes_binds_to_the_same_group(tmp_path):
    """The cell quotation belongs to the cell: it is not part of the group name."""
    plain = _quoted_run(tmp_path, "总工程师：负责分公司技术、质量、研发工作",
                        "zong_gongchengshi", "总工程师：")
    quoted = _quoted_run(tmp_path, "「总工程师：负责分公司技术、质量、研发工作」",
                         "zong_gongchengshi", "总工程师：")

    assert (plain.evidence_class, plain.uncertainty) == ("observed_from_source", None)
    assert (quoted.evidence_class, quoted.uncertainty) == (plain.evidence_class, plain.uncertainty)


def test_the_quoted_sentence_keeps_its_own_text_and_evidence(tmp_path):
    duty = _quoted_run(tmp_path, "「总工程师：负责分公司技术、质量、研发工作」",
                       "zong_gongchengshi", "总工程师：")

    assert duty.meaning == "「总工程师：负责分公司技术、质量、研发工作」"
    assert duty.evidence_refs


def test_a_quote_inside_a_name_is_not_taken_for_a_wrapper():
    from catalyst_platform.understand_semantic import _duty_named_group

    assert _duty_named_group("「部门「A」：做事」") == "部门「A」"
    assert _duty_named_group("部门「A」：做事") == "部门「A」"


def test_a_quoted_sentence_naming_another_group_is_still_refused(tmp_path):
    duty = _quoted_run(tmp_path, "「分公司其他员工：负责分公司项目具体执行」",
                       "xiangmu_jingli_ji_geji_yuangong", "分公司其他员工", key="duty_qita")

    assert duty.evidence_class == "unresolved"
    assert duty.uncertainty == "degraded:duty_holder_names_another_group:分公司其他员工"


def test_a_quoted_column_heading_is_still_a_label(tmp_path):
    duty = _quoted_run(tmp_path, "「服务：专业能力建设，服务一线，风险管控」",
                       "zhongtai_zhineng_bumen", "服务：", key="duty_fuwu")

    assert (duty.evidence_class, duty.uncertainty) == ("observed_from_source", None)


def test_a_quoted_post_with_a_bracket_alias_still_binds(tmp_path):
    duty = _quoted_run(tmp_path, "「总工程师（技术副经理）：负责分公司技术、质量、研发工作」",
                       "zong_gongchengshi", "总工程师（技术副经理）")

    assert (duty.evidence_class, duty.uncertainty) == ("observed_from_source", None)
