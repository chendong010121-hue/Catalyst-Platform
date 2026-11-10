"""The novelty gate decides who may spend money, and stores why it did not."""
import json

import pytest

from catalyst_platform import knowledge_intake
from catalyst_platform.knowledge_novelty import (
    FULL,
    LINK_ONLY,
    PROPOSE,
    SKIP,
    UNREAD,
    assess_novelty,
    candidate_surfaces,
    read_receipts,
    write_receipt,
)
from catalyst_platform.understand_models import _TextUnit
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.wiki_mentions import EntityEntry, EntityIndex


def unit(locator: str, quote: str) -> _TextUnit:
    return _TextUnit('source', 'relative.md', 'revision', 'revision', locator, quote)


def index(*pairs: tuple[str, str]) -> EntityIndex:
    return EntityIndex.from_entries(
        EntityEntry(surface=surface, canonical_key=key, canonical_id='canonical:' + key, kind='entity')
        for surface, key in pairs
    )


def test_an_unchanged_revision_costs_nothing():
    verdict = assess_novelty(index=index(), units=[unit('line:1', '市场营销中心负责预算')],
                             revision_changed=False)
    assert verdict.tier == SKIP
    assert verdict.reason == 'source_revision_unchanged'
    assert verdict.spends_money is False


def test_unchanged_bytes_are_judged_again_when_the_caller_asks():
    # The revision is stable, but nobody ever read it: an outline staged before its material
    # had names must not stay unmodelled forever because the file on disk did not move.
    verdict = assess_novelty(index=index(), units=[unit('line:1', '新设数字化运营中心，负责集团数据资产。')],
                             revision_changed=False, rejudge=True)
    assert verdict.tier == PROPOSE
    assert verdict.reason == 'unresolved_entity_names'


def test_rejudging_bytes_that_were_already_proposed_does_not_pay_again():
    verdict = assess_novelty(index=index(), units=[unit('line:1', '新设数字化运营中心，负责集团数据资产。')],
                             revision_changed=False, rejudge=True, already_proposed=True)
    assert verdict.tier == SKIP
    assert verdict.reason == 'candidate_already_staged'
    assert verdict.spends_money is False


def test_a_document_with_nothing_extractable_costs_nothing():
    verdict = assess_novelty(index=index(), units=[])
    assert verdict.tier == SKIP
    assert verdict.reason == 'no_extractable_text'


def test_every_name_resolved_and_no_rule_dialect_means_link_only():
    built = index(('市场营销中心', 'center'), ('工程管理中心', 'engineering'))
    verdict = assess_novelty(
        index=built,
        units=[unit('line:1', '市场营销中心与工程管理中心联合评审。')],
        dialect_claims=0,
    )
    assert verdict.tier == LINK_ONLY
    assert verdict.spends_money is False
    assert verdict.known_ratio == 1.0


def test_an_unresolved_name_is_why_we_pay():
    built = index(('市场营销中心', 'center'))
    verdict = assess_novelty(
        index=built,
        units=[unit('line:1', '新设数字化运营中心，隶属市场营销中心。')],
    )
    assert verdict.tier == PROPOSE
    assert '数字化运营中心' in verdict.unknown_surfaces
    assert verdict.spends_money is True


def test_rule_dialect_without_an_accepted_claim_is_also_novel():
    verdict = assess_novelty(
        index=index(),
        units=[unit('line:1', '合同金额不得超过五十万元。')],
        dialect_claims=3,
    )
    assert verdict.tier == PROPOSE
    assert verdict.reason == 'rule_dialect_present_without_accepted_claim'


def test_a_reviewer_can_always_ask_for_a_full_reading():
    verdict = assess_novelty(index=index(), units=[unit('line:1', 'x')], force_full=True)
    assert verdict.tier == FULL
    assert verdict.spends_money is True


def test_known_names_are_not_reported_as_unknown_candidates():
    built = index(('工程管理中心', 'engineering'))
    candidates = candidate_surfaces([unit('line:1', '工程管理中心与安全监督中心')], built)
    assert '工程管理中心' not in candidates
    assert '安全监督中心' in candidates


def test_candidate_surfaces_are_bounded_and_deterministic():
    units = [unit(f'line:{index_}', f'第{index_}个临时委员会负责') for index_ in range(80)]
    first = candidate_surfaces(units, index())
    second = candidate_surfaces(units, index())
    assert first == second
    assert len(first) <= 40


def test_the_receipt_is_written_outside_the_store(tmp_path):
    built = index()
    verdict = assess_novelty(index=built, units=[unit('line:1', '新设战略投资部')],
                             source_id='source_x', source_revision='a' * 64)
    path = write_receipt(tmp_path, verdict)
    assert path.is_file()
    stored = json.loads(path.read_text(encoding='utf-8'))
    assert stored['spends_money'] is True
    assert stored['tier'] == PROPOSE
    assert path.parent.name == 'novelty'
    assert read_receipts(tmp_path)[0]['source_id'] == 'source_x'


class _ReachedTheModel(Exception):
    """Raised by the stub when the paid path is actually entered."""


class _StubPort:
    def understand(self, request, *, source_root):  # noqa: ARG002
        raise _ReachedTheModel()


def make_wiki(tmp_path) -> ProjectWiki:
    return ProjectWiki(tmp_path / 'workspace', [tmp_path], enterprise_id='enterprise', project_id='project')


def test_a_single_short_note_does_not_reach_the_model(tmp_path, monkeypatch):
    # A note is not a page: prose only pays once a document is mostly prose.

    monkeypatch.setattr(knowledge_intake, 'UnderstandPort', _StubPort)
    wiki = make_wiki(tmp_path)
    path = tmp_path / 'memo.md'
    path.write_text('今天的会议改到下午三点。\n', encoding='utf-8')

    outcome = knowledge_intake.intake_source(wiki, path)

    assert outcome['status'] == 'LINKED_ONLY'
    assert outcome['understand_status'] == 'not_called'
    assert outcome['novelty']['tier'] == LINK_ONLY
    assert outcome['novelty_receipt']


def test_a_new_org_name_does_reach_the_model(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_intake, 'UnderstandPort', _StubPort)
    wiki = make_wiki(tmp_path)
    path = tmp_path / 'reorg.md'
    path.write_text('新设数字化运营中心，负责集团数据资产。\n', encoding='utf-8')

    with pytest.raises(_ReachedTheModel):
        knowledge_intake.intake_source(wiki, path)


def test_the_second_intake_of_the_same_bytes_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_intake, 'UnderstandPort', _StubPort)
    wiki = make_wiki(tmp_path)
    path = tmp_path / 'memo.md'
    path.write_text('今天的会议改到下午三点。\n', encoding='utf-8')

    knowledge_intake.intake_source(wiki, path)
    second = knowledge_intake.intake_source(wiki, path)

    assert second['status'] == 'SKIPPED'
    assert second['source']['status'] == 'no_op'
    assert second['novelty']['reason'] == 'source_revision_unchanged'

def test_an_unchanged_document_nobody_modelled_is_judged_again(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge_intake, 'UnderstandPort', _StubPort)
    wiki = make_wiki(tmp_path)
    path = tmp_path / 'reorg.md'
    path.write_text('新设数字化运营中心，负责集团数据资产。\n', encoding='utf-8')

    with pytest.raises(_ReachedTheModel):
        knowledge_intake.intake_source(wiki, path)
    unchanged = knowledge_intake.intake_source(wiki, path)

    assert unchanged['status'] == 'SKIPPED'
    with pytest.raises(_ReachedTheModel):
        knowledge_intake.intake_source(wiki, path, rejudge=True)


def test_a_sentence_that_ends_in_a_suffix_is_not_a_name():
    # An outside audit of 40 unknown surfaces (2026-10-31) found these four: each ends in
    # 部 or 室, and each is a sentence about an organisation rather than its name.
    built = index()
    surfaces = candidate_surfaces(
        [unit('line:1', '看外部，审视企业外部，找到主责部门，企管转到办公室。')], built)

    assert surfaces == ()


def test_a_role_a_time_and_a_cut_name_are_not_names():
    built = index()
    surfaces = candidate_surfaces(
        [unit('line:1', '上半年公司责任部门与承办部门会同公司本部，见有限公司文件。')], built)

    assert surfaces == ()


def test_real_names_survive_the_proposal_filter():
    # The same audit's 21 real names, including the ones whose opening word looks like
    # noise (公司防汛指挥部) or whose tail is a role word (资料整编部门).
    built = index()
    text = '法务风控部、资料整编部门、公司防汛指挥部、中建六局水电公司、南水北调集团。'

    surfaces = candidate_surfaces([unit('line:1', text)], built)

    for name in ('法务风控部', '资料整编部门', '公司防汛指挥部', '中建六局水电公司', '南水北调集团'):
        assert name in surfaces


def test_an_anonymous_type_is_not_an_organisation():
    # "大型投资集团", "专业化子公司": a class of organisations, not one of them.
    built = index()
    surfaces = candidate_surfaces(
        [unit('line:1', '打造专业化子公司，对标大型投资集团与区域化分公司。')], built)

    assert surfaces == ()


def test_a_clause_that_opens_with_an_evaluation_is_not_a_name():
    built = index()
    surfaces = candidate_surfaces([unit('line:1', '获评天津市企业技术中心，严格落实党管干部。')], built)

    assert surfaces == ()


def test_a_document_whose_only_unknowns_are_sentences_stays_free():
    built = index()
    verdict = assess_novelty(
        index=built,
        units=[unit('line:1', '分管领导要看外部，明确外部责任部门与承办部门。')],
    )

    assert verdict.tier == LINK_ONLY
    assert verdict.spends_money is False


def _sentence(index_: int) -> _TextUnit:
    return unit(f"line:{index_}", f"本季度经营分析会改为下午三点召开，请提前准备第{index_}份材料。")


def _rule_line(index_: int) -> _TextUnit:
    return unit(f"line:r{index_}", f"合同金额不得超过五十万元，第{index_}类事项逾期须书面说明。")


def test_a_truncated_reading_is_not_called_nothing_new():
    verdict = assess_novelty(index=index(), units=[unit('line:1', '甲 乙 丙')], truncated=True,
                             unread_locators=1870)
    assert verdict.tier == UNREAD
    assert verdict.reason == 'unread_part_cannot_be_judged'
    assert verdict.spends_money is False
    assert verdict.unread_locators == 1870


def test_a_truncated_reading_with_a_new_name_still_pays():
    built = index(('市场营销中心', 'center'))
    verdict = assess_novelty(index=built, units=[unit('line:1', '新设数字化运营中心')], truncated=True)
    assert verdict.tier == PROPOSE
    assert verdict.reason == 'unresolved_entity_names'


def test_a_page_of_prose_pays_even_with_no_new_name():
    verdict = assess_novelty(index=index(), units=[_sentence(item) for item in range(1, 11)])
    assert verdict.tier == PROPOSE
    assert verdict.reason == 'prose_without_unresolved_names'
    assert verdict.prose_density >= 0.35


def test_rule_language_pays_without_naming_any_new_organisation():
    verdict = assess_novelty(index=index(), units=[_rule_line(item) for item in range(1, 10)])
    assert verdict.tier == PROPOSE
    assert verdict.reason == 'rule_language_present'
    assert verdict.rule_unit_count >= 8


def test_an_outline_of_a_source_read_whole_stays_free():
    verdict = assess_novelty(
        index=index(), units=[_sentence(item) for item in range(1, 11)],
        source_name='03_经营计划/大纲_年度经营计划.md',
        siblings={'03_经营计划/年度经营计划-202506028（汇报版）.pptx': 'PARSED'},
    )
    assert verdict.tier == LINK_ONLY
    assert verdict.reason.startswith('covered_by_sibling:')
    assert verdict.covered_by == '03_经营计划/年度经营计划-202506028（汇报版）.pptx'
    assert verdict.spends_money is False


def test_an_outline_is_covered_even_when_the_material_was_read_in_part():
    # The outline states nothing its own material does not, so a partly read material
    # still stands for it; the shortfall is reported on the material's own page.
    verdict = assess_novelty(
        index=index(), units=[_sentence(item) for item in range(1, 11)],
        source_name='大纲_年度经营计划.md',
        siblings={'年度经营计划-202506028（汇报版）.pptx': 'PARSED_TRUNCATED'},
    )
    assert verdict.covered_by == '年度经营计划-202506028（汇报版）.pptx'
    assert verdict.tier == LINK_ONLY


def test_an_outline_of_a_source_never_read_is_not_covered():
    verdict = assess_novelty(
        index=index(), units=[_sentence(item) for item in range(1, 11)],
        source_name='大纲_年度经营计划.md',
        siblings={'年度经营计划-202506028（汇报版）.pptx': 'NOT_PARSED'},
    )
    assert verdict.covered_by is None
    assert verdict.tier == PROPOSE


def test_only_a_name_that_says_outline_may_be_covered():
    verdict = assess_novelty(
        index=index(), units=[_sentence(item) for item in range(1, 11)],
        source_name='年度经营计划.md',
        siblings={'年度经营计划-202506028（汇报版）.pptx': 'PARSED'},
    )
    assert verdict.covered_by is None


def test_a_file_that_only_names_files_is_not_novel():
    units = [unit('line:1', '`04_制度流程与标准化/2025-07_制度优化总结/制度优化总结汇报7.18.pptx`'),
             unit('line:2', '水利集团战略纲要-20250321(定稿).pptx、水利集团战略纲要.md')]
    verdict = assess_novelty(index=index(), units=units)
    assert verdict.tier == LINK_ONLY
    assert verdict.unknown_surfaces == ()
