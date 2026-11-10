"""One source-type list in front of every gate, and a document that reaches units.

The three gates that decide whether a selected file may be read (session routing in
``user_session`` and ``workspace_session``, and the semantic test manifest) each used to
carry their own literal set of suffixes. A file could be accepted by one and refused by
the next with nothing failing in between, so a Word document was admitted to the demo
and then never became units.
"""
import inspect
import zipfile

import pytest

from catalyst_platform import semantic_acceptance, understand_sources, user_session, workspace_session
from catalyst_platform.semantic_acceptance import file_manifest
from catalyst_platform.understand_sources import SOURCE_SUFFIXES, _extract, _safe_file

_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def docx(tmp_path, paragraphs):
    path = tmp_path / 'brief.docx'
    body = ''.join(f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p>' for text in paragraphs)
    with zipfile.ZipFile(path, 'w') as package:
        package.writestr('word/document.xml', f'<w:document xmlns:w="{_NS}"><w:body>{body}</w:body></w:document>')
    return path


def test_source_gates_share_one_suffix_list():
    assert SOURCE_SUFFIXES == frozenset({'.txt', '.md', '.pptx', '.docx', '.pdf', '.xlsx'})
    for module in (user_session, workspace_session, semantic_acceptance):
        # the same object, not a copy that happens to hold the same strings today
        assert module.SOURCE_SUFFIXES is understand_sources.SOURCE_SUFFIXES
        assert 'SOURCE_SUFFIXES' in inspect.getsource(module)
    # a gate may never let through a type the reader behind it refuses
    assert SOURCE_SUFFIXES <= understand_sources._ALLOWED


@pytest.mark.parametrize('name', ['brief.docx', 'brief.pdf', 'brief.xlsx', 'deck.pptx', 'notes.md', 'notes.txt'])
def test_manifest_admits_every_gated_format(tmp_path, name):
    (tmp_path / name).write_bytes(b'synthetic')
    assert [row['relative_path'] for row in file_manifest(tmp_path)] == [name]


def test_manifest_still_refuses_a_type_outside_the_gate(tmp_path):
    (tmp_path / 'payload.exe').write_bytes(b'synthetic')
    with pytest.raises(ValueError, match='source_type_not_supported'):
        file_manifest(tmp_path)


def test_reader_gate_admits_the_same_suffixes(tmp_path):
    for name in ('brief.docx', 'deck.pptx', 'notes.md'):
        path = tmp_path / name
        path.write_bytes(b'synthetic')
        _safe_file(path, tmp_path)
    (tmp_path / 'payload.exe').write_bytes(b'synthetic')
    with pytest.raises(ValueError, match='unsupported'):
        _safe_file(tmp_path / 'payload.exe', tmp_path)


def test_docx_through_the_gate_becomes_addressed_units(tmp_path):
    source = docx(tmp_path, ['一、总体要求', '企业管理部负责统筹转型工作。', '二、主要做法', '各分公司按区域设置。'])
    units, warnings = _extract(source, source.name, 's1', 'r1')
    assert [unit.locator for unit in units] == [f'word/document.xml#paragraph:{index}' for index in range(1, 5)]
    assert units[1].quote == '企业管理部负责统筹转型工作。'
    assert not [warning for warning in warnings if warning.startswith('UNSUPPORTED')]
