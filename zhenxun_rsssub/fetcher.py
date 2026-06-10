from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
import time
from typing import Literal

import feedparser
from nonebot import logger
from yarl import URL
from zhenxun.utils.http_utils import AsyncHttpx

from .globals import plugin_config
from .fetch_models import FetchResult, compact_error

HEADERS = {
    "Accept": "application/xhtml+xml,application/xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    ),
    "Connection": "keep-alive",
    "Content-Type": "application/xml; charset=utf-8",
}

ACCEPT_FETCH_STATUS_CODES = (304, *range(400, 600))


async def fetch(rss) -> FetchResult:
    """Fetch RSS content."""
    url = URL(rss.get_url())
    request_proxy = get_request_proxy(rss.use_proxy, url)
    result = await fetch_url(rss, url, request_proxy=request_proxy, source="primary")
    if result.ok or result.cached:
        record_fetch_result(rss, result)
        return result

    if not rss.url.scheme and plugin_config.rsshub_fallback_urls:
        logger.warning(
            f"{rss._log_prefix} failed to access {url}: {result.error}, "
            "trying fallback RSSHub endpoints"
        )
        result = await fetch_fallback(rss, request_proxy, previous=result)
    else:
        logger.error(f"{rss._log_prefix} failed to access {url}: {result.error}")

    record_fetch_result(rss, result)
    return result


def get_cached_headers(rss, url: str) -> dict[str, str]:
    cached = rss.http_cache.get(url, {})
    primary_url = rss.get_url()
    etag = cached.get("etag")
    last_modified = cached.get("last_modified")
    if url == primary_url:
        etag = etag or rss.etag
        last_modified = last_modified or rss.last_modified
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    return headers


def update_http_cache(rss, url: str, headers: dict[str, str]) -> None:
    old_cache = rss.http_cache.get(url, {})
    etag = headers.get("etag")
    last_modified = headers.get("last-modified")
    if not etag and not last_modified:
        return
    rss.http_cache[url] = {
        "etag": etag or old_cache.get("etag"),
        "last_modified": last_modified or old_cache.get("last_modified"),
    }
    if url == rss.get_url():
        rss.etag = rss.http_cache[url]["etag"]
        rss.last_modified = rss.http_cache[url]["last_modified"]
    rss.mark_state_dirty()


def record_fetch_result(rss, result: FetchResult) -> None:
    rss.last_fetch_result = result.to_record()
    rss.last_bozo = result.bozo
    rss.last_bozo_exception = result.bozo_exception
    if result.error:
        rss.last_error = result.error
    rss.mark_state_dirty()
    if result.bozo_exception:
        logger.warning(f"{rss._log_prefix} feedparser bozo: {result.bozo_exception}")


def get_request_proxy(use_proxy: bool, url: URL) -> str | bool | None:
    """Return proxy config for AsyncHttpx.

    ``None`` means use 真寻全局 HTTP 客户端配置；``False`` means explicitly
    disable proxy for this request.
    """
    if url.host in {"127.0.0.1", "localhost"}:
        return False
    if not use_proxy:
        return False
    if plugin_config.proxy:
        return str(plugin_config.proxy)
    return None


async def fetch_url(
    rss,
    url: URL,
    *,
    request_proxy: str | bool | None,
    source: Literal["primary", "fallback"],
) -> FetchResult:
    started_at = time.monotonic()
    cookie = rss.cookie or None
    headers = HEADERS.copy()
    if cookie:
        headers["Cookie"] = cookie
    if not plugin_config.debug:
        headers.update(get_cached_headers(rss, str(url)))

    try:
        request_kwargs = {
            "headers": headers,
            "timeout": 10,
            "accept_status_codes": ACCEPT_FETCH_STATUS_CODES,
        }
        if isinstance(request_proxy, str):
            request_kwargs["proxy"] = request_proxy
        elif request_proxy is False:
            request_kwargs["use_proxy"] = False
        resp = await AsyncHttpx.get(str(url), **request_kwargs)
        elapsed_ms = (time.monotonic() - started_at) * 1000
        headers = normalize_headers(resp.headers)
        content_length = content_length_from_response(headers, resp.content)
        result = FetchResult(
            ok=False,
            status=resp.status_code,
            url=str(url),
            source=source,
            headers=headers,
            elapsed_ms=elapsed_ms,
            content_length=content_length,
            retry_after=parse_retry_after(headers),
        )
        if resp.status_code == 304 or (
            resp.status_code == 200 and int(headers.get("content-length", "1")) == 0
        ):
            result.ok = True
            result.cached = True
            return result

        if resp.status_code < 200 or resp.status_code >= 300:
            result.error = http_error(resp.status_code, resp.text)
            return result

        update_http_cache(rss, str(url), headers)
        data = feedparser.parse(resp.text)
        bozo_exception = data.get("bozo_exception")
        result.data = data
        result.bozo = bool(data.get("bozo"))
        result.bozo_exception = str(bozo_exception) if bozo_exception else None
        result.timing_hint_xml = extract_timing_hint_xml(resp.text)
        result.ok = bool(data.get("feed"))
        if not result.ok:
            result.error = (
                result.bozo_exception or "Parsed document is not a valid feed"
            )
        return result
    except Exception as e:
        return exception_result(
            url=str(url),
            source=source,
            error=e,
            elapsed_ms=(time.monotonic() - started_at) * 1000,
        )


async def fetch_fallback(
    rss, request_proxy: str | bool | None, *, previous: FetchResult | None = None
) -> FetchResult:
    """Fetch RSS content from fallback RSSHub endpoints."""
    results: list[FetchResult] = []
    if previous:
        results.append(previous)
    for fallback_url in plugin_config.rsshub_fallback_urls:
        url = URL(rss.get_url(fallback_url))
        fallback_proxy = False if request_proxy is False else get_request_proxy(
            rss.use_proxy, url
        )
        result = await fetch_url(
            rss, url, request_proxy=fallback_proxy, source="fallback"
        )
        if result.ok or result.cached:
            return result
        logger.error(f"{rss._log_prefix} failed to access {url}: {result.error}")
        results.append(result)

    if not results:
        return FetchResult(
            ok=False,
            status=None,
            url=str(rss.url),
            source="fallback",
            error="No RSSHub fallback URL configured",
        )
    latest = results[-1]
    errors = []
    for item in results:
        error = item.error or f"HTTP {item.status or 'unknown'}"
        errors.append(f"{item.source} {item.url}: {error}")
    latest.error = compact_error("; ".join(errors), 600)
    return latest


def normalize_headers(headers) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in headers.items()}


def content_length_from_response(headers: dict[str, str], content: bytes) -> int:
    try:
        return int(headers.get("content-length") or len(content))
    except (TypeError, ValueError):
        return len(content)


def extract_timing_hint_xml(text: str) -> str:
    snippets = []
    for tag in ("ttl", "skipHours", "skipDays"):
        snippets.extend(re.findall(rf"<{tag}\b[^>]*>.*?</{tag}>", text, re.I | re.S))
    return "\n".join(snippets)


def http_error(status: int, text: str) -> str:
    body = " ".join((text or "").split())
    if len(body) > 200:
        body = body[:197] + "..."
    return f"HTTP {status}" + (f": {body}" if body else "")


def parse_retry_after(headers: dict[str, str]) -> int | None:
    value = headers.get("retry-after")
    if not value:
        return None
    value = value.strip()
    try:
        seconds = int(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        seconds = int((retry_at - datetime.now(timezone.utc)).total_seconds())
    return max(0, seconds)


def exception_result(
    *,
    url: str,
    source: Literal["primary", "fallback"],
    error: Exception,
    elapsed_ms: float,
) -> FetchResult:
    status = None
    headers: dict[str, str] = {}
    error_text = compact_error(f"{error.__class__.__name__}: {error}")
    return FetchResult(
        ok=False,
        status=status,
        url=url,
        source=source,
        headers=headers,
        error=error_text,
        elapsed_ms=elapsed_ms,
        retry_after=parse_retry_after(headers),
        content_length=0,
    )
