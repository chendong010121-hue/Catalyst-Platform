"""The six corrections a human review put into RELATION-CLASSES v1.1, as cases.

Every case here was a real defect on one card or the sentence that stops it: a state verb
read as a state, a subject borrowed across list items, a governance line given a predicate
it never had, a reporting line refused because its receiver is a committee.
"""
from __future__ import annotations

from catalyst_platform.understand_relation_classes import (
    CLASS_SET_VERSION,
    actor_role,
    judge_duty,
    judge_relation,
    layout_binds,
    name_forms,
    pair_conflicts,
    sentence_state,
    direct_superior,
    binding_issues,
)


def test_a_finished_change_is_not_a_plan():
    assert sentence_state("四分公司已合并到智静，保留四分法人主体")[0] == "as-is"
    assert sentence_state("此前成立的专业化子公司")[0] == "as-is"


def test_a_planned_change_is_to_be():
    assert sentence_state("拟整合投资管理中心与市场营销中心")[0] == "to-be"
    assert sentence_state("下一步合并三家分公司")[0] == "to-be"
    assert sentence_state("需要整合背景与风险管控")[0] == "to-be"


def test_a_bare_state_verb_needs_the_page_to_be_a_proposal():
    # "设置为" on its own says a change happened or was proposed; only the page decides.
    assert sentence_state("设置为市场营销中心")[0] is None
    assert sentence_state("设置为市场营销中心", proposal_context=True)[0] == "to-be"


def test_a_negated_change_states_no_state():
    state, why = sentence_state("未设置为市场营销中心")
    assert state is None and "否定" in why


def test_a_subject_outside_its_own_item_does_not_vouch_for_it():
    issues = binding_issues("六、开展年度经营计划", "组织升级小组", "年度经营计划")
    assert "subject_absent" in issues
    # The same words with the holder named in the item do bind.
    assert "subject_absent" not in binding_issues(
        "四、组织升级小组研讨确定各部门职责与岗位设置", "组织升级小组", "各部门职责与岗位设置")


def test_a_governance_line_alone_fixes_no_predicate():
    verdict = judge_relation(subject="董事会", obj="天津市水利工程集团有限公司", sentence="",
                             drawn=True, path=("董事会", "天津市水利工程集团有限公司"),
                             page_state="current", governance=True)
    # A drawn line into the board says a governance relation exists, not which one: the row
    # asks, even though the page declares its state.
    assert not verdict.assertable
    assert verdict.predicate is None
    assert "治理" in (verdict.question or "")


def test_a_sentence_that_says_report_to_is_a_reporting_line():
    verdict = judge_relation(subject="组织升级小组", obj="变革委员会",
                             sentence="组织升级小组向变革委员会汇报决策", drawn=False,
                             raw_predicate="负责", page_state="current")
    assert verdict.predicate == "汇报"
    assert verdict.evidence_class == "observed_from_source"
    assert verdict.assertable


def test_a_reporting_line_may_end_at_a_committee_not_only_at_a_post():
    verdict = judge_relation(subject="党委办公室", obj="党委会",
                             sentence="党委办公室向党委会汇报工作", drawn=False, page_state="current")
    assert verdict.predicate == "汇报" and verdict.assertable


def test_setting_up_departments_runs_parent_to_child():
    verdict = judge_relation(
        subject="市场营销中心", obj="招投标部",
        sentence="整合投资管理中心、市场营销中心，设置为市场营销中心，下设招投标部、策划部、投资管理部",
        drawn=True, path=("市场营销中心", "招投标部"), page_state="target")
    assert verdict.predicate == "下设" and verdict.assertable


def test_a_row_written_the_other_way_round_is_corrected_not_dropped():
    # live46 wrote 投资管理部 → 市场营销中心 off these very words; §1 fixes the direction of
    # 下设, so the row is turned round instead of losing the edge.
    verdict = judge_relation(
        subject="投资管理部", obj="市场营销中心",
        sentence="整合投资管理中心、市场营销中心，设置为市场营销中心，下设招投标部、策划部、投资管理部",
        drawn=False, raw_predicate="隶属", page_state="target")
    assert verdict.predicate == "下设" and verdict.swapped
    # The same sentence read the right way round is left alone.
    kept = judge_relation(
        subject="市场营销中心", obj="投资管理部",
        sentence="整合投资管理中心、市场营销中心，设置为市场营销中心，下设招投标部、策划部、投资管理部",
        drawn=False, raw_predicate="下设", page_state="target")
    assert kept.predicate == "下设" and not kept.swapped


def test_one_pair_carries_one_of_the_inverse_pair():
    rows = [{"predicate": "下设", "subject": "市场营销中心", "object": "招投标部"},
            {"predicate": "隶属", "subject": "招投标部", "object": "市场营销中心"}]
    assert pair_conflicts(rows)


def test_the_investment_band_never_says_membership():
    verdict = judge_relation(subject="天水智信", obj="天津市水利工程集团有限公司", sentence="",
                             drawn=True, path=("天水智信", "对外投资单位", "经理层", "天津市水利工程集团有限公司"),
                             page_state="current", raw_predicate="隶属")
    assert verdict.predicate == "投资关联"
    assert verdict.assertable and "投资关联" in verdict.why


def test_no_path_is_not_a_direct_superior():
    judgement = judge_relation(subject="一分公司", obj="天津市水利工程集团有限公司", sentence="",
                               drawn=True, path=("一分公司", "前台部门(分公司)", "经理层", "天津市水利工程集团有限公司"),
                               page_state="current")
    assert direct_superior(judgement, ("一分公司", "前台部门(分公司)", "经理层", "天津市水利工程集团有限公司"),
                           "", "一分公司", "天津市水利工程集团有限公司") == "indirect"
    # A relation with neither a drawing nor a path is unknown, never "direct".
    bare = judge_relation(subject="组织升级小组", obj="各部门", sentence="", drawn=False)
    assert direct_superior(bare, (), "", "组织升级小组", "各部门") == "unknown"


def test_a_duty_without_its_owner_in_the_item_keeps_the_owner_unknown():
    borrowed = judge_duty(holder="组织升级小组", holder_known=True,
                          sentence="六、开展年度经营计划")
    assert borrowed.verdict == "ask" and "由谁负责" in (borrowed.question or "")
    owned = judge_duty(holder="组织升级小组", holder_known=True,
                       sentence="五、组织升级小组研讨确定三定方案")
    assert owned.assertable and owned.predicate == "负责"


def test_the_class_set_carries_its_version():
    assert CLASS_SET_VERSION.startswith("relation-classes.")


def test_a_bracket_is_a_second_name_not_a_second_thing():
    # The post is labelled "总工程师（技术副经理）"; the cell beside it writes "总工程师：".
    owned = judge_duty(holder="总工程师 （技术副经理）", holder_known=True,
                       sentence="总工程师：负责分公司技术、质量、研发工作")
    assert owned.assertable and owned.predicate == "负责"
    # The same rule keeps a centre's alias from going missing in a sentence.
    assert "object_absent" not in binding_issues("技术研发中心下设招投标部", "市场营销中心", "技术研发中心（质量技术部）")


def test_a_duty_binds_to_a_post_only_when_they_share_a_row():
    post = (4_830_000, 2_960_000, 2_680_000, 470_000)      # 分公司经理, row 2.96in
    beside = (7_580_000, 3_010_000, 3_790_000, 370_000)    # its duty cell, same row
    above = (5_010_000, 2_140_000, 3_070_000, 1_000_000)   # 后台职能部门
    note = (8_450_000, 2_140_000, 5_280_000, 1_000_000)    # the 服务 note beside it
    assert layout_binds(beside, post)
    assert layout_binds(note, above)
    # The 中台 department one row down does not own the note from the row above it.
    assert not layout_binds(note, (5_010_000, 3_560_000, 3_070_000, 1_000_000))


def test_a_duty_bound_by_layout_says_so_and_a_wrong_row_asks():
    bound = judge_duty(holder="分公司经理", holder_known=True,
                       sentence="全面负责分公司经营，主抓市场营销", layout_bound=True,
                       layout_ref="slide12#shape:3 与 slide12#shape:9 同纵带")
    assert bound.assertable and bound.evidence_class == "inferred"
    wrong = judge_duty(holder="中台职能部门", holder_known=True,
                       sentence="服务：专业能力建设，服务一线，风险管控",
                       layout_bound=False, band_holder="后台职能部门")
    assert not wrong.assertable and "不同行" in wrong.why


def test_a_label_is_not_a_statement():
    # "客 户" is a page label: quoted alone it names neither end of a relation.
    assert "subject_absent" in binding_issues("客 户", "一分公司", "客 户")
    # A bracket is the same thing written twice, in either bracket style.
    assert name_forms("党委办公室 （宣传部）") == ("党委办公室(宣传部)", "党委办公室", "宣传部")


def test_a_column_heading_is_not_a_parent():
    verdict = judge_relation(
        subject="市场营销中心", obj="中台部门", sentence="", drawn=True,
        path=("市场营销中心", "中台部门", "经理层", "董事会", "天津市水利工程集团有限公司"),
        page_state="current", band_object="中台部门")
    assert not verdict.assertable and verdict.predicate is None
    assert "分类列" in verdict.why


def test_an_unstated_reporter_keeps_the_verb_and_asks():
    # Review 57: item three says "向变革委员会汇报决策" — the reporter is unstated, and
    # recording the receiver as the object of a responsibility would invert the relation.
    verdict = judge_relation(subject="组织升级小组", obj="变革委员会", drawn=False,
                             sentence="三、向变革委员会汇报决策，并召开部门级公司会议",
                             raw_predicate="负责", page_state="current")
    assert verdict.predicate == "汇报" and not verdict.assertable

# ---- v1.2：live46 全量人审复现出来的六类缺口，逐条留成用例 ----

def test_a_connector_that_exists_is_never_reported_as_missing():
    # 41 rows on one card said "the page never drew this line" while the OOXML has it.
    drawn_none = judge_relation(subject="三分公司", obj="水利集团区域化的分公司架构", sentence="",
                                drawn=False, raw_edge="ppt/slides/slide3.xml#cxn:12",
                                direction_note="盒子的位置：水利集团区域化的分公司架构 在上、三分公司 在下")
    assert not drawn_none.assertable
    assert "线在" in drawn_none.why and "没有画出这条线" not in drawn_none.why
    assert drawn_none.tier == "raw"
    # ... and when there really is no line, the old wording stays.
    no_line = judge_relation(subject="甲", obj="乙", sentence="", drawn=False)
    assert "没有画出这条线" in no_line.why


def test_an_object_the_sentence_never_names_is_not_asserted():
    verdict = judge_relation(subject="市场营销中心", obj="投资管理部",
                             sentence="整合投资管理中心、市场营销中心，设置为市场营销中心，下设招投标部、策划部",
                             drawn=False, page_state="to-be")
    assert not verdict.assertable and "对象" in verdict.why


def test_the_agent_is_read_by_role_not_by_word_order():
    # 受事前置：对象在前，负责人仍是财务部。
    front = judge_relation(subject="财务部", obj="付款凭证", sentence="付款凭证由财务部负责",
                           drawn=False, page_state="current")
    assert front.assertable and front.predicate == "负责"
    plain = judge_relation(subject="财务部", obj="付款凭证", sentence="财务部负责付款凭证",
                           drawn=False, page_state="current")
    assert plain.assertable


def test_a_responsibility_written_with_the_ends_swapped_asks_instead_of_asserting():
    verdict = judge_relation(subject="付款凭证", obj="财务部", sentence="财务部负责付款凭证",
                             drawn=False, page_state="current")
    assert not verdict.assertable
    assert "写反" in verdict.why or "负责人" in verdict.why


def test_a_reporting_line_reads_reporter_and_receiver():
    ok = judge_relation(subject="组织升级小组", obj="变革委员会",
                        sentence="组织升级小组向变革委员会汇报决策", drawn=False, page_state="current")
    assert ok.assertable and ok.predicate == "汇报"
    back = judge_relation(subject="变革委员会", obj="组织升级小组",
                          sentence="组织升级小组向变革委员会汇报决策", drawn=False, page_state="current")
    assert not back.assertable


def test_a_reversed_reporting_line_is_found_both_ways():
    assert actor_role("组织升级小组向变革委员会汇报决策", "变革委员会", "组织升级小组", "汇报")[0] == "reversed"
    assert actor_role("付款凭证由财务部负责", "财务部", "付款凭证", "负责")[0] == "agent"


def test_a_negated_duty_is_kept_but_never_turned_positive():
    verdict = judge_duty(holder="财务部", sentence="财务部不负责审批", holder_known=True)
    assert not verdict.assertable
    assert verdict.qualifier == "negated" and verdict.predicate is None
    assert "不负责审批" in verdict.why          # 原句与否定都在，没被改写


def test_a_conditional_duty_is_kept_with_its_condition():
    verdict = judge_duty(holder="财务部", sentence="财务部在审计期间负责付款凭证核验", holder_known=True)
    assert not verdict.assertable
    assert verdict.qualifier == "conditional"
    assert "审计期间" in verdict.why


def test_a_scope_clause_makes_the_duty_conditional():
    # 第 5 页三格：说清什么时候/什么范围才这么做，就不是无条件的现行职责。
    cases = [
        ("大项目部", "公司大项目做完即可解散项目部，新业务培育起来之后，可成立子公司", "之后"),
        ("分公司", "分公司有资源，或便于在区域开展的新业务，由分公司和市场营销中心共同协作完成", "或"),
        ("子公司", "非工程类新业务、部分市场空间、业务规模足够大，专业性足够强的工程新业务", "足够"),
    ]
    for holder, sentence, mark in cases:
        verdict = judge_duty(holder=holder, sentence=sentence, holder_known=True)
        assert not verdict.assertable, sentence
        assert verdict.qualifier == "conditional", sentence
        assert mark in verdict.why, sentence        # 条件写进理由，原句不动


def test_a_word_that_only_looks_conditional_is_not_one():
    # "具有一定的稳定性"是性质、"：负责…"是岗位职责，都不带适用范围。
    for holder, sentence in (("子公司", "负责非工程业务，子公司业务需具有一定的稳定性"),
                             ("总工程师", "总工程师：负责分公司技术、质量、研发工作")):
        verdict = judge_duty(holder=holder, sentence=sentence, holder_known=True)
        assert verdict.qualifier == "", sentence
        assert verdict.assertable, sentence


def test_negation_does_not_wipe_the_state():
    # "不需要" 里那个"需要"不是方案语气；"未设置为" 仍按设置类动词走。
    assert sentence_state("不需要负责付款凭证核验")[0] is None
    assert sentence_state("未设置为市场营销中心", proposal_context=True)[0] == "to-be"


def test_merging_onto_is_an_action_not_a_state():
    assert sentence_state("合并到智静")[0] is None
    assert sentence_state("拟合并到智静")[0] == "to-be"
    assert sentence_state("已经合并到智静")[0] == "as-is"


def test_a_plan_in_a_name_is_not_a_tense():
    assert sentence_state("年度经营计划")[0] is None
    assert sentence_state("计划于2026年完成整合")[0] == "to-be"


def test_a_duty_inside_a_group_asks_for_the_group_not_the_nearest_member():
    verdict = judge_duty(holder="水利集团子公司", sentence="统筹管理子公司日常运营工作",
                         holder_known=True, grouped=True, layout_ref="slide6#shape:25")
    assert not verdict.assertable
    assert "整组" in (verdict.question or "") and "津北水务" not in (verdict.question or "")


def test_a_band_label_is_not_a_concrete_department():
    from catalyst_platform import understand_structure as struct
    for name in ("前台部门（分公司）", "中台部门", "后台部门", "对外投资单位",
                 "水利集团区域化的分公司架构"):
        assert struct.is_band(name)
