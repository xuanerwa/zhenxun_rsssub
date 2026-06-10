from __future__ import annotations

from nonebot.adapters import Bot, Event
from nonebot.internal.rule import Rule
from nonebot.permission import SUPERUSER
from nonebot_plugin_uninfo import Uninfo

from zhenxun.models.level_user import LevelUser
from zhenxun.utils.platform import PlatformUtils

from .host_adapter import get_event_target
from .runtime_config import get_cached_config


def _group_whitelist() -> set[str]:
    return {str(group_id) for group_id in get_cached_config("group_whitelist")}


def is_group_allowed(group_id: int | str | None) -> bool:
    if group_id is None:
        return False
    if not get_cached_config("group_whitelist_enabled"):
        return True
    whitelist = _group_whitelist()
    return str(group_id) in whitelist


def rss_command_rule(level: int = 5) -> Rule:
    async def _rule(bot: Bot, event: Event, session: Uninfo) -> bool:
        if await SUPERUSER(bot, event):
            target = get_event_target(event)
            return target.scene_type != "group" or is_group_allowed(target.group_id)

        if PlatformUtils.is_qbot(session):
            return False

        target = get_event_target(event)
        if target.scene_type == "private":
            return not get_cached_config("private_subscribe_superuser_only")

        if target.scene_type == "group":
            if not is_group_allowed(target.group_id):
                return False
            return bool(
                await LevelUser.check_level(
                    session.user.id, str(target.group_id), level
                )
            )

        return False

    return Rule(_rule)
