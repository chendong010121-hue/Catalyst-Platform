"""Loopback contract for the read-only capability review route."""
import json
import threading
from urllib.request import urlopen

import pytest

from catalyst_platform.workspace_ui import create_workspace_server


@pytest.fixture
def service(tmp_path):
    server = create_workspace_server(tmp_path / 'workspace', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_address[1]}'
    yield base
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def get(base, path):
    with urlopen(base + path, timeout=10) as response:
        return json.load(response)


def test_capability_review_is_read_only_and_empty_without_declarations(service):
    value = get(service, '/api/capability-review')
    assert value['write_enabled'] is False
    assert value['scope'] == 'READ_ONLY_COMPARISON_NO_WIKI_WRITE'
    assert value['source'] == 'workspace'
    assert value['items'] == [] and value['claims'] == []
