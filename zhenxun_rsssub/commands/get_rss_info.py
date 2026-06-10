from nonebot_plugin_alconna import Arparma

from . import rss_cmd
from .tools import (
    TargetResolveError,
    find_target_rss,
    option_group_id,
    resolve_command_target,
)


def _flag(value: bool, true_text: str = "on", false_text: str = "off") -> str:
    return true_text if value else false_text


@rss_cmd.assign("详情")
async def get_rss_information(bot, event, result: Arparma, name: str):
    group_id = option_group_id(result, "详情")
    try:
        target = await resolve_command_target(bot, event, group_id)
    except TargetResolveError as e:
        await rss_cmd.finish(str(e))

    rss = await find_target_rss(target, name)
    if rss is None:
        await rss_cmd.finish("找不到该订阅")

    msgs = [
        f"订阅名：{rss.name} | 状态 {_flag(not rss.stop, 'enabled', 'paused')}",
        f"订阅地址：{rss.url}",
        f"更新频率：{rss.frequency}",
        f"?? {_flag(rss.use_proxy)} | Cookie "
        f"{_flag(bool(rss.cookie), 'set', 'empty')}",
        f"仅标题 {_flag(rss.only_feed_title)} | 仅图片 {_flag(rss.only_feed_pic)}",
        f"下载图片 {_flag(rss.download_pic)} | 合并转发 {_flag(rss.send_merged_msg)}",
        f"合并窗口：{rss.merge_window_minutes} 分钟",
        f"隐藏内容显示 {_flag(rss.show_hidden_content)}",
        f"白名单关键词：{rss.white_list_keyword}",
        f"黑名单关键词：{rss.black_list_keyword}",
        f"去重模式：{rss.deduplication_modes}",
        f"图片数量限制：{rss.max_image_number}",
        f"河蟹关键词：{rss.content_to_remove}",
    ]
    await rss_cmd.finish("\n".join(msgs))
