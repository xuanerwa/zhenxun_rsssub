from nonebot_plugin_alconna import Arparma
from yarl import URL

from ..rss import RSS
from ..scheduler import create_rss_update_job
from . import rss_cmd
from .tools import TargetResolveError, option_group_id, resolve_command_target


def _same_url(saved_rss: RSS, input_url: str) -> bool:
    normalized_input = str(URL(input_url))
    return normalized_input in {str(saved_rss.url), saved_rss.get_url()}


def _target_already_subscribed(rss: RSS, target) -> bool:
    if target.scene_type == "private" and target.user_id is not None:
        return target.user_id in rss.user_id
    if target.scene_type == "group" and target.group_id is not None:
        return target.group_id in rss.group_id
    return False


@rss_cmd.assign("添加")
async def add_rss(bot, event, result: Arparma, name: str, url: str | None = None):
    group_id = option_group_id(result, "添加")
    try:
        target = await resolve_command_target(bot, event, group_id)
    except TargetResolveError as e:
        await rss_cmd.finish(str(e))

    rss = await RSS.get_by_name(name)
    if rss is not None:
        if url and not _same_url(rss, url):
            await rss_cmd.finish(
                f"⚠️ 已存在同名订阅 {name}，且地址与已有订阅不一致，"
                "请更换订阅名称"
            )

        if _target_already_subscribed(rss, target):
            await rss_cmd.finish(f"⚠️ 当前会话已订阅 {name}")

        rss.add_subscriber(user_id=target.user_id, group_id=target.group_id)
        rss.upsert()
        await create_rss_update_job(rss, run_immediately=False)
        await rss_cmd.finish(
            f"👏 已将当前会话追加到订阅 {name}"
        )

    if not url:
        await rss_cmd.finish(
            f"❌ 找不到订阅 {name}，请提供订阅地址：订阅姬 添加 {name} <RSS地址>"
        )

    rss = RSS(name=name, url=URL(url))
    rss.add_subscriber(user_id=target.user_id, group_id=target.group_id)
    await create_rss_update_job(rss, run_immediately=True)
    await rss_cmd.finish(f"👏 已成功添加订阅 {name}")
