"""Actual Harness tool selection with synthetic transport, no external API."""
import json
import socket
import pytest
from catalyst_platform.asset_records import builtin_assets
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_settings import WorkspaceSettings
from tests.test_workspace_model_settings import configuration,packet,run


@pytest.fixture(autouse=True)
def no_external(monkeypatch):
    def deny(*a,**k):raise AssertionError('WIKI_ASSETS_ZERO_API')
    monkeypatch.setattr(socket.socket,'connect',deny)


def test_model_selects_real_asset_tool_and_consumes_registered_records(tmp_path):
    session=WorkspaceUserSession(tmp_path/'work')
    session.app.components.assets.register(builtin_assets())
    requests=[]
    def transport(url,headers,body):
        request=json.loads(body);requests.append(request)
        if len(requests)==1:
            assert len(request['tools'])==1
            tool_name=request['tools'][0]['function']['name']
            # The actual records are not hardcoded into model's first input.
            assert 'system.dispatch-ledger' not in json.dumps(request['messages'])
            response=packet();response['choices'][0]['message']={'role':'assistant','content':None,
              'tool_calls':[{'id':'asset-call','type':'function','function':{'name':tool_name,'arguments':'{"query":"*"}'}}]}
            response['choices'][0]['finish_reason']='tool_calls'
            return 200,response
        tool=next(m for m in request['messages'] if m['role']=='tool')
        assert 'system.dispatch-ledger' in tool['content'] and 'DECLARED_INTERFACE_DEPENDENCY' in tool['content']
        assert 'source_path' not in tool['content'] and 'api_key' not in tool['content']
        return 200,packet('我从 Wiki 资产目录查到已登记的系统组件；登记不等于执行授权。')
    session.settings=WorkspaceSettings(session.app,transport=transport)
    config=configuration();config['allow_asset_read']=True
    session.settings.configure(config)
    result=run(session,'我们的系统内现在有什么资产？它们如何连接？')
    assert result['state']=='CHAT_COMPLETED' and result['asset_read_verified'], result
    assert len(requests)==2 and result['external_calls']==0
    from catalyst_platform.trace_log import JsonlTraceStore
    events=JsonlTraceStore(session.workspace).inspect_run(result['run_id'])['events']
    assert any(e['event_type']=='tool.execution.started' and e['capability_id']=='wiki_assets' for e in events)
    assert result['model_receipt'] and len(session.settings.ledger.read())==4


def test_text_only_authorization_never_exposes_asset_tool(tmp_path):
    session=WorkspaceUserSession(tmp_path/'text');requests=[]
    def transport(*args):requests.append(json.loads(args[2]));return 200,packet()
    session.settings=WorkspaceSettings(session.app,transport=transport)
    session.settings.configure(configuration())
    result=run(session,'有什么资产？')
    assert result['state']=='CHAT_COMPLETED' and not requests[0].get('tools')
    assert not result.get('asset_read_verified')


def test_asset_query_exports_only_pinned_metadata_not_originals(tmp_path):
    from catalyst_platform.harness_plugins import WikiAssetQueryCapability
    session=WorkspaceUserSession(tmp_path/'empty')
    cap=WikiAssetQueryCapability(session.app.components.assets)
    context=type('Context',(),{'enterprise_context':{'id':'synthetic'}})()
    result=cap.invoke({'query':'*'},context)
    assert result.data['assets']==[] and result.data['connections']==[]


def test_prebound_asset_tool_collision_stops_before_provider(tmp_path):
    from catalyst_platform.harness_plugins import WikiAssetQueryCapability
    session=WorkspaceUserSession(tmp_path/'collision')
    # Same class, foreign asset store is not this Host's authorized inventory.
    foreign=WorkspaceUserSession(tmp_path/'foreign')
    session.app._catalog.register(WikiAssetQueryCapability(foreign.app.components.assets),
      capability_version='1.0.0',execution={'side_effect':'none'},metadata={
      'model_policy':{'mode':'workspace_scoped_query','max_calls':1}})
    calls=[]
    session.settings=WorkspaceSettings(session.app,transport=lambda *a:(calls.append(1) or (200,packet())))
    config=configuration();config['allow_asset_read']=True;session.settings.configure(config)
    result=run(session,'有哪些资产？')
    assert result['state']=='BLOCKED' and calls==[]


def test_model_answer_without_tool_is_not_presented_as_verified_asset_read(tmp_path):
    session=WorkspaceUserSession(tmp_path/'no-read')
    session.settings=WorkspaceSettings(session.app,transport=lambda *a:(200,packet('仅回答，未调用工具。')))
    config=configuration();config['allow_asset_read']=True;session.settings.configure(config)
    result=run(session,'系统内有什么资产？')
    assert result['state']=='CHAT_COMPLETED' and result['asset_read_verified'] is False


def test_two_request_budget_cannot_silently_expand_for_asset_tool(tmp_path):
    session=WorkspaceUserSession(tmp_path/'one-request');calls=[]
    def transport(*args):
        calls.append(1);request=json.loads(args[2]);name=request['tools'][0]['function']['name']
        result=packet();result['choices'][0]['message']={'role':'assistant','content':None,'tool_calls':[
            {'id':'asset-one','type':'function','function':{'name':name,'arguments':'{"query":"*"}'}}]}
        result['choices'][0]['finish_reason']='tool_calls';return 200,result
    session.settings=WorkspaceSettings(session.app,transport=transport)
    config=configuration();config.update(allow_asset_read=True,max_requests=1);session.settings.configure(config)
    result=run(session,'资产？')
    assert result['state']!='CHAT_COMPLETED' and len(calls)==1
