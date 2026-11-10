"""Bounded workbook parsing preserves cell coordinates; no formulas executed."""
import io
import zipfile
from pathlib import Path
import pytest
from catalyst_platform.understand_only import UnderstandPort,UnderstandingRequest,_extract


def workbook(tmp_path, *, target='worksheets/sheet1.xml', external=False, rows=2):
    path=tmp_path/'synthetic.xlsx'
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    relns='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    relation='http://schemas.openxmlformats.org/package/2006/relationships'
    with zipfile.ZipFile(path,'w') as package:
        package.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="{relns}"><sheets><sheet name="台账" sheetId="1" r:id="rId1"/></sheets></workbook>')
        mode=' TargetMode="External"' if external else ''
        package.writestr('xl/_rels/workbook.xml.rels',f'<Relationships xmlns="{relation}"><Relationship Id="rId1" Target="{target}"{mode}/></Relationships>')
        package.writestr('xl/sharedStrings.xml',f'<sst xmlns="{ns}"><si><t>管理事项</t></si></sst>')
        data=''.join(f'<row r="{r}"><c r="A{r}" t="s"><v>0</v></c><c r="B{r}" t="inlineStr"><is><t>计划状态</t></is></c><c r="C{r}"><f>1+1</f><v>2</v></c></row>' for r in range(1,rows+1))
        package.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData>{data}</sheetData><mergeCells><mergeCell ref="A1:A2"/></mergeCells></worksheet>')
    return path


def test_xlsx_is_an_actual_understand_source(tmp_path):
    source=workbook(tmp_path)
    result=UnderstandPort().understand(UnderstandingRequest('workbook-read','理解来源',source_refs=(source,)),source_root=tmp_path)
    assert result.source_inventory
    assert result.evidence_refs
    assert any('sheet1.xml#' in r.locator for r in result.evidence_refs)
    assert any('A1' in r.quote and '管理事项' in r.quote for r in result.evidence_refs)
    assert any('FORMULA_NOT_RECALCULATED' in w for w in result.source_warnings)


@pytest.mark.parametrize('target,external',[('../outside.xml',False),('https://invalid.example/a',True)])
def test_external_or_escaping_sheet_target_refused(tmp_path,target,external):
    source=workbook(tmp_path,target=target,external=external)
    with pytest.raises(ValueError):_extract(source,source.name,'source','revision')


def test_workbook_truncation_is_explicit_and_bounded(tmp_path):
    source=workbook(tmp_path,rows=510)
    units,warnings=_extract(source,source.name,'source','revision')
    assert len(units)==500
    assert 'PARTIAL_LOCATOR_LIMIT_500' in warnings
    expanded,warnings=_extract(source,source.name,'source','revision',unit_limit=700)
    assert len(expanded)>500
    assert not any(w.startswith('PARTIAL_LOCATOR_LIMIT') for w in warnings)


def test_presentation_locator_truncation_is_not_silent(tmp_path):
    # A slide is read one text box at a time, so 510 cells are 510 shapes. The bare
    # <a:t> elements this fixture used to hold were not a deck Understand can read.
    source=tmp_path/'many.pptx'
    ns_p='http://schemas.openxmlformats.org/presentationml/2006/main'
    ns_a='http://schemas.openxmlformats.org/drawingml/2006/main'
    shapes=''.join(f'<p:sp><p:nvSpPr><p:nvPr/></p:nvSpPr><p:txBody><a:p><a:r><a:t>text {index}</a:t></a:r></a:p></p:txBody></p:sp>' for index in range(510))
    with zipfile.ZipFile(source,'w') as z:
        z.writestr('ppt/slides/slide1.xml',f'<p:sld xmlns:p="{ns_p}" xmlns:a="{ns_a}"><p:cSld><p:spTree>{shapes}</p:spTree></p:cSld></p:sld>')
    units,warnings=_extract(source,source.name,'source','revision')
    assert len(units)==500 and 'PARTIAL_LOCATOR_LIMIT_500' in warnings
