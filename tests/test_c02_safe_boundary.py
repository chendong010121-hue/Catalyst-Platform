"""SYNTHETIC_OFFLINE_STUB through actual Harness Agent/Runtime/Tool/Port."""
import hashlib,json
from pathlib import Path
import pytest
from catalyst_platform.c02_safe_boundary import run_offline_agent,DispatchFence


def case(tmp_path):
    sources=tmp_path/'sources';sources.mkdir();p=sources/'duties.md';p.write_bytes('服务组负责登记。\n'.encode())
    return sources,{'document':{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'locators':None}}


def exchange(url,body):
    wire=json.loads(body)
    if wire.get('response_format'):
        ref=json.loads(wire['messages'][-1]['content'])['evidence'][0]['evidence_id']
        msg={'content':json.dumps({'items':[dict(kind='entity',key='service',meaning='服务组',evidence_class='SOURCE_DIRECT',evidence_refs=[ref])]},ensure_ascii=False)};finish='stop'
    else:
        msg={'content':None,'tool_calls':[{'id':'offline-selection','type':'function','function':{'name':wire['tools'][0]['function']['name'],'arguments':json.dumps({'source_ids':['document']})}}]};finish='tool_calls'
    msg['role']='assistant'
    return 200,{'id':'synthetic-offline-response','model':'deepseek-flash','choices':[{'message':msg,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':10}}


def test_same_real_agent_path_success_stops_before_any_business_write(tmp_path):
    sources,manifest=case(tmp_path);r=run_offline_agent(tmp_path/'run',sources,manifest,exchange=exchange)
    assert r['status']=='CAPTURED_VALIDATED_NO_WRITE_STOP'
    assert r['attempts']==2 and r['actual_provider_network_calls']==0
    assert r['business_files']==[] and r['business_harvest_calls']==0
    assert r['side_effect_attempts']==[]
    assert r['runtime_terminal']=='failure' # deliberate Stop is a real tool failure
    assert r['agent_autonomy']=='AGENT_AUTONOMY_LIVE_NOT_PROVEN'


def test_connection_failure_consumes_attempt_and_stops(tmp_path):
    s,m=case(tmp_path)
    def fail(*a):raise ConnectionError('offline injected fault')
    r=run_offline_agent(tmp_path/'run',s,m,exchange=fail)
    assert r['attempts']==1 and r['budget']['uncertain'] and r['status']=='SUBJECT_OR_TRANSPORT_FAILED_STOP'


def test_request_pin_mismatch_never_dispatches(tmp_path):
    s,m=case(tmp_path);r=run_offline_agent(tmp_path/'run',s,m,exchange=exchange,request_pins={'selection':'0'*64})
    assert r['attempts']==0 and r['status']=='SUBJECT_OR_TRANSPORT_FAILED_STOP'


def test_source_hash_drift_refused_before_any_run(tmp_path):
    s,m=case(tmp_path);m['document']['sha256']='0'*64
    with pytest.raises(ValueError,match='source'):run_offline_agent(tmp_path/'run',s,m,exchange=exchange)


def test_old_ledger_or_harvest_callback_rejected(tmp_path):
    s,m=case(tmp_path)
    with pytest.raises(ValueError):run_offline_agent(tmp_path/'run',s,m,exchange=exchange,prior_ledger={'attempts':1})
    with pytest.raises(ValueError):run_offline_agent(tmp_path/'run',s,m,exchange=exchange,harvest=lambda r:['bad'])


def test_same_run_directory_cannot_be_reused(tmp_path):
    s,m=case(tmp_path);run_offline_agent(tmp_path/'run',s,m,exchange=exchange)
    with pytest.raises(FileExistsError):run_offline_agent(tmp_path/'run',s,m,exchange=exchange)


def test_observer_payload_mutation_rejected(tmp_path):
    s,m=case(tmp_path)
    def mutate(packet):packet['model']='other'
    r=run_offline_agent(tmp_path/'run',s,m,exchange=exchange,observer=mutate)
    assert r['attempts']==0


def test_transport_fence_max_two_and_third_never_calls_exchange(tmp_path):
    calls=[];f=DispatchFence(tmp_path,lambda u,b:(calls.append(b) or (200,{})))
    body=json.dumps({'model':'deepseek-flash','max_tokens':4096,'thinking':{'type':'disabled'}}).encode()
    f('https://api.deepseek.com/chat/completions',{},body);f('https://api.deepseek.com/chat/completions',{},body)
    with pytest.raises(ValueError):f('https://api.deepseek.com/chat/completions',{},body)
    assert len(calls)==2


def test_sdk_retry_dispatch_is_refused_by_existing_p0_observer(tmp_path):
    from catalyst_platform.llm_provider import ObservedModelProvider
    from catalyst_platform.llm_controls import ModelTask,ModelControlError
    class SDK:
        def set_external_call_observer(self,f):self.f=f
        def request(self,r):self.f();self.f()
    p=ObservedModelProvider('deepseek','deepseek-flash',SDK(),'offline',task=ModelTask('retry','deepseek','deepseek-flash',2,'1',200000,8192,'2','8','0.04','offline'))
    from agent_runtime.contracts import ModelRequest,Message
    with pytest.raises(ModelControlError):p.request(ModelRequest(messages=(Message('user','stub'),)))
    assert p.budget_snapshot['attempts']==1 and p.budget_snapshot['uncertain']


def test_parallel_transport_race_rejected_without_extra_exchange(tmp_path):
    import threading
    entered=threading.Event();release=threading.Event();calls=[]
    def slow(u,b):calls.append(b);entered.set();release.wait(3);return 200,{}
    f=DispatchFence(tmp_path,slow);body=json.dumps({'model':'deepseek-flash','max_tokens':4096,'thinking':{'type':'disabled'}}).encode()
    t=threading.Thread(target=lambda:f('https://api.deepseek.com/chat/completions',{},body));t.start();assert entered.wait(2)
    try:
        with pytest.raises(ValueError,match='parallel'):f('https://api.deepseek.com/chat/completions',{},body)
    finally:release.set();t.join(3)
    assert len(calls)==1 and f.attempts==1


def test_wrong_model_never_calls_exchange(tmp_path):
    calls=[];f=DispatchFence(tmp_path,lambda *a:calls.append(a))
    with pytest.raises(ValueError):f('https://api.deepseek.com/chat/completions',{},json.dumps({'model':'deepseek-v4-flash','max_tokens':8192}).encode())
    assert calls==[]


def test_business_write_attempt_is_denied_not_rolled_back(tmp_path):
    s,m=case(tmp_path);actual=[]
    def malicious(url,body):
        target=tmp_path/'run/.catalyst/wiki/unauthorized';actual.append('attempt')
        target.mkdir(parents=True)
        return exchange(url,body)
    r=run_offline_agent(tmp_path/'run',s,m,exchange=malicious)
    assert actual==['attempt'] and not (tmp_path/'run/.catalyst/wiki').exists()
    assert r['side_effect_attempts'] and r['business_files']==[]


def test_selection_subset_rejected_after_one_mock_call(tmp_path):
    s,m=case(tmp_path)
    def wrong(url,body):
        status,data=exchange(url,body);data['choices'][0]['message']['tool_calls'][0]['function']['arguments']='{"source_ids":["not-admitted"]}';return status,data
    r=run_offline_agent(tmp_path/'run',s,m,exchange=wrong)
    assert r['attempts']==1 and r['boundary_capture_calls']==0


def test_readonly_observer_preserves_exact_requests_and_responses(tmp_path):
    s,m=case(tmp_path);seen=[]
    a=run_offline_agent(tmp_path/'a',s,m,exchange=exchange)
    b=run_offline_agent(tmp_path/'b',s,m,exchange=exchange,observer=lambda packet:seen.append(hashlib.sha256(json.dumps(packet,sort_keys=True).encode()).hexdigest()))
    assert [r['model_request_sha256'] for r in a['requests']]==[r['model_request_sha256'] for r in b['requests']]
    assert [r['request_sha256'] for r in a['transport']]==[r['request_sha256'] for r in b['transport']]
    assert [r['response_sha256'] for r in a['transport']]==[r['response_sha256'] for r in b['transport']]
    assert len(seen)==2


def test_pin_any_gold_or_tool_schema_addition_rejected(tmp_path):
    s,m=case(tmp_path);a=run_offline_agent(tmp_path/'a',s,m,exchange=exchange)
    pins={r['stage']:r['model_request_sha256'] for r in a['requests']}
    # Tool catalog/schema/goal fields are covered by full ModelRequest pin.
    pins['selection']='changed-by-gold-or-tool-schema'
    b=run_offline_agent(tmp_path/'b',s,m,exchange=exchange,request_pins=pins)
    assert b['attempts']==0


def test_hidden_final_response_not_dispatched_after_success_stop(tmp_path):
    s,m=case(tmp_path);stages=[]
    def record(u,b):stages.append('extraction' if json.loads(b).get('response_format') else 'selection_or_final');return exchange(u,b)
    r=run_offline_agent(tmp_path/'run',s,m,exchange=record)
    assert stages==['selection_or_final','extraction'] and r['attempts']==2


def test_two_processes_cannot_reuse_one_run_directory(tmp_path):
    import subprocess,sys
    s,m=case(tmp_path);manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(m),encoding='utf-8')
    code="from pathlib import Path;import sys,json;from catalyst_platform.c02_safe_boundary import run_offline_agent;from catalyst_platform.c02_eval_entries import synthetic_exchange;run_offline_agent(Path(sys.argv[1]),Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_text(encoding='utf-8')),exchange=synthetic_exchange)"
    command=[sys.executable,'-B','-c',code,str(tmp_path/'one-run'),str(s),str(manifest)]
    a=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);b=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    aa=a.communicate(timeout=20);bb=b.communicate(timeout=20)
    assert sorted([a.returncode,b.returncode])==[0,1]
    assert b'FileExistsError' in aa[1]+bb[1]
    receipt=json.loads((tmp_path/'one-run/receipt.json').read_text(encoding='utf-8'))
    assert receipt['attempts']==2


@pytest.mark.parametrize('injection',['gold','tool_schema'])
def test_simulated_gold_or_tool_schema_injection_is_blocked_before_dispatch(tmp_path,injection):
    s,m=case(tmp_path)
    def contaminate(packet):
        if injection=='gold':packet['messages'].append({'role':'user','content':'SYNTHETIC_PRIVATE_GOLD_DO_NOT_SEND'})
        else:packet['tools'][0]['parameters']['required'].append('owner_approved')
    r=run_offline_agent(tmp_path/'run',s,m,exchange=exchange,observer=contaminate)
    assert r['attempts']==0 and not r['transport']
