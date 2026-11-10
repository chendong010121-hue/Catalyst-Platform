"""Synthetic TEST-SCOPE relation explanation; P0 mock transport, zero paid API."""
import json
from pathlib import Path
import pytest
from catalyst_platform.workbench import CatalystWorkbench,WorkbenchError
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.semantic_wiki import SemanticWiki
from tests.test_p0_admission_identity import _recorder,_verifier,_semantic_receipt,_owner_receipt,_version_receipt
from tests.test_stage1_semantic_recovery import OrganizationFixtureProvider
from tests.test_api_infrastructure_p0 import provider,task,response


def accepted(tmp_path,backend='json'):
    roots=tmp_path/'sources';roots.mkdir()
    source=roots/'synthetic.txt'
    source.write_text('市场部负责客户线索登记，运营部负责合同复核。市场部向运营部移交复核材料。\n客户立项由市场部发起；超过十万元由运营主管复核。',encoding='utf-8')
    workspace=tmp_path/'workspace'
    app=CatalystWorkbench(workspace,[roots])
    session=app.new_session(domain={'id':'local'},enterprise={'id':'synthetic'})
    wiki=ProjectWiki(workspace,[roots],enterprise_id='synthetic',project_id='relation-explanation',backend=backend)
    rec=_recorder(workspace,'relationship-explanation')
    semantic=SemanticWiki(wiki,recorder=rec,receipt_verifier=_verifier)
    actor=dict(verified=True,simulation=True,permissions=['knowledge.propose','knowledge.read','model.invoke'],readable_scope_ids=[wiki.scope_id])
    proposal=session.propose_enterprise_semantics('整理企业本体',source_refs=[source],source_root=roots,
        semantic=semantic,provider=OrganizationFixtureProvider(),actor_context=actor,
        harvest=lambda r:[i.item_id for i in r.semantic_candidate.items if i.kind!='unknown'])
    candidate=wiki.semantic_state()['candidates'][proposal['proposal']['candidate_id']]
    semantic.evaluate(candidate['candidate_id'],actor_origin='independent_evaluator')
    semantic.record_external_evaluation_receipt(receipt=_semantic_receipt(wiki,candidate),actor_origin='independent_evaluator')
    version=semantic.decide(candidate['candidate_id'],decision='ACCEPTED',actor_origin='manager_acceptance',reason_code='reviewed',authority_receipt=_owner_receipt(wiki,candidate))['version_id']
    semantic.activate(version,actor_origin='manager_acceptance',authority_receipt=_version_receipt(wiki,version,candidate,action='ACTIVATE',expected_head=None))
    actor['approved_model_egress_version_ids']=[version]
    return session,semantic,actor,source,version


def answer_provider(monkeypatch,semantic,*,bad=None,source=None):
    relation=semantic.resolve_relations('市场部',actor_origin='catalyst_deterministic')['relations'][0]['meaning_id']
    def transport(url,headers,body):
        payload=json.loads(body)
        context=json.loads(payload['messages'][-1]['content'])
        assert context['relations']['version_id']
        assert context['relations']['relations'][0]['meaning_id']==relation
        item=dict(text='市场部向运营部移交复核。',relation_ids=[relation])
        if bad=='citation':item['relation_ids']=['invented']
        if bad=='missing_citation':item['relation_ids']=[]
        if bad=='extra':item['approved']=True
        if bad=='changed':next(source.parent.rglob('*.md')).write_text('派生证据包发生变化。',encoding='utf-8')
        text=json.dumps(dict(sentences=[item],unknowns=['审批权和未关联条件仍待确认。']),ensure_ascii=False)
        return 200,response(content=text)
    return provider(monkeypatch,task(input_token_limit=200000),transport)


@pytest.mark.parametrize('backend',['json','sqlite'])
def test_query_to_explanation_uses_real_accepted_wiki_version(tmp_path,monkeypatch,backend):
    session,semantic,actor,source,version=accepted(tmp_path,backend)
    governed,seen=answer_provider(monkeypatch,semantic)
    result=session.explain_enterprise_relations('市场部','请用普通中文解释部门移交关系',semantic=semantic,provider=governed,actor_context=actor,allow_test_scope=True)
    assert result['version_id']==version
    assert result['authority_class']=='test_only'
    assert result['semantic_quality']=='NOT_EVALUATED'
    assert '市场部向运营部' in result['answer']
    assert result['citations'] and result['unknowns']
    assert len(seen)==1 and governed.budget_snapshot['attempts']==1
    assert any(e.get('span_name')=='harness.explain_enterprise_relations' for e in semantic.recorder.store.inspect_run(semantic.recorder.run_id)['events'])


@pytest.mark.parametrize('bad',['citation','missing_citation','extra','changed'])
def test_invalid_citation_or_changed_source_fails_closed(tmp_path,monkeypatch,bad):
    session,semantic,actor,source,_=accepted(tmp_path)
    governed,seen=answer_provider(monkeypatch,semantic,bad=bad,source=source)
    with pytest.raises(WorkbenchError):
        session.explain_enterprise_relations('市场部','解释关系',semantic=semantic,provider=governed,actor_context=actor,allow_test_scope=True)
    assert len(seen)==1


@pytest.mark.parametrize('denial',['scope','permission','test_scope','no_relation','ungoverned','model_permission','egress','no_authority'])
def test_refusal_precedes_model_dispatch(tmp_path,monkeypatch,denial):
    session,semantic,actor,source,_=accepted(tmp_path)
    governed,seen=answer_provider(monkeypatch,semantic)
    if denial=='scope':actor['readable_scope_ids']=[]
    if denial=='permission':actor['permissions']=[]
    if denial=='model_permission':actor['permissions']=['knowledge.read']
    if denial=='egress':actor['approved_model_egress_version_ids']=[]
    if denial=='no_authority':
        original_state=semantic.wiki.semantic_state
        def unknown_authority():
            state=original_state()
            state['accepted_versions'][state['active_version_id']]['authority_class']=None
            return state
        monkeypatch.setattr(semantic.wiki,'semantic_state',unknown_authority)
    query='不存在的部门' if denial=='no_relation' else '市场部'
    with pytest.raises(WorkbenchError):
        session.explain_enterprise_relations(query,'解释关系',semantic=semantic,
            provider=OrganizationFixtureProvider() if denial=='ungoverned' else governed,
            actor_context=actor,allow_test_scope=denial!='test_scope')
    assert seen==[]


def test_original_change_does_not_rewrite_frozen_accepted_evidence(tmp_path,monkeypatch):
    session,semantic,actor,source,version=accepted(tmp_path)
    source.write_text('新版本原件，不得改写既有已接纳快照。',encoding='utf-8')
    governed,seen=answer_provider(monkeypatch,semantic)
    result=session.explain_enterprise_relations('市场部','解释已有快照中的关系',semantic=semantic,
        provider=governed,actor_context=actor,allow_test_scope=True)
    assert result['version_id']==version and len(seen)==1
