"""DatabaseManager: the only place that knows SQL.

Methods are named after what the application wants to do (record a failed scan,
assign a card) and return plain dicts, so callers never see rows, cursors or queries.
"""
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, filename TEXT NOT NULL, stored TEXT NOT NULL,
    mime TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS mappings(
    uid TEXT PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    label TEXT NOT NULL DEFAULT '', updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS failed_scans(
    uid TEXT PRIMARY KEY, count INTEGER NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL);
"""

FILE_COLUMNS = ("id", "title", "filename", "stored", "mime", "size", "sha256", "updated")
FILE_WITH_USAGE = (
    "SELECT f.*, (SELECT COUNT(*) FROM mappings m WHERE m.file_id = f.id) AS uses FROM files f"
)


class DatabaseManager:
    def __init__(self, path: Path):
        self.path = path
        with self._transaction() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _transaction(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---- audio files ----------------------------------------------------

    def add_file(self, *, title, filename, stored, mime, size, sha256) -> dict:
        with self._transaction() as c:
            cur = c.execute(
                "INSERT INTO files(title, filename, stored, mime, size, sha256, updated) VALUES(?,?,?,?,?,?,?)",
                (title, filename, stored, mime, size, sha256, time.time()),
            )
            return self._file(c, cur.lastrowid)

    def get_file(self, file_id: int) -> dict | None:
        with self._transaction() as c:
            return self._file(c, file_id)

    def list_files(self) -> list[dict]:
        with self._transaction() as c:
            rows = c.execute(FILE_WITH_USAGE + " ORDER BY f.title COLLATE NOCASE")
            return [dict(r) for r in rows]

    def rename_file(self, file_id: int, title: str) -> dict | None:
        with self._transaction() as c:
            c.execute("UPDATE files SET title = ? WHERE id = ?", (title, file_id))
            return self._file(c, file_id)

    def update_file_content(self, file_id: int, *, filename, stored, mime, size, sha256) -> dict | None:
        with self._transaction() as c:
            c.execute(
                "UPDATE files SET filename=?, stored=?, mime=?, size=?, sha256=?, updated=? WHERE id=?",
                (filename, stored, mime, size, sha256, time.time(), file_id),
            )
            return self._file(c, file_id)

    def delete_file(self, file_id: int) -> None:
        """Deletes the file row; its card mappings go with it (ON DELETE CASCADE)."""
        with self._transaction() as c:
            c.execute("DELETE FROM files WHERE id = ?", (file_id,))

    # ---- card mappings --------------------------------------------------

    def find_mapping(self, uid: str) -> dict | None:
        """Returns {'uid', 'label', 'file': {...}} for a mapped card, else None."""
        with self._transaction() as c:
            row = c.execute(
                "SELECT m.uid, m.label, f.* FROM mappings m JOIN files f ON f.id = m.file_id WHERE m.uid = ?",
                (uid,),
            ).fetchone()
            if row is None:
                return None
            return {"uid": row["uid"], "label": row["label"], "file": {k: row[k] for k in FILE_COLUMNS}}

    def list_mappings(self) -> list[dict]:
        with self._transaction() as c:
            rows = c.execute(
                "SELECT m.uid, m.label, m.updated, m.file_id, f.title AS file_title "
                "FROM mappings m JOIN files f ON f.id = m.file_id ORDER BY m.updated DESC"
            )
            return [dict(r) for r in rows]

    def assign_card(self, uid: str, file_id: int, label: str) -> None:
        """Map a card to a file and clear it from the failed scans, atomically."""
        with self._transaction() as c:
            c.execute(
                "INSERT INTO mappings(uid, file_id, label, updated) VALUES(?,?,?,?) "
                "ON CONFLICT(uid) DO UPDATE SET file_id=excluded.file_id, label=excluded.label, "
                "updated=excluded.updated",
                (uid, file_id, label, time.time()),
            )
            c.execute("DELETE FROM failed_scans WHERE uid = ?", (uid,))

    def remove_mapping(self, uid: str) -> None:
        with self._transaction() as c:
            c.execute("DELETE FROM mappings WHERE uid = ?", (uid,))

    # ---- failed scans ---------------------------------------------------

    def record_failed_scan(self, uid: str) -> None:
        now = time.time()
        with self._transaction() as c:
            c.execute(
                "INSERT INTO failed_scans(uid, count, first_seen, last_seen) VALUES(?,1,?,?) "
                "ON CONFLICT(uid) DO UPDATE SET count = count + 1, last_seen = excluded.last_seen",
                (uid, now, now),
            )

    def list_failed_scans(self) -> list[dict]:
        with self._transaction() as c:
            return [dict(r) for r in c.execute("SELECT * FROM failed_scans ORDER BY last_seen DESC")]

    def dismiss_failed_scan(self, uid: str) -> None:
        with self._transaction() as c:
            c.execute("DELETE FROM failed_scans WHERE uid = ?", (uid,))

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _file(c, file_id: int) -> dict | None:
        row = c.execute(FILE_WITH_USAGE + " WHERE f.id = ?", (file_id,)).fetchone()
        return dict(row) if row else None
