from copy import deepcopy
import re

from yarl import URL

from ..host_adapter import get_event_target, is_group_event
from ..repository_entries import rename_entries_file
from ..rss import RSS
from ..scheduler import create_rss_update_job, remove_rss_update_job
from . import rss_cmd


def handle_edit_name(rss: RSS, value: str, event=None):
    remove_rss_update_job(rss)
    old_name = rss.name
    rss.name = value
    rename_entries_file(old_name, rss.name)


def handle_edit_url(rss: RSS, value: str, event=None):
    rss.url = URL(value)


def handle_edit_user_id(rss: RSS, value: str, event=None):
    if event is None:
        return
    if is_group_event(event):
        rss_cmd.send("❌ 禁止在群组中修改订阅账号，如要取消订阅请使用 del 命令！")
        return
    if value == "-1":
        rss.user_id = set()
        return

    new_users = {int(uid) for uid in value.split(",") if len(uid) > 0}
    if value.startswith(","):
        rss.user_id |= new_users
    else:
        rss.user_id = new_users


def handle_edit_group_id(rss: RSS, value: str, event=None):
    if event is None:
        return
    if is_group_event(event):
        raise Exception("❌ 禁止在群组中修改订阅账号，如要取消订阅请使用 del 命令！")
    if value == "-1":
        rss.group_id = set()
        return

    new_groups = {int(gid) for gid in value.split(",") if len(gid) > 0}
    if value.startswith(","):
        rss.group_id |= new_groups
    else:
        rss.group_id = new_groups


def handle_edit_use_proxy(rss: RSS, value: str, event=None):
    rss.use_proxy = bool(int(value))


def handle_edit_frequency(rss: RSS, value: str, event=None):
    if re.search(r"[_*/,-]", value):
        rss.frequency = value
    else:
        if int(float(value)) < 1:
            rss.frequency = "1"
        else:
            rss.frequency = str(int(float(value)))


def handle_edit_only_feed_title(rss: RSS, value: str, event=None):
    rss.only_feed_title = bool(int(value))


def handle_edit_only_feed_pic(rss: RSS, value: str, event=None):
    rss.only_feed_pic = bool(int(value))


def handle_edit_download_pic(rss: RSS, value: str, event=None):
    rss.download_pic = bool(int(value))


def handle_edit_cookie(rss: RSS, value: str, event=None):
    rss.cookie = value


def handle_edit_white_list_keyword(rss: RSS, value: str, event=None):
    if value == "-1":
        rss.white_list_keyword = ""
        return
    re.compile(value)
    rss.white_list_keyword = value


def handle_edit_black_list_keyword(rss: RSS, value: str, event=None):
    if value == "-1":
        rss.black_list_keyword = ""
        return
    re.compile(value)
    rss.black_list_keyword = value


def handle_edit_deduplication_modes(rss: RSS, value: str, event=None):
    if not value.startswith(("+", "-")):
        raise Exception("❌ mode 参数错误")
    operation = value[0]
    mode = value[1:]
    if mode not in {"title", "link", "or"}:
        raise Exception("❌ mode 参数错误")
    if operation == "+":
        rss.deduplication_modes.add(mode)
    else:
        rss.deduplication_modes.discard(mode)


def handle_edit_max_image_number(rss: RSS, value: str, event=None):
    if not value.isdigit() or int(value) < 0:
        raise Exception("❌ max_image_number 参数错误")
    rss.max_image_number = int(value)


def handle_exit_content_to_remove(rss: RSS, value: str, event=None):
    if not value.startswith(("+", "-")):
        raise Exception("❌ hexie 参数错误")
    operation = value[0]
    keyword = value[1:]
    if operation == "+":
        rss.content_to_remove.add(keyword)
    else:
        rss.content_to_remove.discard(keyword)


def handle_edit_send_merge_msg(rss: RSS, value: str, event=None):
    rss.send_merged_msg = bool(int(value))


def handle_edit_stop(rss: RSS, value: str, event=None):
    rss.stop = bool(int(value))


EDIT_HANDLERS = {
    "name": handle_edit_name,
    "url": handle_edit_url,
    "qq": handle_edit_user_id,
    "qun": handle_edit_group_id,
    "proxy": handle_edit_use_proxy,
    "freq": handle_edit_frequency,
    "ot": handle_edit_only_feed_title,
    "op": handle_edit_only_feed_pic,
    "dp": handle_edit_download_pic,
    "cookie": handle_edit_cookie,
    "wkey": handle_edit_white_list_keyword,
    "bkey": handle_edit_black_list_keyword,
    "mode": handle_edit_deduplication_modes,
    "image": handle_edit_max_image_number,
    "hexie": handle_exit_content_to_remove,
    "merge": handle_edit_send_merge_msg,
    "stop": handle_edit_stop,
}

EDIT_KEY_ALIASES = {
    "名称": "name",
    "地址": "url",
    "账号": "qq",
    "群": "qun",
    "群号": "qun",
    "代理": "proxy",
    "频率": "freq",
    "间隔": "freq",
    "仅标题": "ot",
    "只标题": "ot",
    "仅图片": "op",
    "只图片": "op",
    "下载图片": "dp",
    "白名单": "wkey",
    "黑名单": "bkey",
    "去重": "mode",
    "模式": "mode",
    "图片": "image",
    "图片数": "image",
    "河蟹": "hexie",
    "过滤": "hexie",
    "合并": "merge",
    "暂停": "stop",
    "停止": "stop",
}

BOOL_VALUE_ALIASES = {
    "开": "1",
    "开启": "1",
    "启用": "1",
    "是": "1",
    "真": "1",
    "true": "1",
    "on": "1",
    "关": "0",
    "关闭": "0",
    "禁用": "0",
    "否": "0",
    "假": "0",
    "false": "0",
    "off": "0",
}

BOOL_KEYS = {"proxy", "ot", "op", "dp", "merge", "stop"}

EDIT_HELP = {
    "名称": "名称=新订阅名",
    "地址": "地址=https://example.com/rss.xml",
    "频率": "频率=5 或 频率=*/10_*_*_*_*",
    "代理": "代理=开/关",
    "仅标题": "仅标题=开/关",
    "仅图片": "仅图片=开/关",
    "下载图片": "下载图片=开/关",
    "cookie": "cookie=xxx",
    "白名单": "白名单=正则 或 白名单=-1 清空",
    "黑名单": "黑名单=正则 或 黑名单=-1 清空",
    "去重": "去重=+title/link/or 或 去重=-title/link/or",
    "图片": "图片=0 或 图片=5",
    "河蟹": "河蟹=+正则 或 河蟹=-正则",
    "合并": "合并=开/关",
    "暂停": "暂停=开/关",
}


def format_edit_keys() -> str:
    return "可用属性：\n" + "\n".join(
        f"- {key}: {usage}" for key, usage in EDIT_HELP.items()
    )


def parse_edit_option(option: str) -> tuple[str, str]:
    if "=" not in option:
        raise ValueError(
            f"参数 `{option}` 缺少 `=`。\n"
            f"示例：频率=30 或 代理=开\n{format_edit_keys()}"
        )
    key, value = option.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"参数 `{option}` 的属性名为空。\n{format_edit_keys()}")
    normalized_key = EDIT_KEY_ALIASES.get(key, key)
    if normalized_key not in EDIT_HANDLERS:
        raise ValueError(f"属性 `{key}` 不存在。\n{format_edit_keys()}")
    value = value.strip()
    if normalized_key in BOOL_KEYS:
        value = BOOL_VALUE_ALIASES.get(value.lower(), value)
    return normalized_key, value


@rss_cmd.assign("设置")
async def edit_rss(event, name: str, options: list[str]):
    rss = RSS.get_by_name(name)
    target = get_event_target(event)
    missing = not rss
    if rss and target.scene_type == "private":
        missing = target.user_id not in rss.user_id
    elif rss and target.scene_type == "group":
        missing = target.group_id not in rss.group_id
    if missing:
        await rss_cmd.finish("❌ 找不到该订阅")
    if rss is None:
        return

    old_name = rss.name
    new_rss = deepcopy(rss)

    for option in options:
        try:
            key, value = parse_edit_option(option)
        except ValueError as e:
            await rss_cmd.finish(f"❌ 修改参数格式错误：\n{e}")

        try:
            EDIT_HANDLERS[key](new_rss, value, event)
        except Exception as e:
            await rss_cmd.finish(f"❌ 修改 {key} 失败，错误信息:\n{e}")

    # 参数更新完毕，写入数据库
    new_rss.upsert(old_name)

    # 更新定时任务
    if not new_rss.stop:
        # 更新之后的 RSS 没有停止更新，则添加定时任务
        await create_rss_update_job(new_rss)
    elif not rss.stop:
        # 更新之后的 RSS 停止更新了，说明想让原来的 RSS 停止更新，则删除定时任务
        remove_rss_update_job(rss)

    await rss_cmd.finish("👏 修改成功")
