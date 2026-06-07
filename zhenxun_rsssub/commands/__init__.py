from nonebot import require
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import on_alconna

from .cmd_parser import alconna

# 使用命令解析器 Alconna 注册事件响应器
rss_cmd = on_alconna(alconna, permission=GROUP_OWNER | GROUP_ADMIN | SUPERUSER)

# 注册事件处理函数
from . import add_rss as add_rss
from . import delete_rss as delete_rss
from . import edit_rss as edit_rss
from . import get_rss_info as get_rss_info
from . import list_rss as list_rss
from . import operate_rss as operate_rss
