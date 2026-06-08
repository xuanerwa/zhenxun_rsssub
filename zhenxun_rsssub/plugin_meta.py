# ruff: noqa: E501
from __future__ import annotations

from nonebot.plugin import PluginMetadata

from zhenxun.configs.utils import Command, Example, PluginExtraData, RegisterConfig

from .config import Config

USAGE = """
指令：
    订阅姬 添加 订阅名 订阅地址
    订阅姬 删除 订阅名 [订阅名 ...]
    订阅姬 列表
    订阅姬 详情 订阅名
    订阅姬 设置 订阅名 属性=值 [属性=值 ...]
    订阅姬 测试 订阅名
    订阅姬 拉取 订阅名
    订阅姬 状态 [订阅名]
    订阅姬 导出 [订阅名] [文件] [原始] [opml]
    订阅姬 导入 [--dry-run] JSON内容|OPML内容|file:路径

常用属性：
    频率=5                 设置更新间隔，单位分钟
    代理=开/关           是否使用全局代理
    仅标题=开/关         仅推送标题
    仅图片=开/关         仅推送图片
    下载图片=开/关       下载图片后再推送
    图片=0 或 图片=5     限制单条推送图片数量
    白名单=正则 或 白名单=-1   设置/清空白名单关键词
    黑名单=正则 或 黑名单=-1   设置/清空黑名单关键词
    cookie=xxx             设置抓取 Cookie
    合并=开/关           是否尝试合并转发
    暂停=开/关           暂停/恢复订阅

示例：
    订阅姬 添加 真寻更新 https://example.com/feed.xml
    订阅姬 添加 RSSHub路由 /bilibili/user/video/123456
    订阅姬 添加 TG频道 /telegram/channel/botnews
    订阅姬 拉取 真寻更新
    订阅姬 状态 真寻更新
    订阅姬 设置 真寻更新 频率=30 图片=5
    订阅姬 导出 真寻更新 file opml
    订阅姬 导入 --dry-run file:rss_export_all.json
""".strip()

COMMANDS = [
    Command(
        command="订阅姬 添加",
        params=["订阅名", "订阅地址"],
        description="添加 RSS 订阅到当前群聊或私聊",
        examples=[
            Example(
                exec="订阅姬 添加 真寻更新 https://example.com/feed.xml",
                description="添加完整 RSS 地址",
            ),
            Example(
                exec="订阅姬 添加 RSSHub路由 /bilibili/user/video/123456",
                description="通过 RSSHub 路由添加订阅",
            ),
            Example(
                exec="订阅姬 添加 TG频道 /telegram/channel/botnews",
                description="订阅 Telegram 频道",
            ),
        ],
    ),
    Command(
        command="订阅姬 删除",
        params=["订阅名", "[订阅名 ...]"],
        description="取消当前会话的一个或多个订阅",
    ),
    Command(
        command="订阅姬 列表",
        description="查看当前会话的订阅列表",
    ),
    Command(
        command="订阅姬 详情",
        params=["订阅名"],
        description="查看订阅详情",
    ),
    Command(
        command="订阅姬 设置",
        params=[
            "订阅名",
            "属性=值",
            "[属性=值 ...]",
        ],
        description="修改订阅属性，例如 频率=30 图片=5",
    ),
    Command(
        command="订阅姬 测试",
        params=["订阅名"],
        description="抓取并预览解析结果，不发送、不写入去重状态",
    ),
    Command(
        command="订阅姬 拉取",
        params=["订阅名"],
        description="立即抓取并推送订阅更新",
    ),
    Command(
        command="订阅姬 状态",
        params=["[订阅名]"],
        description="查看订阅运行状态、抓取诊断和最近错误",
    ),
    Command(
        command="订阅姬 导出",
        params=["[订阅名]", "[file]", "[raw]", "[opml]"],
        description="导出订阅，支持 JSON/OPML、文件发送和敏感字段不脱敏",
    ),
    Command(
        command="订阅姬 导入",
        params=["[--dry-run]", "JSON内容|OPML内容|file:路径"],
        description="导入订阅，支持预检和文件导入",
    ),
]

CONFIGS = [
    RegisterConfig(
        module="dingyueji",
        key="DEBUG",
        value=False,
        help="调试模式",
        default_value=False,
        type=bool,
    ),
    RegisterConfig(
        module="dingyueji",
        key="RSSHUB_URL",
        value="https://rsshub.app",
        help="默认 RSSHub 地址，用于 / 开头的 RSSHub 路由",
        default_value="https://rsshub.app",
        type=str,
    ),
    RegisterConfig(
        module="dingyueji",
        key="RSSHUB_FALLBACK_URLS",
        value=[],
        help="RSSHub 备用地址列表，主地址失败时依次尝试",
        default_value=[],
        type=list[str],
    ),
    RegisterConfig(
        module="dingyueji",
        key="PROXY",
        value=None,
        help="RSS 抓取和媒体下载使用的代理地址",
        default_value=None,
        type=str,
    ),
    RegisterConfig(
        module="dingyueji",
        key="BLACK_WORDS",
        value=None,
        help="屏蔽词列表，匹配到的内容将被过滤",
        default_value=None,
        type=list[str],
    ),
    RegisterConfig(
        module="dingyueji",
        key="CACHE_EXPIRE",
        value=14,
        help="订阅历史和媒体缓存保留天数",
        default_value=14,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="BLOCKQUOTE",
        value=True,
        help="是否在消息中保留引用块格式",
        default_value=True,
        type=bool,
    ),
    RegisterConfig(
        module="dingyueji",
        key="IMAGE_COMPRESS_SIZE",
        value=2 * 1024,
        help="图片压缩尺寸阈值（KB）",
        default_value=2 * 1024,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="GIF_COMPRESS_SIZE",
        value=6 * 1024,
        help="GIF 压缩尺寸阈值（KB）",
        default_value=6 * 1024,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="ENABLE_ONLINE_GIF_COMPRESS",
        value=False,
        help="是否启用在线 GIF 压缩服务",
        default_value=False,
        type=bool,
    ),
    RegisterConfig(
        module="dingyueji",
        key="MEDIA_DOWNLOAD_CONCURRENCY",
        value=4,
        help="媒体下载并发数",
        default_value=4,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="MEDIA_CACHE_TTL_SECONDS",
        value=300,
        help="媒体缓存存活时间（秒）",
        default_value=300,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="MEDIA_CACHE_MAX_ITEMS",
        value=256,
        help="媒体缓存最大条目数",
        default_value=256,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="MAX_MEDIA_BYTES_PER_UPDATE",
        value=20 * 1024 * 1024,
        help="单次更新允许下载的最大媒体总字节数",
        default_value=20 * 1024 * 1024,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="MAX_LENGTH",
        value=500,
        help="单条 RSS 文本推送最大长度",
        default_value=500,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="RSS_ENTRIES_FILE_LIMIT",
        value=200,
        help="RSS 条目文件保存数量限制",
        default_value=200,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="EXPORT_MASK_SENSITIVE",
        value=True,
        help="导出订阅时默认脱敏 cookie 等敏感字段",
        default_value=True,
        type=bool,
    ),
    RegisterConfig(
        module="dingyueji",
        key="SCHEDULER_BATCH_INTERVAL_SECONDS",
        value=60,
        help="调度器批次执行间隔（秒）",
        default_value=60,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="SCHEDULER_BATCH_CONCURRENCY",
        value=4,
        help="调度器批次并发数",
        default_value=4,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="SCHEDULER_PER_HOST_CONCURRENCY",
        value=1,
        help="每个主机的并发数",
        default_value=1,
        type=int,
    ),
]

__plugin_meta__ = PluginMetadata(
    name="订阅姬",
    description="RSS 订阅、抓取、去重与推送助手",
    usage=USAGE,
    type="application",
    homepage="https://github.com/HibiKier/zhenxun_bot",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra=PluginExtraData(
        author="liuzhaoze / zhenxun",
        version="0.1.0",
        commands=COMMANDS,
        configs=CONFIGS,
        aliases={"RSS", "RSS订阅"},
    ).to_dict(),
)
