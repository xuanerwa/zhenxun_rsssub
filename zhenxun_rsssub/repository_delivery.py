from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import asyncio

from .models.rss_models import RssDeliveryLog


async def _upsert_delivery_record_async(record: dict[str, Any]) -> None:
    """异步方法：插入或更新投递记录"""
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
    
    # 准备数据（不包含查询条件字段）
    delivery_data = {
        "status": status,
        "error": record.get("error"),
        "message_id": record.get("message_id"),
        "time": record.get("time"),
    }
    
    # 使用update_or_create确保数据一致性
    await RssDeliveryLog.update_or_create(
        feed_name=feed_name,
        entry_hash=entry_hash,
        target_type=target_type,
        target_id=target_id,
        defaults=delivery_data
    )


async def upsert_delivery_log(record: dict[str, Any]) -> None:
    await upsert_delivery_logs([record])


async def upsert_delivery_logs(records: Iterable[dict[str, Any]]) -> None:
    """插入或更新多条投递记录"""
    records_list = list(records)
    if not records_list:
        return
    
    for record in records_list:
        await _upsert_delivery_record_async(record)


async def load_delivery_logs(
    feed_name: str, entry_hash: str | None = None
) -> list[dict[str, Any]]:
    """加载投递日志"""
    if entry_hash:
        logs = await RssDeliveryLog.filter(
            feed_name=feed_name, 
            entry_hash=entry_hash
        ).order_by("-updated_at").all()
    else:
        logs = await RssDeliveryLog.filter(
            feed_name=feed_name
        ).order_by("-updated_at").all()
    
    return [
        {
            "feed_name": log.feed_name,
            "entry_hash": log.entry_hash,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "status": log.status,
            "error": log.error,
            "message_id": log.message_id,
            "time": log.time,
        }
        for log in logs
    ]


async def delivered_target_keys(feed_name: str, entry_hash: str) -> set[tuple[str, str]]:
    """获取已成功投递的目标键"""
    logs = await load_delivery_logs(feed_name, entry_hash)
    
    result = set()
    for record in logs:
        if record.get("status") != "success":
            continue
        target_type = str(record.get("target_type") or "")
        target_id = str(record.get("target_id") or "")
        if target_type and target_id:
            result.add((target_type, target_id))
    return result


async def delete_delivery_logs(feed_name: str) -> None:
    """删除投递日志"""
    await RssDeliveryLog.filter(feed_name=feed_name).delete()
