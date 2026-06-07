from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .globals import plugin_config
from .repository_db import db, transaction
from .repository_lock import get_feed_write_lock, locked_feeds
from .repository_utils import json_dumps, json_loads
from .utils import extract_entry_fields, get_entry_datetime


def _entry_datetime_text(entry: dict[str, Any]) -> str:
    try:
        return get_entry_datetime(entry).isoformat()
    except Exception:
        return ""


def _upsert_entry(conn, feed_name: str, entry: dict[str, Any]) -> None:
    entry = extract_entry_fields(entry)
    entry_hash = str(entry.get("hash") or "")
    if not entry_hash:
        return
    conn.execute(
        """
        INSERT INTO feed_entries(
            feed_name, entry_hash, data, entry_datetime, to_send, updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(feed_name, entry_hash) DO UPDATE SET
            data = excluded.data,
            entry_datetime = excluded.entry_datetime,
            to_send = excluded.to_send,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            feed_name,
            entry_hash,
            json_dumps(entry),
            _entry_datetime_text(entry),
            1 if entry.get("to_send") else 0,
        ),
    )


def entries_file_exists(name: str) -> bool:
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM feed_entries WHERE feed_name = ? LIMIT 1",
            (name,),
        ).fetchone()
    return row is not None


def rename_entries_file(old_name: str, new_name: str) -> None:
    with locked_feeds(old_name, new_name):
        with transaction() as conn:
            conn.execute(
                "UPDATE feed_entries SET feed_name = ? WHERE feed_name = ?",
                (new_name, old_name),
            )
            conn.execute(
                "UPDATE delivery_log SET feed_name = ? WHERE feed_name = ?",
                (new_name, old_name),
            )
            conn.execute(
                "UPDATE feed_state SET feed_name = ? WHERE feed_name = ?",
                (new_name, old_name),
            )


def delete_entries_file(name: str) -> None:
    with get_feed_write_lock(name):
        with transaction() as conn:
            conn.execute("DELETE FROM feed_entries WHERE feed_name = ?", (name,))
            conn.execute("DELETE FROM delivery_log WHERE feed_name = ?", (name,))


def load_entries(name: str) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT data FROM feed_entries
            WHERE feed_name = ?
            ORDER BY entry_datetime, rowid
            """,
            (name,),
        ).fetchall()
        return [json_loads(row["data"], {}) for row in rows]


async def initialize_entries(name: str, entries: Iterable[dict[str, Any]]) -> None:
    entries = list(entries)
    with get_feed_write_lock(name):
        with transaction() as conn:
            conn.execute("DELETE FROM feed_entries WHERE feed_name = ?", (name,))
            for entry in entries:
                _upsert_entry(conn, name, entry)


async def write_entry(name: str, entry: dict[str, Any]) -> None:
    with get_feed_write_lock(name):
        with transaction() as conn:
            _upsert_entry(conn, name, entry)


async def truncate_entries(name: str, num_new_entries: int) -> None:
    with get_feed_write_lock(name):
        with transaction() as conn:
            limit = plugin_config.rss_entries_file_limit + num_new_entries
            rows = conn.execute(
                """
                SELECT entry_hash FROM feed_entries
                WHERE feed_name = ?
                ORDER BY entry_datetime DESC, rowid DESC
                LIMIT -1 OFFSET ?
                """,
                (name, limit),
            ).fetchall()
            hashes = [row["entry_hash"] for row in rows]
            if not hashes:
                return
            conn.executemany(
                "DELETE FROM feed_entries WHERE feed_name = ? AND entry_hash = ?",
                [(name, entry_hash) for entry_hash in hashes],
            )
