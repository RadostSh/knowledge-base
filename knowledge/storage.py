"""SQLite persistence layer for the knowledge base."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from knowledge.models import KnowledgeItem, StorageError

ENV_DB_PATH = "KNOWLEDGE_DB_PATH"
REQUIRED_COLUMNS = frozenset({"id", "title", "content"})


def get_default_db_path() -> Path:
    """Return the database path from KNOWLEDGE_DB_PATH, or ~/.knowledge_base.db."""
    value = os.environ.get(ENV_DB_PATH, "").strip()
    if value:
        return Path(value).expanduser()
    return Path.home() / ".knowledge_base.db"


def _escape_like(query: str) -> str:
    """Escape LIKE wildcards so they are matched literally (used with ESCAPE '\\')."""
    return query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqliteStorage:
    """Stores knowledge items in a SQLite database, one connection per operation."""
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path).expanduser() if db_path is not None else get_default_db_path()
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(
                f"Cannot create the directory for the database at {self.db_path}: {exc}."
            ) from exc
        self._init_db()

    @contextmanager
    def _connect(self, action: str) -> Iterator[sqlite3.Connection]:
        """Open a connection for one transaction; always close it, wrap errors in StorageError."""
        try:
            with closing(sqlite3.connect(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                with conn:
                    yield conn
        except (sqlite3.Error, OSError) as exc:
            raise StorageError(
                f"Cannot {action} the database at {self.db_path}: {exc}. "
                "The file may be corrupted or not writable."
            ) from exc

    def _init_db(self) -> None:
        """Create the schema if needed and verify the file is a knowledge base database."""
        with self._connect("open") as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS items ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "title TEXT NOT NULL, "
                "content TEXT NOT NULL)"
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(items)")}
        if not REQUIRED_COLUMNS <= columns:
            raise StorageError(
                f"The file at {self.db_path} is not a valid knowledge base database "
                "(the 'items' table has an unexpected structure)."
            )

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> KnowledgeItem:
        """Convert a database row to a KnowledgeItem."""
        return KnowledgeItem(id=row["id"], title=row["title"], content=row["content"])

    def add(self, title: str, content: str) -> KnowledgeItem:
        """Insert a new item and return it with its assigned ID."""
        with self._connect("write to") as conn:
            cursor = conn.execute(
                "INSERT INTO items (title, content) VALUES (?, ?)", (title, content)
            )
            item_id = cursor.lastrowid
        if item_id is None:
            raise StorageError(f"Failed to retrieve ID for inserted item in {self.db_path}.")
        return KnowledgeItem(id=item_id, title=title, content=content)

    def list_all(self) -> list[KnowledgeItem]:
        """Return all items ordered by ID."""
        with self._connect("read from") as conn:
            rows = conn.execute("SELECT id, title, content FROM items ORDER BY id ASC").fetchall()
        return [self._row_to_item(row) for row in rows]

    def get_by_id(self, item_id: int) -> KnowledgeItem | None:
        """Return the item with the given ID, or None if it does not exist."""
        with self._connect("read from") as conn:
            row = conn.execute(
                "SELECT id, title, content FROM items WHERE id = ?", (item_id,)
            ).fetchone()
        return self._row_to_item(row) if row is not None else None

    def search(self, query: str) -> list[KnowledgeItem]:
        """Return items whose title or content contains the query, ordered by ID."""
        # Note: SQLite's LIKE is case-insensitive only for ASCII letters.
        pattern = f"%{_escape_like(query)}%"
        with self._connect("read from") as conn:
            rows = conn.execute(
                "SELECT id, title, content FROM items "
                "WHERE title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\' "
                "ORDER BY id ASC",
                (pattern, pattern),
            ).fetchall()
        return [self._row_to_item(row) for row in rows]

    def update(self, item_id: int, title: str, content: str) -> KnowledgeItem | None:
        """Replace an item's title and content; return None if the ID does not exist."""
        with self._connect("write to") as conn:
            cursor = conn.execute(
                "UPDATE items SET title = ?, content = ? WHERE id = ?", (title, content, item_id)
            )
            if cursor.rowcount == 0:
                return None
        return KnowledgeItem(id=item_id, title=title, content=content)

    def delete(self, item_id: int) -> bool:
        """Delete the item with the given ID; return True if a row was deleted."""
        with self._connect("write to") as conn:
            cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0
