"""Workspace dispatch seam over the exact qualified, packaged Host engine.

The existing engine is shipped byte-for-byte as a runtime dependency. This
adapter alone understands legacy policy/row names and private append methods.
A hash permits relocation, not admission of arbitrary code. Historical Host
code, run state and authorization are never loaded by the default assembly.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Protocol, runtime_checkable

# Compatibility name retained for callers selecting an explicit relocation.
HOST_DURABLE = Path(__file__).resolve().parent / '_vendor' / 'dispatch_ledger_v1.py'
HOST_DURABLE_SHA = 'e8ab364abe523e91144649bae11bdde7b32b4c2812d6c6bdee6d1a1c20444df3'


@runtime_checkable
class WorkspaceLedger(Protocol):
    """A dispatch ledger, not an Agent-facing Capability or permission grant."""
    def reserve_chat(self, request_sha: str, run_id: str) -> Mapping[str, Any]: ...
    def settle(self, slot: int, response: Mapping[str, Any], output_cap: int) -> Mapping[str, Any]: ...
    def fail(self, slot: int, reason: str) -> Mapping[str, Any]: ...
    def is_settled(self) -> bool: ...
    def usage_snapshot(self) -> Mapping[str, Any]: ...


@runtime_checkable
class LedgerFactory(Protocol):
    def check_prior_scopes(self, root: Path) -> None: ...
    def open_scope(self, root: Path, policy: Mapping[str, Any]) -> WorkspaceLedger: ...


def load_host_ledger(module_path=HOST_DURABLE, expected_sha256=HOST_DURABLE_SHA):
    if expected_sha256 != HOST_DURABLE_SHA:
        raise ValueError('unqualified_host_ledger_engine')
    path = Path(module_path).resolve(strict=True)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('qualified_host_ledger_identity_changed')
    # Execute the verified bytes, not a second filesystem read via an importer.
    # This also avoids writing caches into the frozen Host directory.
    module = ModuleType('catalyst_qualified_workspace_durable')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def chat_ledger(host, root, policy):
    """Compatibility adapter; reservation/settlement persisted protocol unchanged."""
    class ChatLedger(host.Ledger):
        def __init__(self, root, *, policy):
            if policy.get('execution_profile') != 'daily':
                super().__init__(root,policy=policy)
                return
            # Same qualified locking, hash chain, fsync and settlement engine.
            # The workspace Adapter owns the additive daily metering policy;
            # the frozen experiment engine and its finite protocol stay intact.
            if policy.get('max_requests') is not None or policy.get('budget_cny') is not None:
                raise ValueError('daily_policy_cannot_impersonate_experiment')
            for key in ('reserve_cny','input_cny_per_million','output_cny_per_million','cache_hit_cny_per_million'):
                rate=Decimal(policy[key])
                if not rate.is_finite() or rate<0:raise ValueError('invalid_daily_metering_rate')
            if Decimal(policy['reserve_cny'])<=0 or not policy.get('task_id'):
                raise ValueError('daily_request_reservation_required')
            super().__init__(root,policy=None)
            self.policy=policy
            self.path=self.root/'M6B_DISPATCH_LEDGER.jsonl'
            with host.Lock(self.root/'LEDGER.lock'):
                pin=self.root/'M6B_POLICY.json'
                if not pin.exists():host.put(pin,host.canonical(policy))
                if pin.read_bytes()!=host.canonical(policy):raise ValueError('daily_policy_drift')

        def reserve_chat(self, request_sha, run_id):
            with host.Lock(self.root / 'LEDGER.lock'):
                rows = self.read()
                pending, stopped = self._dispatch_state(rows)
                if pending or stopped:
                    raise ValueError('prior_dispatch_uncertain_or_stopped')
                if (self.root / 'M6B_POLICY.json').read_bytes() != host.canonical(self.policy):
                    raise ValueError('scope_policy_changed')
                reserved = [r for r in rows if r['event'] == 'RESERVED_BEFORE_SEND']
                if self.policy.get('execution_profile')!='daily' and (len(reserved) >= self.policy['max_requests'] or
                    (len(reserved) + 1) * Decimal(self.policy['reserve_cny']) > Decimal(self.policy['budget_cny'])):
                    raise ValueError('scope_request_or_budget_limit')
                return self._append(rows, 'RESERVED_BEFORE_SEND', slot=len(reserved) + 1,
                    arm='workspace.chat', stage='chat.completion', run_id=run_id,
                    request_sha256=request_sha, reserved_cny=self.policy['reserve_cny'], task_id=self.policy['task_id'])

        def usage_snapshot(self):
            with host.Lock(self.root / 'LEDGER.lock'):
                rows = self.read()
                if (self.root / 'M6B_POLICY.json').read_bytes() != host.canonical(self.policy):
                    raise ValueError('scope_policy_changed')
                count = sum(r['event'] == 'RESERVED_BEFORE_SEND' for r in rows)
                return {'reserved_requests': count,
                        'reserved_cny': str(count * Decimal(self.policy['reserve_cny'])),
                        'settled': self.is_settled()}
    return ChatLedger(root, policy=policy)


class PinnedHostLedgerFactory:
    """Qualified deployment adapter: same engine may live at another local path.

    New engine identities require a separate code/admission review; passing a
    matching self-computed hash for unqualified code does not authorize loading.
    Factory injection is trusted Host assembly, not a browser input contract.
    """
    def __init__(self, module_path=HOST_DURABLE, expected_sha256=HOST_DURABLE_SHA):
        if expected_sha256 != HOST_DURABLE_SHA:
            raise ValueError('unqualified_host_ledger_engine')
        self.module_path = Path(module_path)
        self.expected_sha256 = expected_sha256

    def _load(self):
        return load_host_ledger(self.module_path, self.expected_sha256)

    def check_prior_scopes(self, root):
        host = self._load()
        # Only the caller's own UI scopes. Never enumerate historical campaigns.
        scopes = Path(root)
        for scope in scopes.iterdir() if scopes.exists() else ():
            if not scope.is_dir():
                continue
            pin = scope / 'M6B_POLICY.json'
            if not pin.exists():
                if (scope / 'M6B_DISPATCH_LEDGER.jsonl').exists():
                    raise ValueError('previous_scope_policy_missing')
                continue
            policy = json.loads(pin.read_text(encoding='utf-8'))
            if not chat_ledger(host,pin.parent,policy).is_settled():
                raise ValueError('previous_scope_requires_manual_reconciliation')

    def open_scope(self, root, policy):
        # Defensive copy of the scope policy; any later drift still fails closed.
        immutable_input = json.loads(json.dumps(dict(policy)))
        return chat_ledger(self._load(), root, immutable_input)
