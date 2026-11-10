"""Method-local NL evaluation applicability and independent atomic assessments.

This adapter verifies receipt/data binding. It does not infer entailment from
text overlap, create authoritative Gold, or grant Evaluation/Owner authority.
"""
import hashlib
import json
from pathlib import Path
from .evaluation_adapter import OWNER_BLOB,digest
from .evaluation_profiles import ONTOLOGY_DIMENSIONS,_dimension

MODES={'DIRECT_SUPPORT','MULTI_SOURCE_COMPOSITION','BOUNDED_INFERENCE','INSUFFICIENT','CONTRADICTED'}
CLASSES={'observed_from_source':'SOURCE_DIRECT','inferred':'INFERRED','conflict':'CONFLICT','unresolved':'UNKNOWN'}

def atomic_digest(item):
    value={k:item.get(k) for k in ('kind','key','meaning','evidence_class','evidence_refs','uncertainty','subject','predicate','object')}
    value['evidence_class']=CLASSES.get(value['evidence_class'],value['evidence_class'])
    return digest(value)


def nl_profile():
    return {'id':'NL_C02','version':'2','owner_blob':OWNER_BLOB,'owner':'capability-evaluation-v3','dimensions':ONTOLOGY_DIMENSIONS,'objective':'TASK_SUCCESS','hard_dimensions':['STRUCTURE_VALIDITY','SOURCE_SUPPORT','FACTUAL_PRECISION','COMPETENCY_COVERAGE'],'scope':'Original typed attachment plus mechanical checks and bound independent atomic assessments. No automatic NL entailment or Owner authority.'}


def _typed_attachment_accepts(rows,evidence):
    """Reuse the existing in-memory typed check, without a producer/store/recorder.

    The empty seed is schema context only, not a source scan or a persisted
    Candidate. Endpoint and uncertainty obligations remain checked below.
    No second kind enum/Schema is maintained here. The original Port is unchanged.
    """
    from .understand_only import (UnderstandPort,UnderstandingResult,UnderstandIntent,
                                 IntentRoute,EvidenceRef)
    seed=UnderstandingResult(version='0.1.0',request_id='evaluation-schema-only',
        intent=UnderstandIntent.KNOWLEDGE_PROPOSE,result_type='SemanticCandidate',
        status='PARTIAL',route=IntentRoute(UnderstandIntent.KNOWLEDGE_PROPOSE,'evaluation','schema-only'),
        evidence_refs=tuple(EvidenceRef(evidence_id=e['evidence_id'],source_id='',relative_path='',
            source_revision='',source_sha256=e.get('source_sha256',''),locator=e.get('locator',''),
            quote=e.get('quote',''),span_sha256=e.get('span_sha256','')) for e in evidence.values()))
    try:
        UnderstandPort().attach_producer_items(seed,producer_kind='CATALYST_NATIVE_MODEL',
            producer_invocation_id='evaluation-schema-only',items=rows,recorder=None)
    except (ValueError,TypeError):
        return False
    return True


def nl_grader(observation,gold):
    if observation.get('review_kind')=='CONFIDENTIAL_FROZEN_RESPONSE_DIAGNOSTIC':
        # Evaluator-private paths, never passed to a live Subject or exported.
        refs=gold['frozen_artifacts'];response=Path(refs['response']);request=Path(refs['request'])
        for p,key in [(response,'response_sha256'),(request,'request_sha256')]:
            if hashlib.sha256(p.read_bytes()).hexdigest()!=refs[key]:raise ValueError('Frozen artifact drift')
        if observation['frozen_output_sha256']!=refs['response_sha256']:raise ValueError('Evaluation bound to a different output')
        wire=json.loads(response.read_text(encoding='utf-8'));packet=json.loads(request.read_text(encoding='utf-8'));payload=json.loads(packet['messages'][-1]['content'])
        evidence=[];manifest={}
        for e in payload['evidence']:
            source=payload['sources'][e['s']]['source_sha256'];span=hashlib.sha256(e['quote'].encode()).hexdigest()
            evidence.append({'evidence_id':e['evidence_id'],'source_sha256':source,'span_sha256':span,'quote':e['quote'],'locator':e['locator']});manifest.setdefault(source,{})[e['locator']]=span
        raw=json.loads(wire['choices'][0]['message']['content'])
        result=nl_grader({'items':raw['items'],'evidence':evidence,'source_manifest':manifest},{'basis':'CALIBRATION_PENDING'})
        # Findings contain only item hashes, anonymous positions and counts.
        result['atomic_findings']=[{'item_index':i,'item_digest':f['item_digest'],'mode':f['mode'],'basis':'REAL_ENTERPRISE_NL_NOT_EVALUATED'} for i,f in enumerate(result['atomic_findings'])]
        result['frozen_output_sha256']=refs['response_sha256'];return result
    rows=observation.get('items',[]);evidence={e['evidence_id']:e for e in observation.get('evidence',[])}
    manifest=observation.get('source_manifest',{});violations=[];source_errors=[];findings=[]
    if not _typed_attachment_accepts(rows,evidence):
        violations.append({'reason':'TYPED_VALIDATOR_REJECTED','validator':'UnderstandPort.attach_producer_items'})
    entities={r.get('key') for r in rows if isinstance(r,dict) and r.get('kind')=='entity'}
    identities=set()
    for index,r in enumerate(rows):
        if not isinstance(r,dict):violations.append({'index':index,'reason':'INVALID_ITEM'});continue
        kind,key=r.get('kind'),r.get('key');identity=(kind,key)
        evidence_class=CLASSES.get(r.get('evidence_class'),r.get('evidence_class'))
        if not isinstance(key,str) or not key.strip() or not isinstance(kind,str) or not r.get('meaning'):violations.append({'index':index,'reason':'REQUIRED_FIELD'})
        if identity in identities:violations.append({'index':index,'reason':'DUPLICATE_ID'})
        identities.add(identity)
        if evidence_class not in {'SOURCE_DIRECT','INFERRED','CONFLICT','UNKNOWN'}:violations.append({'index':index,'reason':'EVIDENCE_CLASS'})
        if evidence_class in {'INFERRED','UNKNOWN'} and not str(r.get('uncertainty') or '').strip():violations.append({'index':index,'reason':'MISSING_UNCERTAINTY'})
        if kind=='relation':
            for endpoint in ['subject','object']:
                value=r.get(endpoint)
                if not isinstance(value,str) or value.lstrip('@') not in entities:violations.append({'index':index,'reason':'MISSING_'+endpoint.upper()})
        refs=r.get('evidence_refs')
        if not isinstance(refs,list):violations.append({'index':index,'reason':'EVIDENCE_REF_SHAPE'});refs=[]
        if not refs and evidence_class=='SOURCE_DIRECT':source_errors.append({'index':index,'reason':'NO_SOURCE'})
        for ref in refs:
            e=evidence.get(ref)
            if e is None:violations.append({'index':index,'reason':'MISSING_EVIDENCE'});continue
            span=hashlib.sha256(e.get('quote','').encode()).hexdigest()
            if span!=e.get('span_sha256') or manifest.get(e.get('source_sha256'),{}).get(e.get('locator'))!=span:source_errors.append({'index':index,'reason':'SOURCE_LOCATION_DIGEST_MISMATCH'})
    calibrated=gold.get('basis')=='SYNTHETIC_NL_HEALTH_ONLY'
    # Real NL receipts are a separate trust decision. Never trust a boolean in
    # arbitrary Gold data as an Owner signoff. No such verifier is configured.
    pending=not calibrated
    assessments=gold.get('assessments',{}) if calibrated else {}
    good=[];seen=set()
    for r in rows:
        if not isinstance(r,dict):continue
        key=r.get('key');assessment=assessments.get(key);mode='INSUFFICIENT';bound=False
        if r.get('kind')=='unknown' and key in gold.get('allowed_boundary_unknowns',[]):continue
        if assessment and assessment.get('item_digest')==atomic_digest(r):
            refs=assessment.get('source_refs',[])
            bound=(bool(refs) or (r.get('kind')=='unknown' and gold.get('unanswerable'))) and set(refs)<=set(r.get('evidence_refs',[])) and all(ref in evidence for ref in refs)
            if assessment.get('mode')=='MULTI_SOURCE_COMPOSITION':bound=bound and len({evidence.get(ref,{}).get('source_sha256') for ref in refs})>=2
            if assessment.get('mode')=='BOUNDED_INFERENCE':bound=bound and CLASSES.get(r.get('evidence_class'),r.get('evidence_class'))=='INFERRED' and bool(r.get('uncertainty'))
            if bound and assessment.get('mode') in MODES:mode=assessment['mode'];seen.add(key)
        ok=bound and mode in {'DIRECT_SUPPORT','MULTI_SOURCE_COMPOSITION','BOUNDED_INFERENCE'}
        good.append(ok)
        findings.append({'item_key':key,'item_digest':atomic_digest(r),'mode':mode,'source_refs':r.get('evidence_refs',[]),'scope':assessment.get('scope') if bound else None,'condition':assessment.get('conditions',[]) if bound else [],'exception':assessment.get('exceptions',[]) if bound else [],'assessment_bound':bound,'basis':assessment.get('basis') if bound else 'NO_INDEPENDENT_ASSESSMENT','mechanical_source_presence_is_not_support':True})
    required=set(gold.get('required_claims',[]));coverage=bool(required) and required<=seen
    factual=bool(good) and all(good)
    if gold.get('unanswerable') and calibrated:
        factual=bool(rows) and all(r.get('kind')=='unknown' and r.get('uncertainty') for r in rows);coverage=required<=seen and bool(required)
    structure=not violations;support=not source_errors
    success=None if pending or source_errors else structure and factual and coverage
    dimensions={d:_dimension(None) for d in ONTOLOGY_DIMENSIONS}
    dimensions.update(STRUCTURE_VALIDITY=_dimension(structure),SOURCE_SUPPORT=_dimension(support),FACTUAL_PRECISION=_dimension(None if pending else factual),COMPETENCY_COVERAGE=_dimension(None if pending else coverage),UNRESOLVED_CONTRADICTION=_dimension(None if pending else factual),EVALUATION_HEALTH=_dimension(True),TASK_SUCCESS=_dimension(success))
    return {'task_success':success,'dimensions':dimensions,'critical_faults':violations+source_errors,'failure_class':'STRUCTURE_GATE_REJECTED_DIAGNOSTIC_ONLY' if violations else 'SOURCE_IDENTITY_ERROR' if source_errors else 'CALIBRATION_PENDING' if pending else None if success else 'INDEPENDENT_ASSESSMENT_OR_COVERAGE_FAILURE','violations':violations,'atomic_findings':findings,'evaluation_scope':'DIAGNOSTIC_ONLY' if pending or violations else 'SYNTHETIC_NL_HEALTH_ONLY','formal_nl_semantic_evaluation':'NOT_EVALUATED','owner_gold_signoff':'PENDING','typed_candidate_created':False,'competency_query':'NOT_REACHED' if violations else 'NOT_PROVEN','oracle_limit':'Real NL reference calibration/verifier not configured; synthetic receipts are not authoritative enterprise Gold.'}
