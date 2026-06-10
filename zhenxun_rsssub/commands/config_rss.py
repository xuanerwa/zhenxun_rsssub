from __future__ import annotations

from nonebot.adapters import Bot, Event
from nonebot.internal.rule import Rule
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import on_alconna

from zhenxun.utils.message import MessageUtils
from zhenxun.utils.image_utils import ImageTemplate

from ..host_adapter import is_group_event
from ..runtime_config import (
    CONFIG_ITEMS,
    all_config_values,
    format_value,
    get_item,
    get_runtime_config,
    parse_value,
    set_runtime_config,
)
from .cmd_parser import config_alconna


async def _config_rule(bot: Bot, event: Event) -> bool:
    if not await SUPERUSER(bot, event):
        return False
    if is_group_event(event):
        getter = getattr(event, "is_tome", None)
        if callable(getter):
            return bool(getter())
        return bool(getattr(event, "to_me", False))
    return True


config_cmd = on_alconna(
    config_alconna,
    rule=Rule(_config_rule),
    priority=4,
    block=True,
)


async def _send_image(image) -> None:
    await MessageUtils.build_message(image).send()


async def _build_status_image():
    rows = []
    for item, value in all_config_values():
        rows.append([item.title, format_value(value), item.help])
    return await ImageTemplate.table_page(
        "订阅姬配置状态",
        "这些是可以用命令热修改的通用配置；修改后不用重启。",
        ["配置", "当前值", "说明"],
        rows,
        row_space=28,
        column_space=24,
        padding=8,
    )


async def _build_help_image():
    rows = []
    for item in CONFIG_ITEMS:
        rows.append(
            [
                item.title,
                " / ".join((item.key, *item.aliases[:2])),
                item.value_hint,
                item.help,
            ]
        )
    return await ImageTemplate.table_page(
        "订阅姬配置帮助",
        "只有超级用户可以修改。示例：订阅姬 配置 群白名单 添加 141514 123456",
        ["配置", "可用名称", "怎么填", "说明"],
        rows,
        row_space=28,
        column_space=24,
        padding=8,
    )


def _split_option(option: str) -> tuple[str, str]:
    if "=" not in option:
        raise ValueError(f"参数 `{option}` 缺少 `=`")
    key, value = option.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        raise ValueError(f"参数 `{option}` 的配置名为空")
    return key, value


def _group_id_values(values: tuple[str, ...]) -> list[str]:
    raw_values: list[str] = []
    for value in values:
        raw_values.extend(
            item.strip()
            for item in value.replace("，", ",").split(",")
            if item.strip()
        )
    if not raw_values:
        raise ValueError("群白名单操作需要填写群号")
    for value in raw_values:
        if not value.isdigit():
            raise ValueError(f"群号 `{value}` 格式错误，只能填写数字")
    return raw_values


async def _handle_group_whitelist_command(options: tuple[str, ...]) -> str | None:
    if not options:
        return None
    item = get_item(options[0])
    if item is None or item.key != "group_whitelist":
        return None
    if len(options) < 2:
        raise ValueError("群白名单快捷命令缺少操作，可用：添加、删除、清空")

    operation = options[1]
    current = [str(group_id) for group_id in await get_runtime_config("group_whitelist")]
    if operation in {"添加", "add", "+", "加入"}:
        group_ids = _group_id_values(options[2:])
        merged = list(dict.fromkeys([*current, *group_ids]))
        await set_runtime_config("group_whitelist", merged)
        return f"群白名单={format_value(merged)}"
    if operation in {"删除", "del", "remove", "-", "移除"}:
        group_ids = set(_group_id_values(options[2:]))
        updated = [group_id for group_id in current if group_id not in group_ids]
        await set_runtime_config("group_whitelist", updated)
        return f"群白名单={format_value(updated)}"
    if operation in {"清空", "clear", "重置"}:
        await set_runtime_config("group_whitelist", [])
        return "群白名单=空"

    raise ValueError("群白名单操作不支持，可用：添加、删除、清空")


@config_cmd.assign("配置")
async def config_rss(bot: Bot, event: Event, options=()):
    options = tuple(options or ())
    if not options or (len(options) == 1 and options[0] in {"状态", "status", "查看"}):
        await _send_image(await _build_status_image())
        return

    if len(options) == 1 and options[0] in {"帮助", "help", "说明"}:
        await _send_image(await _build_help_image())
        return

    try:
        if changed_text := await _handle_group_whitelist_command(options):
            image = await _build_status_image()
            await MessageUtils.build_message(f"✅ 已更新：{changed_text}").send()
            await _send_image(image)
            return
    except Exception as e:
        await config_cmd.finish(f"❌ 配置修改失败：{e}")

    changed: list[str] = []
    for option in options:
        try:
            key, raw_value = _split_option(option)
            item = get_item(key)
            if item is None:
                raise ValueError(f"配置 `{key}` 不存在")
            value = parse_value(item, raw_value)
            await set_runtime_config(item.key, value)
            changed.append(f"{item.title}={format_value(value)}")
        except Exception as e:
            await config_cmd.finish(f"❌ 配置修改失败：{e}")

    image = await _build_status_image()
    await MessageUtils.build_message("✅ 已更新：" + "，".join(changed)).send()
    await _send_image(image)
