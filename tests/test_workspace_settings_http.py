"""Loopback HTTP contracts with no real Provider or credentials."""
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from catalyst_platform.workspace_ui import create_workspace_server


@pytest.fixture
def service(tmp_path):
    server=create_workspace_server(tmp_path/'workspace',port=0)
    calls=[]
    def offline(url,headers,body):
        calls.append(json.loads(body))
        return 200,{'id':'offline-http','model':'deepseek-flash','system_fingerprint':'offline-http',
            'choices':[{'index':0,'message':{'role':'assistant','content':'Catalyst 离线 HTTP 验收替身。'},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':50,'completion_tokens':10,'total_tokens':60}}
    server.run_request.settings.transport_override=offline
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_address[1]}'
    def get(path):
        with urlopen(base+path,timeout=5) as r:return json.load(r)
    token=get('/api/config')['csrf_token']
    def post(data,*,csrf=token,origin=None):
        headers={'Content-Type':'application/json','X-Catalyst-CSRF':csrf}
        if origin:headers['Origin']=origin
        req=Request(base+'/api/settings',data=json.dumps(data).encode(),headers=headers,method='POST')
        try:
            with urlopen(req,timeout=5) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    yield server,calls,get,post
    server.shutdown();server.server_close();thread.join(timeout=5)


def test_settings_get_does_not_discover_environment_credentials(service,monkeypatch):
    server,calls,get,post=service
    monkeypatch.setenv('DEEPSEEK_API_KEY','DO-NOT-READ-ENV-KEY')
    result=get('/api/settings')
    assert result['key_status']=='MISSING' and not result['enabled'] and not calls


def test_settings_csrf_and_origin_are_required(service):
    server,calls,get,post=service
    data={'action':'profile','data':{'display_name':'x','workspace_name':'x'}}
    assert post(data,csrf='wrong')[0]==403
    assert post(data,origin='https://unrelated.invalid')[0]==403
    assert server.run_request.settings.profile['display_name']=='本地用户'


def test_profile_persists_but_has_no_authority_semantics(service):
    server,calls,get,post=service
    status,result=post({'action':'profile','data':{'display_name':'测试用户','workspace_name':'本机'}})
    assert status==200 and result['profile']['display_name']=='测试用户'
    assert not result['enabled'] and not calls


def test_model_save_returns_no_key_and_spends_nothing(service):
    server,calls,get,post=service
    cfg={'provider_id':'deepseek','model':'deepseek-flash','api_key':'OFFLINE-HTTP-KEY',
         'max_requests':1,'budget_cny':'1','max_output_tokens':1024,'consent':True}
    status,result=post({'action':'model','data':cfg})
    assert status==200 and result['configured'] and not result['model_verified_by_api']
    assert 'OFFLINE-HTTP-KEY' not in json.dumps(result) and not calls
    assert get('/api/config')['paid_calls_enabled'] is True


def test_bad_budget_is_stable_http_400(service):
    server,calls,get,post=service
    cfg={'provider_id':'deepseek','model':'deepseek-flash','api_key':'OFFLINE-HTTP-KEY',
         'max_requests':1,'budget_cny':'not-a-number','max_output_tokens':1024,'consent':True}
    status,result=post({'action':'model','data':cfg})
    assert status==400 and result['error']['code']=='budget_value_invalid' and not calls
