"""Bounded local maintenance adapter over existing lifecycle/Runtime/R4.

Two fixed source-controlled Tool/method pairs only. No user paths, commands, model
access, enterprise authority, generic installer or autonomous promotion.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from .components import discover_local_component
from .observability import RunRecorder
from .trace_log import JsonlTraceStore
from .workspace_ledger import load_host_ledger

PRODUCT=Path(__file__).resolve().parents[1]
PACKAGES=PRODUCT/'examples/local_components/local_text_stats'
PINS={'1.0.0':'197ece19fd150adf55f8efce9a74bb583a45fecb231b320d5cdf1505c738a8b9',
      '2.0.0':'6a29c71e23f530e3df0be91a61fd90d60e479477fb54d7040725d21b38f93eb0'}
CID='local_text_stats'
METHOD_ID='project-understand'
METHOD_PACKAGES=PRODUCT/'examples/project_methods'/METHOD_ID
METHOD_PINS={'0.1.0':'3ca790e2e9b59c61566ee6f466f60f2532a229bac078daa9221ae906411f66d7',
             '0.1.1':'f9cc15c5a4bc7c7a3dcfec47e306ed4517bae5fe082a86acb4afe0c10a226b91'}
IMMUTABLE=('review_id','product','parent','candidate','evaluation','diff','operation','basis_id')


def target_spec(target):
    if target==CID:return PACKAGES,PINS,'1.0.0','2.0.0','tests/test_r5_extensible_components.py'
    if target==METHOD_ID:return METHOD_PACKAGES,METHOD_PINS,'0.1.0','0.1.1','tests/project_understand/test_method_lifecycle.py'
    raise ValueError('maintenance_target_not_allowed')


def immutable_fields(row):
    # Existing tool receipts retain their original digest contract.
    return {k:row.get(k) for k in IMMUTABLE+(('target',) if 'target' in row else ())}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def product_identity():
    def git(*args):return subprocess.check_output(['git','-C',str(PRODUCT),*args],text=True,encoding='utf-8',timeout=15).strip()
    return {'commit':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),
            'dirty':bool(git('status','--porcelain=v1'))}


class LocalMaintenance:
    """Exact receipts and restart-only activation of two fixed local targets."""
    def __init__(self,app,*,run_regression=True):
        self.app=app
        self.root=app.state_root/'maintenance'
        self.run_regression=run_regression  # Trusted test assembly only, never HTTP configurable.
        self._host=None
        # Existing lifecycle temp filenames need Windows path headroom. Keep
        # validation state separate, on the workspace volume, with a short
        # workspace-derived identity; never reuse an experiment/run directory.
        self.validation_root=Path(app.workspace.anchor)/'CatalystValidation'/digest(str(app.workspace))[:16]

    @property
    def host(self):
        if self._host is None:self._host=load_host_ledger()
        return self._host

    def _lock(self):return self.host.Lock(self.root/'maintenance.lock')

    def _path(self,rid):
        if not isinstance(rid,str) or not re.fullmatch(r'review_[a-f0-9]{32}',rid):raise ValueError('invalid_maintenance_review')
        return self.root/'reviews'/(rid+'.json')

    def _write(self,row):self.app._atomic_json(self._path(row['review_id']),row)

    def _read(self,rid):
        path=self._path(rid)
        if not path.is_file() or path.is_symlink() or path.stat().st_size>1_000_000:raise ValueError('maintenance_review_unavailable')
        row=json.loads(path.read_text(encoding='utf-8'))
        if row.get('approval_digest')!=digest(immutable_fields(row)):raise ValueError('maintenance_receipt_changed')
        target_spec(row.get('target',CID))
        return row

    def _seal(self,row):
        row['approval_digest']=digest(immutable_fields(row))
        self._write(row)
        return row

    def items(self):
        if not (self.root/'reviews').exists():return []
        return sorted([self._read(p.stem) for p in (self.root/'reviews').glob('review_*.json')],key=lambda r:r['review_id'],reverse=True)

    def active_identity(self,target=CID):
        target_spec(target)
        for component in self.app.components.list_components():
            if component['component_id']!=target:continue
            for version in component['versions']:
                if version['active']:
                    return {'component_id':target,'version':version['version'],'package_sha256':version['package_sha256']}
        return None

    def _candidate(self,version,path=None,target=CID):
        packages,pins,*_=target_spec(target)
        package=discover_local_component(path or packages/version)
        if version not in pins or package.component_id!=target or package.version!=version or package.package_sha256!=pins[version]:
            raise ValueError('maintenance_package_changed')
        return package

    def _event(self,kind,**fields):
        rec=RunRecorder(JsonlTraceStore(self.app.workspace),run_id='run_'+uuid.uuid4().hex,
                        request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex)
        rec.start(request_kind='maintenance.'+kind,component='LocalMaintenance')
        span=rec.start_span('maintenance.'+kind,kind='CHAIN',attributes=fields)
        status='failure' if fields.get('status') in ('FAILED','FAILED_ROLLED_BACK','RECOVERY_REQUIRED','VALIDATION_FAILED') else 'success'
        rec.end_span(span,status=status,attributes=fields)
        rec.finish(status,external_calls=0)
        return rec.run_id

    def _probe(self,app,version,*,text='Hello 世界\nSecond line\n',expected=4):
        source=app.workspace/'inputs'/('maintenance-probe-'+uuid.uuid4().hex+'.txt')
        source.parent.mkdir(parents=True,exist_ok=True)
        self.host.put(source,text.encode('utf-8'))
        session=app.new_session(domain={'id':'local'},enterprise={'id':'maintenance-test'})
        rec=RunRecorder(JsonlTraceStore(app.workspace),run_id='run_'+uuid.uuid4().hex,
                        request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex)
        rec.start(request_kind='maintenance.tool_probe',input_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
        run=session.invoke(CID,version,{'path':str(source.resolve())},recorder=rec)
        rec.finish(run.result.status,external_calls=0)
        value=run.result.output
        passed=(run.result.status=='success' and value.get('word_count')==expected and
                value.get('line_count')==len(text.splitlines()) and value.get('character_count')==len(text) and
                value.get('source_sha256')==hashlib.sha256(source.read_bytes()).hexdigest())
        return {'passed':passed,'output':value,'run_id':rec.run_id,'status':run.result.status}

    def _method_probe(self,app,version):
        """Read the installed immutable method lease; never run package code/LLM."""
        rec=RunRecorder(JsonlTraceStore(app.workspace),run_id='run_'+uuid.uuid4().hex,
                        request_id='req_'+uuid.uuid4().hex,invocation_id='inv_'+uuid.uuid4().hex)
        rec.start(request_kind='maintenance.method_probe',component='LocalMaintenance')
        span=rec.start_span('maintenance.method_snapshot',kind='CHAIN')
        with app.components.acquire_method(METHOD_ID) as snapshot:
            expected=self._candidate(version,target=METHOD_ID)
            passed=(snapshot['component_id']==METHOD_ID and snapshot['version']==version
                and snapshot['package_sha256']==expected.package_sha256
                and dict(snapshot['files'])=={k:v.decode('utf-8') for k,v in expected.files.items()})
            value={'component_id':snapshot['component_id'],'version':snapshot['version'],
                   'package_sha256':snapshot['package_sha256'],'files':sorted(snapshot['files'])}
        rec.end_span(span,status='success' if passed else 'failure',attributes=value)
        rec.finish('success' if passed else 'failure',external_calls=0)
        return {'passed':passed,'output':value,'run_id':rec.run_id,
                'status':'METHOD_SNAPSHOT_MATCH' if passed else 'METHOD_SNAPSHOT_MISMATCH',
                'fixture_only':True,'semantic_quality':'NOT_EVALUATED'}

    def _isolated(self,root,version,package=None,target=CID):
        from .workbench import CatalystWorkbench
        app=CatalystWorkbench(root,[root/'inputs'])
        candidate=package or self._candidate(version,target=target)
        app.components.admit(candidate.package_dir,candidate.package_sha256)
        app.components.activate(target,version)
        return app

    def probe_existing_v2(self):
        package=discover_local_component(PACKAGES/'2.0.0')
        app=self._isolated(self.validation_root/('old-'+uuid.uuid4().hex[:10]),'2.0.0',package)
        try:return self._probe(app,'2.0.0')
        finally:app.components.close_loaded();app.plugins.close()

    def _regression(self,root,target=CID):
        if not self.run_regression:return {'status':'TEST_ASSEMBLY_ONLY','passed':True}
        root.mkdir(parents=True,exist_ok=True)
        # Fixed in-repo regression, no user shell or command selection. Drop known
        # credential variables by name without inspecting their values.
        env=os.environ.copy()
        for name in ('CATALYST_LLM_API_KEY','DEEPSEEK_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY'):
            env.pop(name,None)
        env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        fence="import socket,sys,pytest; socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('MAINTENANCE_ZERO_NETWORK')); sys.exit(pytest.main(sys.argv[1:]))"
        test_path=target_spec(target)[4]
        result=subprocess.run([sys.executable,'-c',fence,'-q',test_path,'-p','no:cacheprovider','--basetemp='+str(root/'tmp')],
                              cwd=PRODUCT,env=env,capture_output=True,timeout=180)
        log=result.stdout+result.stderr
        self.host.put(root/'pytest.log',log)
        return {'status':'PASSED' if result.returncode==0 else 'FAILED','passed':result.returncode==0,
                'command':['python','-m','pytest','-q',test_path,'-p','no:cacheprovider'],
                'definition_sha256':hashlib.sha256((PRODUCT/test_path).read_bytes()).hexdigest(),
                'log_sha256':hashlib.sha256(log).hexdigest(),'exit_code':result.returncode}

    def prepare(self,target=CID):
        _,pins,parent_version,candidate_version,_=target_spec(target)
        with self._lock():
            if any(r['status'] in ('PENDING_RESTART','APPLYING','ROLLBACK_PENDING') for r in self.items()):
                raise ValueError('maintenance_restart_pending')
            parent=self.active_identity(target)
            if parent and (parent['version'] not in pins or parent['package_sha256']!=pins[parent['version']]):
                raise ValueError('maintenance_parent_not_supported')
            if parent and parent['version']==candidate_version:raise ValueError('maintenance_already_current')
            current=self._candidate(parent_version,target=target);candidate=self._candidate(candidate_version,target=target)
            rid='review_'+uuid.uuid4().hex
            stage=self.root/'packages'/rid;stage.mkdir(parents=True)
            self.host.put(stage/'manifest.json',candidate.manifest_bytes)
            if target==METHOD_ID:
                for name,data in candidate.files.items():self.host.put(stage/name,data)
            else:self.host.put(stage/'tool.py',candidate.source_bytes)
            root=self.validation_root/rid[-12:]
            app=self._isolated(root/'candidate',candidate_version,self._candidate(candidate_version,stage,target),target)
            try:
                if target==METHOD_ID:checks=[self._method_probe(app,candidate_version)]
                else:
                    checks=[self._probe(app,'2.0.0'),self._probe(app,'2.0.0',text='甲部门\nAlpha beta\n',expected=3)]
                    # Real Runtime/Policy rejection for a file outside the allowed root.
                    denied=app.new_session(domain={'id':'local'},enterprise={'id':'maintenance-test'}).invoke(CID,'2.0.0',{'path':str(PRODUCT/'README.md')})
                    checks.append({'passed':denied.result.status!='success','status':'OUT_OF_SCOPE_REJECTED','run_id':None})
            finally:app.components.close_loaded();app.plugins.close()
            regression=self._regression(root/'regression',target) if target==METHOD_ID else self._regression(root/'regression')
            evaluation={'passed':all(c['passed'] for c in checks) and regression['passed'],
                        'checks':checks,'runtime_run_ids':[c['run_id'] for c in checks],
                        'regression':regression,'api_calls':0,'semantic_quality':'NOT_EVALUATED'}
            evaluation['artifact_root']=str(root)
            if target==METHOD_ID:evaluation['fixture_only']=True
            artifacts=[p for p in root.rglob('*') if p.is_file() and (p.suffix in ('.json','.jsonl','.log'))]
            evaluation['artifacts']=[{'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(artifacts)]
            before=current.files if target==METHOD_ID else {'tool.py':current.source_bytes}
            after=candidate.files if target==METHOD_ID else {'tool.py':candidate.source_bytes}
            diff=''.join(''.join(difflib.unified_diff(before.get(name,b'').decode().splitlines(True),after.get(name,b'').decode().splitlines(True),
                 fromfile=f'{target}/{parent_version}/{name}',tofile=f'{target}/{candidate_version}/{name}')) for name in sorted(set(before)|set(after)))
            row={'review_id':rid,'target':target,
                 'title':'项目理解方法：生命周期测试夹具更新' if target==METHOD_ID else '本地文本统计：启用现有 Unicode 计数版本',
                 'status':'VALIDATED' if evaluation['passed'] else 'VALIDATION_FAILED',
                 'product':product_identity(),'parent':parent,
                 'candidate':{'component_id':target,'version':candidate_version,'package_sha256':candidate.package_sha256},
                 'evaluation':evaluation,'operation':'UPDATE','basis_id':None,
                 'diff':diff,
                 'authority':'LOCAL_MAINTENANCE_ONLY_NOT_WIKI_OWNER','can_accept':evaluation['passed'],
                 'note':('未激活；方法候选仅为确定性生命周期测试夹具，不证明语义改进。确认后仍须重启。'
                         if target==METHOD_ID else '未激活；仅此受信工具包。确认后仍须重启。无正式业务语义或 RSI 资格。')}
            self._seal(row);self._event('validated',review_id=rid,status=row['status'])
            return row

    def _checked(self,rid,approval_digest):
        row=self._read(rid)
        target=row.get('target',CID)
        _,_,_,candidate_version,test_path=target_spec(target)
        if row['approval_digest']!=approval_digest:raise ValueError('maintenance_stale_approval')
        if row['evaluation']['passed'] is not True:raise ValueError('maintenance_validation_failed')
        if row['product']!=product_identity():raise ValueError('maintenance_product_changed')
        candidate=self._candidate(candidate_version,self.root/'packages'/rid,target)
        if row['candidate']!={'component_id':target,'version':candidate_version,'package_sha256':candidate.package_sha256}:
            raise ValueError('maintenance_candidate_identity_changed')
        if row['operation']!='UPDATE' or row['basis_id'] is not None:raise ValueError('maintenance_operation_changed')
        artifacts=Path(row['evaluation']['artifact_root'])
        if artifacts!=self.validation_root/rid[-12:]:raise ValueError('maintenance_artifact_identity_changed')
        for item in row['evaluation']['artifacts']:
            artifact=artifacts/item['path']
            if not artifact.resolve().is_relative_to(artifacts.resolve()) or artifact.is_symlink() or not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest()!=item['sha256']:
                raise ValueError('maintenance_evidence_changed')
        regression=row['evaluation']['regression']
        if self.run_regression and (regression['status']!='PASSED' or regression.get('exit_code')!=0
                                    or not regression.get('log_sha256') or not regression.get('definition_sha256')):
            raise ValueError('maintenance_production_regression_required')
        if self.run_regression and row['product']['dirty']:raise ValueError('maintenance_clean_product_required')
        if regression['status']!='TEST_ASSEMBLY_ONLY' and hashlib.sha256((PRODUCT/test_path).read_bytes()).hexdigest()!=regression['definition_sha256']:
            raise ValueError('maintenance_test_definition_changed')
        return row

    def approve(self,rid,approval_digest,*,confirmed):
        with self._lock():
            row=self._checked(rid,approval_digest)
            if confirmed is not True or row['status']!='VALIDATED' or not row['evaluation']['passed']:
                raise ValueError('maintenance_confirmation_required')
            if self.active_identity(row.get('target',CID))!=row['parent']:raise ValueError('maintenance_parent_changed')
            if any(r['status'] in ('PENDING_RESTART','APPLYING','ROLLBACK_PENDING') for r in self.items()):raise ValueError('maintenance_restart_pending')
            row.update(status='PENDING_RESTART',confirmed_by='LOCAL_WORKSPACE_USER',confirmed_digest=approval_digest,can_accept=False)
            self._write(row);self._event('approved',review_id=rid)
            return row

    def reject(self,rid,approval_digest,*,confirmed):
        with self._lock():
            row=self._checked(rid,approval_digest)
            if confirmed is not True or row['status']!='VALIDATED':raise ValueError('maintenance_confirmation_required')
            row.update(status='REJECTED',can_accept=False);self._write(row)
            self._event('rejected',review_id=rid);return row

    def request_rollback(self,rid,approval_digest,*,confirmed):
        with self._lock():
            row=self._checked(rid,approval_digest)
            if confirmed is not True or row['status']!='APPLIED' or self.active_identity(row.get('target',CID))!=row['candidate']:
                raise ValueError('maintenance_rollback_not_available')
            if any(r['status'] in ('PENDING_RESTART','APPLYING','ROLLBACK_PENDING') for r in self.items()):
                raise ValueError('maintenance_restart_pending')
            row.update(status='ROLLBACK_PENDING');self._write(row)
            self._event('rollback_approved',review_id=rid);return row

    def _restore(self,parent,target=CID):
        _,pins,*_=target_spec(target)
        if parent is None:
            if any(c['component_id']==target for c in self.app.components.list_components()):
                self.app.components.deactivate(target)
            if self.active_identity(target) is not None or (target==CID and any(self.app._catalog.is_active(CID,version) for version in pins)):
                raise ValueError('maintenance_unexpected_active_binding')
        else:
            if parent['component_id']!=target or parent['version'] not in pins or parent['package_sha256']!=pins[parent['version']]:raise ValueError('maintenance_rollback_identity')
            self.app.components.activate(target,parent['version'])

    def _restore_and_verify(self,parent,target=CID):
        self._restore(parent,target)
        if self.active_identity(target)!=parent:raise ValueError('maintenance_restore_identity_failed')
        if parent is not None:
            value=self._method_probe(self.app,parent['version']) if target==METHOD_ID else self._probe(self.app,parent['version'],expected=3 if parent['version']=='1.0.0' else 4)
            if not value['passed']:raise ValueError('maintenance_restore_health_failed')
            return value['run_id']
        return None

    def health(self,version,target=CID):
        target_spec(target)
        value=self._method_probe(self.app,version) if target==METHOD_ID else self._probe(self.app,version,expected=3 if version=='1.0.0' else 4)
        if not value['passed']:raise ValueError('maintenance_startup_health_failed')
        return value

    def apply_pending(self):
        """Called only from cold startup, never from the approval HTTP handler."""
        with self._lock():
            rows=[r for r in self.items() if r['status'] in ('PENDING_RESTART','ROLLBACK_PENDING','APPLYING')]
            if not rows:return None
            if len(rows)!=1:raise ValueError('maintenance_multiple_pending')
            row=rows[0];rid=row['review_id']
            if row['status']=='APPLYING':raise ValueError('maintenance_incomplete_startup_review_required')
            target=row.get('target',CID)
            candidate_version=target_spec(target)[3]
            original=self.active_identity(target);rollback=row['status']=='ROLLBACK_PENDING'
            try:
                row=self._checked(rid,row['confirmed_digest'])
                expected=row['candidate'] if rollback else row['parent']
                if original!=expected:raise ValueError('maintenance_parent_changed')
                row['status']='APPLYING';self._write(row)
                if rollback:self._restore(row['parent'],target)
                else:
                    candidate=self._candidate(candidate_version,self.root/'packages'/rid,target)
                    self.app.components.admit(candidate.package_dir,candidate.package_sha256)
                    self.app.components.activate(target,candidate_version)
                active=self.active_identity(target)
                check=(self.health(active['version'],target) if target==METHOD_ID else self.health(active['version'])) if active else {'run_id':None,'passed':True}
                row.update(status='ROLLED_BACK' if rollback else 'APPLIED',startup_receipt={'active':active,'runtime_run_id':check['run_id'],'passed':True})
            except Exception as exc:
                try:
                    recovery_run=self._restore_and_verify(original,target) if target==METHOD_ID else self._restore_and_verify(original)
                    row.update(status='FAILED_ROLLED_BACK' if original is not None else 'FAILED',error=type(exc).__name__,
                               recovery_receipt={'restored':original,'runtime_run_id':recovery_run,'passed':True})
                except Exception:
                    row.update(status='RECOVERY_REQUIRED',error=type(exc).__name__)
            self._write(row);self._event('startup',review_id=rid,status=row['status'])
            return row

    def install_test_parent(self,target=CID):
        """Trusted test fixture helper; deliberately not a browser action."""
        if self.run_regression:raise ValueError('maintenance_test_only')
        parent_version=target_spec(target)[2]
        candidate=self._candidate(parent_version,target=target)
        self.app.components.admit(candidate.package_dir,candidate.package_sha256)
        self.app.components.activate(target,parent_version)
