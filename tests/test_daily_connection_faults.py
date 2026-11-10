"""Read-only review probes: only temporary synthetic workspaces and fake transport."""
import json
import pytest
from catalyst_platform.workspace_session import WorkspaceUserSession
from catalyst_platform.workspace_credentials import WorkspaceCredential
from tests.test_workspace_credentials import FakeProtection
from tests.test_workspace_model_settings import packet, run
from tests.project_understand.test_project_runtime import offline
from tests.test_daily_connection import connect


def test_rejected_connection_commit_does_not_publish_provider(tmp_path, offline, monkeypatch):
    host = WorkspaceUserSession(tmp_path/'daily')
    calls = []
    host.settings.transport_override = lambda *_: (calls.append(1) or (200, packet()))
    original = host.app._atomic_json
    def write(path, *args, **kwargs):
        if path.name == 'connection.json':
            raise OSError('SYNTHETIC_CONNECTION_PERSIST_FAILURE')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(host.app, '_atomic_json', write)
    with pytest.raises(OSError):
        connect(host)
    assert host.settings.provider is None, 'Rejected connect still publishes a usable daily provider'
    assert calls == []


def test_ephemeral_key_does_not_restore_a_different_saved_connection(tmp_path, offline):
    host = WorkspaceUserSession(tmp_path/'daily')
    protection = FakeProtection()
    host.settings.credential_store = WorkspaceCredential(host.app, protector=protection)
    host.settings.credential_store.save('OFFLINE-OLD-SYNTHETIC-KEY')
    host.settings.transport_override = lambda *_: (200, packet())
    connect(host)  # different explicitly supplied key, remember=False
    restarted = WorkspaceUserSession(host.workspace)
    restarted.settings.credential_store = WorkspaceCredential(restarted.app, protector=protection)
    restarted.settings.transport_override = lambda *_: (200, packet())
    restarted.settings.ensure_daily_connection()
    assert protection.reads == 0, 'Restart silently decrypts and selects the older saved key'
    assert restarted.settings.provider is None


def test_daily_cancel_can_resume_without_clearing_experiment_uncertainty(tmp_path, offline):
    host = WorkspaceUserSession(tmp_path/'daily')
    calls = []
    host.settings.transport_override = lambda *_: (calls.append(1) or (200, packet()))
    connect(host)
    host.settings.provider.cancel()
    assert run(host)['state'] == 'CHAT_COMPLETED'
    assert calls == [1]


def test_stale_daily_is_usable_but_experiment_remains_strict(tmp_path, offline, monkeypatch):
    import catalyst_platform.workspace_settings as settings
    from datetime import datetime, timezone, timedelta
    host = WorkspaceUserSession(tmp_path/'daily')
    host.settings.transport_override = lambda *_: (200, packet())
    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026,10,30,tzinfo=timezone.utc)
    monkeypatch.setattr(settings, 'datetime', Later)
    connect(host)
    assert host.settings.snapshot()['price_estimate_stale']
    assert run(host)['state'] == 'CHAT_COMPLETED'
    assert not host.settings.snapshot()['test_connection_available']


def test_late_preferences_failure_cannot_authorize_restart(tmp_path,offline,monkeypatch):
    host=WorkspaceUserSession(tmp_path/'daily');protection=FakeProtection()
    host.settings.credential_store=WorkspaceCredential(host.app,protector=protection)
    original=host.app._atomic_json
    def write(path,*args,**kwargs):
        if path.name=='model-preferences.json':raise OSError('SYNTHETIC_PREFERENCES_FAILURE')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(host.app,'_atomic_json',write)
    with pytest.raises(OSError):
        host.settings.connect(dict(provider_id='deepseek',model='deepseek-flash',api_key='OFFLINE-REJECTED-KEY',remember=True))
    assert host.settings.provider is None
    restarted=WorkspaceUserSession(host.workspace)
    restarted.settings.credential_store=WorkspaceCredential(restarted.app,protector=protection)
    restarted.settings.ensure_daily_connection()
    assert restarted.settings.provider is None and protection.reads==0


def test_changed_saved_ciphertext_never_restores_under_prior_approval(tmp_path,offline):
    host=WorkspaceUserSession(tmp_path/'daily');protection=FakeProtection()
    host.settings.credential_store=WorkspaceCredential(host.app,protector=protection)
    host.settings.connect(dict(provider_id='deepseek',model='deepseek-flash',api_key='OFFLINE-ORIGINAL-KEY',remember=True))
    host.settings.credential_store.save('OFFLINE-REPLACEMENT-KEY')
    restored=WorkspaceUserSession(host.workspace)
    restored.settings.credential_store=WorkspaceCredential(restored.app,protector=protection)
    with pytest.raises(ValueError,match='saved_connection_identity_changed'):restored.settings.ensure_daily_connection()
    assert protection.reads==0 and restored.settings.provider is None
