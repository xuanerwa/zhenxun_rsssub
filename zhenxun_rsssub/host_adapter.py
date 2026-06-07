from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import nonebot
from nonebot import logger
from nonebot.adapters.onebot.v11 import Bot

RssSceneType = Literal["private", "group", "unknown"]
_last_onebot_id: str | None = None


@dataclass(frozen=True)
class RssTarget:
    scene_type: RssSceneType
    user_id: int | None = None
    group_id: int | None = None


def get_event_target(event: object) -> RssTarget:
    """Extract the subscription target from a OneBot event."""
    group_id = getattr(event, "group_id", None)
    user_id = getattr(event, "user_id", None)
    if group_id is not None:
        return RssTarget(scene_type="group", group_id=int(group_id))
    if user_id is not None:
        return RssTarget(scene_type="private", user_id=int(user_id))
    return RssTarget(scene_type="unknown")


def is_private_event(event: object) -> bool:
    return get_event_target(event).scene_type == "private"


def is_group_event(event: object) -> bool:
    return get_event_target(event).scene_type == "group"


def remember_bot(bot: Bot) -> None:
    """Keep the last known OneBot bot for background RSS jobs."""
    global _last_onebot_id
    _last_onebot_id = bot.self_id


def resolve_onebot(bot_id: str | None = None) -> Bot | None:
    """Resolve a OneBot V11 bot without falling back to arbitrary adapters."""
    candidates: list[Bot] = []
    if bot_id:
        try:
            bot = nonebot.get_bot(bot_id)
        except KeyError:
            logger.warning(f"RSS specified Bot {bot_id} is not connected")
        else:
            if isinstance(bot, Bot):
                return bot
            logger.warning(f"RSS specified Bot {bot_id} is not OneBot V11")
            return None

    if _last_onebot_id:
        try:
            bot = nonebot.get_bot(_last_onebot_id)
        except KeyError:
            logger.warning(
                f"RSS remembered OneBot Bot {_last_onebot_id} is not connected"
            )
        else:
            if isinstance(bot, Bot):
                return bot

    for bot in nonebot.get_bots().values():
        if isinstance(bot, Bot):
            candidates.append(bot)

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        logger.warning("Multiple OneBot bots online; RSS background job skipped")
        return None
    logger.warning("No OneBot bot online; RSS background job skipped")
    return None


async def notify_superusers(bot: Bot | None, superusers: set[str], msg: str) -> None:
    """Notify superusers through OneBot private messages."""
    if bot is None:
        bot = resolve_onebot()
    if bot is None:
        logger.warning(f"Unable to notify superusers for RSS message: {msg}")
        return
    for su in superusers:
        try:
            await bot.send_private_msg(user_id=int(su), message=f"订阅姬: {msg}")
        except Exception as e:
            logger.error(f"Failed to notify RSS superuser {su}: {e}")
