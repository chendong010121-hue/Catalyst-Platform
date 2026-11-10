from dataclasses import asdict
import json
import pytest
from agent_runtime.contracts import Message, ModelRequest
from catalyst_platform.llm_controls import ModelTask, TaskBudget, input_token_envelope
from catalyst_platform.understand_only import UnderstandPort, UnderstandingRequest

def test_compact_source_reference_is_lossless(tmp_path):
    source=tmp_path/'table.md'
    original='部门|职责|合并单元格 A1:B2\n甲部|登记；乙部同名但身份未明\n'
    source.write_text(original,encoding='utf-8')
    class Captured(Exception): pass
    class Capture:
        def request(self,request):
            self.request_value=request
            raise Captured()
    provider=Capture()
    with pytest.raises(Captured):
        UnderstandPort().understand(UnderstandingRequest('compact','企业语义',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',requested_depth='semantic',budget_steps=16),source_root=tmp_path,semantic_provider=provider)
    payload=json.loads(provider.request_value.messages[-1].content)
    assert [r['quote'] for r in payload['evidence']]==original.splitlines()
    assert [r['locator'] for r in payload['evidence']]==['line:1','line:2']
    for row in payload['evidence']:
        assert set(row)=={'evidence_id','s','locator','quote'}
        assert payload['sources'][row['s']]['relative_path']=='table.md'
        assert payload['sources'][row['s']]['source_sha256']
        assert payload['sources'][row['s']]['source_id']
    assert 'using s ' in provider.request_value.messages[0].content

@pytest.mark.parametrize('margin',[1,0,-1],ids=['below','exact','above'])
def test_p0_conservative_input_boundary(margin):
    req=ModelRequest(messages=(Message(role='user',content='中文表格 A1:B2'),),parameters={'max_tokens':4096})
    envelope=input_token_envelope(json.dumps(asdict(req),ensure_ascii=False))
    task=ModelTask('boundary','deepseek','deepseek-flash',1,'10',envelope+margin,4096,'2','8','0.04','OFFLINE_ONLY')
    budget=TaskBudget(task)
    if margin<0:
        with pytest.raises(Exception) as exc:budget.prepare(req)
        assert exc.value.public_code=='llm_input_limit'
    else:assert budget.prepare(req)==req
    assert budget.snapshot['attempts']==0

@pytest.mark.parametrize('fault',['length','missing_meaning','incomplete_json'])
def test_output_protocol_fail_closed(tmp_path,fault):
    from agent_runtime.contracts import ModelResponse
    source=tmp_path/'original.txt';source.write_text('甲组向乙组移交事项。',encoding='utf-8')
    class Invalid:
        def request(self,request):
            evidence=json.loads(request.messages[-1].content)['evidence'][0]['evidence_id']
            row=dict(kind='entity',key='a',meaning='甲组',evidence_class='SOURCE_DIRECT',evidence_refs=[evidence])
            if fault=='missing_meaning':row.pop('meaning')

            items=[row]
            content=json.dumps({'items':items})
            if fault=='incomplete_json':content=content[:-1]
            return ModelResponse(content=content,finish_reason='length' if fault=='length' else 'stop')
    with pytest.raises((ValueError,KeyError)):
        UnderstandPort().understand(UnderstandingRequest('invalid','企业语义',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',requested_depth='semantic',budget_steps=16),source_root=tmp_path,semantic_provider=Invalid())

def test_row_citing_evidence_never_supplied_is_dropped_not_the_card(tmp_path):
    from agent_runtime.contracts import ModelResponse
    source=tmp_path/'original.txt';source.write_text('甲组向乙组移交事项。',encoding='utf-8')
    class Unbound:
        def request(self,request):
            evidence=json.loads(request.messages[-1].content)['evidence'][0]['evidence_id']
            bound=dict(kind='entity',key='a',meaning='甲组',evidence_class='SOURCE_DIRECT',evidence_refs=[evidence])
            unbound=dict(kind='entity',key='b',meaning='乙组',evidence_class='SOURCE_DIRECT',evidence_refs=['not_supplied'])
            return ModelResponse(content=json.dumps({'items':[bound,unbound]}),finish_reason='stop')
    result=UnderstandPort().understand(UnderstandingRequest('invalid','企业语义',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',requested_depth='semantic',budget_steps=16),source_root=tmp_path,semantic_provider=Unbound())
    # Only the row that cites evidence the answer never received goes; the card keeps the rest.
    keys={i.key for i in result.semantic_candidate.items if i.kind=='entity'}
    assert keys=={'a'}
    assert result.producer_attribution['dropped_invalid_items']=={'evidence_ref_not_supplied':1}
    assert result.producer_attribution['dropped_invalid_item_keys']==[{'item_key':'b','rule':'evidence_ref_not_supplied'}]

def test_relation_with_an_undeclared_endpoint_is_dropped_and_counted(tmp_path):
    from agent_runtime.contracts import ModelResponse
    source=tmp_path/'original.txt';source.write_text('甲组向乙组移交事项。',encoding='utf-8')
    class Dangling:
        def request(self,request):
            evidence=json.loads(request.messages[-1].content)['evidence'][0]['evidence_id']
            row=dict(kind='entity',key='a',meaning='甲组',evidence_class='SOURCE_DIRECT',evidence_refs=[evidence])
            edge=dict(kind='relation',key='r',meaning='移交',subject='a',predicate='hands_to',object='absent',evidence_class='SOURCE_DIRECT',evidence_refs=[evidence])
            return ModelResponse(content=json.dumps({'items':[row,edge]}),finish_reason='stop')
    result=UnderstandPort().understand(UnderstandingRequest('invalid','企业语义',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',requested_depth='semantic',budget_steps=16),source_root=tmp_path,semantic_provider=Dangling())
    assert [i.key for i in result.semantic_candidate.items if i.kind=='relation']==[]
    assert result.producer_attribution['dropped_relation_count']==1
    assert result.producer_attribution['dropped_relations']==[{'item_key':'r','rule':'relation_endpoint_not_declared'}]
    assert 'a' in {i.key for i in result.semantic_candidate.items}

def _evidence_packet(quote, rows=366):
    payload=json.dumps(dict(sources={'s1':{'relative_path':'x.pptx','source_sha256':'a'*64}},
        evidence=[dict(evidence_id='ev_%024x'%i,s='s1',locator='ppt/slides/slide%d.xml#text:%d'%(i%14+1,i),quote=quote(i)) for i in range(rows)],
        warnings=[]),ensure_ascii=False)
    return ModelRequest(messages=(Message(role='system',content='M'*5000),Message(role='user',content=payload)),
        parameters={'max_tokens':4096,'response_format':{'type':'json_object'}})

def test_cjk_evidence_packet_that_fits_the_declared_limit_is_admitted():
    # The shape of the packet the live P1 run refused: 366 rows, ~3k Chinese characters
    # carried by 50KB of JSON scaffolding.
    req=_evidence_packet(lambda i:'第%d条职责由综合办公室按工作性质划分到岗位'%i)
    text=json.dumps(asdict(req),ensure_ascii=False)
    assert len(text.encode('utf-8'))>50000
    assert len(text.encode('utf-8'))*2+1024>32000        # the old per-byte envelope refused this
    assert input_token_envelope(text)<32000               # the content-aware bound admits it
    task=ModelTask('cjk','deepseek','deepseek-flash',1,'10',32000,4096,'2','8','0.04','OFFLINE_ONLY')
    assert TaskBudget(task).prepare(req)==req

def test_ascii_packet_beyond_the_declared_limit_is_still_refused():
    req=_evidence_packet(lambda i:'row %d '%i+'a'*180)
    assert input_token_envelope(json.dumps(asdict(req),ensure_ascii=False))>32000
    task=ModelTask('ascii','deepseek','deepseek-flash',1,'10',32000,4096,'2','8','0.04','OFFLINE_ONLY')
    with pytest.raises(Exception) as exc:TaskBudget(task).prepare(req)
    assert exc.value.public_code=='llm_input_limit'

def test_reported_usage_above_the_declaration_still_locks_the_task():
    from agent_runtime.contracts import ModelResponse,ModelUsage
    req=ModelRequest(messages=(Message(role='user',content='中文表格 A1:B2'),),parameters={'max_tokens':4096})
    limit=input_token_envelope(json.dumps(asdict(req),ensure_ascii=False))
    task=ModelTask('lock','deepseek','deepseek-flash',1,'10',limit,4096,'2','8','0.04','OFFLINE_ONLY')
    budget=TaskBudget(task);budget.prepare(req);budget.dispatch()
    with pytest.raises(Exception) as exc:budget.finish(ModelResponse(content='{}',finish_reason='stop',usage=ModelUsage(limit+1,10)),req)
    assert exc.value.public_code=='llm_usage_bound_exceeded'
    assert budget.settled is False
