import pytest

from tests.project_live.test_project_acceptance import configured, qualification_clock
from tests.project_understand.test_project_runtime import offline
from tests.project_live.test_daily_workflow_boundary import recorder


def test_project_card_binds_custom_limits_and_executes_existing_method(tmp_path, offline):
    host, root, calls, flow = configured(tmp_path)
    row = flow.prepare('agent', 'Explain this Agent dependency', 2,
                       limits={'max_requests': 5, 'max_output_tokens': 2048})
    assert row['card']['max_requests'] == 5
    assert row['card']['max_output_tokens'] == 2048
    assert row['card']['budget_cny'] == '0.40192'
    rec = recorder(host)
    host.prepare(rec)
    result = flow.execute(row['test_id'], row['card_sha256'], rec)
    assert result['status'] == 'success', result
    assert len(calls) == 4
    assert flow.get(row['test_id'])['budget']['max_requests'] == 5


@pytest.mark.parametrize('limits', [
    {'max_requests': 0, 'max_output_tokens': 4096},
    {'max_requests': 21, 'max_output_tokens': 4096},
    {'max_requests': 4, 'max_output_tokens': 4097},
    {'max_requests': True, 'max_output_tokens': 1024},
    {'max_requests': 4, 'max_output_tokens': 1024, 'budget_cny': '0'},
])
def test_invalid_custom_limits_cannot_prepare_or_dispatch(tmp_path, offline, limits):
    host, root, calls, flow = configured(tmp_path)
    with pytest.raises(ValueError):
        flow.prepare('agent', 'inspect', 1, limits=limits)
    assert calls == []
    assert not flow.items()


def test_tampering_with_bound_limits_blocks_test(tmp_path, offline):
    host, root, calls, flow = configured(tmp_path)
    row = flow.prepare('agent', 'inspect', 1, limits={'max_requests': 5, 'max_output_tokens': 2048})
    row['card']['max_requests'] = 6
    host.app._atomic_json(flow.directory(row['test_id']) / 'record.json', row)
    with pytest.raises(ValueError, match='test_record_changed'):
        flow.validate(row['test_id'], row['card_sha256'])
    assert calls == []
