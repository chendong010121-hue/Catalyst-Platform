"""The resident wiki is a projection: same store, same bytes, and a human edit is kept."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import catalyst_platform.wiki_pages
from catalyst_platform.ontology_concepts import concept_set_of, empty_concept_state
from catalyst_platform.understand_models import _TextUnit
from catalyst_platform.wiki import WikiUnavailable
from catalyst_platform.wiki_pages import (
    PROJECTION_VERSION,
    Page,
    PageSet,
    diverged_pages,
    link_report,
    materialize,
    page_link_index,
    project,
    scan_sources,
)


def unit(locator: str, quote: str, source_id: str = 'source_a') -> _TextUnit:
    return _TextUnit(source_id, 'org.pptx', 'revision', 'revision', locator, quote)


def meaning(meaning_id, kind, key, text, *, canonical_id=None, business_type=None,
            evidence=None, **extra):
    row = {
        'meaning_id': meaning_id,
        'kind': kind,
        'key': key,
        'meaning': text,
        'canonical_key': key,
        'canonical_id': canonical_id,
        'business_type': business_type,
        'freshness_status': 'fresh',
        'evidence': evidence or [{
            'source_id': 'source_a', 'source_revision': 'r1', 'locator': 'ppt/slides/slide9.xml#text:2',
            'line_start': 1, 'line_end': 1, 'span_sha256': 'a' * 64,
            'evidence_class': 'observed_from_source', 'freshness_status': 'fresh',
        }],
    }
    row.update(extra)
    return row


class FakeWiki:
    """The read surface the projection is allowed to use, and nothing else."""

    def __init__(self, tmp_path: Path, meanings, sources):
        self._meanings = meanings
        self._sources = sources
        self.workspace = tmp_path / 'workspace'
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.roots = (tmp_path,)

    def accepted_meanings(self):
        return {'scope_id': 'enterprise:e/project:p', 'active_version_id': 'v1', 'meanings': self._meanings}

    def sources(self):
        return self._sources

    def source_record(self, source_id):
        return next(row for row in self._sources if row['source_id'] == source_id)

    def semantic_state(self):
        return {'transitions': [{'transition_id': 't1', 'operation': 'candidate.decide',
                                 'actor_origin': 'manager_acceptance', 'status': 'awaiting_terminal'}]}


def wiki_with(tmp_path):
    center = meaning('m1', 'entity', 'marketing_center', '市场营销中心',
                     canonical_id='c1', business_type='Department')
    hq = meaning('m2', 'entity', 'zongbu', '总部', canonical_id='c2', business_type='Department')
    relation = meaning('m3', 'relation', 'k', '@c1 隶属 @c2', canonical_id=None,
                       canonical_subject_id='c1', canonical_object_id='c2', predicate_key='隶属')
    alias = meaning('m4', 'alias', '营销中心', '营销中心', canonical_id='c1')
    meanings = [center, hq, relation, alias]
    sources = [{
        'source_id': 'source_a', 'scope_id': 'enterprise:e/project:p', 'relative_path': 'org.pptx',
        'revision': 'r1', 'source_format': 'pptx',
        'extraction': {'status': 'truncated', 'unit_count': 500, 'locator_count': 2242,
                       'truncated': True, 'part_errors': [], 'vision_missing': ['NEEDS_VISION:x']},
    }]
    return FakeWiki(tmp_path, meanings, sources)


def test_an_entity_page_carries_its_evidence_and_its_relations(tmp_path):
    pages = project(wiki_with(tmp_path))
    entity = next(page for page in pages.pages if page.path == 'entities/marketing_center.md')
    assert '市场营销中心' in entity.content
    assert 'ppt/slides/slide9.xml#text:2' in entity.content
    assert '营销中心' in entity.content          # the accepted alias
    assert '总部' in entity.content              # the relation target, by name not key
    assert f'generated_from: "{PROJECTION_VERSION}:' in entity.content


def test_a_short_generic_name_is_shown_as_unconfirmed_not_as_a_mention(tmp_path):
    wiki = wiki_with(tmp_path)
    scan = {'source_a': (unit('ppt/slides/slide2.xml#text:1', '总部与分子公司的关系'),)}
    pages = project(wiki, scan=scan)
    hq = next(page for page in pages.pages if page.path == 'entities/zongbu.md')
    assert '未确认' in hq.content
    assert '总部与分子公司的关系' not in hq.content
    assert '不作为识别' in hq.content


def test_the_same_store_projects_to_the_same_bytes(tmp_path):
    wiki = wiki_with(tmp_path)
    first = project(wiki)
    second = project(wiki)
    assert [page.content for page in first.pages] == [page.content for page in second.pages]


def test_materialize_is_idempotent(tmp_path):
    wiki = wiki_with(tmp_path)
    pages = project(wiki).pages
    root = tmp_path / 'wiki-pages'
    first = materialize(pages, root)
    second = materialize(project(wiki).pages, root)
    assert first['written'] and not second['written']
    assert (root / 'overview.md').is_file()
    assert (root / 'index.md').is_file()
    assert (root / '.projection.json').is_file()


def test_a_human_edit_is_kept_and_reported(tmp_path):
    wiki = wiki_with(tmp_path)
    root = tmp_path / 'wiki-pages'
    materialize(project(wiki, root=root).pages, root)
    target = root / 'entities/marketing_center.md'
    edited = target.read_text(encoding='utf-8') + '\n人工补注：这一段尚未核实。\n'
    target.write_text(edited, encoding='utf-8')

    pages = project(wiki, root=root)
    outcome = materialize(pages, root)

    assert 'entities/marketing_center.md' in outcome['diverged']
    assert target.read_text(encoding='utf-8') == edited
    assert 'entities/marketing_center.md' in diverged_pages(pages.pages, root)


def test_a_truncated_source_says_so_on_its_page(tmp_path):
    wiki = wiki_with(tmp_path)
    source = next(page for page in project(wiki).pages if page.kind == 'source')
    assert 'extraction_status: "truncated"' in source.content
    assert '只读了一部分' in source.content
    assert '图文未读' in source.content


def test_scan_sources_extracts_a_staged_markdown_file(tmp_path):
    class MarkdownWiki(FakeWiki):
        def __init__(self, root):
            super().__init__(root, [], [{
                'source_id': 'source_md', 'scope_id': 'enterprise:e/project:p',
                'relative_path': 'memo.md', 'revision': 'r1', 'source_format': 'markdown',
            }])

    (tmp_path / 'memo.md').write_text('市场营销中心负责预算。\n', encoding='utf-8')
    scanned = scan_sources(MarkdownWiki(tmp_path))
    assert set(scanned) == {'source_md'}
    assert scanned['source_md'][0].locator == 'line:1'
    assert '市场营销中心' in scanned['source_md'][0].quote

class VersionedWiki(FakeWiki):
    """The same read surface, plus the version ledger and the concept set a real store has."""

    def __init__(self, tmp_path: Path, meanings, sources, *, version=None, concept_ledger=None,
                 digest='a' * 64):
        super().__init__(tmp_path, meanings, sources)
        self._version = version
        self._concept_ledger = concept_ledger
        self.scope_id = 'enterprise:e/project:p'
        self.backend = 'json'
        self.digest = digest

    def index_digest(self):
        return self.digest

    def accepted_meanings(self):
        accepted = super().accepted_meanings()
        if self._version is not None:
            accepted['active_version_id'] = self._version['version_id']
        return accepted

    def semantic_state(self):
        state = dict(super().semantic_state())
        if self._version is not None:
            state['accepted_versions'] = {self._version['version_id']: self._version}
            state['active_version_id'] = self._version['version_id']
        return state

    def concept_state(self):
        return self._concept_ledger or empty_concept_state()

    def concept_set(self):
        return concept_set_of(self.concept_state())


def _version(repository_meaning):
    return {
        'version_id': 'version_p1', 'parent_version_id': None, 'candidate_id': 'candidate_p1',
        'decision_id': 'decision_p1', 'source_id': 'source_a', 'source_revision': 'r1',
        'authority_class': 'test_only', 'confirmed_by_absence_count': 0,
        'meanings': {repository_meaning['meaning_id']: repository_meaning},
        'diff': {'added_meaning_ids': [repository_meaning['meaning_id']], 'changed_meaning_ids': [],
                 'removed_meaning_ids': [], 'evidence_added_meaning_ids': [],
                 'evidence_removed_meaning_ids': [], 'carried_meaning_ids': []},
    }


def _ledger_with_ward():
    from catalyst_platform.ontology_concepts import define_concept, empty_concept_state
    from catalyst_platform.ontology_types import Action, Attribute, Concept, Metric, Relation

    state = empty_concept_state()
    define_concept(state, Concept(
        'Ward', '病区', 'Organization', '病区、护理单元：医院里独立收治的一段病床',
        attributes=(Attribute('bed_count', 'number', True, '核定床位数'),),
        relations=(Relation('yields', 'Deliverable'),),
        actions=(Action('收治'),),
        metrics=(Metric('平均住院日', '天'),)),
        actor='owner', reason='医院资料里有病区')
    return state


def _ward_wiki(tmp_path: Path, *, ledger=None):
    ward = meaning('m1', 'entity', 'ward_a', '病区甲', canonical_id='c1', business_type='Ward')
    bed = meaning('m2', 'entity', 'bed_a', '床位甲', canonical_id='c2', business_type='Bed')
    link = meaning('m3', 'relation', 'k', '@c1 含 @c2', business_type=None,
                   canonical_subject_id='c1', canonical_object_id='c2', predicate_key='含')
    sources = wiki_with(tmp_path).sources()
    return VersionedWiki(tmp_path, [ward, bed, link], sources,
                         version=_version(ward), concept_ledger=ledger)


def test_a_version_page_says_what_it_changed_and_who_accepted_it(tmp_path):
    pages = _ward_wiki(tmp_path)
    page = next(row for row in project(pages).pages if row.path == 'versions/version_p1.md')

    assert 'authority_class: "test_only"' in page.content
    assert 'active: true' in page.content
    assert '当前生效' in page.content
    assert '## 改了什么' in page.content
    assert '新增 1 条' in page.content
    assert '病区甲' in page.content


def test_a_store_without_accepted_versions_has_no_version_page(tmp_path):
    pages = project(wiki_with(tmp_path)).pages

    assert not [row for row in pages if row.kind == 'version']
    assert any(row.path == 'gaps.md' for row in pages)


def test_a_declared_type_page_shows_its_structure_and_what_it_still_misses(tmp_path):
    page = next(row for row in project(_ward_wiki(tmp_path, ledger=_ledger_with_ward())).pages
                if row.path == 'concepts/Ward.md')

    assert 'meta_kind: "Organization"' in page.content
    assert '## 声明的结构' in page.content
    assert 'bed_count' in page.content and '必填' in page.content
    assert 'yields' in page.content
    assert '收治' in page.content
    assert '平均住院日' in page.content
    assert '- 病区甲' in page.content
    assert '## 还缺什么' in page.content


def test_a_type_outside_the_concept_set_is_its_own_page_and_a_gap(tmp_path):
    pages = project(_ward_wiki(tmp_path, ledger=_ledger_with_ward())).pages
    outside = next(row for row in pages if row.path == 'concepts/Bed.md')
    gaps = next(row for row in pages if row.path == 'gaps.md')

    assert 'declared_by_scope: false' in outside.content
    assert '不在本 scope 的概念集里' in outside.content
    assert '`Bed`：1 个实体' in gaps.content


def test_the_gap_page_names_the_entities_no_relation_touches(tmp_path):
    ward = meaning('m1', 'entity', 'ward_a', '病区甲', canonical_id='c1', business_type='Ward')
    bed = meaning('m2', 'entity', 'bed_a', '床位甲', canonical_id='c2', business_type='Bed')
    lonely = meaning('m4', 'entity', 'ward_c', '病区丙', canonical_id='c3', business_type='Ward')
    link = meaning('m3', 'relation', 'k', '@c1 含 @c2', business_type=None,
                   canonical_subject_id='c1', canonical_object_id='c2', predicate_key='含')
    wiki = VersionedWiki(tmp_path, [ward, bed, lonely, link], wiki_with(tmp_path).sources(),
                         version=_version(ward), concept_ledger=_ledger_with_ward())
    gaps = next(row for row in project(wiki).pages if row.path == 'gaps.md')
    isolated = gaps.content.split('## 没有任何关系的实体')[1].split('## ')[0]

    assert '（1）' in isolated
    assert '病区丙' in isolated
    assert '病区甲' not in isolated


def test_the_authority_banner_names_the_version_on_every_entity_page(tmp_path):
    pages = project(_ward_wiki(tmp_path, ledger=_ledger_with_ward())).pages
    entity = next(row for row in pages if row.path == 'entities/ward_a.md')

    assert '> 权威：已接受版本 `version_p1`' in entity.content
    assert 'version_id: "version_p1"' in entity.content
    assert 'authority_class: "test_only"' in entity.content


def test_the_index_lists_the_version_and_the_gap_page(tmp_path):
    index = next(row for row in project(_ward_wiki(tmp_path, ledger=_ledger_with_ward())).pages
                 if row.path == 'index.md')

    assert '## version' in index.content and 'versions/version_p1.md' in index.content
    assert '## gaps' in index.content and 'gaps.md' in index.content



def test_a_page_set_names_the_store_the_version_and_the_renderer(tmp_path):
    wiki = _ward_wiki(tmp_path, ledger=_ledger_with_ward())
    pages = project(wiki)

    assert pages.identity['scope_id'] == 'enterprise:e/project:p'
    assert pages.identity['backend'] == 'json'
    assert pages.identity['store_index_sha256'] == 'a' * 64
    assert pages.identity['active_version_id'] == 'version_p1'
    assert isinstance(pages.identity['concept_set_version'], str)
    assert pages.identity['concept_set_version']
    assert pages.identity['source_roots'] == [str(tmp_path)]
    renderer = pages.identity['renderer']
    assert renderer['name'] == 'catalyst_platform.wiki_pages'
    assert renderer['version'] == PROJECTION_VERSION
    module = Path(catalyst_platform.wiki_pages.__file__)
    assert renderer['source_sha256'] == hashlib.sha256(module.read_bytes()).hexdigest()
    assert pages.identity['snapshot'] == {
        'method': 'index_digest_before_and_after', 'attempts': 1}


def test_the_manifest_records_the_pages_and_the_identity(tmp_path):
    wiki = _ward_wiki(tmp_path, ledger=_ledger_with_ward())
    root = tmp_path / 'wiki-pages'
    pages = project(wiki, root=root)

    outcome = materialize(pages.pages, root, identity=pages.identity)
    document = json.loads((root / '.projection.json').read_text(encoding='utf-8'))

    assert outcome['identity_changed'] is True
    assert document['schema_version'] == 2
    assert document['identity'] == pages.identity
    index_page = next(page for page in pages.pages if page.path == 'index.md')
    assert document['pages']['index.md'] == index_page.sha256

    again = materialize(project(wiki, root=root).pages, root, identity=pages.identity)
    assert again['identity_changed'] is False
    assert not again['written']


def test_a_legacy_flat_manifest_still_protects_an_edited_page(tmp_path):
    wiki = wiki_with(tmp_path)
    root = tmp_path / 'wiki-pages'
    pages = project(wiki).pages
    generated = next(page for page in pages if page.path == 'entities/marketing_center.md')
    target = root / 'entities/marketing_center.md'
    target.parent.mkdir(parents=True)
    target.write_text(generated.content, encoding='utf-8')
    edited = generated.content + '\n人工补注：这一段尚未核实。\n'
    target.write_text(edited, encoding='utf-8')
    (root / '.projection.json').write_text(
        json.dumps({'entities/marketing_center.md': generated.sha256}), encoding='utf-8')

    outcome = materialize(pages, root)

    assert 'entities/marketing_center.md' in outcome['diverged']
    assert target.read_text(encoding='utf-8') == edited
    rewritten = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert rewritten['schema_version'] == 2
    assert rewritten['pages']['entities/marketing_center.md'] == generated.sha256


def test_a_changed_store_digest_is_reported_as_another_identity(tmp_path):
    wiki = _ward_wiki(tmp_path, ledger=_ledger_with_ward())
    root = tmp_path / 'wiki-pages'
    first = project(wiki, root=root)
    materialize(first.pages, root, identity=first.identity)

    wiki.digest = 'b' * 64
    later = project(wiki, root=root)
    outcome = materialize(later.pages, root, identity=later.identity)

    assert outcome['identity_changed'] is True
    document = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert document['identity']['store_index_sha256'] == 'b' * 64


def _cli(*args):
    completed = subprocess.run(
        [sys.executable, "-m", "catalyst_platform", *args],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"}, check=False,
    )
    return completed.returncode, (json.loads(completed.stdout) if completed.stdout.strip() else {})


def test_an_unknown_file_is_a_conflict_and_is_left_alone(tmp_path):
    wiki = wiki_with(tmp_path)
    root = tmp_path / 'wiki-pages'
    root.mkdir()
    hand_written = '# 概览\n\n这是别人写的概览。\n'
    (root / 'overview.md').write_text(hand_written, encoding='utf-8')

    outcome = materialize(project(wiki, root=root).pages, root)

    assert outcome['conflicts'] == ['overview.md']
    assert (root / 'overview.md').read_text(encoding='utf-8') == hand_written
    assert 'index.md' in outcome['written']
    manifest = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert 'overview.md' not in manifest['pages']


def test_an_identical_unknown_file_is_adopted_instead_of_conflicting(tmp_path):
    wiki = wiki_with(tmp_path)
    root = tmp_path / 'wiki-pages'
    root.mkdir()
    pages = project(wiki, root=root).pages
    overview = next(page for page in pages if page.path == 'overview.md')
    (root / 'overview.md').write_text(overview.content, encoding='utf-8')

    outcome = materialize(pages, root)

    assert outcome['conflicts'] == []
    assert 'overview.md' in outcome['skipped']
    manifest = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert manifest['pages']['overview.md'] == overview.sha256

    edited = overview.content + '\n人工补注：这一段尚未核实。\n'
    (root / 'overview.md').write_text(edited, encoding='utf-8')
    again = materialize(pages, root)

    assert 'overview.md' in again['diverged']
    assert (root / 'overview.md').read_text(encoding='utf-8') == edited


def _history_wiki(tmp_path, *, announce=True):
    ward = meaning('m1', 'entity', 'ward_a', '病区甲', canonical_id='c1', business_type='Ward')
    bed = meaning('m2', 'entity', 'bed_a', '床位甲', canonical_id='c2', business_type='Bed')
    link = meaning('m3', 'relation', 'k', '@c1 含 @c2', business_type=None,
                   canonical_subject_id='c1', canonical_object_id='c2', predicate_key='含')
    sources = wiki_with(tmp_path).sources()
    ledger = _ledger_with_ward()
    return VersionedWiki(tmp_path, [ward, bed, link], sources,
                         version=_version(ward) if announce else None, concept_ledger=ledger)


def test_a_page_the_store_no_longer_produces_is_archived(tmp_path):
    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    version_page = root / 'versions/version_p1.md'
    assert version_page.is_file()
    original = version_page.read_text(encoding='utf-8')

    quiet = _history_wiki(tmp_path, announce=False)
    outcome = materialize(project(quiet, root=root).pages, root, identity=project(quiet).identity)

    assert outcome['archived'] == ['versions/version_p1.md']
    assert not version_page.exists()
    digest = hashlib.sha256(original.encode('utf-8')).hexdigest()[:16]
    archived = root / '.obsolete' / digest / 'versions' / 'version_p1.md'
    assert archived.is_file() and archived.read_text(encoding='utf-8') == original
    manifest = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert 'versions/version_p1.md' not in manifest['pages']


def test_a_page_a_person_edited_is_kept_when_the_store_stops_producing_it(tmp_path):
    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    version_page = root / 'versions/version_p1.md'
    edited = version_page.read_text(encoding='utf-8') + '\n人工补注：这一版的分母我核过。\n'
    version_page.write_text(edited, encoding='utf-8')

    quiet = _history_wiki(tmp_path, announce=False)
    outcome = materialize(project(quiet, root=root).pages, root)

    assert outcome['obsolete_kept'] == ['versions/version_p1.md']
    assert version_page.read_text(encoding='utf-8') == edited
    assert not (root / '.obsolete').exists()


def test_the_cli_reports_a_conflict_and_exits_non_zero(tmp_path):
    sources = tmp_path / 'sources'
    sources.mkdir()
    root = tmp_path / 'pages'
    root.mkdir()
    hand_written = '# 概览\n\n别人写的。\n'
    (root / 'overview.md').write_text(hand_written, encoding='utf-8')
    common = ['wiki', 'pages', '--workspace', str(tmp_path / 'workspace'),
              '--wiki-root', str(sources), '--enterprise-id', 'ent', '--project-id', 'cli',
              '--root', str(root)]

    code, checked = _cli(*common, '--check')

    assert code == 1
    assert checked['status'] == 'conflict'
    assert checked['conflicts'] == ['overview.md']
    assert not (root / 'index.md').exists()

    code, outcome = _cli(*common)

    assert code == 1
    assert outcome['status'] == 'conflict'
    assert (root / 'overview.md').read_text(encoding='utf-8') == hand_written
    assert (root / 'index.md').is_file()
    assert outcome['identity']['scope_id'] == 'enterprise:ent/project:cli'


class _UnreadableConcepts(FakeWiki):
    def concept_state(self):
        raise RuntimeError('concept ledger unreadable')


class _UnreadableConceptSet(FakeWiki):
    def concept_set(self):
        raise RuntimeError('concept set unreadable')


def test_a_concept_ledger_that_cannot_be_read_stops_the_projection(tmp_path):
    base = wiki_with(tmp_path)
    wiki = _UnreadableConcepts(tmp_path, base._meanings, base.sources())
    root = tmp_path / 'wiki-pages'

    with pytest.raises(RuntimeError, match='concept ledger unreadable'):
        project(wiki, root=root)
    assert not root.exists()


def test_a_concept_set_that_cannot_be_read_stops_the_projection(tmp_path):
    base = wiki_with(tmp_path)
    wiki = _UnreadableConceptSet(tmp_path, base._meanings, base.sources())
    root = tmp_path / 'wiki-pages'

    with pytest.raises(RuntimeError, match='concept set unreadable'):
        project(wiki, root=root)
    assert not root.exists()


def test_a_manifest_entry_that_leaves_the_root_cannot_move_a_file(tmp_path):
    """The audit's probe: a manifest naming ../external.md and its digest."""
    root = tmp_path / 'pages'
    root.mkdir()
    external = tmp_path / 'external.md'
    external.write_text('outside the page root\n', encoding='utf-8')
    digest = hashlib.sha256(external.read_bytes()).hexdigest()
    (root / '.projection.json').write_text(
        json.dumps({'schema_version': 2, 'pages': {'../external.md': digest}}), encoding='utf-8')

    outcome = materialize([], root)

    assert outcome['refused'] == ['../external.md']
    assert outcome['archived'] == []
    assert external.is_file() and external.read_text(encoding='utf-8') == 'outside the page root\n'
    assert not (root / 'external.md').exists()
    assert not (root / '.obsolete').exists()
    # The bad entry stays in the manifest: it is wrong, and every run says so again.
    manifest = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert manifest['pages'] == {'../external.md': digest}


def test_an_absolute_drive_or_parent_page_path_is_refused_before_writing(tmp_path):
    root = tmp_path / 'pages'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    good = Page(path='index.md', kind='index', title='索引', content='# 索引\n')
    pages = PageSet(pages=(good,) + tuple(
        Page(path=bad, kind='index', title='坏路径', content='# 越界\n')
        for bad in ('../escape.md', 'entities/../../escape.md', str(outside / 'absolute.md'),
                    'C:/Windows/escape.md', '.obsolete/x.md', '.projection.json')))

    outcome = materialize(pages, root)

    assert outcome['refused'] == sorted([
        '../escape.md', 'entities/../../escape.md', str(outside / 'absolute.md'),
        'C:/Windows/escape.md', '.obsolete/x.md', '.projection.json'])
    assert outcome['written'] == ['index.md']
    assert not (tmp_path / 'escape.md').exists()
    assert not (outside / 'absolute.md').exists()
    assert (root / 'index.md').is_file()
    manifest = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert manifest['pages'] == {'index.md': good.sha256}


def test_a_second_page_of_the_same_name_keeps_the_first_history(tmp_path):
    """Two generations archived at one path: both survive, each under its own digest."""
    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    first_text = (root / 'versions' / 'version_p1.md').read_text(encoding='utf-8')
    quiet = _history_wiki(tmp_path, announce=False)
    materialize(project(quiet, root=root).pages, root)
    first_digest = hashlib.sha256(first_text.encode('utf-8')).hexdigest()[:16]

    ward = meaning('m1', 'entity', 'ward_a', '病区甲', canonical_id='c1', business_type='Ward')
    bed = meaning('m2', 'entity', 'bed_a', '床位甲', canonical_id='c2', business_type='Bed')
    wider = _version(ward)
    wider['meanings'][bed['meaning_id']] = bed
    wider_wiki = VersionedWiki(
        tmp_path,
        [ward, bed],
        wiki_with(tmp_path).sources(),
        version=wider,
        concept_ledger=_ledger_with_ward(),
    )
    materialize(project(wider_wiki, root=root).pages, root)
    second_text = (root / 'versions' / 'version_p1.md').read_text(encoding='utf-8')
    assert second_text != first_text
    second_quiet = _history_wiki(tmp_path, announce=False)
    outcome = materialize(project(second_quiet, root=root).pages, root)

    second_digest = hashlib.sha256(second_text.encode('utf-8')).hexdigest()[:16]
    assert outcome['archived'] == ['versions/version_p1.md']
    assert first_digest != second_digest
    archived_first = root / '.obsolete' / first_digest / 'versions' / 'version_p1.md'
    archived_second = root / '.obsolete' / second_digest / 'versions' / 'version_p1.md'
    assert archived_first.read_text(encoding='utf-8') == first_text
    assert archived_second.read_text(encoding='utf-8') == second_text


def test_archiving_the_same_bytes_twice_reuses_one_copy(tmp_path):
    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    text = (root / 'versions' / 'version_p1.md').read_text(encoding='utf-8')
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    quiet = _history_wiki(tmp_path, announce=False)

    materialize(project(quiet, root=root).pages, root)
    # The same generation comes back, is published again, and goes obsolete again.
    materialize(first.pages, root)
    again = materialize(project(quiet, root=root).pages, root)

    assert again['archived'] == ['versions/version_p1.md']
    archived = list((root / '.obsolete' / digest).rglob('*.md'))
    assert [path.name for path in archived] == ['version_p1.md']
    assert archived[0].read_text(encoding='utf-8') == text


def test_a_run_interrupted_before_the_manifest_reconciles_on_the_next_run(tmp_path, monkeypatch):
    """Pages are written one by one; only the record is atomic, and the next run repairs it."""
    import catalyst_platform.wiki_pages as pages_module

    wiki = _history_wiki(tmp_path)
    root = tmp_path / 'wiki-pages'
    pages = project(wiki, root=root)

    def refuse(root_path, recorded, identity):
        raise OSError('the manifest could not be replaced in this test')

    monkeypatch.setattr(pages_module, '_write_manifest', refuse)
    try:
        with pytest.raises(OSError):
            materialize(pages.pages, root, identity=pages.identity)
    finally:
        monkeypatch.undo()

    assert (root / 'index.md').is_file()
    assert not (root / '.projection.json').exists()

    outcome = materialize(project(wiki, root=root).pages, root, identity=pages.identity)

    assert outcome['written'] == []
    assert outcome['conflicts'] == [] and outcome['diverged'] == [] and outcome['refused'] == []
    assert len(outcome['skipped']) == len(pages.pages)
    assert outcome['complete'] is True
    assert (root / '.projection.json').is_file()


def test_a_store_that_moves_under_the_projection_publishes_nothing(tmp_path):
    """A digest that differs at the two ends means the pages describe no single generation."""
    base = _history_wiki(tmp_path)

    class MovingWiki(VersionedWiki):
        def semantic_state(self):
            state = super().semantic_state()
            self.digest = hashlib.sha256((self.digest + '!').encode('utf-8')).hexdigest()
            return state

    moving = MovingWiki(tmp_path, base._meanings, base.sources(),
                        version=_version(base._meanings[0]), concept_ledger=_ledger_with_ward())

    with pytest.raises(WikiUnavailable, match='changed while its pages were being projected'):
        project(moving)


def test_a_read_surface_without_a_digest_says_so_in_the_identity(tmp_path):
    pages = project(wiki_with(tmp_path))

    assert pages.identity['store_index_sha256'] is None
    assert pages.identity['snapshot'] == {'method': 'none', 'attempts': 1}


def test_a_partial_publication_reports_itself_incomplete(tmp_path):
    """A returned result is not a claim that nothing was blocked; `complete` is."""
    wiki = wiki_with(tmp_path)
    root = tmp_path / 'partial'
    root.mkdir()
    hand_written = '# 概览\n\n别人写的。\n'
    (root / 'overview.md').write_text(hand_written, encoding='utf-8')

    outcome = materialize(project(wiki, root=root).pages, root)

    assert outcome['conflicts'] == ['overview.md']
    assert outcome['complete'] is False
    assert 'index.md' in outcome['written']          # the rest is still published
    assert (root / 'overview.md').read_text(encoding='utf-8') == hand_written


def test_a_page_kept_after_the_store_dropped_it_keeps_the_tree_incomplete(tmp_path):
    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    page = root / 'versions' / 'version_p1.md'
    page.write_text(page.read_text(encoding='utf-8') + '\n人工补注：这一版我核过。\n', encoding='utf-8')
    quiet = _history_wiki(tmp_path, announce=False)

    outcome = materialize(project(quiet, root=root).pages, root)

    assert outcome['obsolete_kept'] == ['versions/version_p1.md']
    assert outcome['complete'] is False


def test_a_failed_page_write_neither_loses_a_human_edit_nor_claims_completion(tmp_path, monkeypatch):
    import catalyst_platform.wiki_pages as pages_module

    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    edited = root / 'entities' / 'ward_a.md'
    human = edited.read_text(encoding='utf-8') + '\n人工补注：保留。\n'
    edited.write_text(human, encoding='utf-8')

    ward = meaning('m1', 'entity', 'ward_a', '病区甲', canonical_id='c1', business_type='Ward')
    bed = meaning('m2', 'entity', 'bed_a', '床位甲', canonical_id='c2', business_type='Bed')
    wider = _version(ward)
    wider['meanings'][bed['meaning_id']] = bed
    moved = VersionedWiki(tmp_path, [ward, bed], wiki_with(tmp_path).sources(),
                          version=wider, concept_ledger=_ledger_with_ward())
    later = project(moved, root=root)

    real = pages_module._write_page
    calls = {'n': 0}

    def fail_third(target, content):
        calls['n'] += 1
        if calls['n'] == 3:
            raise OSError('page write refused in this test')
        real(target, content)

    monkeypatch.setattr(pages_module, '_write_page', fail_third)
    try:
        with pytest.raises(OSError):
            materialize(later.pages, root, identity=later.identity)
    finally:
        monkeypatch.undo()

    # Nothing claims the tree was published: the record is still the previous generation.
    manifest = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert manifest['identity'] == first.identity
    assert edited.read_text(encoding='utf-8') == human

    outcome = materialize(project(moved, root=root).pages, root, identity=later.identity)

    assert edited.read_text(encoding='utf-8') == human
    assert 'entities/ward_a.md' in outcome['diverged'] + outcome['skipped']
    assert outcome['complete'] is True


def test_a_failed_archive_move_keeps_the_page_and_the_next_run_finishes(tmp_path, monkeypatch):
    import catalyst_platform.wiki_pages as pages_module

    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    quiet = _history_wiki(tmp_path, announce=False)

    def refuse(target, destination):
        raise OSError('archive move refused in this test')

    monkeypatch.setattr(pages_module, '_archive_page', refuse)
    try:
        with pytest.raises(OSError):
            materialize(project(quiet, root=root).pages, root)
    finally:
        monkeypatch.undo()

    page = root / 'versions' / 'version_p1.md'
    assert page.is_file()
    manifest = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert 'versions/version_p1.md' in manifest['pages']

    outcome = materialize(project(quiet, root=root).pages, root)

    assert outcome['archived'] == ['versions/version_p1.md']
    assert outcome['complete'] is True
    assert not page.exists()


def _wider_wiki(tmp_path):
    """The same store after one more entity was accepted: a new page and several edits."""
    ward = meaning('m1', 'entity', 'ward_a', '病区甲', canonical_id='c1', business_type='Ward')
    bed = meaning('m2', 'entity', 'bed_a', '床位甲', canonical_id='c2', business_type='Bed')
    extra = meaning('m4', 'entity', 'ward_c', '病区丙', canonical_id='c3', business_type='Ward')
    wider = _version(ward)
    wider['meanings'][extra['meaning_id']] = extra
    return VersionedWiki(tmp_path, [ward, bed, extra], wiki_with(tmp_path).sources(),
                         version=wider, concept_ledger=_ledger_with_ward())


def test_a_failed_run_over_an_existing_tree_leaves_a_mixed_but_recorded_state(tmp_path, monkeypatch):
    """Not only a first publication: an old manifest, some pages already updated, then a failure."""
    import catalyst_platform.wiki_pages as pages_module

    root = tmp_path / 'wiki-pages'
    first = project(_history_wiki(tmp_path), root=root)
    materialize(first.pages, root, identity=first.identity)
    before = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    old_version_text = (root / 'versions' / 'version_p1.md').read_text(encoding='utf-8')

    newer = _wider_wiki(tmp_path)
    later = project(newer, root=root)

    real = pages_module._write_page
    calls = {'n': 0}

    def fail_third(target, content):
        calls['n'] += 1
        if calls['n'] == 3:
            raise OSError('page write refused in this test')
        real(target, content)

    monkeypatch.setattr(pages_module, '_write_page', fail_third)
    try:
        with pytest.raises(OSError):
            materialize(later.pages, root, identity=later.identity)
    finally:
        monkeypatch.undo()

    # Mixed tree: at least one page already holds the new generation (and the manifest does
    # not vouch for it), while another is still the old one - and the record is untouched, so
    # nothing claims the new generation was published.
    after = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert after == before
    written_new = [
        page.path for page in later.pages
        if (root / page.path).is_file()
        and (root / page.path).read_text(encoding='utf-8') == page.content
        and before['pages'].get(page.path) != page.sha256
    ]
    still_old = [
        page.path for page in later.pages
        if (root / page.path).is_file()
        and (root / page.path).read_text(encoding='utf-8') != page.content
    ]
    assert calls['n'] == 3
    assert written_new and still_old
    assert (root / 'versions' / 'version_p1.md').read_text(encoding='utf-8') == old_version_text
    assert after['pages']['versions/version_p1.md'] == before['pages']['versions/version_p1.md']

    # The next run finishes the generation: every page equals the new output, the record agrees.
    outcome = materialize(project(newer, root=root).pages, root, identity=later.identity)

    assert outcome['complete'] is True
    assert outcome['conflicts'] == [] and outcome['refused'] == []
    for page in later.pages:
        assert (root / page.path).read_text(encoding='utf-8') == page.content
    final = json.loads((root / '.projection.json').read_text(encoding='utf-8'))
    assert final['identity'] == later.identity


def test_a_re_entry_that_fails_again_still_converges(tmp_path, monkeypatch):
    import catalyst_platform.wiki_pages as pages_module

    root = tmp_path / 'wiki-pages'
    wiki = _history_wiki(tmp_path)
    pages = project(wiki, root=root)

    def refuse_write(target, content):
        raise OSError('page write refused in this test')

    monkeypatch.setattr(pages_module, '_write_page', refuse_write)
    try:
        with pytest.raises(OSError):
            materialize(pages.pages, root)
    finally:
        monkeypatch.undo()
    assert not (root / '.projection.json').exists()

    def refuse_manifest(root_path, recorded, identity):
        raise OSError('manifest refused in this test')

    monkeypatch.setattr(pages_module, '_write_manifest', refuse_manifest)
    try:
        with pytest.raises(OSError):
            materialize(pages.pages, root, identity=pages.identity)
    finally:
        monkeypatch.undo()
    assert not (root / '.projection.json').exists()

    outcome = materialize(project(wiki, root=root).pages, root, identity=pages.identity)

    assert outcome['complete'] is True
    assert outcome['conflicts'] == [] and outcome['refused'] == []
    assert (root / '.projection.json').is_file()


def test_the_projection_says_where_its_own_links_lead(tmp_path):
    page_set = project(wiki_with(tmp_path))
    links = page_set.stats["links"]

    assert links["links"] > 0
    assert links["unresolved"] == []
    assert links["ambiguous"] == []
    assert len(links["resolved"]) == links["links"]
    # Every page has its own title here, so the count is the page count.
    assert links["duplicate_titles"] == {}
    assert links["titles"] == len(page_set.pages)


def test_a_link_resolves_to_the_file_whose_title_it_names():
    pages = [
        Page("overview.md", "overview", "概览", "- 还缺什么见 [[缺口]]"),
        Page("gaps.md", "gaps", "缺口", "# 缺口"),
    ]

    report = link_report(pages)

    assert page_link_index(pages) == {"概览": ("overview.md",), "缺口": ("gaps.md",)}
    assert report["links"] == 1
    assert report["resolved"] == [{"title": "缺口", "from": "overview.md", "path": "gaps.md"}]
    assert report["unresolved"] == []
    assert report["ambiguous"] == []


def test_a_title_no_page_carries_is_unresolved_rather_than_invented():
    pages = [Page("index.md", "index", "索引", "- [[缺口]]")]

    report = link_report(pages)

    assert report["unresolved"] == [{"title": "缺口", "from": "index.md"}]
    assert report["resolved"] == []
    assert report["ambiguous"] == []


def test_a_title_two_pages_carry_cannot_be_resolved_by_name():
    pages = [
        Page("entities/a.md", "entity", "总部", "# 总部"),
        Page("entities/b.md", "entity", "总部", "# 总部"),
        Page("index.md", "index", "索引", "- [[总部]]"),
    ]

    report = link_report(pages)

    assert report["ambiguous"] == [{
        "title": "总部", "from": "index.md", "paths": ["entities/a.md", "entities/b.md"]}]
    assert report["resolved"] == []
    assert report["unresolved"] == []
    assert report["duplicate_titles"] == {"总部": ["entities/a.md", "entities/b.md"]}


def test_a_link_that_names_a_heading_or_an_alias_still_names_the_page():
    pages = [
        Page("gaps.md", "gaps", "缺口", "# 缺口"),
        Page("index.md", "index", "索引", "- [[缺口#未被类型化的实体]] 与 [[缺口|这一页]]"),
    ]

    report = link_report(pages)

    assert [(row["title"], row["path"]) for row in report["resolved"]] == [
        ("缺口", "gaps.md"), ("缺口", "gaps.md")]
    assert report["unresolved"] == []
    assert report["ambiguous"] == []


def test_two_entities_with_the_same_name_make_the_index_link_ambiguous(tmp_path):
    # Two accepted entities can be called the same thing; a title then names neither of them,
    # and the projection has to say so instead of linking to whichever page came first.
    first = meaning("m1", "entity", "zongbu_a", "总部", canonical_id="c1", business_type="Department")
    second = meaning("m2", "entity", "zongbu_b", "总部", canonical_id="c2", business_type="Department")
    page_set = project(FakeWiki(tmp_path, [first, second], []))

    links = page_set.stats["links"]

    assert links["duplicate_titles"] == {
        "总部": ["entities/zongbu_a.md", "entities/zongbu_b.md"]}
    assert [row["title"] for row in links["ambiguous"]] == ["总部", "总部"]
    assert links["unresolved"] == []
    # The other pages still link by a name that names exactly one page.
    assert links["resolved"]
