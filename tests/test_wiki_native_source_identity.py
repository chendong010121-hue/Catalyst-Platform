"""Native document identity only; no claims, authority or model calls."""
import hashlib
import pytest
from catalyst_platform.wiki import ProjectWiki,WikiScopeError

@pytest.mark.parametrize('backend',['json','sqlite'])
@pytest.mark.parametrize('ext',['docx','pptx','pdf'])
def test_native_source_keeps_byte_identity_and_cold_read(tmp_path,backend,ext):
    root=tmp_path/'sources';root.mkdir();source=root/('document.'+ext);source.write_bytes(b'\x00native-test-bytes\xff')
    wiki=ProjectWiki(tmp_path/'workspace',[root],enterprise_id='synthetic',project_id='native',backend=backend)
    receipt=wiki.stage_native_source(source)
    assert receipt['revision']==hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt['claim_count']==0
    with pytest.raises(WikiScopeError):wiki.source_snapshot(receipt['source_id'])
    fresh=ProjectWiki(tmp_path/'workspace',[root],enterprise_id='synthetic',project_id='native',backend=backend).native_source_snapshot(receipt['source_id'])
    assert fresh['current_revision']==receipt['revision'] and fresh['source']['revision']==receipt['revision']
    assert 'content' not in fresh and 'bytes' not in fresh
    source.write_bytes(b'changed')
    stale=wiki.native_source_snapshot(receipt['source_id'])
    assert stale['current_revision']!=stale['source']['revision']


def test_native_source_rejects_outside_root_and_unsupported_format(tmp_path):
    root=tmp_path/'sources';root.mkdir();outside=tmp_path/'outside.pdf';outside.write_bytes(b'x');bad=root/'script.exe';bad.write_bytes(b'x')
    wiki=ProjectWiki(tmp_path/'workspace',[root],enterprise_id='synthetic',project_id='native')
    for p in (outside,bad):
        with pytest.raises(WikiScopeError):wiki.stage_native_source(p)


@pytest.mark.parametrize('maker,extension',[('_docx','docx'),('_pptx_table','pptx'),('_text_pdf','pdf')])
def test_native_document_evidence_maps_exact_location_without_inventing_claims(tmp_path,maker,extension):
    from tests import test_understand_only as f
    from catalyst_platform.understand_only import UnderstandPort,UnderstandingRequest
    from catalyst_platform.understand_wiki import UnderstandWikiAdapter
    root=tmp_path/'sources';root.mkdir();source=root/('evidence.'+extension);getattr(f,maker)(source)
    wiki=ProjectWiki(tmp_path/'workspace',[root],enterprise_id='synthetic',project_id='native')
    class Semantic:
        def stage_native_source(self,path,*,actor_origin):return wiki.stage_native_source(path)
        def _emit(self,*args,**kwargs):pass
    a=UnderstandWikiAdapter(wiki,Semantic(),root)
    result=UnderstandPort().understand(UnderstandingRequest('offline','inspect',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',scope_id=wiki.scope_id,requested_depth='semantic',budget_steps=16),source_root=root).to_dict()
    assert result['evidence_refs']
    bindings,content=a._source_files(result);mapping=a._map_evidence(result,bindings,content)
    assert bindings[0]['status']=='STAGED'
    assert all(x['mapping_status']=='MAPPED' for x in mapping)
    assert wiki.claim_history(bindings[0]['wiki_source_id'])==[]
    altered={**result,'evidence_refs':[dict(result['evidence_refs'][0],quote='different')]}
    assert a._map_evidence(altered,bindings,content)[0]['mapping_status']=='SPAN_DIGEST_MISMATCH'


@pytest.mark.parametrize('backend',['json','sqlite'])
@pytest.mark.parametrize('maker,extension',[('_docx','docx'),('_pptx_table','pptx'),('_text_pdf','pdf')])
def test_native_candidate_submit_cold_read_and_stale_refusal(tmp_path,backend,maker,extension):
    from tests import test_understand_only as f
    from catalyst_platform.understand_only import UnderstandPort,UnderstandingRequest
    from catalyst_platform.understand_wiki import UnderstandWikiAdapter
    from catalyst_platform.semantic_wiki import SemanticWiki
    from catalyst_platform.gateway import CatalystGateway
    root=tmp_path/'sources';root.mkdir();source=root/('evidence.'+extension);getattr(f,maker)(source)
    workspace=tmp_path/'workspace';wiki=ProjectWiki(workspace,[root],enterprise_id='synthetic',project_id='native',backend=backend);gateway=CatalystGateway(workspace)
    result=UnderstandPort().understand(UnderstandingRequest('offline-native','read document',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',scope_id=wiki.scope_id,requested_depth='semantic',budget_steps=16),source_root=root).to_dict()
    def submit(rec):return UnderstandWikiAdapter(wiki,SemanticWiki(wiki,recorder=rec),root).submit(result,declared_scope_id=wiki.scope_id)
    outcome=gateway.semantic_operation(operation='understand.candidate.submit',scope_id=wiki.scope_id,actor_origin='offline_fixture',input_value={'contract_version':'catalyst.understand_handoff.v1'},action=submit)
    receipt=outcome['result'];assert receipt['mapping_status']=='COMPLETE'
    cold=ProjectWiki(workspace,[root],enterprise_id='synthetic',project_id='native',backend=backend)
    class Reader:
        def _emit(self,*args,**kwargs):pass
    adapter=UnderstandWikiAdapter(cold,Reader(),root);eid=result['evidence_refs'][0]['evidence_id'];assert adapter.evidence(receipt['candidate_id'],eid)['status']=='RESOLVED'
    assert cold.semantic_state()['active_version_id'] is None
    source.write_bytes(source.read_bytes()+b'drift');assert adapter.evidence(receipt['candidate_id'],eid)['status']=='STALE_SOURCE_REVISION'


def test_native_mapping_rejects_forged_locator_and_unreadable_pdf(tmp_path):
    from tests.test_understand_only import _pptx
    from catalyst_platform.understand_only import UnderstandPort,UnderstandingRequest
    from catalyst_platform.understand_wiki import UnderstandWikiAdapter
    root=tmp_path/'sources';root.mkdir();source=root/'evidence.pptx';_pptx(source)
    wiki=ProjectWiki(tmp_path/'workspace',[root],enterprise_id='synthetic',project_id='native')
    class Semantic:
        def stage_native_source(self,path,*,actor_origin):return wiki.stage_native_source(path)
        def _emit(self,*args,**kwargs):pass
    a=UnderstandWikiAdapter(wiki,Semantic(),root)
    result=UnderstandPort().understand(UnderstandingRequest('offline','inspect',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',scope_id=wiki.scope_id,requested_depth='semantic',budget_steps=16),source_root=root).to_dict()
    bindings,content=a._source_files(result)
    altered={**result,'evidence_refs':[dict(result['evidence_refs'][0],locator='ppt/slides/slide9999.xml#text:1')]}
    assert a._map_evidence(altered,bindings,content)[0]['mapping_status']=='ANCHOR_MISMATCH'
    changed={**result,'evidence_refs':[dict(result['evidence_refs'][0],source_revision='OTHER_REVISION')]}
    assert a._map_evidence(changed,bindings,content)[0]['mapping_status']=='SOURCE_IDENTITY_MISMATCH'
    broken=root/'broken.pdf';broken.write_bytes(b'not a pdf')
    from pypdf.errors import PdfReadError
    with pytest.raises(PdfReadError):
        UnderstandPort().understand(UnderstandingRequest('broken','inspect',source_refs=(broken,),intent='KNOWLEDGE_PROPOSE',scope_id=wiki.scope_id,requested_depth='semantic',budget_steps=16),source_root=root)


def test_native_source_does_not_break_existing_markdown_source_discovery(tmp_path):
    from catalyst_platform.source_connection import SourceReadService
    root=tmp_path/'sources';root.mkdir();md=root/'source.md';md.write_text('# Hiring policy\nHiring role and policy.',encoding='utf8');native=root/'hiring.pdf';native.write_bytes(b'native identity only')
    wiki=ProjectWiki(tmp_path/'workspace',[root],enterprise_id='synthetic',project_id='native')
    wiki.stage_markdown(md);wiki.stage_native_source(native)
    result=SourceReadService(wiki).search('hiring','synthetic')
    assert result['references'] and all(r['source_id'] for r in result['references'])
