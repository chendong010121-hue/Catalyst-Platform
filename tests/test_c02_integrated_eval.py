"""One shared Eval + actual Agent boundary, SYNTHETIC_OFFLINE_STUB only."""
import importlib.util,json,hashlib
from pathlib import Path


def test_actual_agent_boundary_and_shared_nl_eval_and_report(tmp_path):
    script=Path(__file__).resolve().parents[1]/'scripts/c02_p1_p3_offline_acceptance.py'
    spec=importlib.util.spec_from_file_location('offline_acceptance',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    root=tmp_path/'joint';module.main(root)
    receipt=json.loads((root/'INTEGRATED_ZERO_PAID_E2E_RECEIPT.json').read_text(encoding='utf-8'))
    assert receipt['synthetic'][0]['task_success'] is True
    assert receipt['logical_mock_dispatches']==2 and receipt['new_network_calls']==0
    assert receipt['enterprise_nl_semantics']=='NOT_EVALUATED'
    assert not receipt['gate']['accept']
    m=json.loads((root/'SHA256_MANIFEST.json').read_text(encoding='utf-8'))
    for name,pin in m.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==pin
