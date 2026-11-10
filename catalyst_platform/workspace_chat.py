"""Local chat history projected from the same artifacts as run observation."""

import json
import re
import uuid

from .context import Turn
from .llm_controls import input_token_envelope
from .workspace_context import CHAT_HISTORY_SERVICE


class WorkspaceChat:
    def __init__(self, app):
        self.app = app
        self.marker = app.state_root / "workspace-settings" / "chat-thread.json"
        self.results = app.state_root / "user-results"

    def thread(self):
        return self._index()["thread_id"]

    def _index(self):
        if not self.marker.exists():
            return {"thread_id": "initial", "threads": ["initial"]}
        value = json.loads(self.marker.read_text(encoding="utf-8"))
        value.setdefault("threads", list(dict.fromkeys([value["thread_id"], "initial"])))
        return value

    def new_thread(self):
        value = self._index()
        thread_id = uuid.uuid4().hex
        self.app._atomic_json(self.marker, {"thread_id": thread_id, "threads": [thread_id, *value["threads"]]})

    def threads(self):
        rows = {thread_id: {"id": thread_id, "title": "新对话"} for thread_id in self._index()["threads"]}
        for turn in self.recent():
            thread_id = turn["thread_id"]
            if thread_id not in rows or rows[thread_id]["title"] == "新对话":
                rows[thread_id] = {"id": thread_id, "title": turn["message"][:48]}
        return list(rows.values())

    def exists(self, thread_id):
        return isinstance(thread_id, str) and (
            thread_id == "initial" or bool(re.fullmatch(r"[0-9a-f]{32}", thread_id))
            and (thread_id in self._index()["threads"] or bool(self.recent(1, thread=thread_id)))
        )

    def recent(self, limit=100, *, thread=None, context_only=False):
        rows = []
        paths = sorted(self.results.glob("run_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
        for path in paths:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            chat = record.get("chat")
            if record.get("task_type") != "basic_chat" or not chat:
                continue
            if thread is not None and chat["thread_id"] != thread:
                continue
            if context_only and not (chat["daily"] and record["state"] == "CHAT_COMPLETED"):
                continue
            rows.append({
                "run_id": record["run_id"], "thread_id": chat["thread_id"],
                "message": chat["message"], "answer": record["result"]["output"].get("answer", ""),
                "mode": record["mode"], "state": record["state"],
                "provider": record.get("provider"), "model": record.get("model"),
                "external_calls": record["external_calls"],
                "context_run_ids": chat.get("context_run_ids", []),
            })
            if len(rows) >= limit:
                break
        return list(reversed(rows))

    def context(self, thread, budget):
        select = self.app.plugins.service(CHAT_HISTORY_SERVICE)
        if select is None or budget <= 0:
            return [], []
        turns = tuple(Turn(row["run_id"], row["message"], row["answer"])
                      for row in self.recent(thread=thread, context_only=True))
        messages, run_ids = select(turns, budget)
        if not set(run_ids) <= {turn.run_id for turn in turns}:
            raise ValueError("invalid_chat_context_sources")
        if messages and input_token_envelope(json.dumps(messages, ensure_ascii=False)) > budget:
            raise ValueError("chat_context_budget_exceeded")
        return messages, run_ids
