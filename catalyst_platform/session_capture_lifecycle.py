"""Control ownership for captures on the existing WorkspaceUserSession.

This adapter owns no runner, provider scope, task approval or execution loop.
"""
from contextlib import contextmanager


class SessionCaptureLifecycle:
    def __init__(self, session, recorder):
        self.session = session
        self.recorder = recorder
        self.finalized = False

    @property
    def execution(self):
        return self.session._execution

    @property
    def control(self):
        return self.session._control

    @property
    def signal(self):
        signal = self.session._pending.get(self.recorder.run_id)
        if signal is None or signal.is_set():
            raise ValueError('test_cancelled')
        return signal

    def bind(self, child, *, prepare=False):
        with self.control:
            signal = self.signal
            if prepare:
                child.prepare(self.recorder)
                child._pending[self.recorder.run_id] = signal
            self.session.settings.active_run_id = self.recorder.run_id
            if not hasattr(self.session, '_capture_providers'):
                self.session._capture_providers = {}
            self.session._capture_providers[self.recorder.run_id] = child.settings.provider

    @contextmanager
    def managed(self, child, retained, key):
        """Close partially initialized subjects when admission/persistence raises."""
        try:
            yield child
        finally:
            if not self.finalized:
                self.finish(child)
                if self.unresolved(child):
                    retained[key] = child
                else:
                    self.close(child)

    def finish(self, child):
        # Both sessions may still hold registrations if result persistence failed.
        for session in (self.session, child):
            with session._control:
                session._pending.pop(self.recorder.run_id, None)
                session._recorders.pop(self.recorder.run_id, None)
                getattr(session, '_capture_providers', {}).pop(self.recorder.run_id, None)
                if session is self.session or not self.unresolved(child):
                    session.settings.active_run_id = None
        self.finalized = True

    @staticmethod
    def unresolved(child):
        return bool(getattr(child.session, '_project_pending_handles', {}) or
                    (child.settings.provider is not None and child.settings.provider.budget_snapshot['uncertain']))

    @staticmethod
    def close(child):
        try:
            child.settings.disconnect()
        finally:
            try:
                child.app.components.close_loaded()
            finally:
                child.app.plugins.close()
