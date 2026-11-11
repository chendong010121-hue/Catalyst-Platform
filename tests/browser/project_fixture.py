"""OFFLINE browser fixture over the original server; not a production runner."""
import argparse,json,socket
from datetime import datetime,timedelta
from pathlib import Path
from catalyst_platform.workspace_ui import create_workspace_server
from catalyst_platform.model_qualification import load_qualification,DEFAULT_QUALIFICATION
from catalyst_platform.project_understand import ProjectUnderstandingRequest
from tests.project_understand.test_project_runtime import script
import catalyst_platform.workspace_settings as settings

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--owner-scope-fixture',action='store_true')
    parser.add_argument('--semantic',action='store_true')
    parser.add_argument('--infrastructure',action='store_true')
    parser.add_argument('--daily-replies',action='store_true')
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    original=socket.socket.connect
    def connect(sock,address):
        if not isinstance(address,tuple) or address[0] not in ('127.0.0.1','::1'):raise RuntimeError('PROJECT_BROWSER_EXTERNAL_CONNECT_DENIED')
        return original(sock,address)
    socket.socket.connect=connect
    instant=load_qualification(DEFAULT_QUALIFICATION).verified_at+timedelta(seconds=1)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    settings.datetime=Clock
    import catalyst_platform.project_acceptance as acceptance
    acceptance.datetime=Clock
    import catalyst_platform.qualification_refresh as qualification
    qualification.datetime=Clock
    qualification_file=DEFAULT_QUALIFICATION
    if args.infrastructure:
        q=json.loads(DEFAULT_QUALIFICATION.read_text(encoding='utf-8'));q.update(schema_version=2,max_output_tokens=32768)
        qualification_file=args.out/'fixture-qualification.json'
        qualification_file.write_text(json.dumps(q),encoding='utf-8')
        original_check=qualification.QualificationReview.check
        public_table=(Path(__file__).parents[1]/'fixtures/deepseek_official_pricing_table_20261027.html').read_bytes()
        qualification.QualificationReview.check=lambda self:original_check(self,fetch=lambda:public_table)
    root=args.workspace/'synthetic-source';root.mkdir(parents=True,exist_ok=True)
    (root/'agent.py').write_text('from worker import run\ndef main():\n    return run()\n',encoding='utf-8')
    (root/'worker.py').write_text('def run():\n    return "offline browser fixture"\n',encoding='utf-8')
    calls,transport=script(root)
    critical=ProjectUnderstandingRequest('browser','Explain this Agent dependency','agent',2).critical_questions
    def send(url,headers,body):
        result=transport(url,headers,body)
        if len(calls)==3:
            f=result[1]['choices'][0]['message']['tool_calls'][0]['function'];params=json.loads(f['arguments']);analysis=json.loads(params['query'])
            analysis['questions']=[dict(question_id=q,critical=True,status='SUPPORTED' if i==0 else 'EXPLICITLY_UNRESOLVED',claim_ids=['c1'] if i==0 else []) for i,q in enumerate(critical)]
            params['query']=json.dumps(analysis);f['arguments']=json.dumps(params)
        (args.out/'fake-calls.json').write_text(json.dumps(calls,ensure_ascii=False,indent=2),encoding='utf-8')
        return result
    scope=None
    if args.owner_scope_fixture:
        from catalyst_platform.project_understand import source_manifest,digest
        from catalyst_platform.components import discover_local_component
        package=Path(__file__).resolve().parents[2]/'examples/project_methods/project-understand/0.1.0'
        scope=dict(version=1,scope_id='OFFLINE_BROWSER_SCOPE',source_id='synthetic-agent',source_manifest_sha256=digest(source_manifest(root)),method_sha256=discover_local_component(package).package_sha256,objective='Explain this Agent dependency',max_depth=2,provider_id='deepseek',model='deepseek-flash',max_requests=4,budget_cny='0.387072',max_output_tokens=4096,input_token_limit=32000,expires_at=(datetime.now().astimezone()+timedelta(hours=1)).isoformat(),owner_approval='EXPLICIT_LOCAL_OWNER')
    sources={'synthetic-agent':{'root':root,'object_type':'agent'}}
    if args.semantic or args.infrastructure:
        from catalyst_platform.workbench import CapabilityCatalog
        from catalyst_platform.semantic_acceptance import file_manifest
        from tests.test_workspace_model_settings import packet
        docs=args.workspace/'synthetic-documents';docs.mkdir(exist_ok=True)
        (docs/'duties.md').write_text('服务组负责登记。\n',encoding='utf-8')
        sid=file_manifest(docs)[0]['source_id']
        sources['synthetic-documents']=dict(root=docs,object_type='enterprise_documents',task_kind='enterprise_semantics',
            label='合成制度 · 原 Understand',review_questions=['是否有来源支持职责归属？'])
        def send(url,headers,body):
            p=json.loads(body);calls.append(p)
            if args.infrastructure and 'Prepare a test configuration' in p['messages'][-1]['content']:
                result=packet(json.dumps(dict(source_id='synthetic-documents',objective='理解组织职责，形成有来源的候选',
                    max_depth=1,max_requests=4,max_output_tokens=16384,evaluation_mode='mechanical_plus_independent_review')))
            elif args.daily_replies and any(
                tool.get('function', {}).get('name') == CapabilityCatalog.internal_key('workspace_status', '1.0.0')
                for tool in p.get('tools', ())
            ):
                result=packet('这是本地合成日常回复，可以继续工作。')
            elif p.get('response_format'):
                evidence=json.loads(p['messages'][-1]['content'])['evidence']
                result=packet(json.dumps({'items':[dict(kind='entity',key='team',meaning='服务组',evidence_class='SOURCE_DIRECT',evidence_refs=[evidence[0]['evidence_id']])]},ensure_ascii=False))
            else:
                result=packet();result['choices'][0]={'message':{'role':'assistant','content':None,'tool_calls':[{'id':'synthetic-selection','type':'function','function':{'name':CapabilityCatalog.internal_key('understand','1.0.0'),'arguments':json.dumps({'source_ids':[sid]})}}]},'finish_reason':'tool_calls'}
            (args.out/'fake-calls.json').write_text(json.dumps(calls,ensure_ascii=False),encoding='utf-8')
            return 200,result
    server=create_workspace_server(args.workspace,port=args.port,project_sources=sources,project_live_scope=scope,
                                   qualification_path=qualification_file)
    session=server.run_request
    package=Path(__file__).resolve().parents[2]/'examples/project_methods/project-understand/0.1.0'
    candidate=session.app.components.discover(package)
    if not (session.app.components.installed_root/'project-understand/0.1.0').exists():
        session.app.components.admit(package,candidate['package_sha256'])
    session.app.components.activate('project-understand','0.1.0')
    session.settings.transport_override=send
    (args.out/'ready.json').write_text(json.dumps({'fixture':'FAKE_TRANSPORT_NOT_LIVE','real_api_calls':0,'method':candidate['package_sha256']}),encoding='utf-8')
    try:server.serve_forever()
    finally:server.server_close()

if __name__=='__main__':main()
