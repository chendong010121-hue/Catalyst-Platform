"""Offline protocol proof, not a claim of live model autonomy or semantic quality."""
import hashlib
import json

import pytest
from agent_runtime.contracts import ModelResponse, ModelToolCall
from catalyst_platform.workbench import CatalystWorkbench
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.semantic_wiki import SemanticWiki
from catalyst_platform.trace_log import JsonlTraceStore
from tests.test_p0_admission_identity import _recorder


class TurnProvider:
    model = 'offline-tool-selection-fixture'
    provider_id = 'offline'
    mode = 'offline'
    external_calls = 0

    def __init__(self, truncated=False, repeat=False):
        self.requests = []
        self.stages = []
        self.truncated = truncated
        self.repeat = repeat

    def request(self, request):
        self.requests.append(request)
        if request.parameters.get('response_format'):
            self.stages.append('extraction')
            evidence = json.loads(request.messages[-1].content)['evidence']
            ref = evidence[0]['evidence_id']
            rows = [dict(kind='entity', key='service', meaning='服务组', evidence_class='SOURCE_DIRECT', evidence_refs=[ref]),
                    dict(kind='claim', key='duty', meaning='服务组负责工单登记', evidence_class='SOURCE_DIRECT', evidence_refs=[ref]),
                    dict(kind='unknown', key='owner', meaning='正式审批人未知', evidence_class='UNKNOWN', evidence_refs=[], uncertainty='资料未说明')]
            return ModelResponse(content=json.dumps({'items': rows}, ensure_ascii=False), finish_reason='length' if self.truncated else 'stop')
        tool_messages = [m for m in request.messages if m.role == 'tool']
        if not tool_messages or (self.repeat and len(tool_messages) == 1):
            self.stages.append('selection')
            tool = next(t for t in request.tools if 'enterprise semantics' in t.description)
            # Native Reasoner supplies the exact registered tool name.
            return ModelResponse(tool_calls=(ModelToolCall(id='understand-call-'+str(len(tool_messages)), name=tool.name,
                arguments=json.dumps({'source_ids': ['document']})),), finish_reason='tool_calls')
        self.stages.append('final')
        result = json.loads(tool_messages[-1].content)
        assert result['status'] == 'EVALUATION_PENDING'
        assert result['authority'] == 'CANDIDATE_ONLY'
        assert result['candidate_id']
        return ModelResponse(content='已生成有来源的候选，等待独立评价及 Owner 审核，尚未激活。', finish_reason='stop')


def setup_case(tmp_path, backend='json', **provider_kwargs):
    from catalyst_platform.semantic_tool import SemanticProposalContext, AdmittedSource
    roots = tmp_path / 'sources'; roots.mkdir()
    source = roots / 'duties.md'; source.write_text('服务组负责工单登记。\n', encoding='utf-8')
    workspace = tmp_path / 'workspace'
    recorder = _recorder(workspace, 'agent-understand')
    wiki = ProjectWiki(workspace, [roots], enterprise_id='synthetic', project_id='tool', backend=backend)
    semantic = SemanticWiki(wiki, recorder=recorder)
    app = CatalystWorkbench(workspace, [roots])
    session = app.new_session(domain={'id': 'local'}, enterprise={'id': 'synthetic'})
    provider = TurnProvider(**provider_kwargs)
    actor = dict(verified=True, simulation=True, permissions=['knowledge.propose'], readable_scope_ids=[wiki.scope_id])
    proposal = SemanticProposalContext(source_root=roots,
        sources={'document': AdmittedSource(source, hashlib.sha256(source.read_bytes()).hexdigest())},
        semantic=semantic, provider=provider, actor_context=actor,
        harvest=lambda result: [i.item_id for i in result.semantic_candidate.items if i.kind == 'entity'])
    return app, session, provider, proposal, recorder, wiki


@pytest.mark.parametrize('backend', ['json', 'sqlite'])
def test_same_agent_turn_selects_understand_and_receives_candidate(tmp_path, backend):
    app, session, provider, proposal, recorder, wiki = setup_case(tmp_path, backend)
    run = session.ask('请理解这份资料并提供可审查结果', provider=provider, execution_mode='agent',
        visible_capabilities=[('understand', '1.0.0')], proposal_context=proposal, recorder=recorder)
    assert provider.stages == ['selection', 'extraction', 'final']
    assert run.result.status == 'success'
    assert '尚未激活' in run.result.output['answer']
    assert '服务组负责工单登记' not in provider.requests[0].messages[-1].content
    assert session.tool_execution_count('understand') == 1
    assert len(wiki.semantic_state()['candidates']) == 1
    assert wiki.semantic_state()['active_version_id'] is None
    cold = ProjectWiki(wiki.workspace, [proposal.source_root], enterprise_id='synthetic', project_id='tool', backend=backend)
    assert cold.semantic_state()['candidates'] == wiki.semantic_state()['candidates']
    assert app.plugins.service('understand.port') is not None
    recorder.finish('success')
    events = JsonlTraceStore(wiki.workspace).inspect_run(recorder.run_id)['events']
    assert any(e['event_type'] == 'tool.result' for e in events)
    assert {e['run_id'] for e in events} == {recorder.run_id}


@pytest.mark.parametrize('failure', ['permission', 'scope', 'changed', 'metadata'])
def test_host_admission_rejects_before_any_model_call(tmp_path, failure):
    from dataclasses import replace
    from catalyst_platform.semantic_tool import AdmittedSource
    _, session, provider, proposal, recorder, wiki = setup_case(tmp_path)
    if failure == 'permission':
        proposal = replace(proposal, actor_context={**proposal.actor_context, 'permissions': []})
    elif failure == 'scope':
        proposal = replace(proposal, actor_context={**proposal.actor_context, 'readable_scope_ids': ['another']})
    elif failure == 'changed':
        next(iter(proposal.sources.values())).path.write_text('changed', encoding='utf-8')
    else:
        source = next(iter(proposal.sources.values()))
        proposal = replace(proposal, sources={'document': AdmittedSource(source.path, source.sha256, role='CASE_METADATA')})
    with pytest.raises((ValueError, RuntimeError)):
        session.ask('形成语义候选', provider=provider, execution_mode='agent',
            visible_capabilities=[('understand', '1.0.0')], proposal_context=proposal, recorder=recorder)
    assert provider.requests == []
    assert wiki.semantic_state()['candidates'] == {}


def test_truncated_extraction_is_not_a_candidate(tmp_path):
    _, session, provider, proposal, recorder, wiki = setup_case(tmp_path, truncated=True)
    run = session.ask('形成语义候选', provider=provider, execution_mode='agent',
        visible_capabilities=[('understand', '1.0.0')], proposal_context=proposal, recorder=recorder)
    assert provider.stages == ['selection', 'extraction']
    assert run.result.status == 'failure'
    assert wiki.semantic_state()['candidates'] == {}
    assert wiki.semantic_state()['active_version_id'] is None


def test_agent_without_sources_can_answer_without_understand(tmp_path):
    class Answer:
        model = 'offline'
        def request(self, request):
            assert not request.tools
            return ModelResponse(content='你好', finish_reason='stop')
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    run = app.new_session(domain={}, enterprise={}).ask('你好', provider=Answer(), execution_mode='agent')
    assert run.result.status == 'success'
    assert run.result.output['answer'] == '你好'


def test_read_only_legacy_mode_cannot_invoke_proposal_tool(tmp_path):
    _, session, provider, proposal, recorder, wiki = setup_case(tmp_path)
    run = session.ask('形成语义候选', provider=provider,
        visible_capabilities=[('understand', '1.0.0')], recorder=recorder)
    assert run.result.status == 'failure'
    assert not provider.requests
    assert wiki.semantic_state()['candidates'] == {}


def test_live_provider_without_existing_p0_task_is_rejected(tmp_path):
    _, session, provider, proposal, recorder, _ = setup_case(tmp_path)
    provider.mode = 'live'
    with pytest.raises(ValueError, match='P0'):
        session.ask('形成候选',provider=provider,execution_mode='agent',
            visible_capabilities=[('understand','1.0.0')],proposal_context=proposal,recorder=recorder)
    assert not provider.requests


def test_proposal_tool_is_inactive_until_explicit_host_opt_in(tmp_path):
    app, _, _, _, _, _ = setup_case(tmp_path)
    assert app._catalog.get('understand','1.0.0') is None
    assert 'understand' not in {row.id for row in app._catalog.list()}


def test_host_tool_limit_prevents_second_extraction(tmp_path):
    _, session, provider, proposal, recorder, wiki = setup_case(tmp_path, repeat=True)
    run = session.ask('形成候选',provider=provider,execution_mode='agent',
        visible_capabilities=[('understand','1.0.0')],proposal_context=proposal,recorder=recorder)
    assert provider.stages == ['selection','extraction','selection']
    assert run.result.status == 'failure'
    assert len(wiki.semantic_state()['candidates']) == 1
    assert wiki.semantic_state()['active_version_id'] is None


def test_unload_withdraws_proposal_binding_without_deleting_candidate(tmp_path):
    app, session, provider, proposal, recorder, wiki = setup_case(tmp_path)
    session.ask('形成候选',provider=provider,execution_mode='agent',
        visible_capabilities=[('understand','1.0.0')],proposal_context=proposal,recorder=recorder)
    before=wiki.semantic_state()
    app.plugins.unload('understand')
    assert app._catalog.get('understand','1.0.0') is None
    with pytest.raises(ValueError,match='inactive'):
        session.ask('再次形成候选',provider=provider,execution_mode='agent',
            visible_capabilities=[('understand','1.0.0')],proposal_context=proposal,recorder=recorder)
    assert wiki.semantic_state()==before


def test_agent_selection_extraction_reply_share_p0_budget(tmp_path, monkeypatch):
    from dataclasses import replace
    from tests.test_api_infrastructure_p0 import provider as make_provider, task, response
    from catalyst_platform.workbench import CapabilityCatalog
    _, session, _, proposal, recorder, wiki = setup_case(tmp_path)
    stages=[]
    def send(_url,_headers,body):
        payload=json.loads(body)
        assert payload['model']=='deepseek-flash'
        if payload.get('response_format'):
            stages.append('extraction')
            evidence=json.loads(payload['messages'][-1]['content'])['evidence']
            row=dict(kind='entity',key='team',meaning='服务组',evidence_class='SOURCE_DIRECT',evidence_refs=[evidence[0]['evidence_id']])
            return 200,response(content=json.dumps({'items':[row]},ensure_ascii=False))
        if any(m['role']=='tool' for m in payload['messages']):
            stages.append('final')
            return 200,response(content='候选等待独立评价与 Owner 审核，未激活。')
        stages.append('selection')
        reply=response()
        reply['choices'][0]={'message':{'role':'assistant','content':None,'tool_calls':[{'id':'shared-budget-call','type':'function',
            'function':{'name':CapabilityCatalog.internal_key('understand','1.0.0'),'arguments':json.dumps({'source_ids':['document']})}}]},'finish_reason':'tool_calls'}
        return 200,reply
    p,seen=make_provider(monkeypatch,task(max_requests=3,input_token_limit=100000,max_output_tokens=1024),send)
    proposal=replace(proposal,provider=p)
    run=session.ask('形成候选',provider=p,execution_mode='agent',visible_capabilities=[('understand','1.0.0')],proposal_context=proposal,recorder=recorder)
    assert stages==['selection','extraction','final']
    assert run.result.status=='success'
    assert p.budget_snapshot['attempts']==3
    assert len(seen)==3
    assert {r['max_tokens'] for r in seen}=={1024}
