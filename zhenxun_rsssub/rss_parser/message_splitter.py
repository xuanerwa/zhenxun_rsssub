from __future__ import annotations

import re

from ..rss_message import RssMessage


def text_length(text: str) -> int:
    return len(text)


def _join_parts(parts: list[str], separator: str = "") -> str:
    return separator.join(part for part in parts if part)


def truncate_text(text: str, limit: int) -> str:
    if limit <= 0 or text_length(text) <= limit:
        return text
    return f"{text[:limit]}..."


def truncate_message_text(message: RssMessage, limit: int) -> RssMessage:
    if limit <= 0:
        return message
    return RssMessage(
        text=truncate_text(message.text, limit),
        images=list(message.images),
        videos=list(message.videos),
        link=message.link,
        nodes=list(message.nodes),
    )


def _split_by_length(text: str, limit: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for char in text:
        if current and current_size + 1 > limit:
            chunks.append("".join(current))
            current = [char]
            current_size = 1
        else:
            current.append(char)
            current_size += 1
    if current:
        chunks.append("".join(current))
    return chunks


def _split_long_line(line: str, limit: int) -> list[str]:
    if text_length(line) <= limit:
        return [line]
    if line.isspace():
        return _split_by_length(line, limit)

    sentence_parts = [part for part in re.split(r"(?<=[。！？!?；;])", line) if part]
    if len(sentence_parts) > 1:
        return _pack_units(sentence_parts, limit, "")

    space_parts = re.split(r"(\s+)", line)
    if len([part for part in space_parts if part]) > 1:
        return _pack_units(space_parts, limit, "")

    return _split_by_length(line, limit)


def _pack_units(units: list[str], limit: int, separator: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for unit in units:
        if not unit:
            continue
        pieces = [unit]
        if text_length(unit) > limit:
            pieces = (
                _split_long_line(unit, limit)
                if "\n" not in unit
                else _split_long_block(unit, limit)
            )
        for piece in pieces:
            candidate = _join_parts([*current, piece], separator)
            if current and text_length(candidate) > limit:
                chunks.append(_join_parts(current, separator).strip())
                current = [piece]
            else:
                current.append(piece)
    if current:
        chunks.append(_join_parts(current, separator).strip())
    return [chunk for chunk in chunks if chunk]


def _split_long_block(block: str, limit: int) -> list[str]:
    lines = block.splitlines()
    if len(lines) <= 1:
        return _split_long_line(block, limit)
    split_lines: list[str] = []
    for line in lines:
        split_lines.extend(_split_long_line(line, limit))
    return _pack_units(split_lines, limit, "\n")


def split_text_by_length(text: str, limit: int) -> list[str]:
    if limit <= 0 or text_length(text) <= limit:
        return [text] if text else []

    paragraphs = re.split(r"\n{2,}", text)
    chunks = _pack_units(paragraphs, limit, "\n\n")
    result: list[str] = []
    for chunk in chunks:
        if text_length(chunk) <= limit:
            result.append(chunk)
        else:
            result.extend(_split_long_block(chunk, limit))
    return result


def build_split_forward_messages(title: str, message: RssMessage, limit: int) -> list[RssMessage] | None:
    if limit <= 0:
        return None

    titled_message = RssMessage(
        text=(f"{title}\n\n{message.text}" if title and message.text else title or message.text),
        images=list(message.images),
        videos=list(message.videos),
        link=message.link,
        nodes=list(message.nodes),
    )
    if text_length(titled_message.plain_text()) <= limit:
        return None

    chunks = split_text_by_length(message.text, limit)
    nodes = [RssMessage(text=title)] if title else []
    for index, chunk in enumerate(chunks):
        nodes.append(
            RssMessage(
                text=chunk,
                images=list(message.images) if index == 0 else [],
                videos=list(message.videos) if index == 0 else [],
                link=message.link if index == len(chunks) - 1 else "",
                nodes=list(message.nodes) if index == 0 else [],
            )
        )
    if not chunks and (message.images or message.videos or message.link):
        nodes.append(
            RssMessage(
                images=list(message.images),
                videos=list(message.videos),
                link=message.link,
                nodes=list(message.nodes),
            )
        )
    return nodes if len(nodes) >= 2 else None
