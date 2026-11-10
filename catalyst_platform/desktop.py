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
from agent_runtime.native_tools_v2 import NativeToolsV2Reasoner, NativeToolsV2Runtime
from agent_runtime.policies import StepLimitPolicy

from . import wiki_search
from .plugin_composition import PluginComposer


class _RunSnapshots:
    """Runtime checkpoints for one run. Desktop receipts are durable; runs cannot resume here."""

    def load(self, session_id):
        return self.snapshot

    def commit(self, snapshot):
        self.snapshot = snapshot


class Desktop:
    def __init__(self, workspace, *, composer, provider, provider_mode):
        self.runs = Path(workspace).resolve() / ".catalyst" / "desktop-runs"
        self.composer = composer
        self.provider = provider
        self.provider_mode = provider_mode

    def status(self):
        return {
            "provider_mode": self.provider_mode,
            "can_chat": self.provider is not None,
            "plugins": self.composer.active_plugins,
            "available_tools": [wiki_search.TOOL_ID] if self.composer.service(wiki_search.SERVICE) else [],
        }

    def chat(self, message, *, allow_wiki):
        if self.provider is None:
            raise ValueError("model_not_configured")
        wiki = self.composer.service(wiki_search.SERVICE)
        if allow_wiki and wiki is None:
            raise ValueError("wiki_not_mounted")
        capabilities = {wiki_search.TOOL_ID: wiki} if allow_wiki else {}
        snapshots = _RunSnapshots()
        runtime = NativeToolsV2Runtime(
            reasoner=NativeToolsV2Reasoner(self.provider),
            capabilities=capabilities,
            policy=StepLimitPolicy(4),
            state_store=snapshots,
        )
        run_id = uuid.uuid4().hex
        snapshot = runtime.create(Goal(message))
        error = None
        try:
            snapshot = runtime.run(snapshot.session_id)
        except Exception as exc:
            snapshot = snapshots.load(snapshot.session_id)
            error = type(exc).__name__
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
            "provider_mode": self.provider_mode,
            "message": message,
            "answer": decision.reason if complete else None,
            "error": error or (None if complete else getattr(decision, "reason", "run_stopped")),
            "plugins": self.composer.active_plugins,
            "visible_tools": list(capabilities),
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
    for filename in ("desktop.py", "desktop.html", "desktop.js", "plugin_composition.py", "wiki_search.py"):
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
            elif match := re.fullmatch(r"/api/runs/([0-9a-f]{32})", self.path):
                path = desktop.runs / (match[1] + ".json")
                if path.is_file():
                    self.reply(200, path.read_bytes())
                else:
                    self.reply(404, {"error": "run_not_found"})
            else:
                self.reply(404, {"error": "not_found"})

        def do_POST(self):
            if not self.local():
                return
            if self.path != "/api/chat":
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
                if (
                    not isinstance(body, dict) or set(body) != {"message", "allow_wiki"}
                    or not isinstance(body["message"], str) or not 1 <= len(body["message"].strip()) <= 2000
                    or type(body["allow_wiki"]) is not bool
                ):
                    raise ValueError
            except (ValueError, UnicodeError):
                self.reply(400, {"error": "invalid_chat_request"})
                return
            try:
                receipt = desktop.chat(body["message"].strip(), allow_wiki=body["allow_wiki"])
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
            result = json.loads(message)
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
    parser.add_argument("--demo", action="store_true", help="Use a local demonstration provider with no network.")
    args = parser.parse_args()
    definitions = [wiki_search.definition(wiki_search.load_export(args.wiki_export))] if args.wiki_export else []
    composer = PluginComposer(definitions=definitions, profiles={"desktop": [item.plugin_id for item in definitions]})
    composer.compose("desktop")
    desktop = Desktop(args.workspace, composer=composer, provider=_DemoProvider() if args.demo else None,
                      provider_mode="OFFLINE_DEMO" if args.demo else "UNCONFIGURED")
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
