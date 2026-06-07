from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
from typing import TYPE_CHECKING

from nonebot import logger
from yarl import URL

if TYPE_CHECKING:
    from ..rss import RSS

from ..globals import plugin_config
from ..rss_message import RssImage
from ..utils import get_entry_datetime
from .context import Context
from .html_document_processor import (
    extract_image_urls,
    extract_video_poster_urls,
    handle_html_tags,
    html_text,
)
from .image_processor import get_rss_image
from .rss_parser import ParsingHandlerManager
from .utils import get_summary


def _remaining_media_bytes(ctx: Context) -> int | None:
    limit = int(plugin_config.max_media_bytes_per_update or 0)
    if limit <= 0:
        return None
    return max(0, limit - ctx.media_bytes_used)


async def _append_rss_image(
    ctx: Context, rss: "RSS", url: URL, content: bytes | None = None
):
    remaining_bytes = _remaining_media_bytes(ctx)
    if remaining_bytes is not None and remaining_bytes <= 0:
        ctx.msg_image_buffer.append(
            RssImage(
                url=str(url),
                name=url.name or "image.png",
                missing_text=f"media download budget exhausted, skipped: {url}",
            )
        )
        return

    image = await get_rss_image(
        url,
        rss.use_proxy,
        rss.download_pic,
        rss.sanitized_name,
        content,
        remaining_bytes=remaining_bytes,
    )
    if image.bytes_used:
        ctx.media_bytes_used += image.bytes_used
    elif image.raw:
        ctx.media_bytes_used += len(image.raw)
    ctx.msg_image_buffer.append(image)


@ParsingHandlerManager.process_handler(priority=0)
async def validate_entry(ctx: Context, rss: "RSS"):
    """检查当前处理的文章是否有效"""
    if not ctx.entry:
        logger.error(f"[{rss.name}]未能正确装填待处理的文章，终止后续处理")
        ctx.continue_process = False


@ParsingHandlerManager.process_handler(priority=20)
async def handle_entry_title(ctx: Context, rss: "RSS"):
    """处理文章标题"""
    if rss.only_feed_pic:
        # 仅推送图片模式下不处理标题
        return

    entry = ctx.entry

    entry_title = entry.get("title", "无标题")
    if not plugin_config.blockquote:
        entry_title = re.sub(r" - 转发 .*", "", entry_title)

    entry_title = "标题：" + entry_title

    if rss.only_feed_title:
        ctx.msg_text_buffer += entry_title
        return

    # 判断标题与正文的相似度，避免标题正文一样，或者标题为正文前缀等情况
    try:
        summary_text = html_text(
            get_summary(entry), remove_blockquote=not plugin_config.blockquote
        )
        similarity = SequenceMatcher(
            None, summary_text[: len(entry_title)], entry_title
        )
        if similarity.ratio() > 0.6:
            # 标题与正文相似时取消显示标题
            entry_title = ""
    except Exception as e:
        logger.warning(f"[{rss.name}]没有正文内容: {e}")

    ctx.msg_text_buffer += entry_title


@ParsingHandlerManager.process_handler(priority=40)
async def handle_images(ctx: Context, rss: "RSS"):
    """处理文章图片"""
    if rss.only_feed_title:
        # 仅推送标题模式下不处理图片
        return

    if rss.only_feed_pic:
        # 仅推送图片模式下不推送文本
        ctx.msg_text_buffer = ""

    entry = ctx.entry

    if entry.get("image_content"):
        await _append_rss_image(
            ctx,
            rss,
            URL(entry.get("gif_url", "")),
            entry["image_content"],
        )
        return

    summary = get_summary(entry)
    entry_images = extract_image_urls(summary)
    if 0 < rss.max_image_number < len(entry_images):
        ctx.msg_text_buffer += (
            f"图片数量限制已启用，仅显示 {rss.max_image_number} 张图片\n"
        )
        entry_images = entry_images[: rss.max_image_number]
    for url in entry_images:
        await _append_rss_image(ctx, rss, URL(url))

    # 处理视频
    video_posters = extract_video_poster_urls(summary)
    if video_posters:
        ctx.msg_text_buffer += "\n视频封面："
        for url in video_posters:
            await _append_rss_image(ctx, rss, URL(url))


@ParsingHandlerManager.process_handler(priority=49)
async def decide_whether_handle_summary(ctx: Context, rss: "RSS"):
    """决定是否处理正文"""
    if rss.only_feed_title or rss.only_feed_pic:
        ctx.continue_process = False


@ParsingHandlerManager.process_handler()
async def handle_summary(ctx: Context, rss: "RSS"):
    """处理文章正文"""
    entry = ctx.entry

    try:
        article = handle_html_tags(get_summary(entry))
    except Exception as e:
        logger.warning(f"[{rss.name}]处理正文时出错: {e}")

    ctx.msg_text_buffer += "\n\n" + article


@ParsingHandlerManager.process_handler(priority=60)
async def remove_unwanted_content(ctx: Context, rss: "RSS"):
    """移除指定内容"""
    article = ctx.msg_text_buffer
    if rss.content_to_remove:
        for pattern in rss.content_to_remove:
            article = re.sub(pattern, "", article)
        # 去除多余换行
        while "\n\n\n" in article:
            article = article.replace("\n\n\n", "\n\n")
        article = article.strip()

    ctx.msg_text_buffer = article


@ParsingHandlerManager.process_handler(priority=70)
async def note_link(ctx: Context, rss: "RSS"):
    """添加文章链接"""
    ctx.msg_text_buffer += f"\n\n链接：{ctx.entry.get('link', '无链接')}"


@ParsingHandlerManager.process_handler(priority=71)
async def note_datetime(ctx: Context, rss: "RSS"):
    """添加文章时间"""
    entry_datetime = get_entry_datetime(ctx.entry)
    now = datetime.now(entry_datetime.tzinfo or timezone.utc)
    if entry_datetime <= now:
        entry_datetime = entry_datetime.astimezone()
    ctx.msg_text_buffer += f"\n日期：{entry_datetime:%Y年%m月%d日 %H:%M:%S}"
