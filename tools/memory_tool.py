"""MemoryTool – cross-session persistent key-value memory.

Mirrors Anthropic's ``memory_20250818`` client tool but works with **any LLM**.
Memories are stored in a SQLite database so they survive across conversations.

Operations:

* ``remember``  – store or update a memory entry
* ``recall``    – retrieve memories matching a query
* ``forget``    – delete a specific memory
* ``list_memories`` – list all stored memories

Usage::

    from buddy.tools.memory_tool import MemoryTool

    agent = Agent(model=..., tools=[MemoryTool(db_path="memory.db")])
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from buddy.tools.toolkit import Toolkit

logger = logging.getLogger(__name__)

ANTHROPIC_TOOL_TYPE = "memory_20250818"

_DEFAULT_DB = Path.home() / ".buddy" / "memory.db"


class MemoryTool(Toolkit):
    """Persist and retrieve facts across conversations using a local SQLite store.

    Equivalent to Anthropic's ``memory_20250818`` client tool, with a
    file-based SQLite backend that works on any platform and with any LLM.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Defaults to ``~/.buddy/memory.db``.
    namespace:
        Optional namespace to isolate memories per agent or user.
    max_memories:
        Soft cap on the total number of memories stored.  Oldest excess entries
        are pruned automatically when the limit is reached.
    """

    ANTHROPIC_TOOL_TYPE = ANTHROPIC_TOOL_TYPE

    def __init__(
        self,
        db_path: Optional[str] = None,
        namespace: str = "default",
        max_memories: int = 1000,
        **kwargs: Any,
    ):
        self._db_path = Path(db_path or _DEFAULT_DB)
        self._namespace = namespace
        self._max_memories = max_memories
        self._lock = threading.Lock()
        self._init_db()

        super().__init__(
            name="memory",
            tools=[self.remember, self.recall, self.forget, self.list_memories],
            instructions=(
                "Use the memory tools to persist important information across conversations. "
                "Call remember() to store key facts, recall() to look up stored information, "
                "and forget() to remove outdated entries. "
                "Always retrieve relevant memories at the start of a conversation."
            ),
            **kwargs,
        )

    # ── DB setup ─────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace   TEXT    NOT NULL,
                    key         TEXT    NOT NULL,
                    value       TEXT    NOT NULL,
                    tags        TEXT    DEFAULT '',
                    created_at  TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL,
                    UNIQUE(namespace, key)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ns_key ON memories(namespace, key)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), check_same_thread=False)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── tool methods ─────────────────────────────────────────────────────────

    def remember(self, key: str, value: str, tags: Optional[str] = None) -> str:
        """Store or update a memory entry.

        Saves a piece of information under a descriptive key. If a memory with
        the same key already exists it is updated. Good for storing user
        preferences, important facts, task progress, and decisions made.

        Args:
            key: A short, descriptive label for the memory (e.g. "user_name").
            value: The information to remember (can be a full sentence or JSON).
            tags: Optional comma-separated tags for categorisation (e.g. "preference,user").

        Returns:
            str: Confirmation message.
        """
        now = self._now()
        tags_str = tags or ""
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (namespace, key, value, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET
                    value=excluded.value,
                    tags=excluded.tags,
                    updated_at=excluded.updated_at
                """,
                (self._namespace, key, value, tags_str, now, now),
            )
            self._prune(conn)
        return f"Memory '{key}' stored."

    def recall(self, query: str, limit: int = 10) -> str:
        """Retrieve memories matching a search query.

        Searches memory keys, values, and tags for the query terms. Returns
        the most recently updated matching memories. Call this at the start
        of a conversation to load relevant context.

        Args:
            query: Keywords to search for across memory keys, values, and tags.
            limit: Maximum number of results to return.

        Returns:
            str: JSON list of matching memories with key, value, tags, and updated_at.
        """
        terms = query.lower().split()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value, tags, updated_at FROM memories WHERE namespace=? ORDER BY updated_at DESC",
                (self._namespace,),
            ).fetchall()

        results = []
        for key, value, tags, updated_at in rows:
            text = f"{key} {value} {tags}".lower()
            if any(t in text for t in terms):
                results.append({"key": key, "value": value, "tags": tags, "updated_at": updated_at})
            if len(results) >= limit:
                break

        if not results:
            return json.dumps({"message": "No matching memories found.", "results": []})
        return json.dumps({"results": results})

    def forget(self, key: str) -> str:
        """Delete a specific memory by its key.

        Permanently removes the memory entry. Use this to clean up outdated
        or incorrect information.

        Args:
            key: The exact key of the memory to delete.

        Returns:
            str: Confirmation or error message.
        """
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE namespace=? AND key=?",
                (self._namespace, key),
            )
            deleted = cursor.rowcount
        if deleted:
            return f"Memory '{key}' deleted."
        return json.dumps({"error": f"No memory found with key '{key}'."})

    def list_memories(self, tag_filter: Optional[str] = None, limit: int = 50) -> str:
        """List all stored memories, optionally filtered by tag.

        Returns a summary of all memories in the current namespace. Use
        ``tag_filter`` to narrow results to a specific category.

        Args:
            tag_filter: Optional tag to filter by (e.g. "preference").
            limit: Maximum number of entries to return.

        Returns:
            str: JSON list of all memories.
        """
        with self._connect() as conn:
            if tag_filter:
                rows = conn.execute(
                    "SELECT key, value, tags, updated_at FROM memories "
                    "WHERE namespace=? AND tags LIKE ? ORDER BY updated_at DESC LIMIT ?",
                    (self._namespace, f"%{tag_filter}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT key, value, tags, updated_at FROM memories "
                    "WHERE namespace=? ORDER BY updated_at DESC LIMIT ?",
                    (self._namespace, limit),
                ).fetchall()

        entries: List[dict] = [
            {"key": r[0], "value": r[1], "tags": r[2], "updated_at": r[3]} for r in rows
        ]
        return json.dumps({"total": len(entries), "memories": entries})

    def _prune(self, conn: sqlite3.Connection) -> None:
        """Remove the oldest entries when the memory store exceeds max_memories."""
        count = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE namespace=?", (self._namespace,)
        ).fetchone()[0]
        excess = count - self._max_memories
        if excess > 0:
            conn.execute(
                """
                DELETE FROM memories WHERE id IN (
                    SELECT id FROM memories WHERE namespace=? ORDER BY updated_at ASC LIMIT ?
                )
                """,
                (self._namespace, excess),
            )

    def to_anthropic_client_tool(self) -> dict:
        """Return the Anthropic API client-tool declaration."""
        return {"type": self.ANTHROPIC_TOOL_TYPE}
