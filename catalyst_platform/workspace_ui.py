"""Local Workspace UI over the existing monitor/session, not another execution host.

Only the original monitor POST routes execute work. Added routes project the
same session Catalog and scoped Wiki. This entry has no live credential path.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import os
import secrets
import re
import subprocess
import uuid
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .monitor import create_monitor_server
from .observability import RunRecorder
from .semantic_wiki import SemanticWiki
from .semantic_keys import verifier as _key_verifier
from .understand_wiki import UnderstandWikiAdapter
from .workspace_context import DEFAULT_CHAT_CONTEXT_PLUGIN
from .workspace_session import WorkspaceUserSession
from .knowledge_intake import SUPPORTED_SOURCE_SUFFIXES, KnowledgeIntakeError, intake_source
from .understand_sources import _MAX_FILE_BYTES as MAX_SOURCE_BYTES
from .understand_sources import _MAX_TEXT_BYTES as MAX_PART_TEXT_BYTES
from .wiki import ProjectWiki, WikiScopeError
from .wiki_model import acceptance_basis_summary, build as wiki_model_read
from .model_qualification import DEFAULT_QUALIFICATION
from .maintenance import LocalMaintenance
from . import review_surface

ASSETS = Path(__file__).with_name('workspace_assets')
_KNOWLEDGE_UPLOAD_BODY_BYTES = 24 * 1024 * 1024


class _LocalRequestError(ValueError):
    """A refused local request whose code is safe to return to this Workspace."""

    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def _git_identity():
    root = Path(__file__).resolve().parents[1]
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                              text=True, encoding='utf-8', check=True, timeout=15).stdout.strip()
    return {'commit': git('rev-parse', 'HEAD'), 'tree': git('rev-parse', 'HEAD^{tree}'),
            'dirty': bool(git('status', '--porcelain=v1')), 'source_root': str(root)}


def create_workspace_server(workspace, *, port=8792, backend='json', mode='MOCK', ledger_factory=None,
                            qualification_path=DEFAULT_QUALIFICATION, project_sources=None, project_live_scope=None,
                            chat_context_plugin=DEFAULT_CHAT_CONTEXT_PLUGIN):
    # Host assembly only. Browser requests select IDs; no browser path can join
    # this admitted table or register a method package.
    sources = {}
    for source_id, spec in (project_sources or {}).items():
        if (not isinstance(source_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', source_id)
                or not isinstance(spec, dict) or set(spec) - {'root', 'object_type', 'entry_source_ids', 'task_kind', 'method_root', 'extraction_mode', 'label', 'review_questions'}
                or not {'root', 'object_type'} <= set(spec)
                or spec['object_type'] not in ('agent', 'skill', 'plugin', 'enterprise_documents') or not isinstance(spec['root'], Path)):
            raise ValueError('project_source_configuration_invalid')
        if (spec.get('task_kind','project_analysis') not in {'project_analysis','enterprise_semantics'}
                or (spec['object_type']=='enterprise_documents') != (spec.get('task_kind')=='enterprise_semantics')
                or (spec.get('task_kind')!='enterprise_semantics' and set(spec)&{'method_root','extraction_mode'})):
            raise ValueError('test_task_source_contract_mismatch')
        from .project_understand import reject_source_links
        root = reject_source_links(spec['root']).resolve(strict=True)
        if not root.is_dir() or spec['root'].is_symlink():
            raise ValueError('project_source_configuration_invalid')
        sources[source_id] = {**spec, 'root': root}
        if (not isinstance(spec.get('label',source_id),str) or not 1<=len(spec.get('label',source_id))<=160
                or not isinstance(spec.get('review_questions',[]),(list,tuple))
                or len(spec.get('review_questions',[]))>30
                or any(not isinstance(q,str) or not 1<=len(q)<=2000 for q in spec.get('review_questions',[]))):
            raise ValueError('test_review_configuration_invalid')
        if 'entry_source_ids' in spec:
            entries = spec['entry_source_ids']
            if not isinstance(entries, (tuple, list)) or not all(isinstance(e, str) for e in entries):
                raise ValueError('project_source_configuration_invalid')
            sources[source_id]['entry_source_ids'] = tuple(entries)
    session = WorkspaceUserSession(workspace, backend=backend, mode=mode, ledger_factory=ledger_factory,
                                    qualification_path=qualification_path, chat_context_plugin=chat_context_plugin)
    if project_live_scope is not None:
        from .project_understand import validate_live_project_scope
        sid=project_live_scope.get('source_id')
        if sid not in sources:raise ValueError('project_live_source_not_admitted')
        validate_live_project_scope(project_live_scope,sources[sid],project_live_scope['objective'],project_live_scope['max_depth'],method_sha256=project_live_scope['method_sha256'])
        session._project_live_scope=json.loads(json.dumps(project_live_scope))
        session.settings.project_live_scope=session._project_live_scope
    session.app._project_source_roots = tuple(spec['root'] for spec in sources.values())
    from .project_acceptance import ProjectAcceptance
    project_tests = ProjectAcceptance(session, sources)
    requests = {}
    admission = threading.local()

    class ProjectDispatch:
        """One-time Host dispatch into the original Monitor scheduler."""
        def __getattr__(self, name):
            return getattr(session, name)

        def prepare(self, recorder):
            session.prepare(recorder)
            token = getattr(admission, 'token', None)
            if token in requests:
                requests[token]['queued'] = True

        def __call__(self, message, selected_file, recorder, *, thread_id=None):
            if thread_id is not None:
                return session(message, selected_file, recorder, thread_id=thread_id)
            request = requests.pop(message, None)
            if request is None:
                return session(message, selected_file, recorder)
            span = recorder.start_span('development.configuration.admitted' if request.get('plan_request') else 'project.request.admitted', kind='CHAIN', attributes={
                'source_id': 'PROFILE_METADATA_ONLY' if request.get('plan_request') else request['source_id'],
                'objective_sha256': hashlib.sha256(request['objective'].encode()).hexdigest(),
                'max_depth': request['max_depth']})
            recorder.end_span(span, status='success')
            if request.get('test_id') or request.get('plan_request'):
                try:
                    if request.get('plan_request'):return project_tests.propose(request['plan_request'],recorder)
                    return project_tests.execute(request['test_id'],request['card_sha256'],recorder)
                except Exception as exc:
                    session._pending.pop(recorder.run_id,None);session._recorders.pop(recorder.run_id,None)
                    recorder.event('request.failed',error_type=type(exc).__name__)
                    if not recorder.is_finished:recorder.finish('failure')
                    return {'run_id':recorder.run_id,'state':'BLOCKED','status':'failure',
                        'task_type':'test_configuration' if request.get('plan_request') else 'project_analysis',
                        'test_id':request.get('test_id'),
                        'error':{'code':'project_test_stopped','type':type(exc).__name__},
                        'result':{'output':{'answer':'测试门禁或执行已停止，请查看测试记录。'}}}
            return self.analyze_project(request['spec'], request['objective'], request['max_depth'], recorder)

    dispatcher = ProjectDispatch() if sources else session
    wiki = ProjectWiki(session.workspace, [session.input_root], enterprise_id='synthetic',
                       project_id='local-ui-demo', backend=backend)
    # One workbench, more than one knowledge scope. Only the daily scope is written here;
    # a declared scope is opened read-only, and its store has to already live in this
    # workspace, so switching scope never mixes two scopes' data or hands out approval.
    daily_scope = wiki.scope_id
    scopes = review_surface.registered_scopes(session.workspace, daily_scope)

    def chosen_scope(query):
        wanted = (query.get('scope') or [daily_scope])[0]
        row = next((r for r in scopes['scopes'] if r['scope_id'] == wanted), None)
        if row is None:
            raise review_surface.ReadingError('scope_unknown', '这个工作区没有声明该知识范围。', 404)
        if wanted == daily_scope:
            return wiki, row
        return review_surface.open_scope(session.workspace, [session.input_root], wanted,
                                        read_only=row['read_only']), row

    dispositions = review_surface.ReviewDispositions(session.workspace)
    opinions = review_surface.ReviewItemOpinions(session.workspace)
    products = review_surface.declared_products(session.workspace)
    server = create_monitor_server(session.workspace, dispatcher, port=port,
                                   input_root=session.input_root)
    server.project_sources = sources
    server.restart_requested = False
    server.maintenance_admission = threading.RLock()
    server.maintenance = LocalMaintenance(session.app)
    try:
        pending=server.maintenance.items()
        if any(r['status']=='RECOVERY_REQUIRED' for r in pending):
            raise ValueError('maintenance_recovery_required_normal_start_blocked')
        if any(r['status'] in ('PENDING_RESTART','ROLLBACK_PENDING','APPLYING') for r in pending):
            session.settings.ledger_factory.check_prior_scopes(session.settings.root/'scopes')
            applied=server.maintenance.apply_pending()
            if applied and applied['status']=='RECOVERY_REQUIRED':
                raise ValueError('maintenance_recovery_required_normal_start_blocked')
    except Exception:
        server.server_close()
        raise
    original_handler = server.RequestHandlerClass
    identity = _git_identity()

    def asset_projection():
        try:return {'items':session.app.components.assets.list(),'error':None}
        except (ValueError,OSError):return {'items':None,'error':'ASSET_METADATA_UNAVAILABLE'}

    def catalog():
        # The SAME actual Catalog: discovery plus its registered, Host-gated
        # descriptors. A descriptor's presence never grants execution permission.
        active = {(d.id, d.capability_version) for d in session.session.discover()}
        descriptors = session.app._catalog.registry.list()
        return [{'id': d.id, 'version': d.capability_version, 'name': d.name,
                 'description': d.description, 'input_schema': d.input_schema,
                 'output_schema': d.output_schema, 'execution': d.execution,
                 'registered': True, 'active': (d.id, d.capability_version) in active,
                 'execution_authorization': 'NOT_INFERRED_FROM_DISCOVERY'}
                for d in sorted(descriptors, key=lambda d: (d.id, d.capability_version))]

    def semantic_read(candidate_id, active_wiki=None, graph_view='business', limit=500,
                      focus=None, evidence=False):
        book = active_wiki or wiki
        recorder = RunRecorder(server.trace_store, run_id='run_' + uuid.uuid4().hex,
                               request_id='req_' + uuid.uuid4().hex,
                               invocation_id='inv_' + uuid.uuid4().hex,
                               trace_id=uuid.uuid4().hex)
        recorder.start(request_kind='workspace_ontology_read', component='WorkspaceUI',
                       actor='local_workspace_user', entry_point='workspace_ui')
        recorder.bind_session(session.session_id)
        try:
            semantic = SemanticWiki(book, recorder=recorder, recover_pending=False, receipt_verifier=_key_verifier(book.workspace))
            if candidate_id:
                adapter = UnderstandWikiAdapter(book, semantic, session.input_root)
                if graph_view == 'all':
                    # The provenance view is unchanged for every consumer that asks for it.
                    value = adapter.candidate_graph(candidate_id, limit=limit)
                else:
                    value = adapter.business_graph(candidate_id, limit=limit,
                                                   focus=focus, evidence=evidence)
            else:
                value = semantic.ontology_graph(actor_origin='catalyst_deterministic', limit=100)
                # `authority` on the graph is the store's ('MANAGER_ACCEPTED_SCOPED_SEMANTICS');
                # what the version was admitted under is a separate fact, and the one a
                # reader has to be able to see: a test admission must not read as a business one.
                state = book.semantic_state()
                version = state['accepted_versions'].get(state.get('active_version_id')) or {}
                value = {**value, 'authority_class': version.get('authority_class'),
                         'candidate_id': version.get('candidate_id'),
                         'acceptance_basis': version.get('owner_acceptance_basis'),
                         'candidate_meanings_included': value.get('candidate_meanings_included')}
            recorder.finish('success', external_calls=0)
            return {**value, 'read_run_id': recorder.run_id,
                    'view_tier': 'candidate' if candidate_id else 'accepted',
                    'scope_id': book.scope_id}
        except Exception as exc:
            recorder.event('request.failed', error_type=type(exc).__name__)
            recorder.finish('failure', error_type=type(exc).__name__, external_calls=0)
            raise

    def semantic_candidates(active_wiki=None):
        """Every candidate in this scope, including the ones already decided.

        `/api/reviews` lists what still needs a decision, so a candidate the product has
        already accepted disappears from it; that is the wrong list for "open the latest
        candidate". This one lists what exists and the chain each one is part of --
        wrapper -> typed candidate -> decision -> version -- so a reader can check the
        lifecycle instead of inferring it. Nothing here is written: opening it cannot
        change what the Wiki holds.
        """
        from .semantic_wiki import _candidate_content_digest
        book = active_wiki or wiki
        state = book.semantic_state()
        rows = []
        for cid, row in sorted(state['candidates'].items()):
            decision = state['decisions'].get(row.get('latest_decision_id') or '') or {}
            evaluation = state['evaluations'].get(row.get('latest_evaluation_id') or '') or {}
            rows.append({
                'candidate_id': cid,
                'type': row.get('candidate_type') or 'native',
                'status': row.get('status'),
                'authority': row.get('authority') or 'CANDIDATE_ONLY',
                'mapping_status': row.get('mapping_status'),
                'typed_candidate_id': row.get('typed_candidate_id'),
                'source_id': row.get('source_id'),
                'source_revision': row.get('source_revision'),
                'proposer_origin': row.get('proposer_origin'),
                'evaluation_status': evaluation.get('status'),
                'decision': decision.get('decision'),
                'version_id': decision.get('version_id'),
                'created_run_id': row.get('created_run_id'),
                # The digest a decision is and stays bound to. The store refuses to bind an
                # evaluation or a decision to different content, so a candidate that changed
                # after a decision shows up here as itself, not as silently re-approved.
                'content_digest': _candidate_content_digest(row),
                'decision_source_revision': decision.get('source_revision'),
                'revision_matches_decision': (not decision
                                              or decision.get('source_revision') == row.get('source_revision')),
            })
        versions = [{'version_id': vid, 'candidate_id': v.get('candidate_id'),
                      'authority_class': v.get('authority_class'),
                      'decision_id': v.get('decision_id'),
                      'source_id': v.get('source_id'),
                      'source_revision': v.get('source_revision'),
                      # Who admitted this version and on what basis, copied from the version.
                      # The task card says "未记录业务批准依据" when this is missing.
                      'acceptance_basis_state': ('recorded' if isinstance(
                          v.get('owner_acceptance_basis'), dict) else 'missing'),
                      'acceptance_basis': acceptance_basis_summary(v.get('owner_acceptance_basis'))}
                     for vid, v in sorted(state['accepted_versions'].items())]
        active = state.get('active_version_id')
        return {'scope_id': book.scope_id, 'active_version_id': active,
                'active_authority_class': (state['accepted_versions'].get(active) or {}).get('authority_class'),
                'candidates': rows, 'versions': versions,
                'counts': {'candidates': len(rows), 'versions': len(versions),
                           'decided': sum(1 for r in rows if r['decision']),
                           'with_version': sum(1 for r in rows if r['version_id'])}}

    def run_products_view(query):
        """The whole modelling candidate one controlled run produced, read as a projection.

        It is not imported into any scope: the rows come from the candidate's own reading,
        and what the hand-off did not carry comes from the run's own record, so the count
        a reader sees is the count the run made -- not a re-derivation from text.
        """
        wanted = (query.get('scope') or [None])[0]
        items = []
        for product in products:
            if wanted and product['scope_id'] != wanted:
                continue
            head = {'product_id': product['product_id'], 'label': product['label'],
                    'root': product['root'], 'scope_id': product['scope_id'],
                    'candidate_id': product['candidate_id'], 'note': product['note'],
                    'files': product['files']}
            try:
                book, _row = chosen_scope({'scope': [product['scope_id']]})
                state = book.semantic_state()
            except review_surface.ReadingError as exc:
                items.append({**head, 'readable': False, 'error': exc.code,
                              'message': '这个范围在当前工作区打不开。'})
                continue
            candidate = state['candidates'].get(product['candidate_id']) or {}
            result = candidate.get('understanding_result')
            if not isinstance(result, dict):
                items.append({**head, 'readable': False, 'error': 'candidate_missing',
                              'message': '运行产物所属的候选不在这个范围里。'})
                continue
            try:
                detail = review_surface.product_rows(product, result)
            except review_surface.ReadingError as exc:
                items.append({**head, 'readable': False, 'error': exc.code, 'message': str(exc)})
                continue
            items.append({**head, 'readable': True, 'counts': detail['counts'],
                          'unaccounted': detail['unaccounted'], 'receipt': detail['receipt'],
                          'rows': detail['rows']})
        return {'items': items, 'total': len(items), 'scope': wanted,
                'note': '运行产物是受控运行的只读投影：不写 Wiki，不改变正式准入。'}

    class WorkspaceHandler(original_handler):
        def do_GET(self):
            if server.restart_requested:
                self.close_connection=True
                self._error('workspace_restarting','The old instance is closing; reconnect after restart.',status=503)
                return
            if not self._host_allowed() or not self._origin_allowed():
                self._error('origin_not_allowed', 'Only this local Workspace may read these routes.', status=403)
                return
            parsed = urlsplit(self.path)
            if parsed.path == '/api/development-offline':
                from .evaluation_workflow import offline_profiles
                self._json({'profiles': offline_profiles(), 'scope': 'SYNTHETIC_DETERMINISTIC_ONLY'})
                return
            if parsed.path == '/api/evaluation-workflow-guide':
                from .evaluation_workflow import workflow_guide
                try:self._json(workflow_guide(parse_qs(parsed.query).get('mode',['build-eval'])[0],session.app.components))
                except (ValueError,OSError,RuntimeError,KeyError):self._error('workflow_guide_unavailable','Select a supported workflow mode.',status=400)
                return
            if parsed.path == '/api/evaluation-workflows':
                try:self._json({'items':session.evaluation_workflows(),'execution_enabled':False,'profile':'DAILY_WITH_SEPARATE_EVALUATION_PREPARATION'})
                except (ValueError,OSError):self._error('workflow_integrity_unavailable','Workflow record needs local review.',status=409)
                return
            if parsed.path == '/api/project-sources':
                from .project_understand import source_manifest,digest
                include_manifest=parse_qs(parsed.query).get('include_manifest')==['1']
                value={'items': [{'source_id': sid, 'label': spec.get('label',sid), 'object_type': spec['object_type'],
                                  **({'source_manifest_sha256':digest(source_manifest(spec['root']))}
                                     if include_manifest and spec.get('task_kind')!='enterprise_semantics' else {}),
                                  **({'task_kind':spec['task_kind']} if 'task_kind' in spec else {})}
                                 for sid,spec in sorted(sources.items())]}
                if project_live_scope is not None:value['live_scope']=dict(project_live_scope)
                self._json(value)
                return
            if parsed.path == '/api/project-tests':
                try:
                    try:allowance=project_tests.planning_allowance()
                    except ValueError:allowance=None
                    self._json({'items':project_tests.items(),'plans':project_tests.plans(),
                        'planning_allowance':allowance,'execution_enabled':True,
                        'scope':'HOST_ADMITTED_CONFIGURABLE_ACCEPTANCE'})
                except (ValueError,OSError):self._error('project_test_record_unavailable','Test records need review.',status=409)
                return
            if parsed.path == '/api/maintenance':
                try:
                    self._json({'items':server.maintenance.items(),'active':server.maintenance.active_identity(),
                                'method_active':server.maintenance.active_identity('project-understand'),
                                'authority':'LOCAL_MAINTENANCE_NOT_ENTERPRISE_OWNER',
                                'supported_target':'local_text_stats:1.0.0→2.0.0',
                                'supported_targets':['local_text_stats','project-understand'],
                                'restart_supported':True})
                except (ValueError,OSError,RuntimeError):
                    self._error('maintenance_evidence_unavailable','Maintenance evidence needs local review.',status=409)
                return
            if parsed.path == '/api/capability-review':
                from .capability_review import review
                try:
                    self._json(review(session.workspace))
                except (ValueError, OSError):
                    self._error('capability_review_unavailable', 'Capability claims need local review.', status=409)
                return
            if parsed.path == '/api/settings':
                try:
                    self._json(session.settings.snapshot())
                except (ValueError, OSError):
                    self._error('settings_scope_unavailable', 'Stored scope needs local review.', status=409)
                return
            if parsed.path == '/api/config':
                self._json({'csrf_token': self.server.local_csrf_token, 'mode': session.mode,
                            'session_id': session.session_id,
                            'paid_calls_enabled': session.settings.snapshot()['enabled'],
                            'live_scope': 'TEXT_CHAT_ONLY', 'file_extraction': 'MOCK'})
                return
            static = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                      '/styles.css': ('styles.css', 'text/css'),
                      '/wiki-contract.js': ('wiki-contract.js', 'text/javascript'),
                      '/business-graph.js': ('business-graph.js', 'text/javascript'),
                      '/wiki': ('wiki.html', 'text/html'), '/wiki.js': ('wiki.js', 'text/javascript'),
                      '/wiki.css': ('wiki.css', 'text/css')}
            if parsed.path in static:
                filename, mime = static[parsed.path]
                body = (ASSETS / filename).read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mime + '; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Frame-Options', 'DENY')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)
                return
            routes = {'/api/chat', '/api/asset-connections', '/api/assets', '/api/asset-document', '/api/workspace', '/api/capabilities', '/api/knowledge', '/api/document', '/api/imports', '/api/imported-document',
                      '/api/ontology', '/api/reviews', '/api/wiki/model', '/api/semantic/candidates',
                      '/api/knowledge-scopes', '/api/run-products', '/api/review-dispositions',
                      '/api/review-item-opinions'}
            if parsed.path not in routes:
                super().do_GET()
                return
            if len(self.path) > 4096:
                self._error('query_too_long', 'Query exceeds the local limit.', status=400)
                return
            if not session._execution.acquire(blocking=False):
                self._error('workspace_busy', 'A local task is committing; read again after it finishes.', status=409)
                return
            try:
                query = parse_qs(parsed.query)
                if parsed.path == '/api/chat':
                    if project_live_scope is not None:
                        self._error('project_scope_only', 'This isolated scope only admits its project task.', status=403)
                        return
                    chat = session.settings.chat
                    thread_id = query.get('thread', [chat.thread()])[0]
                    if not chat.exists(thread_id):
                        self._error('chat_thread_invalid', 'Select an existing conversation.', status=404)
                        return
                    value = {'thread_id': thread_id, 'turns': chat.recent(thread=thread_id), 'threads': chat.threads()}
                elif parsed.path == '/api/asset-connections':
                    value=session.app.components.assets.query_summary('*')
                elif parsed.path == '/api/assets':
                    value = {**asset_projection(),
                             'basis':'LIFECYCLE_ASSET_METADATA_WITH_CURRENT_CATALOG_PROJECTION',
                             'registration_does_not_authorize':True}
                elif parsed.path == '/api/asset-document':
                    value = session.app.components.assets.document(query.get('id',[''])[0],query.get('version',[''])[0])
                elif parsed.path == '/api/workspace':
                    value = {'mode': session.mode, 'paid_calls_enabled': session.settings.snapshot()['enabled'],
                             'session_id': session.session_id, 'scope_id': wiki.scope_id,
                             'backend': backend, 'source_identity': identity,
                             'workspace_id': hashlib.sha256(os.path.normcase(str(session.workspace.resolve())).encode()).hexdigest(),
                             'source_root_id': hashlib.sha256(os.path.normcase(str(Path(identity['source_root']).resolve())).encode()).hexdigest(),
                             'supported_task': 'BOUNDED_OFFLINE_ENTERPRISE_SEMANTICS',
                             'agent_creation': 'DRAFT_ONLY_NOT_IMPLEMENTED',
                             'basic_chat': 'LIVE_WHEN_EXPLICITLY_CONFIGURED_OTHERWISE_LOCAL_INFO',
                             'execution_entry': 'HarnessSession.capture_execution',
                             'architecture_baseline': '4923b4bf1ad8b8d16cab280908cfe915ff5e754b',
                             'modules': {'assembly': str(Path(__import__('catalyst_platform.workspace_session', fromlist=['x']).__file__).resolve()),
                                         'session_control_base': str(Path(__import__('catalyst_platform.user_session', fromlist=['x']).__file__).resolve()),
                                         'monitor': str(Path(__import__('catalyst_platform.monitor', fromlist=['x']).__file__).resolve())}}
                elif parsed.path == '/api/capabilities':
                    assets=asset_projection()
                    value = {'items': catalog(), 'basis': 'CURRENT_SESSION_REGISTERED_CATALOG',
                             'session_id': session.session_id,'assets':assets['items'],'asset_error':assets['error']}
                elif parsed.path == '/api/imports':
                    rows = []
                    for path in sorted(session.input_root.iterdir()):
                        if len(rows) >= 100:
                            break
                        if (not path.is_file() or path.is_symlink() or path.resolve().parent != session.input_root
                                or not re.fullmatch(r'[a-f0-9]{64}\.(txt|md|pptx)', path.name)):
                            continue
                        rows.append({'id': path.name, 'bytes': path.stat().st_size,
                                     'source_sha256': path.stem, 'status': 'IMPORTED_NOT_WIKI_ADMITTED'})
                    value = {'items': rows, 'limit': 100, 'possibly_truncated': len(rows) == 100}
                elif parsed.path == '/api/imported-document':
                    fid = query.get('id', [''])[0]
                    if not re.fullmatch(r'[a-f0-9]{64}\.(txt|md|pptx)', fid):
                        raise ValueError('invalid imported identity')
                    path = (session.input_root / fid).resolve(strict=True)
                    if path.parent != session.input_root or path.stat().st_size > 700000:
                        raise ValueError('imported source escaped scope')
                    raw = path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != path.stem:
                        raise ValueError('imported source hash changed')
                    value = {'id': fid, 'source_sha256': path.stem,
                             'content': raw.decode('utf-8-sig') if path.suffix != '.pptx' else None,
                             'preview_status': 'TEXT' if path.suffix != '.pptx' else 'PPTX_PREVIEW_NOT_IMPLEMENTED',
                             'authority': 'IMPORTED_ORIGINAL_NOT_ACCEPTED_KNOWLEDGE'}
                elif parsed.path == '/api/knowledge':
                    assets=asset_projection()
                    result = wiki.read_knowledge(query.get('q', ['*'])[0], mode='source_discovery', limit=100)
                    # read_knowledge's source/document tiers can exceed limit; bound the UI projection explicitly.
                    rows = result['documents']
                    value = {'items': rows[:100], 'total': len(rows), 'truncated': len(rows) > 100,
                             'scope_id': wiki.scope_id, 'read_mode': 'source_discovery',
                             'asset_documents':assets['items'],'asset_error':assets['error']}
                elif parsed.path == '/api/document':
                    source_id = query.get('id', [''])[0]
                    if not re.fullmatch(r'[A-Za-z0-9_:-]{1,160}', source_id):
                        raise ValueError('invalid source identity')
                    record = wiki.source_record(source_id)
                    if record.get('source_format') in {'docx', 'pptx', 'pdf'}:
                        # Wiki keeps a native document as bytes identity; it holds no
                        # extracted text, so the reader reports freshness and says so
                        # instead of pretending the file is unreadable.
                        try:
                            current = wiki.native_source_snapshot(source_id)['current_revision']
                        except WikiScopeError:
                            current = None
                        value = {'source_id': source_id, 'content': None,
                                 'source_revision': record.get('revision'),
                                 'current_revision': current,
                                 'fresh': None if current is None else current == record.get('revision'),
                                 'relative_path': record.get('relative_path'),
                                 'source_format': record.get('source_format'),
                                 'status': record.get('status') or 'STAGED',
                                 'preview_status': 'NATIVE_DOCUMENT_NOT_PARSED',
                                 'authority': 'NATIVE_SOURCE_IDENTITY_ONLY'}
                    else:
                        snapshot = wiki.source_snapshot(source_id)
                        value = {'source_id': source_id, 'content': snapshot['content'],
                                 'source_revision': snapshot['source'].get('revision'),
                                 'current_revision': snapshot['current_revision'],
                                 'relative_path': snapshot['source'].get('relative_path'),
                                 'source_format': 'md',
                                 'status': record.get('status') or 'STAGED',
                                 'authority': 'SOURCE_DOCUMENT_NOT_ACCEPTED_ONTOLOGY'}
                elif parsed.path == '/api/wiki/model':
                    # The reading surface is a projection of this scope's own store: no page tree
                    # is written and no model is called, so the answer is always the live Wiki.
                    book, _row = chosen_scope(query)
                    value = wiki_model_read(book)
                elif parsed.path == '/api/semantic/candidates':
                    book, row = chosen_scope(query)
                    self._json({**semantic_candidates(book), 'read_only': row['read_only'],
                                'scope_label': row['label']})
                    return
                elif parsed.path == '/api/knowledge-scopes':
                    self._json(scopes)
                    return
                elif parsed.path == '/api/run-products':
                    self._json(run_products_view(query))
                    return
                elif parsed.path == '/api/review-dispositions':
                    self._json(dispositions.view(
                        scope_id=(query.get('scope') or [None])[0],
                        candidate_id=(query.get('candidate_id') or [None])[0]))
                    return
                elif parsed.path == '/api/review-item-opinions':
                    scope_id = (query.get('scope') or [None])[0]
                    candidate_id = (query.get('candidate_id') or [None])[0]
                    value = opinions.view(scope_id=scope_id, candidate_id=candidate_id)
                    if candidate_id:
                        # The three counts a reviewer needs apart, against the run's own rows.
                        rows = []
                        for item in run_products_view(query)['items']:
                            if item.get('candidate_id') == candidate_id and item.get('readable'):
                                rows = item.get('rows') or []
                                break
                        value['coverage'] = opinions.coverage(
                            scope_id=scope_id, candidate_id=candidate_id, rows=rows)
                    self._json(value)
                    return
                elif parsed.path == '/api/ontology':
                    candidate_id = query.get('candidate_id', [None])[0]
                    if candidate_id is not None and not re.fullmatch(r'(?:candidate|understand)_[a-f0-9]{24,64}', candidate_id):
                        raise ValueError('invalid candidate identity')
                    graph_view = (query.get('view') or ['business'])[0]
                    if graph_view not in {'business', 'all'}:
                        raise ValueError('invalid graph view')
                    graph_limit = int((query.get('limit') or ['500'])[0])
                    if not 1 <= graph_limit <= 500:
                        raise ValueError('invalid graph limit')
                    graph_focus = (query.get('focus') or [None])[0] or None
                    if graph_focus is not None and not re.fullmatch(r'understand-item:[A-Za-z0-9_.:-]{1,120}', graph_focus):
                        raise ValueError('invalid graph focus')
                    graph_evidence = (query.get('evidence') or ['0'])[0] in {'1', 'true', 'yes'}
                    book, _row = chosen_scope(query)
                    value = semantic_read(candidate_id, book, graph_view=graph_view,
                                          limit=graph_limit, focus=graph_focus,
                                          evidence=graph_evidence)
                else:
                    data = wiki.semantic_state()
                    rows = []
                    for cid, c in data['candidates'].items():
                        decision = data['decisions'].get(c.get('latest_decision_id'), {})
                        if decision.get('decision') in {'ACCEPTED', 'REJECTED'}:
                            continue
                        evaluation = data['evaluations'].get(c.get('latest_evaluation_id'), {})
                        rows.append({'candidate_id': cid, 'status': 'REVIEW_REQUIRED',
                                     'evaluation': evaluation, 'decision': decision,
                                     'can_accept': False, 'can_reject': False,
                                     'reason': 'No external evaluation/Owner authorization is installed by this UI.'})
                    value = {'items': rows[:100], 'total': len(rows), 'truncated': len(rows) > 100,
                             'active_version_id': data['active_version_id'], 'scope_id': wiki.scope_id}
                self._json(value)
            except (ValueError, KeyError, OSError, RuntimeError) as exc:
                self._error(getattr(exc, 'code', 'workspace_read_unavailable'),
                            'The scoped resource is unavailable: ' + type(exc).__name__,
                            status=getattr(exc, 'status', 400))
            finally:
                session._execution.release()

        def do_POST(self):
            # Serialize accepting a new task with restart admission. Existing
            # task execution still belongs to the original session/Runtime.
            with server.maintenance_admission:
                self._maintenance_post()

        def _knowledge_origin_ok(self):
            return (self._host_allowed() and self._origin_allowed() and
                    secrets.compare_digest(self.headers.get('X-Catalyst-CSRF', ''), server.local_csrf_token))

        def _opinion_post(self):
            """Record one item's opinion, or withdraw one, under the digest it was shown with.

            Same rules as a disposition and a separate ledger: an opinion about one duty is
            not a decision about the candidate. Nothing here creates a version, activates
            one, or changes a row's qualification.
            """
            if not self._knowledge_origin_ok():
                self.close_connection = True
                self._error('opinion_origin_or_csrf_invalid', 'Use this local Workspace.', status=403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384 or self.headers.get_content_type() != 'application/json':
                    raise _LocalRequestError('opinion_request_invalid')
                payload = json.loads(self.rfile.read(length))
                if (not isinstance(payload, dict)
                        or set(payload) - {'scope_id', 'candidate_id', 'item_id', 'content_digest',
                                           'stance', 'reason', 'withdraw'}):
                    raise _LocalRequestError('opinion_request_invalid')
                if payload.get('withdraw'):
                    result = opinions.withdraw(record_id=str(payload['withdraw']),
                                               reason=payload.get('reason') or '')
                else:
                    candidate_id = payload.get('candidate_id') or ''
                    scope_id = payload.get('scope_id') or daily_scope
                    rows = []
                    for item in run_products_view({'scope': [scope_id]}).get('items', []):
                        if item.get('candidate_id') == candidate_id and item.get('readable'):
                            rows = item.get('rows') or []
                            break
                    row = next((row for row in rows
                                if str(row.get('item_id')) == str(payload.get('item_id'))), None)
                    if row is None:
                        raise review_surface.ReadingError(
                            'opinion_item_unknown', '这个运行产物里没有该条目。', 404)
                    if payload.get('content_digest') != row.get('digest'):
                        raise review_surface.ReadingError(
                            'opinion_item_changed',
                            '条目内容与留意见时看到的不一致，意见未记录；重新读取后再留意见。', 409)
                    result = opinions.record(scope_id=scope_id, candidate_id=candidate_id,
                                             item_id=str(row.get('item_id')),
                                             content_digest=row.get('digest') or '',
                                             stance=payload.get('stance') or '',
                                             reason=payload.get('reason') or '')
                self._json(result, status=201)
            except review_surface.ReadingError as exc:
                self._error(exc.code, str(exc), status=exc.status)
            except _LocalRequestError as exc:
                self._error(exc.code, '逐条意见请求不合法。', status=exc.status)
            except (ValueError, KeyError, OSError, TypeError):
                self._error('opinion_failed', '逐条意见没有记录。', status=400)

        def _disposition_post(self):
            """Record a review disposition, bound to the digest the reviewer was shown.

            This is the interaction the old review page had and the Wiki never accepted as
            a decision: a person can accept, defer or reject a candidate with a reason, and
            withdraw it later. Nothing here creates a version, activates one, or writes to
            a scope: the ledger is what a later reader checks the opinion against.
            """
            if not self._knowledge_origin_ok():
                self.close_connection = True
                self._error('disposition_origin_or_csrf_invalid', 'Use this local Workspace.', status=403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384 or self.headers.get_content_type() != 'application/json':
                    raise _LocalRequestError('disposition_request_invalid')
                payload = json.loads(self.rfile.read(length))
                if (not isinstance(payload, dict)
                        or set(payload) - {'scope_id', 'candidate_id', 'content_digest', 'action', 'reason', 'withdraw'}):
                    raise _LocalRequestError('disposition_request_invalid')
                if payload.get('withdraw'):
                    result = dispositions.withdraw(record_id=str(payload['withdraw']),
                                                   reason=payload.get('reason') or '')
                else:
                    from .semantic_wiki import _candidate_content_digest
                    book, _row = chosen_scope({'scope': [payload.get('scope_id') or daily_scope]})
                    candidate = (book.semantic_state()['candidates'].get(payload.get('candidate_id') or '')
                                 or {})
                    if not candidate:
                        raise review_surface.ReadingError('candidate_missing', '这个范围里没有该候选。', 404)
                    current = _candidate_content_digest(candidate)
                    if payload.get('content_digest') != current:
                        raise review_surface.ReadingError(
                            'candidate_changed',
                            '候选内容与处置时看到的不一致，处置未记录；重新读取后再处置。', 409)
                    result = dispositions.record(scope_id=book.scope_id,
                                                 candidate_id=payload['candidate_id'],
                                                 content_digest=current,
                                                 action=payload.get('action') or '',
                                                 reason=payload.get('reason') or '',
                                                 source_revision=candidate.get('source_revision'))
                self._json(result, status=201)
            except review_surface.ReadingError as exc:
                self._error(exc.code, str(exc), status=exc.status)
            except _LocalRequestError as exc:
                self._error(exc.code, '处置请求不合法。', status=exc.status)
            except (ValueError, KeyError, OSError, TypeError):
                self._error('disposition_failed', '处置没有记录。', status=400)

        def _knowledge_stage_post(self):
            """Let one explicit local file enter Wiki, and stop at the candidate layer."""
            if not self._knowledge_origin_ok():
                self.close_connection = True
                self._error('knowledge_origin_or_csrf_invalid', 'Use this local Workspace.', status=403)
                return
            if not session._execution.acquire(blocking=False):
                self._error('workspace_busy', 'Finish the current request first.', status=409)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= _KNOWLEDGE_UPLOAD_BODY_BYTES or self.headers.get_content_type() != 'application/json':
                    self.close_connection = True
                    raise _LocalRequestError('knowledge_upload_invalid')
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or set(payload) != {'name', 'data_base64'}:
                    raise _LocalRequestError('knowledge_upload_invalid')
                name = payload['name']
                if not isinstance(name, str) or not re.fullmatch(r'[^/\\:*?"<>|]{1,160}', name):
                    raise _LocalRequestError('knowledge_upload_invalid')
                suffix = Path(name).suffix.casefold()
                if suffix not in SUPPORTED_SOURCE_SUFFIXES:
                    raise _LocalRequestError('knowledge_upload_unsupported_format')
                raw = base64.b64decode(payload['data_base64'], validate=True)
                limit = MAX_PART_TEXT_BYTES if suffix == '.md' else MAX_SOURCE_BYTES
                if not raw or len(raw) > limit:
                    raise _LocalRequestError('knowledge_upload_too_large')
                target_dir = (session.input_root / 'uploads').resolve()
                target_dir.mkdir(parents=True, exist_ok=True)
                target = (target_dir / name).resolve()
                if target.parent != target_dir:
                    raise _LocalRequestError('knowledge_upload_invalid')
                target.write_bytes(raw)
                # A method this workspace admitted and activated reads the document under its
                # own lease; with none active the product tree reads it and the response says
                # which assembly ran (response.assembly.kind), so a merged commit cannot
                # pass for one.
                result = intake_source(wiki, target, source_root=session.input_root,
                                       actor_origin='local_workspace_user',
                                       methods=session.app.components)
                self._json(result, status=201)
            except _LocalRequestError as exc:
                self._error(exc.code, 'The document was not accepted for registration.', status=exc.status)
            except KnowledgeIntakeError as exc:
                self._error(getattr(exc, 'code', 'knowledge_intake_failed'),
                            'The file was stored but could not become a candidate.', status=409)
            except (ValueError, OSError, KeyError, TypeError, binascii.Error):
                self._error('knowledge_upload_invalid',
                            'Select a Markdown, Word, PowerPoint or PDF file under the size limit.', status=400)
            finally:
                session._execution.release()

        def _knowledge_withdraw_post(self):
            """Stop one staged source from being read or searched, keeping its history."""
            if not self._knowledge_origin_ok():
                self.close_connection = True
                self._error('knowledge_origin_or_csrf_invalid', 'Use this local Workspace.', status=403)
                return
            if not session._execution.acquire(blocking=False):
                self._error('workspace_busy', 'Finish the current request first.', status=409)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096 or self.headers.get_content_type() != 'application/json':
                    raise _LocalRequestError('knowledge_withdraw_invalid')
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or set(payload) != {'source_id'}:
                    raise _LocalRequestError('knowledge_withdraw_invalid')
                source_id = payload['source_id']
                if not isinstance(source_id, str) or not re.fullmatch(r'[A-Za-z0-9_:-]{1,160}', source_id):
                    raise _LocalRequestError('knowledge_withdraw_invalid')
                self._json(wiki.withdraw_source(source_id))
            except WikiScopeError:
                self._error('knowledge_withdraw_unavailable', 'That source is not staged in this scope.', status=404)
            except _LocalRequestError as exc:
                self._error(exc.code, 'Send one staged source identity.', status=exc.status)
            except (ValueError, OSError, KeyError, TypeError):
                self._error('knowledge_withdraw_invalid', 'Send one staged source identity.', status=400)
            finally:
                session._execution.release()

        def _test_post(self):
            if (not self._host_allowed() or not self._origin_allowed() or
                    not secrets.compare_digest(self.headers.get('X-Catalyst-CSRF',''),server.local_csrf_token)):
                self.close_connection=True
                self._error('project_origin_or_csrf_invalid','Use this local Workspace.',status=403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=16384 or self.headers.get_content_type()!='application/json':
                    self.close_connection=True
                    raise ValueError('test_request_invalid')
                payload=json.loads(self.rfile.read(length))
                if not isinstance(payload,dict):raise ValueError('test_request_invalid')
                if set(payload)=={'action','request','confirmed'} and payload['action']=='draft':
                    if (payload['confirmed'] is not True or not isinstance(payload['request'],str)
                            or not 1<=len(payload['request'].strip())<=2000 or not sources
                            or project_live_scope is not None or not session.settings.snapshot()['test_connection_available']):
                        raise ValueError('explicit_planning_allowance_required')
                    project_tests.planning_allowance()
                    self._project_post({'source_id':next(iter(sources)),'objective':payload['request'],'max_depth':0},
                                       plan_request=payload['request'])
                    return
                if set(payload)=={'action','source_id','objective','max_depth'} and payload['action']=='prepare':
                    row=project_tests.prepare(payload['source_id'],payload['objective'],payload['max_depth'])
                    self._json(row);return
                if set(payload)=={'action','source_id','objective','max_depth','limits'} and payload['action']=='prepare':
                    row=project_tests.prepare(payload['source_id'],payload['objective'],payload['max_depth'],limits=payload['limits'])
                    self._json(row);return
                if set(payload)!={'action','test_id','card_sha256','confirmed'} or payload['action']!='execute' or payload['confirmed'] is not True:
                    raise ValueError('explicit_test_confirmation_required')
                if project_live_scope is not None:raise ValueError('legacy_scope_cannot_launch_project_test')
                if not session.settings.snapshot()['test_connection_available']:raise ValueError('model_connection_unavailable')
                row=project_tests.validate(payload['test_id'],payload['card_sha256']);c=row['card']
            except (ValueError,OSError,KeyError,TypeError):
                self._error('project_test_preflight_blocked','Check model connection, card and source qualification.',status=409);return
            self._project_post({'source_id':c['source_id'],'objective':c['objective'],'max_depth':c['max_depth']},test_row=row)

        def _project_post(self, accepted=None, *, test_row=None, plan_request=None):
            if (not self._host_allowed() or not self._origin_allowed() or
                    not secrets.compare_digest(self.headers.get('X-Catalyst-CSRF', ''), server.local_csrf_token)):
                self.close_connection = True
                self._error('project_origin_or_csrf_invalid', 'Use this local Workspace.', status=403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384 or self.headers.get_content_type() != 'application/json':
                    self.close_connection = True
                    raise ValueError('project_request_invalid')
                body = accepted if accepted is not None else json.loads(self.rfile.read(length))
                fields={'source_id', 'objective', 'max_depth'}
                if (not isinstance(body, dict) or not fields<=set(body) or set(body)-fields-{'source_approval_sha256'}
                        or not isinstance(body['source_id'], str) or body['source_id'] not in sources
                        or not isinstance(body['objective'], str) or not body['objective'].strip()
                        or len(body['objective']) > 4000 or type(body['max_depth']) is not int
                        or body['max_depth'] not in (0, 1, 2)):
                    raise ValueError('project_request_invalid')
                if test_row is None and plan_request is None and sources[body['source_id']].get('task_kind')=='enterprise_semantics':
                    raise ValueError('semantic_test_requires_reviewed_card')
                approved=None
                daily=session.settings.snapshot()['connection_mode']=='daily'
                if test_row is None and plan_request is None and daily:
                    from .project_understand import source_manifest,digest
                    approved=digest(source_manifest(sources[body['source_id']]['root']))
                    if body.get('source_approval_sha256')!=approved:
                        raise ValueError('daily_source_approval_required')
            except (ValueError, UnicodeDecodeError):
                self._error('project_request_invalid', 'Select an admitted source, objective and static depth.', status=400)
                return
            if not session._execution.acquire(blocking=False):
                self._error('workspace_busy', 'Finish the current request first.', status=409)
                return
            try:
                with session._control:
                    if session._pending:
                        self._error('workspace_busy', 'Finish the queued request first.', status=409)
                        return
            finally:
                session._execution.release()
            token = 'project_host_' + secrets.token_hex(32)
            request = {**body, 'spec': dict(sources[body['source_id']]), 'queued': False}
            if approved is not None:
                request['spec'].update(approved_manifest_sha256=approved,daily_read_approval_sha256=approved)
            if test_row is not None:request.update(test_id=test_row['test_id'],card_sha256=test_row['card_sha256'])
            if plan_request is not None:request['plan_request']=plan_request
            requests[token] = request
            # Original Monitor owns recorder creation, prepare/cancel, asynchronous
            # execution, R4 and result persistence. This is only an admission adapter.
            raw = json.dumps({'message': token, 'selected_file': None}).encode()
            original_path, original_file = self.path, self.rfile
            original_length = self.headers.get('Content-Length')
            self.path, self.rfile = '/api/ask', io.BytesIO(raw)
            self.headers.replace_header('Content-Length', str(len(raw)))
            admission.token = token
            try:
                super().do_POST()
            finally:
                admission.token = None
                self.path, self.rfile = original_path, original_file
                self.headers.replace_header('Content-Length', original_length)
                if not request['queued']:
                    requests.pop(token, None)

        def _maintenance_post(self):
            if getattr(session.session, '_project_pending_handles', {}):
                self.close_connection=True
                self._error('project_runtime_unresolved','A prior execution requires qualified reconciliation.',status=409)
                return
            route = urlsplit(self.path).path
            if server.restart_requested:
                self.close_connection=True
                self._error('workspace_restarting','Wait for restart before submitting work.',status=409)
                return
            if route == '/api/knowledge/stage':
                self._knowledge_stage_post()
                return
            if route == '/api/knowledge/withdraw':
                self._knowledge_withdraw_post()
                return
            if route == '/api/review-dispositions':
                self._disposition_post()
                return
            if route == '/api/review-item-opinions':
                self._opinion_post()
                return
            if route == '/api/development-offline':
                if (not self._host_allowed() or not self._origin_allowed() or
                        not secrets.compare_digest(self.headers.get('X-Catalyst-CSRF', ''), server.local_csrf_token)):
                    self.close_connection=True
                    self._error('development_origin_or_csrf_invalid','Use this local Workspace.',status=403);return
                try:
                    length = int(self.headers.get('Content-Length','0'))
                    if not 0 < length <= 1024 or self.headers.get_content_type() != 'application/json':
                        raise ValueError('invalid request')
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict) or set(payload) != {'profile'}:
                        raise ValueError('invalid fields')
                    if not session._execution.acquire(blocking=False):
                        self._error('workspace_busy','Finish the current request first.',status=409);return
                    try:
                        with session._control:
                            if session._pending: raise ValueError('workspace_busy')
                        from .evaluation_workflow import run_offline_check
                        result = run_offline_check(session.app, payload['profile'])
                    finally:
                        session._execution.release()
                    self._json(result)
                except (ValueError, KeyError, OSError, TypeError):
                    self._error('development_offline_blocked','Offline evaluation could not be completed.',status=409)
                return
            if route == '/api/project-tests':
                self._test_post()
                return
            if route == '/api/project-analysis':
                self._project_post()
                return
            if project_live_scope is not None and route=='/api/ask':
                self.close_connection=True
                self._error('project_scope_only','This isolated scope only admits its project task.',status=403)
                return
            if route not in ('/api/settings','/api/maintenance'):
                super().do_POST()
                return
            if (not self._host_allowed() or not self._origin_allowed() or
                not secrets.compare_digest(self.headers.get('X-Catalyst-CSRF', ''), self.server.local_csrf_token)):
                self._error('settings_origin_or_csrf_invalid', 'Use this local Workspace to configure settings.', status=403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384 or self.headers.get_content_type() != 'application/json':
                    self.close_connection = True
                    self._error('settings_request_invalid', 'Bounded JSON settings required.', status=400)
                    return
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict) or set(payload) != {'action', 'data'}:
                    raise ValueError('settings_fields_invalid')
            except (ValueError, UnicodeDecodeError):
                self._error('settings_request_invalid', 'Bounded JSON settings required.', status=400)
                return
            if not session._execution.acquire(blocking=False):
                self._error('workspace_busy', 'Finish the current request before changing its model scope.', status=409)
                return
            try:
                action, data = payload['action'], payload['data']
                if route == '/api/maintenance':
                    with session._control:
                        if session._pending:
                            raise ValueError('maintenance_tasks_pending')
                    if action=='prepare' and data=={}:
                        result=server.maintenance.prepare()
                    elif action=='prepare' and isinstance(data,dict) and set(data)=={'target'} and data['target'] in ('local_text_stats','project-understand'):
                        result=server.maintenance.prepare(target=data['target'])
                    elif action in ('approve','reject','rollback') and isinstance(data,dict) and set(data)=={'review_id','approval_digest','confirmed'}:
                        method=server.maintenance.request_rollback if action=='rollback' else getattr(server.maintenance,action)
                        result=method(data['review_id'],data['approval_digest'],confirmed=data['confirmed'])
                    elif action=='restart' and data=={'confirmed':True}:
                        with session._control:
                            if session._pending:
                                raise ValueError('maintenance_tasks_pending')
                        session.settings.ledger_factory.check_prior_scopes(session.settings.root/'scopes')
                        session.settings.disconnect()
                        server.restart_requested=True
                        self.close_connection=True
                        self._json({'status':'RESTARTING','credentials':'CLEARED_REENTER_AFTER_RESTART'})
                        threading.Thread(target=server.shutdown,daemon=True).start()
                        return
                    else:raise ValueError('maintenance_action_not_allowed')
                    self._json(result)
                    return
                if action == 'profile' and isinstance(data, dict):
                    result = session.settings.update_profile(data)
                elif action in {'connection','credential_save','credential_forget','model_saved','model_remember',
                                'qualification_check','qualification_approve'} and isinstance(data,dict):
                    with session._control:
                        if session._pending:raise ValueError('workspace_tasks_pending')
                    if project_live_scope is not None:raise ValueError('legacy_scope_settings_fixed')
                    if action=='connection':result=session.settings.connect(data)
                    elif action=='credential_save':result=session.settings.save_credential(data)
                    elif action=='credential_forget':result=session.settings.forget_credential(data)
                    elif action=='model_saved':result=session.settings.configure_saved(data)
                    elif action=='model_remember':result=session.settings.configure_and_remember(data)
                    elif action=='qualification_approve':result=session.settings.approve_qualification(data)
                    elif data=={}:result=session.settings.check_qualification()
                    else:raise ValueError('qualification_check_fields_invalid')
                elif action == 'model' and isinstance(data, dict):
                    result = session.settings.configure(data)
                elif action == 'disconnect' and data == {}:
                    result = session.settings.disconnect()
                elif action == 'clear_history' and data == {}:
                    session.settings.chat.new_thread()
                    session.settings.history = []
                    result = session.settings.snapshot()
                    result['chat_thread_id'] = session.settings.chat.thread()
                else:
                    raise ValueError('settings_action_invalid')
                self._json(result)
            except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
                # Only stable policy errors; never echo input or raw Provider bodies.
                code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r'[a-z0-9_]{1,120}', str(exc)) else 'settings_configuration_rejected'
                self._error(code, 'Configuration was not activated. Review the declared scope and limits.', status=400)
            finally:
                session._execution.release()

    server.RequestHandlerClass = WorkspaceHandler
    return server


def main():
    parser = argparse.ArgumentParser(description='Catalyst local Workspace; text Live requires explicit browser model scope.')
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--project-config',type=Path,help='Trusted Host-only frozen project source and optional one-shot live scope JSON; no credentials.')
    parser.add_argument('--port', type=int, default=8792)
    parser.add_argument('--wiki-backend', choices=['json', 'sqlite'], default='json')
    parser.add_argument('--mode', choices=['mock', 'blocked'], default='mock')
    parser.add_argument('--ledger-module', type=Path, help='Trusted local path for the qualified Host durable engine; requires --ledger-sha256.')
    parser.add_argument('--ledger-sha256', help='Qualified engine identity; arbitrary hashes are not admitted.')
    parser.add_argument('--model-qualification', type=Path, default=DEFAULT_QUALIFICATION,
                        help='Trusted local model/rate qualification JSON; never a credential file or browser option.')
    args = parser.parse_args()
    if (args.ledger_module is None) != (args.ledger_sha256 is None):
        parser.error('--ledger-module and --ledger-sha256 must be supplied together')
    ledger_factory = None
    if args.ledger_module is not None:
        from .workspace_ledger import PinnedHostLedgerFactory
        try:
            ledger_factory = PinnedHostLedgerFactory(args.ledger_module, args.ledger_sha256)
        except ValueError:
            parser.error('Unqualified ledger identity; no engine was loaded.')
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    project_sources=None;project_live_scope=None
    if args.project_config:
        config=json.loads(args.project_config.read_text(encoding='utf-8'))
        if not isinstance(config,dict) or not {'sources'}<=set(config) or set(config)-{'sources','live_scope'}:parser.error('invalid project config')
        project_sources={sid:{**spec,'root':Path(spec['root'])} for sid,spec in config['sources'].items()}
        for spec in project_sources.values():
            if 'method_root' in spec:spec['method_root']=Path(spec['method_root'])
        project_live_scope=config.get('live_scope')
    while True:
        server = create_workspace_server(args.workspace, port=args.port,
                                         backend=args.wiki_backend, mode=args.mode.upper(), ledger_factory=ledger_factory,
                                         qualification_path=args.model_qualification,project_sources=project_sources,project_live_scope=project_live_scope)
        print(f'Catalyst Workspace: http://127.0.0.1:{server.server_address[1]}/ (files={args.mode.upper()}, text credentials initially absent; browser scope required)', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.restart_requested=False
        finally:
            server.server_close()
            if server.restart_requested:
                server.run_request.app.components.close_loaded()
                server.run_request.app.plugins.close()
        if not server.restart_requested:
            break


if __name__ == '__main__':
    main()
