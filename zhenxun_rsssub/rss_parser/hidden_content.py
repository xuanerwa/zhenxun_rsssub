from __future__ import annotations

from bs4 import BeautifulSoup, Tag

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
)


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


def remove_hidden_content(soup: BeautifulSoup) -> bool:
    removed = False
    for tag in list(soup.find_all(True)):
        if is_hidden_tag(tag):
            tag.decompose()
            removed = True
    return removed


def has_spoiler_text(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in HIDDEN_TEXT_MARKERS)
