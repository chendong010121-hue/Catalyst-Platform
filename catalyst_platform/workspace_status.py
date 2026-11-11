"""Read the local Workspace as it is, for the assistant to answer from.

The chat used to describe the system from the fixed application text and the
Catalog index. This module reads the same artifacts the product already writes:
run results, the R4 event log (including reported token and cache usage), the
workspace configuration files, the live Catalog and the model/ledger scope.
Nothing is inferred: an unreadable or absent artifact is reported as such.

The capability is read-only, local and bounded. It never opens the credential
store and never returns a key.
"""
from __future__ import annotations

import json
import os
import platform
import threading
from datetime import datetime, timezone
from pathlib import Path

from agent_runtime.contracts import CapabilityDescriptor as RuntimeCapabilityDescriptor
from agent_runtime.contracts import Failure, Success


CAPABILITY_ID = 'workspace_status'
CAPABILITY_VERSION = '1.0.0'
MAX_RESULT_RECORDS = 100
RECENT_RUNS = 8
RECENT_EVENTS = 12
RECENT_CALLS = 20
LOG_TAIL_BYTES = 512 * 1024
MAX_RESULT_BYTES = 1_000_000

_SECTIONS = ('all', 'state', 'runs', 'logs', 'config')
_CONFIG_FILES = (
    ('profile', 'workspace-settings/profile.json'),
    ('model_preferences', 'workspace-settings/model-preferences.json'),
    ('connection', 'workspace-settings/connection.json'),
    ('model_qualification', 'workspace-settings/model-qualification.json'),
    ('chat_thread', 'workspace-settings/chat-thread.json'),
    ('capabilities', 'capabilities.json'),
    ('scopes', 'scopes.json'),
    ('run_products', 'run-products.json'),
)
_WATCHED_EVENTS = {
    'request.started', 'request.failed', 'request.terminal', 'llm.request.failed',
    'llm.response.received', 'tool.result', 'tool.execution.denied',
    'tool.execution.unresolved', 'result.emitted', 'authorization.decided',
}
_DIRECTORIES = ('user-results', 'traces', 'sessions', 'wiki', 'captures', 'maintenance')


def _utc(moment: float) -> str:
    return datetime.fromtimestamp(moment, timezone.utc).isoformat(timespec='seconds')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _read_json(path: Path):
    try:
        if path.stat().st_size > MAX_RESULT_BYTES:
            return None
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _modified(path: Path) -> str | None:
    try:
        return _utc(path.stat().st_mtime)
    except OSError:
        return None


def _file_row(root: Path, relative: str) -> dict:
    path = root / relative
    try:
        stat = path.stat()
    except OSError:
        return {'file': relative, 'present': False}
    return {'file': relative, 'present': True, 'bytes': stat.st_size,
            'modified_at': _utc(stat.st_mtime)}


def _run_rows(state_root: Path) -> tuple[list[dict], int]:
    results = state_root / 'user-results'
    try:
        paths = sorted(results.glob('run_*.json'), key=lambda item: item.stat().st_mtime_ns,
                       reverse=True)[:MAX_RESULT_RECORDS]
    except OSError:
        return [], 0
    rows = []
    for path in paths:
        record = _read_json(path)
        if not isinstance(record, dict):
            rows.append({'run_id': path.stem, 'unreadable': True})
            continue
        budget = record.get('budget') if isinstance(record.get('budget'), dict) else {}
        error = record.get('error') if isinstance(record.get('error'), dict) else {}
        rows.append({
            'run_id': record.get('run_id') or path.stem,
            'task_type': record.get('task_type'),
            'state': record.get('state'),
            'mode': record.get('mode'),
            'provider': record.get('provider'),
            'model': record.get('model'),
            'external_calls': record.get('external_calls'),
            'input_tokens': budget.get('input_tokens'),
            'output_tokens': budget.get('output_tokens'),
            'charged_cny': budget.get('charged_cny'),
            'error': error.get('code'),
            'status_read_verified': record.get('workspace_status_read_verified'),
            'asset_read_verified': record.get('asset_read_verified'),
            'modified_at': _modified(path),
        })
    return rows, len(paths)


def _event_lines(state_root: Path) -> list[dict]:
    path = state_root / 'traces' / 'runs.jsonl'
    try:
        with path.open('rb') as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - LOG_TAIL_BYTES))
            raw = handle.read(LOG_TAIL_BYTES).decode('utf-8', 'replace')
    except OSError:
        return []
    lines = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            lines.append(value)
    return lines


def _logs_and_usage(state_root: Path) -> tuple[dict, dict]:
    events = _event_lines(state_root)
    watched = [{'timestamp': event.get('timestamp'), 'run_id': event.get('run_id'),
                'event_type': event.get('event_type'),
                'status': event.get('status') or event.get('terminal_status'),
                'error_type': event.get('error_type'),
                'error_code': event.get('error_code') or event.get('error_type')}
               for event in events if event.get('event_type') in _WATCHED_EVENTS]
    calls = []
    for event in events:
        if event.get('event_type') != 'llm.response.received':
            continue
        total = event.get('input_tokens')
        hit = event.get('cache_hit_input_tokens')
        miss = event.get('cache_miss_input_tokens')
        calls.append({
            'timestamp': event.get('timestamp'), 'run_id': event.get('run_id'),
            'model': event.get('model'), 'input_tokens': total,
            'output_tokens': event.get('output_tokens'),
            'cache_hit_input_tokens': hit, 'cache_miss_input_tokens': miss,
            'cache_hit_rate': round(hit / total, 4) if isinstance(hit, int) and isinstance(total, int) and total > 0 else None,
        })
    recent_calls = calls[-RECENT_CALLS:]
    measured = [call for call in recent_calls if call['cache_hit_rate'] is not None]
    usage = {
        'window_calls': len(calls),
        'recent': recent_calls,
        'measured_calls': len(measured),
        'measured_input_tokens': sum(call['input_tokens'] for call in measured),
        'measured_cache_hit_input_tokens': sum(call['cache_hit_input_tokens'] for call in measured),
        'input_tokens': sum(call['input_tokens'] or 0 for call in recent_calls if isinstance(call['input_tokens'], int)),
        'output_tokens': sum(call['output_tokens'] or 0 for call in recent_calls if isinstance(call['output_tokens'], int)),
        'cache_hit_input_tokens': sum(call['cache_hit_input_tokens'] or 0 for call in recent_calls if isinstance(call['cache_hit_input_tokens'], int)),
        'cache_hit_rate': round(sum(call['cache_hit_input_tokens'] or 0 for call in measured)
                                / max(1, sum(call['input_tokens'] or 0 for call in measured)), 4)
        if measured else None,
    }
    logs = {'event_lines_read': len(events), 'recent': watched[-RECENT_EVENTS:],
            'recent_failures': sum(1 for event in watched if event.get('event_type') in
                                   ('request.failed', 'llm.request.failed', 'tool.execution.denied'))}
    return logs, usage


def _catalog_rows(app) -> dict:
    try:
        active = {(descriptor.id, descriptor.capability_version)
                  for descriptor in app._catalog.registry.list()
                  if app._catalog.is_active(descriptor.id, descriptor.capability_version)}
        descriptors = app._catalog.registry.list()
    except (AttributeError, OSError, ValueError):
        return {'items': [], 'active': 0, 'error': 'catalog_unreadable'}
    items = [{
        'id': descriptor.id, 'version': descriptor.capability_version,
        'side_effect': descriptor.execution.get('side_effect'),
        'active': (descriptor.id, descriptor.capability_version) in active,
    } for descriptor in sorted(descriptors, key=lambda row: (row.id, row.capability_version))]
    return {'items': items, 'active': sum(1 for item in items if item['active'])}


def _model_row(settings) -> dict:
    try:
        snapshot = settings.snapshot()
    except (AttributeError, OSError, ValueError):
        return {'error': 'settings_unreadable'}
    budget = snapshot.get('budget') if isinstance(snapshot.get('budget'), dict) else {}
    return {
        'configured': snapshot.get('configured'),
        'enabled': snapshot.get('enabled'),
        'connection_mode': snapshot.get('connection_mode'),
        'provider_id': snapshot.get('provider_id'),
        'model': snapshot.get('model'),
        'key_status': snapshot.get('key_status'),
        'qualification_status': snapshot.get('qualification_status'),
        'stop_reason': snapshot.get('stop_reason'),
        'scope': snapshot.get('scope'),
        'allow_asset_read': snapshot.get('allow_asset_read'),
        'allow_project_read': snapshot.get('allow_project_read'),
        'saved_credential_available': snapshot.get('saved_credential_available'),
        'credential_persistence': snapshot.get('credential_persistence'),
        'input_token_limit': snapshot.get('input_token_limit'),
        'reserved_requests': snapshot.get('reserved_requests'),
        'authorization_reserved_cny': snapshot.get('authorization_reserved_cny'),
        'history_turns': snapshot.get('history_turns'),
        'budget': {key: budget.get(key) for key in
                   ('attempts', 'max_requests', 'charged_cny', 'budget_cny', 'last_status',
                    'input_tokens', 'output_tokens', 'uncertain')},
    }


def _directory_rows(state_root: Path) -> dict:
    rows = {}
    for name in _DIRECTORIES:
        path = state_root / name
        try:
            rows[name] = sum(1 for _ in path.iterdir()) if path.is_dir() else None
        except OSError:
            rows[name] = None
    return rows


def collect(session) -> dict:
    """One bounded reading of this Workspace. Missing data stays missing."""
    app = session.app
    state_root = Path(app.state_root)
    runs, indexed = _run_rows(state_root)
    logs, usage = _logs_and_usage(state_root)
    config = [_file_row(state_root, relative) for _name, relative in _CONFIG_FILES]
    by_state, by_mode = {}, {}
    for row in runs:
        state = row.get('state') or 'UNRECORDED'
        by_state[state] = by_state.get(state, 0) + 1
        mode = row.get('mode') or 'UNRECORDED'
        by_mode[mode] = by_mode.get(mode, 0) + 1
    snapshot = {
        'generated_at': _now(),
        'workspace': {
            'root': str(session.workspace),
            'state_root': str(state_root),
            'input_root': str(session.input_root),
            'backend': getattr(session, 'backend', None),
            'mode': getattr(session, 'mode', None),
            'session_id': getattr(session, 'session_id', None),
            'source_identity': getattr(session, 'source_identity', None),
        },
        'process': {'pid': os.getpid(), 'python': platform.python_version(),
                    'platform': platform.platform()},
        'model': _model_row(session.settings),
        'catalog': _catalog_rows(app),
        'runs': {
            'total': indexed,
            'by_state': by_state,
            'by_mode': by_mode,
            'recent': runs[:RECENT_RUNS],
        },
        'logs': logs,
        'usage': usage,
        'config': {
            'files': config,
            'present': sum(1 for row in config if row['present']),
            'total': len(config),
        },
        'directories': _directory_rows(state_root),
    }
    return snapshot


def section_view(snapshot: dict, section: str) -> dict:
    """Project the snapshot to one question's needs without changing its facts."""
    if section not in _SECTIONS:
        raise ValueError('invalid_workspace_status_section')
    workspace = {key: snapshot['workspace'][key] for key in ('backend', 'mode')}
    identity = snapshot['workspace']['source_identity']
    if isinstance(identity, dict):
        workspace['source_identity'] = {key: identity.get(key) for key in ('commit', 'tree', 'dirty')}
    if section == 'all':
        return {'section': section, **snapshot, 'workspace': workspace}
    selected = {'generated_at': snapshot['generated_at'], 'section': section}
    if section == 'state':
        selected.update({key: snapshot[key] for key in ('process', 'model', 'catalog', 'directories')})
        selected['workspace'] = workspace
    elif section == 'runs':
        selected['runs'] = snapshot['runs']
    elif section == 'logs':
        selected['logs'] = snapshot['logs']
        selected['usage'] = snapshot['usage']
    elif section == 'config':
        selected['config'] = snapshot['config']
    return selected


def render_text(snapshot: dict) -> str:
    """A factual local summary for the no-model path; no model, no brochure."""
    workspace = snapshot['workspace']
    model = snapshot['model']
    runs = snapshot['runs']
    logs = snapshot['logs']
    usage = snapshot['usage']
    config = snapshot['config']
    catalog = snapshot['catalog']
    states = '，'.join(f'{key} {value}' for key, value in sorted(runs['by_state'].items())) or '无'
    lines = [
        f'Catalyst Workplace 本机状态（{snapshot["generated_at"]}）',
        f'- 工作区：{workspace["root"]}；会话 {workspace["session_id"]}；状态目录 {workspace["state_root"]}',
        f'- 模型：{model.get("model")} · {"可用" if model.get("enabled") else "不可用"}'
        f'（{model.get("stop_reason") or "无停止原因"}）；本轮未调用模型。',
        f'- 能力目录：{len(catalog["items"])} 项登记，{catalog["active"]} 项当前激活；登记不等于授权。',
        f'- 运行记录：{runs["total"]} 条（{states}）。',
    ]
    if runs['recent']:
        latest = runs['recent'][0]
        lines.append(f'- 最近记录：{latest.get("run_id")} · {latest.get("task_type")} · '
                     f'{latest.get("state")}')
    failures = [event for event in logs['recent'] if event.get('event_type') in
                ('request.failed', 'llm.request.failed', 'tool.execution.denied')]
    lines.append(f'- 事件日志：读取 {logs["event_lines_read"]} 条，最近 {len(logs["recent"])} 条中失败 {len(failures)} 次'
                 + (f'（{", ".join(sorted({event.get("error_code") or event.get("event_type") for event in failures}))}）' if failures else '') + '。')
    if usage['measured_calls']:
        lines.append(f'- Token：最近 {usage["measured_calls"]} 次已计量模型响应，输入 {usage["measured_input_tokens"]}，'
                     f'缓存命中 {usage["measured_cache_hit_input_tokens"]}（{usage["cache_hit_rate"]:.1%}）。')
    else:
        lines.append('- Token：本机记录中没有可用的缓存命中数据。')
    lines.append(f'- 配置：{config["present"]}/{config["total"]} 个已知配置文件存在。')
    lines.append('这是对本机文件与记录的直接读取，不是模型推断。需要更细的日志或配置时可直接查看 Observability 或设置页。')
    return '\n'.join(lines)


class WorkspaceStatusCapability:
    """Read this Workspace's own state, event log and configuration."""

    id = CAPABILITY_ID

    def __init__(self, session) -> None:
        self.session = session
        self._lock = threading.RLock()

    def describe(self):
        return RuntimeCapabilityDescriptor(
            id=self.id,
            name='Local workspace status',
            description=('读取本机工作区的真实状态：运行记录与终态、R4 事件日志与 Token/缓存用量、'
                         '配置文件是否存在、能力目录、模型连接与费用账本、关键目录计数。'
                         '只读本机文件；不访问网络，不返回密钥。'
                         'section 选 all（全部）、state（工作区/模型/目录）、runs、logs（含用量）或 config。'),
            input_schema={
                'type': 'object',
                'properties': {'section': {'type': 'string',
                                           'enum': list(_SECTIONS)}},
                'required': ['section'],
                'additionalProperties': False,
            },
            output_schema={'type': 'object'},
        )

    def invoke(self, parameters, context):
        section = parameters.get('section', 'all') if isinstance(parameters, dict) else 'all'
        if section not in _SECTIONS:
            return Failure('section must be one of ' + ', '.join(_SECTIONS))
        try:
            with self._lock:
                snapshot = collect(self.session)
        except (OSError, ValueError, RuntimeError):
            return Failure('workspace_status_unavailable')
        return Success(section_view(snapshot, section))
