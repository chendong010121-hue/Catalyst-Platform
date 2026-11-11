"""Thin offline browser assembly onto the current shared execution capture seam.

Reuses LocalUserSession's session/control lifecycle, not its legacy execution
method. Deterministic transport is explicitly MOCK and never performs HTTP.
"""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from dataclasses import asdict
from contextlib import nullcontext

from agent_runtime.contracts import Message, ModelRequest
from .llm_controls import ModelTask
from .llm_provider import configured_model_provider
from .semantic_tool import AdmittedSource, SemanticProposalContext
from .semantic_wiki import SemanticWiki
from .semantic_keys import verifier as _key_verifier
from .user_session import LocalUserSession, OrganizationDemoProvider, UserTaskBlocked
from .understand_sources import SOURCE_SUFFIXES
from .wiki import ProjectWiki
from .workbench import CapabilityCatalog
from .workspace_context import DEFAULT_CHAT_CONTEXT_PLUGIN
from .workspace_settings import WorkspaceSettings


class WorkspaceUserSession(LocalUserSession):
    """Same Workbench/Runtime/Provider/P0/R4; capture stops before Harvest."""

    def __init__(self, *args, chat_context_plugin=DEFAULT_CHAT_CONTEXT_PLUGIN, **kwargs):
        ledger_factory = kwargs.pop('ledger_factory', None)
        from .model_qualification import DEFAULT_QUALIFICATION
        qualification_path = kwargs.pop('qualification_path', DEFAULT_QUALIFICATION)
        super().__init__(*args, chat_context_plugin=chat_context_plugin, **kwargs)
        self.settings = WorkspaceSettings(self.app, allow_live=self.mode != 'BLOCKED', ledger_factory=ledger_factory,
                                          qualification_path=qualification_path)

    def capture_lifecycle(self, recorder):
        """Own cancellation registration and cleanup for an existing child capture."""
        from .session_capture_lifecycle import SessionCaptureLifecycle
        return SessionCaptureLifecycle(self, recorder)

    def evaluation_workflows(self):
        from .evaluation_workflow import list_workflows
        return list_workflows(self.app)

    def _prepare_evaluation(self, message, mode, recorder):
        from .evaluation_workflow import prepare_workflow
        self.prepare(recorder)
        # Same cancellation lock as LocalUserSession.cancel; no API calls here.
        with self._execution, self._control:
            try:
                output={'run_id':recorder.run_id,'request_id':recorder.request_id,'task_type':'evaluation_workflow',
                    'state':'CANCELLED','status':'interrupted','external_calls':0,'candidate_id':None,'version_id':None,
                    'execution_entry':'Existing Workspace workflow preparation (no model)',
                    'result':{'output':{'answer':'已取消方案准备；没有执行实验。'}},'error':None}
                if not self._pending[recorder.run_id].is_set():
                    row=prepare_workflow(self.app,message,mode)
                    span=recorder.start_span('evaluation.workflow.prepared',kind='CHAIN',attributes={'status':'PREPARED_NOT_EXECUTED;workflow='+row['workflow_id']+';mode='+mode})
                    recorder.end_span(span,status='success')
                    output.update(state='WORKFLOW_PREPARED',status='success',workflow=row,
                        result={'output':{'answer':'已准备独立的测试/迭代待审方案。请进入“测试与迭代”审阅；尚未执行测试、调用模型、修改方法或激活候选。'}})
                self.app._atomic_json(self.app.state_root/'user-results'/(recorder.run_id+'.json'),output)
                recorder.finish(output['status'],external_calls=0)
                return output
            except Exception as exc:
                recorder.event('request.failed',error_type=type(exc).__name__)
                recorder.finish('failure',external_calls=0)
                raise
            finally:
                self._pending.pop(recorder.run_id,None);self._recorders.pop(recorder.run_id,None)

    def _basic_chat(self, message, recorder, *, thread_id=None):
        self.prepare(recorder)
        with self._execution:
            output = {'run_id': recorder.run_id, 'request_id': recorder.request_id,
                      'workspace_session_id': self.session_id, 'session_id': None,
                      'candidate_id': None, 'version_id': None, 'external_calls': 0,
                      'error': None, 'result': {'output': {}}, 'task_type': 'basic_chat'}
            settings = self.settings
            thread = thread_id or settings.chat.thread()
            output['chat'] = {'thread_id': thread, 'message': message, 'daily': False}
            provider = None
            run = None
            try:
                # Check cancellation and publish its Provider atomically with
                # the same lock used by cancel(). Queued requests cannot send
                # after an accepted cancellation.
                with self._control:
                    if getattr(self.session,'_project_pending_handles',{}):raise UserTaskBlocked('PROJECT_RUNTIME_RECONCILIATION_REQUIRED')
                    if getattr(self,'_project_live_scope',None) is not None:raise UserTaskBlocked('PROJECT_SCOPE_ONLY')
                    if self.mode == 'BLOCKED':
                        raise UserTaskBlocked('HOST_BLOCKED')
                    if self._pending[recorder.run_id].is_set():
                        raise UserTaskBlocked('CANCELLED')
                    settings.ensure_daily_connection()
                    with settings.lock:
                        provider = settings.provider
                        metadata = settings.snapshot()
                        if metadata['enabled']:
                            settings.active_run_id = recorder.run_id
                            self._capture_providers = getattr(self, '_capture_providers', {})
                            self._capture_providers[recorder.run_id] = provider
                # The Catalog is an index, not a description to answer from: only
                # the id and version travel in the text, and status questions must
                # read this Workspace through the tool below.
                caps = [{'id': d.id, 'version': d.capability_version}
                        for d in self.session.discover()]
                if provider is None:
                    # Read the same local files the product reads; never describe a
                    # system this process has not looked at.
                    from .workspace_status import collect, render_text
                    try:
                        snapshot = collect(self)
                        answer = render_text(snapshot)
                        status = {'generated_at': snapshot['generated_at'],
                                  'runs_total': snapshot['runs']['total'],
                                  'event_lines_read': snapshot['logs']['event_lines_read'],
                                  'config_present': snapshot['config']['present'],
                                  'config_total': snapshot['config']['total']}
                    except (OSError, ValueError, RuntimeError):
                        answer = '本机状态读取失败：没有生成推断性说明。请查看 Observability 或设置页。'
                        status = {'error': 'workspace_status_unavailable'}
                    output.update(mode='LOCAL_INFO', state='LOCAL_INFO', status='success',
                                  execution_entry='Workspace local status read (no model)',
                                  local_status=status,
                                  result={'output': {'answer': answer}})
                    span = recorder.start_span('workspace.local_help', kind='CHAIN')
                    recorder.end_span(span, status='success')
                else:
                    if not metadata['enabled']:
                        raise UserTaskBlocked('MODEL_SCOPE_UNAVAILABLE')
                    before = settings.network_attempts
                    # The original Harness is the only Agent loop. Context is
                    # explicit application information; no file roots/content.
                    # Status questions read this Workspace through a local,
                    # read-only tool instead of the prompt's own description.
                    from .workspace_status import (CAPABILITY_ID as STATUS_ID,
                        CAPABILITY_VERSION as STATUS_VERSION, WorkspaceStatusCapability)
                    existing=self.app._catalog.get(STATUS_ID,STATUS_VERSION)
                    if existing is not None and (type(existing.implementation) is not WorkspaceStatusCapability
                        or getattr(existing.implementation,'session',None) is not self
                        or existing.metadata.get('component_id')!='workspace-status'
                        or existing.metadata.get('component_version')!='0.1.0'
                        or existing.metadata.get('llm_visibility')!='explicit'
                        or existing.metadata.get('model_policy')!={'mode':'workspace_scoped_query','max_calls':1}
                        or existing.descriptor.execution.get('side_effect')!='none'):
                        raise UserTaskBlocked('STATUS_TOOL_BINDING_CONFLICT')
                    if existing is None:
                        self.app._catalog.register(WorkspaceStatusCapability(self),
                            capability_version=STATUS_VERSION,execution={'side_effect':'none'},metadata={
                            'component_id':'workspace-status','component_version':'0.1.0',
                            'llm_visibility':'explicit','model_policy':{'mode':'workspace_scoped_query','max_calls':1}})
                    visible=((STATUS_ID,STATUS_VERSION),)
                    if settings.allow_asset_read:
                        from .harness_plugins import WikiAssetQueryCapability
                        existing=self.app._catalog.get('wiki_assets','1.0.0')
                        if existing is not None and (type(existing.implementation) is not WikiAssetQueryCapability
                            or existing.implementation.assets is not self.app.components.assets
                            or existing.metadata.get('component_id')!='wiki-product-assets'
                            or existing.metadata.get('component_version')!='0.1.0'
                            or existing.metadata.get('llm_visibility')!='explicit'
                            or existing.metadata.get('model_policy')!={'mode':'workspace_scoped_query','max_calls':1}
                            or existing.descriptor.execution.get('side_effect')!='none'):
                            raise UserTaskBlocked('ASSET_TOOL_BINDING_CONFLICT')
                        if existing is None:
                            self.app._catalog.register(WikiAssetQueryCapability(self.app.components.assets),
                                capability_version='1.0.0',execution={'side_effect':'none'},metadata={
                                'component_id':'wiki-product-assets','component_version':'0.1.0',
                                'llm_visibility':'explicit','model_policy':{'mode':'workspace_scoped_query','max_calls':1}})
                        visible=visible+(('wiki_assets','1.0.0'),)
                    # The model sees the wire name (the Catalog's internal key), not
                    # the capability id; the prompt names both so selection is unambiguous.
                    tool_index=tuple((cid,ver,self.app._catalog.internal_key(cid,ver)) for cid,ver in visible)
                    daily = metadata['connection_mode'] == 'daily'
                    output['chat']['daily'] = daily
                    model = metadata['model']
                    if daily or thread_id is not None:
                        from .llm_controls import input_token_envelope
                        base = settings.context(caps, model=model, history=[], tools=tool_index) + '\n当前用户消息：\n' + message
                        budget = min(8192, (metadata.get('input_token_limit') or 0) - input_token_envelope(base) - 4096)
                        history, run_ids = settings.chat.context(thread, budget)
                        output['chat']['context_run_ids'] = run_ids
                        output['chat']['context_usage'] = {
                            'input_limit': metadata.get('input_token_limit'),
                            'history_budget': max(0, budget),
                        }
                    else:
                        history = settings.history[-6:]
                    contextual = settings.context(caps, model=model, history=history, tools=tool_index) + '\n当前用户消息：\n' + message
                    run = self.session.ask(contextual, provider=provider, visible_capabilities=visible,
                                           execution_mode='agent', recorder=recorder)
                    output.update(mode='LIVE_CHAT', state='CHAT_COMPLETED' if run.result.status == 'success' else 'FAILED',
                                  status=run.result.status, session_id=run.session_id,
                                  execution_entry='HarnessSession.ask(agent, tools=['+','.join(name for name,_v in visible)+'])',
                                  result=run.result.to_dict(), provider='deepseek',
                                  model=model,
                                  error=run.result.to_dict().get('error'),
                                  external_calls=settings.network_attempts - before,
                                  budget=provider.budget_snapshot, model_receipt=settings.last_model_receipt,
                                  scope_id=settings.task.task_id)
                    usage = output['chat'].setdefault('context_usage', {
                        'input_limit': metadata.get('input_token_limit'),
                    })
                    if output['budget'].get('last_status') == 'metered':
                        usage['input_tokens'] = output['budget'].get('input_tokens')
                    events=recorder.store.inspect_run(recorder.run_id)['events']
                    output['asset_read_verified']=any(e['event_type']=='tool.result' and
                        e.get('capability_id')=='wiki_assets' and e.get('status')=='success' for e in events)
                    output['workspace_status_read_verified']=any(e['event_type']=='tool.result' and
                        e.get('capability_id')==STATUS_ID and e.get('status')=='success' for e in events)
                    if run.result.status == 'success' and not self._pending[recorder.run_id].is_set():
                        answer = run.result.output.get('answer', '')
                        settings.history.extend([{'role': 'user', 'content': message},
                                                 {'role': 'assistant', 'content': answer}])
                        settings.history = settings.history[-6:]
            except Exception as exc:
                output.update(mode='LIVE_CHAT' if provider else 'LOCAL_INFO', state='BLOCKED', status='failure',
                              error={'code': getattr(exc, 'code', type(exc).__name__)},
                              result={'output': {'answer': '请求已停止：' + getattr(exc, 'code', type(exc).__name__)}})
                recorder.event('request.failed', error_type=type(exc).__name__)
            finally:
                if run is not None:
                    lifecycle = {'handle_released': False}
                    cleanup_span = None
                    try:
                        cleanup_span = recorder.start_span('session.handle.release', kind='CHAIN')
                    except Exception as exc:
                        lifecycle['observation_error_type'] = type(exc).__name__
                    try:
                        lifecycle['handle_released'] = self.session.release_completed_run(run.session_id)
                    except Exception as exc:
                        lifecycle['release_error_type'] = type(exc).__name__
                    output['lifecycle'] = lifecycle
                    if cleanup_span is not None:
                        try:
                            failed = 'release_error_type' in lifecycle
                            attributes = {'status': 'release_failed' if failed else
                                          ('released' if lifecycle['handle_released'] else 'retained')}
                            if failed:
                                attributes['error.type'] = lifecycle['release_error_type']
                            recorder.end_span(cleanup_span, status='failure' if failed else 'success', attributes=attributes)
                        except Exception as exc:
                            # Cleanup observation must not replace the primary result.
                            lifecycle['observation_error_type'] = type(exc).__name__
                with settings.lock:
                    if not getattr(self.session,'_project_pending_handles',{}):settings.active_run_id = None
            with self._control:
                if self._pending[recorder.run_id].is_set():
                    output.update(state='CANCELLED', status='interrupted')
                    output['result']['output'] = {'answer': '已请求停止；已发出请求的费用不能保证撤销。'}
                self.app._atomic_json(self.app.state_root / 'user-results' / (recorder.run_id + '.json'), output)
                recorder.event('result.emitted', status=output['status'])
                recorder.finish(output['status'], external_calls=output['external_calls'])
                self._pending.pop(recorder.run_id, None)
                self._recorders.pop(recorder.run_id, None)
                getattr(self, '_capture_providers', {}).pop(recorder.run_id, None)
            return output

    def prepare(self, recorder):
        # Agent mode owns a fresh concrete Runtime session per capture. Do not
        # pre-bind the legacy stable UI context ID to its RunRecorder.
        with self._control:
            self._pending.setdefault(recorder.run_id, threading.Event())
            self._recorders[recorder.run_id] = recorder

    def cancel(self, run_id):
        accepted = super().cancel(run_id)
        with self._control:
            provider = getattr(self, '_capture_providers', {}).get(run_id)
            if accepted and provider is not None:
                provider.cancel()
        return accepted

    def analyze_project(self, source_spec, objective, max_depth, recorder):
        """Opt-in project path; P0–P3 deliberately require an offline transport."""
        from .project_understand import run_project_analysis, ProjectUnderstandingRequest
        self.prepare(recorder)
        live_scope=getattr(self,"_project_live_scope",None)
        captured=None;admission_path=None;network_before=getattr(self.settings,"network_attempts",0)
        signal=self._pending[recorder.run_id]
        output={'run_id':recorder.run_id,'request_id':recorder.request_id,'session_id':None,
            'execution_profile':'experiment' if live_scope is not None else 'daily','task_type':'project_analysis','state':'FAILED','status':'failure','external_calls':0,
            'candidate_id':None,'version_id':None,'execution_entry':'HarnessSession.ask(agent)',
            'result':{'output':{}},'error':None}
        with self._execution:
            try:
                if self.mode=='BLOCKED':raise UserTaskBlocked('HOST_BLOCKED')
                if signal.is_set():raise UserTaskBlocked('CANCELLED')
                if getattr(self.session,'_project_pending_handles',{}):raise UserTaskBlocked('PROJECT_RUNTIME_RECONCILIATION_REQUIRED')
                restore=getattr(self.settings,'ensure_daily_connection',None)
                if callable(restore):restore()
                # Do not reuse chat consent as authority to transmit repository files.
                approved=source_spec.get('daily_read_approval_sha256')
                if approved is not None:
                    from .project_understand import source_manifest,digest
                    if (self.settings.task is None or self.settings.task.execution_profile!='daily'
                            or approved!=digest(source_manifest(source_spec['root']))):
                        raise UserTaskBlocked('PROJECT_SOURCE_APPROVAL_CHANGED')
                if self.settings.transport_override is None and live_scope is None and not self.settings.allow_project_read and approved is None:raise UserTaskBlocked('PROJECT_LIVE_NOT_AUTHORIZED')
                with self._control:
                    if signal.is_set():raise UserTaskBlocked('CANCELLED')
                    with self.settings.lock:
                        provider=self.settings.provider
                        if provider is None or not self.settings.snapshot()['enabled']:raise UserTaskBlocked('MODEL_SCOPE_UNAVAILABLE')
                        self.settings.active_run_id=recorder.run_id
                    self._capture_providers=getattr(self,'_capture_providers',{})
                    self._capture_providers[recorder.run_id]=provider
                request=ProjectUnderstandingRequest(recorder.request_id,objective,source_spec['object_type'],max_depth)
                if live_scope is not None:
                    from .project_understand import validate_live_project_scope,consume_live_project_scope
                    with self.app.components.acquire_method('project-understand') as method:
                        validate_live_project_scope(live_scope,source_spec,objective,max_depth,method_sha256=method['package_sha256'])
                    task=self.settings.task
                    if (task.provider_id!=live_scope['provider_id'] or task.model!=live_scope['model'] or task.max_requests!=live_scope['max_requests'] or task.budget_cny!=live_scope['budget_cny'] or task.input_token_limit!=live_scope['input_token_limit'] or task.max_output_tokens!=4096):raise UserTaskBlocked('PROJECT_SCOPE_MODEL_MISMATCH')
                    if self.settings.provider.budget_snapshot['attempts']!=0:raise UserTaskBlocked('PROJECT_SCOPE_NOT_FRESH')
                    admission_path=consume_live_project_scope(self.app,live_scope,recorder.run_id,task.task_id)
                    span=recorder.start_span('project.live.admitted',kind='CHAIN',attributes={'status':'OWNER_BOUND_READ_ONLY;scope='+live_scope['scope_id']})
                    recorder.end_span(span,status='success')
                with provider.capture_calls() if live_scope is not None else nullcontext(None) as captured:
                    from .project_understand import DAILY_PROJECT_POLICY
                    value=run_project_analysis(self.session,request,source_spec['root'],provider=provider,recorder=recorder,
                        execution_policy=DAILY_PROJECT_POLICY if live_scope is None else None,
                        **({'expected_manifest_sha256':source_spec['approved_manifest_sha256']} if 'approved_manifest_sha256' in source_spec else {}))
                output.update(state='PROJECT_ANALYZED',status='success',session_id=value['session_id'])
                output['lifecycle']=value['lifecycle']
                output['result']['output']={'answer':'项目分析已提交，等待独立评价；真实语义质量未认证。','project_analysis':value}
            except Exception as exc:
                output.update(state='BLOCKED' if isinstance(exc,UserTaskBlocked) else 'FAILED',error={'code':getattr(exc,'code',type(exc).__name__),'type':type(exc).__name__})
                output['session_id']=getattr(exc,'session_id',None)
                output['lifecycle']=getattr(exc,'lifecycle',{})
                if output['lifecycle'].get('method_lease_retained'):output['state']='UNRESOLVED'
                output['result']['output']['answer']=output['error']['code']
                recorder.event('request.failed',error_type=type(exc).__name__,error_code=output['error']['code'])
            finally:
                if captured is not None:
                    records=[{'request':asdict(c['request']),'response':asdict(c['response']) if c['response'] is not None else None,'error_type':type(c['error']).__name__ if c['error'] else None,'dispatched':c['dispatched']} for c in captured]
                    self.app._atomic_json(admission_path.parent/'requests-responses.json',{'records':records,'scope':live_scope,'run_id':recorder.run_id})
                    output['live_receipt']={'scope_id':live_scope['scope_id'],'capture_path':str(admission_path.parent/'requests-responses.json'),'budget':provider.budget_snapshot,'provider_receipt':self.settings.last_model_receipt}
                output['external_calls']=getattr(self.settings,'network_attempts',0)-network_before
                with self._control:
                    if signal.is_set():output.update(state='CANCELLED',status='interrupted')
                    data=json.dumps(output,ensure_ascii=False,sort_keys=True).encode()
                    recorder.event('result.emitted',status=output['status'],result_sha256=hashlib.sha256(data).hexdigest())
                    self.app._atomic_json(self.app.state_root/'user-results'/(recorder.run_id+'.json'),output)
                    recorder.finish(output['status'],external_calls=output['external_calls'])
                    self._pending.pop(recorder.run_id,None);self._recorders.pop(recorder.run_id,None)
                    getattr(self,'_capture_providers',{}).pop(recorder.run_id,None)
                with self.settings.lock:
                    if not output.get('lifecycle',{}).get('method_lease_retained') and not getattr(self.session,'_project_pending_handles',{}):
                        self.settings.active_run_id=None
        return output

    def __call__(self, message, selected_file, recorder, *, thread_id=None):
        if thread_id is not None:
            return self._basic_chat(message, recorder, thread_id=thread_id)
        if selected_file is None:
            from .evaluation_workflow import workflow_intent
            intent=workflow_intent(message)
            if intent is not None:return self._prepare_evaluation(message,intent,recorder)
            return self._basic_chat(message, recorder)
        self.prepare(recorder)
        signal = self._pending[recorder.run_id]
        output = {'run_id': recorder.run_id, 'session_id': None,
                  'workspace_session_id': self.session_id,
                  'request_id': recorder.request_id, 'mode': self.mode,
                  'candidate_id': None, 'version_id': None, 'external_calls': 0,
                  'execution_entry': 'HarnessSession.capture_execution',
                  'result': {'output': {}}, 'state': 'VALIDATING', 'error': None}
        with self._execution:
            try:
                if getattr(self.session,'_project_pending_handles',{}):raise UserTaskBlocked('PROJECT_RUNTIME_RECONCILIATION_REQUIRED')
                if self.mode != 'MOCK':
                    raise UserTaskBlocked('BLOCKED_PROVIDER')
                if signal.is_set():
                    raise UserTaskBlocked('CANCELLED')
                if not selected_file:
                    raise UserTaskBlocked('SOURCE_REQUIRED')
                source = Path(selected_file).resolve(strict=True)
                if source.parent != self.input_root or source.suffix.lower() not in SOURCE_SUFFIXES:
                    raise UserTaskBlocked('SOURCE_NOT_AUTHORIZED')
                if source.stat().st_size > 700_000:
                    raise UserTaskBlocked('SOURCE_TOO_LARGE')
                sha = hashlib.sha256(source.read_bytes()).hexdigest()
                if sha != source.stem:
                    raise UserTaskBlocked('SOURCE_IDENTITY_CHANGED')
                wiki = ProjectWiki(self.workspace, [self.input_root], enterprise_id='synthetic',
                                   project_id='local-ui-demo', backend=self.backend)
                semantic = SemanticWiki(wiki, recorder=recorder, receipt_verifier=_key_verifier(wiki.workspace))
                fixture = OrganizationDemoProvider()

                def offline_transport(_url, _headers, body):
                    if signal.is_set():
                        raise UserTaskBlocked('CANCELLED')
                    packet = json.loads(body)
                    if packet.get('response_format'):
                        # Reuse the original bounded fixture facts; never interpret arbitrary text as known facts.
                        request = ModelRequest(messages=(Message(role='user', content=packet['messages'][-1]['content']),))
                        content = fixture.request(request).content
                        choice = {'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}
                    else:
                        name = CapabilityCatalog.internal_key('understand', '1.0.0')
                        if name not in {t['function']['name'] for t in packet.get('tools', [])}:
                            raise UserTaskBlocked('UNDERSTAND_TOOL_NOT_VISIBLE')
                        choice = {'message': {'role': 'assistant', 'content': None, 'tool_calls': [
                            {'id': 'offline-understand', 'type': 'function', 'function': {
                                'name': name, 'arguments': json.dumps({'source_ids': ['document']})}}]},
                            'finish_reason': 'tool_calls'}
                    # Fixture metering only, explicitly not vendor tokens or billing.
                    return 200, {'id': 'offline-' + recorder.run_id, 'model': 'workspace-offline-fixture',
                                 'choices': [choice], 'usage': {'prompt_tokens': 10,
                                 'completion_tokens': 10, 'total_tokens': 20}}

                task = ModelTask('workspace-' + recorder.run_id, 'openai-compatible',
                                 'workspace-offline-fixture', 2, '1', 200000, 4096,
                                 '1', '1', '1', 'OFFLINE_FIXTURE_NOT_VENDOR_USAGE')
                provider = configured_model_provider(provider_id=task.provider_id,
                    api_key='OFFLINE-NON-CREDENTIAL', model=task.model,
                    base_url='https://offline.invalid', transport=offline_transport, task=task)
                provider.mode = 'offline'
                with self._control:
                    if not hasattr(self, '_capture_providers'):
                        self._capture_providers = {}
                    self._capture_providers[recorder.run_id] = provider
                actor = {'verified': True, 'simulation': True, 'permissions': ['knowledge.propose'],
                         'readable_scope_ids': [wiki.scope_id]}

                def no_harvest(_result):
                    raise RuntimeError('Workspace capture must stop before Harvest')

                context = SemanticProposalContext(source_root=self.input_root,
                    sources={'document': AdmittedSource(source, sha)}, semantic=semantic,
                    provider=provider, actor_context=actor, harvest=no_harvest)
                captured = self.session.capture_execution(message, provider=provider,
                    visible_capabilities=(('understand', '1.0.0'),), proposal_context=context,
                    recorder=recorder, artifact_dir=self.app.state_root / 'captures' / recorder.run_id)
                receipt = captured.summary()
                output.update(capture=receipt, session_id=recorder.session_id,
                              source_sha256=sha, scope_id=wiki.scope_id,
                              logical_mock_dispatches=provider.budget_snapshot['attempts'],
                              usage_basis='FIXTURE_NOT_VENDOR_USAGE')
                try:
                    output['observation'] = captured.observation()
                except ValueError:
                    pass
                output['state'] = 'CAPTURED_BEFORE_HARVEST' if receipt['status'] == 'CAPTURED' else receipt['status']
                output['status'] = 'success' if receipt['status'] == 'CAPTURED' else 'failure'
                output['result']['output']['answer'] = (
                    '已通过共享执行基座完成 MOCK 候选捕获，停止在 Harvest 之前。'
                    '尚未进行独立业务语义评价，也未保存为正式 Wiki 候选或激活版本。'
                    if receipt['status'] == 'CAPTURED' else
                    '共享执行返回 ' + receipt['status'] + '；请查看原始运行证据与错误。')
            except Exception as exc:
                output.update(state='BLOCKED' if isinstance(exc, UserTaskBlocked) else 'FAILED', status='failure',
                              error={'code': getattr(exc, 'code', type(exc).__name__), 'type': type(exc).__name__})
                output['result']['output']['answer'] = output['error']['code']
                recorder.event('request.failed', error_type=type(exc).__name__, error_code=output['error']['code'])
            with self._control:
                if signal.is_set():
                    output.update(state='CANCELLED', status='interrupted', error={'code': 'CANCELLED'})
                    output['result']['output']['answer'] = '已停止后续步骤；已生成的执行证据保留。'
                data = json.dumps(output, ensure_ascii=False, sort_keys=True).encode('utf-8')
                recorder.event('result.emitted', status=output['status'], result_sha256=hashlib.sha256(data).hexdigest())
                self.app._atomic_json(self.app.state_root / 'user-results' / (recorder.run_id + '.json'), output)
                recorder.finish(output['status'], external_calls=0, session_id=recorder.session_id,
                                execution_entry='HarnessSession.capture_execution')
                self._pending.pop(recorder.run_id, None)
                self._recorders.pop(recorder.run_id, None)
                getattr(self, '_capture_providers', {}).pop(recorder.run_id, None)
        return output
