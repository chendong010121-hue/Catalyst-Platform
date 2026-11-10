"""The daily entry says which assembly read the document, and a merge does not enable one.

Two assemblies exist. A workspace with an admitted and activated method reads under that
method's lease and the result names the package, the concept set, the extraction mode and
the implementation. A workspace with none still lets the document into Wiki, and the result
says the product's own Skill tree read it. What it must never do is let the second look
like the first.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from agent_runtime.contracts import ModelResponse

from catalyst_platform.components import ComponentError
from catalyst_platform.knowledge_intake import intake_source
from catalyst_platform.semantic_method import SEMANTIC_COMPONENT, SEMANTIC_INTERFACE, SEMANTIC_SERVICES, SEMANTIC_SKILL
from catalyst_platform.wiki import ProjectWiki
from catalyst_platform.workbench import CatalystWorkbench

TEXT = "新设数字化运营中心，负责集团数据资产。\n"


class _OneEntity:
    """One entity, answered offline: no network, no key, no spend."""

    model = "intake-fixture"
    structured_output_token_limit = 4096
    model_output_token_limit = 8192

    def request(self, request):
        evidence = json.loads(request.messages[-1].content)["evidence"][0]["evidence_id"]
        return ModelResponse(content=json.dumps({"items": [
            {"kind": "entity", "key": "digital_ops", "meaning": "数字化运营中心",
             "evidence_class": "SOURCE_DIRECT", "evidence_refs": [evidence]}]},
            ensure_ascii=False), finish_reason="stop")


def _package(root, version="0.1.0"):
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        f"---\nname: {SEMANTIC_SKILL}\nversion: {version}\ndescription: intake fixture\n---\n\nINTAKE-MARKER\n",
        encoding="utf-8")
    manifest = {
        "manifest_version": 1, "component_id": SEMANTIC_COMPONENT, "resource_type": "method_data",
        "version": version, "skill_name": SEMANTIC_SKILL,
        "required_product_interface": SEMANTIC_INTERFACE,
        "provides": ["enterprise-ontology"], "requires": sorted(SEMANTIC_SERVICES),
        "files": {"SKILL.md": hashlib.sha256((root / "SKILL.md").read_bytes()).hexdigest()},
        "license_sources": [{"name": "Catalyst", "revision": "fixture", "license": "original",
                             "adaptation": "fixture"}],
        "evaluation_refs": ["fixture"], "llm_visibility": "explicit",
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _store(tmp_path):
    return CatalystWorkbench(tmp_path / "bench", [tmp_path / "bench-inputs"]).components


def _admit(store, package, *, activate=True):
    receipt = store.discover(package)
    store.admit(package, receipt["package_sha256"])
    if activate:
        store.activate(SEMANTIC_COMPONENT, "0.1.0")


def _wiki(tmp_path):
    return ProjectWiki(tmp_path / "workspace", [tmp_path], enterprise_id="enterprise", project_id="project")


def _source(tmp_path):
    path = tmp_path / "reorg.md"
    path.write_text(TEXT, encoding="utf-8")
    return path


def test_intake_reads_under_the_registered_method_and_names_it(tmp_path):
    wiki = _wiki(tmp_path)
    store = _store(tmp_path)
    _admit(store, _package(tmp_path / "package"))

    outcome = intake_source(wiki, _source(tmp_path), source_root=tmp_path, methods=store,
                            semantic_provider=_OneEntity(), label="intake-case")

    assembly = outcome["assembly"]
    assert assembly["kind"] == "registered_method"
    assert assembly["method"]["component_id"] == SEMANTIC_COMPONENT
    assert assembly["method"]["version"] == "0.1.0"
    assert assembly["method"]["skill_name"] == SEMANTIC_SKILL
    assert len(assembly["method"]["package_sha256"]) == 64
    assert assembly["extraction_mode"] == "single_stage"
    assert assembly["concepts"]["version"] == "starter-1"
    assert assembly["concepts"]["count"] == 11
    assert len(assembly["concepts"]["digest"]) == 64
    assert len(assembly["implementation"]) == 64
    assert assembly["lease"]["released"] is True
    # The document is still only a candidate: a run does not accept anything.
    assert outcome["authority"] == "CANDIDATE_ONLY"
    assert wiki.semantic_state()["active_version_id"] is None


def test_an_inactive_method_lets_the_document_in_but_is_not_claimed(tmp_path):
    wiki = _wiki(tmp_path)
    store = _store(tmp_path)
    _admit(store, _package(tmp_path / "package"), activate=False)

    outcome = intake_source(wiki, _source(tmp_path), source_root=tmp_path, methods=store,
                            semantic_provider=_OneEntity())

    assembly = outcome["assembly"]
    assert assembly["kind"] == "builtin_skill"
    assert SEMANTIC_COMPONENT in assembly["reason"]
    assert "no version of" in assembly["reason"]
    assert "method" not in assembly
    assert outcome["source"]["source_id"]


def test_without_a_component_store_the_result_says_what_read_it(tmp_path):
    outcome = intake_source(_wiki(tmp_path), _source(tmp_path), source_root=tmp_path)

    assert outcome["assembly"]["kind"] == "builtin_skill"
    assert "no component store was supplied" in outcome["assembly"]["reason"]
    assert outcome["assembly"]["concepts"]["version"] == "starter-1"


def test_a_store_that_admitted_nothing_is_the_same_not_enabled_case(tmp_path):
    # An empty store and a store with an admitted but inactive method are different states
    # of the same fact: nothing is enabled here, so nothing may be claimed.
    outcome = intake_source(_wiki(tmp_path), _source(tmp_path), source_root=tmp_path,
                            methods=_store(tmp_path), semantic_provider=_OneEntity())

    assert outcome["assembly"]["kind"] == "builtin_skill"
    assert "is admitted in this workspace" in outcome["assembly"]["reason"]


class _Busy:
    """A store whose method is being updated: the run must stop, not quietly read anyway."""

    def acquire_method(self, component_id):  # noqa: ARG002
        raise ComponentError("method_update_busy")


def test_a_broken_method_seam_is_not_hidden_behind_the_builtin_reading(tmp_path):
    with pytest.raises(ComponentError, match="method_update_busy"):
        intake_source(_wiki(tmp_path), _source(tmp_path), source_root=tmp_path,
                      methods=_Busy(), semantic_provider=_OneEntity())
