"""Small current-Windows-user DPAPI adapter; never searches external stores.

Availability is metadata only. Decryption is an explicit connect/confirmed-test
operation, never startup, GET, automatic resume, logging or credential discovery.
"""
import ctypes
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
