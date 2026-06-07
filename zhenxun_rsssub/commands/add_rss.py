from yarl import URL

from ..host_adapter import get_event_target
from ..rss import RSS
from ..scheduler import create_rss_update_job
from . import rss_cmd


@rss_cmd.assign("添加")
async def add_rss(event, name: str, url: str):
    if RSS.get_by_name(name) is not None:
        await rss_cmd.finish(
            f"⚠️ 已存在同名订阅 {name}，请更换名称或使用 edit 命令追加订阅者"
        )

    rss = RSS(name=name, url=URL(url))
    target = get_event_target(event)
    rss.add_subscriber(user_id=target.user_id, group_id=target.group_id)
    await create_rss_update_job(rss, run_immediately=True)
    await rss_cmd.finish(f"👏 已成功添加订阅 {name}")
