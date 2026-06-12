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
from nonebot_plugin_alconna import FallbackStrategy, UniMessage

from zhenxun.utils.platform import PlatformUtils

from .globals import global_config
from .host_adapter import resolve_onebot
from .rss_message import RssImage, RssMessage, RssVideo
from .runtime_config import get_cached_config

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


def _send_timeout_seconds() -> int:
    value = get_cached_config("message_send_timeout_seconds")
    return max(1, int(value or 12))


def _reply_message_id(
    reply_to: dict[tuple[str, int], str] | None,
    target_type: Literal["private", "group"],
    target_id: int,
) -> str | None:
    return (reply_to or {}).get((target_type, target_id))


async def send_onebot_message_with_lock(
    bot: Bot,
    target_id: int,
    target_type: Literal["private", "group"],
    msg: Message,
    *,
    reply_to_message_id: str | None = None,
) -> DeliveryResult:
    start_time = time.monotonic()
    target = DeliveryTarget(target_type, target_id)

    async def _send(current_message: Message):
        return await bot.send_msg(
            message_type=target_type,
            user_id=target_id,
            group_id=target_id,
            message=current_message,
        )

    async with sending_lock[(target_id, target_type)]:
        try:
            message = msg
            if reply_to_message_id:
                message = MessageSegment.reply(int(reply_to_message_id)) + msg
            response = await asyncio.wait_for(
                _send(message),
                timeout=_send_timeout_seconds(),
            )
        except Exception as e:
            if not reply_to_message_id or isinstance(e, asyncio.TimeoutError):
                if isinstance(e, asyncio.TimeoutError):
                    error = f"send_msg timed out after {_send_timeout_seconds()}s"
                    logger.error(
                        f"Failed to send RSS message to {target_type}({target_id}): "
                        f"{error}"
                    )
                    result = delivery_result(target, status="failed", error=error)
                    return result
                logger.error(
                    f"Failed to send RSS message to {target_type}({target_id}): {e}"
                )
                result = delivery_result(target, status="failed", error=str(e))
                return result

            logger.warning(
                f"Failed to send RSS message with reply to {target_type}({target_id}), "
                f"retry without reply: {e}"
            )
            try:
                response = await asyncio.wait_for(
                    _send(msg),
                    timeout=_send_timeout_seconds(),
                )
            except asyncio.TimeoutError:
                error = f"send_msg timed out after {_send_timeout_seconds()}s"
                logger.error(
                    f"Failed to send RSS message to {target_type}({target_id}): {error}"
                )
                result = delivery_result(target, status="failed", error=error)
            except Exception as retry_error:
                logger.error(
                    f"Failed to send RSS message to {target_type}({target_id}): "
                    f"{retry_error}"
                )
                result = delivery_result(
                    target, status="failed", error=str(retry_error)
                )
            else:
                message_id = None
                if isinstance(response, dict):
                    raw_message_id = response.get("message_id")
                    message_id = (
                        str(raw_message_id) if raw_message_id is not None else None
                    )
                result = delivery_result(
                    target,
                    status="success",
                    message_id=message_id,
                )
            return result
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
    if image.failed:
        return image.missing_text
    if image.raw:
        encoded = base64.b64encode(image.raw).decode()
        return MessageSegment.image(f"base64://{encoded}")
    if image.url:
        return MessageSegment.image(image.url)
    return image.missing_text


def _video_to_onebot_segment(video: RssVideo) -> MessageSegment | str:
    if video.failed:
        return video.missing_text
    if video.raw:
        encoded = base64.b64encode(video.raw).decode()
        return MessageSegment.video(f"base64://{encoded}")
    if video.url:
        return MessageSegment.video(video.url)
    return video.missing_text


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
                else "订阅姬",
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
    for video in message.videos:
        segment = _video_to_onebot_segment(video)
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
        if image.failed and image.missing_text:
            result.append("\n" + image.missing_text)
        elif image.raw:
            result.image(raw=image.raw, name=image.name)
        elif image.url:
            result.image(url=image.url, name=image.name)
        elif image.missing_text:
            result.append("\n" + image.missing_text)
    for video in message.videos:
        if video.failed and video.missing_text:
            result.append("\n" + video.missing_text)
        elif video.raw:
            result.video(raw=video.raw, mimetype=video.mimetype, name=video.name)
        elif video.url:
            result.video(url=video.url, mimetype=video.mimetype, name=video.name)
        elif video.missing_text:
            result.append("\n" + video.missing_text)
    return result


async def send_message(
    user_id: set[int],
    group_id: set[int],
    message: RssMessage | list[RssMessage],
    *,
    bot: BaseBot | None = None,
    reply_to: dict[tuple[str, int], str] | None = None,
) -> list[DeliveryResult]:
    bot = bot or resolve_onebot()
    if bot is None:
        return [
            delivery_result(target, status="failed", error="no available bot")
            for target in build_delivery_targets(user_id, group_id)
        ]

    if isinstance(bot, Bot):
        return await send_onebot_message(user_id, group_id, message, bot, reply_to)
    return await send_uni_message(user_id, group_id, message, bot, reply_to)


async def send_onebot_message(
    user_id: set[int],
    group_id: set[int],
    message: RssMessage | list[RssMessage],
    bot: Bot,
    reply_to: dict[tuple[str, int], str] | None = None,
) -> list[DeliveryResult]:
    wrapped_msg = build_onebot_message(bot, message)
    results: list[DeliveryResult] = []
    if user_id:
        results.extend(
            await asyncio.gather(
                *(
                    send_onebot_message_with_lock(
                        bot,
                        uid,
                        "private",
                        wrapped_msg,
                        reply_to_message_id=_reply_message_id(reply_to, "private", uid),
                    )
                    for uid in user_id
                )
            )
        )
    if group_id:
        results.extend(
            await asyncio.gather(
                *(
                    send_onebot_message_with_lock(
                        bot,
                        gid,
                        "group",
                        wrapped_msg,
                        reply_to_message_id=_reply_message_id(reply_to, "group", gid),
                    )
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
    *,
    reply_to_message_id: str | None = None,
) -> DeliveryResult:
    start_time = time.monotonic()
    delivery_target = DeliveryTarget(target_type, target_id)

    async def _send(current_message: UniMessage, target) -> None:
        await current_message.send(
            target=target,
            bot=bot,
            fallback=FallbackStrategy.rollback,
        )

    async with sending_lock[(target_id, f"uni:{target_type}")]:
        target = None
        try:
            target = PlatformUtils.get_target(
                user_id=str(target_id) if target_type == "private" else None,
                group_id=str(target_id) if target_type == "group" else None,
            )
            if target is None:
                raise ValueError("no available message target")
            uni_message = build_uni_message(message)
            if reply_to_message_id:
                uni_message = UniMessage.reply(reply_to_message_id) + uni_message
            await asyncio.wait_for(
                _send(uni_message, target),
                timeout=_send_timeout_seconds(),
            )
        except Exception as e:
            if reply_to_message_id and not isinstance(e, asyncio.TimeoutError):
                logger.warning(
                    f"Failed to send RSS UniMessage with reply to "
                    f"{target_type}({target_id}), retry without reply: {e}"
                )
                # if target was not obtained, cannot retry
                if target is None:
                    error = "no available message target"
                    logger.error(
                        f"Failed to send RSS UniMessage to "
                        f"{target_type}({target_id}): {error}"
                    )
                    return delivery_result(
                        delivery_target, status="failed", error=error
                    )

                try:
                    await asyncio.wait_for(
                        _send(build_uni_message(message), target),
                        timeout=_send_timeout_seconds(),
                    )
                except asyncio.TimeoutError:
                    error = f"send message timed out after {_send_timeout_seconds()}s"
                    logger.error(
                        f"Failed to send RSS UniMessage to "
                        f"{target_type}({target_id}): {error}"
                    )
                    return delivery_result(
                        delivery_target, status="failed", error=error
                    )
                except Exception as retry_error:
                    logger.error(
                        f"Failed to send RSS UniMessage to "
                        f"{target_type}({target_id}): {retry_error}"
                    )
                    return delivery_result(
                        delivery_target, status="failed", error=str(retry_error)
                    )
                return delivery_result(delivery_target, status="success")

            if isinstance(e, asyncio.TimeoutError):
                error = f"send message timed out after {_send_timeout_seconds()}s"
                logger.error(
                    f"Failed to send RSS UniMessage to "
                    f"{target_type}({target_id}): {error}"
                )
                return delivery_result(delivery_target, status="failed", error=error)
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
    reply_to: dict[tuple[str, int], str] | None = None,
) -> list[DeliveryResult]:
    messages = message if isinstance(message, list) else [message]
    results: list[DeliveryResult] = []
    for msg in messages:
        if user_id:
            results.extend(
                await asyncio.gather(
                    *(
                        _send_uni_to_target(
                            bot,
                            uid,
                            "private",
                            msg,
                            reply_to_message_id=(reply_to or {}).get(("private", uid)),
                        )
                        for uid in user_id
                    )
                )
            )
        if group_id:
            results.extend(
                await asyncio.gather(
                    *(
                        _send_uni_to_target(
                            bot,
                            gid,
                            "group",
                            msg,
                            reply_to_message_id=(reply_to or {}).get(("group", gid)),
                        )
                        for gid in group_id
                    )
                )
            )
    return results
