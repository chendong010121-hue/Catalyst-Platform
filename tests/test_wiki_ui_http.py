"""Loopback contract for the Wiki reading surface: one model read, one page, nothing written."""
import json
import threading
from urllib.request import urlopen

import pytest

from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workspace_ui import create_workspace_server


def stage(workspace):
    inputs = workspace / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    source = inputs / "notes.md"
    source.write_text("# 组织\n\n市场营销中心负责集团品牌与市场推广。\n", encoding="utf-8")
    wiki = ProjectWiki(workspace, [inputs], enterprise_id="synthetic",
                       project_id="local-ui-demo", backend="json")
    wiki.stage_markdown(source)
    return source


@pytest.fixture
def service(tmp_path):
    workspace = tmp_path / "workspace"
    stage(workspace)
    server = create_workspace_server(workspace, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", workspace
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_the_model_route_reads_the_live_wiki_and_writes_nothing(service):
    base, workspace = service
    index = workspace / ".catalyst" / "wiki" / "synthetic" / "local-ui-demo" / "wiki.json"
    before = index.read_bytes()
    with urlopen(base + "/api/wiki/model", timeout=30) as response:
        assert response.status == 200
        assert response.headers["Cache-Control"] == "no-store"
        model = json.load(response)
    assert index.read_bytes() == before
    assert model["meta"]["scope"] == "enterprise:synthetic/project:local-ui-demo"
    assert model["meta"]["index_stable"] is True
    assert model["meta"]["verify"]["status"] == "OK"
    assert model["meta"]["sources"]["recorded"] == 1
    assert model["meta"]["sources"]["present"] == 1
    assert {page["kind"] for page in model["pages"]} >= {"overview", "index", "gaps", "log", "source"}
    assert [page["title"] for page in model["pages"] if page["kind"] == "source"] == ["notes.md"]
    assert model["evidence"] == {}


def test_the_reading_page_and_its_assets_come_from_the_same_origin(service):
    base, _ = service
    cases = (("/wiki", 'id="wk-q"', "text/html"),
             ("/wiki?page=overview.md", 'id="wk-layout"', "text/html"),
             ("/wiki.js", "/api/wiki/model", "text/javascript"),
             ("/wiki.css", ".wk-layout", "text/css"))
    for path, needle, mime in cases:
        with urlopen(base + path, timeout=10) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200, path
            assert needle in body, path
            assert response.headers["Content-Type"].startswith(mime), path
            assert "default-src 'self'" in response.headers["Content-Security-Policy"], path
