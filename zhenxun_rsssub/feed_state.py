from __future__ import annotations

from datetime import datetime, timedelta, timezone
from datetime import time as datetime_time
import re
from typing import Any

from nonebot import logger

from .models import FetchResult

WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def next_retry_datetime(rss) -> datetime | None:
    if not rss.next_retry_at:
        return None
    try:
        retry_at = datetime.fromisoformat(rss.next_retry_at)
    except ValueError:
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return retry_at


def is_retry_deferred(rss) -> bool:
    retry_at = next_retry_datetime(rss)
    return bool(retry_at and datetime.now(timezone.utc) < retry_at)


def recommended_update_datetime(rss) -> datetime | None:
    if not rss.next_recommended_update_at:
        return None
    try:
        update_at = datetime.fromisoformat(rss.next_recommended_update_at)
    except ValueError:
        return None
    if update_at.tzinfo is None:
        update_at = update_at.replace(tzinfo=timezone.utc)
    return update_at


def is_recommended_update_deferred(rss) -> bool:
    update_at = recommended_update_datetime(rss)
    return bool(update_at and datetime.now(timezone.utc) < update_at)


def parse_user_frequency_minutes(rss) -> int | None:
    if re.search(r"[_*/,-]", rss.frequency):
        return None
    try:
        return max(1, int(float(rss.frequency)))
    except (TypeError, ValueError):
        return None


def effective_interval_minutes(rss) -> int | None:
    user_minutes = parse_user_frequency_minutes(rss)
    feed_minutes = (
        rss.feed_ttl_minutes
        if isinstance(rss.feed_ttl_minutes, int) and rss.feed_ttl_minutes > 0
        else None
    )
    if user_minutes and feed_minutes:
        return max(user_minutes, feed_minutes)
    return user_minutes or feed_minutes


def update_feed_timing_hints(
    rss, data: dict[str, Any], timing_hint_xml: str = ""
) -> None:
    feed = data.get("feed") or {}
    rss.feed_ttl_minutes = parse_feed_ttl(feed)
    rss.feed_skip_hours = parse_skip_hours(feed, timing_hint_xml)
    rss.feed_skip_days = parse_skip_days(feed, timing_hint_xml)
    rss.mark_state_dirty()


def update_next_recommended_update(rss) -> None:
    next_at = calculate_next_recommended_update(rss)
    rss.next_recommended_update_at = next_at.isoformat() if next_at else None
    rss.mark_state_dirty()


def calculate_next_recommended_update(
    rss, start: datetime | None = None
) -> datetime | None:
    interval_minutes = effective_interval_minutes(rss)
    if interval_minutes is None:
        return None
    candidate = (start or datetime.now(timezone.utc)) + timedelta(
        minutes=interval_minutes
    )
    return apply_feed_skip_windows(rss, candidate)


def apply_feed_skip_windows(rss, candidate: datetime) -> datetime:
    candidate = candidate.astimezone(timezone.utc)
    skip_days = set(rss.feed_skip_days or [])
    skip_hours = set(rss.feed_skip_hours or [])

    for _ in range(24 * 14):
        if candidate.weekday() in skip_days:
            candidate = datetime.combine(
                (candidate + timedelta(days=1)).date(),
                datetime_time.min,
                tzinfo=timezone.utc,
            )
            continue
        if candidate.hour in skip_hours:
            candidate = candidate.replace(
                minute=0, second=0, microsecond=0
            ) + timedelta(hours=1)
            continue
        return candidate
    return candidate


def mark_fetch_failure(
    rss, error: str | None = None, result: FetchResult | None = None
) -> None:
    rss.error_count += 1
    delay_minutes = min(60, 2 ** min(rss.error_count - 1, 6))
    retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
    if result and result.retry_after:
        retry_after_at = datetime.now(timezone.utc) + timedelta(
            seconds=result.retry_after
        )
        retry_at = max(retry_at, retry_after_at)
    rss.next_retry_at = retry_at.isoformat()
    if error:
        rss.last_error = error
    rss.mark_state_dirty()
    logger.warning(
        f"{rss._log_prefix} fetch failed {rss.error_count} times, "
        f"retry after {delay_minutes} minute(s)"
    )


def mark_fetch_success(rss) -> None:
    rss.last_success_at = datetime.now(timezone.utc).isoformat()
    rss.last_error = None
    rss.error_count = 0
    rss.next_retry_at = None
    update_next_recommended_update(rss)
    rss.mark_state_dirty()


def parse_feed_ttl(feed: dict[str, Any]) -> int | None:
    raw_ttl = feed.get("ttl")
    if raw_ttl is None:
        return None
    try:
        ttl = int(float(str(raw_ttl).strip()))
    except (TypeError, ValueError):
        return None
    return ttl if ttl > 0 else None


def raw_xml_values(timing_hint_xml: str, tag: str) -> list[str]:
    if not timing_hint_xml:
        return []
    return re.findall(rf"<{tag}>\s*([^<]+?)\s*</{tag}>", timing_hint_xml, re.I)


def collect_feed_values(feed: dict[str, Any], key: str) -> list[Any]:
    values: list[Any] = []
    raw = feed.get(key)
    if isinstance(raw, list | tuple | set):
        values.extend(raw)
    elif raw not in (None, ""):
        values.append(raw)
    return values


def parse_skip_hours(feed: dict[str, Any], timing_hint_xml: str = "") -> list[int]:
    values = collect_feed_values(feed, "skiphours")
    values.extend(collect_feed_values(feed, "hour"))
    values.extend(raw_xml_values(timing_hint_xml, "hour"))
    result = set()
    for value in values:
        for part in re.split(r"[,\s]+", str(value).strip()):
            if not part:
                continue
            try:
                hour = int(part)
            except ValueError:
                continue
            if 0 <= hour <= 23:
                result.add(hour)
    return sorted(result)


def parse_skip_days(feed: dict[str, Any], timing_hint_xml: str = "") -> list[int]:
    values = collect_feed_values(feed, "skipdays")
    values.extend(collect_feed_values(feed, "day"))
    values.extend(raw_xml_values(timing_hint_xml, "day"))
    result = set()
    for value in values:
        for part in re.split(r"[,\s]+", str(value).strip()):
            if not part:
                continue
            normalized = part.lower()
            if normalized in WEEKDAY_NAMES:
                result.add(WEEKDAY_NAMES[normalized])
                continue
            try:
                day = int(part)
            except ValueError:
                continue
            if 0 <= day <= 6:
                result.add(day)
    return sorted(result)
