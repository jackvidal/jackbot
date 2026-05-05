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
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_tokens (
              provider TEXT NOT NULL,
              user_id TEXT NOT NULL,
              access_token TEXT,
              refresh_token TEXT,
              token_expiry INTEGER,
              scopes TEXT,
              updated_at INTEGER NOT NULL,
              PRIMARY KEY (provider, user_id)
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


def save_oauth_tokens(
    provider: str,
    user_id: str,
    access_token: str | None,
    refresh_token: str | None,
    expiry: int | None,
    scopes: str | None,
):
    with _conn() as c:
        c.execute(
            """
            INSERT INTO oauth_tokens
              (provider, user_id, access_token, refresh_token, token_expiry, scopes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (provider, user_id) DO UPDATE SET
              access_token=excluded.access_token,
              refresh_token=COALESCE(excluded.refresh_token, oauth_tokens.refresh_token),
              token_expiry=excluded.token_expiry,
              scopes=excluded.scopes,
              updated_at=excluded.updated_at
            """,
            (provider, user_id, access_token, refresh_token, expiry, scopes, int(time.time())),
        )


def get_oauth_tokens(provider: str, user_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            """
            SELECT access_token, refresh_token, token_expiry, scopes
            FROM oauth_tokens WHERE provider=? AND user_id=?
            """,
            (provider, user_id),
        ).fetchone()
    if not row:
        return None
    return {
        "access_token": row[0],
        "refresh_token": row[1],
        "expiry": row[2],
        "scopes": row[3],
    }
