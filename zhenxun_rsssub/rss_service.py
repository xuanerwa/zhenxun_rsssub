from __future__ import annotations

import time

from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot

from . import feed_state
from .globals import global_config, plugin_config
from .host_adapter import notify_superusers, resolve_onebot
from .repository_entries import entries_file_exists, initialize_entries
from .rss_parser import RSSParser
from .utils import (
    extract_entry_fields,
    extract_valid_group_id,
    extract_valid_user_id,
    get_entry_hash,
)


async def extract_valid_subscribers(rss, bot: Bot):
    if rss.user_id:
        rss.user_id = await extract_valid_user_id(bot, rss.user_id)
    if rss.group_id:
        rss.group_id = await extract_valid_group_id(bot, rss.group_id)


async def update(rss, bot: Bot | None = None, *, force: bool = False):
    lock = rss._get_update_lock()
    if lock.locked():
        logger.info(f"{rss._log_prefix} update already running, skip this turn")
        return

    try:
        async with lock:
            with rss.defer_state_write():
                await update_locked(rss, bot, force=force)
    except Exception as e:
        feed_state.mark_fetch_failure(rss, str(e))
        logger.exception(f"{rss._log_prefix} update failed: {e}")


async def update_locked(rss, bot: Bot | None = None, *, force: bool = False):
    bot = bot or resolve_onebot()
    if bot is None:
        return
    if not force and feed_state.is_retry_deferred(rss):
        retry_at = feed_state.next_retry_datetime(rss)
        logger.info(f"{rss._log_prefix} retry deferred until {retry_at}")
        return
    if not force and feed_state.is_recommended_update_deferred(rss):
        update_at = feed_state.recommended_update_datetime(rss)
        logger.info(f"{rss._log_prefix} feed timing deferred until {update_at}")
        return

    await extract_valid_subscribers(rss, bot)
    if not any([rss.user_id, rss.group_id]):
        await stop_update_and_notify(rss, bot, reason="no valid subscription target")
        return

    result = await rss.fetch()
    data = result.data
    initial_fetch = not entries_file_exists(rss.name)

    if result.cached:
        feed_state.mark_fetch_success(rss)
        rss._record_metrics(result=result, error=None)
        logger.info(f"{rss._log_prefix}no updates found")
        return

    if not result.ok or not data or not data.get("feed"):
        error = result.error or "Unable to fetch or parse feed"
        notify_msg = "Unable to fetch"
        if rss.cookie:
            notify_msg += ", Cookie "
        notify_msg += f" or URL is invalid: {error}"
        feed_state.mark_fetch_failure(rss, notify_msg, result)
        rss._record_metrics(result=result, error=error)

        if initial_fetch:
            if plugin_config.proxy and not rss.use_proxy:
                logger.info(f"{rss._log_prefix}initial fetch failed, retry with proxy")
                rss.use_proxy = True
                rss.next_retry_at = None
                rss.mark_state_dirty()
                await update_locked(rss, bot, force=True)
            else:
                await stop_update_and_notify(
                    rss, bot, "initial fetch failed: " + notify_msg
                )

        if rss.error_count >= 100:
            await stop_update_and_notify(
                rss, bot, "fetch failed 100 times: " + notify_msg
            )

        return

    feed_state.update_feed_timing_hints(rss, data, result.timing_hint_xml)
    feed_state.mark_fetch_success(rss)

    if initial_fetch:
        entries = []
        for entry in data["entries"]:
            entry["hash"] = get_entry_hash(entry)
            entries.append(extract_entry_fields(entry))

        await initialize_entries(rss.name, entries)

        logger.info(f"{rss._log_prefix}initial fetch succeeded, baseline initialized")
        rss._record_metrics(
            result=result,
            entry_count=len(data.get("entries") or []),
            new_entry_count=len(entries),
            error=None,
        )
        return

    parse_started_at = time.monotonic()
    ctx = await RSSParser(rss=rss).parse(data)
    rss._record_metrics(
        result=result,
        parse_duration_ms=(time.monotonic() - parse_started_at) * 1000,
        send_duration_ms=ctx.send_duration_ms,
        entry_count=len(ctx.entries),
        new_entry_count=len(ctx.new_entries),
        image_count=sum(len(message.images) for message in ctx.msg_contents.values()),
        messages_sent=ctx.messages_sent,
        error=None,
    )


async def test_parse(rss) -> tuple[bool, str]:
    result = await rss.fetch()
    data = result.data
    if result.cached:
        feed_state.mark_fetch_success(rss)
        rss._record_metrics(result=result, error=None)
        return (
            True,
            "\n".join(
                [
                    "Condition request hit cache; no new content.",
                    f"Source: {result.source}",
                    f"Status: {result.status or 'unknown'}",
                    f"URL: {result.url}",
                    f"Elapsed: {result.elapsed_ms:.0f} ms",
                ]
            ),
        )
    if not result.ok or not data or not data.get("feed"):
        error = result.error or "Unable to fetch or parse feed"
        feed_state.mark_fetch_failure(rss, f"test fetch failed: {error}", result)
        rss._record_metrics(result=result, error=error)
        return (
            False,
            "\n".join(
                [
                    "Fetch failed: unable to fetch or parse feed.",
                    f"Source: {result.source}",
                    f"Status: {result.status or 'unknown'}",
                    f"URL: {result.url}",
                    f"Error: {error}",
                    f"Elapsed: {result.elapsed_ms:.0f} ms",
                ]
            ),
        )

    feed_state.update_feed_timing_hints(rss, data, result.timing_hint_xml)
    feed_state.mark_fetch_success(rss)
    parse_started_at = time.monotonic()
    ctx = await RSSParser(rss=rss).parse(data, dry_run=True)
    rss._record_metrics(
        result=result,
        parse_duration_ms=(time.monotonic() - parse_started_at) * 1000,
        send_duration_ms=ctx.send_duration_ms,
        entry_count=len(ctx.entries),
        new_entry_count=len(ctx.new_entries),
        image_count=sum(len(message.images) for message in ctx.msg_contents.values()),
        messages_sent=0,
        error=None,
    )
    lines = [
        f"Test parse completed: {rss.name}",
        f"Source: {result.source}",
        f"Status: {result.status or 'unknown'}",
        f"URL: {result.url}",
        f"Elapsed: {result.elapsed_ms:.0f} ms",
        f"Content-Length: {result.content_length} bytes",
        f"Feed title: {ctx.title or 'unknown'}",
        f"Entries: {len(ctx.entries)}",
        f"New entries: {len(ctx.new_entries)}",
        f"Preview messages: {len(ctx.msg_contents)}",
    ]
    for index, message in enumerate(ctx.msg_contents.values(), 1):
        preview = message.plain_text().replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:117] + "..."
        lines.append(
            f"{index}. {preview or '[image only]'} | images {len(message.images)}"
        )
        if index >= 5:
            break
    return True, "\n".join(lines)


async def stop_update_and_notify(rss, bot: Bot, reason: str):
    """Stop feed updates and notify superusers."""
    rss.stop = True
    rss.upsert()
    from .scheduler import remove_rss_update_job

    remove_rss_update_job(rss)
    await notify_superusers(
        bot,
        global_config.superusers,
        f"{rss.name}[{rss.url}] stopped ({reason})",
    )
