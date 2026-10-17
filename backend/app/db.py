"""SQLite = the authoritative source of truth for users, roles, ACLs, versions, cache dependencies, audit."""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
  password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
  authz_version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS user_roles(
  user_id TEXT NOT NULL, role TEXT NOT NULL, PRIMARY KEY(user_id, role));
-- administrative capabilities are separate from document-read permissions
CREATE TABLE IF NOT EXISTS role_capabilities(
  role TEXT NOT NULL, capability TEXT NOT NULL, PRIMARY KEY(role, capability));
CREATE TABLE IF NOT EXISTS documents(
  id TEXT PRIMARY KEY, title TEXT NOT NULL, sensitivity TEXT NOT NULL, filename TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1, acl_version INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active',      -- active | removed
  injection_flagged INTEGER NOT NULL DEFAULT 0, pii_count INTEGER NOT NULL DEFAULT 0,
  created_by TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS document_versions(
  doc_id TEXT NOT NULL, version INTEGER NOT NULL, content_sha256 TEXT NOT NULL,
  filename TEXT NOT NULL, chunk_count INTEGER NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY(doc_id, version));
-- explicit ACL: a role listed here may read the document; nothing is implied (no admin bypass)
CREATE TABLE IF NOT EXISTS document_acl(
  doc_id TEXT NOT NULL, role TEXT NOT NULL, PRIMARY KEY(doc_id, role));
-- explicit per-user deny overrides role grants ("subject to explicit restrictions")
CREATE TABLE IF NOT EXISTS document_user_deny(
  doc_id TEXT NOT NULL, user_id TEXT NOT NULL, PRIMARY KEY(doc_id, user_id));
CREATE TABLE IF NOT EXISTS chunks(
  id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, doc_version INTEGER NOT NULL, idx INTEGER NOT NULL,
  text TEXT NOT NULL, vector TEXT NOT NULL, injection_score REAL NOT NULL DEFAULT 0,
  quarantined INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON chunks(doc_id);
CREATE TABLE IF NOT EXISTS answer_cache(
  key TEXT PRIMARY KEY, user_id TEXT NOT NULL, question_hash TEXT NOT NULL,
  user_authz_version INTEGER NOT NULL, answer_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cache_deps(
  cache_key TEXT NOT NULL, doc_id TEXT NOT NULL, doc_version INTEGER NOT NULL,
  acl_version INTEGER NOT NULL, chunk_ids TEXT NOT NULL, PRIMARY KEY(cache_key, doc_id));
CREATE INDEX IF NOT EXISTS ix_deps_doc ON cache_deps(doc_id);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, event_type TEXT NOT NULL,
  request_id TEXT, user_id TEXT, outcome TEXT, detail TEXT NOT NULL,
  prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
"""

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None
_path: str | None = None


def init_db(path: str) -> None:
    global _conn, _path
    with _lock:
        if _conn is not None:
            _conn.close()
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys=ON")
        _conn.executescript(SCHEMA)
        _path = path


def conn() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("database not initialised")
    return _conn


@contextmanager
def tx():
    """Serialised write transaction (process-wide lock + BEGIN IMMEDIATE)."""
    with _lock:
        c = conn()
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise


def q(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    with _lock:
        return conn().execute(sql, params).fetchall()


def q1(sql: str, params: tuple = ()):
    rows = q(sql, params)
    return rows[0] if rows else None
