"""Bounded extraction says what it could not read; a staged source keeps that record."""
import zipfile

from pathlib import Path

import pytest

from catalyst_platform.knowledge_intake import KnowledgeIntakeError, stage_and_scan
from catalyst_platform.understand_only import _extract
from catalyst_platform.understand_sources import extract_with_report
from catalyst_platform.wiki import ProjectWiki


_NS = ('xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
       'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"')


def deck(path: Path, *, slides: int = 1, texts_per_slide: int = 3, media: int = 0) -> Path:
    """A deck as PowerPoint writes it: every text lives in a shape, inside a paragraph.

    A bare `<a:t>` under `<p:sld>` is not a shape and has no place on the page, so a
    reader that addresses cells cannot quote it. The fixture stands for what the product
    reads, not for the smallest XML that happens to contain the letters.
    """
    with zipfile.ZipFile(path, 'w') as package:
        for index in range(1, slides + 1):
            shapes = ''.join(
                '<p:sp><p:txBody><a:p><a:r><a:t>第{}页第{}段</a:t></a:r></a:p></p:txBody></p:sp>'
                .format(index, item) for item in range(1, texts_per_slide + 1))
            package.writestr(f'ppt/slides/slide{index}.xml',
                             f'<p:sld {_NS}><p:cSld><p:spTree>{shapes}</p:spTree></p:cSld></p:sld>')
        for index in range(media):
            package.writestr(f'ppt/media/image{index}.png', b'\x89PNG\r\n\x1a\n' + b'0' * 32)
    return path


def test_complete_extraction_reports_no_truncation(tmp_path):
    source = deck(tmp_path / 'small.pptx', slides=2)
    units, report = extract_with_report(source, 'small.pptx', 'source', 'revision')
    assert len(units) == 6
    assert report.status == 'complete'
    assert report.truncated is False
    assert report.locator_count == report.unit_count == 6


def test_truncation_is_a_field_not_only_a_warning(tmp_path):
    source = deck(tmp_path / 'wide.pptx', slides=1, texts_per_slide=510)
    units, warnings = _extract(source, 'wide.pptx', 'source', 'revision')
    assert len(units) == 500 and 'PARTIAL_LOCATOR_LIMIT_500' in warnings

    units, report = extract_with_report(source, 'wide.pptx', 'source', 'revision',
                                        unit_limit=500)
    assert report.status == 'truncated'
    assert report.truncated is True
    assert report.locator_count == 510 > report.unit_count == 500

    # The default reading bound is the document, not a caller's budget: 510 units fit.
    whole, whole_report = extract_with_report(source, 'wide.pptx', 'source', 'revision')
    assert len(whole) == 510
    assert whole_report.truncated is False
    assert whole_report.status == 'complete'


def test_media_members_do_not_spend_the_text_budget(tmp_path):
    # 600 pictures push the member count past the old 512 bound while the text is tiny.
    source = deck(tmp_path / 'illustrated.pptx', slides=3, media=600)
    units, report = extract_with_report(source, 'illustrated.pptx', 'source', 'revision')
    assert report.status == 'complete'
    assert len(units) == 9


def test_a_table_slide_is_read_not_reported_as_unread(tmp_path):
    # A table graphicFrame used to be flagged NEEDS_VISION although every cell was read.
    source = tmp_path / 'table.pptx'
    with zipfile.ZipFile(source, 'w') as package:
        package.writestr(
            'ppt/slides/slide1.xml',
            f'<p:sld {_NS}><p:cSld><p:spTree><p:graphicFrame><a:graphic><a:graphicData><a:tbl>'
            '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>营业收入</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
            '</a:tbl></a:graphicData></a:graphic></p:graphicFrame></p:spTree></p:cSld></p:sld>',
        )
    units, report = extract_with_report(source, 'table.pptx', 'source', 'revision')
    assert [unit.quote for unit in units] == ['营业收入']
    assert report.vision_missing == ()
    assert report.status == 'complete'


def test_a_picture_slide_is_still_reported_as_unread(tmp_path):
    source = tmp_path / 'picture.pptx'
    with zipfile.ZipFile(source, 'w') as package:
        package.writestr('ppt/slides/slide1.xml', f'<p:sld {_NS}><p:pic/></p:sld>')
    units, report = extract_with_report(source, 'picture.pptx', 'source', 'revision')
    assert units == []
    assert report.vision_missing == ('NEEDS_VISION:ppt/slides/slide1.xml',)


def test_a_damaged_slide_is_named_not_swallowed(tmp_path):
    source = deck(tmp_path / 'broken.pptx', slides=1)
    with zipfile.ZipFile(source, 'a') as package:
        package.writestr('ppt/slides/slide2.xml', '<p:sld><unclosed>')
    units, report = extract_with_report(source, 'broken.pptx', 'source', 'revision')
    assert report.status == 'partial'
    assert any(item.startswith('ppt/slides/slide2.xml:') for item in report.part_errors)
    assert report.unit_count == 3


def test_oversized_document_is_refused_by_name(tmp_path):
    source = tmp_path / 'huge.pptx'
    source.write_bytes(b'PK\x03\x04' + b'0' * (129 * 1024 * 1024))
    with pytest.raises(ValueError):
        _extract(source, 'huge.pptx', 'source', 'revision')


def test_record_extraction_is_the_source_completeness_state(tmp_path):
    wiki = ProjectWiki(tmp_path / 'workspace', [tmp_path], enterprise_id='enterprise', project_id='project')
    source = deck(tmp_path / 'recorded.pptx', slides=1)
    staged = wiki.stage_native_source(source)
    assert wiki.source_record(staged['source_id'])['content_status'] == 'NOT_PARSED'

    units, report = extract_with_report(source, 'recorded.pptx', staged['source_id'], staged['revision'])
    recorded = wiki.record_extraction(staged['source_id'], report.to_dict())

    assert recorded['extraction']['status'] == 'complete'
    assert recorded['extraction']['unit_count'] == len(units) == 3
    assert wiki.source_record(staged['source_id'])['content_status'] == 'PARSED'


def test_a_reading_that_shrinks_for_the_same_bytes_is_flagged(tmp_path):
    wiki = ProjectWiki(tmp_path / 'workspace', [tmp_path], enterprise_id='enterprise', project_id='project')
    source = deck(tmp_path / 'shrinking.pptx', slides=4)
    staged = wiki.stage_native_source(source)
    _, report = extract_with_report(source, 'shrinking.pptx', staged['source_id'], staged['revision'])
    first = wiki.record_extraction(staged['source_id'], report.to_dict())
    assert first['extraction']['unit_count'] == 12
    assert first['extraction']['shrink_suspect'] is None

    shrunk = dict(report.to_dict(), unit_count=3)
    second = wiki.record_extraction(staged['source_id'], shrunk)

    assert second['extraction']['shrink_suspect'] == {
        'previous_unit_count': 12, 'unit_count': 3, 'ratio': 0.25}
    assert any(item.startswith('EXTRACTION_SHRINK_SUSPECT') for item in second['extraction']['warnings'])


def test_record_extraction_refuses_an_unbounded_status(tmp_path):
    wiki = ProjectWiki(tmp_path / 'workspace', [tmp_path], enterprise_id='enterprise', project_id='project')
    source = deck(tmp_path / 'refused.pptx', slides=1)
    staged = wiki.stage_native_source(source)
    with pytest.raises(Exception):
        wiki.record_extraction(staged['source_id'], {'status': 'probably_fine', 'unit_count': 1, 'locator_count': 1})


def test_stage_and_scan_reads_a_workbook_without_a_model(tmp_path):
    path = tmp_path / 'ledger.xlsx'
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    relns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    relation = 'http://schemas.openxmlformats.org/package/2006/relationships'
    with zipfile.ZipFile(path, 'w') as package:
        package.writestr('xl/workbook.xml',
                         f'<workbook xmlns="{ns}" xmlns:r="{relns}"><sheets>'
                         f'<sheet name="台账" sheetId="1" r:id="rId1"/></sheets></workbook>')
        package.writestr('xl/_rels/workbook.xml.rels',
                         f'<Relationships xmlns="{relation}">'
                         f'<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        package.writestr('xl/worksheets/sheet1.xml',
                         f'<worksheet xmlns="{ns}"><sheetData>'
                         f'<row r="1"><c r="A1" t="inlineStr"><is><t>管理事项</t></is></c></row>'
                         f'</sheetData></worksheet>')

    wiki = ProjectWiki(tmp_path / 'workspace', [tmp_path], enterprise_id='enterprise', project_id='project')
    outcome = stage_and_scan(wiki, path)

    assert outcome['source']['status'] == 'staged'
    assert outcome['extraction']['status'] == 'complete'
    assert outcome['unit_count'] >= 2
    assert wiki.source_record(outcome['source']['source_id'])['content_status'] == 'PARSED'


def test_binary_word_document_is_refused_with_a_code(tmp_path):
    path = tmp_path / 'legacy.doc'
    path.write_bytes(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\0' * 512)
    wiki = ProjectWiki(tmp_path / 'workspace', [tmp_path], enterprise_id='enterprise', project_id='project')
    with pytest.raises(KnowledgeIntakeError) as raised:
        stage_and_scan(wiki, path)
    assert raised.value.code == 'source_format_unsupported'
