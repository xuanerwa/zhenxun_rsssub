from nonebot import require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import on_alconna

from ..access_control import rss_command_rule
from .cmd_parser import alconna

# 使用命令解析器 Alconna 注册事件响应器
rss_cmd = on_alconna(alconna, rule=rss_command_rule(5), priority=5, block=True)

# 注册事件处理函数
from . import add_rss as add_rss
from . import config_rss as config_rss
from . import delete_rss as delete_rss
from . import edit_rss as edit_rss
from . import get_rss_info as get_rss_info
from . import list_rss as list_rss
from . import operate_rss as operate_rss
