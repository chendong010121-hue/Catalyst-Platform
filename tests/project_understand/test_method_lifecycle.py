"""Data-only method admission and frozen run leases over the existing lifecycle."""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from catalyst_platform.components import ComponentError
from catalyst_platform.workbench import CatalystWorkbench


def package(root, version="0.1.0", *, text="method instructions"):
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(text, encoding="utf-8")
    (root / "references").mkdir()
    (root / "references" / "depth.md").write_text("D0 then D1", encoding="utf-8")
    manifest = {
        "manifest_version": 1, "component_id": "project-understand",
        "resource_type": "method_data", "version": version,
        "skill_name": "understand-project", "required_product_interface": "project-analysis.v1",
        "provides": ["understand-project"],
        "requires": ["project_inspect", "project_expand_evidence", "project_submit_analysis"],
        "files": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                  for name in ["SKILL.md", "references/depth.md"]},
        "license_sources": [{"name": "Catalyst", "revision": "local-v0", "license": "original", "adaptation": "original method"}],
        "evaluation_refs": ["offline-lifecycle-fixture"], "llm_visibility": "explicit",
    }
    save_manifest(root, manifest)
    return root


def save_manifest(root, value):
    (root / "manifest.json").write_text(json.dumps(value), encoding="utf-8")


def admit(methods, source):
    receipt = methods.discover(source)
    methods.admit(source, receipt["package_sha256"])
    return receipt


def test_method_versions_lease_update_rollback_and_cold_load(tmp_path, monkeypatch):
    bench = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"])
    methods = bench.components
    old = admit(methods, package(tmp_path / "old"))
    new = admit(methods, package(tmp_path / "new", "0.1.1", text="lifecycle fixture"))
    monkeypatch.setattr(methods, "_load_admitted", lambda *a: pytest.fail("method imported as Tool"))
    assert methods.activate("project-understand", "0.1.0")["transition"] == "activated"
    with methods.acquire_method() as frozen:
        assert frozen["package_sha256"] == old["package_sha256"]
        assert frozen["files"]["SKILL.md"] == "method instructions"
        for target in (frozen, frozen["files"], frozen["manifest"], frozen["manifest"]["files"]):
            with pytest.raises(TypeError):
                target["bad"] = "changed"
        assert methods.activate("project-understand", "0.1.0")["transition"] == "no-op"
        with pytest.raises(ComponentError, match="method_update_busy"):
            methods.activate("project-understand", "0.1.1")
        with pytest.raises(ComponentError, match="method_update_busy"):
            methods.deactivate("project-understand")
    methods.activate("project-understand", "0.1.1")
    with methods.acquire_method() as frozen:
        assert frozen["package_sha256"] == new["package_sha256"]
    cold = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    cold.load_active()
    with cold.acquire_method() as frozen:
        assert frozen["version"] == "0.1.1"
    assert methods.activate("project-understand", "0.1.0")["transition"] == "restored"
    row = methods.list_components()[0]
    assert row["resource_type"] == "method_data"
    assert all(v["resource_type"] == "method_data" for v in row["versions"])
    methods.deactivate("project-understand")
    assert len(methods.list_components()[0]["versions"]) == 2
    with pytest.raises(ComponentError, match="active"):
        methods.acquire_method().__enter__()


@pytest.mark.parametrize("mutation", ["sha", "escape", "absolute", "backslash", "script", "unlisted", "interface", "requires", "visibility", "utf8", "oversized", "total", "json_duplicate", "wrong_skill"])
def test_method_package_rejects_unsafe_data(tmp_path, mutation):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    source = package(tmp_path / "method")
    manifest = json.loads((source / "manifest.json").read_text())
    if mutation == "sha":
        (source / "SKILL.md").write_text("tampered", encoding="utf-8")
    elif mutation in ("escape", "absolute", "backslash", "script"):
        name = {"escape": "../outside.md", "absolute": "C:/outside.md", "backslash": "references\\outside.md", "script": "references/run.py"}[mutation]
        manifest["files"][name] = "0" * 64
    elif mutation == "unlisted":
        (source / "references" / "run.py").write_text("raise RuntimeError()")
    elif mutation == "interface":
        manifest["required_product_interface"] = "unknown.v999"
    elif mutation == "requires":
        manifest["requires"] = ["execute_shell"]
    elif mutation == "visibility":
        manifest["llm_visibility"] = "automatic"
    elif mutation == "wrong_skill":
        manifest["skill_name"] = "arbitrary"
    elif mutation in ("utf8", "oversized"):
        data = b"\xff" if mutation == "utf8" else b"x" * (128 * 1024 + 1)
        (source / "SKILL.md").write_bytes(data)
        manifest["files"]["SKILL.md"] = hashlib.sha256(data).hexdigest()
    elif mutation == "total":
        for n in range(5):
            data = b"x" * (128 * 1024)
            name = f"references/{n}.md"
            (source / name).write_bytes(data)
            manifest["files"][name] = hashlib.sha256(data).hexdigest()
    elif mutation == "json_duplicate":
        (source / "manifest.json").write_text('{"resource_type":"method_data","resource_type":"method_data"}')
        with pytest.raises(ComponentError):
            methods.discover(source)
        return
    save_manifest(source, manifest)
    with pytest.raises(ComponentError):
        methods.discover(source)
    assert methods.list_components() == []


def test_method_conflicting_identity_and_failed_activation_preserve_pointer(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "old"))
    admit(methods, package(tmp_path / "next", "0.1.1"))
    methods.activate("project-understand", "0.1.0")
    changed = package(tmp_path / "changed", text="different bytes same version")
    with pytest.raises(ComponentError, match="different source identity"):
        admit(methods, changed)
    installed = methods.installed_root / "project-understand" / "0.1.1" / "SKILL.md"
    installed.write_text("corrupt", encoding="utf-8")
    with pytest.raises(ComponentError):
        methods.activate("project-understand", "0.1.1")
    with methods.acquire_method() as frozen:
        assert frozen["version"] == "0.1.0"


def test_method_symlink_and_junction_are_rejected(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    source = package(tmp_path / "method")
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    path = source / "references" / "depth.md"
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Host does not permit symlinks")
    with pytest.raises(ComponentError):
        methods.discover(source)


def test_lease_releases_after_exception_and_snapshot_is_detached(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    admit(methods, package(tmp_path / "method"))
    methods.activate("project-understand", "0.1.0")
    with pytest.raises(RuntimeError):
        with methods.acquire_method() as frozen:
            (methods.installed_root / "project-understand" / "0.1.0" / "SKILL.md").write_text("changed")
            assert frozen["files"]["SKILL.md"] == "method instructions"
            raise RuntimeError("run failed")
    methods.deactivate("project-understand")


def test_method_manifest_bytes_are_part_of_package_identity(tmp_path):
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    source = package(tmp_path / "method")
    original = admit(methods, source)
    manifest = source / "manifest.json"
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    altered = methods.discover(source)
    assert altered["package_sha256"] != original["package_sha256"]
    with pytest.raises(ComponentError, match="different source identity"):
        methods.admit(source, altered["package_sha256"])


def test_windows_directory_junction_rejected_without_symlink_privilege(tmp_path):
    import os
    if os.name != "nt":
        pytest.skip("Windows junction check")
    methods = CatalystWorkbench(tmp_path / "workspace", [tmp_path / "wiki"]).components
    source = package(tmp_path / "method")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "outside.md").write_text("must not read")
    link = source / "references" / "linked"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
    assert result.returncode == 0, result.stderr
    try:
        with pytest.raises(ComponentError, match="symlinks|reparse"):
            methods.discover(source)
    finally:
        link.rmdir()
