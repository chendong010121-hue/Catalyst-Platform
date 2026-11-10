"""Local user assembly over the existing HarnessSession, not a second agent loop.

MOCK is a deliberately bounded organization fixture. No credential resolver,
network client, Owner issuer or production approval is installed by this host.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path

from agent_runtime.contracts import ModelResponse
from .workbench import CatalystWorkbench, WorkbenchError
from .understand_only import route_understand_request, UnderstandIntent
from .understand_sources import SOURCE_SUFFIXES
from .semantic_wiki import SemanticWiki, SemanticTransitionError
from .semantic_keys import verifier as _key_verifier
from .wiki import ProjectWiki

DEMO_TEXT = '市场部负责客户线索登记，运营部负责合同复核。市场部向运营部移交复核材料。\n客户立项由市场部发起；超过十万元由运营主管复核。'


class UserTaskBlocked(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class OrganizationDemoProvider:
    """Known nonsensitive fixture, not a natural language understanding model.

    A document is read one part at a time, so one call sees only that part's evidence:
    a fact is emitted when this call's evidence carries its complete literal phrase, and
    the parts are assembled upstream exactly as they are for a real provider. Nothing
    outside those phrases is ever emitted, so an arbitrary document yields no items
    instead of a fabricated interpretation; the demo therefore never claims to have
    understood material it only read.
    """
    model = 'MOCK-organization-fixture'
    provider_id = 'offline-fixture'
    mode = 'MOCK'
    external_calls = 0

    def request(self, request):
        payload = json.loads(request.messages[-1].content)
        evidence = payload.get('evidence') or []
        items: list[dict] = []
        def fact(kind, key, phrase, **extra):
            ref = next((r for r in evidence if phrase in str(r.get('quote') or '')), None)
            if ref is None:
                return
            items.append(dict(kind=kind, key=key, meaning=phrase, evidence_class='SOURCE_DIRECT',
                              evidence_refs=[ref['evidence_id']], **extra))
        fact('entity','marketing','市场部')
        fact('entity','operations','运营部')
        fact('claim','marketing_duty','市场部负责客户线索登记')
        fact('condition','threshold','超过十万元由运营主管复核')
        fact('relation','handoff','市场部向运营部移交复核',
             subject='marketing',predicate='移交复核',object='operations')
        if any(row['meaning'] == '市场部负责客户线索登记' for row in items):
            items.append(dict(kind='unknown',key='authority',meaning='实际审批权限未知',
                              evidence_class='UNKNOWN', evidence_refs=[],uncertainty='演示不证明生产权限'))
        return ModelResponse(content=json.dumps({'items':items},ensure_ascii=False),finish_reason='stop')


class LocalUserSession:
    """One serialized local session; HTTP and Python use the same callable.

    provider is host-only offline dependency injection for acceptance tests. The
    browser cannot supply it. Live authorization is intentionally not implemented.
    """
    def __init__(self, workspace, *, backend='json', mode='MOCK', provider=None,
                 understand_skill_root=None, understand_extraction_mode='single_stage',
                 chat_context_plugin=None):
        if mode not in {'MOCK','BLOCKED'}:
            raise ValueError('This host only permits offline MOCK or BLOCKED mode')
        self.workspace = Path(workspace).resolve()
        self.input_root = self.workspace / 'inputs'
        self.input_root.mkdir(parents=True, exist_ok=True)
        self.app = CatalystWorkbench(self.workspace, [self.input_root],
            understand_skill_root=understand_skill_root,
            understand_extraction_mode=understand_extraction_mode, chat_context_plugin=chat_context_plugin)
        self.session = self.app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
        metadata = self.app.session_dir / 'local-user.json'
        if metadata.exists():
            data = json.loads(metadata.read_text(encoding='utf-8'))
            if data['backend'] != backend or not re.fullmatch(r'session_[a-f0-9]{32}',data['session_id']):
                raise ValueError('Existing user session backend/identity mismatch')
            self.session.session_id = data['session_id']
        else:
            self.app._atomic_json(metadata,dict(session_id=self.session.session_id,backend=backend))
        self.session_id = self.session.session_id
        self.mode = mode
        self.backend = backend
        self.provider = provider or OrganizationDemoProvider()
        self._execution = threading.Lock()
        self._control = threading.RLock()
        self._pending = {}
        self._recorders = {}

    def prepare(self, recorder):
        with self._control:
            recorder.bind_session(self.session_id)
            self._pending.setdefault(recorder.run_id, threading.Event())
            self._recorders[recorder.run_id] = recorder

    def is_pending(self, run_id):
        with self._control:
            return run_id in self._pending

    def cancel(self, run_id):
        with self._control:
            event = self._pending.get(run_id)
            if event is None: return False
            event.set()
            recorder = self._recorders[run_id]
            span = recorder.start_span('user.cancel_requested',kind='CHAIN')
            recorder.end_span(span,status='success',attributes={'effect_certainty':'unknown'})
            return True

    def __call__(self, message, selected_file, recorder):
        self.prepare(recorder)
        signal = self._pending[recorder.run_id]
        def check():
            if signal.is_set(): raise UserTaskBlocked('CANCELLED')
        output = dict(run_id=recorder.run_id, session_id=self.session_id,
                      request_id=recorder.request_id, mode=self.mode,
                      state='VALIDATING', candidate_id=None, version_id=None,
                      external_calls=0, result={'output':{}}, error=None)
        semantic = None
        # No overlapping Wiki mutation or sharing one budget across concurrent turns.
        with self._execution:
            stage = recorder.start_span('user.validate_and_route',kind='CHAIN')
            try:
                check()
                route = route_understand_request(message)
                if route.intent is not UnderstandIntent.KNOWLEDGE_PROPOSE:
                    raise UserTaskBlocked('UNSUPPORTED')
                if self.mode == 'BLOCKED':
                    # No credential lookup. The host did not inject any authorized live provider.
                    raise UserTaskBlocked('BLOCKED_CREDENTIAL')
                if not selected_file:
                    raise UserTaskBlocked('SOURCE_REQUIRED')
                source = Path(selected_file).resolve()
                if source.parent != self.input_root or not source.is_file() or source.suffix.lower() not in SOURCE_SUFFIXES:
                    raise UserTaskBlocked('SOURCE_NOT_AUTHORIZED')
                if source.stat().st_size > 700_000:
                    raise UserTaskBlocked('SOURCE_TOO_LARGE')
                output['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
                recorder.end_span(stage,status='success',attributes={'source_sha256':output['source_sha256']})
                stage = None
                output['state'] = 'RUNNING'
                wiki = ProjectWiki(self.workspace,[self.input_root],enterprise_id='synthetic',
                                   project_id='local-ui-demo',backend=self.backend)
                semantic = SemanticWiki(wiki,recorder=recorder,receipt_verifier=_key_verifier(wiki.workspace))
                actor = dict(verified=True,simulation=True,permissions=['knowledge.propose'],
                             readable_scope_ids=[wiki.scope_id])
                delegate = self.provider
                class CancellableProvider:
                    model = getattr(delegate,'model','offline')
                    provider_id = getattr(delegate,'provider_id','offline')
                    @property
                    def budget_snapshot(self):
                        return getattr(delegate,'budget_snapshot',{})
                    def request(self, request):
                        check()
                        response = delegate.request(request)
                        check()
                        return response
                def select(understanding):
                    check()
                    span = recorder.start_span('harvest.select_supported_items',kind='CHAIN')
                    selected = [i.item_id for i in understanding.semantic_candidate.items
                                if i.kind not in {'unknown','conflict'} and i.evidence_refs]
                    recorder.end_span(span,status='success')
                    return selected
                proposed = self.session.propose_enterprise_semantics(
                    message,source_refs=[source],source_root=self.input_root,semantic=semantic,
                    provider=CancellableProvider(),actor_context=actor,harvest=select)
                output.update(candidate_id=proposed['proposal']['candidate_id'],
                              proposal=proposed, scope_id=wiki.scope_id)
                check()
                evaluation = semantic.evaluate(output['candidate_id'],actor_origin='independent_evaluator')
                output['evaluation'] = evaluation
                # Exercise the real gate. No external evaluation or Owner authority
                # is minted by a page click. A passing structural check is insufficient.
                try:
                    semantic.decide(output['candidate_id'],decision='ACCEPTED',
                                    actor_origin='manager_acceptance',reason_code='reviewed')
                except SemanticTransitionError as exc:
                    output.update(state='WAITING_FOR_REVIEW', error={'code':exc.code})
                else:
                    raise RuntimeError('Wiki admitted a candidate without authority')
                output['result']['output']['answer'] = (
                    'MOCK 离线流程已生成有证据的本体候选，已保存为待审候选。'
                    '结构检查不等于独立语义评价；尚未接纳或激活正式版本。')
            except Exception as exc:
                code = getattr(exc,'code',None)
                if code is None:
                    code = ('HARNESS_DENIED' if isinstance(exc,WorkbenchError) else
                            'MODEL_OUTPUT_INVALID' if isinstance(exc,(ValueError,KeyError)) else 'EXECUTION_FAILED')
                aliases = {'evaluation_rejected':'EVALUATION_REJECTED', 'llm_budget_exhausted':'BUDGET_EXHAUSTED','llm_request_limit':'BUDGET_EXHAUSTED',
                           'llm_cancelled':'CANCELLED','llm_structured_output_invalid':'MODEL_OUTPUT_INVALID','llm_output_truncated':'MODEL_OUTPUT_INVALID'}
                code = aliases.get(code,code)
                output['state'] = ('CANCELLED' if code=='CANCELLED' else
                                   'BLOCKED' if isinstance(exc,UserTaskBlocked) or code=='BUDGET_EXHAUSTED' else 'FAILED')
                output['error'] = {'code':code,'type':type(exc).__name__}
                output['result']['output']['answer'] = code
                if stage:
                    recorder.end_span(stage,status='failure',attributes={'catalyst.error.code':code})
                recorder.event('request.failed',error_code=code,error_type=type(exc).__name__)
            with self._control:
                if signal.is_set():
                    output.update(state='CANCELLED',error={'code':'CANCELLED'})
                    output['result']['output']['answer'] = '已停止后续步骤。已产生的候选保留待审；取消不代表远端计算停止或退款。'
                output['status'] = ('success' if output['state']=='WAITING_FOR_REVIEW' else
                                    'interrupted' if output['state']=='CANCELLED' else 'failure')
                final_stage = recorder.start_span('user.state.' + output['state'],kind='CHAIN')
                recorder.end_span(final_stage,status='success',attributes={'catalyst.error.code':(output['error'] or {}).get('code')})
                data = json.dumps(output,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
                recorder.event('result.emitted',status=output['status'],result_sha256=hashlib.sha256(data).hexdigest(),
                               error_code=(output['error'] or {}).get('code'))
                self.app._atomic_json(self.app.state_root/'user-results'/(recorder.run_id+'.json'),output)
                recorder.finish(output['status'],external_calls=0,session_id=self.session_id)
                if semantic: semantic.finalize_run(recorder.run_id,output['status'])
                self._pending.pop(recorder.run_id,None)
                self._recorders.pop(recorder.run_id,None)
        return output
