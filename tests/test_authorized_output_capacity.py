"""Offline checks for explicitly authorized higher DeepSeek output; no paid API."""
import json
import pytest
from agent_runtime.contracts import Message, ModelRequest
from agent_runtime.providers.deepseek import DeepSeekModelProvider
from catalyst_platform.llm_provider import configured_model_provider
from tests.test_api_infrastructure_p0 import task, response
from catalyst_platform.understand_only import UnderstandPort, UnderstandingRequest

def test_explicit_8192_task_reaches_existing_transport_and_port(tmp_path,monkeypatch):
    import catalyst_platform.llm_provider as lp
    seen=[]
    def transport(url,headers,body):
        wire=json.loads(body);seen.append(wire)
        evidence=json.loads(wire['messages'][-1]['content'])['evidence'][0]['evidence_id']
        content=json.dumps({'items':[dict(kind='entity',key='team',meaning='服务组',evidence_class='SOURCE_DIRECT',evidence_refs=[evidence])]})
        return 200,response(content=content)
    monkeypatch.setattr(lp,'DeepSeekModelProvider',lambda **kw:DeepSeekModelProvider(**kw,transport=transport))
    p=configured_model_provider(provider_id='deepseek',model='deepseek-flash',api_key='offline-test',base_url='https://api.deepseek.com',task=task(max_output_tokens=8192))
    source=tmp_path/'source.txt';source.write_text('服务组负责登记。',encoding='utf-8')
    result=UnderstandPort().understand(UnderstandingRequest('approved-output','企业语义',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',requested_depth='semantic',budget_steps=16),source_root=tmp_path,semantic_provider=p)
    assert result.semantic_candidate and seen[0]['max_tokens']==8192
    assert seen[0]['thinking']=={'type':'disabled'}
    assert p.budget_snapshot['attempts']==1

def test_unconfigured_delegate_preserves_4096_default():
    p=DeepSeekModelProvider(api_key='offline-test',transport=lambda *_:pytest.fail('must not dispatch'))
    with pytest.raises(Exception):p.request(ModelRequest(messages=(Message('user','test'),),parameters={'max_tokens':4097}))

def test_8192_hard_ceiling_rejects_larger_task():
    with pytest.raises(ValueError):task(max_output_tokens=8193)

def test_explicit_delegate_still_rejects_above_approved_limit():
    p=DeepSeekModelProvider(api_key='offline-test',output_token_limit=8192,transport=lambda *_:pytest.fail('must not dispatch'))
    with pytest.raises(Exception):p.request(ModelRequest(messages=(Message('user','test'),),parameters={'max_tokens':8193}))
