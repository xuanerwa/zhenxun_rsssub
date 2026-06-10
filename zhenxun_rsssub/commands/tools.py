from __future__ import annotations

from nonebot.adapters import Bot, Event
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import Arparma

from ..access_control import is_group_allowed
from ..host_adapter import get_event_target
from ..host_adapter import RssTarget
from ..rss import RSS


class TargetResolveError(Exception):
    pass


def option_group_id(result: Arparma | None, subcommand: str) -> str | None:
    if result is None:
        return None
    value = result.query(f"{subcommand}.group.group_id")
    return str(value) if value is not None else None


async def resolve_command_target(
    bot: Bot,
    event: Event,
    group_id: str | None = None,
) -> RssTarget | None:
    """Resolve the current subscription target.

    Superusers may pass ``-g/--group`` to manage another group. Normal users are
    scoped to the current event target by the command rule.
    """
    if group_id:
        if not await SUPERUSER(bot, event):
            raise TargetResolveError("❌ 只有超级用户可以指定群组")
        if not is_group_allowed(group_id):
            raise TargetResolveError("❌ 该群不在订阅姬群白名单中")
        return RssTarget(scene_type="group", group_id=int(group_id))
    return get_event_target(event)


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


async def find_target_rss(target: RssTarget, name: str) -> RSS | None:
    rss = await RSS.get_by_name(name)
    if rss is None:
        return None
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


async def target_rss_list(target: RssTarget) -> list[RSS]:
    all_rss = await RSS.load_rss_data()
    if target.scene_type == "private":
        return [rss for rss in all_rss if target.user_id in rss.user_id]
    if target.scene_type == "group":
        return [rss for rss in all_rss if target.group_id in rss.group_id]
    return []
