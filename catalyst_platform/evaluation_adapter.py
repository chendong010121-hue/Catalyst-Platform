"""Method-local Capability Evaluation V3 execution adapter.

No model client, Runtime, registry, semantic authority, or activation lives here.
Entry and grader are host-supplied existing functions. Gold never enters entry.
"""
from __future__ import annotations
import copy
import hashlib
import inspect
import json
import re
import time
from pathlib import Path
from ._vendor.skillopt_sleep.gate import evaluate_gate
from ._vendor.wikiskill.score_rules import finite

OWNER_BLOB='7ab41c22454f255a89a66b93e449e2fd5c4deab8'
PROBES={'KNOWN_GOOD','KNOWN_BAD','NULL','WRONG_QUESTION_CONFIDENT','BROKEN_TASK_OR_INFRA_ERROR'}

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def file_digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def _write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(canonical(value))
def _function_identity(fn):
    path=Path(inspect.getsourcefile(fn)).resolve()
    return {'path':str(path),'sha256':file_digest(path),'function':fn.__qualname__}
def _profile(profile):
    if profile.get('owner_blob')!=OWNER_BLOB:raise ValueError('Unresolved Capability Evaluation V3 owner identity')
    if not profile.get('dimensions') or profile.get('objective') not in profile['dimensions']:raise ValueError('Profile needs explicit dimensions and objective')
    if not set(profile.get('hard_dimensions',[]))<=set(profile['dimensions']):raise ValueError('Undeclared hard dimension')

def _evaluator_packet(observation):
    """Hide arm metadata and artifact paths, never redact result prose by keyword.

    This is logical packet isolation for trusted graders, not a hostile-process
    sandbox. Equal artifact paths receive equal opaque aliases within a packet.
    """
    aliases={}
    hidden={'target_identity','variant','arm','entry_version','target_revision'}
    paths={'path','source_path','artifact_path','uri'}
    def visit(value):
        if isinstance(value,list):return [visit(v) for v in value]
        if not isinstance(value,dict):return copy.deepcopy(value)
        result={}
        for key,item in value.items():
            if key in hidden:continue
            if key in paths and isinstance(item,str):
                result[key]=aliases.setdefault(item,f'artifact://a{len(aliases)+1}')
            else:result[key]=visit(item)
        return result
    return visit(observation)


def _grade(profile,grader,observation,gold):
    if observation.get('execution_error'):
        return {'task_success':None,'dimensions':{},'critical_faults':[], 'failure_class':'INFRASTRUCTURE_ERROR','status':'infrastructure_failed'}
    try:
        # Arm/version mapping is owner-private, never part of evaluator input.
        packet=_evaluator_packet(observation)
        value=copy.deepcopy(grader(packet,copy.deepcopy(gold)))
        if type(value.get('task_success')) not in (bool,type(None)):raise ValueError('Task success must be bool or unknown')
        if set(value.get('dimensions',{}))!=set(profile['dimensions']):raise ValueError('Grader expectations differ from declared Profile')
        for item in value['dimensions'].values():
            if item['status'] not in {'PASS','FAIL','NOT_EVALUATED','UNKNOWN'}:raise ValueError('Unknown measurement status')
            if item.get('value') is not None:finite(item['value'])
        if value['task_success'] is True and (value.get('critical_faults') or any(value['dimensions'][d]['status']!='PASS' for d in profile['hard_dimensions'])):raise ValueError('Critical fault hidden by success')
        value['status']='valid';return value
    except Exception as exc:
        return {'task_success':None,'dimensions':{},'critical_faults':[],'failure_class':'GRADER_ERROR','status':'invalid','grader_error_type':type(exc).__name__}

def check_health(profile,grader,probes):
    _profile(profile)
    checks=[]
    for p in probes:
        result=_grade(profile,grader,p['observation'],p['gold'])
        actual=result['failure_class'] if result['task_success'] is None else result['task_success']
        checks.append({'id':p['id'],'expected':p['expected'],'actual':actual,'passed':actual==p['expected'] and p.get('basis')=='INDEPENDENT'})
    ok={c['id'] for c in checks}==PROBES and len(checks)==len(PROBES) and all(c['passed'] for c in checks)
    return {'status':'PASS' if ok else 'FAIL','profile_sha256':digest(profile),'grader_identity':_function_identity(grader),'probe_sha256':digest(probes),'checks':checks,'claim_scope':'Frozen independent deterministic controls; not model-judge calibration or signed authority'}

def _evidence(observation,workspace):
    kind=observation.get('execution_kind')
    if kind not in {'UNIT_CONTROL','PRODUCT_RUNTIME','PRODUCT_UNDERSTAND','FROZEN_RESULT_REVIEW'}:raise ValueError('Execution provenance absent')
    refs=observation.get('evidence_refs',[])
    if kind!='UNIT_CONTROL' and not refs:raise ValueError('Real entry needs artifacts')
    for row in refs:
        p=Path(row['path'])
        if not p.is_absolute():p=workspace/p
        if p.is_symlink() or not p.resolve().is_relative_to(workspace.resolve()) or not p.is_file() or file_digest(p)!=row['sha256']:raise ValueError('Evidence identity mismatch')


    if kind in {'PRODUCT_RUNTIME','PRODUCT_UNDERSTAND'}:
        from jsonschema import Draft202012Validator
        # Existing v1.6 consumer schema includes Understand candidate/query
        # events; the historical v1.5 schema cannot validate that real path.
        schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/run_event_v1_6.schema.json').read_text(encoding='utf-8'))
        traces=[r for r in refs if r.get('role')=='r4']
        if len(traces)!=1:raise ValueError('One actual R4 trace required')
        p=Path(traces[0]['path']);p=p if p.is_absolute() else workspace/p
        try:
            events=[json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
            for e in events:Draft202012Validator(schema).validate(e)
            if not events or {e['run_id'] for e in events}!={observation['run_id']}:raise ValueError('Run identity differs')
            if [e['sequence'] for e in events]!=list(range(len(events))):raise ValueError('Broken event order')
            if events[0]['event_type']!='request.started' or events[-1]['event_type']!='request.terminal':raise ValueError('Incomplete run trace')
            if kind=='PRODUCT_RUNTIME' and (not any(r.get('role')=='runtime_state' for r in refs) or not any(e['event_type']=='tool.result' and e.get('capability_id')==observation['capability_id'] for e in events)):raise ValueError('Real tool participation absent')
        except Exception as exc:raise ValueError('Invalid R4 execution provenance') from exc

def run_evaluation(profile,cases,entry,grader,destination,*,health,target_identity,mode='BENCHMARK_CASE'):
    """One shared bounded path; no retry, dynamic download or automatic selection."""
    _profile(profile)
    if not cases:raise ValueError('Empty case set cannot qualify')
    if health['status']!='PASS' or health['profile_sha256']!=digest(profile) or health['grader_identity']!=_function_identity(grader):raise ValueError('Measurement health not established for exact grader/Profile')
    ids=[c['id'] for c in cases]
    if len(ids)!=len(set(ids)) or any(not re.fullmatch('[A-Za-z0-9_-]{1,80}',v) for v in ids):raise ValueError('Unsafe or duplicate case identity')
    train={digest(c['public']) for c in cases if c['split']=='train'}
    held={digest(c['public']) for c in cases if c['split'] in {'val','test'}}
    if train&held:raise ValueError('train/held-out overlap')
    if mode not in {'BENCHMARK_CASE','FROZEN_RESULT_REVIEW'}:raise ValueError('Entry mode not declared')
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=False)
    protected={str(Path(__file__).resolve()):file_digest(__file__),**{_function_identity(fn)['path']:_function_identity(fn)['sha256'] for fn in (entry,grader,evaluate_gate,finite)}}
    meta={'profile':copy.deepcopy(profile),'profile_sha256':digest(profile),'cases_sha256':digest(cases),'entry_identity':_function_identity(entry),'grader_identity':_function_identity(grader),'target_identity':target_identity,'entry_mode':mode,'execution_by_evaluation':mode!='FROZEN_RESULT_REVIEW','public_cases':[{k:c[k] for k in ('id','split','critical') if k in c} for c in cases],'protected_files':protected,'health':health}
    _write(destination/'metadata.json',meta);_write(destination/'private/frozen_cases.json',cases)
    rows=[];errors=[];started=time.perf_counter()
    for case in cases:
        workspace=destination/'cases'/case['id'];workspace.mkdir(parents=True)
        try:
            observation=entry(copy.deepcopy(case['public']),workspace)
            canonical(observation)
        except Exception as exc:
            observation={'execution_error':type(exc).__name__,'execution_kind':'UNIT_CONTROL','evidence_refs':[]}
        _write(workspace/'observation.json',observation)
        _write(workspace/'evaluator_packet.json',_evaluator_packet(observation))
        # Detect mutation before grading. Logical separation is not an OS sandbox.
        if any(file_digest(p)!=pin for p,pin in protected.items()):raise ValueError('Frozen grader/runner/entry changed during execution')
        try:
            if mode=='FROZEN_RESULT_REVIEW' and observation.get('execution_kind')!='FROZEN_RESULT_REVIEW':raise ValueError('Frozen review must use a frozen artifact loader')
            _evidence(observation,workspace);grade=_grade(profile,grader,observation,case['gold'])
        except (ValueError,KeyError,TypeError):grade={'task_success':None,'dimensions':{},'critical_faults':[],'failure_class':'EVIDENCE_IDENTITY_ERROR','status':'invalid'}
        _write(workspace/'grading.json',grade)
        # Existing upstream renderer links these frozen review packets. R4
        # remains in the original case artifact; this is not a new event log.
        _write(destination/'traces'/f"{case['id']}.json",{'case_id':case['id'],'observation':observation,'grading':grade,'gold_reference':f"private/frozen_cases.json#{case['id']}",'execution_evidence':'See observation.evidence_refs; report packet does not confer execution authority'})
        row={'id':case['id'],'split':case['split'],'critical':bool(case.get('critical')),'observation_sha256':file_digest(workspace/'observation.json'),**grade}
        rows.append(row)
        if grade['task_success'] is None:errors.append({'id':case['id'],'class':grade['failure_class'],'message':'Not scored; inspect frozen observation and grading'})
    if any(file_digest(p)!=pin for p,pin in protected.items()):raise ValueError('Frozen measurement changed during grading')
    _write(destination/'evaluation.json',{'rows':rows,'elapsed_seconds':time.perf_counter()-started,'profile_sha256':meta['profile_sha256']})
    with (destination/'results.jsonl').open('xb') as f:
        for row in rows:
            grade={d:finite(v['value']) for d,v in row['dimensions'].items() if v.get('value') is not None}
            if row['task_success'] is not None:grade['TASK_SUCCESS']=float(row['task_success'])
            f.write(canonical({'prompt_id':row['id'],'status':'ok' if row['task_success'] is not None else 'error','grade':grade,'model':'NO_MODEL_LOCAL_ENTRY','rep':0})+b'\n')
    with (destination/'errors.jsonl').open('xb') as f:
        for error in errors:f.write(canonical(error)+b'\n')
    _write(destination/'summary.json',{'execution':'NO_PAID_MODELS','applicability':'Method-local offline evidence; no Owner admission'})
    # Seal all observed artifacts, not merely the final score JSON.
    manifest={str(p.relative_to(destination)):file_digest(p) for p in destination.rglob('*') if p.is_file()}
    _write(destination/'manifest.json',manifest)
    return {'path':str(destination),'rows':rows,'metadata':meta}

def _read_verified(path):
    path=Path(path);manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
    for name,pin in manifest.items():
        p=(path/name)
        if p.is_symlink() or not p.resolve().is_relative_to(path.resolve()) or not p.is_file() or file_digest(p)!=pin:raise ValueError('Frozen evidence identity mismatch')
    actual={str(p.relative_to(path)) for p in path.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if actual!=set(manifest):raise ValueError('Incomplete frozen evidence identity inventory')
    meta=json.loads((path/'metadata.json').read_text(encoding='utf-8'))
    if any(file_digest(p)!=pin for p,pin in meta['protected_files'].items()):raise ValueError('Frozen measurement identity changed')
    return meta,json.loads((path/'evaluation.json').read_text(encoding='utf-8'))['rows']

def compare_evaluations(parent,candidate):
    """Advisory method choice. Only the unchanged SkillOpt gate compares scores."""
    pm,pr=_read_verified(parent);cm,cr=_read_verified(candidate)
    for field in ('profile_sha256','cases_sha256','grader_identity'):
        if pm[field]!=cm[field]:raise ValueError('Incomparable frozen measurement identity')
    if [r['id'] for r in pr]!=[r['id'] for r in cr]:raise ValueError('Unpaired cases')
    if any(r['task_success'] is None for r in pr+cr):return {'accept':False,'reason':'MEASUREMENT_OR_INFRA_ERROR','owner_admission':False}
    if any(r.get('critical_faults') for r in cr):return {'accept':False,'reason':'CANDIDATE_CRITICAL_FAULT','owner_admission':False}
    regressions=[p['id'] for p,c in zip(pr,cr) if p['critical'] and p['task_success'] and not c['task_success']]
    if regressions:return {'accept':False,'reason':'CRITICAL_REGRESSION','cases':regressions,'owner_admission':False}
    pairs=[(p,c) for p,c in zip(pr,cr) if p['split'] in {'val','test'}]
    if not pairs:return {'accept':False,'reason':'NO_HELD_OUT_CASES','owner_admission':False}
    ps=sum(p['task_success'] for p,c in pairs)/len(pairs);cs=sum(c['task_success'] for p,c in pairs)/len(pairs)
    gate=evaluate_gate(cm['target_identity'],finite(cs),pm['target_identity'],finite(ps),pm['target_identity'],finite(ps),0,1)
    return {'accept':gate.action!='reject','reason':gate.action,'parent_score':ps,'candidate_score':cs,'owner_admission':False,'gate':'unchanged SkillOpt sleep evaluate_gate; task-success only, dimensions preserved independently'}
