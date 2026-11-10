"""Pinned declaration clock for named zero-paid Workspace mechanism tests.

Uses the shipped declaration's valid instant, not a live price qualification.
Production metadata is unchanged. Expiry, drift and future documents have
independent negative tests; each module uses explicit fake transports.
"""
from datetime import datetime, timezone, timedelta
import pytest


@pytest.fixture(autouse=True)
def frozen_workspace_tariff_clock(request, monkeypatch):
    if request.node.path.name not in {
        'test_workspace_model_settings.py', 'test_workspace_settings_http.py',
        'test_workspace_ledger_seam.py', 'test_provider_transport_seam.py',
        'test_wiki_asset_chat.py', 'test_provider_lifecycle.py',
    }:
        return
    import catalyst_platform.workspace_settings as settings
    from catalyst_platform.model_qualification import load_qualification, DEFAULT_QUALIFICATION
    instant = load_qualification(DEFAULT_QUALIFICATION).verified_at + timedelta(seconds=1)
    class FixtureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz is not None else instant.replace(tzinfo=None)
    monkeypatch.setattr(settings, 'datetime', FixtureClock)
