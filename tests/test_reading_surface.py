"""The reading surface: what a document says about its own cells, checked on the cells.

A candidate can only be as good as the surface it is read from. These are the checks the
reading-surface contract (v0, 2026-10-31) names A1-A6, applied to a Word document: role and
outline level as the file declares them, headings the section chain is built from, field
codes counted instead of quoted, runs joined without inventing a space, and a witness for
a name that was assembled from more than one run.
"""
import json
import zipfile
import xml.etree.ElementTree as ET

import pytest

from catalyst_platform.understand_sources import _extract

_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def paragraph(text, style=None, runs=None):
    if runs is not None:
        body = ''.join(f'<w:r><w:t>{part}</w:t></w:r>' for part in runs)
    elif style:
        body = f'<w:r><w:t>{text}</w:t></w:r>'
    else:
        body = f'<w:r><w:t>{text}</w:t></w:r>'
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ''
    return f'<w:p>{properties}{body}</w:p>'


def field_code(instruction, visible):
    return (f'<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r><w:instrText>{instruction}</w:instrText></w:r>'
            f'<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            f'<w:r><w:t>{visible}</w:t></w:r>'
            f'<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def word(tmp_path, body, cells=(('部门', '职责'),)):
    path = tmp_path / 'brief.docx'
    rows = ''.join(
        '<w:tr>' + ''.join(f'<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>' for cell in row) + '</w:tr>'
        for row in cells)
    table = f'<w:tbl>{rows}</w:tbl>'
    styles = (f'<w:styles xmlns:w="{_W}">'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading2"><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>'
              '</w:styles>')
    with zipfile.ZipFile(path, 'w') as package:
        package.writestr('word/document.xml', f'<w:document xmlns:w="{_W}"><w:body>{body}{table}</w:body></w:document>')
        package.writestr('word/styles.xml', styles)
    return path


@pytest.fixture()
def surface(tmp_path):
    body = ''.join([
        field_code(' TOC \\o "1-3" \\h ', '一、总体要求 1'),
        paragraph('一、总体要求', style='Heading1'),
        paragraph('', runs=['市场', '副经理']),
        paragraph('（一）职责分工', style='Heading2'),
        paragraph('综合办公室负责合同审核。'),
        paragraph('', runs=['空段被跳过']),
    ])
    units, warnings = _extract(word(tmp_path, body), 'brief.docx', 's1', 'r1')
    return units, warnings


def reader_text(unit):
    return unit.quote


def test_a1_every_cell_says_what_it_is(surface):
    units, _ = surface
    assert units
    for unit in units:
        assert unit.unit_id if hasattr(unit, 'unit_id') else unit.locator
        assert unit.unit_kind in {'format', 'window'}
        assert isinstance(unit.path, tuple)
        assert unit.role is not None
        if unit.role != 'unknown':
            assert unit.role_source in {'format', 'inferred'}, unit
        if unit.role_source == 'inferred':
            assert unit.reason, unit


def test_a2_field_codes_are_counted_and_never_quoted(surface):
    units, warnings = surface
    apparatus = [warning for warning in warnings if warning.startswith('APPARATUS:')]
    assert len(apparatus) == 1 and 'paragraph:1' in apparatus[0]
    for unit in units:
        assert 'TOC' not in unit.quote and 'instrText' not in unit.quote
    assert all(not unit.locator.endswith('paragraph:1') for unit in units)


def test_a3_a_quote_is_the_text_the_reader_sees(surface):
    units, _ = surface
    by_locator = {unit.locator: unit.quote for unit in units}
    assert by_locator['word/document.xml#paragraph:3'] == '市场副经理'
    assert by_locator['word/document.xml#paragraph:5'] == '综合办公室负责合同审核。'
    assert by_locator['word/document.xml#table:1:r1:c1'] == '部门'
    for unit in units:
        assert ''.join(unit.quote.split()) == ''.join(reader_text(unit).split())


def test_a4_a_section_chain_names_headings_that_come_before_the_cell(surface):
    units, _ = surface
    heading_positions = {unit.quote: index for index, unit in enumerate(units)
                         if unit.role in {'heading', 'title'}}
    assert set(heading_positions) == {'一、总体要求', '（一）职责分工'}
    for index, unit in enumerate(units):
        for name in unit.path:
            assert name in heading_positions, (unit.locator, unit.path)
            assert heading_positions[name] < index, (unit.locator, unit.path)
    nested = [unit for unit in units if unit.path == ('一、总体要求', '（一）职责分工')]
    assert [unit.locator for unit in nested] == [
        'word/document.xml#paragraph:5', 'word/document.xml#paragraph:6',
        'word/document.xml#table:1:r1:c1', 'word/document.xml#table:1:r1:c2',
    ]
    assert [unit.level for unit in units if unit.role == 'heading'] == [1, 2]
    assert all(unit.role_source == 'format' for unit in units if unit.role == 'heading')


def test_a5_the_surface_adds_no_character(surface, tmp_path):
    units, _ = surface
    with zipfile.ZipFile(tmp_path / 'brief.docx') as package:
        root = ET.fromstring(package.read('word/document.xml'))
    squashed = ''.join(''.join(node.text or '' for node in root.iter(f'{{{_W}}}t')).split())
    for unit in units:
        assert ''.join(unit.quote.split()) in squashed, unit.locator


def test_a6_a_name_assembled_from_two_runs_carries_its_witness(surface):
    units, _ = surface
    assembled = next(unit for unit in units if unit.quote == '市场副经理')
    assert assembled.witness == {'text': '市场副经理', 'locator': assembled.locator}
    locators = {unit.locator for unit in units}
    for unit in units:
        if unit.witness:
            assert unit.witness['locator'] in locators
            assert unit.witness['text'] == unit.quote
    single_run = next(unit for unit in units if unit.quote == '综合办公室负责合同审核。')
    assert single_run.witness is None


_A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
_P = 'http://schemas.openxmlformats.org/presentationml/2006/main'


def shape(lines, placeholder=None):
    paragraphs = ''.join(
        f'<a:p><a:r><a:t>{line}</a:t></a:r></a:p>' for line in lines)
    properties = f'<p:nvSpPr><p:nvPr><p:ph type="{placeholder}"/></p:nvPr></p:nvSpPr>' if placeholder else '<p:nvSpPr><p:nvPr/></p:nvSpPr>'
    return f'<p:sp>{properties}<p:txBody><a:bodyPr/>{paragraphs}</p:txBody></p:sp>'


def deck(tmp_path):
    """One slide: a title, a two-line org-chart label, and a one-row table."""
    table = ('<p:graphicFrame><a:graphic><a:graphicData><a:tbl>'
             '<a:tr><a:tc><a:txBody><a:p><a:r><a:t>岗位</a:t></a:r></a:p></a:txBody></a:tc>'
             '<a:tc><a:txBody><a:p><a:r><a:t>职责</a:t></a:r></a:p></a:txBody></a:tc></a:tr>'
             '</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')
    body = (shape(['水利集团现有组织结构'], 'title')
            + shape(['市场', '副经理'])
            + shape(['综合办公室'])
            + table)
    path = tmp_path / 'deck.pptx'
    with zipfile.ZipFile(path, 'w') as package:
        package.writestr('ppt/slides/slide1.xml',
                         f'<p:sld xmlns:p="{_P}" xmlns:a="{_A}"><p:cSld><p:spTree>'
                         f'<p:nvGrpSpPr/><p:grpSpPr/>{body}</p:spTree></p:cSld></p:sld>')
    return path


def test_a_pptx_shape_is_the_cell_a_reader_sees(tmp_path):
    units, _ = _extract(deck(tmp_path), 'deck.pptx', 's1', 'r1')
    locators = [unit.locator for unit in units]
    # One cell per shape; the table is not re-cut per run. The page also states once
    # which state it shows, in its own title words, as a cell of its own.
    assert locators == ['ppt/slides/slide1.xml#shape:1', 'ppt/slides/slide1.xml#shape:2',
                        'ppt/slides/slide1.xml#shape:3', 'ppt/slides/slide1.xml#table:1:r1:c1',
                        'ppt/slides/slide1.xml#table:1:r1:c2', 'ppt/slides/slide1.xml#state']
    assert units[-1].unit_kind == 'structure' and units[-1].role == 'state'
    assert json.loads(units[-1].quote) == {'title': '水利集团现有组织结构', 'declares': 'current'}
    label = units[1]
    # the name is on two lines of one box: one cell, never two halves
    assert label.quote == '市场 副经理'
    assert ''.join(label.quote.split()) == '市场副经理'
    assert label.witness == {'text': '市场 副经理', 'locator': label.locator}
    assert units[0].role == 'title' and units[0].level == 1
    assert units[2].witness is None
    assert units[3].role == 'table_cell' and units[3].quote == '岗位'
