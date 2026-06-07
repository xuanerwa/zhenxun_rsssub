from ..host_adapter import get_event_target
from ..rss import RSS
from . import rss_cmd


@rss_cmd.assign("列表")
async def list_rss(event):
    target = get_event_target(event)
    if target.scene_type == "private":
        rss_list = [rss for rss in RSS.load_rss_data() if target.user_id in rss.user_id]
    elif target.scene_type == "group":
        rss_list = [
            rss for rss in RSS.load_rss_data() if target.group_id in rss.group_id
        ]
    else:
        rss_list = []

    if not rss_list:
        await rss_cmd.finish("❌ 当前没有任何订阅")

    msgs = [f"📄 当前有 {len(rss_list)} 条订阅"]
    for rss in rss_list:
        msgs.append(f"{'🔴' if rss.stop else '🟢'} {rss.name}")
    await rss_cmd.finish("\n".join(msgs))
