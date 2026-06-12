from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import tempfile

from nonebot import logger
from yarl import URL
from zhenxun.utils.http_utils import AsyncHttpx

from ..globals import plugin_config
from ..runtime_config import get_cached_config
from ..rss_message import RssVideo
from .image_processor import _get_download_semaphore

VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-m4v",
    "video/x-matroska",
}

ACCEPT_VIDEO_ERROR_STATUS_CODES = tuple(range(400, 500))
ISO_DURATION_RE = re.compile(
    r"^P(?:\d+D)?T?"
    r"(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?$",
    re.I,
)


def _media_proxy() -> str | None:
    media_proxy = getattr(plugin_config, "media_proxy", None)
    if media_proxy:
        return str(media_proxy)
    return None


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def _looks_like_video_url(url: str) -> bool:
    lower = url.lower().split("?", 1)[0]
    return lower.endswith((".mp4", ".webm", ".mov", ".m4v", ".mkv"))


def _is_valid_video_response(
    url: str, content_type: str | None, content: bytes
) -> bool:
    normalized = _normalize_content_type(content_type)
    if normalized in VIDEO_CONTENT_TYPES or normalized.startswith("video/"):
        return True
    if normalized in {"text/html", "text/plain", "application/json"}:
        return False
    return _looks_like_video_url(url) and bool(content)


def _duration_from_attrs(raw_duration: str | None) -> float | None:
    if not raw_duration:
        return None
    value = raw_duration.strip()
    if not value:
        return None
    value = value.strip()
    lowered = value.lower()
    if lowered.endswith("ms"):
        try:
            return float(value[:-2]) / 1000
        except ValueError:
            return None
    if lowered.endswith("s"):
        value = value[:-1]
    try:
        return float(value)
    except ValueError:
        pass
    if match := ISO_DURATION_RE.match(raw_duration.strip()):
        hours = float(match.group("hours") or 0)
        minutes = float(match.group("minutes") or 0)
        seconds = float(match.group("seconds") or 0)
        return hours * 3600 + minutes * 60 + seconds
    parts = value.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return float(seconds)


def _format_duration_minutes(duration_seconds: float) -> float:
    return round(duration_seconds / 60, 1)


def _duration_limit_message(duration_seconds: float, max_minutes: int, url: URL) -> str:
    return (
        f"视频时长 {_format_duration_minutes(duration_seconds)} 分钟"
        f"超过限制 {max_minutes} 分钟，已跳过：{url}"
    )


def _check_duration(
    duration_seconds: float | None, max_minutes: int, url: URL
) -> str | None:
    if max_minutes <= 0 or duration_seconds is None:
        return None
    if duration_seconds > max_minutes * 60:
        return _duration_limit_message(duration_seconds, max_minutes, url)
    return None


def _probe_video_duration(content: bytes, suffix: str) -> float | None:
    if not shutil.which("ffprobe"):
        return None
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(content)
            temp_path = temp.name
        output = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                temp_path,
            ],
            stderr=subprocess.STDOUT,
            timeout=8,
            text=True,
        )
        return float(output.strip())
    except Exception as e:
        logger.debug(f"视频时长探测失败: {e}")
        return None
    finally:
        if temp_path:
            try:
                import os

                os.unlink(temp_path)
            except OSError:
                pass


def _video_name(url: URL) -> str:
    name = url.name or "video.mp4"
    return name if "." in name else f"{name}.mp4"


async def download_video(url: str, use_proxy: bool) -> tuple[bytes | None, str | None]:
    url = str(url)
    referer = f"{URL(url).scheme}://{URL(url).host}/"
    headers = {"referer": referer}
    async with _get_download_semaphore():
        request_kwargs = {
            "headers": headers,
            "timeout": max(1, int(get_cached_config("media_download_timeout_seconds") or 8)),
            "accept_status_codes": ACCEPT_VIDEO_ERROR_STATUS_CODES,
        }
        if proxy := _media_proxy():
            request_kwargs["proxy"] = proxy
        else:
            request_kwargs["use_proxy"] = use_proxy
        resp = await AsyncHttpx.get(url, **request_kwargs)

    content = resp.content
    content_type = resp.headers.get("content-type")
    if resp.status_code >= 400:
        logger.warning(
            f"Video [{url}] download rejected. "
            f"Content-Type: {content_type} status: {resp.status_code}"
        )
        return None, content_type
    if not content:
        logger.warning(f"Video [{url}] download failed: empty content")
        return None, content_type
    if not _is_valid_video_response(url, content_type, content):
        logger.warning(
            f"Video [{url}] ignored due to invalid Content-Type: "
            f"{content_type} status: {resp.status_code}"
        )
        return None, content_type
    return content, content_type


async def get_rss_video(
    url: URL,
    use_proxy: bool,
    *,
    duration_seconds: float | None = None,
    remaining_bytes: int | None = None,
) -> RssVideo:
    missing_text = f"视频下载失败，已跳过：{url}"
    max_minutes = int(get_cached_config("video_download_max_minutes") or 0)
    if message := _check_duration(duration_seconds, max_minutes, url):
        return RssVideo(
            url=str(url),
            name=_video_name(url),
            missing_text=message,
            failed=True,
        )

    try:
        content, content_type = await download_video(str(url), use_proxy)
    except asyncio.TimeoutError:
        return RssVideo(
            url=str(url),
            name=_video_name(url),
            missing_text=f"视频下载超时，已跳过：{url}",
            failed=True,
        )
    except Exception as e:
        logger.warning(f"视频下载失败，已跳过: {url} ({e})")
        return RssVideo(
            url=str(url), name=_video_name(url), missing_text=missing_text, failed=True
        )

    if not content:
        return RssVideo(
            url=str(url), name=_video_name(url), missing_text=missing_text, failed=True
        )

    if remaining_bytes is not None and len(content) > remaining_bytes:
        return RssVideo(
            url=str(url),
            name=_video_name(url),
            missing_text=f"视频超过本轮下载预算，已跳过：{url}",
            bytes_used=len(content),
            failed=True,
        )

    if max_minutes > 0 and duration_seconds is None:
        probed = _probe_video_duration(content, URL(url).suffix or ".mp4")
        if message := _check_duration(probed, max_minutes, url):
            return RssVideo(
                url=str(url),
                name=_video_name(url),
                missing_text=message,
                bytes_used=len(content),
                failed=True,
            )

    mimetype = _normalize_content_type(content_type) or "video/mp4"
    return RssVideo(
        raw=content,
        url=str(url),
        name=_video_name(url),
        bytes_used=len(content),
        mimetype=mimetype,
    )


def parse_duration(value: str | None) -> float | None:
    return _duration_from_attrs(value)


def looks_like_video_url(url: str) -> bool:
    return _looks_like_video_url(url)
