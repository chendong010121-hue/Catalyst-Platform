"""A session snapshot still lands when its workspace is deeper than Windows' path limit.

The platform evaluation case runs five directories below its workspace, and the atomic
write adds a temporary file beside the session file, so a readable layout passes
``MAX_PATH`` without anyone writing a long name. Windows then refuses the plain path;
the store must hand over the extended-length form instead.
"""

from __future__ import annotations

import os
from pathlib import Path

from agent_runtime.contracts import Goal, SessionSnapshot
from catalyst_platform.storage import JsonFileStateStore, _os_path

SESSION_ID = "session_" + "b" * 48


def _deep_directory(root: Path) -> Path:
    """Grow the directory in steps, each one still short enough for Windows to create."""
    segment = "workspace_segment_that_keeps_going"
    directory = root
    while len(os.fspath(directory / segment)) <= 240:
        directory = directory / segment
        directory.mkdir()
    return directory


def test_a_snapshot_round_trips_past_the_windows_path_limit(tmp_path):
    directory = _deep_directory(tmp_path)
    path = directory / f"{SESSION_ID}.json"
    if os.name == "nt":
        # The session file is the path Windows would refuse, and the temporary file
        # beside it is longer still.
        assert len(os.fspath(path)) > 260
        assert _os_path(path).startswith("\\\\?\\")

    snapshot = SessionSnapshot(
        session_id=SESSION_ID,
        goal=Goal("keep a session recoverable from a deep workspace"),
        state={"step": 3, "note": "deep"},
    )
    store = JsonFileStateStore(directory)
    store.commit(snapshot)

    assert store.load(SESSION_ID) == snapshot
    assert os.path.isfile(_os_path(path))
    # Nothing but the session file is left: the temporary file went away.
    assert os.listdir(directory) == [f"{SESSION_ID}.json"]


def test_a_short_path_is_handed_over_unchanged(tmp_path):
    short = Path(tmp_path) / "sessions" / "session_short.json"
    assert _os_path(short) == os.fspath(short)
