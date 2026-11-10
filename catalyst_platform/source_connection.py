"""One bounded source consumer over existing Wiki/Plugin/Catalog/Runtime.

No recipe engine, Agent composition, search duplicate or semantic Authority.
"""
from __future__ import annotations

import hashlib
import uuid

from agent_runtime.contracts import CapabilityDescriptor,Success,Failure
from .plugin_composition import PluginComposer,PluginDefinition,PluginEffect
from .observability import RunRecorder
from .trace_log import JsonlTraceStore

FIELDS=('scope_id','source_id','revision','locator','content_sha256')
REFERENCE_SCHEMA={'type':'object','properties':{x:{'type':'string'} for x in FIELDS},
                  'required':list(FIELDS),'additionalProperties':False}


class SourceReadService:
    interface_version='1'
    def __init__(self,wiki):self.wiki=wiki

    def _check_scope(self,enterprise):
        if enterprise!=self.wiki.enterprise_id:raise ValueError('source_scope_denied')

    def _reference(self,snapshot):
        source=snapshot['source'];content=snapshot['content'];encoded=content.encode('utf-8')
        if snapshot['current_revision']!=source['revision']:raise ValueError('source_revision_drift')
        if not encoded or len(encoded)>65536:raise ValueError('source_read_bound')
        return dict(scope_id=self.wiki.scope_id,source_id=source['source_id'],revision=source['revision'],
                    locator='lines:1-'+str(len(content.splitlines())),content_sha256=hashlib.sha256(encoded).hexdigest())

    def search(self,query,enterprise):
        self._check_scope(enterprise)
        if not isinstance(query,str) or not 1<=len(query.strip())<=256:raise ValueError('source_query_invalid')
        rows=self.wiki.read_knowledge(query,mode='source_discovery',limit=10)['documents']
        # This legacy whole-text read contract only accepts Markdown snapshots.
        # Native sources remain discoverable as metadata through Wiki, but must
        # not make unrelated Markdown reads fail or masquerade as UTF-8 text.
        native=[row for row in rows[:10] if str(row.get('relative_path','')).casefold().endswith(('.docx','.pptx','.pdf'))]
        compatible=[row for row in rows[:10] if row not in native]
        result={'references':[self._reference(self.wiki.source_snapshot(row['source_id'])) for row in compatible],
                'authority':'SOURCE_DOCUMENT_NOT_ACCEPTED_ONTOLOGY','truncated':len(rows)>10}
        if native:
            result['native_sources_not_readable_by_this_interface']=len(native)
        return result

    def read(self,reference,enterprise):
        self._check_scope(enterprise)
        if (not isinstance(reference,dict) or set(reference)!=set(FIELDS)
            or any(not isinstance(reference[k],str) or not 1<=len(reference[k])<=256 for k in FIELDS)
            or reference['scope_id']!=self.wiki.scope_id):raise ValueError('source_reference_invalid')
        snapshot=self.wiki.source_snapshot(reference['source_id'])
        if reference!=self._reference(snapshot):raise ValueError('source_reference_identity_mismatch')
        return {'reference':dict(reference),'content':snapshot['content'],
                'authority':'SOURCE_DOCUMENT_NOT_ACCEPTED_ONTOLOGY'}


class SourceReadCapability:
    id='source_read'
    def __init__(self,service):self.service=service
    def describe(self):
        return CapabilityDescriptor(id=self.id,name='Read an exact source reference',
          description='Read a bounded already-staged original by exact scope/revision/locator/hash; no ontology acceptance.',
          input_schema={'type':'object','properties':{'reference':REFERENCE_SCHEMA},'required':['reference'],'additionalProperties':False},
          output_schema={'type':'object'})
    def invoke(self,parameters,context):
        try:return Success(self.service.read(parameters['reference'],context.enterprise_context.get('id')))
        except (KeyError,ValueError,OSError,RuntimeError) as exc:return Failure('source_read_refused:'+type(exc).__name__)


def build_source_connection(workspace,wiki):
    """Explicit trusted assembly: reuse wiki_search, register only source_read."""
    from .workbench import CatalystWorkbench
    service=SourceReadService(wiki)
    app=CatalystWorkbench(workspace,wiki.roots,wiki_search_adapter=service.search,
                         enterprise_source_allowlist={wiki.enterprise_id:wiki.roots})
    def apply(context):
        bound=context.require('source.read')
        if bound.interface_version!='1':raise ValueError('source_interface_version')
        catalog=context.require('capability.catalog')
        catalog.register(SourceReadCapability(bound),capability_version='1.0.0',execution={'side_effect':'none'},
          metadata={'component_id':'source-reference-reader','component_version':'0.1.0',
                    'llm_visibility':'explicit','model_policy':{'mode':'workspace_scoped_query','max_calls':1}})
        return PluginEffect(services={'source.reader.action':bound},revoke=lambda:catalog.deactivate('source_read','1.0.0'))
    composer=PluginComposer(definitions=(PluginDefinition('source-reference-reader','0.1.0',('source.reader.action',),
      ('source.read','capability.catalog'),apply),),profiles={'source-read':('source-reference-reader',)},
      host_services={'source.read':service,'capability.catalog':app._catalog})
    composer.compose('source-read')
    return app,service,composer


def run_source_connection(app,service,query,source_id):
    """Fixed two steps; explicit source selection, no fallback/retry/staging."""
    if app.wiki_search_adapter!=service.search:raise ValueError('source_consumer_binding_mismatch')
    session=app.new_session(domain={'id':'local'},enterprise={'id':service.wiki.enterprise_id})
    runs=[]
    def invoke(cap,parameters):
        run_id='run_'+uuid.uuid4().hex
        recorder=RunRecorder(JsonlTraceStore(app.workspace),run_id=run_id,request_id='req_'+uuid.uuid4().hex,
            invocation_id='inv_'+uuid.uuid4().hex,trace_id=uuid.uuid4().hex)
        recorder.start(request_kind='source_connection',component='SourceConnection',actor='local_host')
        try:
            run=session.invoke(cap,'1.0.0',parameters,recorder=recorder)
            runs.append({'run_id':run_id,'capability_id':cap,'version':'1.0.0','status':run.result.status})
            recorder.finish(run.result.status,external_calls=0)
            if run.result.status!='success':raise ValueError('source_connection_step_failed')
            return run.result.output
        except BaseException:
            if not runs or runs[-1]['run_id']!=run_id:recorder.finish('failure',external_calls=0)
            raise
    first=invoke('wiki_search',{'query':query})
    matches=[ref for ref in first.get('references',[]) if ref['source_id']==source_id]
    if len(matches)!=1:raise ValueError('explicit_source_selection_unresolved')
    second=invoke('source_read',{'reference':matches[0]})
    return {'status':'success',**second,'runs':runs,'external_api_requests':0,
            'semantic_quality':'NOT_EVALUATED','composition':'FIXED_TWO_ACTION_CONNECTION_NOT_AGENT'}
