from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import Arparma

from . import rss_cmd
from .tools import (
    TargetResolveError,
    option_group_id,
    resolve_command_target,
    target_rss_list,
)


@rss_cmd.assign("列表")
async def list_rss(bot: Bot, event: Event, result: Arparma):
    group_id = option_group_id(result, "列表")
    try:
        target = await resolve_command_target(bot, event, group_id)
    except TargetResolveError as e:
        await rss_cmd.finish(str(e))

    rss_list = await target_rss_list(target)
    if not rss_list:
        await rss_cmd.finish("❌ 当前没有任何订阅")

    msgs = [f"📫 当前有 {len(rss_list)} 条订阅"]
    for rss in rss_list:
        msgs.append(f"{'🔴' if rss.stop else '🟢'} {rss.name}")
    await rss_cmd.finish("\n".join(msgs))
