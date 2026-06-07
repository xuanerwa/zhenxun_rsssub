from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
import sqlite3
from threading import RLock

from nonebot import require

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

DB_FILE = store.get_plugin_data_file("rss.sqlite3")
_db_lock = RLock()
_initialized = False


def _connect() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS feeds (
            name TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feed_targets (
            feed_name TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (feed_name, target_type, target_id)
        );

        CREATE TABLE IF NOT EXISTS feed_entries (
            feed_name TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            data TEXT NOT NULL,
            entry_datetime TEXT,
            to_send INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (feed_name, entry_hash)
        );

        CREATE TABLE IF NOT EXISTS feed_state (
            feed_name TEXT NOT NULL,
            state_key TEXT NOT NULL,
            state_value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (feed_name, state_key)
        );

        CREATE TABLE IF NOT EXISTS delivery_log (
            feed_name TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            message_id TEXT,
            time TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (feed_name, entry_hash, target_type, target_id)
        );

        CREATE INDEX IF NOT EXISTS idx_feed_entries_feed_time
            ON feed_entries(feed_name, entry_datetime);
        CREATE INDEX IF NOT EXISTS idx_delivery_log_feed_entry_status
            ON delivery_log(feed_name, entry_hash, status);
        """
    )


def _ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    with _db_lock:
        if _initialized:
            return
        conn = _connect()
        try:
            _create_schema(conn)
            conn.commit()
            _initialized = True
        finally:
            conn.close()


@contextmanager
def db() -> Iterable[sqlite3.Connection]:
    _ensure_initialized()
    with _db_lock:
        conn = _connect()
        try:
            yield conn
        finally:
            conn.close()


@contextmanager
def transaction() -> Iterable[sqlite3.Connection]:
    with db() as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
