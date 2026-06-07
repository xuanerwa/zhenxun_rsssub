from __future__ import annotations

from typing import Any

from .repository_db import db, transaction
from .repository_lock import get_feed_write_lock, locked_feeds
from .repository_utils import json_dumps, json_loads


def _upsert_feed_targets(conn, name: str, data: dict[str, Any]) -> None:
    conn.execute("DELETE FROM feed_targets WHERE feed_name = ?", (name,))
    for uid in data.get("user_id") or []:
        conn.execute(
            """
            INSERT OR REPLACE INTO feed_targets(feed_name, target_type, target_id)
            VALUES (?, 'private', ?)
            """,
            (name, str(uid)),
        )
    for gid in data.get("group_id") or []:
        conn.execute(
            """
            INSERT OR REPLACE INTO feed_targets(feed_name, target_type, target_id)
            VALUES (?, 'group', ?)
            """,
            (name, str(gid)),
        )


def _upsert_feed_record(conn, name: str, data: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO feeds(name, data, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(name) DO UPDATE SET
            data = excluded.data,
            updated_at = CURRENT_TIMESTAMP
        """,
        (name, json_dumps(data)),
    )
    _upsert_feed_targets(conn, name, data)


def load_feed_records() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT data FROM feeds ORDER BY name").fetchall()
        return [json_loads(row["data"], {}) for row in rows]


def upsert_feed_state(name: str, data: dict[str, Any]) -> None:
    with get_feed_write_lock(name):
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO feeds(name, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (name, json_dumps(data)),
            )


def rename_feed_record(old_name: str, new_name: str, data: dict[str, Any]) -> None:
    with get_feed_write_lock("__feeds__"):
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
                conn.execute("DELETE FROM feeds WHERE name = ?", (old_name,))
                _upsert_feed_record(conn, new_name, data)


def upsert_feed_record(name: str, data: dict[str, Any], old_name: str | None = None):
    with get_feed_write_lock("__feeds__"):
        with locked_feeds(name, old_name or ""):
            with transaction() as conn:
                if old_name and old_name != name:
                    conn.execute(
                        "UPDATE feed_entries SET feed_name = ? WHERE feed_name = ?",
                        (name, old_name),
                    )
                    conn.execute(
                        "UPDATE delivery_log SET feed_name = ? WHERE feed_name = ?",
                        (name, old_name),
                    )
                    conn.execute(
                        "UPDATE feed_state SET feed_name = ? WHERE feed_name = ?",
                        (name, old_name),
                    )
                    conn.execute("DELETE FROM feeds WHERE name = ?", (old_name,))
                _upsert_feed_record(conn, name, data)


def remove_feed_record(name: str) -> None:
    with get_feed_write_lock("__feeds__"):
        with get_feed_write_lock(name):
            with transaction() as conn:
                conn.execute("DELETE FROM feeds WHERE name = ?", (name,))
                conn.execute("DELETE FROM feed_entries WHERE feed_name = ?", (name,))
                conn.execute("DELETE FROM delivery_log WHERE feed_name = ?", (name,))
                conn.execute("DELETE FROM feed_state WHERE feed_name = ?", (name,))
