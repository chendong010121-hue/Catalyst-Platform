"""Synthetic adapter controls; real-entry acceptance is exercised separately."""
import json
import pytest
from catalyst_platform.evaluation_adapter import check_health, run_evaluation, compare_evaluations

PROFILE={'id':'unit','version':'1','dimensions':['TASK_SUCCESS'],'objective':'TASK_SUCCESS','hard_dimensions':['TASK_SUCCESS'],'owner':'capability-evaluation-v3','owner_blob':'7ab41c22454f255a89a66b93e449e2fd5c4deab8'}
def exact(observation,gold):
    ok=observation.get('answer')==gold['answer']
    return {'task_success':ok,'dimensions':{'TASK_SUCCESS':{'status':'PASS' if ok else 'FAIL','value':float(ok)}},'critical_faults':[], 'failure_class':None if ok else 'CAPABILITY_FAILURE'}
def probes():
    return [{'id':k,'basis':'INDEPENDENT','observation':o,'gold':{'answer':'correct'},'expected':e} for k,o,e in [('KNOWN_GOOD',{'answer':'correct'},True),('KNOWN_BAD',{'answer':'false'},False),('NULL',{},False),('WRONG_QUESTION_CONFIDENT',{'answer':'different task'},False),('BROKEN_TASK_OR_INFRA_ERROR',{'execution_error':'unavailable'},'INFRASTRUCTURE_ERROR')]]
def entry(public,workspace):return {'answer':public['answer'],'execution_kind':'UNIT_CONTROL','evidence_refs':[]}
def case(answer='correct',critical=False):return {'id':'c1','split':'val','critical':critical,'public':{'answer':answer},'gold':{'answer':'correct'}}
def run(tmp_path,name,cases=None,fn=entry,grader=exact):
    health=check_health(PROFILE,grader,probes())
    return run_evaluation(PROFILE,cases or [case()],fn,grader,tmp_path/name,health=health,target_identity=name)

def test_health_discriminates_oracle_bad_null_wrong_and_infra():
    assert check_health(PROFILE,exact,probes())['status']=='PASS'
def test_always_pass_grader_fails_health():
    def wrong(o,g):return exact({'answer':'correct'},g)
    assert check_health(PROFILE,wrong,probes())['status']=='FAIL'
def test_gold_never_enters_entry_and_observation_frozen_first(tmp_path):
    def observed(public,workspace):
        assert set(public)=={'answer'}
        return entry(public,workspace)
    r=run(tmp_path,'a',fn=observed)
    assert r['rows'][0]['task_success'] is True
    assert (tmp_path/'a/cases/c1/observation.json').is_file()
def test_infra_not_scored_zero(tmp_path):
    def broken(*args):raise OSError('offline')
    r=run(tmp_path,'a',fn=broken)
    assert r['rows'][0]['failure_class']=='INFRASTRUCTURE_ERROR'
    assert r['rows'][0]['task_success'] is None
def test_empty_case_set_rejected(tmp_path):
    with pytest.raises(ValueError):run_evaluation(PROFILE,[],entry,exact,tmp_path/'a',health=check_health(PROFILE,exact,probes()),target_identity='a')
def test_train_heldout_overlap_rejected(tmp_path):
    cases=[case(),dict(case(),id='c2',split='train')]
    with pytest.raises(ValueError,match='overlap'):run(tmp_path,'a',cases=cases)
def test_forged_execution_evidence_rejected(tmp_path):
    def forged(p,w):return {'answer':'correct','execution_kind':'PRODUCT_RUNTIME','evidence_refs':[{'path':'missing.json','sha256':'0'*64}]}
    r=run(tmp_path,'a',fn=forged)
    assert r['rows'][0]['failure_class']=='EVIDENCE_IDENTITY_ERROR'
def test_result_tampering_invalidates_comparison(tmp_path):
    run(tmp_path,'a');run(tmp_path,'b')
    (tmp_path/'b/cases/c1/observation.json').write_text('{}')
    with pytest.raises(ValueError,match='identity'):compare_evaluations(tmp_path/'a',tmp_path/'b')
def test_same_score_is_not_improvement(tmp_path):
    run(tmp_path,'a');run(tmp_path,'b')
    assert compare_evaluations(tmp_path/'a',tmp_path/'b')['accept'] is False


def test_real_file_tool_uses_runtime_and_r4(tmp_path):
    from catalyst_platform.evaluation_entries import file_title_entry
    observation=file_title_entry({'filename':'input.md','content':'# Real local title\n'},tmp_path)
    assert observation['execution_kind']=='PRODUCT_RUNTIME'
    assert observation['output']['title']=='Real local title'
    assert {r['role'] for r in observation['evidence_refs']}=={'r4','source','runtime_state'}

def test_existing_but_fabricated_r4_is_not_execution_evidence(tmp_path):
    import hashlib
    def forged(p,w):
        trace=w/'trace.jsonl';trace.write_text('{}\n')
        state=w/'state.json';state.write_text('{}')
        return {'answer':'correct','execution_kind':'PRODUCT_RUNTIME','run_id':'invented','capability_id':'read_file_title','evidence_refs':[{'path':str(x),'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'role':role} for x,role in [(trace,'r4'),(state,'runtime_state')]]}
    r=run(tmp_path,'a',fn=forged)
    assert r['rows'][0]['failure_class']=='EVIDENCE_IDENTITY_ERROR'

def test_higher_mean_cannot_hide_critical_regression(tmp_path):
    cases=[{'id':f'c{i}','split':'val','critical':i==0,'public':{'number':i},'gold':{'answer':'correct'}} for i in range(4)]
    def parent(p,w):return {'answer':'correct' if p['number']==0 else 'wrong','execution_kind':'UNIT_CONTROL','evidence_refs':[]}
    def candidate(p,w):return {'answer':'wrong' if p['number']==0 else 'correct','execution_kind':'UNIT_CONTROL','evidence_refs':[]}
    run(tmp_path,'a',cases=cases,fn=parent);run(tmp_path,'b',cases=cases,fn=candidate)
    decision=compare_evaluations(tmp_path/'a',tmp_path/'b')
    assert decision['accept'] is False and decision['reason']=='CRITICAL_REGRESSION'

def test_evaluator_identity_paths_opaque_but_result_prose_preserved(tmp_path):
    observed=[]
    def inspect_packet(o,g):
        observed.append(o)
        assert o['note']=='The source describes protocol V2 and baseline procedures.'
        assert 'baseline' not in o['output']['source']['path']
        return exact(o,g)
    oracle=probes()
    for probe in oracle:probe['observation'].update(note='The source describes protocol V2 and baseline procedures.',output={'source':{'path':str(tmp_path/'baseline/input.md')}})
    health=check_health(PROFILE,inspect_packet,oracle)
    assert health['status']=='PASS'


def test_frozen_review_rejects_benchmark_observation(tmp_path):
    result=run_evaluation(PROFILE,[case()],entry,exact,tmp_path/'frozen',health=check_health(PROFILE,exact,probes()),target_identity='frozen',mode='FROZEN_RESULT_REVIEW')
    assert result['rows'][0]['failure_class']=='EVIDENCE_IDENTITY_ERROR'
