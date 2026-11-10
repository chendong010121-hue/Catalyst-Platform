"""Small current-Windows-user DPAPI adapter; never searches external stores.

Availability is metadata only. Decryption is an explicit connect/confirmed-test
operation, never startup, GET, automatic resume, logging or credential discovery.
"""
import base64
import ctypes
import hashlib
import json
import os


class WindowsDPAPI:
    supported = os.name == 'nt'

    def _convert(self, data, entropy, decrypt):
        if not self.supported:
            raise ValueError('windows_protected_storage_unavailable')
        class Blob(ctypes.Structure):
            _fields_=[('size',ctypes.c_uint32),('data',ctypes.POINTER(ctypes.c_ubyte))]
        def blob(raw):
            buffer=ctypes.create_string_buffer(raw)
            return buffer,Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)))
        source,inp=blob(data);salt,ent=blob(entropy);out=Blob()
        crypto=ctypes.WinDLL('crypt32',use_last_error=True)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        operation=crypto.CryptUnprotectData if decrypt else crypto.CryptProtectData
        operation.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),
                            ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Blob)]
        operation.restype=ctypes.c_int
        kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
        try:
            if not operation(ctypes.byref(inp),None,ctypes.byref(ent),None,None,1,ctypes.byref(out)):
                raise ValueError('windows_protected_storage_failed')
            return ctypes.string_at(out.data,out.size)
        finally:
            ctypes.memset(source,0,len(source))
            if out.data:
                ctypes.memset(out.data,0,out.size)
                kernel.LocalFree(out.data)

    def protect(self,data,entropy):return self._convert(data,entropy,False)
    def unprotect(self,data,entropy):return self._convert(data,entropy,True)


class WorkspaceCredential:
    def __init__(self,app,*,protector=None):
        self.app=app;self.protector=protector if protector is not None else WindowsDPAPI()
        self.path=app.state_root/'workspace-settings'/'deepseek-credential.dpapi.json'
        self.entropy=hashlib.sha256(('catalyst:deepseek:https://api.deepseek.com:'+str(app.workspace.resolve())).encode()).digest()

    def _safe(self):
        from .project_understand import reject_source_links
        for path in (self.path,*self.path.parents):
            if path.exists() or path.is_symlink():reject_source_links(path)

    @property
    def available(self):
        self._safe()
        return self.protector.supported and self.path.is_file()

    def save(self,key):
        self._safe()
        if not isinstance(key,str) or not 8<=len(key)<=512 or any(not 33<=ord(c)<=126 for c in key):
            raise ValueError('api_key_format_invalid')
        encrypted=self.protector.protect(key.encode(),self.entropy)
        self.app._atomic_json(self.path,dict(schema=1,provider='deepseek',endpoint='https://api.deepseek.com',
                                           ciphertext=base64.b64encode(encrypted).decode('ascii')))

    def load(self):
        try:
            self._safe()
            if not self.available or self.path.stat().st_size>16384:raise ValueError()
            value=json.loads(self.path.read_text(encoding='utf-8'))
            if (set(value)!={'schema','provider','endpoint','ciphertext'} or value['schema']!=1
                    or value['provider']!='deepseek' or value['endpoint']!='https://api.deepseek.com'):raise ValueError()
            key=self.protector.unprotect(base64.b64decode(value['ciphertext'],validate=True),self.entropy).decode('ascii')
            if not 8<=len(key)<=512 or any(not 33<=ord(c)<=126 for c in key):raise ValueError()
            return key
        except (ValueError,OSError,TypeError,KeyError,UnicodeError):
            raise ValueError('saved_credential_unavailable') from None

    def identity(self):
        """Ciphertext-file identity for binding an explicit saved connection."""
        import hashlib
        self._safe()
        if not self.available or self.path.stat().st_size>16384:
            raise ValueError('saved_credential_unavailable')
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def delete(self):
        self._safe()
        self.path.unlink(missing_ok=True)
