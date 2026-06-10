from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import asyncio

from .globals import plugin_config
from .models.rss_models import RssEntry, RssDeliveryLog
from .utils import extract_entry_fields, get_entry_datetime


def _entry_datetime_text(entry: dict[str, Any]) -> str:
    try:
        return get_entry_datetime(entry).isoformat()
    except Exception:
        return ""


async def _upsert_entry_async(feed_name: str, entry: dict[str, Any]) -> None:
    """异步方法：插入或更新文章条目"""
    entry = extract_entry_fields(entry)
    entry_hash = str(entry.get("hash") or "")
    if not entry_hash:
        return
    
    # 准备数据（不包含 feed_name 和 entry_hash，因为它们是查询条件）
    entry_data = {
        "data": entry,
        "entry_datetime": _entry_datetime_text(entry),
        "to_send": bool(entry.get("to_send")),
    }
    
    # 使用update_or_create确保数据一致性
    await RssEntry.update_or_create(
        feed_name=feed_name,
        entry_hash=entry_hash,
        defaults=entry_data
    )


async def entries_file_exists(name: str) -> bool:
    """检查订阅文章文件是否存在"""
    count = await RssEntry.filter(feed_name=name).count()
    return count > 0


async def rename_entries_file(old_name: str, new_name: str) -> None:
    """重命名文章文件"""
    await RssEntry.filter(feed_name=old_name).update(feed_name=new_name)
    await RssDeliveryLog.filter(feed_name=old_name).update(feed_name=new_name)


async def delete_entries_file(name: str) -> None:
    """删除文章文件"""
    await RssEntry.filter(feed_name=name).delete()
    await RssDeliveryLog.filter(feed_name=name).delete()


async def load_entries(name: str) -> list[dict[str, Any]]:
    """加载文章条目"""
    entries = await RssEntry.filter(feed_name=name).order_by("entry_datetime", "id").all()
    return [entry.data for entry in entries if entry.data]


async def find_entry_by_link(name: str, link: str) -> dict[str, Any] | None:
    entries = await RssEntry.filter(feed_name=name).all()
    for entry in entries:
        data = entry.data or {}
        if data.get("link") == link:
            return data
    return None


async def initialize_entries(name: str, entries: Iterable[dict[str, Any]]) -> None:
    """初始化文章条目"""
    entries_list = list(entries)
    
    # 先删除现有的条目
    await RssEntry.filter(feed_name=name).delete()
    
    # 批量插入新条目
    for entry in entries_list:
        await _upsert_entry_async(name, entry)


async def write_entry(name: str, entry: dict[str, Any]) -> None:
    """写入文章条目"""
    await _upsert_entry_async(name, entry)


async def truncate_entries(name: str, num_new_entries: int) -> None:
    """截断文章条目，保留最新的条目"""
    limit = plugin_config.rss_entries_file_limit + num_new_entries
    
    # 获取需要删除的条目
    entries_to_delete = await RssEntry.filter(feed_name=name).order_by("-entry_datetime", "-id").offset(limit).all()
    
    # 删除多余的条目
    for entry in entries_to_delete:
        await entry.delete()
