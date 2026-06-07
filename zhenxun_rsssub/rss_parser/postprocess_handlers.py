from __future__ import annotations

import time
from typing import TYPE_CHECKING

from nonebot import logger

if TYPE_CHECKING:
    from ..rss import RSS

from ..repository_delivery import delivered_target_keys, upsert_delivery_logs
from ..rss_message import with_title
from . import rss_entries_file_operations as FileIO
from .context import Context
from .message_sender import send_message
from .rss_parser import ParsingHandlerManager

TargetKey = tuple[str, str]


def _split_target_keys(target_keys: set[TargetKey]) -> tuple[set[int], set[int]]:
    user_ids = {
        int(target_id)
        for target_type, target_id in target_keys
        if target_type == "private"
    }
    group_ids = {
        int(target_id)
        for target_type, target_id in target_keys
        if target_type == "group"
    }
    return user_ids, group_ids


def _success_target_keys(results) -> set[TargetKey]:
    return {
        (result.target_type, str(result.target_id)) for result in results if result.ok
    }


async def _record_delivery_results(rss: "RSS", entry_hash: str, results) -> None:
    await upsert_delivery_logs(
        result.to_record(feed_name=rss.name, entry_hash=entry_hash)
        for result in results
    )


def _missing_target_keys(ctx: Context, rss: "RSS", entry_hash: str) -> set[TargetKey]:
    return ctx.target_keys - delivered_target_keys(rss.name, entry_hash)


async def _write_entry_delivery_state(ctx: Context, rss: "RSS", entry: dict) -> bool:
    missing_targets = _missing_target_keys(ctx, rss, entry["hash"])
    fully_delivered = not missing_targets
    if fully_delivered:
        if rss.deduplication_modes and ctx.conn:
            # Dedup only after every target confirms delivery.
            from .cache_db_manager import insert_into_cache_db

            insert_into_cache_db(ctx.conn, entry)
        entry.pop("to_send", None)
    else:
        entry["to_send"] = True
    await FileIO.write_rss_entry(ctx.rss_name, entry)
    return fully_delivered


@ParsingHandlerManager.postprocess_handler()
async def send_messages(ctx: Context, rss: "RSS"):
    started_at = time.monotonic()
    if not ctx.msg_contents:
        logger.info(f"[{rss.name}]没有新推送")
        return
    if ctx.dry_run:
        return

    any_success = False

    if rss.send_merged_msg:
        # 发送合并转发消息
        msgs_to_send = [
            with_title(ctx.msg_title, message) for message in ctx.msg_contents.values()
        ]
        results = await send_message(rss.user_id, rss.group_id, msgs_to_send)
        success_targets = _success_target_keys(results)
        any_success = bool(success_targets)
        if any_success:
            ctx.messages_sent += len(success_targets) * len(ctx.new_entries)
            for entry in ctx.new_entries:
                entry_hash = entry["hash"]
                await _record_delivery_results(rss, entry_hash, results)
                fully_delivered = await _write_entry_delivery_state(ctx, rss, entry)
                if not fully_delivered:
                    ctx.msg_error_count += 1
        else:
            logger.warning(f"[{rss.name}]发送合并消息失败，将使用逐条发送")
            for entry in ctx.new_entries:
                entry["to_send"] = True
            ctx.msg_error_count += len(ctx.msg_contents)

    new_entries_hash_index_map = {e["hash"]: i for i, e in enumerate(ctx.new_entries)}
    if not any_success:
        for entry_hash, content in ctx.msg_contents.items():
            # 逐条发送消息
            entry = ctx.new_entries[new_entries_hash_index_map[entry_hash]]
            msg_to_send = with_title(ctx.msg_title, content)
            delivered = delivered_target_keys(rss.name, entry_hash)
            missing_targets = ctx.target_keys - delivered
            user_ids, group_ids = _split_target_keys(missing_targets)
            results = await send_message(user_ids, group_ids, msg_to_send)
            await _record_delivery_results(rss, entry_hash, results)

            if not _success_target_keys(results) and missing_targets:
                ctx.msg_error_count += 1
            any_success |= bool(_success_target_keys(results))
            ctx.messages_sent += len(_success_target_keys(results))
            await _write_entry_delivery_state(ctx, rss, entry)

    ctx.send_duration_ms += (time.monotonic() - started_at) * 1000
    await FileIO.truncate_file(ctx.rss_name, len(ctx.new_entries))

    if any_success:
        logger.info(
            f"[{rss.name}]推送成功"
            + (f"，失败{ctx.msg_error_count}次" if ctx.msg_error_count else "")
        )
    else:
        logger.error(f"[{rss.name}]推送失败，共失败{ctx.msg_error_count}次")


@ParsingHandlerManager.postprocess_handler(priority=100)
async def close_db_connection(ctx: Context, rss: "RSS"):
    """关闭数据库连接"""
    if ctx.conn:
        ctx.conn.close()
        ctx.conn = None
