import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR_DEFAULT = Path("./data")
DB_NAME = "studyspace.db"


def _get_db_path(data_dir: str | None = None) -> Path:
    """Return the absolute path to the SQLite database file."""
    if data_dir is None:
        data_dir = os.environ.get("STUDYSPACE_DATA_DIR", str(DATA_DIR_DEFAULT))
    p = Path(data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / DB_NAME


def _ensure_conn(conn: sqlite3.Connection) -> None:
    """Apply safety pragmas on a new connection."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")


def _create_tables(conn: sqlite3.Connection) -> None:
    """Create database tables if they don't exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            page_count INTEGER NOT NULL DEFAULT 0,
            is_scanned INTEGER NOT NULL DEFAULT 0,
            encrypted INTEGER NOT NULL DEFAULT 0,
            last_read_page INTEGER NOT NULL DEFAULT 0,
            preferences TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_doc_deleted ON documents(deleted_at);
        CREATE INDEX IF NOT EXISTS idx_doc_title ON documents(title);

        CREATE TABLE IF NOT EXISTS progress (
            document_id TEXT NOT NULL,
            page_num INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (document_id, page_num),
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_progress_doc ON progress(document_id);
        """
    )
    conn.commit()


class DocumentStore:
    """Document metadata store using SQLite.

    Each operation opens a new connection (check_same_thread=False)
    so the FastAPI test client and async workers can all use it safely.
    """

    def __init__(self, data_dir: str | None = None):
        self.db_path = _get_db_path(data_dir)
        # Ensure parent directory exists and tables are created
        os.makedirs(self.db_path.parent, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            _ensure_conn(conn)
            _create_tables(conn)

    def _connect(self) -> sqlite3.Connection:
        """Open a new connection per operation (safe across threads)."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        _ensure_conn(conn)
        return conn

    # ---- Document CRUD ----

    def insert_document(
        self,
        doc_id: str,
        title: str,
        filename: str,
        file_path: str,
        page_count: int,
        is_scanned: bool,
        encrypted: bool,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        conn.execute(
            """
            INSERT INTO documents (id, title, filename, file_path, page_count, is_scanned, encrypted, last_read_page, preferences, created_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, '{}', ?, NULL)
            """,
            (
                doc_id,
                title,
                filename,
                file_path,
                page_count,
                1 if is_scanned else 0,
                1 if encrypted else 0,
                now,
            ),
        )
        conn.commit()
        conn.close()

    def get_document(self, doc_id: str) -> dict | None:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND deleted_at IS NULL", (doc_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "filename": row["filename"],
            "file_path": row["file_path"],
            "page_count": row["page_count"],
            "is_scanned": bool(row["is_scanned"]),
            "encrypted": bool(row["encrypted"]),
            "last_read_page": row["last_read_page"],
            "preferences": row["preferences"],
            "created_at": row["created_at"],
        }

    def list_documents(self, include_deleted: bool = False) -> list[dict]:
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        if include_deleted:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents WHERE deleted_at IS NULL ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "filename": r["filename"],
                "page_count": r["page_count"],
                "is_scanned": bool(r["is_scanned"]),
                "last_read_page": r["last_read_page"],
            }
            for r in rows
        ]

    def soft_delete(self, doc_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        conn.execute(
            "UPDATE documents SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now, doc_id),
        )
        conn.commit()
        conn.close()

    def restore(self, doc_id: str) -> None:
        conn = self._connect()
        conn.execute(
            "UPDATE documents SET deleted_at = NULL WHERE id = ? AND deleted_at IS NOT NULL",
            (doc_id,),
        )
        conn.commit()
        conn.close()

    def permanent_delete(self, doc_id: str) -> None:
        conn = self._connect()
        # Delete the original file if it exists on disk (check both active and soft-deleted)
        row = conn.execute(
            "SELECT file_path FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row:
            file_path = row[0]  # Tuple index, not dict key
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except OSError:
                pass
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()

    # ---- Progress ----

    def set_progress(self, doc_id: str, page_num: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        # Try insert; if document_id already exists, update instead
        try:
            conn.execute(
                """
                INSERT INTO progress (document_id, page_num, updated_at)
                VALUES (?, ?, ?)
                """,
                (doc_id, page_num, now),
            )
        except sqlite3.IntegrityError:
            conn.execute(
                """
                UPDATE progress SET page_num = ?, updated_at = ?
                WHERE document_id = ?
                """,
                (page_num, now, doc_id),
            )
        # Also update last_read_page in documents table
        conn.execute(
            "UPDATE documents SET last_read_page = ? WHERE id = ?",
            (page_num, doc_id),
        )
        conn.commit()
        conn.close()

    def get_progress(self, doc_id: str) -> int:
        conn = self._connect()
        row = conn.execute(
            "SELECT page_num FROM progress WHERE document_id = ? ORDER BY updated_at DESC LIMIT 1",
            (doc_id,),
        ).fetchone()
        conn.close()
        return row[0] if row else 0

    def close(self) -> None:
        # No persistent connection to close
        pass