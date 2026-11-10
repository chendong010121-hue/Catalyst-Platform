"""Bounded structural controls, never independent enterprise Gold."""
import hashlib,json
from pathlib import Path
import pytest
from catalyst_platform.project_understand import ProjectAnalysisContext,ProjectUnderstandingRequest,validate_project_handoff,ProjectAnalysisError,source_manifest
from tests.project_understand.test_progressive_analysis import packet
from tests.project_understand.test_project_runtime import setup,offline
from catalyst_platform.observability import RunRecorder
from catalyst_platform.trace_log import JsonlTraceStore
import uuid

@pytest.mark.parametrize('kind', ['agent','plugin','skill','repository','tool','workflow'])
def test_object_has_frozen_critical_questions(kind):
    req=ProjectUnderstandingRequest('r','inspect',kind,2)
    assert req.critical_questions
    value=packet();value['object_type']=kind;value['decision_readiness']='NEEDS_EVIDENCE'
    with pytest.raises(ProjectAnalysisError,match='critical'):
        validate_project_handoff(value,request=req,manifest=[{'source_id':'s1'}],evidence=[],source_reads=[])

def test_producer_cannot_downgrade_frozen_critical_question():
    req=ProjectUnderstandingRequest('r','inspect','agent',2,('failure',))
    value=packet();value['questions'][0]['critical']=False
    with pytest.raises(ProjectAnalysisError,match='critical'):
        validate_project_handoff(value,request=req,manifest=[{'source_id':'s1'}],evidence=[],source_reads=[])

def context(session,root):
    rec=RunRecorder(JsonlTraceStore(session.workspace),run_id='run_'+uuid.uuid4().hex,request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex)
    rec.start(request_kind='project_analysis')
    return rec, session.app.components.acquire_method('project-understand')

def test_same_source_is_not_read_twice_and_references_are_selected(tmp_path,offline):
    session,root=setup(tmp_path);rec,lease=context(session,root)
    with lease as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec)
        initial=ctx.initial_context();name=next(p for p in method['files'] if p.startswith('references/'))
        assert ctx.method_reads==['SKILL.md']
        sid=ctx.manifest[0]['source_id']
        first=ctx.execute('project_inspect',{'query':'entry','source_ids':[sid],'references':[name]})
        second=ctx.execute('project_inspect',{'query':'entry','source_ids':[sid]})
        assert len(ctx.source_reads)==1 and len(first['evidence'])==len(second['evidence'])
        assert ctx.method_reads==['SKILL.md',name]
        assert first['structural_facts']
    rec.finish('success')

def test_source_drift_and_outside_source_id_refuse_without_reads(tmp_path,offline):
    session,root=setup(tmp_path);rec,lease=context(session,root)
    with lease as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec)
        with pytest.raises(ProjectAnalysisError,match='source_ids'):
            ctx.execute('project_inspect',{'query':'entry','source_ids':['outside']})
        (root/'agent.py').write_text('changed',encoding='utf-8')
        with pytest.raises(ProjectAnalysisError,match='changed'):
            ctx.execute('project_inspect',{'query':'entry','source_ids':[ctx.manifest[0]['source_id']]})
        assert ctx.source_reads==[]
    rec.finish('failure')

def test_license_text_and_unsupported_javascript_are_distinct(tmp_path,offline):
    session,root=setup(tmp_path)
    (root/'LICENSE').write_text('Fixture license, no enterprise authority.',encoding='utf-8')
    (root/'unsupported.ts').write_text('export const x = 1;',encoding='utf-8')
    rec,lease=context(session,root)
    with lease as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec)
        lic=next(r['source_id'] for r in ctx.manifest if r['relative_path']=='LICENSE')
        js=next(r['source_id'] for r in ctx.manifest if r['relative_path']=='unsupported.ts')
        out=ctx.execute('project_inspect',{'query':'license and unsupported','source_ids':[lic,js]})
        assert [r['source_id'] for r in out['source_reads']]==[lic]
        assert out['unsupported_sources'][0]['source_id']==js and js in out['unread_source_ids']
        assert out['evidence'][0]['quote']=='Fixture license, no enterprise authority.'
    rec.finish('success')

def test_expansion_denial_is_not_normal_success(tmp_path,offline,monkeypatch):
    session,root=setup(tmp_path);rec,lease=context(session,root)
    with lease as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec)
        sid=ctx.manifest[0]['source_id'];ctx.execute('project_inspect',{'query':'entry','source_ids':[sid]})
        from catalyst_platform.understand_only import EvidenceExpansionResult
        monkeypatch.setattr(ctx.port,'expand_evidence',lambda *a,**k: EvidenceExpansionResult(rec.request_id,'STALE_SOURCE','STALE_SOURCE'))
        with pytest.raises(ProjectAnalysisError,match='stale_source'):
            ctx.execute('project_expand_evidence',{'query':'gap','source_ids':[sid]})
        assert ctx.expansion_receipts[-1]['status']=='STALE_SOURCE'
    rec.finish('failure')


def test_license_does_not_poison_later_native_expansion(tmp_path,offline):
    session,root=setup(tmp_path)
    (root/'LICENSE').write_text('Fixture terms.',encoding='utf-8')
    rec,lease=context(session,root)
    with lease as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec)
        lic=next(r['source_id'] for r in ctx.manifest if r['relative_path']=='LICENSE')
        py=next(r['source_id'] for r in ctx.manifest if r['relative_path']=='agent.py')
        ctx.execute('project_inspect',{'query':'license','source_ids':[lic]})
        ctx.execute('project_expand_evidence',{'query':'main','source_ids':[py]})
        assert ctx.expansion_receipts[-1]['status'] in {'EXPANDED','NO_MATCH'}
    rec.finish('success')


def test_windows_source_junction_rejected_before_enumeration(tmp_path):
    import os,subprocess
    if os.name!='nt':pytest.skip('Windows junction check')
    from catalyst_platform.project_understand import source_manifest
    outside=tmp_path/'outside';outside.mkdir();(outside/'private.py').write_text('not admitted',encoding='utf-8')
    root=tmp_path/'root';root.mkdir();(root/'safe.py').write_text('safe',encoding='utf-8')
    link=root/'junction'
    result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(outside)],capture_output=True)
    assert result.returncode==0
    try:
        with pytest.raises(ProjectAnalysisError,match='symlink_denied'):source_manifest(root)
        with pytest.raises(ProjectAnalysisError,match='symlink_denied'):source_manifest(link)
    finally:
        os.rmdir(link)


def test_full_host_read_does_not_expose_or_authorize_every_line(tmp_path,offline):
    session,root=setup(tmp_path)
    (root/'worker.py').write_text('\n'.join('value_'+str(i)+' = '+str(i) for i in range(90)),encoding='utf-8')
    rec,lease=context(session,root)
    with lease as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec)
        sid=next(r['source_id'] for r in ctx.manifest if r['relative_path']=='worker.py')
        out=ctx.execute('project_inspect',{'query':'value_15','source_ids':[sid]})
        assert len(out['evidence'])<=4 and len(ctx.native_evidence)>len(ctx.evidence)
        assert out['source_reads'][0]['source_id']==sid
        assert any('PARTIAL_MODEL_DISCLOSURE' in str(w) for w in ctx.source_warnings)
        hidden=next(e for e in ctx.native_evidence if e.evidence_id not in {x['evidence_id'] for x in ctx.evidence})
        assert hidden.evidence_id not in {x['evidence_id'] for x in out['evidence']}
    rec.finish('success')


def test_repeated_gap_expansion_keeps_native_evidence_unique(tmp_path,offline):
    session,root=setup(tmp_path)
    (root/'worker.py').write_text('\n'.join('value_'+str(i)+' = '+str(i) for i in range(12)),encoding='utf-8')
    rec,lease=context(session,root)
    with lease as method:
        ctx=ProjectAnalysisContext(session.session,ProjectUnderstandingRequest(rec.request_id,'inspect','agent',2),root,method,rec)
        sid=next(r['source_id'] for r in ctx.manifest if r['relative_path']=='worker.py')
        ctx.execute('project_inspect',{'query':'value_1','source_ids':[sid]})
        initial_count=len(ctx.native_evidence)
        ctx.execute('project_expand_evidence',{'query':'value_5','source_ids':[sid]})
        assert ctx.expansion_receipts[-1]['status']=='EXPANDED'
        ctx.execute('project_expand_evidence',{'query':'value_9','source_ids':[sid]})
        assert ctx.expansion_receipts[-1]['status']=='EXPANDED'
        ids=[e.evidence_id for e in ctx.native_evidence]
        assert len(ids)==len(set(ids))==initial_count
        assert len(ctx.source_reads)==1
        assert any(e['quote']=='value_5 = 5' for e in ctx.evidence)
        assert any(e['quote']=='value_9 = 9' for e in ctx.evidence)
    rec.finish('success')
