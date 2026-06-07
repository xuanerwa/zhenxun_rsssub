# ruff: noqa: E501
from __future__ import annotations

from nonebot.plugin import PluginMetadata

from zhenxun.configs.utils import Command, Example, PluginExtraData, RegisterConfig

from .config import Config

USAGE = """
\u6307\u4ee4\uff1a
    \u8ba2\u9605\u59ec \u6dfb\u52a0 \u8ba2\u9605\u540d \u8ba2\u9605\u5730\u5740
    \u8ba2\u9605\u59ec \u5220\u9664 \u8ba2\u9605\u540d [\u8ba2\u9605\u540d ...]
    \u8ba2\u9605\u59ec \u5217\u8868
    \u8ba2\u9605\u59ec \u8be6\u60c5 \u8ba2\u9605\u540d
    \u8ba2\u9605\u59ec \u8bbe\u7f6e \u8ba2\u9605\u540d \u5c5e\u6027=\u503c [\u5c5e\u6027=\u503c ...]
    \u8ba2\u9605\u59ec \u6d4b\u8bd5 \u8ba2\u9605\u540d
    \u8ba2\u9605\u59ec \u62c9\u53d6 \u8ba2\u9605\u540d
    \u8ba2\u9605\u59ec \u72b6\u6001 [\u8ba2\u9605\u540d]
    \u8ba2\u9605\u59ec \u5bfc\u51fa [\u8ba2\u9605\u540d] [\u6587\u4ef6] [\u539f\u59cb] [opml]
    \u8ba2\u9605\u59ec \u5bfc\u5165 [--dry-run] JSON\u5185\u5bb9|OPML\u5185\u5bb9|file:\u8def\u5f84

\u5e38\u7528\u5c5e\u6027\uff1a
    \u9891\u7387=5                 \u8bbe\u7f6e\u66f4\u65b0\u95f4\u9694\uff0c\u5355\u4f4d\u5206\u949f
    \u4ee3\u7406=\u5f00/\u5173           \u662f\u5426\u4f7f\u7528\u5168\u5c40\u4ee3\u7406
    \u4ec5\u6807\u9898=\u5f00/\u5173         \u4ec5\u63a8\u9001\u6807\u9898
    \u4ec5\u56fe\u7247=\u5f00/\u5173         \u4ec5\u63a8\u9001\u56fe\u7247
    \u4e0b\u8f7d\u56fe\u7247=\u5f00/\u5173       \u4e0b\u8f7d\u56fe\u7247\u540e\u518d\u63a8\u9001
    \u56fe\u7247=0 \u6216 \u56fe\u7247=5     \u9650\u5236\u5355\u6761\u63a8\u9001\u56fe\u7247\u6570\u91cf
    \u767d\u540d\u5355=\u6b63\u5219 \u6216 \u767d\u540d\u5355=-1   \u8bbe\u7f6e/\u6e05\u7a7a\u767d\u540d\u5355\u5173\u952e\u8bcd
    \u9ed1\u540d\u5355=\u6b63\u5219 \u6216 \u9ed1\u540d\u5355=-1   \u8bbe\u7f6e/\u6e05\u7a7a\u9ed1\u540d\u5355\u5173\u952e\u8bcd
    cookie=xxx             \u8bbe\u7f6e\u6293\u53d6 Cookie
    \u5408\u5e76=\u5f00/\u5173           \u662f\u5426\u5c1d\u8bd5\u5408\u5e76\u8f6c\u53d1
    \u6682\u505c=\u5f00/\u5173           \u6682\u505c/\u6062\u590d\u8ba2\u9605

\u793a\u4f8b\uff1a
    \u8ba2\u9605\u59ec \u6dfb\u52a0 \u771f\u5bfb\u66f4\u65b0 https://example.com/feed.xml
    \u8ba2\u9605\u59ec \u6dfb\u52a0 RSSHub\u8def\u7531 /bilibili/user/video/123456
    \u8ba2\u9605\u59ec \u62c9\u53d6 \u771f\u5bfb\u66f4\u65b0
    \u8ba2\u9605\u59ec \u72b6\u6001 \u771f\u5bfb\u66f4\u65b0
    \u8ba2\u9605\u59ec \u8bbe\u7f6e \u771f\u5bfb\u66f4\u65b0 \u9891\u7387=30 \u56fe\u7247=5
    \u8ba2\u9605\u59ec \u5bfc\u51fa \u771f\u5bfb\u66f4\u65b0 file opml
    \u8ba2\u9605\u59ec \u5bfc\u5165 --dry-run file:rss_export_all.json
""".strip()

COMMANDS = [
    Command(
        command="\u8ba2\u9605\u59ec \u6dfb\u52a0",
        params=["\u8ba2\u9605\u540d", "\u8ba2\u9605\u5730\u5740"],
        description="\u6dfb\u52a0 RSS \u8ba2\u9605\u5230\u5f53\u524d\u7fa4\u804a\u6216\u79c1\u804a",
        examples=[
            Example(
                exec="\u8ba2\u9605\u59ec \u6dfb\u52a0 \u771f\u5bfb\u66f4\u65b0 https://example.com/feed.xml",
                description="\u6dfb\u52a0\u5b8c\u6574 RSS \u5730\u5740",
            ),
            Example(
                exec="\u8ba2\u9605\u59ec \u6dfb\u52a0 RSSHub\u8def\u7531 /bilibili/user/video/123456",
                description="\u901a\u8fc7 RSSHub \u8def\u7531\u6dfb\u52a0\u8ba2\u9605",
            ),
        ],
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u5220\u9664",
        params=["\u8ba2\u9605\u540d", "[\u8ba2\u9605\u540d ...]"],
        description="\u53d6\u6d88\u5f53\u524d\u4f1a\u8bdd\u7684\u4e00\u4e2a\u6216\u591a\u4e2a\u8ba2\u9605",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u5217\u8868",
        description="\u67e5\u770b\u5f53\u524d\u4f1a\u8bdd\u7684\u8ba2\u9605\u5217\u8868",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u8be6\u60c5",
        params=["\u8ba2\u9605\u540d"],
        description="\u67e5\u770b\u8ba2\u9605\u8be6\u60c5",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u8bbe\u7f6e",
        params=[
            "\u8ba2\u9605\u540d",
            "\u5c5e\u6027=\u503c",
            "[\u5c5e\u6027=\u503c ...]",
        ],
        description="\u4fee\u6539\u8ba2\u9605\u5c5e\u6027\uff0c\u4f8b\u5982 \u9891\u7387=30 \u56fe\u7247=5",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u6d4b\u8bd5",
        params=["\u8ba2\u9605\u540d"],
        description="\u6293\u53d6\u5e76\u9884\u89c8\u89e3\u6790\u7ed3\u679c\uff0c\u4e0d\u53d1\u9001\u3001\u4e0d\u5199\u5165\u53bb\u91cd\u72b6\u6001",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u62c9\u53d6",
        params=["\u8ba2\u9605\u540d"],
        description="\u7acb\u5373\u6293\u53d6\u5e76\u63a8\u9001\u8ba2\u9605\u66f4\u65b0",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u72b6\u6001",
        params=["[\u8ba2\u9605\u540d]"],
        description="\u67e5\u770b\u8ba2\u9605\u8fd0\u884c\u72b6\u6001\u3001\u6293\u53d6\u8bca\u65ad\u548c\u6700\u8fd1\u9519\u8bef",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u5bfc\u51fa",
        params=["[\u8ba2\u9605\u540d]", "[file]", "[raw]", "[opml]"],
        description="\u5bfc\u51fa\u8ba2\u9605\uff0c\u652f\u6301 JSON/OPML\u3001\u6587\u4ef6\u53d1\u9001\u548c\u654f\u611f\u5b57\u6bb5\u4e0d\u8131\u654f",
    ),
    Command(
        command="\u8ba2\u9605\u59ec \u5bfc\u5165",
        params=["[--dry-run]", "JSON\u5185\u5bb9|OPML\u5185\u5bb9|file:\u8def\u5f84"],
        description="\u5bfc\u5165\u8ba2\u9605\uff0c\u652f\u6301\u9884\u68c0\u548c\u6587\u4ef6\u5bfc\u5165",
    ),
]

CONFIGS = [
    RegisterConfig(
        module="dingyueji",
        key="RSSHUB_URL",
        value="https://rsshub.app",
        help="\u9ed8\u8ba4 RSSHub \u5730\u5740\uff0c\u7528\u4e8e / \u5f00\u5934\u7684 RSSHub \u8def\u7531",
        default_value="https://rsshub.app",
        type=str,
    ),
    RegisterConfig(
        module="dingyueji",
        key="RSSHUB_FALLBACK_URLS",
        value=[],
        help="RSSHub \u5907\u7528\u5730\u5740\u5217\u8868\uff0c\u4e3b\u5730\u5740\u5931\u8d25\u65f6\u4f9d\u6b21\u5c1d\u8bd5",
        default_value=[],
        type=list[str],
    ),
    RegisterConfig(
        module="dingyueji",
        key="PROXY",
        value=None,
        help="RSS \u6293\u53d6\u548c\u5a92\u4f53\u4e0b\u8f7d\u4f7f\u7528\u7684\u4ee3\u7406\u5730\u5740",
        default_value=None,
        type=str,
    ),
    RegisterConfig(
        module="dingyueji",
        key="CACHE_EXPIRE",
        value=14,
        help="\u8ba2\u9605\u5386\u53f2\u548c\u5a92\u4f53\u7f13\u5b58\u4fdd\u7559\u5929\u6570",
        default_value=14,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="MAX_LENGTH",
        value=500,
        help="\u5355\u6761 RSS \u6587\u672c\u63a8\u9001\u6700\u5927\u957f\u5ea6",
        default_value=500,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="MAX_MEDIA_BYTES_PER_UPDATE",
        value=20 * 1024 * 1024,
        help="\u5355\u6b21\u66f4\u65b0\u5141\u8bb8\u4e0b\u8f7d\u7684\u6700\u5927\u5a92\u4f53\u603b\u5b57\u8282\u6570",
        default_value=20 * 1024 * 1024,
        type=int,
    ),
    RegisterConfig(
        module="dingyueji",
        key="EXPORT_MASK_SENSITIVE",
        value=True,
        help="\u5bfc\u51fa\u8ba2\u9605\u65f6\u9ed8\u8ba4\u8131\u654f cookie \u7b49\u654f\u611f\u5b57\u6bb5",
        default_value=True,
        type=bool,
    ),
]

__plugin_meta__ = PluginMetadata(
    name="\u8ba2\u9605\u59ec",
    description="RSS \u8ba2\u9605\u3001\u6293\u53d6\u3001\u53bb\u91cd\u4e0e\u63a8\u9001\u52a9\u624b",
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
        aliases={"RSS", "RSS\u8ba2\u9605"},
    ).to_dict(),
)
