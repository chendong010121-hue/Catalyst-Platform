"""Prepare reviewable evaluation requests; no model, executor or grading engine."""
from __future__ import annotations
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .maintenance import product_identity, digest

SKILL_ROOT = Path(__file__).resolve().parent.parent / 'docs' / 'skills' / 'catalyst-eval-workflow'

def _workflow_snapshot(components=None):
    """Consume the active, hash-validated method or the shipped default."""
    if components is not None:
        row = next((r for r in components.list_components()
                    if r['component_id'] == 'development-workflow'), None)
        if row and row.get('active_version'):
            with components.acquire_method('development-workflow') as method:
                return {'files': dict(method['files']), 'version': method['version'],
                        'package_sha256': method['package_sha256'], 'source': 'ACTIVE_METHOD'}
    return {'files': {p.relative_to(SKILL_ROOT).as_posix(): p.read_bytes().decode('utf8')
                      for p in SKILL_ROOT.rglob('*') if p.is_file()},
            'version': None, 'package_sha256': None, 'source': 'SHIPPED_DEFAULT'}


def workflow_guide(mode, components=None):
    names={'build-eval':'build-eval.md','eval-audit':'eval-audit.md','hillclimb':'hillclimb.md'}
    if mode not in names:raise ValueError('workflow_mode_invalid')
    import hashlib
    snapshot = _workflow_snapshot(components)
    raw=snapshot['files']['references/'+names[mode]].encode('utf8')
    return {'mode':mode,'text':raw.decode('utf-8'),'sha256':hashlib.sha256(raw).hexdigest(),
            'method_source':snapshot['source'],'method_version':snapshot['version'],
            'package_sha256':snapshot['package_sha256'],'execution_authorized':False}

def workflow_intent(message):
    """Conservative explicit-intent routing, not an LLM intent-quality claim."""
    text=message.strip().lower()
    explicit_prepare=bool(re.search(r'(准备|制定|设计|建立|生成).{0,40}(测试|评测|回归|benchmark|hill.?climb|迭代)',text))
    if re.search(r'(不要|不用|无需|不必)\s*(准备|制定|设计|建立|生成)',text):return None
    if not explicit_prepare and re.search(r'(不(?:用|要|做|需).*?(测试|迭代)|解释|什么是|介绍|含义|定义)',text):return None
    if not re.search(r'(帮|请|想|准备|开始|执行|做|建立|审查|检查|run |build |audit |hillclimb|hill.climb)',text):return None
    if re.search(r'(hill.?climb|爬坡|迭代(?!器))',text):return 'hillclimb'
    if re.search(r'(审查|审核|检查|audit)',text) and re.search(r'(测试|评价|评测|eval)',text):return 'eval-audit'
    if re.search(r'(测试|评测|回归|benchmark|build.eval)',text):return 'build-eval'
    return None

def prepare_workflow(app, message, mode):
    if mode not in {'build-eval','eval-audit','hillclimb'}:raise ValueError('workflow_mode_invalid')
    import hashlib
    snapshot = _workflow_snapshot(app.components)
    if 'SKILL.md' not in snapshot['files']:raise ValueError('evaluation_workflow_skill_unavailable')
    files={name:hashlib.sha256(text.encode('utf8')).hexdigest() for name,text in snapshot['files'].items()}
    row={'workflow_id':'workflow_'+uuid.uuid4().hex,'mode':mode,'request':message,
         'status':'PREPARED_NOT_EXECUTED','created_at':datetime.now(timezone.utc).isoformat(),
         'parent_identity':product_identity(),'skill':{'name':'development-workflow' if snapshot['source']=='ACTIVE_METHOD' else 'catalyst-eval-workflow','files':files,'sha256':digest(files),
              'source':snapshot['source'],'version':snapshot['version'],'package_sha256':snapshot['package_sha256']},
         'execution_authorized':False,'next_gate':'OWNER_REVIEW_INPUTS_AND_GRADING',
         'candidate_activated':False,'paid_requests':0,'evaluation_scope':'NOT_CREATED',
         'required_gates':['INPUTS_AND_DATA_SCOPE','GRADING_AND_INDEPENDENT_TRUTH','ENTRY_PARITY_AND_HEALTH','NEW_MODEL_COST_AUTHORIZATION','ISOLATION_AND_ROLLBACK'],
         'phase':'WORKFLOW_PREPARATION','subject_workspace':'NOT_CREATED',
         'rollback':'No product or method mutation; recorded Parent remains the rollback identity.'}
    row['record_sha256']=digest(row)
    app._atomic_json(app.state_root/'evaluation-workflows'/row['workflow_id']/'request.json',row)
    return row

def list_workflows(app):
    items=[]
    for p in sorted((app.state_root/'evaluation-workflows').glob('workflow_*/request.json')):
        row=json.loads(p.read_text(encoding='utf-8'));sha=row.pop('record_sha256')
        if digest(row)!=sha:raise ValueError('workflow_record_integrity_changed')
        items.append({**row,'record_sha256':sha})
    return list(reversed(items))


def offline_profiles():
    """Explicit built-in synthetic checks, not arbitrary user-defined executors."""
    return [
        {'id': 'file_title', 'label': '文件标题能力', 'scope': 'SYNTHETIC_FILE_TITLE'},
        {'id': 'ontology', 'label': '本体候选与查询', 'scope': 'SYNTHETIC_EXPLICIT_LABELS_ONLY'},
        {'id': 'file_title_comparison', 'label': '离线版本比较示例', 'scope': 'SYNTHETIC_FAULT_INJECTED_COMPARISON_ONLY'},
    ]


def run_offline_check(app, profile_id):
    """Execute an existing product entry through the existing evaluation adapter.

    Built-in cases are synthetic; no credential, network, user source or formal
    admission is accessed. The adapter owns evidence, health checks and scoring.
    """
    if profile_id not in {'file_title', 'ontology', 'file_title_comparison'}:
        raise ValueError('offline_profile_invalid')
    import copy
    import hashlib
    from .evaluation_adapter import run_evaluation, compare_evaluations
    from .evaluation_demo import profile, health, file_cases, formal_control
    from .evaluation_entries import file_title_entry, file_title_parent_entry, ontology_entry
    from .evaluation_profiles import FILE_DIMENSIONS, ONTOLOGY_DIMENSIONS, file_title_grader, ontology_grader

    if profile_id in {'file_title', 'file_title_comparison'}:
        spec = profile('existing-file-title', FILE_DIMENSIONS)
        cases = file_cases()
        gold = cases[0]['gold']
        good = {'status': 'success', 'source_sha256': gold['source_sha256'],
                'output': {'title': gold['title'], 'source': {'sha256': gold['source_sha256'], 'line': 1}}}
        grader, entry = file_title_grader, file_title_entry
    else:
        spec = profile('ontology-formal-subset', ONTOLOGY_DIMENSIONS)
        good, gold = formal_control()
        text = 'Entity: Team | Team\nEntity: Task | Task\nRelation: Team -> owns -> Task\n'
        cases = []
        for backend in ('json', 'sqlite'):
            expected = copy.deepcopy(gold)
            expected.update(source_sha256=hashlib.sha256(text.encode()).hexdigest(), requires_query=True)
            cases.append({'id': 'candidate_' + backend, 'split': 'test', 'critical': True,
                          'public': {'source_text': text, 'entity_queries': ['Team'], 'backend': backend},
                          'gold': expected})
        grader, entry = ontology_grader, ontology_entry
    measured_health = health(spec, grader, good, gold)
    if measured_health['status'] != 'PASS':
        raise ValueError('offline_evaluator_health_failed')
    check_id = 'check_' + uuid.uuid4().hex
    # Keep nested Runtime snapshots within Windows' practical path limits;
    # exclusive directory creation rejects the unlikely truncated-ID collision.
    parent = app.workspace / 'd'
    if parent.exists():
        import stat
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
                or not parent.resolve().is_relative_to(app.workspace.resolve())):
            raise ValueError('offline_workspace_path_invalid')
    destination = parent / check_id.removeprefix('check_')[:16]
    comparison = None
    if profile_id == 'file_title_comparison':
        destination.mkdir(parents=True, exist_ok=False)
        run_evaluation(spec, cases, file_title_parent_entry, grader, destination / 'p',
                       health=measured_health, target_identity='fault-injected-parent')
        result = run_evaluation(spec, cases, entry, grader, destination / 'c',
                                health=measured_health, target_identity='existing-file-title')
        comparison = compare_evaluations(destination / 'p', destination / 'c')
    else:
        result = run_evaluation(spec, cases, entry, grader, destination, health=measured_health,
                                target_identity='builtin-' + profile_id + ':' + check_id)
    measured = result['rows']
    verdict = ('INVALID' if any(row['task_success'] is None for row in measured)
               else 'PASS' if all(row['task_success'] for row in measured) else 'FAIL')
    return {'check_id': check_id, 'profile': profile_id, 'status': 'COMPLETED', 'verdict': verdict,
            'artifact_root': str(destination), 'cases': measured, 'model_requests': 0,
            'business_semantics': 'NOT_EVALUATED', 'owner_admission': False,
            'scope': 'SYNTHETIC_FAULT_INJECTED_COMPARISON_ONLY' if comparison is not None else 'SYNTHETIC_DETERMINISTIC_ONLY',
            'comparison': comparison, 'reference_promoted': False}
