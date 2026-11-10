"""Observability claims are conditional, not self-authenticating Host proof."""
import copy,json,hashlib
from catalyst_platform.c02_observation_audit import audit_observation


def fixture(tmp_path):
    events=[dict(event_id='a',trace_id='t',run_id='r',event_type='request.started',sequence=0),dict(event_id='b',trace_id='t',run_id='r',event_type='span.started',span_id='s',sequence=1),dict(event_id='c',trace_id='t',run_id='r',event_type='span.ended',span_id='s',sequence=2),dict(event_id='d',trace_id='t',run_id='r',event_type='request.terminal',sequence=3)]
    p=tmp_path/'r4.jsonl';p.write_bytes(b''.join(json.dumps(e).encode()+b'\n' for e in events))
    return events,p,hashlib.sha256(p.read_bytes()).hexdigest()


def test_missing_span_and_wrong_run_and_duplicates(tmp_path):
    e,p,pin=fixture(tmp_path)
    assert audit_observation(e,p,pin,expected_spans=['absent'])['coverage']=='MISSING'
    bad=copy.deepcopy(e);bad[1]['run_id']='other'
    assert audit_observation(bad,p,pin)['coverage']=='AMBIGUOUS'
    assert audit_observation(e+[e[1]],p,pin)['coverage']=='AMBIGUOUS'


def test_nonpersisting_or_backfilled_trace_refused(tmp_path):
    e,p,pin=fixture(tmp_path);p.unlink()
    assert audit_observation(e,p,pin)['disk_binding']=='MISSING'
    p.write_text('{}')
    assert audit_observation(e,p,pin)['disk_binding']=='MISMATCH'


def test_handmade_tool_without_native_receipt_not_proven(tmp_path):
    e,p,pin=fixture(tmp_path)
    r=audit_observation(e,p,pin,claimed_tool=True,provider_tool_receipt=False)
    assert r['tool_selection']=='NOT_PROVEN'


def test_gold_overflow_or_observer_mutation_or_old_artifact_rejected(tmp_path):
    e,p,pin=fixture(tmp_path)
    r=audit_observation(e,p,pin,input_before='a',input_after='b',eval_input='old',frozen_output='new',origin_roles=['gold'])
    assert r['observer_purity']=='DETECTED' and r['evaluation_binding']=='DETECTED' and r['information_leak']=='DETECTED'


def test_usage_and_hidden_attempt_not_silently_accepted(tmp_path):
    e,p,pin=fixture(tmp_path)
    r=audit_observation(e,p,pin,attempt_count=2,response_count=1,usage_expected=99,usage_recorded=2)
    assert r['attempt_reconciliation']=='DETECTED' and r['usage_reconciliation']=='DETECTED'


def test_matching_host_forgery_not_independently_detectable(tmp_path):
    e,p,pin=fixture(tmp_path);r=audit_observation(e,p,pin)
    assert r['independent_host_forgery']=='CANNOT_OBSERVE'


def test_correct_hash_of_old_disk_trace_cannot_attest_other_events(tmp_path):
    e,p,pin=fixture(tmp_path);new=copy.deepcopy(e)
    for row in new:row['run_id']='new-run';row['trace_id']='new-trace'
    r=audit_observation(new,p,pin)
    assert r['disk_binding']=='MISMATCH' and r['coverage']=='AMBIGUOUS'
