"""Lifecycle-owned asset metadata; never a code loader or executable Catalog."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = 'PRODUCT_ASSET_DESCRIPTION_NOT_ENTERPRISE_AUTHORITY'
MAX_BYTES = 2_000_000
TEXT = {'type':'string','minLength':1,'maxLength':2000}
FILE = {'type':'object','required':['path','sha256'],'additionalProperties':False,
        'properties':{'path':TEXT,'sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'}}}
SCHEMA = {'type':'object','additionalProperties':False,
 'required':['asset_id','version','kind','title','responsibility','interface','implementation','provides','requires','tests','limits','lifecycle','capability'],
 'properties':{
  'asset_id':{'type':'string','pattern':'^[a-z][a-z0-9_.-]{0,95}$'},
  'version':{'type':'string','pattern':r'^\d+\.\d+\.\d+(\+[a-f0-9]{12})?$'},
  'kind':{'enum':['service','action','method']},'title':TEXT,'responsibility':TEXT,
  'interface':{'type':'object','required':['id','version'],'additionalProperties':False,'properties':{'id':TEXT,'version':TEXT}},
  'implementation':{'type':'object','required':['entrypoint','files'],'additionalProperties':False,
    'properties':{'entrypoint':TEXT,'files':{'type':'array','minItems':1,'maxItems':16,'items':FILE}}},
  'tests':{'type':'array','minItems':1,'maxItems':16,'items':FILE},
  'provides':{'type':'array','minItems':1,'maxItems':16,'uniqueItems':True,'items':TEXT},
  'requires':{'type':'array','maxItems':16,'uniqueItems':True,'items':TEXT},
  'limits':{'type':'array','minItems':1,'maxItems':16,'items':TEXT},
  'lifecycle':{'enum':['HOST_ASSEMBLY','CATALOG_BINDING','METHOD_REFERENCE']},
  'capability':{'oneOf':[{'type':'null'},{'type':'object','required':['id','version'],'additionalProperties':False,'properties':{'id':TEXT,'version':TEXT}}]}}}


class AssetRecordError(ValueError):pass


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(value):return hashlib.sha256(value).hexdigest()


def source_file(path,*,require_exists=True):
    relative=Path(path)
    if (not relative.parts or relative.is_absolute() or '\\' in path or ':' in path or '..' in relative.parts
        or relative.parts[0] not in {'catalyst_platform','agent_runtime','platform_standard','platform-harness','tests'}
        or relative.suffix not in {'.py','.md','.json'}):
        raise AssetRecordError('asset_source_path_not_allowed')
    target=ROOT/relative
    if not target.resolve().is_relative_to(ROOT) or any(p.is_symlink() for p in (target,*target.parents) if p!=ROOT.parent):
        raise AssetRecordError('asset_source_symlink_or_escape')
    if require_exists and (not target.is_file() or target.stat().st_size>1_000_000):
        raise AssetRecordError('asset_source_missing_or_large')
    return target


def builtin_assets():
    """Source-controlled seeds; never imports the described entrypoint."""
    specs=[
      ('system.harness','service','Harness','catalyst_platform/workbench.py','HarnessSession','tests/test_composition_contract_pilot.py'),
      ('system.runtime','service','Agent Runtime','agent_runtime/runtime.py','Runtime','tests/test_composition_contract_pilot.py'),
      ('system.model-provider','service','Model Provider / P0','catalyst_platform/llm_provider.py','configured_model_provider','tests/test_provider_transport_seam.py'),
      ('system.dispatch-ledger','service','Dispatch Ledger adapter','catalyst_platform/workspace_ledger.py','LedgerFactory','tests/test_workspace_ledger_seam.py'),
      ('system.wiki','service','Source / Ontology Wiki','catalyst_platform/wiki.py','ProjectWiki','tests/test_composition_contract_pilot.py'),
      ('system.observability','service','Run Observability','catalyst_platform/observability.py','RunRecorder','tests/test_provider_transport_seam.py'),
      ('system.evaluation','service','Independent Evaluation adapter','catalyst_platform/evaluation_adapter.py','run_evaluation','tests/test_evaluation_reuse_acceptance.py'),
      ('system.development-workflow','service','Development workflow preparation','catalyst_platform/evaluation_workflow.py','prepare_workflow','tests/test_development_asset_registration.py'),
      ('method.project-acceptance','method','Project understanding acceptance','catalyst_platform/project_acceptance.py','ProjectAcceptance','tests/project_live/test_project_acceptance.py'),
      ('method.evaluation-entry','method','Evaluation Host entry adapter (test support)','catalyst_platform/evaluation_entries.py','ontology_entry','tests/test_evaluation_reuse_acceptance.py'),
      ('method.understand','method','Understand method','catalyst_platform/understand_only.py','UnderstandPort','tests/test_composition_contract_pilot.py'),
      ('capability.wiki_search','action','Source knowledge lookup','catalyst_platform/harness_plugins.py','EvoWikiSearchCapability','tests/test_plugin_composition.py')]
    if (ROOT/'catalyst_platform/source_connection.py').exists():
        specs.append(('capability.source_read','action','Exact source read','catalyst_platform/source_connection.py','SourceReadCapability','tests/test_source_connection.py'))
    rows=[]
    for aid,kind,title,path,entry,test in specs:
        paths=[path]
        if aid=='system.model-provider':paths+=['catalyst_platform/llm_controls.py','agent_runtime/providers/deepseek.py','agent_runtime/providers/openai_compatible.py','agent_runtime/providers/_http.py']
        if aid=='system.model-provider':paths+=['catalyst_platform/model_qualification.py','catalyst_platform/config/deepseek-flash.json','catalyst_platform/config/deepseek-v4-pro.json','catalyst_platform/workspace_settings.py']
        if aid=='system.dispatch-ledger':paths+=['catalyst_platform/_vendor/dispatch_ledger_v1.py','catalyst_platform/_vendor/dispatch_ledger_v1.provenance.json']
        if aid=='system.wiki':paths+=['catalyst_platform/semantic_wiki.py','catalyst_platform/understand_wiki.py']
        if aid=='system.observability':paths+=['catalyst_platform/trace_log.py']
        if aid=='system.runtime':paths+=['agent_runtime/contracts/interfaces.py','agent_runtime/contracts/values.py','agent_runtime/capability_executor.py']
        files=[{'path':p,'sha256':digest(source_file(p).read_bytes())} for p in paths]
        tests=[{'path':p,'sha256':digest(source_file(p).read_bytes())} for p in (test,'tests/conftest.py')]
        if aid in {'system.model-provider','system.dispatch-ledger','system.harness'}:
            tests.append({'path':'tests/test_runtime_configuration.py','sha256':digest(source_file('tests/test_runtime_configuration.py').read_bytes())})
        rows.append(dict(asset_id=aid,version='0.1.0+'+digest(canonical([files,tests]))[:12],kind=kind,title=title,
          responsibility=title+'; responsibility and usage follow the pinned source interface, not the historical stage number.',
          interface={'id':entry,'version':'existing-compatible-v1'},implementation={'entrypoint':path+':'+entry,'files':files},
          provides=[entry],requires=['explicit_host_scope'] if kind!='method' else ['authorized_sources','configured_model_provider'],
          tests=tests,limits=['Source/test identities registered; registration does not execute tests or certify business quality.',
            'No inferred execution permission or enterprise authority.'],
          lifecycle={'service':'HOST_ASSEMBLY','action':'CATALOG_BINDING','method':'METHOD_REFERENCE'}[kind],
          capability={'id':aid.split('.')[-1],'version':'1.0.0'} if kind=='action' else None))
        if aid == 'system.development-workflow':
            rows[-1]['limits'].append('Prepares reviewable workflow only; does not execute benchmarks or autonomous iteration.')
        elif aid == 'system.evaluation':
            rows[-1]['limits'].append('Requires a compatible supplied entry, independent grader and qualified evidence; not a general semantic authority.')
        elif aid == 'method.project-acceptance':
            rows[-1]['limits'].append('Project-only card; fixed project method and current bounded model limits.')
        elif aid == 'method.evaluation-entry':
            rows[-1]['requires'] = ['isolated_test_workspace', 'public_case_input']
            rows[-1]['limits'].append('Deterministic test entry; no LLM and no proof of natural-language semantic quality.')
            rows[-1]['version'] = '0.1.0+' + digest(canonical([files, tests, rows[-1]['requires'], rows[-1]['limits']]))[:12]
    return rows


class AssetRecords:
    def __init__(self,workspace,catalog,write_json):
        self.path=Path(workspace)/'.catalyst'/'asset-descriptions.json'
        self.lock_path=self.path.with_suffix('.lock')
        self.catalog,self.write_json=catalog,write_json
        self._lock=threading.RLock()

    def _file_digest(self,path):return digest(source_file(path).read_bytes())

    def _validate(self,record,*,fresh=False):
        if list(Draft202012Validator(SCHEMA).iter_errors(record)):
            raise AssetRecordError('asset_description_schema_invalid')
        if (record['kind']=='action') != (record['capability'] is not None):
            raise AssetRecordError('asset_kind_binding_mismatch')
        for item in [*record['implementation']['files'],*record['tests']]:
            source_file(item['path'],require_exists=fresh)
            if fresh and self._file_digest(item['path'])!=item['sha256']:
                raise AssetRecordError('asset_source_identity_mismatch')

    def _read(self):
        if not self.path.exists():return {'schema_version':1,'assets':{}}
        try:
            if self.path.is_symlink() or self.path.stat().st_size>MAX_BYTES:raise ValueError()
            state=json.loads(self.path.read_bytes())
            if set(state)!={'schema_version','assets'} or state['schema_version']!=1 or not isinstance(state['assets'],dict):raise ValueError()
            for key,record in state['assets'].items():
                self._validate(record)
                if key!=record['asset_id']+'@'+record['version']:raise ValueError()
            return state
        except (ValueError,OSError,TypeError,KeyError) as exc:
            raise AssetRecordError('asset_descriptions_unreadable') from exc

    def register(self,records):
        values=json.loads(canonical(records))
        if not isinstance(values,list) or not 1<=len(values)<=64:raise AssetRecordError('asset_batch_invalid')
        for record in values:self._validate(record,fresh=True)
        with self._lock:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            try:self.lock_path.mkdir()
            except FileExistsError:raise AssetRecordError('asset_metadata_busy_or_recovery_required') from None
            try:
                state=self._read()
                for record in values:
                    key=record['asset_id']+'@'+record['version'];old=state['assets'].get(key)
                    if old is not None and old!=record:raise AssetRecordError('asset_identity_version_conflict')
                    state['assets'][key]=record
                if len(state['assets'])>512:raise AssetRecordError('asset_metadata_capacity')
                serialized=json.dumps(state,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n'
                if len(serialized.encode('utf-8'))>MAX_BYTES:raise AssetRecordError('asset_metadata_byte_capacity')
                self.write_json(self.path,state)
            finally:self.lock_path.rmdir()
        return {'registered':len(values),'record_count':len(state['assets']),'authority':AUTHORITY,'runtime_mutated':False}

    def list(self):
        with self._lock:
            state=self._read();descriptors={(d.id,d.capability_version) for d in self.catalog.registry.list()}
            rows=[]
            for key,record in sorted(state['assets'].items()):
                try:fresh=all(self._file_digest(x['path'])==x['sha256'] for x in [*record['implementation']['files'],*record['tests']])
                except (ValueError,OSError):fresh=False
                binding=record['capability'];pair=(binding['id'],binding['version']) if binding else None
                rows.append({**record,'record_sha256':digest(canonical(record)),'registration_status':'REGISTERED',
                  'integrity':'MATCH' if fresh else 'DRIFT_OR_MISSING','authority':AUTHORITY,
                  'evidence_status':'TEST_REFERENCES_NOT_TEST_EXECUTION','catalog_registered':pair in descriptors,
                  'catalog_active':bool(pair and self.catalog.is_active(*pair)),'execution_authorized':False})
            return rows

    def document(self,asset_id,version):
        row=next((r for r in self.list() if r['asset_id']==asset_id and r['version']==version),None)
        if row is None:raise AssetRecordError('asset_not_registered')
        return {'asset_id':asset_id,'version':version,'record_sha256':row['record_sha256'],'authority':AUTHORITY,
          'content':'# '+row['title']+'\n\n'+AUTHORITY+'\n\n```json\n'+json.dumps(row,ensure_ascii=False,indent=2)+'\n```\n'}

    def query_summary(self,query):
        """Bounded product-only projection shared by Wiki and its model tool.

        No source bodies, paths, credentials, private evidence or test answers.
        Connections are declared interface dependencies, not observed run calls.
        """
        if not isinstance(query,str) or not 1<=len(query.strip())<=256:
            raise AssetRecordError('asset_query_invalid')
        rows=self.list()
        dependencies={
          'system.harness':['system.runtime','system.model-provider','system.observability'],
          'system.model-provider':['system.dispatch-ledger'],
          'capability.wiki_search':['system.wiki'],
          'capability.source_read':['system.wiki'],
          'method.understand':['system.model-provider']}
        public=[{k:row[k] for k in ('asset_id','version','kind','title','responsibility','interface',
                  'integrity','record_sha256','catalog_registered','catalog_active','evidence_status')} for row in rows]
        known={r['asset_id'] for r in public[:32]}
        connections=[{'from':source,'to':target,'kind':'DECLARED_INTERFACE_DEPENDENCY',
                      'qualification':'SOURCE_ASSEMBLY_REFERENCE_NOT_LIVE_CALL_TRACE',
                      'condition':'WORKSPACE_GUARDED_ASSEMBLY_ONLY' if source=='system.model-provider' else 'DECLARED_LOCAL_PRODUCT_ASSEMBLY'}
                     for source,targets in dependencies.items() for target in targets
                     if source in known and target in known]
        return {'assets':public[:32],'total':len(public),'truncated':len(public)>32,
                'connections':connections,'authority':AUTHORITY,
                'query_interpretation':'BOUNDED_INVENTORY_WITH_DECLARED_DEPENDENCIES',
                'execution_authorized':False,'semantic_quality':'NOT_EVALUATED'}

    def acceptance_plan(self,asset_id,version):
        """Non-executing plan for a separately checked-out candidate and receipts."""
        row=next((r for r in self.list() if r['asset_id']==asset_id and r['version']==version),None)
        if row is None or row['integrity']!='MATCH':raise AssetRecordError('asset_acceptance_identity_unverified')
        return {'asset_id':asset_id,'version':version,'record_sha256':row['record_sha256'],
          'parent_files':row['implementation']['files'],'test_definitions':row['tests'],
          'command':['python','-m','pytest','-q',*[t['path'] for t in row['tests'] if not t['path'].endswith('/conftest.py')],'-p','no:cacheprovider'],
          'required_receipts':['parent_commit_tree','candidate_commit_tree','test_ids','contract_positive_negative','R4_when_executed','source_hashes','rollback'],
          'execution':'NOT_EXECUTED','candidate_workspace':'INDEPENDENT_WORKTREE_REQUIRED',
          'promotion':'EXPLICIT_REVIEW_REQUIRED_NOT_AUTOMATIC','business_semantics':'NOT_EVALUATED'}
