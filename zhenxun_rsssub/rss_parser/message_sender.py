from __future__ import annotations

from nonebot.adapters import Bot

from ..delivery import DeliveryResult
from ..delivery import send_message as deliver_message
from ..rss_message import RssMessage


async def send_message(
    user_id: set[int],
    group_id: set[int],
    message: RssMessage | list[RssMessage],
    *,
    bot: Bot | None = None,
    reply_to: dict[tuple[str, int], str] | None = None,
) -> list[DeliveryResult]:
    return await deliver_message(user_id, group_id, message, bot=bot, reply_to=reply_to)
