"""An edge is confirmed only when one clause says it, in the order the page says it.

Nearness was enough before this: the predicate's word had to sit in a clause naming the
edge's subject, and the other end only had to appear somewhere in the passage. Three
readings that no reviewer would accept came back confirmed on that rule - a negated
sentence, a sentence read backwards, and a sentence that relates one end and merely
mentions the other - so each of them is a case here.
"""
from catalyst_platform.understand_semantic import states_its_relation

MERGE = "整合投资管理中心、市场营销中心，设置为市场营销中心，下设招投标部、策划部、投资管理部"


def test_a_negated_word_states_the_opposite_of_the_edge():
    assert states_its_relation("隶属", "甲部门不隶属乙部门", ("甲部门", "乙部门")) is False
    assert states_its_relation("隶属", "甲部门不属于乙部门", ("甲部门", "乙部门")) is False


def test_the_ends_have_to_stand_in_the_order_the_edge_drew_them():
    assert states_its_relation("隶属", "甲部门隶属乙部门", ("乙部门", "甲部门")) is False
    assert states_its_relation("隶属", "甲部门隶属乙部门", ("甲部门", "乙部门")) is True


def test_one_clause_relates_only_the_ends_it_names():
    passage = "甲部门隶属丙部门，乙部门独立办公"
    assert states_its_relation("隶属", passage, ("甲部门", "乙部门")) is False


def test_an_end_nobody_named_is_not_an_end_the_page_stated():
    # The callers hand over "" for a key no entity carries, and "" sits inside every
    # passage, so an unnamed end would confirm whatever word the passage contains.
    assert states_its_relation("隶属", "甲部门隶属乙部门", ("", "乙部门")) is False
    assert states_its_relation("隶属", "甲部门隶属乙部门", ("甲部门", "")) is False


def test_the_word_this_deck_uses_still_confirms_its_members():
    # 下设 writes the whole and then its members; here the whole is the clause before.
    for member in ("招投标部", "策划部", "投资管理部"):
        assert states_its_relation("隶属", MERGE, (member, "市场营销中心")) is True


def test_a_whole_the_clause_before_merged_is_not_the_organisation():
    # 整合甲、乙，下设丙: 丙 belongs to what the two become, not to either of them.
    merged = "整合投资管理中心、市场营销中心，下设招投标部、策划部"
    assert states_its_relation("隶属", merged, ("招投标部", "市场营销中心")) is False
    assert states_its_relation("隶属", merged, ("招投标部", "投资管理中心")) is False


def test_a_colon_keeps_a_duty_line_off_its_owner():
    # A page writes 名称：职责 as two lines: 「分公司其他员工」：负责 / 分公司项目具体执行. Read
    # across the colon the duty's 分公司 becomes the thing the employee is responsible for,
    # which is a fragment of the duty rather than the company the employee works in.
    passage = "分公司其他员工：负责分公司项目具体执行"
    assert states_its_relation("负责", passage, ("分公司其他员工", "分公司")) is False
    # The same words without the line break do state that relation, so the colon is what
    # decides here and not a name that happens to sit inside the other.
    assert states_its_relation("负责", "分公司其他员工负责分公司", ("分公司其他员工", "分公司")) is True
