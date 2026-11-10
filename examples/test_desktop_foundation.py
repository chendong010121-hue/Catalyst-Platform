"""Offline HTTP acceptance for the mainline desktop and optional Wiki adapter."""

import json
import tempfile
import threading
import unittest
import uuid
from dataclasses import replace
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agent_runtime.providers.deepseek import DeepSeekModelProvider
from catalyst_platform.desktop import Desktop, create_server
from catalyst_platform.plugin_composition import PluginComposer
from catalyst_platform.wiki_search import definition, load_export


class DesktopFoundationTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.requests = []
        self.searches = []
        self.force_wiki = False
        source = self.root / "export.json"
        source.write_text(json.dumps([{
            "title": "North Wing", "excerpt": "The North Wing is closed on Friday.",
            "source": "operations.md:12",
        }]), encoding="utf-8")
        real = definition(load_export(source))

        def alternate(query):
            self.searches.append(query)
            return {"status": "FOUND", "matches": [{"source": "alternate.md:4"}]}

        test_adapter = replace(definition(alternate), plugin_id="test-wiki")
        self.composer = PluginComposer(
            definitions=[real, test_adapter],
            profiles={"enabled": [real.plugin_id], "replacement": [test_adapter.plugin_id]},
        )
        self.addCleanup(self.composer.close)
        provider = DeepSeekModelProvider(api_key="unused-offline", transport=self.transport)
        self.desktop = Desktop(
            self.root, composer=self.composer, provider=provider, provider_mode="SCRIPTED_TRANSPORT"
        )
        server = create_server(self.desktop)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)
        self.base = f"http://127.0.0.1:{server.server_port}"
        self.csrf = self.get("/api/status")["csrf_token"]

    def transport(self, url, headers, body):
        request = json.loads(body)
        self.requests.append(request)
        message = request["messages"][-1]
        if message["role"] == "user" and (request.get("tools") or self.force_wiki):
            reply = {
                "role": "assistant", "content": None,
                "tool_calls": [{
                    "id": "wiki-1", "type": "function",
                    "function": {"name": "wiki_search", "arguments": '{"query":"North Wing"}'},
                }],
            }
            finish = "tool_calls"
        else:
            reply = {"role": "assistant", "content": "Scripted model reply"}
            finish = "stop"
        return 200, {
            "choices": [{"message": reply, "finish_reason": finish}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
        }

    def get(self, path):
        with urlopen(self.base + path, timeout=5) as response:
            return json.load(response)

    def ask(self, allow_wiki=False, *, csrf=None, origin=None):
        return self.post("/api/chat", {"message": "North Wing", "allow_wiki": allow_wiki},
                         csrf=csrf, origin=origin)

    def post(self, path, data, *, csrf=None, origin=None):
        headers = {
            "Content-Type": "application/json",
            "X-Catalyst-CSRF": self.csrf if csrf is None else csrf,
        }
        if origin:
            headers["Origin"] = origin
        request = Request(self.base + path, headers=headers, data=json.dumps(data).encode())
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    def test_base_chat_and_mount_authorize_unload_and_replace(self):
        with urlopen(self.base, timeout=5) as response:
            self.assertIn(b"/desktop.js", response.read())
        self.assertEqual(self.get("/api/status")["available_tools"], [])
        plain = self.ask()
        self.assertEqual(plain["state"], "COMPLETED")
        self.assertEqual(plain["visible_tools"], [])
        self.assertEqual(len(plain["recorded_model_calls"]), 1)
        self.assertEqual(self.get("/api/runs/" + plain["run_id"]), plain)

        self.composer.compose("enabled")
        self.assertEqual(self.get("/api/status")["available_tools"], ["wiki_search"])
        self.assertNotIn("tools", self.requests[-1])
        self.assertEqual(self.ask()["visible_tools"], [])
        self.assertNotIn("tools", self.requests[-1])

        first = self.ask(True)
        self.assertEqual(first["state"], "COMPLETED")
        self.assertEqual(len(first["recorded_model_calls"]), 2)
        self.assertEqual(first["tool_calls"][0]["result"]["data"]["matches"][0]["source"], "operations.md:12")
        self.assertEqual(self.requests[-1]["messages"][-1]["role"], "tool")
        self.composer.unload("evo-wiki-search")
        self.assertEqual(self.ask()["state"], "COMPLETED")
        count = len(self.requests)
        with self.assertRaises(HTTPError) as error:
            self.ask(True)
        self.assertEqual(error.exception.code, 409)
        self.assertEqual(len(self.requests), count)
        self.assertEqual(self.get("/api/runs/" + first["run_id"]), first)

        self.composer.compose("replacement")
        second = self.ask(True)
        self.assertEqual(second["state"], "COMPLETED")
        self.assertEqual(self.searches, ["North Wing"])
        self.assertEqual(second["tool_calls"][0]["result"]["data"]["matches"][0]["source"], "alternate.md:4")
        self.composer.unload("test-wiki")
        self.composer.compose("enabled")
        self.assertEqual(self.ask(True)["tool_calls"][0]["result"]["data"], first["tool_calls"][0]["result"]["data"])

    def test_model_cannot_call_mounted_wiki_without_turn_grant(self):
        self.composer.compose("replacement")
        self.force_wiki = True
        result = self.ask()
        self.assertNotEqual(result["state"], "COMPLETED")
        self.assertEqual(self.searches, [])
        self.assertNotIn("tools", self.requests[0])

    def test_local_post_and_model_gates(self):
        for kwargs in ({"csrf": "incorrect"}, {"origin": "https://example.org"}):
            with self.assertRaises(HTTPError) as error:
                self.ask(**kwargs)
            self.assertEqual(error.exception.code, 403)
        self.desktop.provider = None
        with self.assertRaises(HTTPError) as error:
            self.ask()
        self.assertEqual(error.exception.code, 409)
        self.assertEqual(self.requests, [])

    def test_conversations_project_ordered_context_and_replay_receipts(self):
        first = self.post("/api/conversations", {})["id"]
        second = self.post("/api/conversations", {})["id"]

        def turn(conversation_id, message):
            return {"conversation_id": conversation_id, "request_id": uuid.uuid4().hex,
                    "message": message, "allow_wiki": False}

        a = turn(first, "青桐项目")
        result = self.post("/api/chat", a)
        self.assertEqual(result["context_run_ids"], [])
        self.assertEqual(self.post("/api/chat", a), result)
        self.assertEqual(len(self.requests), 1)
        with self.assertRaises(HTTPError) as error:
            self.post("/api/chat", {**a, "conversation_id": second})
        self.assertEqual(error.exception.code, 409)
        self.assertEqual(len(self.requests), 1)

        b = self.post("/api/chat", turn(second, "海岸项目"))
        self.assertEqual(b["context_run_ids"], [])
        c = self.post("/api/chat", turn(first, "接着说"))
        self.assertEqual(c["context_run_ids"], [a["request_id"]])
        self.assertEqual([(m["role"], m["content"]) for m in self.requests[-1]["messages"][1:]], [
            ("user", "青桐项目"), ("assistant", "Scripted model reply"), ("user", "接着说"),
        ])
        self.assertEqual([row["id"] for row in self.get("/api/conversations")["items"]], [second, first])
        self.assertEqual([row["run_id"] for row in self.get("/api/conversations/" + first)["turns"]],
                         [a["request_id"], c["run_id"]])

    def test_missing_receipt_is_visible_and_same_request_is_not_replayed(self):
        conversation = self.post("/api/conversations", {})["id"]
        run_id = uuid.uuid4().hex
        self.desktop.conversations.reserve(conversation, run_id, "中断的请求", False)
        recovered = Desktop(self.root, composer=self.composer, provider=self.desktop.provider,
                            provider_mode=self.desktop.provider_mode)
        self.assertEqual(recovered.conversation(conversation)["turns"][0]["state"], "UNRESOLVED")
        with self.assertRaises(HTTPError) as error:
            self.post("/api/chat", {"conversation_id": conversation, "request_id": run_id,
                                    "message": "中断的请求", "allow_wiki": False})
        self.assertEqual(error.exception.code, 409)
        self.assertEqual(json.load(error.exception)["error"], "request_unresolved")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
