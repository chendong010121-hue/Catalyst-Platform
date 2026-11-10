"""Local desktop composition entry using the mainline native-tools Runtime."""

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import uuid
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from agent_runtime.contracts import Complete, Goal, ModelResponse, ModelToolCall
from agent_runtime.errors import ModelProviderError
from agent_runtime.native_tools_v2 import NativeToolsV2Reasoner, NativeToolsV2Runtime
from agent_runtime.policies import StepLimitPolicy

from . import context_window, wiki_search, workspace_tools
from .context import SERVICE as CONTEXT_SERVICE, BoundedProvider, ContextLimitExceeded, Turn
from .conversations import Conversations
from .desktop_connection import DesktopConnection
from .plugin_composition import PluginComposer


class _RunSnapshots:
    """Runtime checkpoints for one run. Desktop receipts are durable; runs cannot resume here."""

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        self.snapshot = snapshot


class Desktop:
    def __init__(self, workspace, *, composer, provider, provider_mode, input_budget=16384, connection=None):
        if type(input_budget) is not int or input_budget < 1024:
            raise ValueError("input_budget_too_small")
        workspace = Path(workspace).resolve()
        self.workspace_id = hashlib.sha256(os.path.normcase(str(workspace)).encode("utf-8")).hexdigest()
        state_root = workspace / ".catalyst"
        self.runs = state_root / "desktop-runs"
        self.artifacts = state_root / "desktop-artifacts"
        self.conversations = Conversations(state_root)
        self.composer = composer
        self.provider = provider
        self.provider_mode = provider_mode
        self.input_budget = input_budget
        self.connection = connection

    def status(self):
        strategy = self.composer.service(CONTEXT_SERVICE)
        provider = self.connection.provider if self.connection is not None else self.provider
        return {
            "provider_mode": self.connection.mode if self.connection is not None else self.provider_mode,
            "can_chat": provider is not None,
            "plugins": self.composer.active_plugins,
            "available_tools": [wiki_search.TOOL_ID] if self.composer.service(wiki_search.SERVICE) else [],
            "context_strategy": strategy.version if strategy is not None else None,
            "input_budget": self.input_budget,
            "workspace_id": self.workspace_id,
            "connection": self.connection.status() if self.connection is not None else None,
            "local_tools": [workspace_tools.CATALOG, workspace_tools.WRITE_NOTE]
            if self.connection is not None else [workspace_tools.WRITE_NOTE],
        }

    def read_run(self, run_id):
        try:
            return json.loads((self.runs / (run_id + ".json")).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def conversation(self, conversation_id):
        turns = []
        for run_id, message in self.conversations.turns(conversation_id):
            receipt = self.read_run(run_id)
            turns.append({
                "run_id": run_id,
                "message": message,
                "state": receipt["state"] if receipt else "UNRESOLVED",
                "answer": receipt["answer"] if receipt else None,
                "error": receipt["error"] if receipt else "run_receipt_missing",
                "has_receipt": receipt is not None,
            })
        return {"id": conversation_id, "turns": turns}

    def _context_turns(self, conversation_id, run_id):
        turns = []
        for previous_id, message in self.conversations.turns(conversation_id, before=run_id):
            receipt = self.read_run(previous_id)
            if receipt and receipt["state"] == "COMPLETED":
                turns.append(Turn(previous_id, message, receipt["answer"]))
        return turns

    def chat(self, message, *, allow_wiki, allow_note=False, conversation_id=None, request_id=None):
        if request_id is not None:
            existing = self.read_run(request_id)
            if existing is not None:
                if (
                    existing.get("conversation_id") != conversation_id or existing["message"] != message
                    or (wiki_search.TOOL_ID in existing["visible_tools"]) != allow_wiki
                    or (workspace_tools.WRITE_NOTE in existing["visible_tools"]) != allow_note
                ):
                    raise ValueError("request_identity_conflict")
                return existing
        model_provider = self.connection.provider if self.connection is not None else self.provider
        if model_provider is None:
            raise ValueError("model_not_configured")
        wiki = self.composer.service(wiki_search.SERVICE)
        if allow_wiki and wiki is None:
            raise ValueError("wiki_not_mounted")
        run_id = request_id or uuid.uuid4().hex
        if conversation_id is not None:
            if not self.conversations.reserve(conversation_id, run_id, message, allow_wiki, allow_note):
                receipt = self.read_run(run_id)
                if receipt is None:
                    raise ValueError("request_unresolved")
                return receipt
        strategy = self.composer.service(CONTEXT_SERVICE)
        turns = self._context_turns(conversation_id, run_id) if strategy is not None and conversation_id is not None else ()
        max_requests = self.connection.max_requests if self.connection is not None else 4
        max_output = self.connection.max_output_tokens if self.connection is not None else None
        provider = BoundedProvider(model_provider, strategy, turns, self.input_budget,
                                   max_requests=max_requests, max_output_tokens=max_output)
        capabilities = {wiki_search.TOOL_ID: wiki} if allow_wiki else {}
        if allow_note:
            capabilities[workspace_tools.WRITE_NOTE] = workspace_tools.WriteNote(self.artifacts, run_id)
        if self.connection is not None:
            catalog = workspace_tools.CATALOG
            available = (catalog, workspace_tools.WRITE_NOTE, *((wiki_search.TOOL_ID,) if wiki is not None else ()))
            capabilities[catalog] = workspace_tools.ToolCatalog(available, {catalog, *capabilities})
        snapshots = _RunSnapshots()
        runtime = NativeToolsV2Runtime(
            reasoner=NativeToolsV2Reasoner(provider),
            capabilities=capabilities,
            policy=StepLimitPolicy(4),
            state_store=snapshots,
        )
        snapshot = runtime.create(Goal(message))
        error = None
        auth_failure = False
        try:
            snapshot = runtime.run(snapshot.session_id)
        except Exception as exc:
            snapshot = snapshots.load(snapshot.session_id)
            error = str(exc) if isinstance(exc, ContextLimitExceeded) else type(exc).__name__
            if isinstance(exc, ModelProviderError) and exc.status in (401, 403):
                error = "deepseek_key_rejected"
                auth_failure = True
        if self.connection is not None:
            if auth_failure:
                self.connection.verified = False
            elif any("reported_usage" in call for call in provider.calls):
                self.connection.verified = True
        last = snapshot.history[-1] if snapshot.history else None
        decision = last.decision if last else None
        complete = error is None and isinstance(decision, Complete)
        calls = [turn.model_call for turn in snapshot.native_tools_v2_turns]
        if complete and last.model_call is not None:
            calls.append(last.model_call)
        receipt = {
            "run_id": run_id,
            "runtime_session_id": snapshot.session_id,
            "state": "COMPLETED" if complete else "UNRESOLVED" if snapshot.pending_execution else "STOPPED",
            "provider_mode": self.connection.mode if self.connection is not None else self.provider_mode,
            "message": message,
            "answer": decision.reason if complete else None,
            "error": error or (None if complete else getattr(decision, "reason", "run_stopped")),
            "plugins": self.composer.active_plugins,
            "visible_tools": list(capabilities),
            "context": {
                "strategy": strategy.version if strategy is not None else None,
                "requests": provider.calls,
            },
            "provider_attempts": provider.attempts,
            "max_provider_requests": max_requests,
            "max_output_tokens": max_output,
            "recorded_model_calls": [
                {"finish_reason": call.finish_reason, "usage": asdict(call.usage) if call.usage else None}
                for call in calls
            ],
            "tool_calls": [
                {
                    "id": call.tool_call_id, "name": call.name, "status": call.status,
                    "result": asdict(call.observation) if call.observation else None,
                }
                for turn in snapshot.native_tools_v2_turns for call in turn.calls
            ],
        }
        if conversation_id is not None:
            receipt["conversation_id"] = conversation_id
            first = provider.calls[0] if provider.calls else {}
            receipt["context_run_ids"] = first.get("checkpoint_run_ids", []) + first.get("recent_run_ids", [])
        self.runs.mkdir(parents=True, exist_ok=True)
        destination = self.runs / (run_id + ".json")
        temporary = destination.with_suffix(".tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return receipt


def create_server(desktop, port=0):
    root = Path(__file__).resolve().parent
    assets = {
        "/": ("text/html; charset=utf-8", (root / "desktop.html").read_bytes()),
        "/desktop.js": ("text/javascript; charset=utf-8", (root / "desktop.js").read_bytes()),
    }
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    ).stdout.strip()
    digest = hashlib.sha256()
    for filename in (
        "desktop.py", "desktop.html", "desktop.js", "plugin_composition.py",
        "wiki_search.py", "conversations.py", "context.py", "context_window.py",
        "desktop_connection.py", "windows_dpapi.py", "workspace_tools.py",
    ):
        digest.update((root / filename).read_bytes())
    build = {"commit": commit or None, "desktop_digest": digest.hexdigest()}
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def reply(self, status, data, media="application/json; charset=utf-8"):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", media)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def local(self):
            host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != host or self.headers.get("Origin") not in (None, "http://" + host):
                self.reply(403, {"error": "local_origin_required"})
                return False
            return True

        def do_GET(self):
            if not self.local():
                return
            if self.path in assets:
                media, data = assets[self.path]
                self.reply(200, data, media)
            elif self.path == "/api/status":
                self.reply(200, {**desktop.status(), "build": build, "csrf_token": token})
            elif self.path == "/api/conversations":
                self.reply(200, {"items": desktop.conversations.list()})
            elif match := re.fullmatch(r"/api/conversations/([0-9a-f]{32})", self.path):
                try:
                    conversation = desktop.conversation(match[1])
                except KeyError:
                    self.reply(404, {"error": "conversation_not_found"})
                else:
                    self.reply(200, conversation)
            elif match := re.fullmatch(r"/api/runs/([0-9a-f]{32})", self.path):
                receipt = desktop.read_run(match[1])
                if receipt is not None:
                    self.reply(200, receipt)
                else:
                    self.reply(404, {"error": "run_not_found"})
            elif match := re.fullmatch(r"/api/artifacts/([0-9a-f]{32})", self.path):
                path = desktop.artifacts / (match[1] + ".md")
                if path.resolve() == path and path.is_file():
                    self.reply(200, path.read_bytes(), "text/plain; charset=utf-8")
                else:
                    self.reply(404, {"error": "artifact_not_found"})
            else:
                self.reply(404, {"error": "not_found"})

        def do_POST(self):
            if not self.local():
                return
            if self.path not in ("/api/chat", "/api/conversations", "/api/connection"):
                self.reply(404, {"error": "not_found"})
                return
            if not secrets.compare_digest(self.headers.get("X-Catalyst-CSRF", ""), token):
                self.reply(403, {"error": "csrf_required"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16000 or self.headers.get_content_type() != "application/json":
                    raise ValueError
                body = json.loads(self.rfile.read(size))
            except (ValueError, UnicodeError):
                self.reply(400, {"error": "invalid_request"})
                return
            if self.path == "/api/connection":
                if desktop.connection is None:
                    self.reply(409, {"error": "connection_unavailable"})
                    return
                try:
                    desktop.connection.configure(body)
                except ValueError as exc:
                    self.reply(400, {"error": str(exc)})
                except OSError:
                    self.reply(500, {"error": "credential_store_unavailable"})
                else:
                    self.reply(200, {**desktop.status(), "build": build, "csrf_token": token})
                return
            if self.path == "/api/conversations":
                if body != {}:
                    self.reply(400, {"error": "invalid_conversation_request"})
                    return
                self.reply(201, {"id": desktop.conversations.create()})
                return
            basic = {"message", "allow_wiki"}
            identities = {"conversation_id", "request_id"}
            if (
                not isinstance(body, dict) or set(body) - {"allow_note"} not in (basic, basic | identities)
                or not isinstance(body["message"], str) or not 1 <= len(body["message"].strip()) <= 2000
                or type(body["allow_wiki"]) is not bool
                or type(body.get("allow_note", False)) is not bool
                or any(not isinstance(body[key], str) or not re.fullmatch(r"[0-9a-f]{32}", body[key])
                       for key in identities if key in body)
            ):
                self.reply(400, {"error": "invalid_chat_request"})
                return
            try:
                receipt = desktop.chat(
                    body["message"].strip(), allow_wiki=body["allow_wiki"],
                    allow_note=body.get("allow_note", False),
                    conversation_id=body.get("conversation_id"), request_id=body.get("request_id"),
                )
            except KeyError:
                self.reply(404, {"error": "conversation_not_found"})
                return
            except ValueError as exc:
                self.reply(409, {"error": str(exc)})
                return
            except OSError:
                self.reply(500, {"error": "run_receipt_not_saved"})
                return
            self.reply(200, receipt)

    return HTTPServer(("127.0.0.1", port), Handler)


class _DemoProvider:
    def request(self, request):
        message = request.messages[-1].content
        if request.messages[-1].role == "tool":
            try:
                result = json.loads(message)
            except json.JSONDecodeError:
                return ModelResponse(content="离线演示 · 模型收到 Wiki 结果节选，请在本轮证据查看完整返回。")
            if not isinstance(result, dict) or "matches" not in result:
                return ModelResponse(content="离线演示 · Wiki 查询未完成，请查看本轮证据。")
            return ModelResponse(content=f"离线演示 · Wiki 返回 {len(result['matches'])} 条结果。请打开本轮证据查看。")
        if request.tools:
            call = ModelToolCall("demo-wiki", wiki_search.TOOL_ID, json.dumps({"query": message[:200]}))
            return ModelResponse(tool_calls=(call,), finish_reason="tool_calls")
        return ModelResponse(content=f"离线演示 · 已收到：{message}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--wiki-export", type=Path)
    parser.add_argument("--input-budget", type=int, default=16384, help="Local input estimate limit, minimum 1024.")
    parser.add_argument("--no-context", action="store_true", help="Disable history projection and tool excerpts.")
    parser.add_argument("--demo", action="store_true", help="Use a local demonstration provider with no network.")
    args = parser.parse_args()
    definitions = [wiki_search.definition(wiki_search.load_export(args.wiki_export))] if args.wiki_export else []
    if not args.no_context:
        definitions.append(context_window.definition())
    composer = PluginComposer(definitions=definitions, profiles={"desktop": [item.plugin_id for item in definitions]})
    composer.compose("desktop")
    desktop = Desktop(args.workspace, composer=composer, provider=_DemoProvider() if args.demo else None,
                      provider_mode="OFFLINE_DEMO" if args.demo else "UNCONFIGURED",
                      connection=None if args.demo else DesktopConnection(args.workspace),
                      input_budget=args.input_budget)
    try:
        with create_server(desktop, args.port) as server:
            print(f"http://127.0.0.1:{server.server_port}/", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        composer.close()


if __name__ == "__main__":
    main()
