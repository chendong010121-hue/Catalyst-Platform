"""Replaceable domain graders. Formal fixture truth is not a natural-language judge."""
import hashlib
from pathlib import Path

ONTOLOGY_DIMENSIONS=['STRUCTURE_VALIDITY','SOURCE_SUPPORT','FACTUAL_PRECISION','COMPETENCY_COVERAGE','UNRESOLVED_CONTRADICTION','EVALUATION_HEALTH','TASK_SUCCESS','PERFORMANCE']
FILE_DIMENSIONS=['TASK_SUCCESS','SOURCE_SUPPORT','OUTPUT_IDENTITY','EVALUATION_HEALTH','PERFORMANCE']
def _dimension(ok,numerator=None,denominator=None):
    return {'status':'PASS' if ok is True else 'FAIL' if ok is False else 'NOT_EVALUATED','value':None if denominator==0 or ok is None else (numerator/denominator if numerator is not None and denominator else float(ok)),'numerator':numerator,'denominator':denominator}

def ontology_grader(observation,gold):
    """Judge exact independent formal propositions; do not judge arbitrary prose.

    Supported truth scope is declared by basis, not inferred from word overlap.
    Source presence, exact typed facts and competency scope remain separate.
    """
    if gold.get('basis')!='INDEPENDENT_FORMAL_SYNTHETIC':raise ValueError('No independent formal oracle; semantic evaluation NOT_EVALUATED')
    items=observation.get('items',[]);evidence={e['evidence_id']:e for e in observation.get('evidence',[])}
    explicit={'SOURCE_DIRECT','observed_from_source'};unknown={'UNKNOWN','INFERRED','unresolved','inferred'}
    entities=[x for x in items if x.get('kind')=='entity'];entity_keys={x.get('key') for x in entities if x.get('evidence_class') in explicit}
    structure=[];support=[];truth=[];support_modes=[]
    if len(entity_keys)!=len(entities):structure.append('ENTITY_NOT_EXPLICIT_OR_DUPLICATE')
    datatype=set(gold.get('datatype_keys',[]))
    if datatype&{x.get('key') for x in entities}:structure.append('DATATYPE_AS_ENTITY')
    declared_types=gold.get('entity_types',{})
    for entity in entities:
        if entity['key'] in declared_types and entity.get('entity_type')!=declared_types[entity['key']]:structure.append('ENTITY_TYPE_MISMATCH')
    entity_gold=set(gold.get('entity_keys',[]));relation_gold={tuple(v) for v in gold.get('relations',[])}
    relation_seen=set();kinds={};ordinary_unknown=[]
    for row in items:
        kind=row.get('kind');key=row.get('key');kinds.setdefault(kind,set()).add(key)
        if not isinstance(key,str) or not key or not row.get('meaning'):structure.append('MISSING_REQUIRED_FIELD')
        if row.get('evidence_class') in unknown and not str(row.get('uncertainty') or '').strip():structure.append('MISSING_UNCERTAINTY')
        refs=row.get('evidence_refs',[])
        if any(r not in evidence for r in refs):structure.append('UNKNOWN_EVIDENCE_REFERENCE')
        if key in gold.get('fact_evidence',{}):
            expected_quotes=set(gold['fact_evidence'][key])
            if not any(evidence.get(r,{}).get('quote') in expected_quotes for r in refs):support.append('EVIDENCE_DOES_NOT_SUPPORT_DECLARED_FACT')
        for ref in refs:
            e=evidence.get(ref,{})
            if e.get('source_sha256') not in gold.get('source_sha256s',[gold['source_sha256']]) or hashlib.sha256(e.get('quote','').encode()).hexdigest()!=e.get('span_sha256'):support.append('SOURCE_OR_SPAN_IDENTITY_MISMATCH')
        if kind=='relation':
            if any(row.get(k,'').lstrip('@') not in entity_keys for k in ('subject','object')):structure.append('DANGLING_OR_INFERRED_ENTITY_ENDPOINT')
            triple=tuple(row.get(k,'').lstrip('@') if k!='predicate' else row.get(k) for k in ('subject','predicate','object'));relation_seen.add(triple)
            constraints=gold.get('relation_constraints',{})
            if constraints:
                constraint=constraints.get(triple[1])
                if constraint is None:structure.append('UNDECLARED_RELATION_TYPE')
                elif declared_types.get(triple[0]) not in constraint['domain'] or declared_types.get(triple[2]) not in constraint['range']:structure.append('RELATION_DOMAIN_RANGE_MISMATCH')
            ok=triple in relation_gold;truth.append(ok);support_modes.append({'item_key':key,'mode':'DIRECT_SUPPORT' if ok else 'CONTRADICTED','truth_basis':'Closed explicit formal reference; not prose entailment'})
            if not refs:support.append('UNGROUNDED_RELATION')
        elif kind=='entity':
            truth.append(key in entity_gold);support_modes.append({'item_key':key,'mode':'DIRECT_SUPPORT' if key in entity_gold else 'INSUFFICIENT'})
            if not refs:support.append('UNGROUNDED_ENTITY')
        elif kind in {'condition','exception','conflict'}:
            allowed=set(gold.get({'condition':'conditions','exception':'exceptions','conflict':'conflicts'}[kind],[]));ok=key in allowed
            if key in gold.get('context_values',{}):ok=ok and row.get('meaning')==gold['context_values'][key]
            truth.append(ok);support_modes.append({'item_key':key,'mode':'DIRECT_SUPPORT' if ok else 'INSUFFICIENT'})
            if not refs:support.append('UNGROUNDED_CONTEXT')
        elif kind=='claim':
            expected=gold.get('claims',{}).get(key)
            if expected is None:
                truth.append(False);support_modes.append({'item_key':key,'mode':'INSUFFICIENT','note':'No independent semantic oracle for this free proposition'})
            else:
                ok=row.get('meaning')==expected;truth.append(ok);support_modes.append({'item_key':key,'mode':'DIRECT_SUPPORT' if ok else 'CONTRADICTED','truth_basis':'Exact declared literal property, not general language semantics'})
        elif kind=='unknown' and key not in gold.get('allowed_boundary_unknowns',[]):ordinary_unknown.append(key)
        elif kind not in {'unknown','negative_claim'}:structure.append('UNDECLARED_ITEM_KIND')
    required=[];matched=[]
    for key in entity_gold:required.append(('entity',key));matched.append(key in entity_keys)
    for triple in relation_gold:required.append(('relation',triple));matched.append(triple in relation_seen)
    for kind,field in [('condition','conditions'),('exception','exceptions'),('conflict','conflicts'),('unknown','required_unknowns')]:
        for key in gold.get(field,[]):required.append((kind,key));matched.append(key in kinds.get(kind,set()))
    claims=gold.get('claims',{})
    for key in claims:required.append(('claim',key));matched.append(key in kinds.get('claim',set()))
    abstention=(not ordinary_unknown or all(k in gold.get('required_unknowns',[]) for k in ordinary_unknown))
    if gold.get('unanswerable'):
        abstention=abstention and not relation_seen and bool(kinds.get('unknown'))
    if gold.get('requires_query'):
        returned={tuple(r.get(k) for k in ('subject','predicate','object')) for q in observation.get('queries',[]) for r in q.get('result',{}).get('relations',[])}
        for triple in relation_gold:required.append(('query',triple));matched.append(triple in returned)
        required.append(('query_execution',True));matched.append(bool(observation.get('queries')))
    coverage=all(matched) and bool(required or gold.get('unanswerable'))
    factual=all(truth) if truth else bool(gold.get('unanswerable'))
    passed=not structure and not support and factual and coverage and abstention
    dimensions={
        'STRUCTURE_VALIDITY':_dimension(not structure),
        'SOURCE_SUPPORT':_dimension(not support),
        'FACTUAL_PRECISION':_dimension(factual,sum(truth),len(truth)),
        'COMPETENCY_COVERAGE':_dimension(coverage,sum(matched),len(required)),
        'UNRESOLVED_CONTRADICTION':_dimension(abstention),
        'EVALUATION_HEALTH':_dimension(True),
        'TASK_SUCCESS':_dimension(passed),
        'PERFORMANCE':_dimension(None)}
    failure=None if passed else 'STRUCTURE_FAILURE' if structure else 'SOURCE_SUPPORT_FAILURE' if support else 'SEMANTIC_CONTRADICTION' if not factual else 'COVERAGE_FAILURE' if not coverage else 'ABSTENTION_FAILURE'
    return {'task_success':passed,'dimensions':dimensions,'critical_faults':structure+support,'failure_class':failure,'support_modes':support_modes,'measurement_scope':'Explicit independent synthetic formal facts only; enterprise natural-language semantics NOT_EVALUATED','competency_execution':'CANDIDATE_PREVIEW_QUERY_EXECUTED' if observation.get('queries') else 'COMPETENCY_EXECUTION_NOT_ESTABLISHED','formal_owner_admission':False,'unknown_count':len(ordinary_unknown)}

def file_title_grader(observation,gold):
    """End-state exact title/source/line and negative refusal, not transcript style."""
    if gold.get('basis')!='INDEPENDENT_FILE_CONTRACT':raise ValueError('No independent expected file end-state')
    output=observation.get('output') or {};source=output.get('source') or {}
    actual_status=observation.get('status');source_ok=observation.get('source_sha256')==gold.get('source_sha256')
    if gold.get('expected_refusal'):
        message=str((observation.get('error') or {}).get('message',''))
        task=actual_status=='failure' and not output and gold['expected_refusal'] in message
        identity=source_ok
    else:
        task=actual_status=='success' and output.get('title')==gold['title']
        identity=source_ok and source.get('sha256')==gold.get('source_sha256') and source.get('line')==gold.get('line')
        refs=[r for r in observation.get('evidence_refs',[]) if r.get('role')=='source']
        if refs:identity=identity and source.get('path') in {r['path'] for r in refs}
    success=task and identity
    return {'task_success':success,'dimensions':{'TASK_SUCCESS':_dimension(success),'SOURCE_SUPPORT':_dimension(source_ok),'OUTPUT_IDENTITY':_dimension(identity),'EVALUATION_HEALTH':_dimension(True),'PERFORMANCE':_dimension(None)},'critical_faults':[],'failure_class':None if success else 'CAPABILITY_FAILURE','measurement_scope':'Exact file title/source/line/refusal end-state; no Ontology rubric'}
