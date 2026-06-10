from nonebot.adapters import Bot, Event
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import Arparma

from ..rss import RSS
from ..scheduler import create_rss_update_job, remove_rss_update_job
from . import rss_cmd
from .tools import option_group_id, resolve_command_target


@rss_cmd.assign("删除")
async def delete_rss(
    bot: Bot,
    event: Event,
    result: Arparma,
    names: tuple[str, ...],
):
    group_id = option_group_id(result, "删除")
    target = await resolve_command_target(bot, event, group_id)
    if target is None:
        await rss_cmd.finish("❌ 只有超级用户可以指定群组")

    success: list[str] = []
    fail: list[str] = []
    for name in names:
        rss = await RSS.get_by_name(name)
        if rss is None:
            fail.append(name)
            continue

        done = False
        if target.scene_type == "private" and target.user_id is not None:
            done = rss.remove_subscriber(user_id=target.user_id)
        elif target.scene_type == "group" and target.group_id is not None:
            done = rss.remove_subscriber(group_id=target.group_id)

        if not done:
            fail.append(name)
            continue

        success.append(name)
        if any([rss.user_id, rss.group_id]):
            await create_rss_update_job(rss)
        else:
            remove_rss_update_job(rss)
            rss.destroy()

    msgs: list[str] = []
    if success:
        msgs.append(f"👏 成功取消订阅：{'，'.join(success)}")
    if fail:
        msgs.append(f"❌ 未找到订阅：{'，'.join(fail)}")
    await rss_cmd.finish("\n".join(msgs))


@rss_cmd.assign("彻底删除")
async def destroy_rss(bot: Bot, event: Event, names: tuple[str, ...]):
    if not await SUPERUSER(bot, event):
        await rss_cmd.finish("❌ 只有超级用户可以彻底删除订阅")

    success: list[str] = []
    fail: list[str] = []
    for name in names:
        rss = await RSS.get_by_name(name)
        if rss is None:
            fail.append(name)
            continue
        remove_rss_update_job(rss)
        rss.destroy()
        success.append(name)

    msgs: list[str] = []
    if success:
        msgs.append(f"👏 已彻底删除订阅：{'，'.join(success)}")
    if fail:
        msgs.append(f"❌ 未找到订阅：{'，'.join(fail)}")
    await rss_cmd.finish("\n".join(msgs))
