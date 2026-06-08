from __future__ import annotations

import asyncio
import base64
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Literal

from nonebot import logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot_plugin_alconna import FallbackStrategy, Target, UniMessage

from .globals import global_config
from .host_adapter import resolve_onebot
from .rss_message import RssImage, RssMessage

sending_lock: defaultdict[tuple[int, str], asyncio.Lock] = defaultdict(asyncio.Lock)


@dataclass(slots=True)
class DeliveryTarget:
    target_type: Literal["private", "group"]
    target_id: int


@dataclass(slots=True)
class DeliveryResult:
    target_type: Literal["private", "group"]
    target_id: int
    status: Literal["success", "failed"]
    error: str | None = None
    message_id: str | None = None
    time: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def to_record(self, *, feed_name: str, entry_hash: str) -> dict[str, str | None]:
        return {
            "feed_name": feed_name,
            "entry_hash": entry_hash,
            "target_type": self.target_type,
            "target_id": str(self.target_id),
            "status": self.status,
            "error": self.error,
            "message_id": self.message_id,
            "time": self.time,
        }


def build_delivery_targets(
    user_id: set[int], group_id: set[int]
) -> list[DeliveryTarget]:
    targets = [DeliveryTarget("private", uid) for uid in sorted(user_id)]
    targets.extend(DeliveryTarget("group", gid) for gid in sorted(group_id))
    return targets


def delivery_result(
    target: DeliveryTarget,
    *,
    status: Literal["success", "failed"],
    error: str | None = None,
    message_id: str | None = None,
) -> DeliveryResult:
    return DeliveryResult(
        target_type=target.target_type,
        target_id=target.target_id,
        status=status,
        error=error,
        message_id=message_id,
        time=datetime.now(timezone.utc).isoformat(),
    )


async def send_onebot_message_with_lock(
    bot: Bot,
    target_id: int,
    target_type: Literal["private", "group"],
    msg: Message,
) -> DeliveryResult:
    start_time = time.monotonic()
    target = DeliveryTarget(target_type, target_id)
    async with sending_lock[(target_id, target_type)]:
        try:
            response = await bot.send_msg(
                message_type=target_type,
                user_id=target_id,
                group_id=target_id,
                message=msg,
            )
        except Exception as e:
            logger.error(
                f"Failed to send RSS message to {target_type}({target_id}): {e}"
            )
            result = delivery_result(target, status="failed", error=str(e))
        else:
            message_id = None
            if isinstance(response, dict):
                raw_message_id = response.get("message_id")
                message_id = str(raw_message_id) if raw_message_id is not None else None
            result = delivery_result(
                target,
                status="success",
                message_id=message_id,
            )
        finally:
            await asyncio.sleep(max(0, 1.5 - (time.monotonic() - start_time)))
    return result


def _image_to_onebot_segment(image: RssImage) -> MessageSegment | str:
    if image.raw:
        encoded = base64.b64encode(image.raw).decode()
        return MessageSegment.image(f"base64://{encoded}")
    if image.url:
        return MessageSegment.image(image.url)
    return image.missing_text


def build_onebot_message(bot: Bot, message: RssMessage | list[RssMessage]) -> Message:
    """Build a OneBot message or custom forward message."""
    if isinstance(message, RssMessage):
        return build_onebot_single_message(message)
    return Message(
        [
            MessageSegment.node_custom(
                int(bot.self_id),
                next(iter(global_config.nickname))
                if global_config.nickname
                else "\u200b",
                content=build_onebot_single_message(m),
            )
            for m in message
        ]
    )


def build_onebot_single_message(message: RssMessage) -> Message:
    result = Message()
    if message.text:
        result += MessageSegment.text(message.text)
    if message.link:
        result += MessageSegment.text("\n" + message.link)
    for image in message.images:
        segment = _image_to_onebot_segment(image)
        if isinstance(segment, MessageSegment):
            result += segment
        elif segment:
            result += MessageSegment.text("\n" + segment)
    return result


def build_uni_message(message: RssMessage) -> UniMessage:
    result = UniMessage()
    if message.text:
        result.append(message.text)
    if message.link:
        result.append("\n" + message.link)
    for image in message.images:
        if image.raw:
            result.image(raw=image.raw, name=image.name)
        elif image.url:
            result.image(url=image.url, name=image.name)
        elif image.missing_text:
            result.append("\n" + image.missing_text)
    return result


async def send_message(
    user_id: set[int],
    group_id: set[int],
    message: RssMessage | list[RssMessage],
    *,
    bot: BaseBot | None = None,
) -> list[DeliveryResult]:
    bot = bot or resolve_onebot()
    if bot is None:
        return [
            delivery_result(target, status="failed", error="no available bot")
            for target in build_delivery_targets(user_id, group_id)
        ]

    if isinstance(bot, Bot):
        return await send_onebot_message(user_id, group_id, message, bot)
    return await send_uni_message(user_id, group_id, message, bot)


async def send_onebot_message(
    user_id: set[int],
    group_id: set[int],
    message: RssMessage | list[RssMessage],
    bot: Bot,
) -> list[DeliveryResult]:
    wrapped_msg = build_onebot_message(bot, message)
    results: list[DeliveryResult] = []
    if user_id:
        results.extend(
            await asyncio.gather(
                *(
                    send_onebot_message_with_lock(bot, uid, "private", wrapped_msg)
                    for uid in user_id
                )
            )
        )
    if group_id:
        results.extend(
            await asyncio.gather(
                *(
                    send_onebot_message_with_lock(bot, gid, "group", wrapped_msg)
                    for gid in group_id
                )
            )
        )
    return results


async def _send_uni_to_target(
    bot: BaseBot,
    target_id: int,
    target_type: Literal["private", "group"],
    message: RssMessage,
) -> DeliveryResult:
    start_time = time.monotonic()
    delivery_target = DeliveryTarget(target_type, target_id)
    async with sending_lock[(target_id, f"uni:{target_type}")]:
        try:
            target = Target(
                id=str(target_id),
                private=target_type == "private",
                channel=target_type == "group",
            )
            await build_uni_message(message).send(
                target=target,
                bot=bot,
                fallback=FallbackStrategy.rollback,
            )
        except Exception as e:
            logger.error(
                f"Failed to send RSS UniMessage to {target_type}({target_id}): {e}"
            )
            return delivery_result(delivery_target, status="failed", error=str(e))
        finally:
            await asyncio.sleep(max(0, 1.5 - (time.monotonic() - start_time)))
    return delivery_result(delivery_target, status="success")


async def send_uni_message(
    user_id: set[int],
    group_id: set[int],
    message: RssMessage | list[RssMessage],
    bot: BaseBot,
) -> list[DeliveryResult]:
    messages = message if isinstance(message, list) else [message]
    results: list[DeliveryResult] = []
    for msg in messages:
        if user_id:
            results.extend(
                await asyncio.gather(
                    *(_send_uni_to_target(bot, uid, "private", msg) for uid in user_id)
                )
            )
        if group_id:
            results.extend(
                await asyncio.gather(
                    *(_send_uni_to_target(bot, gid, "group", msg) for gid in group_id)
                )
            )
    return results
