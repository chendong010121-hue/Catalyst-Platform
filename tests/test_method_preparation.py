import pytest
from catalyst_platform.method_preparation import prepare_method


def test_project_profile_still_requires_original_typed_context():
    from catalyst_platform.project_understand import EXACT_ACTIONS
    with pytest.raises(ValueError, match='project Host context is required'):
        prepare_method(None, None, None, EXACT_ACTIONS, None, None, None)


def test_semantic_profile_still_requires_original_typed_context():
    with pytest.raises(ValueError, match='Host SemanticProposalContext is required'):
        prepare_method(None, None, None, (('understand', '1.0.0'),), None, None, None)


def test_generic_preparation_has_no_method_content_or_services():
    prepared = prepare_method(None, None, None, (), None, None, None)
    assert prepared.prompt_suffix == ''
    assert prepared.plugin_services == {}
    assert prepared.native_batch is False


def test_project_adapter_preserves_exact_prompt_and_context_service(monkeypatch):
    from catalyst_platform.project_understand import ProjectAnalysisContext, EXACT_ACTIONS
    context = object.__new__(ProjectAnalysisContext)
    monkeypatch.setattr(ProjectAnalysisContext, 'initial_context', lambda self: 'original method prompt')
    prepared = prepare_method(None, None, None, EXACT_ACTIONS, None, context, None)
    assert prepared.prompt_suffix == '\noriginal method prompt'
    assert prepared.plugin_services == {'project.analysis': context}
    assert prepared.native_batch is True


def test_semantic_adapter_revalidates_before_rejecting_unadmitted_ids(tmp_path, monkeypatch):
    from catalyst_platform.semantic_tool import SemanticProposalContext, AdmittedSource
    calls = []
    context = SemanticProposalContext(tmp_path, {'source-1': AdmittedSource(tmp_path / 'original.md', 'digest')}, None, None, {}, lambda: None)
    monkeypatch.setattr(SemanticProposalContext, 'validate', lambda self, *args: calls.append(args))
    prepared = prepare_method('session', 'recorder', 'provider', (('understand', '1.0.0'),), context, None, None)
    assert prepared.prompt_suffix == '\nHost-admitted original source IDs: ["source-1"]'
    assert prepared.native_batch is False
    with pytest.raises(ValueError, match='explicit subset'):
        prepared.plugin_services['understand.execute'](['not-admitted'])
    assert calls == [('session', 'recorder', 'provider')]


def test_capture_adapter_keeps_mixed_profile_and_context_guards():
    from catalyst_platform.method_preparation import validate_capture_context
    with pytest.raises(ValueError, match='only Understand'):
        validate_capture_context(None, None, None, (('understand', '1.0.0'), ('other', '1')), None)
    with pytest.raises(ValueError, match='only applicable'):
        validate_capture_context(None, None, None, (), object())


def test_semantic_adapter_forwards_admitted_source_and_original_prompt(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from catalyst_platform.semantic_tool import SemanticProposalContext, AdmittedSource
    capture = object()
    received = []
    output = {'captured': True}
    session = SimpleNamespace(propose_enterprise_semantics=lambda *args, **kwargs: (received.append((args, kwargs)) or output))
    context = SemanticProposalContext(tmp_path, {'original': AdmittedSource(tmp_path / 'original.md', 'digest', locators=('L1',))}, 'semantic', 'provider', {}, lambda: None, capture)
    monkeypatch.setattr(SemanticProposalContext, 'validate', lambda *args: None)
    prepared = prepare_method(session, 'recorder', 'provider', (('understand', '1.0.0'),), context, None, None)
    assert prepared.plugin_services['understand.execute'](['original']) is output
    args, kwargs = received[0]
    assert args == ('请理解企业资料并形成组织语义 Ontology 候选。',)
    assert kwargs['source_refs'] == [tmp_path / 'original.md']
    assert kwargs['source_evidence_scope'] == {'original.md': ('L1',)}
    assert kwargs['_capture'] is capture
    assert kwargs['provider'] == 'provider'
