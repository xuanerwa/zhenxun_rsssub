from __future__ import annotations

from typing import Any
import asyncio

from .models.rss_models import RssFeed, RssEntry, RssDeliveryLog
from .repository_utils import sanitize_feed_name


async def _upsert_feed_record_async(name: str, data: dict[str, Any]) -> None:
    """异步方法：更新订阅记录"""
    # 准备数据（不包含 name，因为 name 是查询条件）
    feed_data = {
        "url": data.get("url", ""),
        "user_id": data.get("user_id", []),
        "group_id": data.get("group_id", []),
        "use_proxy": data.get("use_proxy", False),
        "frequency": data.get("frequency", "5"),
        "only_feed_title": data.get("only_feed_title", False),
        "only_feed_pic": data.get("only_feed_pic", False),
        "download_pic": data.get("download_pic", False),
        "cookie": data.get("cookie"),
        "white_list_keyword": data.get("white_list_keyword"),
        "black_list_keyword": data.get("black_list_keyword"),
        "deduplication_modes": data.get("deduplication_modes", []),
        "max_image_number": data.get("max_image_number", 0),
        "content_to_remove": data.get("content_to_remove", []),
        "send_merged_msg": data.get("send_merged_msg", False),
        "show_hidden_content": data.get("show_hidden_content", False),
        "stop": data.get("stop", False),
        "etag": data.get("etag"),
        "last_modified": data.get("last_modified"),
        "http_cache": data.get("http_cache", {}),
        "last_bozo": data.get("last_bozo", False),
        "last_bozo_exception": data.get("last_bozo_exception"),
        "error_count": data.get("error_count", 0),
        "next_retry_at": data.get("next_retry_at"),
        "last_success_at": data.get("last_success_at"),
        "last_error": data.get("last_error"),
        "last_fetch_result": data.get("last_fetch_result", {}),
        "feed_ttl_minutes": data.get("feed_ttl_minutes"),
        "feed_skip_hours": data.get("feed_skip_hours", []),
        "feed_skip_days": data.get("feed_skip_days", []),
        "next_recommended_update_at": data.get("next_recommended_update_at"),
        "last_metrics": data.get("last_metrics", {}),
    }
    
    # 使用update_or_create确保数据一致性
    await RssFeed.update_or_create(
        name=name,
        defaults=feed_data
    )


async def load_feed_records() -> list[dict[str, Any]]:
    """加载所有订阅记录"""
    feeds = await RssFeed.all()
    records = []
    for feed in feeds:
        record = {
            "name": feed.name,
            "url": feed.url,
            "user_id": feed.user_id or [],
            "group_id": feed.group_id or [],
            "use_proxy": feed.use_proxy,
            "frequency": feed.frequency,
            "only_feed_title": feed.only_feed_title,
            "only_feed_pic": feed.only_feed_pic,
            "download_pic": feed.download_pic,
            "cookie": feed.cookie,
            "white_list_keyword": feed.white_list_keyword,
            "black_list_keyword": feed.black_list_keyword,
            "deduplication_modes": feed.deduplication_modes or [],
            "max_image_number": feed.max_image_number,
            "content_to_remove": feed.content_to_remove or [],
            "send_merged_msg": feed.send_merged_msg,
            "show_hidden_content": getattr(feed, "show_hidden_content", False),
            "stop": feed.stop,
            "etag": feed.etag,
            "last_modified": feed.last_modified,
            "http_cache": feed.http_cache or {},
            "last_bozo": feed.last_bozo,
            "last_bozo_exception": feed.last_bozo_exception,
            "error_count": feed.error_count,
            "next_retry_at": feed.next_retry_at,
            "last_success_at": feed.last_success_at,
            "last_error": feed.last_error,
            "last_fetch_result": feed.last_fetch_result or {},
            "feed_ttl_minutes": feed.feed_ttl_minutes,
            "feed_skip_hours": feed.feed_skip_hours or [],
            "feed_skip_days": feed.feed_skip_days or [],
            "next_recommended_update_at": feed.next_recommended_update_at,
            "last_metrics": feed.last_metrics or {},
        }
        records.append(record)
    return records


def upsert_feed_state(name: str, data: dict[str, Any]) -> None:
    """更新订阅状态"""
    async def _upsert():
        await _upsert_feed_record_async(name, data)
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_upsert())
        else:
            loop.run_until_complete(_upsert())
    except RuntimeError:
        asyncio.run(_upsert())


def rename_feed_record(old_name: str, new_name: str, data: dict[str, Any]) -> None:
    """重命名订阅记录"""
    async def _rename():
        # 更新所有相关表中的订阅名称
        await RssFeed.filter(name=old_name).update(name=new_name)
        await RssEntry.filter(feed_name=old_name).update(feed_name=new_name)
        await RssDeliveryLog.filter(feed_name=old_name).update(feed_name=new_name)
        
        # 更新或创建新的订阅记录
        await _upsert_feed_record_async(new_name, data)
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_rename())
        else:
            loop.run_until_complete(_rename())
    except RuntimeError:
        asyncio.run(_rename())


def upsert_feed_record(name: str, data: dict[str, Any], old_name: str | None = None):
    """插入或更新订阅记录"""
    if old_name and old_name != name:
        rename_feed_record(old_name, name, data)
    else:
        async def _upsert():
            await _upsert_feed_record_async(name, data)
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_upsert())
            else:
                loop.run_until_complete(_upsert())
        except RuntimeError:
            asyncio.run(_upsert())


def remove_feed_record(name: str) -> None:
    """删除订阅记录"""
    async def _remove():
        # 删除所有相关数据
        await RssFeed.filter(name=name).delete()
        await RssEntry.filter(feed_name=name).delete()
        await RssDeliveryLog.filter(feed_name=name).delete()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_remove())
        else:
            loop.run_until_complete(_remove())
    except RuntimeError:
        asyncio.run(_remove())
