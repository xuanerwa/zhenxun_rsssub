from dataclasses import dataclass, field
from sqlite3 import Connection
import time
from typing import Any

from nonebot import logger

from ..delivery import DeliveryTarget
from ..rss_message import RssImage, RssMessage


@dataclass
class Context:
    """用于存储 RSS 解析过程中的上下文"""

    # RSS 标题
    title: str = ""
    # RSS 文章列表
    entries: list[dict[str, Any]] = field(default_factory=list)
    # 新增的 RSS 文章列表
    new_entries: list[dict[str, Any]] = field(default_factory=list)
    # 当前 RSS 订阅名，供 repository 定位 entries 文件
    rss_name: str = ""
    # 已保存的 RSS 文章 hash
    old_entry_hashes: set[str] = field(default_factory=set)
    # 当前订阅目标
    target_keys: set[tuple[str, str]] = field(default_factory=set)
    targets: list[DeliveryTarget] = field(default_factory=list)
    # 去重缓存数据库的连接对象
    conn: Connection | None = None

    # 消息发送失败计数
    msg_error_count: int = 0
    # 消息标题
    msg_title: str = ""
    # 新增的 RSS 文章对应的解析结果
    msg_contents: dict[str, RssMessage] = field(default_factory=dict)
    # 暂存单条 RSS 文章的解析结果
    msg_text_buffer: str = ""
    msg_image_buffer: list[RssImage] = field(default_factory=list)
    # 单轮 RSS 更新中的媒体下载预算，避免图片过多时内存和网络峰值过高
    media_bytes_used: int = 0

    # 当前正在解析的文章
    entry: dict[str, Any] | None = None

    # 是否继续执行后续 handler
    continue_process: bool = True
    # 是否只预览解析结果，不发送、不写 entries
    dry_run: bool = False
    # 性能指标
    parse_started_at: float = field(default_factory=time.monotonic)
    send_duration_ms: float = 0.0
    messages_sent: int = 0

    def flush_msg_buffer(self):
        """保存解析结果并清空缓冲区，为下次解析准备"""
        entry_hash = self.entry["hash"]  # 预处理第 1 步计算得到
        message = RssMessage(text=self.msg_text_buffer, images=self.msg_image_buffer)
        if message.is_empty():
            logger.warning("对空缓冲区进行了刷新，该条 RSS 文章未被正确解析")
            return
        self.msg_contents[entry_hash] = message
        self.msg_text_buffer = ""
        self.msg_image_buffer = []
        self.continue_process = True

    def flush_msg_contents(self):
        """在消息发送结束后调用，清空已发送的消息内容"""
        self.msg_contents.clear()
