from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from dataclasses import fields as dataclass_fields
from datetime import datetime, timezone
from typing import Any, ClassVar, Literal

from nonebot.adapters.onebot.v11 import Bot
from pydantic import HttpUrl
from yarl import URL

from . import feed_state, fetcher, rss_service
from .globals import plugin_config
from .models import FetchResult
from .repository_entries import delete_entries_file
from .repository_feeds import (
    load_feed_records,
    remove_feed_record,
    rename_feed_record,
    upsert_feed_record,
    upsert_feed_state,
)
from .repository_utils import sanitize_feed_name


@dataclass
class RSS:
    # 订阅名
    name: str = ""
    # 订阅地址
    url: URL = field(default_factory=lambda: URL(""))
    # 订阅用户
    user_id: set[int] = field(default_factory=set)
    # 订阅群组
    group_id: set[int] = field(default_factory=set)
    # 是否使用代理
    use_proxy: bool = False
    # 更新频率 (分钟/次)
    frequency: str = "5"
    # 仅推送标题
    only_feed_title: bool = False
    # 仅推送图片
    only_feed_pic: bool = False
    # 是否下载图片
    download_pic: bool = False
    # 获取订阅更新时使用的 cookie
    cookie: str = ""
    # 白名单关键词
    white_list_keyword: str = ""
    # 黑名单关键词
    black_list_keyword: str = ""
    # 去重模式
    deduplication_modes: set[Literal["title", "link", "or"]] = field(
        default_factory=set
    )
    # 图片数量限制，防止消息太长刷屏
    max_image_number: int = 0
    # 正文待移除内容，支持正则
    content_to_remove: set[str] = field(default_factory=set)
    # 当一次更新多条消息时，是否尝试发送合并消息
    send_merged_msg: bool = False
    # 停止更新
    stop: bool = False
    # HTTP ETag
    etag: str | None = None
    # 上次更新时间
    last_modified: str | None = None
    # 按实际抓取 URL 记录条件请求状态，供 RSSHub fallback 独立缓存
    http_cache: dict[str, dict[str, str | None]] = field(default_factory=dict)
    # 最近一次 feedparser 解析异常标记
    last_bozo: bool = False
    # 最近一次 feedparser 解析异常说明
    last_bozo_exception: str | None = None
    # 连续抓取失败的次数，超过 100 就停止更新
    error_count: int = 0
    # 下一次允许重试的时间，用于失败后的指数退避
    next_retry_at: str | None = None
    # 最近一次成功抓取或缓存命中的时间
    last_success_at: str | None = None
    # 最近一次错误说明
    last_error: str | None = None
    # 最近一次抓取结构化结果，用于 订阅姬 状态 / fallback 诊断
    last_fetch_result: dict[str, Any] = field(default_factory=dict)
    # feed 自身推荐的最小更新间隔（分钟），来自 ttl
    feed_ttl_minutes: int | None = None
    # feed 建议跳过的小时（0-23），来自 skipHours
    feed_skip_hours: list[int] = field(default_factory=list)
    # feed 建议跳过的星期（0=Monday），来自 skipDays
    feed_skip_days: list[int] = field(default_factory=list)
    # feed 提示或 HTTP Retry-After 计算出的下次建议拉取时间
    next_recommended_update_at: str | None = None
    # 最近一次运行观测指标
    last_metrics: dict[str, Any] = field(default_factory=dict)

    _locks: ClassVar[dict[str, asyncio.Lock]] = {}

    def __post_init__(self):
        self._log_prefix = f"[RSS: {self.name}]"
        self._defer_state_write = False
        self._state_dirty = False

    def defer_state_write(self):
        return _DeferredStateWrite(self)

    def mark_state_dirty(self) -> None:
        if self._defer_state_write:
            self._state_dirty = True
        else:
            self.flush_state()

    def flush_state(self) -> None:
        self._state_dirty = False
        upsert_feed_state(self.name, self.to_record())

    @staticmethod
    def _normalize_record(item: dict[str, Any]) -> dict[str, Any]:
        if isinstance(item.get("url"), str):
            item["url"] = URL(item["url"])
        if isinstance(item.get("user_id"), list):
            item["user_id"] = set(item["user_id"])
        if isinstance(item.get("group_id"), list):
            item["group_id"] = set(item["group_id"])
        if isinstance(item.get("deduplication_modes"), list):
            item["deduplication_modes"] = set(item["deduplication_modes"])
        if isinstance(item.get("content_to_remove"), list):
            item["content_to_remove"] = set(item["content_to_remove"])
        if not isinstance(item.get("http_cache"), dict):
            item["http_cache"] = {}
        if not isinstance(item.get("next_retry_at"), str):
            item["next_retry_at"] = None
        if not isinstance(item.get("last_success_at"), str):
            item["last_success_at"] = None
        if not isinstance(item.get("last_error"), str):
            item["last_error"] = None
        if not isinstance(item.get("last_fetch_result"), dict):
            item["last_fetch_result"] = {}
        if item.get("feed_ttl_minutes") is not None and not isinstance(
            item.get("feed_ttl_minutes"), int
        ):
            item["feed_ttl_minutes"] = None
        if not isinstance(item.get("feed_skip_hours"), list):
            item["feed_skip_hours"] = []
        if not isinstance(item.get("feed_skip_days"), list):
            item["feed_skip_days"] = []
        if not isinstance(item.get("next_recommended_update_at"), str):
            item["next_recommended_update_at"] = None
        if not isinstance(item.get("last_metrics"), dict):
            item["last_metrics"] = {}
        return item

    @classmethod
    def from_record(cls, item: dict[str, Any]) -> "RSS":
        normalized = cls._normalize_record(item.copy())
        init_fields = {field.name for field in dataclass_fields(cls) if field.init}
        return cls(
            **{key: value for key, value in normalized.items() if key in init_fields}
        )

    @staticmethod
    def load_rss_data() -> list["RSS"]:
        """加载全部RSS数据"""

        rss_list = []
        for item in load_feed_records():
            rss_list.append(RSS.from_record(item))
        return rss_list

    @staticmethod
    def get_by_name(name: str) -> "RSS | None":
        """通过订阅名获取RSS数据"""
        all_rss = RSS.load_rss_data()
        return next((rss for rss in all_rss if rss.name == name), None)

    def add_subscriber(
        self, *, user_id: int | None = None, group_id: int | None = None
    ):
        """添加订阅者"""
        if user_id:
            self.user_id.add(user_id)
        if group_id:
            self.group_id.add(group_id)
        self.upsert()

    def remove_subscriber(
        self, *, user_id: int | None = None, group_id: int | None = None
    ) -> bool:
        """移除订阅者"""
        if user_id and user_id not in self.user_id:
            return False
        if group_id and group_id not in self.group_id:
            return False
        if user_id:
            self.user_id.remove(user_id)
        if group_id:
            self.group_id.remove(group_id)
        self.upsert()
        return True

    def destroy(self):
        """删除整个RSS订阅"""
        remove_feed_record(self.name)
        delete_entries_file(self.name)

    def upsert(self, old_name: str | None = None):
        """Insert or update feed configuration and target indexes."""
        data = self.to_record()
        if old_name and old_name != self.name:
            rename_feed_record(old_name, self.name, data)
        else:
            upsert_feed_record(self.name, data, old_name)
        self._state_dirty = False

    def to_record(self) -> dict[str, Any]:
        """Serialize RSS data for repository/export."""
        data = {k: v for k, v in self.__dict__.copy().items() if not k.startswith("_")}
        data["url"] = str(self.url)
        data["user_id"] = list(self.user_id)
        data["group_id"] = list(self.group_id)
        data["deduplication_modes"] = list(self.deduplication_modes)
        data["content_to_remove"] = list(self.content_to_remove)
        return data

    @property
    def sanitized_name(self) -> str:
        """去除 RSS 订阅名中无法作为文件名的非法字符"""
        return sanitize_feed_name(self.name)

    def get_url(self, rsshub_url: HttpUrl = plugin_config.rsshub_url) -> str:
        if self.url.scheme in {"http", "https"}:
            # url 是完整的订阅链接
            return str(self.url)
        else:
            # url 不是完整链接则代表 RSSHub 路由
            base = str(rsshub_url).rstrip("/")
            route = str(self.url).lstrip("/")
            return f"{base}/{route}"

    def _record_metrics(
        self,
        *,
        result: FetchResult,
        parse_duration_ms: float = 0.0,
        send_duration_ms: float = 0.0,
        entry_count: int = 0,
        new_entry_count: int = 0,
        image_count: int = 0,
        messages_sent: int = 0,
        error: str | None = None,
    ) -> None:
        self.last_metrics = {
            "time": datetime.now(timezone.utc).isoformat(),
            "fetch_ms": round(result.elapsed_ms, 2),
            "parse_ms": round(parse_duration_ms, 2),
            "send_ms": round(send_duration_ms, 2),
            "http_status": result.status,
            "entry_count": entry_count,
            "new_entry_count": new_entry_count,
            "image_count": image_count,
            "messages_sent": messages_sent,
            "error": error,
        }
        self.mark_state_dirty()

    @property
    def _lock_key(self) -> str:
        return self.sanitized_name or self.name or str(self.url)

    def _get_update_lock(self) -> asyncio.Lock:
        return self._locks.setdefault(self._lock_key, asyncio.Lock())

    def effective_interval_minutes(self) -> int | None:
        return feed_state.effective_interval_minutes(self)

    async def update(self, bot: Bot | None = None, *, force: bool = False):
        await rss_service.update(self, bot, force=force)

    async def test_parse(self) -> tuple[bool, str]:
        return await rss_service.test_parse(self)

    async def fetch(self) -> FetchResult:
        return await fetcher.fetch(self)

    async def stop_update_and_notify(self, bot: Bot, reason: str):
        await rss_service.stop_update_and_notify(self, bot, reason)


class _DeferredStateWrite:
    def __init__(self, rss: RSS):
        self.rss = rss
        self.previous = False

    def __enter__(self):
        self.previous = self.rss._defer_state_write
        self.rss._defer_state_write = True
        return self.rss

    def __exit__(self, exc_type, exc, tb):
        self.rss._defer_state_write = self.previous
        if (
            exc_type is None
            and self.rss._state_dirty
            and not self.rss._defer_state_write
        ):
            self.rss.flush_state()
        return False
