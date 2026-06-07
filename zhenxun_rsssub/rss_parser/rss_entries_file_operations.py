from typing import Any

from ..repository_entries import truncate_entries, write_entry


async def write_rss_entry(rss_name: str, entry: dict[str, Any]):
    await write_entry(rss_name, entry)


async def truncate_file(rss_name: str, num_new_entries: int):
    """限制 rss entries file 中条目的数量"""
    await truncate_entries(rss_name, num_new_entries)
