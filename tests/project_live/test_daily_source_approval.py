"""Daily source approval is per action, not part of model connection."""
import json
import threading
import socket
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from catalyst_platform.workspace_ui import create_workspace_server
from tests.project_understand.test_project_runtime import offline
LOCAL_CONNECT=socket.socket.connect


def test_daily_source_manifest_approval_is_explicit_and_change_sensitive(tmp_path,offline,monkeypatch):
    def local(sock,address):
        if address[0]!='127.0.0.1':raise AssertionError('EXTERNAL_CONNECTION_FORBIDDEN')
        return LOCAL_CONNECT(sock,address)
    monkeypatch.setattr(socket.socket,'connect',local)
    root=tmp_path/'source';root.mkdir();(root/'README.md').write_text('Public synthetic source',encoding='utf8')
    server=create_workspace_server(tmp_path/'workspace',port=0,project_sources={'public':dict(root=root,object_type='skill')})
    server.run_request.settings.connect(dict(provider_id='deepseek',model='deepseek-flash',api_key='OFFLINE-SOURCE-KEY',remember=False))
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    base='http://127.0.0.1:'+str(server.server_address[1])
    def get(path):
        with urlopen(base+path) as r:return json.load(r)
    csrf=get('/api/config')['csrf_token']
    def post(body):
        request=Request(base+'/api/project-analysis',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Catalyst-CSRF':csrf})
        try:
            with urlopen(request) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    try:
        source=get('/api/project-sources?include_manifest=1')['items'][0]
        assert source['source_manifest_sha256']
        body=dict(source_id='public',objective='Explain source',max_depth=1)
        assert post(body)[0]==400
        assert post(dict(body,source_approval_sha256='0'*64))[0]==400
        old=source['source_manifest_sha256'];(root/'README.md').write_text('Changed source',encoding='utf8')
        assert post(dict(body,source_approval_sha256=old))[0]==400
        assert server.run_request.settings.provider.budget_snapshot['attempts']==0
    finally:server.shutdown();server.server_close();t.join(5)
