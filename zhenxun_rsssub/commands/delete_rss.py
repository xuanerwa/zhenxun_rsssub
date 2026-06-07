from ..host_adapter import get_event_target
from ..rss import RSS
from ..scheduler import create_rss_update_job, remove_rss_update_job
from . import rss_cmd


@rss_cmd.assign("删除")
async def delete_rss(event, names: tuple[str, ...]):
    success: list[str] = []
    fail: list[str] = []

    target = get_event_target(event)
    for name in names:
        rss = RSS.get_by_name(name)
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
        else:
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
