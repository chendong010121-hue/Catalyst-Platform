"""Host-only source/method snapshot and projection for the existing test card.

No executor, model client, semantic grader or business write is implemented here.
"""
import hashlib
from pathlib import Path
from .project_understand import digest, reject_source_links
from .understand_sources import SOURCE_SUFFIXES
from .semantic_keys import verifier as _key_verifier


def file_manifest(root, *, method=False):
    root = reject_source_links(Path(root)).resolve(strict=True)
    rows = []
    paths=[];pending=[root];seen=0
    while pending:
        for entry in pending.pop().iterdir():
            seen+=1
            if seen>4096:raise ValueError('semantic_test_scan_limit')
            reject_source_links(entry)
            # The product writes its derived evidence package back into the source root;
            # Understand refuses to read it as a source, so it is not in the manifest either,
            # or the manifest and the inventory disagree and no card can be prepared.
            if entry.name in {'.git','node_modules','.venv','__pycache__','.catalyst','.catalyst-proposals'}:continue
            if entry.is_dir():pending.append(entry)
            elif entry.is_file():paths.append(entry)
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if not method and path.suffix.lower() not in SOURCE_SUFFIXES:
            raise ValueError('semantic_test_source_type_not_supported')
        if any(part.lower().startswith(('.env','credentials','secrets','.vault')) for part in path.relative_to(root).parts):
            raise ValueError('credential_like_source_denied')
        if path.stat().st_size > 2_000_000:
            raise ValueError('semantic_test_file_too_large')
        raw = path.read_bytes()
        if len(raw) > 2_000_000:
            raise ValueError('semantic_test_file_too_large')
        rows.append(dict(relative_path=relative, sha256=hashlib.sha256(raw).hexdigest(),
                         bytes=len(raw), source_id='s_' + hashlib.sha256(relative.encode()).hexdigest()[:16]))
        if len(rows) > (128 if method else 16) or sum(r['bytes'] for r in rows) > 8_000_000:
            raise ValueError('semantic_test_manifest_too_large')
    if not rows:
        raise ValueError('semantic_test_manifest_empty')
    return rows


def method_identity(spec):
    from .understand_only import _SKILL_ROOT
    root = Path(spec.get('method_root', _SKILL_ROOT))
    mode = spec.get('extraction_mode', 'single_stage')
    if mode not in {'single_stage', 'source_local_two_stage'}:
        raise ValueError('semantic_test_method_mode_invalid')
    files = file_manifest(root, method=True)
    return dict(component_id='understand', version='host-pinned', package_sha256=digest(files),
                extraction_mode=mode, files=files)


def source_preflight(spec, manifest):
    """Use the very same deterministic inventory before any model dispatch."""
    from .understand_only import UnderstandPort, UnderstandIntent, _skill_plan
    root = Path(spec['root'])
    pairs = [(root / r['relative_path'], r['relative_path']) for r in manifest]
    port = UnderstandPort(skill_root=spec.get('method_root'),
                          extraction_mode=spec.get('extraction_mode', 'single_stage'))
    port._resolver.load(_skill_plan(UnderstandIntent.KNOWLEDGE_PROPOSE, pairs, depth='semantic'), progressive=True)
    records, units, warnings = port._inventory(pairs, root)
    if (len(records) != len(manifest) or not units
            or any(not r.locator_count for r in records)
            or any(w.startswith(('PARTIAL','UNSUPPORTED')) for w in warnings)
            or sum(r.locator_count for r in records) != len(units)):
        raise ValueError('semantic_test_source_not_completely_readable')
    return dict(files=[dict(relative_path=r.relative_path, sha256=r.source_sha256,
                            extracted_text_sha256=r.extracted_text_sha256, locators=r.locator_count)
                       for r in records], warnings=list(warnings), model_calls=0)


def copy_verified(root, destination, manifest):
    root = Path(root)
    for row in manifest:
        source = reject_source_links(root / row['relative_path'])
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['sha256'] or len(raw) != row['bytes']:
            raise ValueError('test_snapshot_source_changed')
        target = destination / row['relative_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)


def snapshot(spec, subject, card):
    from .understand_only import _SKILL_ROOT
    # Private method files never enter source roots or browser-controlled paths.
    copy_verified(spec.get('method_root', _SKILL_ROOT), subject / 'method', card['method']['files'])
    copy_verified(spec['root'], subject / 'inputs', card['sources'])
    return dict(understand_skill_root=subject / 'method',
                understand_extraction_mode=card['method']['extraction_mode'])


def execute(child, card, recorder, revision=None, verifier_provider=None):
    from .semantic_tool import AdmittedSource, SemanticProposalContext
    from .semantic_wiki import SemanticWiki
    from .wiki import ProjectWiki
    provider = child.settings.provider
    wiki = ProjectWiki(child.workspace, [child.input_root], enterprise_id='synthetic',
                       project_id='development-capture', backend=child.backend)
    semantic = SemanticWiki(wiki, recorder=recorder, receipt_verifier=_key_verifier(wiki.workspace))
    sources = {r['source_id']: AdmittedSource(child.input_root / r['relative_path'], r['sha256'])
               for r in card['sources']}
    def forbidden_harvest(_):
        raise ValueError('test_business_write_forbidden')
    context = SemanticProposalContext(child.input_root, sources, semantic, provider,
        dict(verified=True, simulation=True, permissions=['knowledge.propose'],
             readable_scope_ids=[wiki.scope_id]), forbidden_harvest, None, revision,
        # A separate model reads the candidate in its own context; the host supplies it
        # and its own bounded budget, so the extraction scope keeps its own ledger.
        verifier_provider=verifier_provider)
    capture = child.session.capture_execution(card['objective'], provider=provider,
        visible_capabilities=(('understand', '1.0.0'),), proposal_context=context,
        recorder=recorder, artifact_dir=child.app.state_root / 'captures' / recorder.run_id)
    receipt = capture.summary()
    state = wiki.semantic_state()
    if state['candidates'] or state['active_version_id'] is not None:
        raise ValueError('test_business_write_detected')
    # A typed Unsupported/no-result object is not an extracted semantic result.
    produced = receipt['typed_capture'] and bool(capture.payload().get('semantic_candidate'))
    inventory=capture.payload().get('source_inventory',[]) if receipt['typed_capture'] else []
    actual={(r['relative_path'],r['source_sha256']) for r in inventory}
    missing=[r['relative_path'] for r in card['sources'] if (r['relative_path'],r['sha256']) not in actual]
    passed = receipt['status'] == 'CAPTURED' and produced and not missing
    cancelled=child._pending[recorder.run_id].is_set()
    if cancelled:passed=False
    if cancelled:status='CANCELLED'
    elif receipt['status']!='CAPTURED':status=receipt['status']
    elif not produced:status='SEMANTIC_RESULT_NOT_PRODUCED'
    elif missing:status='PARTIAL_SOURCE_COVERAGE'
    else:status='CAPTURED'
    return dict(run_id=recorder.run_id, status='success' if passed else 'failure',
                state=status,
                execution_entry='Existing Harness capture_execution → Understand Plugin',
                mode='OFFLINE_FAKE' if child.settings.transport_override is not None else 'LIVE',
                observation=capture.observation() if 'observation' in receipt['artifacts'] else None,
                logical_mock_dispatches=provider.budget_snapshot['attempts'] if child.settings.transport_override is not None else 0,
                source_coverage={'read':inventory,'unread':missing},
                external_calls=child.settings.network_attempts,
                task_type='enterprise_semantics', capture=receipt,
                result={'output': {'answer': '已捕获候选，等待独立业务审阅。' if passed else '提取未通过；原始响应已保留。'}},
                semantic_quality='NOT_EVALUATED')
