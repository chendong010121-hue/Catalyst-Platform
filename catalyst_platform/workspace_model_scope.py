"""Existing Provider/P0/ledger assembly shared by daily and experiment policies.

This internal Adapter owns only assembling a configured scope; it grants no
source access or business admission and implements no model loop or transport.
"""
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from contextlib import nullcontext
from decimal import Decimal
import hashlib
import json
import uuid
from .llm_controls import ModelTask


def _now():
    # Preserve the existing Host clock injection and expiry behavior.
    from .workspace_settings import datetime as clock
    return clock.now(timezone.utc)


def daily_task(q):
    return ModelTask('workspace-daily-'+uuid.uuid4().hex,'deepseek',q.model,None,None,
        q.input_token_limit,min(8192,q.max_output_tokens),q.input_cny_per_million,
        q.output_cny_per_million,q.cache_hit_cny_per_million,
        q.price_reference+'#qualification='+q.sha256,model_output_token_limit=q.max_output_tokens,
        execution_profile='daily')


def activate(settings, key, qualified, task, *, allow_projects=False, allow_assets=False, project_scope=None,
             commit_connection=None, timeout=45):
    # Preserve the existing public Host factory injection seam; callers and
    # transport tests must exercise the same assembly, without Provider internals.
    from .workspace_settings import configured_model_provider
    self=settings
    daily=task.execution_profile=='daily'
    reserve=(task.input_token_limit*Decimal(task.input_cny_per_million)
             +task.max_output_tokens*Decimal(task.output_cny_per_million))/1000000
    policy = {**asdict(task), 'reserve_cny': str(reserve),
              'served_models': list(qualified.served_models),
              'qualification_sha256': qualified.sha256,
              'qualification_verified_at': qualified.verified_at.isoformat(),
              'qualification_valid_until': qualified.valid_until.isoformat(),
              'owner_scope': 'UI_DAILY_ADMITTED_PROJECT_READ_ONLY' if allow_projects else 'UI_TEXT_AND_PRODUCT_ASSET_METADATA' if allow_assets else 'UI_EXPLICIT_TEXT_ONLY',
              'allow_project_read':allow_projects,
              'request_context': 'Catalyst description + chat text'+(' + product asset summaries via wiki_assets (no source documents)' if allow_assets else '')+(' + Host-admitted project sources via project analysis' if allow_projects else '')}
    if project_scope is not None:
        policy.update(owner_scope='OWNER_BOUND_PROJECT_READ_ONLY',project_live_scope=project_scope,project_scope_sha256=hashlib.sha256(json.dumps(project_scope,sort_keys=True).encode()).hexdigest())
    with self.lock:
        if self.active_run_id:
            raise ValueError('model_request_in_progress')
        if self.ledger and not self.ledger.is_settled():
            raise ValueError('uncertain_scope_requires_manual_reconciliation_before_new_authorization')
        self.ledger_factory.check_prior_scopes(self.root / 'scopes')
        ledger = self.ledger_factory.open_scope(self.root / 'scopes' / task.task_id, policy)
        expires = None if daily else min(_now() + timedelta(hours=8), qualified.valid_until)

        def qualify_request(_request=None):
            if not daily:qualified.assert_current(_now())
            elif hashlib.sha256(qualified.path.read_bytes()).hexdigest()!=qualified.sha256:
                raise ValueError('model_qualification_changed')
            if expires is not None and _now() >= expires:
                raise ValueError('model_scope_expired')

        # Freeze the trusted assembly override for this authorized scope.
        # A later preferences change must not swap an active transport.
        transport_override = self.transport_override

        def guarded_transport(send_once, url, headers, body):
            qualify_request()
            if url != 'https://api.deepseek.com/chat/completions':
                raise ValueError('endpoint_scope_mismatch')
            slot = ledger.reserve_chat(hashlib.sha256(body).hexdigest(), self.active_run_id)['slot']
            try:
                # The original Provider owns the bound HTTP implementation.
                # Reservation can wait on disk/locks. Recheck at the actual
                # send boundary and retain the slot on any late rejection.
                qualify_request()
                if transport_override is None:
                    self.network_attempts += 1
                result = send_once()
                status, response = result[:2]
                if status != 200:
                    ledger.fail(slot, 'HTTP_' + str(status))
                    return result
                settled = ledger.settle(slot, response, task.max_output_tokens)
                self.last_model_receipt = {k: settled.get(k) for k in
                    ('provider_request_id', 'model', 'system_fingerprint', 'usage', 'peak_rate_estimated_cny')}
                return result
            except Exception:
                ledger.fail(slot, 'TRANSPORT_OR_USAGE_UNCERTAIN')
                raise

        provider = configured_model_provider(provider_id='deepseek', api_key=key,
            model=qualified.model, base_url='https://api.deepseek.com', timeout=timeout,
            task=task, transport=transport_override, transport_guard=guarded_transport,
            before_request=qualify_request,
            configuration_source='workspace_browser_explicit_memory')
        # Deliberate allowlist: never serialize incoming data/api_key.
        try:
            with self.provider.retirement() if self.provider is not None else nullcontext():
                self.app._atomic_json(self.config_path, {k: policy[k] for k in
                    ('provider_id', 'model', 'max_requests', 'budget_cny', 'max_output_tokens', 'price_reference',
                     'qualification_sha256', 'qualification_verified_at', 'qualification_valid_until', 'execution_profile')})
                # The resumable connection marker is the LAST durable commit.
                # A rejected preferences write cannot authorize restart restore.
                if commit_connection is not None:commit_connection()
        except Exception:
            provider.close()
            raise
        # Publish only after the durable preferences commit succeeds. A
        # rejected configuration cannot become an invisible paid scope.
        self.task, self.ledger, self.provider, self.expires = task, ledger, provider, expires
        self.qualification = qualified
        self.allow_asset_read=allow_assets
        self.allow_project_read=allow_projects
        self.last_model_receipt = None
        self.connection_disabled=False
        self.history = []
        # Reuse only this explicitly configured in-memory connection. The
        # caller cannot obtain the key or inherit the daily task/ledger.
        def configure_test(target_app, limits):
            from .workspace_settings import WorkspaceSettings
            child = WorkspaceSettings(target_app, transport=transport_override,
                allow_live=self.allow_live, ledger_factory=self.ledger_factory,
                qualification_path=self.qualification_path)
            child.configure(dict(api_key=key, provider_id='deepseek',model=qualified.model,
                consent=True,allow_project_read=True,allow_asset_read=False,**limits))
            return child
        self._test_connection = configure_test
    return self.snapshot()
