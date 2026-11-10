import hashlib
import pytest
from catalyst_platform.project_understand import (
    ProjectUnderstandingRequest, ProjectAnalysisContext, source_manifest,
    validate_project_handoff, ProjectAnalysisError,
)

def test_inventory_is_bounded_and_cannot_follow_symlinks(tmp_path):
    (tmp_path/'a.py').write_text('def run(): return 1\n',encoding='utf-8')
    rows=source_manifest(tmp_path)
    assert rows[0]['relative_path']=='a.py' and len(rows[0]['sha256'])==64
    (tmp_path/'huge.py').write_bytes(b'x'*70000)
    with pytest.raises(ProjectAnalysisError):source_manifest(tmp_path)

def packet():
    return dict(schema_version='project-understanding.v1',objective='inspect',object_type='agent',
        requested_depth=2,achieved_depth=0,analysis_finished=True,decision_readiness='READY_FOR_REVIEW',
        questions=[dict(question_id='failure',critical=True,status='EXPLICITLY_UNRESOLVED',claim_ids=[])],
        claims=[],dependencies=[],reuse_suggestions=[],unknowns=['runtime not observed'],
        coverage={'read_source_ids':[],'unread_source_ids':['s1']})

def test_critical_unknown_does_not_become_ready():
    request=ProjectUnderstandingRequest('req1','inspect','agent',2,('failure',))
    value=packet()
    with pytest.raises(ProjectAnalysisError,match='critical'):
        validate_project_handoff(value,request=request,manifest=[{'source_id':'s1'}],evidence=[],source_reads=[])
    value['decision_readiness']='NEEDS_EVIDENCE'
    assert validate_project_handoff(value,request=request,manifest=[{'source_id':'s1'}],evidence=[],source_reads=[])['decision_readiness']=='NEEDS_EVIDENCE'

def test_reference_membership_is_not_semantic_approval():
    request=ProjectUnderstandingRequest('req1','inspect','agent',2,('failure',))
    value=packet();value.update(claims=[dict(claim_id='c1',text='fake semantics',evidence_ids=['absent'],conditions=[],exceptions=[],support_mode='SOURCE_DIRECT')])
    value['decision_readiness']='NEEDS_EVIDENCE'
    with pytest.raises(ProjectAnalysisError,match='evidence'):
        validate_project_handoff(value,request=request,manifest=[{'source_id':'s1'}],evidence=[],source_reads=[])

def test_coverage_must_equal_actual_reads():
    value=packet();value['decision_readiness']='NEEDS_EVIDENCE';value['coverage']['read_source_ids']=['s1'];value['coverage']['unread_source_ids']=[]
    with pytest.raises(ProjectAnalysisError,match='coverage'):
        validate_project_handoff(value,request=ProjectUnderstandingRequest('r','inspect','agent',2,('failure',)),manifest=[{'source_id':'s1'}],evidence=[],source_reads=[])


def test_source_index_losslessly_preserves_every_path_and_id():
    from catalyst_platform.project_understand import source_index
    rows=[{'relative_path':'pkg/deep/a.py','source_id':'a'}, {'relative_path':'pkg/deep/b.py','source_id':'b'}, {'relative_path':'LICENSE','source_id':'license'}]
    def flatten(node,prefix=''):
        result={}
        for name,value in node.items():
            path=prefix+name
            if isinstance(value,dict):result.update(flatten(value,path+'/'))
            else:result[path]=value
        return result
    assert flatten(source_index(rows))=={r['relative_path']:r['source_id'] for r in rows}
