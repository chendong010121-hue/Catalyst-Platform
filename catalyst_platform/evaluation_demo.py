"""Bounded offline acceptance campaign; one adapter, two existing capabilities.

All inputs are independent synthetic public fixtures. No model or API client.
Run: python -m catalyst_platform.evaluation_demo --output <new-directory>
"""
import argparse,copy,hashlib,json,subprocess
from pathlib import Path
from .evaluation_adapter import OWNER_BLOB,canonical,check_health,run_evaluation,compare_evaluations,file_digest
from .evaluation_entries import file_title_entry,file_title_parent_entry,file_title_critical_entry,ontology_entry
from .evaluation_profiles import FILE_DIMENSIONS,ONTOLOGY_DIMENSIONS,file_title_grader,ontology_grader


def profile(name,dimensions):
    return {'id':name,'version':'1','owner':'capability-evaluation-v3','owner_blob':OWNER_BLOB,'dimensions':dimensions,'objective':'TASK_SUCCESS','hard_dimensions':[d for d in dimensions if d not in {'PERFORMANCE','EVALUATION_HEALTH'}],'acceptance':'Advisory method comparison; never Owner admission'}


def formal_control():
    quote='Relation: Team -> owns -> Task'
    evidence={'evidence_id':'e1','quote':quote,'source_sha256':'independent-formal-source','span_sha256':hashlib.sha256(quote.encode()).hexdigest(),'locator':'line:3'}
    rows=[dict(kind='entity',key=k,meaning=k,evidence_class='SOURCE_DIRECT',evidence_refs=['e1']) for k in ['Team','Task']]
    rows.append(dict(kind='relation',key='r',meaning=quote,subject='Team',predicate='owns',object='Task',evidence_class='SOURCE_DIRECT',evidence_refs=['e1']))
    gold={'basis':'INDEPENDENT_FORMAL_SYNTHETIC','source_sha256':evidence['source_sha256'],'entity_keys':['Team','Task'],'relations':[['Team','owns','Task']],'allowed_boundary_unknowns':['approval','binding']}
    return {'execution_kind':'UNIT_CONTROL','items':rows,'evidence':[evidence]},gold


def health(profile,grader,good,gold):
    bad=copy.deepcopy(good);wrong=copy.deepcopy(good)
    if grader is ontology_grader:
        bad['items'][-1]['object']='missing';wrong['items'][-1].update(subject='Task',object='Team')
    else:
        bad['output']['title']='wrong title';wrong['output']['title']='answer to a different task'
    probes=[{'id':name,'basis':'INDEPENDENT','observation':obs,'gold':gold,'expected':expected} for name,obs,expected in [('KNOWN_GOOD',good,True),('KNOWN_BAD',bad,False),('NULL',{},False),('WRONG_QUESTION_CONFIDENT',wrong,False),('BROKEN_TASK_OR_INFRA_ERROR',{'execution_error':'offline infrastructure unavailable'},'INFRASTRUCTURE_ERROR')]]
    return check_health(profile,grader,probes)


def frozen_entry(public,workspace):
    """Only loads a frozen synthetic negative control; never invokes a Subject."""
    path=Path(public['artifact']);assert file_digest(path)==public['sha256']
    data=path.read_bytes();local=workspace/'frozen.json';local.write_bytes(data)
    result=json.loads(data);result.update(execution_kind='FROZEN_RESULT_REVIEW',evidence_refs=[{'path':str(local),'sha256':file_digest(local),'role':'frozen_observation'}])
    return result


def file_cases():
    result=[]
    for i in range(3):
        title=f'Independent heading {i+1}';content=f'# {title} ###\nBody\n'
        result.append({'id':f'trailing_{i+1}','split':'test','critical':False,'public':{'filename':'input.md','content':content},'gold':{'basis':'INDEPENDENT_FILE_CONTRACT','source_sha256':hashlib.sha256(content.encode()).hexdigest(),'title':title,'line':1}})
    content='```markdown\n# Fenced example\n```\n# Actual heading\n'
    result.append({'id':'fenced_critical','split':'test','critical':True,'public':{'filename':'input.md','content':content},'gold':{'basis':'INDEPENDENT_FILE_CONTRACT','source_sha256':hashlib.sha256(content.encode()).hexdigest(),'title':'Actual heading','line':4}})
    return result


def main(destination):
    root=Path(destination).resolve();root.mkdir(parents=True,exist_ok=False)
    def write(name,value):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))
    fp=profile('existing-file-title',FILE_DIMENSIONS);op=profile('ontology-formal-subset',ONTOLOGY_DIMENSIONS)
    cases=file_cases();g=cases[0]['gold'];good={'status':'success','source_sha256':g['source_sha256'],'output':{'title':g['title'],'source':{'sha256':g['source_sha256'],'line':1}}}
    fh=health(fp,file_title_grader,good,g);control,og=formal_control();oh=health(op,ontology_grader,control,og)
    assert fh['status']==oh['status']=='PASS'
    write('health.json',{'file_title':fh,'ontology':oh});write('SECOND_SKILL_EVAL_PROFILE.json',fp);write('ONTOLOGY_EVAL_PROFILE.json',op)
    write('public/SECOND_SKILL_CASES.json',[{k:v for k,v in c.items() if k!='gold'} for c in cases]);write('private/SECOND_SKILL_GOLD.json',[{'id':c['id'],'gold':c['gold']} for c in cases])
    flow=root/'file_title';flow.mkdir()
    for name,entry in [('baseline',file_title_parent_entry),('v1',file_title_entry),('v2',file_title_critical_entry)]:
        run_evaluation(fp,cases,entry,file_title_grader,flow/name,health=fh,target_identity=name)
    gates={'better':compare_evaluations(flow/'baseline',flow/'v1'),'worse':compare_evaluations(flow/'v1',flow/'baseline'),'higher_mean_critical_regression':compare_evaluations(flow/'baseline',flow/'v2')}
    assert gates['better']['accept'] and not gates['worse']['accept'] and gates['higher_mean_critical_regression']['reason']=='CRITICAL_REGRESSION'
    write('SECOND_SKILL_RESULTS.json',{'gates':gates,'claim':'GATE_BEHAVIOR_PROVEN; isolated fault-injected method variants, not model Skill improvement','runtime_path':'existing HarnessSession.invoke -> Runtime -> inherited FileTitleCapability.invoke'})
    text='Entity: Team | Team\nEntity: Task | Task\nRelation: Team -> owns -> Task\n'
    ont=[]
    for backend in ['json','sqlite']:
        gold=copy.deepcopy(og);gold.update(source_sha256=hashlib.sha256(text.encode()).hexdigest(),requires_query=True)
        ont.append({'id':'candidate_'+backend,'split':'test','critical':True,'public':{'source_text':text,'entity_queries':['Team'],'backend':backend},'gold':gold})
    write('public/ONTOLOGY_EVAL_CASES.json',[{k:v for k,v in c.items() if k!='gold'} for c in ont]);write('private/ONTOLOGY_GOLD.json',[{'id':c['id'],'gold':c['gold']} for c in ont])
    actual=run_evaluation(op,ont,ontology_entry,ontology_grader,root/'ontology'/'baseline',health=oh,target_identity='existing-deterministic-Understand')
    assert all(r['task_success'] for r in actual['rows']),actual['rows']
    negatives=[]
    def add(name,change,expected=False):
        observation=copy.deepcopy(control);gold=copy.deepcopy(og);change(observation,gold)
        artifact=root/'frozen_controls'/f'{name}.json';artifact.parent.mkdir(exist_ok=True);artifact.write_bytes(canonical(observation))
        negatives.append({'id':name,'split':'test','critical':True,'public':{'artifact':str(artifact),'sha256':file_digest(artifact)},'gold':gold,'expected':expected})
    add('supported',lambda o,g:None,True)
    add('missing_object',lambda o,g:o['items'].pop(1))
    add('datatype_endpoint',lambda o,g:g.update(datatype_keys=['Task']))
    add('reversed_relation',lambda o,g:o['items'][-1].update(subject='Task',object='Team'))
    add('missing_evidence',lambda o,g:o['items'][-1].update(evidence_refs=['absent']))
    add('opposite_existing_evidence',lambda o,g:g.update(relations=[['Task','owns','Team']]))
    add('unrelated_existing_evidence',lambda o,g:g.update(fact_evidence={'r':['Different independent supporting line']}))
    add('cross_source_conflict_dropped',lambda o,g:g.update(conflicts=['two_source_conflict']))
    add('authority_inferred',lambda o,g:o['items'].append(dict(kind='claim',key='owner_approved',meaning='approved',evidence_class='INFERRED',uncertainty='not established',evidence_refs=['e1'])))
    add('exception_dropped',lambda o,g:g.update(exceptions=['scope_limit']))
    add('empty_graph',lambda o,g:o.update(items=[]))
    add('tiny_output',lambda o,g:o.update(items=o['items'][:1]))
    def unknown(o,g):o.update(items=[dict(kind='unknown',key='status',meaning='not provided',evidence_class='UNKNOWN',uncertainty='no supporting source',evidence_refs=[])])
    add('all_unknown',unknown)
    def valid_unknown(o,g):
        unknown(o,g);g.update(entity_keys=[],relations=[],required_unknowns=['status'],unanswerable=True)
    add('legitimate_unknown',valid_unknown,True)
    def invalid_unknown(o,g):valid_unknown(o,g);o['items'][0].pop('uncertainty')
    add('invalid_unknown',invalid_unknown)
    add('infra_error',lambda o,g:o.update(execution_error='unavailable'),None)
    add('grader_error',lambda o,g:g.pop('basis'),None)
    frozen=run_evaluation(op,negatives,frozen_entry,ontology_grader,root/'ontology_controls',health=oh,target_identity='independent-frozen-negative-controls',mode='FROZEN_RESULT_REVIEW')
    for expected,row in zip(negatives,frozen['rows']):assert row['task_success'] is expected['expected'],(expected['id'],row)
    write('ONTOLOGY_EVAL_RESULTS.json',{'real_rows':actual['rows'],'frozen_controls':frozen['rows'],'scope':'Independent explicit-label formal subset. Candidate-only preview queries, no formal active ontology. General natural-language truth NOT_EVALUATED.'})
    write('file_title/_state.json',{'metrics':[{'id':d,'kind':'binary'} for d in FILE_DIMENSIONS if d!='PERFORMANCE'],'test_ids':[c['id'] for c in cases],'best':{'round':1}})
    # Renderer consumes the exact same result carrier; never executes Subjects.
    renderer=Path(__file__).resolve().parents[1]/'platform-harness/evaluation/vendor/anthropic/build-report-lite.mjs'
    write('ontology/_state.json',{'metrics':[{'id':d,'kind':'binary'} for d in ONTOLOGY_DIMENSIONS if d!='PERFORMANCE'],'test_ids':[c['id'] for c in ont],'best':{'round':0}})
    receipts=[]
    for target in [flow,root/'ontology']:
        proc=subprocess.run(['node',str(renderer),str(target)],capture_output=True,text=True,check=True)
        receipts.append({'flow':target.name,'stdout':proc.stdout,'stderr':proc.stderr,'report_sha256':file_digest(target/'report.html')})
    write('renderer_receipt.json',{'renderer_sha256':file_digest(renderer),'receipts':receipts})
    write('RUN_MANIFEST.json',{str(p.relative_to(root)):file_digest(p) for p in root.rglob('*') if p.is_file()})
    print(json.dumps({'output':str(root),'real_file_runs':12,'real_ontology_runs':2,'frozen_controls':len(negatives),'gates':gates,'paid_api_calls':0},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);main(parser.parse_args().output)
