import hashlib
import json
from pathlib import Path

import pytest

from catalyst_platform.components import ComponentError
from catalyst_platform.workbench import CatalystWorkbench
from catalyst_platform.evaluation_workflow import workflow_guide, prepare_workflow


def package(root, version, text):
    root.mkdir(parents=True)
    (root / 'references').mkdir()
    files = {'SKILL.md': 'development method', 'references/build-eval.md': text,
             'references/eval-audit.md': 'audit', 'references/hillclimb.md': 'iterate'}
    for name, body in files.items():
        (root / name).write_text(body, encoding='utf8')
    manifest = {'manifest_version': 1, 'component_id': 'development-workflow',
                'resource_type': 'method_data', 'version': version,
                'skill_name': 'development-workflow', 'required_product_interface': 'evaluation-workflow.v1',
                'provides': ['development-workflow'], 'requires': ['prepare_evaluation_workflow'],
                'files': {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files},
                'license_sources': [{'name': 'Catalyst', 'revision': 'fixture', 'license': 'original', 'adaptation': 'fixture'}],
                'evaluation_refs': ['offline-fixture'], 'llm_visibility': 'explicit'}
    (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf8')
    return root


def test_development_method_is_admitted_consumed_replaced_and_restored(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    lifecycle = app.components
    for version, text in [('1.0.0', 'first guide'), ('1.1.0', 'second guide')]:
        candidate = package(tmp_path / version, version, text)
        receipt = lifecycle.discover(candidate)
        lifecycle.admit(candidate, receipt['package_sha256'])
    lifecycle.activate('development-workflow', '1.0.0')
    assert workflow_guide('build-eval', lifecycle)['text'] == 'first guide'
    with lifecycle.acquire_method('development-workflow'):
        with pytest.raises(ComponentError, match='method_update_busy'):
            lifecycle.activate('development-workflow', '1.1.0')
    lifecycle.activate('development-workflow', '1.1.0')
    assert workflow_guide('build-eval', lifecycle)['text'] == 'second guide'
    record = prepare_workflow(app, 'prepare test', 'build-eval')
    assert record['skill']['source'] == 'ACTIVE_METHOD'
    assert record['skill']['version'] == '1.1.0'
    assert record['execution_authorized'] is False
    lifecycle.activate('development-workflow', '1.0.0')
    assert workflow_guide('build-eval', lifecycle)['text'] == 'first guide'


def test_corrupt_active_development_method_does_not_silently_fallback(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    source = package(tmp_path / 'source', '1.0.0', 'original')
    receipt = app.components.discover(source)
    app.components.admit(source, receipt['package_sha256'])
    app.components.activate('development-workflow', '1.0.0')
    installed = app.components.installed_root / 'development-workflow' / '1.0.0' / 'references' / 'build-eval.md'
    installed.write_text('changed', encoding='utf8')
    with pytest.raises(ComponentError):
        workflow_guide('build-eval', app.components)


def test_shipped_development_package_registers_and_is_consumed(tmp_path):
    app = CatalystWorkbench(tmp_path / 'workspace', [tmp_path])
    package_root = Path(__file__).resolve().parents[1] / 'examples/development_methods/development-workflow/0.1.0'
    receipt = app.components.discover(package_root)
    app.components.admit(package_root, receipt['package_sha256'])
    app.components.activate('development-workflow', '0.1.0')
    guide = workflow_guide('build-eval', app.components)
    assert guide['method_source'] == 'ACTIVE_METHOD'
    assert guide['package_sha256'] == receipt['package_sha256']
    assert 'Penguin-derived case organization' in guide['text']
    assert guide['execution_authorized'] is False
