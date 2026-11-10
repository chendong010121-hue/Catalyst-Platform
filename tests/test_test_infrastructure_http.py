import json,threading
from pathlib import Path
from tests.test_workspace_settings_http import service
from tests.test_workspace_credentials import FakeProtection


def test_http_save_forget_and_pending_gate_never_exposes_key(service):
    server,calls,get,post=service;settings=server.run_request.settings;p=FakeProtection();settings.credential_store.protector=p
    data={'action':'credential_save','data':{'api_key':'OFFLINE-ONLY-SAVED-KEY','confirmed':True}}
    assert post(data,csrf='wrong')[0]==403
    status,value=post(data)
    assert status==200 and value['saved_credential_available'] and not value['configured']
    assert 'OFFLINE-ONLY-SAVED-KEY' not in json.dumps(value)
    assert p.reads==0 and not calls
    server.run_request._pending['queued']=threading.Event()
    try:assert post({'action':'model_saved','data':{}})[0]>=400
    finally:server.run_request._pending.clear()
    assert post({'action':'model_saved','data':{'api_key':'invalid'}})[0]>=400 and p.reads==0
    assert post({'action':'model_saved','data':{'provider_id':'deepseek','model':'deepseek-flash','max_requests':2,'budget_cny':'1','max_output_tokens':1024,'consent':False}})[0]>=400 and p.reads==0
    assert post({'action':'credential_forget','data':{'confirmed':True}})[0]==200
    assert not settings.credential_store.available and not calls


def test_http_official_change_requires_exact_confirmation(service,monkeypatch):
    from catalyst_platform.qualification_refresh import QualificationReview
    server,calls,get,post=service;original=QualificationReview.check
    html=(Path(__file__).parent/'fixtures/deepseek_official_pricing_table_20261027.html').read_bytes()
    monkeypatch.setattr(QualificationReview,'check',lambda self:original(self,fetch=lambda:html))
    status,value=post({'action':'qualification_check','data':{}})
    assert status==200 and value['qualification_review']['status']=='REVIEW_REQUIRED'
    sha=value['qualification_review']['proposal_sha256']
    assert post({'action':'qualification_approve','data':{'proposal_sha256':'0'*64,'confirmed':True}})[0]>=400
    status,value=post({'action':'qualification_approve','data':{'proposal_sha256':sha,'confirmed':True}})
    assert status==200 and value['qualification_output_token_limit']==384000
    assert value['qualification_status']=='VALID' and not calls
    assert server.run_request.settings.qualification_path.is_relative_to(server.run_request.workspace)
