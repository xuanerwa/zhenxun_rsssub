from __future__ import annotations

from ..host_adapter import get_event_target
from ..rss import RSS


async def find_visible_rss(event: object, name: str) -> RSS | None:
    rss = await RSS.get_by_name(name)
    if rss is None:
        return None

    target = get_event_target(event)
    if target.scene_type == "private" and target.user_id not in rss.user_id:
        return None
    if target.scene_type == "group" and target.group_id not in rss.group_id:
        return None
    return rss


async def visible_rss_list(event: object) -> list[RSS]:
    target = get_event_target(event)
    all_rss = await RSS.load_rss_data()
    if target.scene_type == "private":
        return [rss for rss in all_rss if target.user_id in rss.user_id]
    if target.scene_type == "group":
        return [rss for rss in all_rss if target.group_id in rss.group_id]
    return []
