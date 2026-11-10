"""Thin real-entry adapters; never a model client or new Agent Loop."""
import dataclasses
import hashlib
import json
import uuid
from pathlib import Path
from .observability import RunRecorder
from .trace_log import JsonlTraceStore
from .workbench import CatalystWorkbench
from .__main__ import _register_file_title

def _reference(path,role):
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'role':role}

def _file_title_run(public,workspace,method_variant="current"):
    """Existing CLI registration -> HarnessSession.invoke -> actual Runtime/tool."""
    workspace=Path(workspace);source=workspace/public.get('filename','input.md')
    if source.resolve().parent!=workspace.resolve():raise ValueError('Only one bounded input filename')
    source.write_bytes(public['content'].encode('utf-8'))
    app=CatalystWorkbench(workspace,[workspace])
    version='1.0.0'
    if method_variant=='current':_register_file_title(app,lambda event:None)
    else:
        from .file_title import FileTitleCapability
        cls={'trailing_fault':_TrailingHashFault,'fence_fault':_FenceFault}[method_variant]
        capability=cls(workspace=workspace,event_sink=lambda event:None)
        version={'trailing_fault':'0.0.1','fence_fault':'0.0.2'}[method_variant]
        app.register_capability(capability.describe(),capability_version=version,execution={'side_effect':'none'},implementation=capability,metadata={'model_policy':{'mode':'selected_file_path','path_parameter':'path','max_calls':1},'llm_visibility':'explicit'})
    session=app.new_session(domain={'id':'local'},enterprise={'id':'eval-local'})
    recorder=RunRecorder(JsonlTraceStore(workspace),run_id='eval-'+uuid.uuid4().hex,request_id='request-'+uuid.uuid4().hex,invocation_id='inv-'+uuid.uuid4().hex)
    recorder.start(request_kind='eval.local.file_title',input_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    run=session.invoke('read_file_title',version,{'path':str(source)},recorder=recorder)
    recorder.finish(run.result.status)
    events=JsonlTraceStore(workspace).inspect_run(recorder.run_id)['events']
    trace=workspace/'r4.jsonl';trace.write_text(''.join(json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for e in events),encoding='utf-8')
    runtime_files=list((workspace/'.catalyst/sessions').glob('*.json'))
    return {'execution_kind':'PRODUCT_RUNTIME','run_id':recorder.run_id,'capability_id':'read_file_title','status':run.result.status,'output':run.result.output,'error':run.result.error,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'evidence_refs':[_reference(trace,'r4'),_reference(source,'source')]+[_reference(p,'runtime_state') for p in runtime_files]}


def ontology_entry(public,workspace):
    """Actual deterministic Understand + existing candidate-only Wiki queries.

    No LLM/Provider is used. This does not prove natural-language extraction.
    """
    from .understand_only import UnderstandPort, UnderstandingRequest
    from .understand_wiki import UnderstandWikiAdapter
    from .semantic_wiki import SemanticWiki
    from .wiki import ProjectWiki
    workspace=Path(workspace);sources=workspace/'sources';sources.mkdir()
    source=sources/'source.md';source.write_bytes(public['source_text'].encode('utf-8'))
    recorder=RunRecorder(JsonlTraceStore(workspace),run_id='eval-'+uuid.uuid4().hex,request_id='request-'+uuid.uuid4().hex,invocation_id='inv-'+uuid.uuid4().hex,event_schema_version='1.6')
    recorder.start(request_kind='eval.local.ontology',input_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    wiki=ProjectWiki(workspace,[sources],enterprise_id='eval-local',project_id='ontology',backend=public.get('backend','json'));semantic=SemanticWiki(wiki,recorder=recorder)
    result=UnderstandPort().understand(UnderstandingRequest(recorder.request_id,'企业语义候选',source_refs=(source,),intent='KNOWLEDGE_PROPOSE',scope_id=wiki.scope_id,requested_depth='semantic',budget_steps=16),source_root=sources,recorder=recorder)
    adapter=UnderstandWikiAdapter(wiki,semantic,sources);candidate=adapter.submit(result.to_dict(),declared_scope_id=wiki.scope_id)
    graph=adapter.candidate_graph(candidate['candidate_id'])
    queries=[{'entity':entity,'result':adapter.relations(candidate['candidate_id'],entity)} for entity in public.get('entity_queries',[])]
    state=wiki.semantic_state();assert state['active_version_id'] is None
    cold=ProjectWiki(workspace,[sources],enterprise_id='eval-local',project_id='ontology',backend=public.get('backend','json'));assert cold.semantic_state()==state
    recorder.finish('success')
    events=JsonlTraceStore(workspace).inspect_run(recorder.run_id)['events'];trace=workspace/'r4.jsonl';trace.write_text(''.join(json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for e in events),encoding='utf-8')
    resultfile=workspace/'understanding.json';resultfile.write_text(json.dumps(result.to_dict(),ensure_ascii=False,sort_keys=True),encoding='utf-8')
    return {'execution_kind':'PRODUCT_UNDERSTAND','run_id':recorder.run_id,'items':[dataclasses.asdict(x) for x in result.semantic_candidate.items],'evidence':[dataclasses.asdict(x) for x in result.evidence_refs],'queries':queries,'graph_authority':graph.get('authority'),'candidate_id':candidate['candidate_id'],'active_version_id':None,'cold_read_equal':True,'backend':public.get('backend','json'),'evidence_refs':[_reference(trace,'r4'),_reference(resultfile,'understanding'),_reference(source,'source')]}


# Fault-injected method demos remain isolated from production registration.
# They invoke inherited real file reading through the existing Runtime.
from .file_title import FileTitleCapability
class _TrailingHashFault(FileTitleCapability):
    @staticmethod
    def _first_markdown_h1(lines):
        import re
        result=FileTitleCapability._first_markdown_h1(lines)
        if result is None:return None
        number,line,title=result
        return number,line,re.sub(r'^ {0,3}#\s+','',line).strip()

class _FenceFault(FileTitleCapability):
    @staticmethod
    def _first_markdown_h1(lines):
        import re
        for number,line in enumerate(lines,1):
            match=re.match(r'^ {0,3}#(?!#)\s+(.+)',line)
            if match:return number,line,re.sub(r'[ \t]+#+$','',match.group(1)).strip()
        return None

def file_title_entry(public,workspace):
    return _file_title_run(public,workspace)

def file_title_parent_entry(public,workspace):
    return _file_title_run(public,workspace,'trailing_fault')

def file_title_critical_entry(public,workspace):
    return _file_title_run(public,workspace,'fence_fault')
