from html import unescape as html_unescape
import re

from bs4 import BeautifulSoup, FeatureNotFound
from yarl import URL

from ..globals import plugin_config


def _soup(html: object) -> BeautifulSoup:
    try:
        return BeautifulSoup(str(html), "lxml")
    except FeatureNotFound:
        return BeautifulSoup(str(html), "html.parser")


def _normalize_weibo_link(text: str, href: str) -> str:
    if re.search(r"https://m\.weibo\.cn/p/index\?extparam=\S+&containerid=\w+", href):
        return ""
    if (
        href.startswith("https://m.weibo.cn/search?containerid=")
        and re.search("#.+#", text)
    ) or (href.startswith("https://weibo.com/") and text.startswith("@")):
        return text
    if href.startswith("https://weibo.cn/sinaurl?u="):
        href = URL(href).query.get("u", href)
    return f" {text}: {href}\n" if text and text != href else f" {href}\n"


def _replace_links(soup: BeautifulSoup) -> None:
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        text = a.get_text(strip=True)
        a.replace_with(_normalize_weibo_link(text, href))


def _format_lists(soup: BeautifulSoup) -> None:
    for list_tag in soup.find_all(["ul", "ol"]):
        ordered = list_tag.name == "ol"
        lines = []
        for index, li in enumerate(list_tag.find_all("li", recursive=False), start=1):
            prefix = f"{index}." if ordered else "-"
            lines.append(f"{prefix} {li.get_text(' ', strip=True)}")
        list_tag.replace_with("\n" + "\n".join(lines) + "\n")

    for li in soup.find_all("li"):
        li.replace_with(f"- {li.get_text(' ', strip=True)}")


def _insert_block_breaks(soup: BeautifulSoup) -> None:
    for br in soup.find_all(["br", "hr"]):
        br.replace_with("\n")
    for tag in soup.find_all(["p", "pre"]):
        tag.append("\n\n")
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        tag.insert_before("\n")
        tag.append("\n")


def _remove_ignored_tags(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["img", "video", "iframe"]):
        tag.decompose()
    if not plugin_config.blockquote:
        for tag in soup.find_all("blockquote"):
            tag.decompose()


def _clean_text(text: str) -> str:
    text = html_unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    text = text.strip()
    if 0 < plugin_config.max_length < len(text):
        text = f"{text[: plugin_config.max_length]}..."
    return text


def handle_html_tags(html: object) -> str:
    soup = _soup(html)
    _remove_ignored_tags(soup)
    _replace_links(soup)
    _format_lists(soup)
    _insert_block_breaks(soup)
    return _clean_text(soup.get_text())


def extract_image_urls(html: str) -> list[str]:
    soup = _soup(html)
    return [src for img in soup.find_all("img") if (src := img.get("src"))]


def extract_video_poster_urls(html: str) -> list[str]:
    soup = _soup(html)
    return [
        poster for video in soup.find_all("video") if (poster := video.get("poster"))
    ]


def html_text(html: str, *, remove_blockquote: bool = False) -> str:
    soup = _soup(html)
    if remove_blockquote:
        for tag in soup.find_all("blockquote"):
            tag.decompose()
    return soup.get_text()
