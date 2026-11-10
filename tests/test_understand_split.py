"""The port is carved by concern; this keeps a later change from quietly undoing that."""
from pathlib import Path

from catalyst_platform import (
    understand_assets,
    understand_manifest,
    understand_models,
    understand_only,
    understand_semantic,
    understand_sources,
    understand_verify,
)


def test_the_facade_re_exports_the_module_that_owns_each_name():
    """Same object, not a copy: a reviewer edits one place and every caller sees it."""
    assert understand_only.EvidenceRef is understand_models.EvidenceRef
    assert understand_only.UnderstandIntent is understand_models.UnderstandIntent
    assert understand_only.UnderstandingResult is understand_models.UnderstandingResult
    assert understand_only.SemanticContractError is understand_models.SemanticContractError
    assert understand_only._parse_frontmatter is understand_manifest._parse_frontmatter
    assert understand_only._SKILL_ROOT is understand_manifest._SKILL_ROOT
    assert understand_only._extract is understand_sources._extract
    assert understand_only.stored_evidence_class is understand_semantic.stored_evidence_class
    assert understand_only.verify_candidate is understand_verify.verify_candidate
    assert understand_only.handoff_external_candidate is understand_verify.handoff_external_candidate


def test_each_direction_of_work_has_one_module_to_edit():
    """Asset decoding and semantic reading must not share a file again."""
    asset_source = Path(understand_assets.__file__).name
    semantic_source = Path(understand_semantic.__file__).name
    facade_source = Path(understand_only.__file__).name
    assert "_inspect_asset" in understand_assets._AssetMixin.__dict__
    assert "_inspect_asset" not in understand_only.UnderstandPort.__dict__
    assert {"_extract_with_provider", "attach_producer_items", "_business_items"} <= set(
        understand_semantic._SemanticMixin.__dict__
    )
    assert not {"_extract_with_provider", "attach_producer_items"} & set(understand_only.UnderstandPort.__dict__)
    assert (asset_source, semantic_source, facade_source) == (
        "understand_assets.py", "understand_semantic.py", "understand_only.py",
    )


def test_the_port_is_the_sum_of_its_mixins_and_nothing_is_shadowed():
    mro = [cls.__name__ for cls in understand_only.UnderstandPort.__mro__]
    assert mro[:4] == ["UnderstandPort", "_SourceMixin", "_AssetMixin", "_SemanticMixin"]
    owners = []
    for name in ("_inspect_asset", "_inventory", "expand_evidence", "attach_producer_items"):
        owner = next(cls for cls in understand_only.UnderstandPort.__mro__ if name in cls.__dict__)
        owners.append(owner.__name__)
    assert owners == ["_AssetMixin", "_SourceMixin", "_SourceMixin", "_SemanticMixin"]
