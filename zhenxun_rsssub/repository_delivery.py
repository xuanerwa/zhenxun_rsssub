from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .repository_db import db, transaction
from .repository_lock import get_feed_write_lock


def _upsert_delivery_record(conn, record: dict[str, Any]) -> None:
    feed_name = str(record.get("feed_name") or "")
    entry_hash = str(record.get("entry_hash") or "")
    target_type = str(record.get("target_type") or "")
    target_id = str(record.get("target_id") or "")
    status = str(record.get("status") or "")
    if (
        not feed_name
        or not entry_hash
        or not target_type
        or not target_id
        or not status
    ):
        return
    conn.execute(
        """
        INSERT INTO delivery_log(
            feed_name, entry_hash, target_type, target_id,
            status, error, message_id, time, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(feed_name, entry_hash, target_type, target_id) DO UPDATE SET
            status = excluded.status,
            error = excluded.error,
            message_id = excluded.message_id,
            time = excluded.time,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            feed_name,
            entry_hash,
            target_type,
            target_id,
            status,
            record.get("error"),
            record.get("message_id"),
            record.get("time"),
        ),
    )


async def upsert_delivery_log(record: dict[str, Any]) -> None:
    await upsert_delivery_logs([record])


async def upsert_delivery_logs(records: Iterable[dict[str, Any]]) -> None:
    records = list(records)
    if not records:
        return
    with get_feed_write_lock("__delivery_log__"):
        with transaction() as conn:
            for record in records:
                _upsert_delivery_record(conn, record)


def load_delivery_logs(
    feed_name: str, entry_hash: str | None = None
) -> list[dict[str, Any]]:
    with db() as conn:
        if entry_hash:
            rows = conn.execute(
                """
                SELECT * FROM delivery_log
                WHERE feed_name = ? AND entry_hash = ?
                ORDER BY updated_at DESC
                """,
                (feed_name, entry_hash),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM delivery_log
                WHERE feed_name = ?
                ORDER BY updated_at DESC
                """,
                (feed_name,),
            ).fetchall()
    return [
        {
            "feed_name": row["feed_name"],
            "entry_hash": row["entry_hash"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "status": row["status"],
            "error": row["error"],
            "message_id": row["message_id"],
            "time": row["time"],
        }
        for row in rows
    ]


def delivered_target_keys(feed_name: str, entry_hash: str) -> set[tuple[str, str]]:
    result = set()
    for record in load_delivery_logs(feed_name, entry_hash):
        if record.get("status") != "success":
            continue
        target_type = str(record.get("target_type") or "")
        target_id = str(record.get("target_id") or "")
        if target_type and target_id:
            result.add((target_type, target_id))
    return result


def delete_delivery_logs(feed_name: str) -> None:
    with get_feed_write_lock("__delivery_log__"):
        with transaction() as conn:
            conn.execute("DELETE FROM delivery_log WHERE feed_name = ?", (feed_name,))
