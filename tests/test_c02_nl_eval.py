"""Synthetic NL Health only, never enterprise semantic Gold."""
import copy,hashlib
import pytest
from catalyst_platform.c02_nl_eval import nl_profile,nl_grader,atomic_digest
from catalyst_platform.evaluation_adapter import check_health


def fixture():
    quote='服务组负责登记；金额超过一万元时交财务复核，紧急抢修除外。'
    evidence=dict(evidence_id='e1',source_sha256='source1',locator='line:1',quote=quote,span_sha256=hashlib.sha256(quote.encode()).hexdigest())
    item=dict(kind='claim',key='registration',meaning=quote,evidence_class='SOURCE_DIRECT',evidence_refs=['e1'])
    observation={'items':[item],'evidence':[evidence],'source_manifest':{'source1':{'line:1':evidence['span_sha256']}}}
    assessment={'item_digest':atomic_digest(item),'mode':'DIRECT_SUPPORT','source_refs':['e1'],'conditions':['金额超过一万元时交财务复核'],'exceptions':['紧急抢修除外'],'scope':'服务组登记','basis':'Independent synthetic annotation, not automated entailment'}
    gold={'basis':'SYNTHETIC_NL_HEALTH_ONLY','required_claims':['registration'],'assessments':{'registration':assessment},'unanswerable':False}
    return observation,gold


def test_missing_real_nl_gold_is_not_measurement_crash_or_zero():
    o,g=fixture();r=nl_grader(o,{'basis':'UNVERIFIED_REFERENCE_HASH'})
    assert r['task_success'] is None and r['failure_class']=='CALIBRATION_PENDING'
    assert r['dimensions']['FACTUAL_PRECISION']['status']=='NOT_EVALUATED'


def test_source_reference_existence_does_not_prove_support():
    o,g=fixture();g['assessments']['registration']['mode']='INSUFFICIENT'
    assert nl_grader(o,g)['task_success'] is False


def test_independent_atomic_receipt_binds_exact_candidate_and_source():
    o,g=fixture();assert nl_grader(o,g)['task_success'] is True
    o['items'][0]['meaning']='财务组负责登记，所有金额都自动批准。'
    r=nl_grader(o,g);assert r['task_success'] is not True
    assert r['atomic_findings'][0]['mode']=='INSUFFICIENT'


@pytest.mark.parametrize('mode',['CONTRADICTED','INSUFFICIENT'])
def test_wrong_direction_time_state_conflict_or_condition_needs_independent_verdict(mode):
    o,g=fixture();g['assessments']['registration']['mode']=mode
    assert nl_grader(o,g)['task_success'] is False


@pytest.mark.parametrize('change',['quote','locator','sha','uncertainty','endpoint'])
def test_mechanical_negatives(change):
    o,g=fixture()
    if change=='quote':o['evidence'][0]['quote']='流畅但不相干的另一句话'
    elif change=='locator':o['evidence'][0]['locator']='line:999'
    elif change=='sha':o['evidence'][0]['source_sha256']='missing'
    elif change=='uncertainty':o['items'][0].update(evidence_class='UNKNOWN')
    else:o['items'][0].update(kind='relation',subject='missing',object='missing',predicate='owns')
    r=nl_grader(o,g);assert r['task_success'] is not True


@pytest.mark.parametrize('rows',[[],[dict(kind='unknown',key='all',meaning='都不知道',evidence_class='UNKNOWN',evidence_refs=[],uncertainty='未读')]])
def test_empty_or_universal_unknown_not_best(rows):
    o,g=fixture();o['items']=rows
    assert nl_grader(o,g)['task_success'] is False


def test_typed_null_defaults_do_not_change_semantic_digest():
    o,g=fixture();a=o['items'][0];b=dict(a,item_id='typed-generated',uncertainty=None,subject=None,predicate=None,object=None)
    assert atomic_digest(a)==atomic_digest(b)


@pytest.mark.parametrize('meaning',['服务组无须登记。','服务组所有金额都可直接批准。','财务部门负责登记。','制度现已生效。'])
def test_omitted_condition_reverse_responsibility_or_temporal_invention_cannot_reuse_assessment(meaning):
    o,g=fixture();o['items'][0]['meaning']=meaning
    assert nl_grader(o,g)['task_success'] is False


def test_conflicting_document_receipt_stays_contradicted():
    o,g=fixture();g['assessments']['registration']['mode']='CONTRADICTED'
    r=nl_grader(o,g);assert r['atomic_findings'][0]['mode']=='CONTRADICTED' and r['task_success'] is False


def test_real_nl_boolean_signoff_is_not_accepted_as_authoritative_gold():
    o,g=fixture();g.update(basis='INDEPENDENT_FROZEN_NL',owner_approved=True)
    assert nl_grader(o,g)['task_success'] is None


def test_existing_typed_evidence_class_alias_preserves_raw_claim_identity():
    o,g=fixture();o['items'][0]['evidence_class']='observed_from_source'
    assert nl_grader(o,g)['task_success'] is True


def test_corrupt_source_measurement_does_not_become_subject_zero():
    o,g=fixture();o['evidence'][0]['span_sha256']='corrupt'
    r=nl_grader(o,g);assert r['task_success'] is None and r['failure_class']=='SOURCE_IDENTITY_ERROR'


def test_positive_assessment_without_bound_source_refs_cannot_pass():
    o,g=fixture();g['assessments']['registration']['source_refs']=[]
    assert nl_grader(o,g)['task_success'] is not True


def test_multi_source_label_requires_distinct_sources():
    o,g=fixture();g['assessments']['registration']['mode']='MULTI_SOURCE_COMPOSITION'
    assert nl_grader(o,g)['task_success'] is not True
