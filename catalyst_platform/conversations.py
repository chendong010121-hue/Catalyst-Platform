"""Workspace conversation order and run identities, independent of model context."""

import sqlite3
import uuid
from contextlib import closing


class Conversations:
    def __init__(self, state_root):
        state_root.mkdir(parents=True, exist_ok=True)
        self.path = state_root / "desktop-conversations.sqlite"
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversation (
                    ordinal INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS turn (
                    ordinal INTEGER PRIMARY KEY,
                    run_id TEXT NOT NULL UNIQUE,
                    conversation_id TEXT NOT NULL REFERENCES conversation(id),
                    message TEXT NOT NULL,
                    allow_wiki INTEGER NOT NULL,
                    allow_note INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS turn_conversation ON turn(conversation_id, ordinal);
            """)
            if not any(row[1] == "allow_note" for row in db.execute("PRAGMA table_info(turn)")):
                db.execute("ALTER TABLE turn ADD COLUMN allow_note INTEGER NOT NULL DEFAULT 0")

    def connect(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def create(self):
        conversation_id = uuid.uuid4().hex
        with closing(self.connect()) as db, db:
            db.execute("INSERT INTO conversation(id) VALUES (?)", (conversation_id,))
        return conversation_id

    def list(self):
        with closing(self.connect()) as db:
            return [
                {"id": conversation_id, "title": (message or "新对话")[:60]}
                for conversation_id, message in db.execute("""
                    SELECT id, (SELECT message FROM turn WHERE conversation_id = conversation.id
                                ORDER BY ordinal LIMIT 1)
                    FROM conversation ORDER BY ordinal DESC
                """)
            ]

    @staticmethod
    def _require(db, conversation_id):
        if db.execute("SELECT 1 FROM conversation WHERE id = ?", (conversation_id,)).fetchone() is None:
            raise KeyError(conversation_id)

    def turns(self, conversation_id, *, before=None):
        with closing(self.connect()) as db:
            self._require(db, conversation_id)
            return db.execute("""
                SELECT run_id, message FROM turn
                WHERE conversation_id = ? AND (? IS NULL OR ordinal < (
                    SELECT ordinal FROM turn WHERE run_id = ?
                ))
                ORDER BY ordinal
            """, (conversation_id, before, before)).fetchall()

    def reserve(self, conversation_id, run_id, message, allow_wiki, allow_note=False):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._require(db, conversation_id)
            values = (conversation_id, message, allow_wiki, allow_note)
            row = db.execute(
                "SELECT conversation_id, message, allow_wiki, allow_note FROM turn WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is not None:
                if row != values:
                    raise ValueError("request_identity_conflict")
                return False
            db.execute(
                "INSERT INTO turn(run_id, conversation_id, message, allow_wiki, allow_note) VALUES (?, ?, ?, ?, ?)",
                (run_id, *values),
            )
            return True
