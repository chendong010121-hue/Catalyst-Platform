"""One workspace, two qualified models, and an explicit switch between them.

The product used to pin `deepseek-flash` in every place a model is named: the
daily connection, the scope assembly, the receipt and the project live scope. A
model is a price and a capacity, so each one now carries its own qualification
file and the workspace resolves the right one when the model changes. An
unqualified name, or a declaration that names another model, is refused.
"""
import json
from decimal import Decimal

import pytest

from catalyst_platform.model_qualification import (
    DEFAULT_QUALIFICATION,
    QUALIFIED_MODELS,
    load_qualification,
    qualification_for,
)
from catalyst_platform.qualification_refresh import parse_official
from catalyst_platform.project_understand import ProjectAnalysisError, validate_live_project_scope
from catalyst_platform.workspace_session import WorkspaceUserSession
from tests.test_workspace_model_settings import packet, run


def _connect(host, model):
    return host.settings.connect(dict(provider_id='deepseek', model=model,
                                      api_key='OFFLINE-SYNTHETIC-KEY', remember=False))


def test_each_qualified_model_carries_its_own_rates():
    flash = load_qualification(DEFAULT_QUALIFICATION)
    pro = load_qualification(qualification_for('deepseek-v4-pro'))
    assert QUALIFIED_MODELS == ('deepseek-flash', 'deepseek-v4-pro')
    assert (flash.model, flash.input_cny_per_million, flash.output_cny_per_million) == ('deepseek-flash', '2', '8')
    # The pro declaration records the vendor page as it prints it, and the page now writes
    # the same two prices with a decimal: 9.0 and 27.0. The rate is the rate.
    assert (pro.model, pro.input_cny_per_million, pro.output_cny_per_million) == ('deepseek-v4-pro', '9.0', '27.0')
    assert pro.price_reference == flash.price_reference


def test_the_workspace_switches_model_and_prices_the_scope_it_opens(tmp_path):
    host = WorkspaceUserSession(tmp_path / 'daily')
    # The offline packet must name the model the scope serves: the ledger refuses
    # a receipt for any model outside the scope's served_models, pro included.
    host.settings.transport_override = lambda *_: (200, packet(model='deepseek-v4-pro'))
    state = _connect(host, 'deepseek-v4-pro')
    assert state['enabled'] and state['model'] == 'deepseek-v4-pro'
    assert state['input_cny_per_million'] == '9.0' and state['output_cny_per_million'] == '27.0'
    # One daily request reserves exactly the qualified worst case of the chosen model.
    reserve = (Decimal(32000) * Decimal('9') + Decimal(8192) * Decimal('27')) / 1000000
    assert Decimal(state['budget']['reserved_per_request_cny']) == reserve
    assert host.settings.ledger.policy['model'] == 'deepseek-v4-pro'
    assert run(host)['state'] == 'CHAT_COMPLETED'
    assert host.settings.snapshot()['budget']['attempts'] == 1


def test_a_model_outside_the_catalog_is_refused_and_nothing_is_scoped(tmp_path):
    host = WorkspaceUserSession(tmp_path / 'daily')
    host.settings.transport_override = lambda *_: (200, packet())
    with pytest.raises(ValueError):
        _connect(host, 'deepseek-v3')
    assert host.settings.provider is None and not list(host.settings.root.glob('scopes/*/M6B_POLICY.json'))


def test_switching_back_to_flash_reprices_the_next_scope(tmp_path):
    host = WorkspaceUserSession(tmp_path / 'daily')
    host.settings.transport_override = lambda *_: (200, packet())
    _connect(host, 'deepseek-v4-pro')
    state = _connect(host, 'deepseek-flash')
    assert state['model'] == 'deepseek-flash' and state['input_cny_per_million'] == '2'
    assert host.settings.qualification_path == host.settings.qualification_path_for('deepseek-flash')


def test_a_local_declaration_for_one_model_does_not_price_the_other(tmp_path):
    host = WorkspaceUserSession(tmp_path / 'daily')
    host.settings.transport_override = lambda *_: (200, packet())
    # The Owner's local approval declares flash; asking for pro must not borrow it.
    host.settings.root.mkdir(parents=True, exist_ok=True)
    local = host.settings.root / 'model-qualification.json'
    local.write_bytes(DEFAULT_QUALIFICATION.read_bytes())
    assert host.settings.qualification_path_for('deepseek-flash') == local
    assert host.settings.qualification_path_for('deepseek-v4-pro') == qualification_for('deepseek-v4-pro')


def test_a_broken_local_declaration_stops_the_switch_instead_of_falling_back(tmp_path):
    host = WorkspaceUserSession(tmp_path / 'daily')
    host.settings.transport_override = lambda *_: (200, packet())
    broken = json.loads(DEFAULT_QUALIFICATION.read_text(encoding='utf-8'))
    broken['max_output_tokens'] = 127
    host.settings.root.mkdir(parents=True, exist_ok=True)
    (host.settings.root / 'model-qualification.json').write_text(json.dumps(broken), encoding='utf-8')
    with pytest.raises(ValueError, match='model_qualification_invalid'):
        host.settings.qualification_path_for('deepseek-v4-pro')


def test_a_declaration_cannot_admit_the_other_model():
    """The served-model list widens protocol names, never the model the file qualifies."""
    payload = json.loads(qualification_for('deepseek-v4-pro').read_text(encoding='utf-8'))
    payload['served_models'] = ['deepseek-v4-pro', 'deepseek-flash']
    path = qualification_for('deepseek-v4-pro').parent.parent / 'config' / '__test_flash_served.json'
    try:
        path.write_text(json.dumps(payload), encoding='utf-8')
        with pytest.raises(ValueError):
            load_qualification(path)
    finally:
        path.unlink(missing_ok=True)


def test_the_official_table_prices_whichever_model_is_being_refreshed():
    raw = open('tests/fixtures/deepseek_official_pricing_table_20261027.html', 'rb').read()
    pro = parse_official(raw, dict(model='deepseek-v4-pro', input_token_limit=32000))
    flash = parse_official(raw, dict(model='deepseek-flash', input_token_limit=32000))
    assert (flash['input_cny_per_million'], flash['output_cny_per_million']) == ('2', '8')
    assert (pro['input_cny_per_million'], pro['output_cny_per_million']) == ('9.0', '27.0')
    assert pro['served_models'][0] == 'deepseek-v4-pro'


def test_a_project_scope_may_be_approved_for_either_model_at_its_own_price():
    base = dict(version=1, scope_id='s1', source_id='src1', source_manifest_sha256='x', method_sha256='y',
                objective='o', max_depth=1, provider_id='deepseek', max_requests=4,
                input_token_limit=32000, max_output_tokens=4096, expires_at='2999-01-01T00:00:00+00:00',
                owner_approval='EXPLICIT_LOCAL_OWNER')
    pro_budget = str((Decimal(32000) * Decimal('9') + Decimal(4096) * Decimal('27')) / 1000000 * 4)
    scope = dict(base, model='deepseek-v4-pro', budget_cny=pro_budget)
    from catalyst_platform.project_understand import _worst_case_reservation
    assert str(_worst_case_reservation(scope)) == pro_budget
    # Flash prices under a pro scope are refused: the budget would under-reserve.
    with pytest.raises(ProjectAnalysisError):
        validate_live_project_scope(dict(scope, budget_cny=str((Decimal(32000) * Decimal('2')
                                                                + Decimal(4096) * Decimal('8')) / 1000000 * 4)),
                                    {'root': '.'}, 'o', 1, method_sha256='y')
