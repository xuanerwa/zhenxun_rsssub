from __future__ import annotations

from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from .rss import RSS

OPML_VERSION = "2.0"


def _xml_url(rss: RSS) -> str:
    return str(rss.url)


def _outline_attrs(rss: RSS) -> dict[str, str]:
    url = _xml_url(rss)
    attrs = {
        "text": rss.name,
        "title": rss.name,
        "type": "rss",
        "xmlUrl": url,
    }
    if rss.last_fetch_result.get("url"):
        attrs["htmlUrl"] = str(rss.last_fetch_result["url"])
    return attrs


def _format_attrs(attrs: dict[str, str]) -> str:
    quote_entities = {'"': "&quot;"}
    return " ".join(
        f'{key}="{escape(value, quote_entities)}"'
        for key, value in attrs.items()
        if value
    )


def export_opml(rss_list: list[RSS]) -> str:
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<opml version="{OPML_VERSION}">',
        "  <head>",
        "    <title>zhenxun_rsssub subscriptions</title>",
        f"    <dateCreated>{now}</dateCreated>",
        "  </head>",
        "  <body>",
    ]
    for rss in rss_list:
        lines.append(f"    <outline {_format_attrs(_outline_attrs(rss))} />")
    lines.extend(["  </body>", "</opml>"])
    return "\n".join(lines)


def import_opml(text: str) -> tuple[list[dict[str, str]], list[str]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return [], [f"OPML 解析失败：{e}"]
    if root.tag.lower() != "opml":
        return [], ["OPML 根节点必须是 <opml>"]

    feeds: list[dict[str, str]] = []
    errors: list[str] = []
    for index, outline in enumerate(root.findall(".//outline"), 1):
        xml_url = outline.attrib.get("xmlUrl") or outline.attrib.get("xmlurl")
        if not xml_url:
            continue
        name = (
            outline.attrib.get("title")
            or outline.attrib.get("text")
            or outline.attrib.get("description")
            or xml_url
        )
        record = {"name": name.strip(), "url": xml_url.strip()}
        if not record["name"] or not record["url"]:
            errors.append(f"第 {index} 个 outline 缺少 name 或 xmlUrl")
            continue
        feeds.append(record)
    if not feeds and not errors:
        errors.append("OPML 中没有找到包含 xmlUrl 的订阅")
    return feeds, errors


def looks_like_opml(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("<opml") or "<opml" in stripped[:200].lower()
