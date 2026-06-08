import contextlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import time
from typing import Any

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot

_BOT_LIST_CACHE_TTL = 300
_friend_id_cache: dict[str, tuple[float, set[int]]] = {}
_group_id_cache: dict[str, tuple[float, set[int]]] = {}


def _cache_get(cache: dict[str, tuple[float, set[int]]], key: str) -> set[int] | None:
    item = cache.get(key)
    if item is None:
        return None
    expires_at, value = item
    if expires_at <= time.monotonic():
        cache.pop(key, None)
        return None
    return value


def _cache_set(cache: dict[str, tuple[float, set[int]]], key: str, value: set[int]):
    cache[key] = (time.monotonic() + _BOT_LIST_CACHE_TTL, value)


async def get_bot_friend_id_list(bot: Bot) -> set[int]:
    """获取机器人好友列表，结果缓存5分钟"""
    cached = _cache_get(_friend_id_cache, bot.self_id)
    if cached is not None:
        return cached
    friends = await bot.get_friend_list()
    result = {friend["user_id"] for friend in friends}
    _cache_set(_friend_id_cache, bot.self_id, result)
    return result


async def get_bot_group_id_list(bot: Bot) -> set[int]:
    """获取机器人群组列表，结果缓存5分钟"""
    cached = _cache_get(_group_id_cache, bot.self_id)
    if cached is not None:
        return cached
    groups = await bot.get_group_list()
    result = {group["group_id"] for group in groups}
    _cache_set(_group_id_cache, bot.self_id, result)
    return result


async def extract_valid_user_id(bot: Bot, user_ids: set[int]) -> set[int]:
    """提取有效的用户ID"""
    bot_users = await get_bot_friend_id_list(bot)
    valid, invalid = user_ids & bot_users, user_ids - bot_users
    if invalid:
        logger.warning(
            f"用户 {', '.join(map(str, invalid))} 不是机器人 {bot.self_id} 的好友"
        )
    return valid


async def extract_valid_group_id(bot: Bot, group_ids: set[int]) -> set[int]:
    """提取有效的群组ID"""
    bot_groups = await get_bot_group_id_list(bot)
    valid, invalid = group_ids & bot_groups, group_ids - bot_groups
    if invalid:
        logger.warning(
            f"机器人 {bot.self_id} 未加入群组 {', '.join(map(str, invalid))}"
        )
    return valid


def extract_entry_fields(entry: dict[str, Any]) -> dict[str, Any]:
    """提取RSS文章中需要的字段"""
    wanted = [
        "id",
        "guid",
        "title",
        "link",
        "published",
        "updated",
        "entry_key",
        "hash",
    ]
    if entry.get("to_send"):
        wanted += ["to_send", "content", "summary"]
    return {k: v for k in wanted if (v := entry.get(k))}


def get_entry_hash(entry: dict[str, Any]) -> str:
    """Build a stable RSS/Atom entry key and hash.

    Priority: id/guid > link > title + published/updated > title hash.
    """
    entry_id = entry.get("id") or entry.get("guid")
    if entry_id:
        unique_str = f"id:{entry_id}"
    elif link := entry.get("link"):
        unique_str = f"link:{link}"
    elif title := entry.get("title"):
        date_text = entry.get("published") or entry.get("updated")
        if date_text:
            unique_str = f"title-date:{title}|{date_text}"
        else:
            unique_str = f"title:{title}"
    else:
        unique_str = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    entry["entry_key"] = unique_str
    return hashlib.md5(unique_str.encode("utf-8")).hexdigest()


def get_entry_datetime(entry: dict[str, Any]) -> datetime:
    date_text = entry.get("published", entry.get("updated"))
    if not date_text:
        return datetime.now(timezone.utc)

    with contextlib.suppress(Exception):
        parsed = parsedate_to_datetime(date_text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return datetime.now(timezone.utc)


def chunk_list(lst: list[Any], chunk_size: int):
    """将列表分块"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]
