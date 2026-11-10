"""Zero-API maintenance lifecycle over existing packages/Runtime."""
import json
from pathlib import Path
import pytest

from catalyst_platform.workbench import CatalystWorkbench


@pytest.fixture
def manager(tmp_path):
    import catalyst_platform.maintenance as module
    app=CatalystWorkbench(tmp_path/'workspace',[tmp_path/'workspace'/'inputs'])
    # Tests isolate package consumer probes; production also runs existing pytest.
    return module.LocalMaintenance(app, run_regression=False)


def test_adapter_exists_without_new_runtime_or_catalog():
    import catalyst_platform.maintenance as module
    assert hasattr(module,'LocalMaintenance')


def test_prepare_tests_exact_candidate_without_activating(manager):
    review=manager.prepare()
    assert review['status']=='VALIDATED' and review['evaluation']['passed']
    assert review['candidate']['version']=='2.0.0'
    assert manager.active_identity() is None
    assert review['diff'] and any(review['evaluation']['runtime_run_ids'])
    assert review['approval_digest']


def test_explicit_approval_waits_for_a_cold_start(manager):
    review=manager.prepare()
    with pytest.raises(ValueError):manager.approve(review['review_id'],review['approval_digest'],confirmed=False)
    manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    assert manager.active_identity() is None
    assert manager.items()[0]['status']=='PENDING_RESTART'
    assert manager.apply_pending()['status']=='APPLIED'
    assert manager.active_identity()['version']=='2.0.0'
    assert manager.items()[0]['startup_receipt']['runtime_run_id']


def test_stale_digest_and_changed_candidate_are_refused(manager):
    review=manager.prepare()
    with pytest.raises(ValueError):manager.approve(review['review_id'],'0'*64,confirmed=True)
    stage=manager.root/'packages'/review['review_id']/'tool.py'
    stage.write_text(stage.read_text()+'\n# changed\n',encoding='utf-8')
    with pytest.raises((ValueError,RuntimeError)):manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    assert manager.active_identity() is None


def test_late_tamper_blocks_startup_without_activation(manager):
    review=manager.prepare();manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    (manager.root/'packages'/review['review_id']/'tool.py').write_text('raise RuntimeError("not executed")',encoding='utf-8')
    result=manager.apply_pending()
    assert result['status']=='FAILED' and manager.active_identity() is None
    assert manager.items()[0]['error']


def test_startup_health_failure_restores_previous_binding(manager,monkeypatch):
    manager.install_test_parent()
    review=manager.prepare();manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    monkeypatch.setattr(manager,'health',lambda *args,**kwargs: (_ for _ in ()).throw(ValueError('fixture_health_failure')))
    result=manager.apply_pending()
    assert result['status']=='FAILED_ROLLED_BACK'
    assert manager.active_identity()['version']=='1.0.0'


def test_rollback_is_separately_confirmed_and_restart_bound(manager):
    manager.install_test_parent()
    review=manager.prepare();manager.approve(review['review_id'],review['approval_digest'],confirmed=True);manager.apply_pending()
    applied=manager.items()[0]
    with pytest.raises(ValueError):manager.request_rollback(applied['review_id'],applied['approval_digest'],confirmed=False)
    manager.request_rollback(applied['review_id'],applied['approval_digest'],confirmed=True)
    assert manager.active_identity()['version']=='2.0.0'
    assert manager.apply_pending()['status']=='ROLLED_BACK'
    assert manager.active_identity()['version']=='1.0.0'


def test_receipt_tamper_or_parent_drift_cannot_be_approved(manager):
    review=manager.prepare()
    record=manager.root/'reviews'/(review['review_id']+'.json')
    data=json.loads(record.read_text());data['evaluation']['passed']=False
    record.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError):manager.approve(review['review_id'],review['approval_digest'],confirmed=True)


def test_duplicate_pending_request_is_not_applied_twice(manager):
    review=manager.prepare();manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    with pytest.raises(ValueError):manager.prepare()
    assert manager.apply_pending()['status']=='APPLIED'
    assert manager.apply_pending() is None


def test_existing_v2_unicode_behavior_is_independently_verified(manager):
    result=manager.probe_existing_v2()
    assert result['passed'] and result['output']['word_count']==4


def test_rejected_card_does_not_change_catalog(manager):
    review=manager.prepare()
    manager.reject(review['review_id'],review['approval_digest'],confirmed=True)
    assert manager.items()[0]['status']=='REJECTED'
    assert manager.apply_pending() is None and manager.active_identity() is None


def test_production_cannot_use_test_assembly_receipt(manager):
    review=manager.prepare();manager.run_regression=True
    with pytest.raises(ValueError,match='production_regression_required'):manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    assert manager.active_identity() is None


def test_health_probe_never_overwrites_existing_user_file(manager):
    source=manager.app.workspace/'inputs'/'maintenance-probe.txt'
    source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(b'preserve user file')
    manager.install_test_parent();manager.health('1.0.0')
    assert source.read_bytes()==b'preserve user file'


def test_corrupt_frozen_evidence_prevents_approval(manager):
    review=manager.prepare()
    root=Path(review['evaluation']['artifact_root'])
    artifact=root/review['evaluation']['artifacts'][0]['path']
    artifact.write_bytes(artifact.read_bytes()+b'\nchanged')
    with pytest.raises(ValueError,match='evidence_changed'):manager.approve(review['review_id'],review['approval_digest'],confirmed=True)


def test_applying_receipt_cannot_be_silently_replayed(manager):
    review=manager.prepare();manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    row=manager.items()[0];row['status']='APPLYING';manager._write(row)
    with pytest.raises(ValueError,match='incomplete_startup'):manager.apply_pending()


def test_failed_recovery_cannot_claim_healthy_rollback(manager,monkeypatch):
    manager.install_test_parent();review=manager.prepare()
    manager.approve(review['review_id'],review['approval_digest'],confirmed=True)
    monkeypatch.setattr(manager,'health',lambda *a: (_ for _ in ()).throw(ValueError('health-failed')))
    monkeypatch.setattr(manager,'_restore_and_verify',lambda *a: (_ for _ in ()).throw(ValueError('restore-failed')))
    assert manager.apply_pending()['status']=='RECOVERY_REQUIRED'


def test_failed_existing_regression_never_becomes_approvable(manager,monkeypatch):
    monkeypatch.setattr(manager,'_regression',lambda root:{'passed':False,'status':'FAILED','exit_code':1})
    row=manager.prepare()
    assert row['status']=='VALIDATION_FAILED' and row['can_accept'] is False
    with pytest.raises(ValueError):manager.approve(row['review_id'],row['approval_digest'],confirmed=True)
    assert manager.active_identity() is None
