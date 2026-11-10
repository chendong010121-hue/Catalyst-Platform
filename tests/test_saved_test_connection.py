from catalyst_platform.workspace_credentials import WorkspaceCredential
from catalyst_platform.workspace_session import WorkspaceUserSession
from tests.test_workspace_credentials import FakeProtection
from tests.project_live.test_project_acceptance import qualification_clock
from tests.project_understand.test_project_runtime import offline
from tests.test_workspace_model_settings import packet


def test_saved_key_survives_restart_without_scope_or_secret_read(tmp_path,offline):
    host=WorkspaceUserSession(tmp_path/'workspace');protection=FakeProtection()
    host.settings.credential_store=WorkspaceCredential(host.app,protector=protection)
    host.settings.save_credential({'api_key':'OFFLINE-SYNTHETIC-KEY','confirmed':True})
    assert host.settings.provider is None
    restored=WorkspaceUserSession(host.workspace)
    restored.settings.credential_store=WorkspaceCredential(restored.app,protector=protection)
    assert restored.settings.snapshot()['saved_credential_available']
    assert restored.settings.snapshot()['test_connection_available']
    assert protection.reads==0 and restored.settings.provider is None
    child=WorkspaceUserSession(tmp_path/'test')
    restored.settings.transport_override=lambda *_:(200,packet())
    connected=restored.settings.configure_test_connection(child.app,dict(max_requests=2,budget_cny='1',max_output_tokens=1024))
    assert protection.reads==1 and connected.provider.budget_snapshot['attempts']==0
    assert restored.settings.provider is None
    restored.settings.disconnect()
    assert not restored.settings.snapshot()['test_connection_available']
    restored.settings.forget_credential({'confirmed':True})
    assert not restored.settings.snapshot()['saved_credential_available']
