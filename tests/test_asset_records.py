"""Metadata registration, not runtime installation or enterprise authority."""
import copy
import json
import socket
import pytest
from catalyst_platform.workbench import CatalystWorkbench


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args,**kwargs):raise AssertionError('ASSETS_ZERO_API')
    monkeypatch.setattr(socket.socket,'connect',deny)


@pytest.fixture
def app(tmp_path):return CatalystWorkbench(tmp_path/'app',[tmp_path])


def test_builtin_registration_persists_but_does_not_activate_or_mutate_runtime_manifest(app):
    from catalyst_platform.asset_records import builtin_assets
    before=app._catalog.list(); manifest=app._read_capability_manifest()
    report=app.components.assets.register(builtin_assets())
    assert report['registered']>=8
    assert app._catalog.list()==before and app._read_capability_manifest()==manifest
    again=CatalystWorkbench(app.workspace,app.wiki_roots)
    assert len(again.components.assets.list())==report['registered']
    assert all(x['authority']=='PRODUCT_ASSET_DESCRIPTION_NOT_ENTERPRISE_AUTHORITY' for x in again.components.assets.list())


def test_same_version_conflict_and_whole_batch_validation(app):
    from catalyst_platform.asset_records import builtin_assets,AssetRecordError
    records=builtin_assets();app.components.assets.register(records)
    before=app.components.assets.path.read_bytes()
    changed=copy.deepcopy(records);changed[0]['responsibility']='different responsibility'
    with pytest.raises(AssetRecordError):app.components.assets.register(changed)
    assert app.components.assets.path.read_bytes()==before
    bad=copy.deepcopy(records);bad[-1]['implementation']['files'][0]['path']='../../secret.env'
    with pytest.raises(AssetRecordError):app.components.assets.register(bad)
    assert app.components.assets.path.read_bytes()==before


@pytest.mark.parametrize('field',['api_key','owner_approved','active','authorized'])
def test_unknown_fields_cannot_smuggle_state_or_credentials(app,field):
    from catalyst_platform.asset_records import builtin_assets,AssetRecordError
    values=builtin_assets();values[0][field]='fixture'
    with pytest.raises(AssetRecordError):app.components.assets.register(values)
    assert not app.components.assets.path.exists()


def test_existing_lock_and_corrupt_sidecar_are_not_repaired(app):
    from catalyst_platform.asset_records import builtin_assets,AssetRecordError
    assets=app.components.assets;assets.path.parent.mkdir(parents=True,exist_ok=True)
    assets.lock_path.mkdir()
    with pytest.raises(AssetRecordError):assets.register(builtin_assets())
    assets.lock_path.rmdir() # This fixture only.
    assets.path.write_text('{broken',encoding='utf-8')
    with pytest.raises(AssetRecordError):assets.register(builtin_assets())
    assert assets.path.read_text(encoding='utf-8')=='{broken'


def test_metadata_document_and_binding_are_separate(app):
    from catalyst_platform.asset_records import builtin_assets
    assets=app.components.assets;assets.register(builtin_assets())
    rows=assets.list();wiki=next(x for x in rows if x['asset_id']=='capability.wiki_search')
    assert wiki['catalog_registered'] and wiki['catalog_active'] and not wiki['execution_authorized']
    assert all(not x['catalog_registered'] for x in rows if x['kind']=='service')
    doc=assets.document(wiki['asset_id'],wiki['version'])
    assert wiki['record_sha256'] in doc['content'] and 'NOT_ENTERPRISE_AUTHORITY' in doc['content']


def test_source_or_test_drift_marks_unverified_without_loading_code(app,monkeypatch):
    from catalyst_platform.asset_records import builtin_assets
    assets=app.components.assets;assets.register(builtin_assets())
    original=assets._file_digest
    monkeypatch.setattr(assets,'_file_digest',lambda path:'0'*64)
    assert all(x['integrity']=='DRIFT_OR_MISSING' for x in assets.list())
    monkeypatch.setattr(assets,'_file_digest',original)
    assert all(x['integrity']=='MATCH' for x in assets.list())


def test_acceptance_plan_has_pinned_parent_but_cannot_promote_or_execute(app):
    from catalyst_platform.asset_records import builtin_assets
    assets=app.components.assets;assets.register(builtin_assets());row=assets.list()[0]
    plan=assets.acceptance_plan(row['asset_id'],row['version'])
    assert plan['execution']=='NOT_EXECUTED' and plan['business_semantics']=='NOT_EVALUATED'
    assert 'INDEPENDENT' in plan['candidate_workspace'] and 'NOT_AUTOMATIC' in plan['promotion']


def test_persistence_failure_has_no_partial_registration(app,monkeypatch):
    from catalyst_platform.asset_records import builtin_assets
    assets=app.components.assets
    def fail(*a):raise OSError('synthetic write failure')
    monkeypatch.setattr(assets,'write_json',fail)
    with pytest.raises(OSError):assets.register(builtin_assets())
    assert not assets.path.exists() and not assets.lock_path.exists()


def test_two_metadata_owners_cannot_overwrite_each_other(app,monkeypatch):
    import threading
    from catalyst_platform.asset_records import builtin_assets,AssetRecords,AssetRecordError
    first=app.components.assets;second=AssetRecords(app.workspace,app._catalog,app._atomic_json)
    entered=threading.Event();release=threading.Event();errors=[];write=first.write_json
    def blocked_write(*args):entered.set();assert release.wait(5);write(*args)
    monkeypatch.setattr(first,'write_json',blocked_write)
    def register():
        try:first.register(builtin_assets())
        except BaseException as exc:errors.append(exc)
    worker=threading.Thread(target=register);worker.start();assert entered.wait(5)
    try:
        with pytest.raises(AssetRecordError):second.register(builtin_assets())
    finally:release.set();worker.join(timeout=5)
    assert not worker.is_alive() and errors==[] and len(first.list())==len(builtin_assets())


def test_empty_path_parts_are_controlled_rejections(app):
    from catalyst_platform.asset_records import builtin_assets,AssetRecordError
    rows=builtin_assets();rows[0]['implementation']['files'][0]['path']='.'
    with pytest.raises(AssetRecordError):app.components.assets.register(rows)


def test_serialized_capacity_failure_never_commits_unreadable_state(app,monkeypatch):
    from catalyst_platform.asset_records import builtin_assets,AssetRecordError
    assets=app.components.assets;records=builtin_assets();assets.register(records)
    before=assets.path.read_bytes()
    import catalyst_platform.asset_records as module
    monkeypatch.setattr(module,'MAX_BYTES',len(before)+100)
    more=copy.deepcopy(records[0]);more['version']='2.0.0';more['responsibility']='x'*2000
    with pytest.raises(AssetRecordError):assets.register([more])
    assert assets.path.read_bytes()==before
