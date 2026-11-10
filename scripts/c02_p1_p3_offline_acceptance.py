"""Offline acceptance through existing Agent and shared Eval; no live option."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalyst_platform.evaluation_adapter import canonical,digest,file_digest,check_health,run_evaluation,compare_evaluations
from catalyst_platform.c02_nl_eval import nl_profile,nl_grader,atomic_digest
from catalyst_platform.c02_eval_entries import agent_evaluation_entry
from catalyst_platform.c02_observation_audit import audit_observation


def make_health():
    quote='服务组负责登记。';span=hashlib.sha256(quote.encode()).hexdigest()
    e={'evidence_id':'e1','quote':quote,'span_sha256':span,'source_sha256':'s1','locator':'line:1'}
    item={'kind':'entity','key':'service','meaning':'服务组','evidence_class':'SOURCE_DIRECT','evidence_refs':['e1']}
    good={'items':[item],'evidence':[e],'source_manifest':{'s1':{'line:1':span}}}
    gold={'basis':'SYNTHETIC_NL_HEALTH_ONLY','required_claims':['service'],'assessments':{'service':{'item_digest':atomic_digest(item),'mode':'DIRECT_SUPPORT','source_refs':['e1'],'scope':'独立合成资料','conditions':[],'exceptions':[],'basis':'Synthetic independent fixture, not enterprise Gold'}}}
    bad=copy.deepcopy(good);bad['items'][0]['evidence_refs']=['not-in-source']
    wrong=copy.deepcopy(good);wrong['items'][0]['meaning']='其他部门具有审批权'
    probes=[{'id':i,'basis':'INDEPENDENT','observation':o,'gold':gold,'expected':x} for i,o,x in [('KNOWN_GOOD',good,True),('KNOWN_BAD',bad,False),('NULL',{},False),('WRONG_QUESTION_CONFIDENT',wrong,False),('BROKEN_TASK_OR_INFRA_ERROR',{'execution_error':'fixture source unavailable'},'INFRASTRUCTURE_ERROR')]]
    h=check_health(nl_profile(),nl_grader,probes);assert h['status']=='PASS';return h


def main(output,historical_root=None):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    save=lambda n,v:(output/n).write_bytes(canonical(v))
    profile=nl_profile();health=make_health();save('profile.json',profile);save('health.json',health)
    sources=output/'synthetic_sources';sources.mkdir();manifest={}
    for i,text in enumerate(['服务组负责登记。','财务组负责核验。','例外条件需要另行确认。'],1):
        p=sources/f'document{i}.md';p.write_bytes((text+'\n').encode());manifest[f'document_{i}']={'path':str(p),'sha256':file_digest(p),'locators':None}
    sid='src_'+hashlib.sha256((str(sources)+'\0document1.md').encode()).hexdigest()[:20]
    ref='ev_'+hashlib.sha256((sid+'\0line:1\0服务组负责登记。').encode()).hexdigest()[:24]
    item={'kind':'entity','key':'service','meaning':'服务组','evidence_class':'SOURCE_DIRECT','evidence_refs':[ref]}
    gold={'basis':'SYNTHETIC_NL_HEALTH_ONLY','required_claims':['service'],'allowed_boundary_unknowns':['approval','binding'],'assessments':{'service':{'item_digest':atomic_digest(item),'mode':'DIRECT_SUPPORT','source_refs':[ref],'scope':'服务组存在于独立合成句子','conditions':[],'exceptions':[],'basis':'Frozen synthetic expectation before Subject stub execution'}}}
    positive={'id':'synthetic_agent_stop','split':'test','critical':True,'public':{'mode':'SYNTHETIC_OFFLINE_STUB','source_root':str(sources),'sources':manifest},'gold':gold}
    # Freeze before execution: no answer/Gold enters the live Agent message.
    save('synthetic_case_pre_registration.json',positive)
    result=run_evaluation(profile,[positive],agent_evaluation_entry,nl_grader,output/'synthetic_eval',health=health,target_identity='SYNTHETIC_OFFLINE_STUB_NO_WRITE_BOUNDARY')
    assert result['rows'][0]['task_success'] is True,result['rows']
    observations=[json.loads((output/'synthetic_eval/cases/synthetic_agent_stop/observation.json').read_text(encoding='utf-8'))]
    reports={'synthetic':result['rows'],'historical':None,'new_network_calls':0,'logical_mock_dispatches':2,'enterprise_nl_semantics':'NOT_EVALUATED','owner_gold_signoff':'PENDING','agent_autonomy':'AGENT_AUTONOMY_LIVE_NOT_PROVEN','scope':'One unchanged Harness Agent path and one shared Eval adapter; no live/hillclimb.'}
    reports['gate']=compare_evaluations(output/'synthetic_eval',output/'synthetic_eval');assert not reports['gate']['accept']
    if historical_root:
        old=Path(historical_root).resolve();raw=old/'RAW_MODEL_OUTPUT_AND_RECEIPT_LOCAL_ONLY';copy_proof=json.loads((old/'SOURCE_BYTE_COPY_AND_LOCATOR_PROOF.json').read_text(encoding='utf-8'))['sources']
        historical_manifest={r['source_id']:{'path':r['copy_path'],'sha256':r['sha256'],'locators':r['locators']} for r in copy_proof}
        identity=json.loads((old/'MODEL_REQUEST_IDENTITY_AND_BLIND_PROOF.json').read_text(encoding='utf-8'));stages={r['stage']:r for r in identity['stages']}
        response_files={stage:{'path':str(raw/f'{i}_{stage}_RAW_HTTP_RESPONSE.json'),'sha256':file_digest(raw/f'{i}_{stage}_RAW_HTTP_RESPONSE.json')} for i,stage in [(1,'selection'),(2,'extraction')]}
        public={'mode':'HISTORICAL_FROZEN_RESPONSE_REPLAY','source_root':str(raw/'original-byte-copies'),'sources':historical_manifest,'request_pins':{s:r['model_request_sha256'] for s,r in stages.items()},'http_pins':{s:r['http_body_sha256'] for s,r in stages.items()},'response_files':response_files,'enterprise_id':'c02-controlled-test','project_id':'agent-live-v11'}
        private={'basis':'CALIBRATION_PENDING','frozen_artifacts':{'response':response_files['extraction']['path'],'response_sha256':response_files['extraction']['sha256'],'request':str(raw/'2_extraction_MODEL_REQUEST.json'),'request_sha256':file_digest(raw/'2_extraction_MODEL_REQUEST.json')}}
        case={'id':'historical_frozen_failure','split':'test','critical':True,'public':public,'gold':private};save('historical_replay_pre_registration.json',case)
        actual=run_evaluation(profile,[case],agent_evaluation_entry,nl_grader,output/'historical_eval',health=health,target_identity='HISTORICAL_RESPONSE_REPLAY_NO_NEW_MODEL')
        row=actual['rows'][0];assert row['task_success'] is None and row['failure_class']=='STRUCTURE_GATE_REJECTED_DIAGNOSTIC_ONLY',row
        assert sum(r['reason']=='MISSING_OBJECT' for r in row['violations'])==14
        assert sum(r['reason']=='MISSING_UNCERTAINTY' for r in row['violations'])==9
        obs=json.loads((output/'historical_eval/cases/historical_frozen_failure/observation.json').read_text(encoding='utf-8'));assert obs['mock_transport_dispatches']==2 and obs['boundary_status']=='SUBJECT_OR_TRANSPORT_FAILED_STOP'
        observations.append(obs);reports.update(historical=actual['rows'],logical_mock_dispatches=4)
    checks=[]
    for observation in observations:
        refs=observation['evidence_refs'];trace=next(r for r in refs if r['role']=='r4');path=Path(trace['path']);events=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
        receipt=next(r for r in refs if r['role']=='boundary_receipt');r=json.loads(Path(receipt['path']).read_text(encoding='utf-8'))
        assert not r['business_files'] and not r['side_effect_attempts'] and r['business_harvest_calls']==0 and not (Path(receipt['path']).parent/'.catalyst/wiki').exists()
        a=audit_observation(events,path,trace['sha256'],claimed_tool=True,provider_tool_receipt=any(e['event_type']=='llm.response.received' and e.get('finish_reason')=='tool_calls' for e in events),eval_input=observation.get('frozen_output_sha256',r['captured_result_sha256']),frozen_output=observation.get('frozen_output_sha256',r['captured_result_sha256']),attempt_count=r['attempts'],response_count=sum(e['event_type']=='llm.response.received' for e in events))
        assert a['coverage']=='DIRECTLY_OBSERVED';checks.append(a)
    reports['observation_checks']=checks;save('INTEGRATED_ZERO_PAID_E2E_RECEIPT.json',reports)
    # Same unchanged upstream renderer/carrier; semantic unknowns remain absent.
    import subprocess
    renderer=Path(__file__).resolve().parents[1]/'platform-harness/evaluation/vendor/anthropic/build-report-lite.mjs'
    flow=output/'report_flow';flow.mkdir()
    for name,source in [('baseline',output/'synthetic_eval')]:
        import shutil
        target=flow/name;target.mkdir()
        for filename in ['results.jsonl','errors.jsonl','summary.json']:(target/filename).write_bytes((source/filename).read_bytes())
    (flow/'_state.json').write_bytes(canonical({'metrics':[{'id':'TASK_SUCCESS','kind':'binary'}],'test_ids':['synthetic_agent_stop'],'best':{'round':0}}))
    process=subprocess.run(['node',str(renderer),str(flow)],capture_output=True,text=True,check=True)
    save('report_render_receipt.json',{'renderer_sha256':file_digest(renderer),'report_sha256':file_digest(flow/'report.html'),'stderr':process.stderr,'scope':'SYNTHETIC_NL_HEALTH_ONLY, no enterprise semantic score'})
    save('SHA256_MANIFEST.json',{str(p.relative_to(output)):file_digest(p) for p in output.rglob('*') if p.is_file()})
    print(json.dumps({'output':str(output),'mock_dispatches':reports['logical_mock_dispatches'],'new_paid_calls':0,'historical_14_plus_9_reproduced':bool(historical_root)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--historical-root');args=parser.parse_args();main(args.output,args.historical_root)
