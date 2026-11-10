"""Original Runtime source approval/restart regression; synthetic transport only."""
from pathlib import Path
from tests.project_understand.test_project_runtime import setup,script,offline
from tests.project_live.test_daily_workflow_boundary import recorder
from tests.test_daily_connection import connect
from tests.project_live.test_project_acceptance import configured
from catalyst_platform.project_understand import source_manifest,digest


def test_daily_project_explicit_approval_runs_original_runtime_and_changed_source_stops(tmp_path,offline):
    host,root,calls,_flow=configured(tmp_path)
    connect(host)
    # Provider retains its synthetic injected transport; admission sees the real-path flag.
    host.settings.transport_override=None
    approved=digest(source_manifest(root))
    spec=dict(root=str(root),object_type='agent',daily_read_approval_sha256=approved,approved_manifest_sha256=approved)
    result=host.analyze_project(spec,'Explain this Agent dependency',2,recorder(host))
    assert result['state']=='PROJECT_ANALYZED',result
    analysis=result['result']['output']['project_analysis']
    assert analysis['tool_executions']=={'project_inspect':1,'project_expand_evidence':1,'project_submit_analysis':1}
    assert len(calls)==4
    assert result['candidate_id'] is None and result['version_id'] is None
    assert result['external_calls']==0
    assert digest(source_manifest(root))==approved
    assert not host.settings.allow_project_read
    assert host.settings.task.execution_profile=='daily' and host.settings.task.max_requests is None
    (root/'worker.py').write_text('def run():\n    return "changed"\n',encoding='utf-8')
    blocked=host.analyze_project(spec,'Explain this Agent dependency',2,recorder(host))
    assert blocked['state']=='BLOCKED'
    assert blocked['error']['code']=='PROJECT_SOURCE_APPROVAL_CHANGED'
    assert len(calls)==4



def test_first_project_task_after_restart_restores_only_on_task(tmp_path,offline):
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from catalyst_platform.workspace_credentials import WorkspaceCredential
    from tests.test_workspace_credentials import FakeProtection
    host,root,calls,_flow=configured(tmp_path)
    transport=host.settings.transport_override
    protection=FakeProtection()
    host.settings.credential_store=WorkspaceCredential(host.app,protector=protection)
    host.settings.connect(dict(provider_id='deepseek',model='deepseek-flash',api_key='OFFLINE-REVIEW-KEY',remember=True))
    restarted=WorkspaceUserSession(host.workspace)
    restarted.settings.credential_store=WorkspaceCredential(restarted.app,protector=protection)
    restarted.settings.transport_override=transport
    assert restarted.settings.snapshot()['connection_mode']=='daily'
    assert restarted.settings.provider is None and protection.reads==0
    approved=digest(source_manifest(root))
    spec=dict(root=str(root),object_type='agent',daily_read_approval_sha256=approved,approved_manifest_sha256=approved)
    result=restarted.analyze_project(spec,'Explain this Agent dependency',2,recorder(restarted))
    assert result['state']=='PROJECT_ANALYZED',result
    assert len(calls)==4 and protection.reads==1
    assert result['external_calls']==0
    assert result['candidate_id'] is None and result['version_id'] is None
    assert not restarted.settings.allow_project_read
