"""Runtime-qualified project cleanup; pending runs keep their method lease."""
from contextlib import contextmanager
from types import SimpleNamespace
import threading

import pytest

from catalyst_platform import project_understand as module


class Session:
    def __init__(self, *, releasable=True, submitted=True, status="success"):
        self.leases = 0
        self.releases = []
        self.releasable = releasable
        self.submitted = submitted
        self.status = status
        self.app = SimpleNamespace(components=self)

    @contextmanager
    def acquire_method(self, component):
        self.leases += 1
        try:
            yield {"component_id": component, "version": "0.1.0", "package_sha256": "f" * 64}
        finally:
            self.leases -= 1

    def tool_execution_count(self, name):
        return 0

    def ask(self, *args, **kwargs):
        kwargs["recorder"].session_id = "runtime-session"
        if self.submitted:
            kwargs["project_context"].result = {"candidate": True}
        return SimpleNamespace(session_id="runtime-session", result=SimpleNamespace(status=self.status, error=None))

    def release_completed_run(self, session_id):
        self.releases.append(session_id)
        return self.releasable


@pytest.fixture
def context(monkeypatch):
    def fake(*args):
        return SimpleNamespace(result=None, evidence=[], source_reads=[], manifest=[], source_manifest_sha256="a" * 64,
                               method_reads=[], source_warnings=[], structural_facts=[], unsupported_sources=[], expansion_receipts=[])
    monkeypatch.setattr(module, "ProjectAnalysisContext", fake)


def invoke(session):
    return module.run_project_analysis(session, SimpleNamespace(objective="inspect"), ".", provider=object(),
                                       recorder=SimpleNamespace(run_id="run-exact", session_id=None))


def test_completed_run_releases_original_handle_and_method(context):
    session = Session()
    result = invoke(session)
    assert session.releases == ["runtime-session"]
    assert session.leases == 0
    assert result["lifecycle"]["handle_released"] is True


def test_terminal_failure_keeps_exact_session_identity_and_cleans_up(context):
    session = Session(submitted=False)
    with pytest.raises(module.ProjectAnalysisError) as caught:
        invoke(session)
    assert caught.value.session_id == "runtime-session"
    assert caught.value.lifecycle["handle_released"] is True
    assert session.leases == 0


def test_pending_runtime_retains_snapshot_lease_and_handle(context):
    session = Session(releasable=False, submitted=False, status="interrupted")
    with pytest.raises(module.ProjectAnalysisError) as caught:
        invoke(session)
    assert caught.value.session_id == "runtime-session"
    assert caught.value.lifecycle["method_lease_retained"] is True
    assert session.leases == 1
    held = session._project_pending_handles["runtime-session"]
    assert held["run_id"] == "run-exact"
    assert held["session_id"] == "runtime-session"
    assert "lease" in held and "context" in held


def test_cleanup_error_preserves_pending_method_and_original_failure(context):
    session = Session(submitted=False)
    def broken(_):
        raise RuntimeError("cleanup unavailable")
    session.release_completed_run = broken
    with pytest.raises(module.ProjectAnalysisError, match="project_not_submitted") as caught:
        invoke(session)
    assert caught.value.lifecycle["release_error_type"] == "RuntimeError"
    assert caught.value.lifecycle["method_lease_retained"] is True
    assert session.leases == 1


def test_raised_runtime_keeps_recorder_bound_identity_and_lease(context):
    session = Session(releasable=False)
    def fail(*args, **kwargs):
        kwargs["recorder"].session_id = "runtime-session"
        raise RuntimeError("runtime publication failed")
    session.ask = fail
    with pytest.raises(RuntimeError, match="publication failed") as caught:
        invoke(session)
    assert caught.value.session_id == "runtime-session"
    assert caught.value.lifecycle["method_lease_retained"] is True
    assert session.leases == 1


@pytest.mark.parametrize("pending", [False, True])
def test_workspace_projects_keep_failure_identity_and_pending_settings_barrier(monkeypatch, tmp_path, pending):
    from catalyst_platform.workspace_session import WorkspaceUserSession
    recorder = SimpleNamespace(run_id="request-run", request_id="request-id",
                               event=lambda *args, **kwargs: None, finish=lambda *args, **kwargs: None)
    settings = SimpleNamespace(lock=threading.RLock(), transport_override=object(), provider=object(),
                               active_run_id=None, snapshot=lambda: {"enabled": True})
    app = SimpleNamespace(state_root=tmp_path, _atomic_json=lambda *args: None)
    harness = SimpleNamespace()
    host = SimpleNamespace(_execution=threading.Lock(), _control=threading.RLock(), settings=settings,
                           mode="MOCK", session=harness, app=app, _pending={}, _recorders={})
    def prepare(rec):
        host._pending[rec.run_id] = threading.Event()
        host._recorders[rec.run_id] = rec
    host.prepare = prepare
    def fail(*args, **kwargs):
        if pending:
            harness._project_pending_handles = {"exact-session": {"run_id": recorder.run_id}}
        error = module.ProjectAnalysisError("project_not_submitted")
        error.session_id = "exact-session"
        error.lifecycle = {"handle_released": not pending, "method_lease_retained": pending}
        raise error
    monkeypatch.setattr(module, "run_project_analysis", fail)
    result = WorkspaceUserSession.analyze_project(host, {"root": tmp_path, "object_type": "agent"}, "inspect", 1, recorder)
    assert result["session_id"] == "exact-session"
    assert result["state"] == ("UNRESOLVED" if pending else "FAILED")
    assert settings.active_run_id == (recorder.run_id if pending else None)
    assert not host._pending


def test_unresolved_project_blocks_programmatic_chat_without_clearing_scope(tmp_path):
    from catalyst_platform.workspace_session import WorkspaceUserSession
    from catalyst_platform.observability import RunRecorder
    from catalyst_platform.trace_log import JsonlTraceStore
    host=WorkspaceUserSession(tmp_path/'workspace')
    host.session._project_pending_handles={'runtime-unknown':{'run_id':'retained-run'}}
    host.settings.active_run_id='retained-run'
    rec=RunRecorder(JsonlTraceStore(host.workspace),run_id='run_blocked_chat',request_id='req_blocked_chat',invocation_id='inv_blocked_chat')
    rec.start(request_kind='natural_language_ask')
    result=host('hello',None,rec)
    assert result['state']=='BLOCKED'
    assert result['error']['code']=='PROJECT_RUNTIME_RECONCILIATION_REQUIRED'
    assert result['external_calls']==0 and host.settings.active_run_id=='retained-run'
