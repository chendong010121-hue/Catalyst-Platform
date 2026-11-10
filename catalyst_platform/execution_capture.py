"""Neutral capture of the existing Product/Runtime, never another executor.

P0 owns model accounting; Host owns durable HTTP dispatch; method adapters own
business projections. Artifacts here are private local observations only.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from agent_runtime.contracts import Act, Success, Failure, Deny


def _bytes(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def _digest(raw):return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ExecutionCaptureResult:
    """Common receipt; payload qualification is explicit, not semantic truth."""
    _receipt: dict[str,Any]
    _root: Path
    provider_error: BaseException | None = field(default=None,repr=False,compare=False)

    def summary(self):return json.loads(json.dumps(self._receipt))

    def _read_json(self,key):
        ref=self._receipt['artifacts'].get(key)
        if ref is None:raise ValueError('capture has no consumable '+key)
        path=(self._root/ref['path']).resolve()
        if not path.is_relative_to(self._root):raise ValueError('capture artifact outside artifact root')
        raw=path.read_bytes()
        if _digest(raw)!=ref['sha256']:raise ValueError('capture artifact hash mismatch')
        return json.loads(raw)

    def payload(self):return self._read_json('payload')


class _ArtifactWriter:
    def __init__(self,root):self.root=root
    def write(self,name,raw):
        path=self.root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        return {'path':name,'sha256':_digest(raw),'bytes':len(raw)}
    def json(self,name,value):return self.write(name,_bytes(value))


class _ExecutionCapture:
    """Per-call observation state; existing Policy authorizes every action."""
    result_class=ExecutionCaptureResult
    schema='catalyst.execution_capture.v1'
    typed_basis='CAPABILITY_OUTPUT_SCHEMA'
    boundary='AFTER_TOOL_BEFORE_FINAL_ANSWER'

    def __init__(self):
        self.attempt_finished=False
        self.payload_value=None
        self.typed_capture=False
        self.failure=None
        self.validation_rejected=False
        self.execution_attempted=False

    def observe(self,history):
        self.execution_attempted = self.execution_attempted or any(
            isinstance(step.decision,Act) and step.execution_id is not None for step in history)
        if self.attempt_finished:return
        for step in history:
            if not isinstance(step.decision,Act):continue
            if isinstance(step.observation,Success):
                self.payload_value=step.observation.data
                self.typed_capture=True
            if isinstance(step.observation,(Success,Failure)) or isinstance(step.policy_verdict,Deny):
                self.attempt_finished=True
                return

    def project(self,writer,calls,artifacts):return {}

    def persist(self,root,calls,run,provider,recorder):
        writer=_ArtifactWriter(root);artifacts={};safe_calls=[]
        for index,call in enumerate(calls):
            request,response,error=call['request'],call['response'],call['error']
            prefix=f'calls/{index+1:03d}'
            request_ref=writer.json(prefix+'_request.json',asdict(request))
            response_ref=writer.json(prefix+'_response.json',asdict(response)) if response is not None else None
            safe_calls.append({'sequence':index+1,'dispatched':call['dispatched'],'request':request_ref,
                'response':response_ref,'error_type':type(error).__name__ if error else None,
                'error_code':getattr(error,'code',None) if error else None})
            if index==len(calls)-1 and response is not None:
                artifacts['raw_response']=response_ref
                if isinstance(response.content,str):artifacts['raw_content']=writer.write(prefix+'_content.raw',response.content.encode('utf-8'))
        if run is not None:
            artifacts['runtime_result']=writer.json('runtime_result.json',run.result.to_dict())
            artifacts['product_trace']=writer.json('product_trace.json',run.trace)
        if self.typed_capture:artifacts['payload']=writer.json('payload.json',self.payload_value)
        projected=self.project(writer,calls,artifacts)
        provider_error=next((c['error'] for c in reversed(calls) if c['error'] is not None),None)
        failure=provider_error or self.failure
        # An answer the output window cut is a rejected output, not a provider failure:
        # the transport did its job and the model wrote as far as it could.
        model_failure=provider_error is not None and getattr(provider_error,'code',None) not in {'llm_structured_output_invalid','llm_output_truncated'}
        if run is None:status='INTERRUPTED'
        elif model_failure:status='MODEL_FAILURE'
        elif self.validation_rejected:status='OUTPUT_REJECTED'
        elif run.result.status!='success':status='EXECUTION_FAILURE'
        else:status='CAPTURED' if self.typed_capture else 'NOT_EXECUTED'
        runtime_error=run.result.error if run is not None else None
        executed=True if self.execution_attempted else None if run is None or run.result.status=='unresolved' else False
        position=self.boundary if executed else 'EXECUTION_NOT_CONFIRMED' if executed is None else 'NO_METHOD_EXECUTION'
        parameters_hash=_digest(_bytes({'provider_id':provider.provider_id,'model':provider.model,
            'parameters':dict(calls[-1]['request'].parameters)})) if calls else None
        receipt={'schema':self.schema,'status':status,'typed_capture':self.typed_capture,
            'typed_basis':self.typed_basis if self.typed_capture else None,'semantic_quality':'NOT_EVALUATED',
            'attempt_finished':self.attempt_finished,'execution_attempted':executed,'boundary':position,
            'authority':'CANDIDATE_ONLY','candidate_id':None,'version_id':None,
            'runtime_terminal':run.result.status if run is not None else 'not_completed',
            'failure_stage':('MODEL' if model_failure else 'VALIDATION' if self.validation_rejected else 'EXECUTION') if status not in ('CAPTURED','NOT_EXECUTED') else None,
            'failure_type':type(failure).__name__ if failure else None,
            'failure_code':getattr(failure,'code',None) or (runtime_error or {}).get('code'),
            'source_payload_sha256':None,'parameters_sha256':parameters_hash,
            'trace':{'run_id':recorder.run_id,'request_id':recorder.request_id,'session_id':recorder.session_id,'invocation_id':recorder.invocation_id},
            'budget':provider.budget_snapshot,'calls':safe_calls,'artifacts':artifacts,**projected}
        writer.json('CAPTURE_RECEIPT.json',receipt)
        return self.result_class(receipt,root,provider_error)
