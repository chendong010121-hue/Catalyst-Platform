"""Synthetic schema controls; confidential real outputs supplied locally, never committed."""
import copy,hashlib,json,os
from pathlib import Path
import pytest
from catalyst_platform.c02_nl_eval import nl_grader

def observation(rows):
    quote='Synthetic source only.';span=hashlib.sha256(quote.encode()).hexdigest()
    return dict(items=rows,evidence=[dict(evidence_id='e1',source_sha256='s1',locator='line:1',quote=quote,span_sha256=span)],source_manifest={'s1':{'line:1':span}})

def item(kind='claim',key='a',**kw):
    return dict(kind=kind,key=key,meaning='Synthetic meaning',evidence_class='SOURCE_DIRECT',evidence_refs=['e1'],**kw)

@pytest.mark.parametrize('kind',['inference','Claim','UNKNOWN','unsupported'])
def test_illegal_kind_must_fail_structure(kind):
    assert nl_grader(observation([item(kind)]),{'basis':'CALIBRATION_PENDING'})['dimensions']['STRUCTURE_VALIDITY']['status']=='FAIL'

@pytest.mark.parametrize('kind',['entity','claim','condition','exception','negative_claim','alias','conflict','unknown'])
def test_original_legal_kinds_remain_accepted(kind):
    row=item(kind)
    if kind=='unknown':row.update(evidence_class='UNKNOWN',uncertainty='Synthetic unknown')
    assert nl_grader(observation([row]),{'basis':'CALIBRATION_PENDING'})['dimensions']['STRUCTURE_VALIDITY']['status']=='PASS'

def test_legal_forward_reference_remains_accepted():
    rows=[item('relation',key='r',subject='@a',predicate='owns',object='@b'),item('entity','b'),item('entity','a')]
    assert nl_grader(observation(rows),{'basis':'CALIBRATION_PENDING'})['dimensions']['STRUCTURE_VALIDITY']['status']=='PASS'

@pytest.mark.parametrize('change',['dangling','uncertainty_missing','uncertainty_type','meaning_type','claim_key_type'])
def test_original_contract_negative(change):
    row=item()
    if change=='dangling':row.update(kind='relation',subject='a',predicate='owns',object='missing')
    elif change=='uncertainty_missing':row.update(kind='unknown',evidence_class='UNKNOWN')
    elif change=='uncertainty_type':row.update(kind='unknown',evidence_class='UNKNOWN',uncertainty=3)
    elif change=='meaning_type':row['meaning']=123
    else:row['key']=4
    assert nl_grader(observation([row]),{'basis':'CALIBRATION_PENDING'})['dimensions']['STRUCTURE_VALIDITY']['status']=='FAIL'

@pytest.mark.parametrize('arm,expected',[('A','PASS'),('B','FAIL')])
def test_frozen_real_m3_output(arm,expected):
    configured=os.environ.get('CATALYST_M4_FROZEN_ROOT')
    if not configured:pytest.skip('Owner-local confidential fixture not configured')
    root=Path(configured)/'execution/live/private'/arm
    raw=root/'extraction_HTTP_RESPONSE.raw';request=root/'extraction_MODEL_REQUEST.json'
    observation=dict(review_kind='CONFIDENTIAL_FROZEN_RESPONSE_DIAGNOSTIC',frozen_output_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
    gold=dict(basis='CALIBRATION_PENDING',frozen_artifacts=dict(response=str(raw),response_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),request=str(request),request_sha256=hashlib.sha256(request.read_bytes()).hexdigest()))
    result=nl_grader(observation,gold)
    assert result['dimensions']['STRUCTURE_VALIDITY']['status']==expected
    assert result['task_success'] is None and result['formal_nl_semantic_evaluation']=='NOT_EVALUATED'

def test_grading_does_not_mutate_input():
    value=observation([item('inference')]);before=copy.deepcopy(value)
    nl_grader(value,{'basis':'CALIBRATION_PENDING'});assert value==before

def test_original_typed_validator_called_without_io(monkeypatch):
    import sys
    from catalyst_platform.understand_only import UnderstandPort
    original=UnderstandPort.attach_producer_items;calls=[];active=[False]
    def wrapped(*args,**kwargs):
        assert kwargs['recorder'] is None
        calls.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(UnderstandPort,'attach_producer_items',wrapped)
    def deny(event,args):
        if not active[0]:return
        if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.mkdir','os.remove','os.rename'):
            raise AssertionError('Grading side effect: '+event)
        if event=='open':
            path,mode,flags=args
            if isinstance(mode,str) and any(x in mode for x in 'wax+'):
                raise AssertionError('Grading filesystem write')
    sys.addaudithook(deny);active[0]=True
    try:
        assert nl_grader(observation([item()]),{'basis':'CALIBRATION_PENDING'})['dimensions']['STRUCTURE_VALIDITY']['status']=='PASS'
        assert nl_grader(observation([item('inference')]),{'basis':'CALIBRATION_PENDING'})['dimensions']['STRUCTURE_VALIDITY']['status']=='FAIL'
    finally:active[0]=False
    assert calls==[1,1]
