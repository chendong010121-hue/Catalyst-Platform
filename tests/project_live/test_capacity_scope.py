"""Explicit Owner input/cost binding; fake-only, no historical scope changes."""
import json
import pytest
from catalyst_platform.model_qualification import DEFAULT_QUALIFICATION,load_qualification
from catalyst_platform.project_understand import validate_live_project_scope
from catalyst_platform.workspace_settings import WorkspaceSettings
from catalyst_platform.workspace_session import WorkspaceUserSession
from tests.project_live.test_admission import setup
from tests.project_understand.test_project_runtime import offline
from tests.test_workspace_model_settings import configuration

def qualification(tmp_path,limit,*,capacity=None):
    data=json.loads(DEFAULT_QUALIFICATION.read_text(encoding='utf-8-sig'));data['input_token_limit']=limit
    if capacity is not None:data['schema_version']=2;data['max_output_tokens']=capacity
    path=tmp_path/('qualification-'+str(capacity)+'.json');path.write_text(json.dumps(data),encoding='utf-8');return path

def test_explicit_64000_scope_keeps_original_exact_reservation_formula(tmp_path,offline):
    app,root,scope=setup(tmp_path)
    scope.update(input_token_limit=64000,budget_cny='0.643072')
    assert validate_live_project_scope(scope,{'root':root},scope['objective'],2,method_sha256='a'*64)==scope
    host=WorkspaceUserSession(tmp_path/'host')
    host.settings=WorkspaceSettings(host.app,transport=lambda *args: (_ for _ in ()).throw(AssertionError('NO_SEND')),qualification_path=qualification(tmp_path,64000))
    host.settings.project_live_scope=scope
    config=configuration();config.update(max_requests=4,budget_cny='0.643072',max_output_tokens=4096)
    host.settings.configure(config)
    assert host.settings.task.input_token_limit==64000
    assert host.settings.provider.budget_snapshot['reserved_per_request_cny']=='0.160768'
    assert host.settings.provider.budget_snapshot['attempts']==0

@pytest.mark.parametrize('limit,budget',[(64000,'0.387072'),(32000,'0.643072'),(64001,'0.643080'),(200000,'1.731072')])
def test_mismatched_or_unauthorized_capacity_never_admits(tmp_path,limit,budget):
    app,root,scope=setup(tmp_path);scope.update(input_token_limit=limit,budget_cny=budget)
    with pytest.raises(ValueError):validate_live_project_scope(scope,{'root':root},scope['objective'],2,method_sha256='a'*64)

def test_qualification_does_not_silently_enlarge_a_32000_owner_scope(tmp_path,offline):
    app,root,scope=setup(tmp_path)
    host=WorkspaceUserSession(tmp_path/'host');host.settings=WorkspaceSettings(host.app,transport=lambda *a: None,qualification_path=qualification(tmp_path,64000));host.settings.project_live_scope=scope
    config=configuration();config.update(max_requests=4,budget_cny='0.387072',max_output_tokens=4096)
    with pytest.raises(ValueError,match='qualification_changed'):host.settings.configure(config)
    assert host.settings.provider is None

def test_input_qualification_still_has_a_hard_ceiling(tmp_path):
    with pytest.raises(ValueError,match='qualification_invalid'):load_qualification(qualification(tmp_path,64001))

def test_model_capacity_above_the_owner_cap_does_not_widen_the_request(tmp_path,offline):
    # A refreshed qualification declares the vendor's real output capacity (384K); the Owner
    # still capped this run at 4096 output tokens and 32000 input tokens.
    app,root,scope=setup(tmp_path)
    host=WorkspaceUserSession(tmp_path/'host')
    host.settings=WorkspaceSettings(host.app,transport=lambda *a: (_ for _ in ()).throw(AssertionError('NO_SEND')),qualification_path=qualification(tmp_path,32000,capacity=384000))
    host.settings.project_live_scope=scope
    config=configuration();config.update(max_requests=4,budget_cny='0.387072',max_output_tokens=4096)
    host.settings.configure(config)
    assert host.settings.task.input_token_limit==32000
    assert host.settings.task.max_output_tokens==4096
    assert host.settings.provider.budget_snapshot['reserved_per_request_cny']=='0.096768'
    assert host.settings.provider.budget_snapshot['attempts']==0

def test_capacity_below_the_owner_cap_is_refused(tmp_path,offline):
    app,root,scope=setup(tmp_path)
    host=WorkspaceUserSession(tmp_path/'host');host.settings=WorkspaceSettings(host.app,transport=lambda *a: None,qualification_path=qualification(tmp_path,32000,capacity=2048));host.settings.project_live_scope=scope
    config=configuration();config.update(max_requests=2,budget_cny='0.193536',max_output_tokens=4096)
    with pytest.raises(ValueError,match='output_bound_exceeds_qualified_model_capacity'):host.settings.configure(config)
    assert host.settings.provider is None

def test_changed_per_token_price_is_refused(tmp_path,offline):
    app,root,scope=setup(tmp_path)
    data=json.loads(qualification(tmp_path,32000,capacity=384000).read_text(encoding='utf-8'));data['input_cny_per_million']='3'
    path=tmp_path/'qualification-price.json';path.write_text(json.dumps(data),encoding='utf-8')
    host=WorkspaceUserSession(tmp_path/'host');host.settings=WorkspaceSettings(host.app,transport=lambda *a: None,qualification_path=path);host.settings.project_live_scope=scope
    config=configuration();config.update(max_requests=2,budget_cny='0.193536',max_output_tokens=4096)
    with pytest.raises(ValueError,match='qualification_changed'):host.settings.configure(config)
    assert host.settings.provider is None
