from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Literal

from nonebot import logger

from .models.rss_models import RssGlobalConfig

ConfigType = Literal["bool", "int", "list[str]"]


@dataclass(slots=True, frozen=True)
class RuntimeConfigItem:
    key: str
    aliases: tuple[str, ...]
    title: str
    type: ConfigType
    default: Any
    help: str
    value_hint: str


CONFIG_ITEMS: tuple[RuntimeConfigItem, ...] = (
    RuntimeConfigItem(
        key="private_subscribe_superuser_only",
        aliases=("私聊仅超级用户", "私聊超级用户", "私聊限制"),
        title="私聊仅超级用户",
        type="bool",
        default=True,
        help="开启后，私聊里只有超级用户能使用订阅姬。",
        value_hint="开/关",
    ),
    RuntimeConfigItem(
        key="group_whitelist_enabled",
        aliases=("群白名单启用", "启用群白名单", "白名单启用"),
        title="启用群白名单",
        type="bool",
        default=False,
        help="开启后，只有群白名单里的群能使用订阅姬；关闭时不限制群号。",
        value_hint="开/关",
    ),
    RuntimeConfigItem(
        key="group_whitelist",
        aliases=("群白名单", "群组白名单", "白名单群"),
        title="群白名单",
        type="list[str]",
        default=[],
        help="允许使用订阅姬的群号。可用快捷命令：群白名单 添加/删除/清空。",
        value_hint="添加 141514 123456",
    ),
    RuntimeConfigItem(
        key="black_words",
        aliases=("全局黑名单词", "屏蔽词", "黑名单词"),
        title="全局屏蔽词",
        type="list[str]",
        default=[],
        help="命中这些词的 RSS 条目不会推送。多个词用逗号分隔，-1 表示清空。",
        value_hint="广告,推广",
    ),
    RuntimeConfigItem(
        key="blockquote",
        aliases=("保留引用", "引用块"),
        title="保留引用内容",
        type="bool",
        default=True,
        help="关闭后会去掉引用内容，Telegram 引用转发会更干净。",
        value_hint="开/关",
    ),
    RuntimeConfigItem(
        key="push_with_link",
        aliases=("推送链接", "带链接", "显示链接"),
        title="推送带链接",
        type="bool",
        default=False,
        help="开启后推送正文里会带原文链接；关闭后仍会尝试引用历史消息。",
        value_hint="开/关",
    ),
    RuntimeConfigItem(
        key="push_on_image_parse_failed",
        aliases=("图片失败推送", "图片解析失败推送"),
        title="图片失败仍推送",
        type="bool",
        default=False,
        help="关闭时，图片解析失败的条目会跳过并等待下次重试。",
        value_hint="开/关",
    ),
    RuntimeConfigItem(
        key="cache_expire",
        aliases=("缓存天数", "去重缓存天数"),
        title="去重缓存天数",
        type="int",
        default=14,
        help="去重历史保留天数，太小可能重复推送旧内容。",
        value_hint="14",
    ),
    RuntimeConfigItem(
        key="image_compress_size",
        aliases=("图片压缩尺寸", "图片尺寸"),
        title="图片压缩尺寸",
        type="int",
        default=2 * 1024,
        help="非 GIF 图片最长边压缩到这个尺寸以内。",
        value_hint="2048",
    ),
    RuntimeConfigItem(
        key="gif_compress_size",
        aliases=("GIF压缩阈值", "GIF大小"),
        title="GIF 大小阈值",
        type="int",
        default=6 * 1024,
        help="超过该 KB 数的 GIF 会进入压缩判断；当前压缩服务关闭时发送原图。",
        value_hint="6144",
    ),
    RuntimeConfigItem(
        key="enable_online_gif_compress",
        aliases=("在线GIF压缩", "GIF在线压缩"),
        title="在线 GIF 压缩",
        type="bool",
        default=False,
        help="预留开关。当前在线 GIF 压缩服务已移除，开启也会发送原图。",
        value_hint="开/关",
    ),
    RuntimeConfigItem(
        key="media_download_concurrency",
        aliases=("媒体并发", "图片并发"),
        title="媒体下载并发",
        type="int",
        default=4,
        help="同一轮更新里同时下载图片/封面的数量。",
        value_hint="4",
    ),
    RuntimeConfigItem(
        key="media_download_timeout_seconds",
        aliases=("媒体超时", "图片超时"),
        title="媒体下载超时",
        type="int",
        default=8,
        help="单张图片或封面下载处理的超时时间，单位秒。",
        value_hint="8",
    ),
    RuntimeConfigItem(
        key="media_cache_ttl_seconds",
        aliases=("媒体缓存时间", "图片缓存时间"),
        title="媒体缓存时间",
        type="int",
        default=300,
        help="已下载媒体在内存中复用的时间，单位秒。",
        value_hint="300",
    ),
    RuntimeConfigItem(
        key="media_cache_max_items",
        aliases=("媒体缓存数量", "图片缓存数量"),
        title="媒体缓存数量",
        type="int",
        default=256,
        help="内存媒体缓存最多保留多少项。",
        value_hint="256",
    ),
    RuntimeConfigItem(
        key="max_media_bytes_per_update",
        aliases=("媒体预算", "图片预算"),
        title="单轮媒体预算",
        type="int",
        default=20 * 1024 * 1024,
        help="单次检查最多下载多少媒体字节，0 表示不限制。",
        value_hint="20971520",
    ),
    RuntimeConfigItem(
        key="max_media_errors_per_update",
        aliases=("媒体失败上限", "图片失败上限"),
        title="媒体失败上限",
        type="int",
        default=3,
        help="单轮媒体下载失败达到该次数后跳过后续媒体，0 表示不限制。",
        value_hint="3",
    ),
    RuntimeConfigItem(
        key="video_download_enabled",
        aliases=("视频下载", "下载视频", "视频推送"),
        title="下载视频",
        type="bool",
        default=False,
        help="开启后会尝试下载 RSS 中的视频并直接推送；关闭时只处理视频封面。",
        value_hint="开/关",
    ),
    RuntimeConfigItem(
        key="video_download_max_minutes",
        aliases=("视频最大分钟", "视频时长上限", "视频最大时长"),
        title="视频最大分钟",
        type="int",
        default=3,
        help="视频超过该分钟数会跳过下载；0 表示不按时长限制。",
        value_hint="3",
    ),
    RuntimeConfigItem(
        key="message_send_timeout_seconds",
        aliases=("发送超时", "消息超时"),
        title="消息发送超时",
        type="int",
        default=12,
        help="向单个目标发送消息的超时时间，单位秒。",
        value_hint="12",
    ),
    RuntimeConfigItem(
        key="scheduler_batch_interval_seconds",
        aliases=("调度间隔", "批次间隔"),
        title="调度扫描间隔",
        type="int",
        default=60,
        help="RSS 后台批量扫描的间隔，单位秒。",
        value_hint="60",
    ),
    RuntimeConfigItem(
        key="scheduler_update_timeout_seconds",
        aliases=("更新超时", "订阅超时"),
        title="单订阅更新超时",
        type="int",
        default=120,
        help="单个订阅完整更新流程的超时时间，单位秒。",
        value_hint="120",
    ),
)

_ITEMS_BY_KEY = {item.key: item for item in CONFIG_ITEMS}
_KEY_BY_ALIAS = {
    alias: item.key for item in CONFIG_ITEMS for alias in (item.key, *item.aliases)
}
_values: dict[str, Any] = {item.key: item.default for item in CONFIG_ITEMS}
_loaded = False

BOOL_TRUE = {"1", "true", "on", "yes", "y", "开", "开启", "启用", "是", "显示"}
BOOL_FALSE = {"0", "false", "off", "no", "n", "关", "关闭", "禁用", "否", "隐藏"}


def normalize_key(key: str) -> str | None:
    return _KEY_BY_ALIAS.get(key.strip())


def get_item(key: str) -> RuntimeConfigItem | None:
    normalized = normalize_key(key) or key
    return _ITEMS_BY_KEY.get(normalized)


def _parse_list(value: str) -> list[str]:
    if value.strip() == "-1":
        return []
    return [
        item.strip()
        for item in value.replace("，", ",").split(",")
        if item.strip()
    ]


def parse_value(item: RuntimeConfigItem, value: str) -> Any:
    value = value.strip()
    if item.type == "bool":
        lowered = value.lower()
        if lowered in BOOL_TRUE:
            return True
        if lowered in BOOL_FALSE:
            return False
        raise ValueError(f"{item.title} 只能设置为 开 或 关")
    if item.type == "int":
        parsed = int(float(value))
        if parsed < 0:
            raise ValueError(f"{item.title} 不能小于 0")
        return parsed
    if item.type == "list[str]":
        return _parse_list(value)
    return value


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "开" if value else "关"
    if isinstance(value, list):
        return "、".join(str(item) for item in value) if value else "空"
    return str(value)


def _normalize_stored_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


async def load_runtime_config() -> None:
    global _loaded
    values = {item.key: item.default for item in CONFIG_ITEMS}
    try:
        records = await RssGlobalConfig.all()
    except Exception as e:
        logger.warning(f"加载订阅姬运行时配置失败，使用默认值: {e}")
        _values.update(values)
        _loaded = True
        return
    for record in records:
        if record.config_key in values:
            values[record.config_key] = _normalize_stored_value(record.config_value)
    _values.update(values)
    _loaded = True


async def ensure_loaded() -> None:
    if not _loaded:
        await load_runtime_config()


async def set_runtime_config(key: str, value: Any) -> None:
    await ensure_loaded()
    if key not in _ITEMS_BY_KEY:
        raise KeyError(key)
    await RssGlobalConfig.update_or_create(
        config_key=key,
        defaults={"config_value": value},
    )
    _values[key] = value


async def get_runtime_config(key: str) -> Any:
    await ensure_loaded()
    if key not in _ITEMS_BY_KEY:
        raise KeyError(key)
    return _values[key]


def get_cached_config(key: str) -> Any:
    if key not in _ITEMS_BY_KEY:
        raise KeyError(key)
    return _values[key]


def all_config_values() -> list[tuple[RuntimeConfigItem, Any]]:
    return [(item, _values[item.key]) for item in CONFIG_ITEMS]
