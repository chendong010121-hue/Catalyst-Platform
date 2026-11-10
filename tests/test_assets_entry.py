import json
import subprocess
import sys
import threading
from urllib.request import urlopen

from catalyst_platform.workspace_ui import create_workspace_server


def test_existing_cli_register_list_and_help_do_not_dispatch(tmp_path):
    workspace=tmp_path/'cli'
    for action in ['register','list']:
        out=subprocess.run([sys.executable,'-m','catalyst_platform','assets',action,'--workspace',str(workspace)],
                           capture_output=True,text=True,encoding='utf-8',timeout=20)
        assert out.returncode==0,out.stdout+out.stderr
        result=json.loads(out.stdout)
        if action=='register':assert result['registered']==13 and result['runtime_mutated'] is False
        else:
            assert len(result['items'])==13
            assert {'system.evaluation','system.development-workflow','method.project-acceptance'} <= {row['asset_id'] for row in result['items']}
    assert not list(workspace.rglob('M6B_POLICY.json'))


def test_workspace_capability_and_wiki_are_same_readonly_asset_projection(tmp_path):
    server=create_workspace_server(tmp_path/'ui',port=0,mode='BLOCKED')
    assets=server.run_request.app.components.assets
    from catalyst_platform.asset_records import builtin_assets
    assets.register(builtin_assets());before=assets.path.read_bytes()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    def get(path):
        with urlopen(base+path,timeout=5) as response:return json.load(response)
    try:
        records=get('/api/assets')['items'];caps=get('/api/capabilities');wiki=get('/api/knowledge')
        assert records==caps['assets']==wiki['asset_documents']
        assert len(caps['items'])==4 # Metadata did not install or activate source_read.
        row=records[0]
        doc=get('/api/asset-document?id='+row['asset_id']+'&version='+row['version'].replace('+','%2B'))
        assert doc['record_sha256']==row['record_sha256']
        assert assets.path.read_bytes()==before and not get('/api/config')['paid_calls_enabled']
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


def test_expired_product_tariff_is_still_rejected_before_any_dispatch(tmp_path,monkeypatch):
    from datetime import datetime,timezone
    import pytest
    import catalyst_platform.workspace_settings as settings
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from tests.test_workspace_model_settings import configuration
    class ExpiredClock(datetime):
        @classmethod
        def now(cls,tz=None):return cls(2026,10,26,12,tzinfo=timezone.utc)
    monkeypatch.setattr(settings,'datetime',ExpiredClock)
    session=WorkspaceUserSession(tmp_path/'expired')
    with pytest.raises(ValueError,match='official_price_refresh_required'):
        session.settings.configure(configuration())
    assert session.settings.provider is None and session.settings.network_attempts==0


def test_cli_connection_selects_exact_existing_scope(tmp_path):
    from catalyst_platform.wiki import ProjectWiki
    workspace=tmp_path/'cli-connect';sources=tmp_path/'inputs';sources.mkdir()
    source=sources/'manual.md';source.write_text('# Source policy\nSynthetic only.\n',encoding='utf-8')
    wiki=ProjectWiki(workspace,[sources],enterprise_id='synthetic',project_id='local-ui-demo')
    staged=wiki.stage_markdown(source)
    args=[sys.executable,'-m','catalyst_platform','assets','connect','--workspace',str(workspace),
      '--source-root',str(sources),'--query','Source policy','--source-id',staged['source_id'],
      '--enterprise-id','synthetic','--project-id','local-ui-demo']
    result=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)['content']==source.read_bytes().decode()
    args[-1]='wrong-project'
    failed=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert failed.returncode!=0 and 'content' not in json.loads(failed.stdout)


def test_corrupt_optional_assets_cannot_block_original_catalog_or_wiki(tmp_path):
    server=create_workspace_server(tmp_path/'corrupt',port=0,mode='BLOCKED')
    assets=server.run_request.app.components.assets;assets.path.parent.mkdir(parents=True,exist_ok=True)
    assets.path.write_text('{broken',encoding='utf-8')
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base=f'http://127.0.0.1:{server.server_port}'
        with urlopen(base+'/api/capabilities') as response:caps=json.load(response)
        assert len(caps['items'])==4 and caps['assets'] is None and caps['asset_error']
        with urlopen(base+'/api/knowledge') as response:knowledge=json.load(response)
        assert knowledge['asset_documents'] is None and knowledge['asset_error']
        with urlopen(base+'/api/assets') as response:unavailable=json.load(response)
        assert unavailable['items'] is None and unavailable['error']
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
