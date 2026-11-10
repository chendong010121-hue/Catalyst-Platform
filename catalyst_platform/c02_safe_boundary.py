"""Offline-only narrow C02 wrapper around the unchanged Harness Agent path.

Mandatory in-process fake transport; no credential resolver or live endpoint
creation. Production code/Validator and Harvest remain untouched.
"""
import dataclasses,hashlib,json,os,sys,threading,uuid,subprocess
from pathlib import Path
from .evaluation_adapter import canonical,digest,file_digest
from .llm_controls import ModelTask
from .llm_provider import ObservedModelProvider
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from .workbench import CatalystWorkbench
from .semantic_tool import AdmittedSource,SemanticProposalContext
from .wiki import ProjectWiki
from .semantic_wiki import SemanticWiki
from .observability import RunRecorder
from .trace_log import JsonlTraceStore

NEUTRAL='请阅读提供的企业资料，理解业务对象、属性、关系、规则及依据，标注不确定性；不要补造来源未给出的事实。'
_ACTIVE=None
_RUN_LOCK=threading.Lock()


def _audit(event,args):
    scope=_ACTIVE
    if scope is None:return
    output,deny,attempts=scope
    if event=='subprocess.Popen':
        command=args[1]
        repository=str(Path(__file__).resolve().parents[1])
        allowed=(['git','-C',repository,'rev-parse','--verify','HEAD'],['git','-C',repository,'status','--porcelain=v1','--untracked-files=all'])
        if any(command==v or command==subprocess.list2cmdline(v) for v in allowed):return
    if event in {'socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'}:
        attempts.append({'kind':'external_execution','event':event});raise PermissionError('Offline boundary denies external execution')
    path=None;writing=False
    if event=='open':
        path,mode,flags=args
        writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
    elif event in {'os.mkdir','os.remove','os.rmdir','os.rename'}:path=args[0];writing=True
    if writing and isinstance(path,(str,bytes,os.PathLike)):
        # A writer past MAX_PATH hands Windows an extended-length path (\\?\...), which is
        # the same file but no longer a prefix-match for the run's own output folder.
        raw=os.fspath(path)
        if isinstance(raw,bytes):raw=raw.decode("utf-8","surrogateescape")
        if raw.startswith("\\\\?\\UNC\\"):raw="\\\\"+raw[8:]
        elif raw.startswith("\\\\?\\"):raw=raw[4:]
        p=Path(raw).resolve()
        if not p.is_relative_to(output) or any(p==d or p.is_relative_to(d) for d in deny):
            attempts.append({'kind':'filesystem_write','path_sha256':hashlib.sha256(str(p).encode()).hexdigest()});raise PermissionError('Offline boundary denies business/source/outside writes')
sys.addaudithook(_audit)


class DispatchFence:
    """Count before each transport invocation, serialize, no SDK retry/fallback.

    This is the mandatory transport boundary, not a Host-wide network monitor.
    """
    def __init__(self,output,exchange):
        self.output=Path(output);self.exchange=exchange;self.attempts=0;self.rows=[];self.lock=threading.Lock();self.closed=False
    def __call__(self,url,headers,body):
        if not self.lock.acquire(blocking=False):raise ValueError('parallel dispatch denied')
        try:
            if self.closed or self.attempts>=2:raise ValueError('two-attempt fence closed')
            wire=json.loads(body)
            if url!='https://api.deepseek.com/chat/completions' or wire.get('model')!='deepseek-flash' or wire.get('thinking')!={'type':'disabled'}:raise ValueError('model/endpoint drift')
            if wire.get('max_tokens') not in {4096,8192}:raise ValueError('output bound drift')
            self.attempts+=1;row={'attempt':self.attempts,'request_sha256':hashlib.sha256(body).hexdigest(),'output_cap':wire['max_tokens'],'status':'ATTEMPT_STARTED','actual_network':False};self.rows.append(row)
            try:
                response=self.exchange(url,body)
                row.update(status='MOCK_RESPONSE',response_sha256=digest(response[1]));return response
            except BaseException as exc:
                row.update(status='FAILED_STOP',error_type=type(exc).__name__);self.closed=True;raise
        finally:self.lock.release()


class _StoppedBeforeHarvest(Exception):pass


class _BoundedProvider(ObservedModelProvider):
    def __init__(self,delegate,task,pins,observer,sources,source_ids):
        super().__init__('deepseek','deepseek-flash',delegate,'SYNTHETIC_OFFLINE_STUB',task=task,require_task=True)
        self.pins=pins;self.observer=observer;self.sources=sources;self.source_ids=set(source_ids);self.requests=[];self.closed=False
    def request(self,request):
        if self.closed:raise ValueError('run already stopped')
        stage='extraction' if request.parameters.get('response_format') else 'selection'
        if (not self.requests and stage!='selection') or (self.requests and (len(self.requests)!=1 or stage!='extraction')):raise ValueError('unexpected third/final/tool stage')
        for source,pin in self.sources.items():
            if file_digest(source)!=pin:raise ValueError('source hash drift')
        request=dataclasses.replace(request,parameters={**request.parameters,'max_tokens':8192 if stage=='extraction' else 4096})
        packet=dataclasses.asdict(request);pin=digest(packet)
        if self.pins and self.pins.get(stage)!=pin:raise ValueError('request hash drift / possible Gold or tool injection')
        if self.observer:
            self.observer(packet)
            if digest(packet)!=pin:raise ValueError('observer changed effective request')
        self.requests.append({'stage':stage,'model_request_sha256':pin,'wire_fields_sha256':digest(packet),'observer_preserved_request':True})
        try:
            result=super().request(request)
            if stage=='selection':
                if result.finish_reason!='tool_calls' or len(result.tool_calls)!=1:raise ValueError('Agent did not select one tool')
                call=result.tool_calls[0]
                if len(request.tools)!=1 or call.name!=request.tools[0].name or set(json.loads(call.arguments).get('source_ids',[]))!=self.source_ids:raise ValueError('Agent did not select the complete admitted source set')
            return result
        except BaseException:self.closed=True;raise


def run_offline_agent(output,source_root,manifest,*,exchange,request_pins=None,observer=None,prior_ledger=None,harvest=None,enterprise_id='synthetic',project_id='c02-offline'):
    """No live switch. Fake transport is explicitly supplied, never credentials.

    Existing real Agent chooses from its model response. Stub responses prove
    wiring only; live autonomy is never inferred. Callback raises before any
    actual Harvest, candidate persistence, Wiki or Graph operation.
    """
    global _ACTIVE
    if prior_ledger is not None or harvest is not None:raise ValueError('old ledger/user Harvest forbidden')
    if not callable(exchange):raise ValueError('mandatory offline fake transport')
    output=Path(output).resolve();root=Path(source_root).resolve()
    if output==root or output.is_relative_to(root) or root.is_relative_to(output):raise ValueError('source/output isolation required')
    sources={};pins={}
    for key,row in manifest.items():
        p=Path(row['path']).resolve()
        if not p.is_relative_to(root) or file_digest(p)!=row['sha256']:raise ValueError('source identity drift')
        sources[key]=AdmittedSource(p,row['sha256'],locators=tuple(row['locators']) if row.get('locators') is not None else None);pins[str(p)]=row['sha256']
    if not _RUN_LOCK.acquire(blocking=False):raise ValueError('parallel run denied')
    previous_bytecode=sys.dont_write_bytecode
    try:
        output.mkdir(parents=True,exist_ok=False) # exclusive process-independent run lock
        (output/'RUN_STARTED.lock').write_text('OFFLINE_ONLY; exclusive directory; never retry this Run',encoding='utf-8')
        denied=[];_ACTIVE=(output,[root,output/'.catalyst/wiki',root/'.catalyst-proposals'],denied);sys.dont_write_bytecode=True
        code_pins={str(Path(__file__).resolve().parent/name):file_digest(Path(__file__).resolve().parent/name) for name in ['c02_safe_boundary.py','workbench.py','understand_only.py','semantic_tool.py','llm_provider.py','llm_controls.py','observability.py','understand_models.py','understand_sources.py','understand_manifest.py','understand_assets.py','understand_semantic.py','understand_verify.py']}
        launch={'code_pins':code_pins,'argv_hash':digest(sys.argv),'cwd_sha256':digest(str(Path.cwd())),'pid':os.getpid(),'source_manifest_sha256':digest(manifest),'request_pins':request_pins,'environment_allowlist':{'PYTHONUTF8':os.environ.get('PYTHONUTF8'),'PYTHONDONTWRITEBYTECODE':os.environ.get('PYTHONDONTWRITEBYTECODE')},'authority':'OFFLINE_ONLY_NO_CREDENTIALS','host_attestation':'SELF_RECORDED_NOT_INDEPENDENT'}
        (output/'launch.json').write_bytes(canonical(launch))
        task=ModelTask('offline-'+uuid.uuid4().hex,'deepseek','deepseek-flash',2,'1',200000,8192,'2','8','0.04','Offline pricing arithmetic only, not live price approval')
        fence=DispatchFence(output,exchange)
        delegate=DeepSeekModelProvider(api_key='SYNTHETIC-NON-CREDENTIAL',model='deepseek-flash',transport=fence,output_token_limit=8192,timeout=180)
        provider=_BoundedProvider(delegate,task,request_pins,observer,pins,manifest)
        store=JsonlTraceStore(output);rec=RunRecorder(store,run_id='c02-offline-'+uuid.uuid4().hex,request_id='request-'+uuid.uuid4().hex,invocation_id='inv-'+uuid.uuid4().hex,event_schema_version='1.6')
        rec.start(request_kind='c02.offline.agent',input_sha256=hashlib.sha256(NEUTRAL.encode()).hexdigest())
        wiki=ProjectWiki(output,[root],enterprise_id=enterprise_id,project_id=project_id);semantic=SemanticWiki(wiki,recorder=rec,recover_pending=False)
        app=CatalystWorkbench(output,[root]);session=app.new_session(domain={'id':'local'},enterprise={'id':enterprise_id})
        captured=[]
        def stop_before_harvest(result):
            captured.append(result);provider.closed=True
            raise _StoppedBeforeHarvest('validated output captured; no Harvest or Wiki writes authorized')
        context=SemanticProposalContext(source_root=root,sources=sources,semantic=semantic,provider=provider,actor_context={'verified':True,'simulation':True,'permissions':['knowledge.propose'],'readable_scope_ids':[wiki.scope_id]},harvest=stop_before_harvest)
        run=None;error=None
        try:
            run=session.ask(NEUTRAL,provider=provider,execution_mode='agent',visible_capabilities=[('understand','1.0.0')],proposal_context=context,recorder=rec)
        except Exception as exc:error=type(exc).__name__
        finally:
            provider.closed=True;fence.closed=True
            if not rec.is_finished:rec.finish('failure')
        events=store.inspect_run(rec.run_id)['events'];r4=output/'r4.jsonl';r4.write_bytes(b''.join(canonical(e)+b'\n' for e in events))
        business=[str(p.relative_to(output)) for p in (output/'.catalyst/wiki').rglob('*') if p.is_file()] if (output/'.catalyst/wiki').exists() else []
        receipt={'status':'CAPTURED_VALIDATED_NO_WRITE_STOP' if captured else 'SUBJECT_OR_TRANSPORT_FAILED_STOP','run_id':rec.run_id,'request_id':rec.request_id,'session_id':session.session_id,'runtime_terminal':run.result.status if run else 'failure','attempts':fence.attempts,'actual_provider_network_calls':0,'logical_mock_provider_dispatches':fence.attempts,'credentials_accessed':False,'budget':provider.budget_snapshot,'transport':fence.rows,'requests':provider.requests,'business_files':business,'business_harvest_calls':0,'boundary_capture_calls':len(captured),'captured_result_sha256':digest(captured[0].to_dict()) if captured else None,'side_effect_attempts':denied,'error_type':error,'r4_sha256':file_digest(r4),'source_hashes_after':{p:file_digest(p) for p in pins},'agent_autonomy':'AGENT_AUTONOMY_LIVE_NOT_PROVEN','observability_authority':'SELF_AUDIT_BY_CODEX','launch_sha256':file_digest(output/'launch.json')}
        assert receipt['source_hashes_after']==pins and not business
        assert all(file_digest(p)==pin for p,pin in code_pins.items())
        receipt['code_pins']=code_pins
        (output/'receipt.json').write_bytes(canonical(receipt))
        # Raw validated data is returned only in memory to the caller's private
        # evaluation boundary. It is never in the ordinary receipt/launch log.
        return {**receipt,'_captured_in_memory':captured[0].to_dict() if captured else None}
    finally:
        _ACTIVE=None;sys.dont_write_bytecode=previous_bytecode;_RUN_LOCK.release()
