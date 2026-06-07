from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import re
from urllib.parse import urlparse

from nonebot import logger, require
from yarl import URL

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from . import feed_state
from .globals import plugin_config
from .host_adapter import resolve_onebot
from .rss import RSS

BATCH_JOB_ID = "zhenxun_rsssub_batch_worker"
_registered_feeds: dict[str, RSS] = {}
_feed_next_due_at: dict[str, datetime] = {}
_host_semaphores: dict[str, asyncio.Semaphore] = {}
_batch_lock: asyncio.Lock | None = None


def stable_jitter_seconds(feed_name: str, max_seconds: int = 60) -> int:
    digest = hashlib.md5(feed_name.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % max(1, max_seconds)


def stable_start_date(feed_name: str, max_delay_seconds: int = 60) -> datetime:
    return datetime.now() + timedelta(
        seconds=stable_jitter_seconds(feed_name, max_delay_seconds)
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _batch_lock() -> asyncio.Lock:
    global _batch_lock
    if _batch_lock is None:
        _batch_lock = asyncio.Lock()
    return _batch_lock


def _configured_batch_interval_seconds() -> int:
    return max(10, int(plugin_config.scheduler_batch_interval_seconds or 60))


def _configured_batch_concurrency() -> int:
    return max(1, int(plugin_config.scheduler_batch_concurrency or 4))


def _configured_host_concurrency() -> int:
    return max(1, int(plugin_config.scheduler_per_host_concurrency or 1))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _feed_host(rss: RSS) -> str:
    try:
        url = URL(rss.get_url())
        if url.host:
            return url.host.lower()
    except Exception:
        pass
    parsed = urlparse(str(rss.url))
    return (parsed.hostname or "__unknown__").lower()


def _host_semaphore(host: str) -> asyncio.Semaphore:
    sem = _host_semaphores.get(host)
    if sem is None:
        sem = asyncio.Semaphore(_configured_host_concurrency())
        _host_semaphores[host] = sem
    return sem


def _cron_due(rss: RSS, now: datetime) -> bool:
    if not re.search(r"[_*/,-]", rss.frequency):
        return False
    next_due = _feed_next_due_at.get(rss.name)
    if next_due is None:
        delay = stable_jitter_seconds(rss.name, _configured_batch_interval_seconds())
        next_due = now + timedelta(seconds=delay)
        _feed_next_due_at[rss.name] = next_due
    return now >= next_due


def _interval_due(rss: RSS, now: datetime) -> bool:
    if re.search(r"[_*/,-]", rss.frequency):
        return _cron_due(rss, now)
    if due_at := _feed_next_due_at.get(rss.name):
        return now >= due_at
    if last_success := _parse_datetime(rss.last_success_at):
        interval = rss.effective_interval_minutes() or int(rss.frequency or 5)
        due_at = last_success + timedelta(minutes=max(1, interval))
    else:
        due_at = now + timedelta(seconds=stable_jitter_seconds(rss.name))
    _feed_next_due_at[rss.name] = due_at
    return now >= due_at


def _deferred_until(rss: RSS) -> datetime | None:
    candidates = [
        feed_state.next_retry_datetime(rss),
        feed_state.recommended_update_datetime(rss),
    ]
    return max((item for item in candidates if item), default=None)


def _is_due(rss: RSS, now: datetime) -> bool:
    if rss.stop or not any([rss.user_id, rss.group_id]):
        return False
    deferred_until = _deferred_until(rss)
    if deferred_until and now < deferred_until:
        _feed_next_due_at[rss.name] = deferred_until
        return False
    return _interval_due(rss, now)


def _schedule_next_due(rss: RSS, now: datetime) -> None:
    deferred_until = _deferred_until(rss)
    if deferred_until and deferred_until > now:
        _feed_next_due_at[rss.name] = deferred_until
        return
    if re.search(r"[_*/,-]", rss.frequency):
        _feed_next_due_at[rss.name] = now + timedelta(
            seconds=_configured_batch_interval_seconds()
        )
        return
    try:
        interval = rss.effective_interval_minutes() or int(rss.frequency or 5)
    except (TypeError, ValueError):
        interval = 5
    _feed_next_due_at[rss.name] = now + timedelta(minutes=max(1, interval))


async def _run_one_feed(rss: RSS, *, force: bool = False) -> None:
    host = _feed_host(rss)
    async with _host_semaphore(host):
        await check_rss_update(rss, force=force)
    _schedule_next_due(rss, _utc_now())


async def check_rss_update(rss: RSS, *, force: bool = False):
    """检查单个RSS订阅的更新。"""
    logger.info(f"检查RSS订阅更新: {rss.name}")
    try:
        await asyncio.wait_for(
            rss.update(resolve_onebot(), force=force),
            timeout=30,
        )
    except asyncio.TimeoutError:
        logger.error(f"{rss.name} 检查更新超时，结束此次任务!")


async def check_registered_feeds() -> None:
    """Batch RSS worker entrypoint."""
    async with _batch_lock():
        now = _utc_now()
        due_feeds = [rss for rss in _registered_feeds.values() if _is_due(rss, now)]
        if not due_feeds:
            return
        sem = asyncio.Semaphore(_configured_batch_concurrency())

        async def guarded(feed: RSS) -> None:
            async with sem:
                await _run_one_feed(feed)

        await asyncio.gather(*(guarded(rss) for rss in due_feeds))


def ensure_batch_job() -> None:
    if scheduler.get_job(BATCH_JOB_ID):
        return
    scheduler.add_job(
        func=check_registered_feeds,
        trigger="interval",
        seconds=_configured_batch_interval_seconds(),
        id=BATCH_JOB_ID,
        misfire_grace_time=30,
        max_instances=1,
        coalesce=True,
    )
    logger.success("RSS batch worker created")


def remove_rss_update_job(rss: RSS):
    """取消订阅的调度注册。"""
    _registered_feeds.pop(rss.name, None)
    _feed_next_due_at.pop(rss.name, None)
    if scheduler.get_job(rss.name):
        scheduler.remove_job(rss.name)


async def create_rss_update_job(rss: RSS, *, run_immediately: bool = True):
    """注册 RSS 到统一 batch worker。"""
    remove_rss_update_job(rss)
    if not any([rss.user_id, rss.group_id]):
        logger.warning(f"RSS订阅 {rss.name} 没有有效的订阅目标，跳过创建任务")
        return

    _registered_feeds[rss.name] = rss
    ensure_batch_job()
    if run_immediately:
        await _run_one_feed(rss, force=True)
    else:
        _feed_next_due_at[rss.name] = stable_start_date(rss.name).astimezone(
            timezone.utc
        )
    logger.success(f"RSS订阅 {rss.name} 已注册到 batch worker")
