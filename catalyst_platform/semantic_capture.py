"""Semantic projection adapter over the shared execution capture interface."""
import json
from .execution_capture import ExecutionCaptureResult, _ExecutionCapture, _bytes, _digest


class SemanticCaptureResult(ExecutionCaptureResult):
    """Compatibility semantic view; common receipt/payload mechanics are shared."""
    def observation(self):return self._read_json('observation')


class _CaptureBoundary(_ExecutionCapture):
    result_class=SemanticCaptureResult
    schema='catalyst.semantic_capture.v1'
    typed_basis='UNDERSTAND_TYPED_VALIDATOR'
    boundary='BEFORE_HARVEST'

    def __init__(self):
        super().__init__()
        self.understanding=None

    def accept(self,result):
        self.understanding=result.to_dict()
        self.payload_value=self.understanding
        self.typed_capture=True
        self.attempt_finished=True

    def reject(self,error):
        self.failure=error
        self.validation_rejected=True
        self.attempt_finished=True

    def tool_summary(self):
        return {'status':'CAPTURED_BEFORE_HARVEST','authority':'CANDIDATE_ONLY',
                'candidate_id':None,'version_id':None,'typed_capture':self.typed_capture}

    def project(self,writer,calls,artifacts):
        extraction=next((c for c in reversed(calls) if c['request'].parameters.get('response_format')=={'type':'json_object'}),None)
        projected={}
        if extraction is not None:
            request,response=extraction['request'],extraction['response']
            payload=json.loads(request.messages[-1].content)
            projected={'source_payload_sha256':_digest(_bytes(payload))}
            if response is not None and isinstance(response.content,str):
                try:raw=json.loads(response.content)
                except ValueError:raw=None
                if isinstance(raw,dict) and isinstance(raw.get('items'),list):
                    evidence,manifest=[],{}
                    for row in payload['evidence']:
                        source=payload['sources'][row['s']]['source_sha256'];span=_digest(row['quote'].encode('utf-8'))
                        evidence.append(dict(row,source_sha256=source,span_sha256=span))
                        manifest.setdefault(source,{})[row['locator']]=span
                    artifacts['observation']=writer.json('observation.json',{'items':raw['items'],'evidence':evidence,'source_manifest':manifest})
        if self.understanding is not None:artifacts['understanding']=writer.json('understanding.json',self.understanding)
        return projected
