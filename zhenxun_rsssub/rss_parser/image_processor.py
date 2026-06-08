import asyncio
import hashlib
from io import BytesIO
import random
import time

from nonebot import logger, require
from PIL import Image, UnidentifiedImageError
from tenacity import retry, stop_after_attempt, stop_after_delay
from yarl import URL

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

from ..globals import plugin_config
from ..http_client import get_bytes_response, get_proxy
from ..rss_message import RssImage

IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/avif",
    "image/heic",
    "image/heif",
    "image/svg+xml",
}

_download_semaphore: asyncio.Semaphore | None = None
_image_cache: dict[str, tuple[float, bytes]] = {}
_image_cache_lock = asyncio.Lock()
ACCEPT_IMAGE_ERROR_STATUS_CODES = tuple(range(400, 500))


def _download_limit() -> int:
    return max(1, int(plugin_config.media_download_concurrency or 1))


def _get_download_semaphore() -> asyncio.Semaphore:
    global _download_semaphore
    limit = _download_limit()
    if _download_semaphore is None:
        _download_semaphore = asyncio.Semaphore(limit)
    return _download_semaphore


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def _looks_like_image_url(url: str) -> bool:
    lower = url.lower()
    return any(
        lower.split("?", 1)[0].endswith(ext)
        for ext in (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".bmp",
            ".avif",
            ".heic",
            ".heif",
            ".svg",
        )
    )


def _is_valid_image_response(
    url: str, content_type: str | None, content: bytes
) -> bool:
    normalized = _normalize_content_type(content_type)
    if normalized in IMAGE_CONTENT_TYPES:
        return True
    if normalized in {"text/html", "text/plain", "application/json"}:
        return False
    # Some feeds omit Content-Type for image CDNs. Allow only if Pillow can identify it.
    if _looks_like_image_url(url):
        try:
            Image.open(BytesIO(content)).verify()
            return True
        except Exception:
            return False
    return False


async def _get_cached_image(key: str) -> bytes | None:
    async with _image_cache_lock:
        cached = _image_cache.get(key)
        if not cached:
            return None
        expires_at, content = cached
        if expires_at <= time.monotonic():
            _image_cache.pop(key, None)
            return None
        return content


async def _set_cached_image(url: str, content: bytes) -> None:
    ttl = max(0, int(plugin_config.media_cache_ttl_seconds or 0))
    if ttl <= 0:
        return
    digest_key = f"sha256:{hashlib.sha256(content).hexdigest()}"
    async with _image_cache_lock:
        max_items = max(2, int(plugin_config.media_cache_max_items or 2))
        if cached := _image_cache.get(digest_key):
            expires_at, cached_content = cached
            if expires_at > time.monotonic():
                content = cached_content
        while len(_image_cache) > max_items - 2:
            oldest = min(_image_cache, key=lambda key: _image_cache[key][0])
            _image_cache.pop(oldest, None)
        expires_at = time.monotonic() + ttl
        _image_cache[f"url:{url}"] = (expires_at, content)
        _image_cache[digest_key] = (expires_at, content)


@retry(stop=(stop_after_attempt(5) | stop_after_delay(30)))
async def download_image(url: str, use_proxy: bool) -> bytes | None:
    url = str(url)
    if cached := await _get_cached_image(f"url:{url}"):
        return cached

    referer = f"{URL(url).scheme}://{URL(url).host}/"
    headers = {"referer": referer}
    async with _get_download_semaphore():
        resp = await get_bytes_response(
            url,
            headers=headers,
            proxy=get_proxy(use_proxy),
            timeout=10,
            accept_status_codes=ACCEPT_IMAGE_ERROR_STATUS_CODES,
        )
    content = resp.content

    if resp.status >= 400:
        logger.warning(
            f"Image [{url}] download rejected. "
            f"Content-Type: {resp.headers.get('content-type')} status: {resp.status}"
        )
        return None

    if len(content) == 0:
        logger.error(
            f"Image [{url}] download failed. Content-Type: "
            f"{resp.headers.get('content-type')} status: {resp.status}"
        )
        return None

    content_type = resp.headers.get("content-type")
    if not _is_valid_image_response(url, content_type, content):
        logger.warning(
            f"Image [{url}] ignored due to invalid Content-Type: "
            f"{content_type} status: {resp.status}"
        )
        return None

    # Convert SVG through the same external image proxy used by the original code.
    if _normalize_content_type(content_type) == "image/svg+xml":
        next_url = str(
            URL("https://images.weserv.nl/").with_query(f"url={url}&output=png")
        )
        return await download_image(next_url, use_proxy)

    await _set_cached_image(url, content)
    return content


async def compress_image(
    url: URL, content: bytes, use_proxy: bool
) -> Image.Image | bytes | None:
    try:
        image = Image.open(BytesIO(content))
    except UnidentifiedImageError:
        logger.error("无法识别图像文件")
        return None

    if image.format != "GIF":
        if image.format == "WEBP":
            with BytesIO() as output:
                image.save(output, "PNG")
                output.seek(0)
                image = Image.open(output)
        # 降低图片分辨率
        image.thumbnail(
            (plugin_config.image_compress_size, plugin_config.image_compress_size)
        )
        width, height = image.size
        logger.debug(f"调整图片大小至: {width} * {height}")
        # 改变角落像素防河蟹
        points = [(0, 0), (0, height - 1), (width - 1, 0), (width - 1, height - 1)]
        for x, y in points:
            image.putpixel((x, y), random.randint(0, 255))
        return image
    else:
        if (
            plugin_config.enable_online_gif_compress
            and len(content) > plugin_config.gif_compress_size * 1024
        ):
            logger.warning("Online GIF compression was removed; send original GIF")
        return content


def save_image(dir: str, name: str, content: bytes):
    file_dir = store.get_plugin_data_dir() / dir
    file_dir.mkdir(parents=True, exist_ok=True)
    file_path = file_dir / name
    file_path.write_bytes(content)
    logger.debug(f"图片已保存至: {file_path}")


def get_image_bytes(content: Image.Image | bytes | None) -> bytes | None:
    if not content:
        return None
    if isinstance(content, Image.Image):
        with BytesIO() as output:
            content.save(output, format=content.format or "PNG")
            return output.getvalue()
    if isinstance(content, bytes):
        return content
    return None


async def get_rss_image(
    url: URL,
    use_proxy: bool,
    save: bool,
    dir: str,
    content: bytes | None = None,
    *,
    remaining_bytes: int | None = None,
) -> RssImage:
    """Download, optionally compress and save an image for later delivery."""
    missing_image_msg = f"图片走丢啦！链接：{url}"
    if not content:
        content = await download_image(url, use_proxy)
    if not content:
        return RssImage(
            url=str(url),
            name=url.name or "image.png",
            missing_text=missing_image_msg,
        )

    if remaining_bytes is not None and len(content) > remaining_bytes:
        return RssImage(
            url=str(url),
            name=url.name or "image.png",
            missing_text=f"图片超过本轮下载预算，已跳过：{url}",
            bytes_used=len(content),
        )

    if save:
        try:
            save_image(dir, url.name, content)
        except Exception as e:
            logger.warning(f"保存图片至本地时出现错误: {e}")

    compressed_content = await compress_image(url, content, use_proxy)
    if not compressed_content:
        return RssImage(
            url=str(url),
            name=url.name or "image.png",
            missing_text=missing_image_msg,
        )

    image_bytes = get_image_bytes(compressed_content)
    if not image_bytes:
        return RssImage(
            url=str(url),
            name=url.name or "image.png",
            missing_text=missing_image_msg,
        )
    return RssImage(
        raw=image_bytes,
        url=str(url),
        name=url.name or "image.png",
        bytes_used=len(content),
    )
