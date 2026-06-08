from sqlite3 import Connection
from typing import Any, Literal

from ..globals import plugin_config


def initialize_cache_db(conn: Connection) -> None:
    # 用来去重的 sqlite3 数据表如果不存在就创建一个
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS main (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" TEXT,
    "link" TEXT,
    "datetime" TEXT DEFAULT (DATETIME('Now', 'LocalTime'))
);"""
    )
    cursor.close()
    conn.commit()
    # 移除超过 plugin_config.cache_expire 天没重复过的记录
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM main WHERE datetime <= DATETIME('Now', 'LocalTime', ?);",
        (f"-{plugin_config.cache_expire} Day",),
    )
    cursor.close()
    conn.commit()


async def is_entry_duplicated(
    conn: Connection,
    entry: dict[str, Any],
    deduplication_modes: set[Literal["title", "link", "or"]],
    *,
    dry_run: bool = False,
) -> bool:
    cursor = conn.cursor()
    title = entry["title"]
    link = entry["link"]

    try:
        sql_conditions = []
        sql_args = []

        for mode in deduplication_modes:
            if mode == "or":  # 跳过 "or" 标记
                continue

            match mode:
                case "title":
                    sql_conditions.append("title=?")
                    sql_args.append(title)
                case "link":
                    sql_conditions.append("link=?")
                    sql_args.append(link)

        # Return early when no configured deduplication field is usable.
        if not sql_conditions:
            return False

        # Combine title/link checks with AND by default, OR when requested.
        if "or" in deduplication_modes:
            sql = f"SELECT id FROM main WHERE ({' OR '.join(sql_conditions)})"
        else:
            sql = f"SELECT id FROM main WHERE {' AND '.join(sql_conditions)}"

        cursor.execute(sql, sql_args)
        result = cursor.fetchone()

        if result is not None:
            before = None
            if dry_run:
                before = conn.total_changes
            if not dry_run:
                result_id = result[0]
                cursor.execute(
                    "UPDATE main SET datetime = DATETIME('Now','LocalTime') "
                    "WHERE id = ?;",
                    (result_id,),
                )
                conn.commit()
            elif before != conn.total_changes:
                raise RuntimeError("dry-run dedup check unexpectedly changed database")
            return True

        return False

    finally:
        cursor.close()


def insert_into_cache_db(conn: Connection, entry: dict[str, Any]) -> None:
    cursor = conn.cursor()
    title = entry["title"]
    link = entry["link"]
    cursor.execute(
        "INSERT INTO main (title, link) VALUES (?, ?);",
        (title, link),
    )
    cursor.close()
    conn.commit()
