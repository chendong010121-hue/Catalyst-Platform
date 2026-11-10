from catalyst_platform.asset_records import builtin_assets
from catalyst_platform.workbench import CatalystWorkbench


def test_development_assets_register_without_claiming_execution(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    rows = {row['asset_id']: row for row in builtin_assets()}
    assert rows['system.evaluation']['kind'] == 'service'
    assert rows['system.development-workflow']['kind'] == 'service'
    assert rows['method.project-acceptance']['kind'] == 'method'
    assert rows['method.evaluation-entry']['kind'] == 'method'
    before = app._catalog.list()
    app.components.assets.register(list(rows.values()))
    assert app._catalog.list() == before
    cold = CatalystWorkbench(app.workspace, app.wiki_roots)
    records = {row['asset_id']: row for row in cold.components.assets.list()}
    for key in ('system.evaluation', 'system.development-workflow',
                'method.project-acceptance', 'method.evaluation-entry'):
        assert records[key]['integrity'] == 'MATCH'
        assert not records[key]['execution_authorized']
