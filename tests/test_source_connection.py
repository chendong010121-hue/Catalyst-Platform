import hashlib
import json
import socket
import pytest
from catalyst_platform.wiki import ProjectWiki


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*a,**k):raise AssertionError('ZERO_API_CONNECTION')
    monkeypatch.setattr(socket.socket,'connect',deny)


@pytest.fixture(params=['json','sqlite'])
def fixture(request,tmp_path):
    root=tmp_path/'sources';root.mkdir();source=root/'policy.md'
    source.write_text('# Synthetic policy\nOperations checks request evidence.\n',encoding='utf-8')
    wiki=ProjectWiki(tmp_path/'wiki',[root],enterprise_id='synthetic',project_id='assets',backend=request.param)
    staged=wiki.stage_markdown(source)
    return wiki,source,staged,tmp_path


def test_same_two_actions_in_original_runtime_and_r4_both_storage_adapters(fixture):
    from catalyst_platform.source_connection import build_source_connection,run_source_connection
    wiki,source,staged,tmp=fixture;semantic_before=wiki.semantic_state()
    app,service,composer=build_source_connection(tmp/'app',wiki)
    app.components.assets.register(__import__('catalyst_platform.asset_records',fromlist=['builtin_assets']).builtin_assets())
    try:
        receipt=run_source_connection(app,service,'Synthetic policy',staged['source_id'])
        assert receipt['status']=='success' and receipt['content']==source.read_bytes().decode('utf-8')
        assert receipt['authority']=='SOURCE_DOCUMENT_NOT_ACCEPTED_ONTOLOGY'
        assert len(receipt['runs'])==2 and receipt['external_api_requests']==0
        from catalyst_platform.trace_log import JsonlTraceStore
        for run in receipt['runs']:
            events=JsonlTraceStore(app.workspace).inspect_run(run['run_id'])['events']
            assert any(e['event_type']=='tool.execution.started' for e in events)
            assert any(e['event_type']=='authorization.decided' for e in events)
        (tmp/'CONNECTION_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:composer.close()
    assert app._catalog.get('source_read','1.0.0') is None
    assert wiki.semantic_state()==semantic_before and source.exists()


@pytest.mark.parametrize('field',['scope_id','source_id','revision','locator','content_sha256'])
def test_exact_reference_mismatch_is_rejected_by_consumer(fixture,field):
    from catalyst_platform.source_connection import SourceReadService
    wiki,source,staged,tmp=fixture;service=SourceReadService(wiki)
    ref=service.search('Synthetic policy','synthetic')['references'][0]
    ref[field]='wrong'
    with pytest.raises((ValueError,RuntimeError)):service.read(ref,'synthetic')


def test_drift_missing_binding_and_scope_do_not_silently_retry_or_activate(fixture):
    from catalyst_platform.source_connection import SourceReadService,build_source_connection,run_source_connection
    wiki,source,staged,tmp=fixture;service=SourceReadService(wiki)
    ref=service.search('Synthetic policy','synthetic')['references'][0]
    with pytest.raises(ValueError):service.read(ref,'other')
    with pytest.raises(ValueError):service.read({**ref,'owner_approved':True},'synthetic')
    source.write_text('# Changed source\n',encoding='utf-8')
    with pytest.raises(ValueError):service.read(ref,'synthetic')
    app,service,composer=build_source_connection(tmp/'app',wiki)
    composer.close()
    with pytest.raises(ValueError):run_source_connection(app,service,'Synthetic policy',staged['source_id'])
