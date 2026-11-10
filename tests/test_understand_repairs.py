"""The repairs a frozen candidate may receive, as cases — each one a defect a review found.

Every case is a real row of the live46 card (or a same-shaped sibling of it): a team typed
as a post, an arrangement that borrowed "as-is" from a heading that says "升级", a duty bound
to the unit in the other row, an event whose ends the sentence names but the record did not
carry, and an UNKNOWN that kept denying what another entry had already answered.
"""
from __future__ import annotations

import hashlib

from catalyst_platform.understand_repairs import (
    event_ends,
    keeps_legal_entity,
    layout_evidence,
    local_end_reference,
    merge_ends,
    narrow_absence_claim,
    page_state_inheritable,
    position_eligible,
    rebind_holder,
    same_end,
    stage_undistinguished,
    supersede_unknown,
)

UPGRADE_TITLE = "现有业务模式升级：深度融入区域发展，从价值分享者到价值创造者"
CURRENT_TITLE = "水利集团现有组织结构："
INTEGRATE = "整合投资管理中心、市场营销中心，设置为市场营销中心，下设招投标部、策划部、投资管理部，统筹管理，发挥规模效应"


# ---- M01/M02: a team is not a post, and an upgrade is not a fact ----

def test_a_team_carrying_work_is_not_a_post():
    # 第 4 页「在公司层面成立专业策划团队」是组织安排，不是岗位；这是本轮被点名的 145。
    assert position_eligible("专业策划团队")[0] is False
    assert position_eligible("各区域分公司")[0] is False
    assert position_eligible("市场营销中心")[0] is False


def test_a_post_keeps_its_type():
    for name in ("分公司经理", "分公司常务副经理", "市场 副经理", "工程 副经理"):
        assert position_eligible(name)[0] is True, name


def test_a_name_with_a_parenthesised_note_is_read_by_its_main_form():
    # 第 12 页那两格都是岗位，尾注不是名字的结尾：「总工程师（技术副经理）」仍是岗位。
    assert position_eligible("总工程师 （技术副经理）")[0] is True
    assert position_eligible("专业策划团队（公司层面）")[0] is False


def test_an_empty_name_gets_no_type():
    assert position_eligible(None)[0] is False
    assert position_eligible("  ")[0] is False


def test_a_page_that_only_says_what_stands_lends_its_state():
    assert page_state_inheritable("as-is", CURRENT_TITLE)[0] is True
    # 只讲方案的页借得出 to-be；「现有…升级…」这种把两种状态印在一起的页借不出任何一种。
    assert page_state_inheritable("to-be", "组织结构调整方案")[0] is True
    assert page_state_inheritable("to-be", UPGRADE_TITLE)[0] is False


def test_a_page_that_announces_a_change_lends_no_as_is():
    assert page_state_inheritable("as-is", UPGRADE_TITLE)[0] is False


def test_the_same_word_anywhere_else_reads_the_same_way():
    # 同义样例：不是关键词清单，而是「这一页在讲调整」这件事。
    for heading in ("组织结构调整方案", "组织架构优化：加强专业分工，加大市场开发力量",
                    "三定方案（讨论稿）", "下一步整合三家分公司", "总部与分公司关系问题的改革设想"):
        assert page_state_inheritable("as-is", heading)[0] is False, heading


def test_a_page_that_prints_both_states_lends_neither():
    # 第二份复核的反例：混合页连 to-be 也不能借。
    for heading in ("现状与调整方案对照", "现有架构与优化后架构", "目前设置与改革方向"):
        assert page_state_inheritable("as-is", heading)[0] is False, heading
        assert page_state_inheritable("to-be", heading)[0] is False, heading


def test_a_page_with_no_state_lends_nothing():
    assert page_state_inheritable("unstated", CURRENT_TITLE)[0] is False
    assert page_state_inheritable(None, CURRENT_TITLE)[0] is False


# ---- M08: the note's holder is the unit in its own row ----

def test_the_note_belongs_to_the_unit_in_its_row():
    # 第 8 页：后台的「服务」被绑给了中台，中台的「管理+赋能」被绑给了后台。
    fix = rebind_holder("中台职能部门", "后台职能部门",
                        "服务：专业能力建设，服务一线，风险管控",
                        "ppt/slides/slide8.xml#shape:3 与 ppt/slides/slide8.xml#shape:5")
    assert fix and fix["holder"] == "后台职能部门"
    assert "版式同一行" in fix["why"]

    fix = rebind_holder("后台职能部门", "中台职能部门",
                        "管理+赋能：体系建设、风险管控+能力建设、资源池",
                        "ppt/slides/slide8.xml#shape:4 与 ppt/slides/slide8.xml#shape:7")
    assert fix and fix["holder"] == "中台职能部门"


def test_a_sentence_that_names_its_holder_beats_the_layout():
    assert rebind_holder("中台职能部门", "后台职能部门", "中台职能部门负责专业能力建设") is None


def test_a_row_that_already_agrees_is_left_alone():
    # 第 12 页 301–303：同排版式绑定本来就是对的，不许被再改一次。
    assert rebind_holder("分公司经理", "分公司经理", "全面负责分公司经营，主抓市场营销") is None
    assert rebind_holder("分公司经理", "", "全面负责分公司经营，主抓市场营销") is None


# ---- M07: the ends the sentence names ----

def test_an_integration_keeps_both_units_before_the_change():
    got = event_ends(INTEGRATE)
    assert got == {"from": ["投资管理中心", "市场营销中心"], "to": ["市场营销中心"]}


def test_a_merge_reads_its_two_ends():
    assert event_ends("一分公司合并到智信，一分部分工作分派到总部相关部门；不再保留一分法人主体") == {
        "from": ["一分公司"], "to": ["智信"]}


def test_a_sentence_without_a_change_states_no_ends():
    assert event_ends("四分公司合并到智静") ["from"] == ["四分公司"]
    assert event_ends("各区域分公司对本区域进行深入研究") is None


def test_the_named_end_keeps_the_candidate_spelling():
    # 「智静」写在原句里、条目写作「天水智静」：没有登记成别名，就不合并、也不新增一个端点，
    # 只把这一对交出去核对。宁可少说，不可自动造名字。
    unresolved: list = []
    assert merge_ends(["天水智信"], ["智信"], None, unresolved) == ["天水智信"]
    assert unresolved == [{"recorded": "天水智信", "sentence": "智信"}]
    assert merge_ends(["市场营销中心"], ["投资管理中心", "市场营销中心"]) == [
        "投资管理中心", "市场营销中心"]


def test_only_a_registered_alias_makes_two_names_one_end():
    # 名字清单不是别名映射：短名没被登记，就证明不了它是长名的简称。
    assert same_end("华北财务部", "财务部") is False
    assert same_end("华北财务部", "财务部", {"华北财务部": ["财务部"]}) is True
    assert same_end("区域市场营销中心", "市场营销中心", {"市场营销中心": ["营销中心"]}) is False
    unresolved: list = []
    assert merge_ends(["华北财务部"], ["财务部"], None, unresolved) == ["华北财务部"]
    assert unresolved == [{"recorded": "华北财务部", "sentence": "财务部"}]
    assert merge_ends(["华北财务部"], ["财务部"], {"华北财务部": ["财务部"]}) == ["华北财务部"]
    # 第三份复核的原始探针：拿一张名字清单当依据。清单不是映射——只登记了长名，
    # 恰恰说明短名与长名的关系没有被登记过，所以答案仍是「不合并」。
    assert same_end("华北财务部", "财务部", ["华北财务部"]) is False


def test_a_denied_change_states_no_ends():
    # 第二份复核的反例：否定被读成合并，还造出了「甲公司未」这个主体。
    assert event_ends("甲公司未合并到乙公司") is None
    assert event_ends("尚未整合甲中心、乙中心，设置为丙中心") is None
    assert event_ends("一分公司不再合并到智信") is None
    assert event_ends("四分公司合并到智静；保留四分法人主体") == {
        "from": ["四分公司"], "to": ["智静"]}


def test_a_conditional_change_states_no_ends():
    # 第三份复核的反例：假设句不是事件，也不许用「若」当主体的第一个字。
    assert event_ends("若甲公司合并到乙公司，则另行评估") is None
    assert event_ends("如果甲公司合并到乙公司，另行评估资源") is None
    assert event_ends("一旦整合甲中心、乙中心，设置为丙中心，再评估人员") is None


def test_the_legal_person_follows_the_wording_only():
    assert keeps_legal_entity("四分公司合并到智静；保留四分法人主体") is True
    assert keeps_legal_entity("一分公司合并到智信，一分部分工作分派到总部相关部门；不再保留一分法人主体") is False
    assert keeps_legal_entity("未保留甲法人主体") is False
    assert keeps_legal_entity("四分公司合并到智静") is None
    assert keeps_legal_entity("成立子公司/事业部") is None


def test_an_undecided_legal_person_is_not_a_keep():
    # 第二份复核的反例：不确定性被当作确定保留。
    for wording in ("尚未确定是否保留甲法人主体", "是否保留甲法人主体待研究",
                    "甲法人主体保留与否待定", "拟保留甲法人主体", "未明确是否保留甲法人主体",
                    "若保留甲法人主体则另议"):
        assert keeps_legal_entity(wording) is None, wording


def test_a_layout_bound_duty_cites_the_box_it_sits_beside():
    # 「后台职能部门」这一位的「服务：…」在版式的同一行上并排；记录若不引那个盒子，
    # 消费者就答不出来（`holder_not_in_own_quote`）——值对、读不到。
    row = layout_evidence("后台职能部门", "ppt/slides/slide8.xml#shape:3", "src_61a1")
    assert row["locator"] == "ppt/slides/slide8.xml#shape:3"
    assert row["quote"] == "后台职能部门"
    assert row["span_sha256"] == hashlib.sha256("后台职能部门".encode("utf-8")).hexdigest()
    assert layout_evidence("", "ppt/slides/slide8.xml#shape:3") is None
    assert layout_evidence("后台职能部门", None) is None


def test_a_repeated_end_asks_for_the_stage_not_for_legality():
    # 第三份复核：同名不等于事件非法——合并后可以保留某个原名称，
    # 缺的是「变更前后各自是什么角色/阶段」，所以只判「待确认」，不判「不合法」。
    fix = stage_undistinguished(["投资管理中心", "市场营销中心"], ["市场营销中心"])
    assert fix["names"] == ["市场营销中心"]
    assert "保留名称的存续方是允许的" in fix["why"]
    assert "角色或阶段" in fix["why"]
    assert stage_undistinguished(["四分公司"], ["天水智静"]) is None


# ---- M06: an answered question keeps its record and points at its answer ----

def test_one_answer_is_a_plain_id_and_the_reason_says_it_is_history():
    fix = supersede_unknown({"class": "resolved_by_text"}, ["879f4d388d8d2228"])
    assert fix["superseded_by"] == "879f4d388d8d2228"
    assert "保留为历史" in fix["reason"]


def test_several_answers_keep_the_list():
    fix = supersede_unknown({"class": "resolved_by_text"},
                            ["a720cb60c8629a92", "056f5f3e5535b8c8", "b9e50ac23b77748c"])
    assert fix["superseded_by"] == ["a720cb60c8629a92", "056f5f3e5535b8c8", "b9e50ac23b77748c"]
    assert "3 条" in fix["reason"]


def test_a_question_still_open_is_not_superseded():
    assert supersede_unknown({"class": "remaining"}, ["879f4d388d8d2228"]) is None
    assert supersede_unknown({"class": "resolved_by_text"}, []) is None
    assert supersede_unknown(None, ["879f4d388d8d2228"]) is None


def test_a_partial_answer_says_what_it_does_not_cover():
    # 引用到的条目自己还挂着 pending：只说「已解决」就是又一次说过头。
    fix = supersede_unknown({"class": "resolved_by_text"}, ["a720cb60c8629a92", "056f5f3e5535b8c8"],
                            note="其中 1 条仍是条件职责（持有人待绑定）；「适用范围」有据，「三者相互关系」仍未陈述")
    assert "保留为历史" in fix["reason"]
    assert "仍未陈述" in fix["reason"]


# ---- M04: an absence claim about a page is a claim about its text ----

def test_an_absence_claim_is_narrowed_to_the_text():
    said = "页面另列「专业驱动」与「营销驱动」两项表述，未说明二者与两种驱动模式的对应关系"
    narrowed = narrow_absence_claim(said)
    assert narrowed and narrowed != said
    assert narrowed.startswith("文本")
    assert "版式上的对应关系需核对原页" in narrowed
    assert "页面没有说明" not in narrowed.replace("不能读成「页面没有说明」", "")


def test_a_claim_that_already_says_where_it_looked_is_left_alone():
    said = "页面另列两项表述，文本未明说二者与两种驱动模式的对应关系"
    assert narrow_absence_claim(said) is None
    done = narrow_absence_claim("页面另列「专业驱动」与「营销驱动」两项表述，未说明二者与两种驱动模式的对应关系")
    assert narrow_absence_claim(done) is None  # 同一句话不会被收窄两次


def test_an_absence_of_something_else_is_not_the_page():
    # 「来源未说明是否批准」说的是材料的审批状态，不是页面少了内容。
    assert narrow_absence_claim("页面标注时间为「2025年1月」，仅说明该页日期，来源未说明版本效力") is None
    assert narrow_absence_claim("各区域分公司对本区域进行深入研究") is None


# ---- M05: a short name inside one sentence is read from that sentence's own row ----

MERGE_QUARTER = "四分公司合并到智静；保留四分法人主体"
MERGE_FIRST = "一分公司合并到智信，一分部分工作分派到总部相关部门；不再保留一分法人主体"
SLIDE7 = ("一分公司", "四分公司", "天水智信", "天水智静", "合并",
          "区域化分公司", "专业化子公司", "分公司", "子公司与子公司")


def _arrow(locator, ends):
    return {"locator": locator,
            "ends": [{"locator": "ppt/slides/slide7.xml#shape:%d" % number, "text": text}
                     for number, text in ends]}


SLIDE7_QUARTER_ARROW = _arrow("ppt/slides/slide7.xml#cxn:3", ((3, "四分公司"), (5, "天水智静")))
SLIDE7_FIRST_ARROW = _arrow("ppt/slides/slide7.xml#cxn:4", ((2, "一分公司"), (4, "天水智信")))


def test_a_short_name_is_bound_to_the_box_the_row_arrow_points_at():
    fix, why = local_end_reference("智静", MERGE_QUARTER, [SLIDE7_QUARTER_ARROW],
                                   ["四分公司"], SLIDE7)
    assert fix is not None, why
    assert fix["full"] == "天水智静"
    # 两个名字都留着：短名不是被折进全名，而是并排写出来。
    assert fix["short"] == "智静" and fix["full"] != fix["short"]
    assert fix["from"] == {"name": "四分公司", "locator": "ppt/slides/slide7.xml#shape:3"}
    assert fix["to"]["locator"] == "ppt/slides/slide7.xml#shape:5"
    assert fix["arrow"] == "ppt/slides/slide7.xml#cxn:3"
    assert "不是全文档别名" in fix["why"]


def test_the_same_short_name_in_another_sentence_is_read_from_that_sentence():
    # 同一个前缀、另一行：只认这一行的箭头，不认前一行的。
    fix, why = local_end_reference("智信", MERGE_FIRST, [SLIDE7_FIRST_ARROW], ["一分公司"], SLIDE7)
    assert fix is not None, why
    assert fix["full"] == "天水智信"


def test_a_binding_is_not_an_alias_registration():
    # 局部读到「智静」指「天水智静」，但身份门的答案不变：没有登记就不是同一个端点。
    assert same_end("天水智静", "智静") is False
    fix, _ = local_end_reference("智静", MERGE_QUARTER, [SLIDE7_QUARTER_ARROW],
                                 ["四分公司"], SLIDE7)
    assert "aliases" not in fix


def test_two_names_containing_the_short_form_leave_it_open():
    page = SLIDE7 + ("智静服务中心",)
    fix, why = local_end_reference("智静", MERGE_QUARTER, [SLIDE7_QUARTER_ARROW],
                                   ["四分公司"], page)
    assert fix is None
    assert "2 个名字含「智静」" in why and "局部不唯一" in why


def test_no_name_containing_the_short_form_leaves_it_open():
    # 句子里写着「智城」，这一页却没有哪个盒子含这两个字：只能等登记，不能就近猜。
    fix, why = local_end_reference("智城", "四分公司合并到智城", [SLIDE7_QUARTER_ARROW],
                                   ["四分公司"], SLIDE7)
    assert fix is None and "没有名字含「智城」" in why


def test_a_row_without_exactly_one_arrow_leaves_it_open():
    fix, why = local_end_reference("智静", MERGE_QUARTER, [], ["四分公司"], SLIDE7)
    assert fix is None and "0 条连线" in why
    fix, why = local_end_reference("智静", MERGE_QUARTER,
                                   [SLIDE7_QUARTER_ARROW, SLIDE7_FIRST_ARROW],
                                   ["四分公司"], SLIDE7)
    assert fix is None and "2 条连线" in why


def test_an_arrow_that_does_not_name_the_absorbing_unit_is_no_direction():
    wrong = _arrow("ppt/slides/slide7.xml#cxn:9", ((5, "天水智静"), (4, "天水智信")))
    fix, why = local_end_reference("智静", MERGE_QUARTER, [wrong], ["四分公司"], SLIDE7)
    assert fix is None and "都不是句子写明的并入方" in why
    both = _arrow("ppt/slides/slide7.xml#cxn:9", ((3, "四分公司"), (2, "一分公司")))
    fix, why = local_end_reference("智静", MERGE_QUARTER, [both], ["四分公司", "一分公司"], SLIDE7)
    assert fix is None and "方向不清" in why


def test_the_other_end_must_carry_the_short_form_and_not_be_it():
    other = _arrow("ppt/slides/slide7.xml#cxn:9", ((3, "四分公司"), (4, "天水智信")))
    fix, why = local_end_reference("智静", MERGE_QUARTER, [other], ["四分公司"], SLIDE7)
    assert fix is None and "不含句中的「智静」" in why
    exact = _arrow("ppt/slides/slide7.xml#cxn:9", ((3, "四分公司"), (5, "智静")))
    fix, why = local_end_reference("智静", MERGE_QUARTER, [exact], ["四分公司"], SLIDE7)
    assert fix is None and "不需要消解" in why


def test_a_name_the_sentence_does_not_use_is_not_bound():
    fix, why = local_end_reference("智静", "四分公司保留四分法人主体", [SLIDE7_QUARTER_ARROW],
                                   ["四分公司"], SLIDE7)
    assert fix is None and "句中没写这个短名" in why


def test_an_end_of_the_change_is_not_a_short_name_to_resolve():
    fix, why = local_end_reference("四分公司", "四分公司合并到智静", [SLIDE7_QUARTER_ARROW],
                                   ["四分公司"], SLIDE7)
    assert fix is None and "本身就是这次变更的一端" in why
