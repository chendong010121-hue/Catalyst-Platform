"""Three boundaries an object view and an opinion have to hold before a graph builds on them.

Each of these was measured false on the shipped code and is fixed in the same patch:

* an opinion's digest must cover what a reviewer actually judges - the holder, the
  qualification, the verification and the evidence links - not only the display text;
* whether a source is derived is a property of the source, not a reading of its evidence
  class, and a span that does not say has to say "unknown" rather than "not derived";
* a condition saved against a duty has to reach the duty's holder page, and one that points
  at nothing has to be listed instead of disappearing from the projection.
"""
from catalyst_platform.object_view import collect, from_meaning, unattached
from catalyst_platform.review_surface import _row_text, digest_source, item_digest
from catalyst_platform.wiki_pages import project

SPAN = {
    'source_id': 'source_a', 'source_revision': 'r1', 'locator': 'ppt/slides/slide9.xml#text:2',
    'line_start': 12, 'line_end': 12, 'span_sha256': 'a' * 64,
    'evidence_class': 'inferred', 'freshness_status': 'unknown',
}
TITLES = {'source_a': 'org.pptx'}
PAGES = {'bumen': ('各部门', 'entities/bumen.md')}


def entity(meaning_id, key, title, canonical_id):
    return {
        'meaning_id': meaning_id, 'kind': 'entity', 'key': key, 'canonical_key': key,
        'canonical_id': canonical_id, 'meaning': title, 'business_type': 'Department',
        'freshness_status': 'unknown', 'evidence': [dict(SPAN)],
    }


def duty(meaning_id, key, text, holder, **extra):
    row = {
        'meaning_id': meaning_id, 'kind': 'duty', 'key': key, 'meaning': text,
        'holder': holder, 'qualification': 'pending',
        'qualification_basis': 'duty_attached_to_another_unit',
        'verification': 'unconfirmed', 'scope_state': 'proposed',
        'evidence_class': 'inferred', 'evidence': [dict(SPAN)],
    }
    row.update(extra)
    return row


def condition(meaning_id, key, text, applies_to, **extra):
    row = {
        'meaning_id': meaning_id, 'kind': 'condition', 'key': key, 'meaning': text,
        'applies_to': list(applies_to), 'unattached': not applies_to,
        'evidence_class': 'inferred', 'evidence': [dict(SPAN)],
    }
    row.update(extra)
    return row


# ------------------------------------------------------------------ 1. the digest
def test_an_opinion_digest_covers_what_a_reviewer_judges():
    base = duty('m1', 'duty_x', '负责分公司项目具体执行', 'bumen')
    base['item_id'] = 'item_1'
    base['evidence_refs'] = [{'evidence_id': 'e1', 'source_id': 'source_a', 'line': 12}]
    baseline = item_digest(base)

    for field, value in (
        ('holder', 'zongbu'),
        ('qualification', 'stated'),
        ('qualification_basis', 'content_read_by_inference'),
        ('verification', 'confirmed'),
        ('meaning', '负责别的项目'),
        ('key', 'duty_y'),
        ('evidence_refs', [{'evidence_id': 'e2', 'source_id': 'source_a', 'line': 12}]),
    ):
        changed = dict(base)
        changed[field] = value
        assert item_digest(changed) != baseline, field


def test_the_review_row_digest_sees_fields_the_page_does_not_show():
    # product_rows builds a display row (seven fields) and a hand-off item (many more). The
    # digest has to be taken over the item, or the saved roles and evidence could change under
    # an opinion nobody re-read.
    item = {
        'item_id': 'item_1', 'kind': 'relation', 'key': 'market_under_group',
        'meaning': '市场营销中心隶属该集团', 'evidence_class': 'inferred',
        'subject': 'shichang_yingxiao_zhongxin', 'object': 'tianjin_shuili_jituan',
        'predicate': '隶属', 'confidence': 'not_calibrated',
        'evidence_refs': ['ev_a', 'ev_b'],
    }
    row = _row_text(item)
    baseline = item_digest(digest_source(row, item))
    assert item_digest(digest_source(row, dict(item))) == baseline
    for field, value in (
        ('subject', 'another_unit'),
        ('object', 'another_group'),
        ('predicate', '包含'),
        ('evidence_refs', ['ev_a']),
        ('evidence_refs', ['ev_a', 'ev_c']),
    ):
        changed = dict(item)
        changed[field] = value
        assert item_digest(digest_source(row, changed)) != baseline, (field, value)


# ------------------------------------------------------------------ 2. derived
def test_derived_is_read_from_the_source_not_from_its_evidence_class():
    row = duty('m1', 'duty_x', '负责某事', 'bumen')
    span = dict(SPAN, evidence_class='observed_from_source', derived=True)
    view = from_meaning(dict(row, evidence=[span]), entities=PAGES, titles=TITLES)
    assert view.citations[0].derived is True
    assert '派生来源' in view.citations[0].line()

    span = dict(SPAN, evidence_class='inferred', derived=False)
    view = from_meaning(dict(row, evidence=[span]), entities=PAGES, titles=TITLES)
    assert view.citations[0].derived is False

    span = dict(SPAN, evidence_class='inferred')
    span.pop('derived', None)
    view = from_meaning(dict(row, evidence=[span]), entities=PAGES, titles=TITLES)
    assert view.citations[0].derived is None
    assert '来源属性未记录' in view.citations[0].line()


# ------------------------------------------------------------------ 3. attachment
class FakeWiki:
    def __init__(self, tmp_path, meanings, sources):
        self._meanings = meanings
        self._sources = sources
        self.workspace = tmp_path / 'workspace'
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.roots = (tmp_path,)

    def accepted_meanings(self):
        return {'scope_id': 'enterprise:e/project:p', 'active_version_id': 'v1',
                'meanings': self._meanings}

    def sources(self):
        return self._sources

    def source_record(self, source_id):
        return next(row for row in self._sources if row['source_id'] == source_id)

    def semantic_state(self):
        return {'transitions': []}


SOURCES = [{
    'source_id': 'source_a', 'scope_id': 'enterprise:e/project:p', 'relative_path': 'org.pptx',
    'revision': 'r1', 'source_format': 'pptx', 'extraction': {'status': 'complete'},
}]


def page_of(pages, path):
    return next(page for page in pages.pages if page.path == path)


def test_a_condition_saved_against_a_duty_reaches_the_holders_page(tmp_path):
    meanings = [
        entity('e1', 'bumen', '各部门', 'c1'),
        duty('m1', 'd1', '负责分公司项目具体执行', 'bumen'),
        condition('m2', 'cond_1', '仅在收到批复后执行', ['d1']),
    ]
    pages = project(FakeWiki(tmp_path, meanings, SOURCES))
    bumen = page_of(pages, 'entities/bumen.md')
    assert '仅在收到批复后执行' in bumen.content
    overview = page_of(pages, 'overview.md').content
    assert '未挂到任何对象 0 条' in overview

    views = collect(meanings, entities=PAGES, titles=TITLES)
    assert unattached(views) == ()


def test_a_condition_pointing_at_nothing_is_listed_not_dropped(tmp_path):
    meanings = [
        entity('e1', 'bumen', '各部门', 'c1'),
        duty('m1', 'd1', '负责某事', 'bumen'),
        condition('m2', 'cond_lost', '以下发供参考的方式给出', ['d_missing']),
    ]
    pages = project(FakeWiki(tmp_path, meanings, SOURCES))
    overview = page_of(pages, 'overview.md').content
    assert '未挂到任何对象 1 条' in overview
    assert '`cond_lost`' in overview


def test_every_object_is_either_on_a_page_or_counted_as_unattached(tmp_path):
    meanings = [
        entity('e1', 'bumen', '各部门', 'c1'),
        entity('e2', 'zongbu', '总部', 'c2'),
        duty('m1', 'd1', '负责某事', 'bumen'),
        duty('m2', 'd2', '负责另一件事', ''),
        condition('m3', 'cond_1', '仅在批复后执行', ['d1']),
        condition('m4', 'cond_lost', '不确定挂在哪里', ['d_missing']),
    ]
    pages = project(FakeWiki(tmp_path, meanings, SOURCES))
    raw = [row for row in meanings if row['kind'] in {'duty', 'event', 'condition'}]
    views = collect(meanings, entities=PAGES, titles=TITLES)
    assert len(views) == len(raw)
    listed = len(unattached(views))
    on_pages = len(views) - listed
    overview = page_of(pages, 'overview.md').content
    total_line = next(line for line in overview.splitlines() if line.startswith('- 业务对象：'))
    counts = {kind: int(total_line.split(f'{label} ')[1].split(' ')[0])
              for kind, label in (('duty', '职责'), ('event', '事件'), ('condition', '条件'))}
    assert counts == {'duty': 2, 'event': 0, 'condition': 2}
    assert f'其中未挂到任何对象 {listed} 条' in overview
    # Conservation: every object is on a page or in the unattached list, never both, never neither.
    assert on_pages + listed == len(raw)
