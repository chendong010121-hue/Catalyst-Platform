import json
from datetime import timedelta
from dataclasses import asdict
import pytest
from catalyst_platform.llm_controls import ModelTask, TaskBudget
from catalyst_platform.model_qualification import DEFAULT_QUALIFICATION, load_qualification
from tests.test_api_infrastructure_p0 import task
from agent_runtime.contracts import ModelRequest


def test_explicit_model_capacity_accepts_16384_without_relaxing_request_bound():
    declaration=ModelTask(**(asdict(task())|{'max_output_tokens':16384,'model_output_token_limit':32768}))
    budget=TaskBudget(declaration)
    assert declaration.max_output_tokens==16384
    with pytest.raises(ValueError):
        ModelTask(**(asdict(declaration)|{'max_output_tokens':32769}))


def test_legacy_task_still_requires_explicit_capacity_above_8192():
    with pytest.raises(ValueError):task(max_output_tokens=16384)


def test_qualification_output_capacity_is_declared_not_fixed_4096(tmp_path):
    value=json.loads(DEFAULT_QUALIFICATION.read_text(encoding='utf-8'))
    value.update(schema_version=2,max_output_tokens=32768)
    p=tmp_path/'qualification.json';p.write_text(json.dumps(value),encoding='utf-8')
    assert load_qualification(p).max_output_tokens==32768

def test_16384_reaches_actual_existing_understand_request(tmp_path,offline):
    import hashlib
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from catalyst_platform.project_acceptance import ProjectAcceptance
    from catalyst_platform.workbench import CapabilityCatalog
    from tests.test_workspace_model_settings import configuration,packet
    from tests.project_live.test_daily_workflow_boundary import recorder
    q=json.loads(DEFAULT_QUALIFICATION.read_text(encoding='utf-8'));q.update(schema_version=2,max_output_tokens=32768)
    path=tmp_path/'qualified.json';path.write_text(json.dumps(q),encoding='utf-8')
    host=WorkspaceUserSession(tmp_path/'workspace',qualification_path=path)
    root=tmp_path/'source';root.mkdir();(root/'a.md').write_text('合成服务组负责登记。',encoding='utf-8')
    calls=[]
    def send(url,headers,body):
        p=json.loads(body);calls.append(p);r=packet()
        if p.get('response_format'):
            assert p['max_tokens']==16384
            e=json.loads(p['messages'][-1]['content'])['evidence'][0]
            r=packet(json.dumps({'items':[dict(kind='entity',key='team',meaning='合成服务组',evidence_class='SOURCE_DIRECT',evidence_refs=[e['evidence_id']])]},ensure_ascii=False))
        else:r['choices'][0]={'message':{'role':'assistant','content':None,'tool_calls':[{'id':'selection','type':'function','function':{'name':CapabilityCatalog.internal_key('understand','1.0.0'),'arguments':json.dumps({'source_ids':[sid]})}}]},'finish_reason':'tool_calls'}
        return 200,r
    host.settings.transport_override=send;host.settings.configure(configuration())
    flow=ProjectAcceptance(host,{'docs':dict(root=root,object_type='enterprise_documents',task_kind='enterprise_semantics')})
    row=flow.prepare('docs','理解组织职责，形成有来源的候选',1,limits=dict(max_requests=4,max_output_tokens=16384))
    sid=row['card']['sources'][0]['source_id'];rec=recorder(host);host.prepare(rec)
    result=flow.execute(row['test_id'],row['card_sha256'],rec)
    assert result['status']=='success' and len(calls)==2
    assert row['card']['max_output_tokens']==16384
    assert flow.get(row['test_id'])['budget']['reserved_per_request_cny']=='0.195072'

from tests.project_live.test_project_acceptance import qualification_clock
from tests.project_understand.test_project_runtime import offline
