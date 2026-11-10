import base64,json
import pytest
from catalyst_platform.workspace_session import WorkspaceUserSession

class FakeProtection:
    supported=True
    def __init__(self):self.reads=0
    def protect(self,data,entropy):return b'OFFLINE-ONLY:'+base64.b64encode(data[::-1]+entropy[:8])
    def unprotect(self,data,entropy):
        self.reads+=1
        value=base64.b64decode(data.removeprefix(b'OFFLINE-ONLY:'))
        if value[-8:]!=entropy[:8]:raise ValueError('wrong scope')
        return value[:-8][::-1]


def test_opt_in_store_is_encrypted_and_metadata_never_reads_secret(tmp_path):
    from catalyst_platform.workspace_credentials import WorkspaceCredential
    host=WorkspaceUserSession(tmp_path/'workspace');protection=FakeProtection()
    store=WorkspaceCredential(host.app,protector=protection)
    assert not store.available
    store.save('OFFLINE-SYNTHETIC-KEY')
    assert store.available and protection.reads==0
    assert b'OFFLINE-SYNTHETIC-KEY' not in store.path.read_bytes()
    reloaded=WorkspaceCredential(host.app,protector=protection)
    assert reloaded.load()=='OFFLINE-SYNTHETIC-KEY' and protection.reads==1
    reloaded.delete();assert not reloaded.available


def test_corrupt_store_never_falls_back_to_other_credentials(tmp_path):
    from catalyst_platform.workspace_credentials import WorkspaceCredential
    host=WorkspaceUserSession(tmp_path/'workspace');store=WorkspaceCredential(host.app,protector=FakeProtection())
    store.path.parent.mkdir(parents=True,exist_ok=True);store.path.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='saved_credential_unavailable'):store.load()


def test_windows_dpapi_synthetic_roundtrip(tmp_path):
    from catalyst_platform.workspace_credentials import WindowsDPAPI
    p=WindowsDPAPI()
    if not p.supported:pytest.skip('Windows DPAPI only')
    cipher=p.protect(b'OFFLINE-FAKE-NON-CREDENTIAL',b'test-scope')
    assert b'OFFLINE-FAKE-NON-CREDENTIAL' not in cipher
    assert p.unprotect(cipher,b'test-scope')==b'OFFLINE-FAKE-NON-CREDENTIAL'
    with pytest.raises(ValueError):p.unprotect(cipher,b'another-scope')
