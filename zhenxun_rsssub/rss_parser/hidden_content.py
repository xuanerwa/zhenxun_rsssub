from __future__ import annotations

import re

from bs4 import BeautifulSoup, NavigableString, Tag

HIDDEN_CLASS_KEYWORDS = {
    "blur",
    "blured",
    "blurred",
    "spoiler",
    "is-spoiler",
    "has-spoiler",
    "tg-spoiler",
    "tgme-spoiler",
    "telegram-spoiler",
    "hidden",
    "sensitive",
    "content-warning",
    "content_warning",
}

HIDDEN_ATTRS = {
    "data-spoiler",
    "data-media-spoiler",
    "data-sensitive",
    "data-hidden",
    "aria-hidden",
}

HIDDEN_TEXT_MARKERS = (
    "（spoiler）",
    "(spoiler)",
    "[spoiler]",
    "spoiler",
    "spolier",
)

SPOILER_TEXT_RE = re.compile(r"\bspo(?:iler|lier)\b", re.I)

HIDDEN_CONTENT_PLACEHOLDER = "隐藏内容已折叠，开启隐藏内容显示后可查看。"
HIDDEN_IMAGE_PLACEHOLDER = "隐藏图片已折叠，开启隐藏内容显示后可查看。"
HIDDEN_VIDEO_PLACEHOLDER = "隐藏视频已折叠，开启隐藏内容显示后可查看。"
HIDDEN_MEDIA_PLACEHOLDER = "隐藏媒体已折叠，开启隐藏内容显示后可查看。"


def _classes(tag: Tag) -> set[str]:
    raw_classes = tag.get("class") or []
    if isinstance(raw_classes, str):
        raw_classes = raw_classes.split()
    return {str(item).strip().lower() for item in raw_classes if str(item).strip()}


def is_hidden_tag(tag: Tag) -> bool:
    classes = _classes(tag)
    if any(keyword in classes for keyword in HIDDEN_CLASS_KEYWORDS):
        return True
    if any(
        any(keyword in class_name for keyword in HIDDEN_CLASS_KEYWORDS)
        for class_name in classes
    ):
        return True
    for attr in HIDDEN_ATTRS:
        value = tag.get(attr)
        if value is None:
            continue
        if str(value).lower() not in {"false", "0", "none", ""}:
            return True
    style = str(tag.get("style") or "").lower()
    if "filter" in style and "blur" in style:
        return True
    title = str(tag.get("title") or tag.get("alt") or "").lower()
    return "spoiler" in title or "sensitive" in title


def _line_is_spoiler_marker(line: str) -> bool:
    return bool(SPOILER_TEXT_RE.search(line))


def _placeholder_text(*, image_count: int = 0, video_count: int = 0) -> str:
    if video_count and image_count:
        return HIDDEN_MEDIA_PLACEHOLDER
    if video_count:
        return HIDDEN_VIDEO_PLACEHOLDER
    if image_count:
        return HIDDEN_IMAGE_PLACEHOLDER
    return HIDDEN_CONTENT_PLACEHOLDER


def _count_hidden_media(tag: Tag) -> tuple[int, int]:
    image_count = len(tag.find_all("img"))
    video_tags = tag.find_all("video")
    video_count = len(video_tags)
    image_count = max(0, image_count - sum(len(video.find_all("img")) for video in video_tags))
    if tag.name == "img":
        image_count += 1
    elif tag.name == "video":
        video_count += 1
    text = tag.get_text(" ", strip=True).lower()
    if image_count and ("video" in text or "视频" in text):
        video_count += 1
        image_count = max(0, image_count - 1)
    return image_count, video_count


def _replace_with_placeholder(tag: Tag) -> None:
    image_count, video_count = _count_hidden_media(tag)
    tag.replace_with(NavigableString(f"\n{_placeholder_text(image_count=image_count, video_count=video_count)}\n"))


def _collapse_spoiler_marker_sections(soup: BeautifulSoup) -> bool:
    for tag in list(soup.find_all(["p", "div", "blockquote"])):
        text = tag.get_text("\n", strip=True)
        lines = text.splitlines()
        marker_index = next(
            (index for index, line in enumerate(lines) if _line_is_spoiler_marker(line)),
            None,
        )
        if marker_index is None:
            continue

        image_count, video_count = _count_hidden_media(tag)
        sibling = tag.next_sibling
        while sibling is not None:
            next_sibling = sibling.next_sibling
            if isinstance(sibling, Tag):
                sibling_images, sibling_videos = _count_hidden_media(sibling)
                image_count += sibling_images
                video_count += sibling_videos
                sibling.decompose()
            elif isinstance(sibling, NavigableString):
                sibling.extract()
            sibling = next_sibling

        visible_lines = [line for line in lines[:marker_index] if line.strip()]
        visible_text = "\n".join(visible_lines)
        placeholder = _placeholder_text(
            image_count=image_count, video_count=video_count
        )
        replacement = f"{visible_text}\n{placeholder}" if visible_text else placeholder
        tag.replace_with(NavigableString(f"\n{replacement}\n"))
        return True
    return False


def remove_hidden_content(soup: BeautifulSoup) -> bool:
    removed = False
    for tag in list(soup.find_all(True)):
        if is_hidden_tag(tag):
            _replace_with_placeholder(tag)
            removed = True
    if _collapse_spoiler_marker_sections(soup):
        removed = True
    return removed


def has_spoiler_text(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in HIDDEN_TEXT_MARKERS) or bool(
        SPOILER_TEXT_RE.search(text)
    )
