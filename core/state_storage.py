# core/state_storage.py

import sqlite3
from pathlib import Path
from typing import TypedDict

DB_PATH = Path("db/state.sqlite3")


class PendingPost(TypedDict):
    """Structure of a post waiting for approval."""

    message_id: int
    text: str
    source_url: str
    created_at: str


class StateStorage:
    """
    SQLite storage for managing pending posts (Human-in-the-Loop).
    """

    def __init__(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(DB_PATH)

    def _init_db(self) -> None:
        """Create table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_posts (
                    message_id INTEGER PRIMARY KEY,
                    text TEXT NOT NULL,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def save_pending_post(self, message_id: int, text: str, source_url: str) -> None:
        """Save a generated post to verify later when button is clicked."""
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pending_posts (message_id, text, source_url) VALUES (?, ?, ?)",
                (message_id, text, source_url),
            )

    def get_pending_post(self, message_id: int) -> PendingPost | None:
        """Retrieve post data by message ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT message_id, text, source_url, created_at FROM pending_posts WHERE message_id = ?",
                (message_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "message_id": row[0],
                    "text": row[1],
                    "source_url": row[2],
                    "created_at": row[3],
                }
            return None

    def delete_pending_post(self, message_id: int) -> None:
        """Remove post from storage after approval or rejection."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM pending_posts WHERE message_id = ?", (message_id,))
