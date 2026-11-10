"""A duty, an event and a condition read the same way from a candidate row or an accepted one.

The tests below hold the two promises batch 2A makes: an object is displayed with the identity,
the qualification and the citation it was saved with - never recomputed, never softened into
"confirmed" - and an object nothing was saved against is reported, not hung on the nearest name.
"""
from catalyst_platform.object_view import (
    attached_to,
    collect,
    from_item,
    from_meaning,
    role_keys,
    unattached,
)
from catalyst_platform.wiki_pages import project

SPAN = {
    'source_id': 'source_a', 'source_revision': 'r1', 'locator': 'ppt/slides/slide9.xml#text:2',
    'line_start': 12, 'line_end': 12, 'span_sha256': 'a' * 64,
    'evidence_class': 'inferred', 'freshness_status': 'unknown',
}


def entity(meaning_id, key, title, canonical_id):
    return {
        'meaning_id': meaning_id, 'kind': 'entity', 'key': key, 'canonical_key': key,
        'canonical_id': canonical_id, 'meaning': title, 'business_type': 'Department',
        'freshness_status': 'unknown', 'evidence': [dict(SPAN)],
    }


def duty(meaning_id, key, text, holder, *, qualification='pending',
         basis='duty_attached_to_another_unit', verification='unconfirmed',
         scope_state='proposed', evidence=None):
    return {
        'meaning_id': meaning_id, 'kind': 'duty', 'key': key, 'meaning': text,
        'holder': holder, 'qualification': qualification, 'qualification_basis': basis,
        'verification': verification, 'scope_state': scope_state,
        'evidence_class': 'inferred', 'evidence': evidence if evidence is not None else [dict(SPAN)],
    }


def event(meaning_id, key, text, before, after, **extra):
    row = {
        'meaning_id': meaning_id, 'kind': 'event', 'key': key, 'meaning': text,
        'from': list(before), 'to': list(after), 'predicate': '合并',
        'qualification': 'pending', 'qualification_basis': 'roles_or_endpoints_unsettled',
        'verification': 'unconfirmed', 'scope_state': 'proposed',
        'evidence_class': 'inferred', 'evidence': [dict(SPAN)],
    }
    row.update(extra)
    return row


def condition(meaning_id, key, text, applies_to):
    return {
        'meaning_id': meaning_id, 'kind': 'condition', 'key': key, 'meaning': text,
        'applies_to': list(applies_to), 'unattached': not applies_to,
        'evidence_class': 'inferred', 'evidence': [dict(SPAN)],
    }


TITLES = {'source_a': 'org.pptx'}
PAGES = {'zongbu': ('总部', 'entities/zongbu.md'), 'bumen': ('各部门', 'entities/bumen.md')}


# --------------------------------------------------------------------- the adapters
def test_a_pending_object_is_shown_as_the_row_saved_it():
    row = duty('m1', 'duty_kaizhan', '开展全公司干部竞岗', 'bumen',
               evidence=[dict(SPAN), dict(SPAN), dict(SPAN)])
    view = from_meaning(row, scope_id='enterprise:e/project:p', version_id='v1',
                        entities=PAGES, titles=TITLES)
    # Three readable spans do not turn a pending reading into a confirmed one.
    assert view.qualification == 'pending'
    assert view.qualification_label.startswith('待审')
    assert view.verification == 'unconfirmed'
    assert view.basis == 'duty_attached_to_another_unit'
    assert '挂在另一个单位名下' in view.basis_label
    assert '已确认' not in view.qualification_label
    assert len(view.citations) == 3
    assert view.identity['version_id'] == 'v1'
    assert view.origin == 'accepted_meaning'


def test_a_candidate_entry_keeps_its_candidate_and_its_own_span():
    entry = {
        'meaning_id': 'meaning_abc', 'kind': 'duty', 'key': 'duty_x',
        'meaning': '负责分公司项目具体执行', 'holder': 'bumen',
        'qualification': 'pending', 'qualification_basis': 'duty_attached_to_another_unit',
        'verification': 'unconfirmed', 'scope_state': 'current',
        'source_id': 'source_a', 'source_revision': 'r1', 'line_start': 24, 'line_end': 24,
        'span_sha256': 'b' * 64, 'evidence_class': 'inferred',
    }
    view = from_item(entry, scope_id='enterprise:e/project:p', candidate_id='candidate_1',
                     entities=PAGES, titles=TITLES)
    assert view.origin == 'candidate_entry'
    assert view.identity['candidate_id'] == 'candidate_1'
    assert view.identity['meaning_id'] == 'meaning_abc'
    assert view.identity['source'] == 'candidate_entry'
    assert len(view.citations) == 1
    # The span records an evidence class but not whether the source is derived, so the
    # origin is unknown - an inferred class does not stand in for "this is the original".
    assert view.citations[0].derived is None
    assert '来源属性未记录' in view.citations[0].line()
    assert 'line:24' in view.citations[0].line()
    assert '没有回读原件' in view.citations[0].line()


def test_an_accepted_meaning_without_an_evidence_list_still_cites_its_recorded_span():
    row = duty('m1', 'duty_x', '负责某项目', 'bumen', evidence=[])
    row['source_id'] = 'source_a'
    row['line_start'] = 7
    row['line_end'] = 7
    view = from_meaning(row, entities=PAGES, titles=TITLES)
    assert len(view.citations) == 1
    assert 'line:7' in view.citations[0].line()


def test_a_condition_without_an_applies_to_is_reported_not_attached():
    rows = [condition('m1', 'cond_a', '以下发供参考的方式给出', [])]
    views = collect(rows, entities=PAGES, titles=TITLES)
    assert views[0].unattached is True
    assert role_keys(rows[0]) == ()
    assert unattached(views) == views
    for key in ('zongbu', 'bumen'):
        assert attached_to(views, key) == ()


def test_only_saved_role_keys_attach_an_object():
    # The statement names 总部, but the row was saved as held by 各部门: a reader is not
    # allowed to move it to the unit that happens to be mentioned.
    rows = [
        entity('e1', 'bumen', '各部门', 'c1'),
        entity('e2', 'zongbu', '总部', 'c2'),
        duty('m1', 'duty_x', '总部与各部门共同开展竞岗', 'bumen'),
    ]
    views = collect(rows, entities=PAGES, titles=TITLES)
    assert attached_to(views, 'bumen')
    assert attached_to(views, 'zongbu') == ()
    assert role_keys(rows[2]) == ('bumen',)


def test_an_event_is_read_as_two_sides_not_as_one_unit():
    row = event('m1', 'si_fengongsi_hebing', '四分公司与投资管理中心合并', ['si'], ['touzi'])
    view = from_meaning(row, titles=TITLES)
    assert [role.label for role in view.roles] == ['起点', '终点']
    assert view.keys == ('si', 'touzi')
    # Neither side has a page in this fixture, so both stay keys rather than a guessed title.
    assert view.roles[0].resolved is False
    assert len(view.unresolved_roles) == 2


def test_an_object_carries_what_the_record_says_is_unsettled():
    row = event('m1', 'si_hebing', '四分公司合并到智静', ['si'], ['zhi'],
                uncertainty='页面未写生效日期')
    view = from_meaning(row, titles=TITLES)
    assert view.to_dict()['unsettled'] == '页面未写生效日期'
    assert view.to_dict()['unsettled_source'] == 'uncertainty'
    # An absence recorded on the row itself is shown as recorded, not as a guess.
    absent = {'meaning_id': 'm2', 'kind': 'unknown', 'key': 'unknown_x',
              'meaning': '这一页没有说明现状还是方案',
              'observed_absence': '整页没有出现「现状」「方案」这类界定词'}
    assert from_meaning(absent, titles=TITLES).to_dict()['unsettled_source'] == 'observed_absence'


def test_an_object_with_no_recorded_uncertainty_says_so():
    view = from_meaning(event('m1', 'si_hebing', '四分公司合并到智静', ['si'], ['zhi']),
                        titles=TITLES)
    assert view.to_dict()['unsettled'] is None
    assert view.to_dict()['unsettled_source'] is None



# --------------------------------------------------------------------- the pages
class FakeWiki:
    """The read surface the projection is allowed to use, and nothing else."""

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


def store(tmp_path):
    meanings = [
        entity('e1', 'bumen', '各部门', 'c1'),
        entity('e2', 'zongbu', '总部', 'c2'),
        duty('m1', 'duty_bumen_jinggang', '「各部门：开展全公司干部竞岗」', 'bumen'),
        event('m2', 'si_hebing', '四分公司并入投资管理中心', ['bumen'], ['zongbu']),
        condition('m3', 'cond_unnamed', '组织架构以下发供参考的方式给出', []),
    ]
    sources = [{
        'source_id': 'source_a', 'scope_id': 'enterprise:e/project:p', 'relative_path': 'org.pptx',
        'revision': 'r1', 'source_format': 'pptx', 'extraction': {'status': 'complete'},
    }]
    return FakeWiki(tmp_path, meanings, sources)


def page_of(pages, path):
    return next(page for page in pages.pages if page.path == path)


def test_an_entity_page_shows_its_duty_holder_and_why_it_is_pending(tmp_path):
    pages = project(store(tmp_path))
    bumen = page_of(pages, 'entities/bumen.md')
    body = bumen.content.split('## 职责')[1].split('## 参与事件')[0]
    assert '「各部门：开展全公司干部竞岗」' in body
    assert '持有者：各部门（`entities/bumen.md`）' in body
    assert '待审（pending）' in body
    assert '未经校验（unconfirmed）' in body
    assert 'duty_attached_to_another_unit' in body
    assert '派生记录（inferred）' in body
    assert '没有回读原件' in body
    assert '意味' not in body  # no invented reason line
    assert 'duty_count: 1' in bumen.content
    assert 'event_count: 1' in bumen.content   # it is the event's starting side
    assert 'condition_count: 0' in bumen.content


def test_an_entity_page_says_what_it_does_not_have(tmp_path):
    pages = project(store(tmp_path))
    zongbu = page_of(pages, 'entities/zongbu.md')
    assert '已接受的知识里没有以它持有的职责。' in zongbu.content
    assert '终点：总部（`entities/zongbu.md`）' in zongbu.content
    assert 'roles_or_endpoints_unsettled' in zongbu.content
    assert '已接受的知识里没有挂在它名下的条件或例外。' in zongbu.content


def test_an_entity_page_writes_what_is_still_unsettled(tmp_path):
    meanings = [
        entity('e1', 'bumen', '各部门', 'c1'),
        entity('e2', 'zongbu', '总部', 'c2'),
        event('m1', 'si_hebing', '四分公司并入投资管理中心', ['bumen'], ['zongbu'],
              uncertainty='页面未写生效日期'),
    ]
    sources = [{
        'source_id': 'source_a', 'scope_id': 'enterprise:e/project:p', 'relative_path': 'org.pptx',
        'revision': 'r1', 'source_format': 'pptx', 'extraction': {'status': 'complete'},
    }]
    pages = project(FakeWiki(tmp_path, meanings, sources))
    bumen = page_of(pages, 'entities/bumen.md')
    assert '尚未确认（记录）：页面未写生效日期' in bumen.content
    # The recorded uncertainty is quoted, never paraphrased into a certainty or a guess.
    assert '已发生' not in bumen.content


def test_an_entity_page_without_a_recorded_uncertainty_says_so(tmp_path):
    pages = project(store(tmp_path))
    zongbu = page_of(pages, 'entities/zongbu.md')
    assert '尚未确认：没有记录未确认项' in zongbu.content


def test_the_overview_counts_the_objects_and_names_the_unattached_one(tmp_path):
    pages = project(store(tmp_path))
    overview = page_of(pages, 'overview.md').content
    assert '职责 1 条、事件 1 条、条件 1 条' in overview
    assert '其中未挂到任何对象 1 条' in overview
    assert '`cond_unnamed`' in overview


def test_a_role_key_with_no_page_stays_a_key(tmp_path):
    meanings = [duty('m1', 'duty_x', '负责某事', 'unit_without_page')]
    sources = [{
        'source_id': 'source_a', 'scope_id': 'enterprise:e/project:p', 'relative_path': 'org.pptx',
        'revision': 'r1', 'source_format': 'pptx', 'extraction': {'status': 'complete'},
    }]
    # No entity page is written at all, so the projection has nothing to attach the duty to.
    pages = project(FakeWiki(tmp_path, meanings, sources))
    assert not any(page.path.startswith('entities/') for page in pages.pages)
    overview = page_of(pages, 'overview.md').content
    # The row saved a holder, but no object stands for that key: the duty is not on any page,
    # so the overview counts it as unattached and names the key that could not be resolved.
    assert '职责 1 条' in overview
    assert '其中未挂到任何对象 1 条' in overview
    assert '`duty_x`' in overview
    assert 'unit_without_page' in overview


def test_page_bytes_stay_a_function_of_the_store(tmp_path):
    wiki = store(tmp_path)
    first = project(wiki)
    second = project(wiki)
    assert [page.content for page in first.pages] == [page.content for page in second.pages]
