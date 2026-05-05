import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "./bot.db"))


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              chat_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at INTEGER NOT NULL
            )
            """
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_conv_chat ON conversations(chat_id, id)")
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_messages (
              msg_id TEXT PRIMARY KEY,
              created_at INTEGER NOT NULL
            )
            """
        )


def seen_message(msg_id: str) -> bool:
    with _conn() as c:
        try:
            c.execute(
                "INSERT INTO seen_messages (msg_id, created_at) VALUES (?, ?)",
                (msg_id, int(time.time())),
            )
            return False
        except sqlite3.IntegrityError:
            return True


def append(chat_id: str, role: str, content: str):
    with _conn() as c:
        c.execute(
            "INSERT INTO conversations (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, int(time.time())),
        )


def tail(chat_id: str, n: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM conversations WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, n),
        ).fetchall()
    return [{"role": r, "content": ct} for r, ct in reversed(rows)]
