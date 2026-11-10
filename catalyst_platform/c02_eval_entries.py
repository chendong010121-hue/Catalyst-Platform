"""C02 case-local bridges to the existing shared Eval adapter.

Only offline fake/frozen transport. Historical enterprise artifacts are read
in place, hash-bound, and never copied to these evaluation result folders.
"""
import json,hashlib
from pathlib import Path
from .evaluation_adapter import digest,file_digest
from .evaluation_entries import _reference
from .c02_safe_boundary import run_offline_agent


def synthetic_exchange(url,body):
    wire=json.loads(body)
    if wire.get('response_format'):
        payload=json.loads(wire['messages'][-1]['content']);ref=payload['evidence'][0]['evidence_id']
        message={'role':'assistant','content':json.dumps({'items':[{'kind':'entity','key':'service','meaning':'服务组','evidence_class':'SOURCE_DIRECT','evidence_refs':[ref]}]},ensure_ascii=False)};finish='stop'
    else:
        goal=wire['messages'][-1]['content'];marker='Host-admitted original source IDs: '
        ids=json.loads(goal.split(marker)[-1])
        message={'role':'assistant','content':None,'tool_calls':[{'id':'offline-native-choice','type':'function','function':{'name':wire['tools'][0]['function']['name'],'arguments':json.dumps({'source_ids':ids})}}]};finish='tool_calls'
    return 200,{'id':'SYNTHETIC_OFFLINE_STUB','model':'deepseek-flash','choices':[{'message':message,'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':10}}


def agent_evaluation_entry(public,workspace):
    workspace=Path(workspace)
    if public['mode']=='HISTORICAL_FROZEN_RESPONSE_REPLAY':
        wirepins=public['http_pins'];responses=public['response_files']
        def exchange(url,body):
            stage='extraction' if json.loads(body).get('response_format') else 'selection'
            if hashlib.sha256(body).hexdigest()!=wirepins[stage]:raise ValueError('frozen HTTP request bytes differ')
            p=Path(responses[stage]['path'])
            if file_digest(p)!=responses[stage]['sha256']:raise ValueError('frozen response drift')
            return 200,json.loads(p.read_text(encoding='utf-8'))
    elif public['mode']=='SYNTHETIC_OFFLINE_STUB':exchange=synthetic_exchange
    else:raise ValueError('No live execution entry')
    receipt=run_offline_agent(workspace/'runtime',public['source_root'],public['sources'],exchange=exchange,request_pins=public.get('request_pins'),enterprise_id=public.get('enterprise_id','synthetic'),project_id=public.get('project_id','c02-offline'))
    captured=receipt.pop('_captured_in_memory');runtime=workspace/'runtime'
    observation={'execution_kind':'PRODUCT_RUNTIME','capability_id':'understand','run_id':receipt['run_id'],'boundary_status':receipt['status'],'actual_provider_calls':0,'mock_transport_dispatches':receipt['attempts'],'agent_autonomy':'AGENT_AUTONOMY_LIVE_NOT_PROVEN','evidence_refs':[_reference(runtime/'r4.jsonl','r4'),_reference(runtime/'receipt.json','boundary_receipt')]+[_reference(p,'runtime_state') for p in (runtime/'.catalyst/sessions').glob('*.json')]}
    if captured:
        observation.update(items=captured['semantic_candidate']['items'],evidence=captured['evidence_refs'])
        manifest={}
        for e in observation['evidence']:manifest.setdefault(e['source_sha256'],{})[e['locator']]=e['span_sha256']
        observation['source_manifest']=manifest
    elif public['mode']=='HISTORICAL_FROZEN_RESPONSE_REPLAY':
        observation.update(review_kind='CONFIDENTIAL_FROZEN_RESPONSE_DIAGNOSTIC',frozen_output_sha256=public['response_files']['extraction']['sha256'])
    else:observation['execution_error']='SUBJECT_OR_TRANSPORT_FAILURE'
    return observation
