from catalyst_platform.workbench import CatalystWorkbench


def test_host_can_inject_existing_port_skill_root(tmp_path):
    root=tmp_path/'frozen-method';root.mkdir()
    app=CatalystWorkbench(tmp_path/'work',[tmp_path],understand_skill_root=root)
    assert app.plugins.service('understand.port')._port._resolver.root==root.resolve()


def test_default_port_method_root_is_unchanged(tmp_path):
    app=CatalystWorkbench(tmp_path/'work',[tmp_path])
    from catalyst_platform.understand_only import _SKILL_ROOT
    assert app.plugins.service('understand.port')._port._resolver.root==_SKILL_ROOT.resolve()
