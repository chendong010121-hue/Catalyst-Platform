"""Read-only claim-relative checks over existing R4 and frozen receipts.

Not an event producer, monitor, or independent Host attestation authority.
"""
import hashlib,json
from pathlib import Path


def audit_observation(events,path,pin,*,expected_spans=(),claimed_tool=False,provider_tool_receipt=False,input_before=None,input_after=None,eval_input=None,frozen_output=None,origin_roles=(),attempt_count=None,response_count=None,usage_expected=None,usage_recorded=None):
    path=Path(path)
    disk='MISSING' if not path.is_file() else 'MATCH' if hashlib.sha256(path.read_bytes()).hexdigest()==pin else 'MISMATCH'
    if disk=='MATCH':
        try:
            if [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]!=events:disk='MISMATCH'
        except (ValueError,OSError):disk='MISMATCH'
    duplicate=len({e.get('event_id') for e in events})!=len(events)
    mismatch=len({e.get('run_id') for e in events})!=1 or len({e.get('trace_id') for e in events})!=1
    spans={e.get('span_id') for e in events if e.get('event_type')=='span.started'}
    orphan=any(e.get('parent_span_id') and e['parent_span_id'] not in spans for e in events)
    sequence=[e.get('sequence') for e in events]==list(range(len(events)))
    coverage='AMBIGUOUS' if duplicate or mismatch or orphan or not sequence else 'MISSING' if not set(expected_spans)<=spans or disk=='MISSING' else 'AMBIGUOUS' if disk!='MATCH' else 'DIRECTLY_OBSERVED'
    # Even matching caller-provided pin cannot authenticate a malicious Host.
    return {'coverage':coverage,'disk_binding':disk,'duplicate_event_ids':duplicate,'run_or_trace_mismatch':mismatch,'parent_orphans':orphan,'sequence_complete':sequence,'tool_selection':'CORRELATED_PROVIDER_RECEIPT' if claimed_tool and provider_tool_receipt else 'NOT_PROVEN' if claimed_tool else 'NOT_APPLICABLE','observer_purity':'UNKNOWN' if input_before is None or input_after is None else 'DETECTED' if input_before!=input_after else 'NO_OBSERVED_CHANGE','evaluation_binding':'UNKNOWN' if eval_input is None or frozen_output is None else 'DETECTED' if eval_input!=frozen_output else 'MATCH','information_leak':'DETECTED' if set(origin_roles)-{'generic_contract','neutral_user_request','original_sources','admitted_source_ids','actual_tool_result'} else 'NO_FORBIDDEN_DECLARED_ORIGIN','attempt_reconciliation':'UNKNOWN' if attempt_count is None or response_count is None else 'DETECTED' if attempt_count!=response_count else 'MATCH','usage_reconciliation':'UNKNOWN' if usage_expected is None or usage_recorded is None else 'DETECTED' if usage_expected!=usage_recorded else 'MATCH','independent_host_forgery':'CANNOT_OBSERVE','scope':'Consistency evidence with trusted pins; not NO_INTERFERENCE or general semantic leak detection'}
