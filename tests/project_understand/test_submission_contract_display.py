import json
import pytest
from catalyst_platform.project_understand import ProjectUnderstandingRequest, ProjectAnalysisContext, validate_project_handoff, ProjectAnalysisError
from tests.project_understand.test_project_runtime import setup,offline
from tests.project_live.test_daily_workflow_boundary import recorder

def test_display_exact_submission_fields_types_and_host_only_request_id(tmp_path,offline):
    host,root=setup(tmp_path);rec=recorder(host)
    with host.app.components.acquire_method('project-understand') as method:
        ctx=ProjectAnalysisContext(host.session,ProjectUnderstandingRequest(rec.request_id,'inspect','skill',2),root,method,rec)
        text=ctx.initial_context()
        assert 'schema_version="project-understanding.v1"' in text
        assert 'requested_depth and achieved_depth must be JSON integers' in text
        assert 'Do not include request_id, max_depth or evaluation_refs' in text
        assert 'Host request metadata (not submission fields)' in text

def test_old_rejected_shape_still_rejected_without_repair():
    request=ProjectUnderstandingRequest('old-request','inspect','skill',2)
    bad={'request_id':'old-request','objective':'inspect','requested_depth':'D2','achieved_depth':'D1'}
    with pytest.raises(ProjectAnalysisError,match='project_handoff_fields'):
        validate_project_handoff(bad,request=request,manifest=[],evidence=[],source_reads=[])
