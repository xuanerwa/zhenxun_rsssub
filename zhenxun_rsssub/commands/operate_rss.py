from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arclet.alconna import Arparma
from nonebot_plugin_alconna import UniMessage

from ..globals import plugin_config
from ..host_adapter import get_event_target
from ..opml import export_opml, import_opml, looks_like_opml
from ..rss import RSS
from ..scheduler import create_rss_update_job
from . import rss_cmd
from .tools import find_visible_rss, visible_rss_list

EXPORT_SCHEMA_VERSION = 2
SENSITIVE_KEYS = {"cookie"}


def _fetch_status_lines(rss: RSS) -> list[str]:
    result = rss.last_fetch_result or {}
    if not result:
        return ["最近抓取：无"]
    return [
        "最近抓取："
        f"{'成功' if result.get('ok') else '失败'}"
        f"{' / 缓存命中' if result.get('cached') else ''}",
        f"抓取来源：{result.get('source') or '未知'}",
        f"状态码：{result.get('status') or '未知'}",
        f"抓取 URL：{result.get('url') or '未知'}",
        f"耗时：{result.get('elapsed_ms') or 0} ms",
        f"内容长度：{result.get('content_length') or 0} bytes",
    ]


def _metrics_status_lines(rss: RSS) -> list[str]:
    metrics = rss.last_metrics or {}
    if not metrics:
        return ["最近指标：无"]
    return [
        "最近指标："
        f"抓取 {metrics.get('fetch_ms') or 0}ms / "
        f"解析 {metrics.get('parse_ms') or 0}ms / "
        f"发送 {metrics.get('send_ms') or 0}ms",
        f"条目：{metrics.get('entry_count') or 0} / "
        f"新增：{metrics.get('new_entry_count') or 0} / "
        f"图片：{metrics.get('image_count') or 0} / "
        f"发送：{metrics.get('messages_sent') or 0}",
        f"指标错误：{metrics.get('error') or '无'}",
    ]


def _mask_sensitive_record(record: dict[str, Any]) -> dict[str, Any]:
    result = record.copy()
    for key in SENSITIVE_KEYS:
        value = result.get(key)
        if value:
            result[key] = "***MASKED***"
    return result


def _export_payload(rss_list: list[RSS], *, mask_sensitive: bool) -> dict[str, Any]:
    feeds = []
    for rss in rss_list:
        record = rss.to_record()
        feeds.append(_mask_sensitive_record(record) if mask_sensitive else record)
    return {
        "schema": "zhenxun_rsssub.export",
        "version": EXPORT_SCHEMA_VERSION,
        "masked_sensitive": mask_sensitive,
        "feeds": feeds,
    }


def _validate_import_payload(payload: Any) -> tuple[list[dict[str, Any]], list[str]]:
    errors = []
    if isinstance(payload, list):
        feeds = payload
    elif isinstance(payload, dict):
        version = payload.get("version")
        if version not in {1, EXPORT_SCHEMA_VERSION}:
            errors.append(f"不支持的 schema version：{version}")
        feeds = payload.get("feeds")
    else:
        return [], ["导入内容必须是对象或列表"]

    if not isinstance(feeds, list):
        return [], [*errors, "缺少 feeds 列表"]

    valid_feeds = []
    for index, item in enumerate(feeds, 1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 项不是对象")
            continue
        if not item.get("name"):
            errors.append(f"第 {index} 项缺少 name")
        if not item.get("url"):
            errors.append(f"第 {index} 项缺少 url")
        if item.get("cookie") == "***MASKED***":
            item = item.copy()
            item["cookie"] = ""
        if item.get("name") and item.get("url"):
            valid_feeds.append(item)
    return valid_feeds, errors


def _import_summary(
    feeds: list[dict[str, Any]], errors: list[str], *, dry_run: bool
) -> str:
    names = [str(item.get("name")) for item in feeds]
    lines = [
        ("🧪 导入预检" if dry_run else "✅ 导入完成") + f"：{len(feeds)} 条有效订阅",
    ]
    if names:
        lines.append("订阅：" + "，".join(names[:20]))
    if len(names) > 20:
        lines.append(f"...以及 {len(names) - 20} 条")
    if errors:
        lines.append("问题：")
        lines.extend(f"- {error}" for error in errors[:10])
    return "\n".join(lines)


async def _send_export_file(
    text: str, name: str | None, *, suffix: str, mimetype: str
) -> bool:
    filename = f"rss_export_{name or 'all'}.{suffix}"
    try:
        await UniMessage.file(
            raw=text.encode("utf-8"),
            name=filename,
            mimetype=mimetype,
        ).send()
    except Exception:
        return False
    return True


def _attach_current_target(event: object, record: dict[str, Any]) -> dict[str, Any]:
    target = get_event_target(event)
    record = record.copy()
    if target.scene_type == "private" and target.user_id is not None:
        users = set(record.get("user_id") or [])
        users.add(target.user_id)
        record["user_id"] = list(users)
    elif target.scene_type == "group" and target.group_id is not None:
        groups = set(record.get("group_id") or [])
        groups.add(target.group_id)
        record["group_id"] = list(groups)
    return record


@rss_cmd.assign("测试")
async def test_rss(event, name: str):
    rss = find_visible_rss(event, name)
    if rss is None:
        await rss_cmd.finish("❌ 找不到该订阅")

    _, message = await rss.test_parse()
    await rss_cmd.finish(message)


@rss_cmd.assign("拉取")
async def pull_rss(event, name: str):
    rss = find_visible_rss(event, name)
    if rss is None:
        await rss_cmd.finish("❌ 找不到该订阅")

    await rss.update(force=True)
    latest = RSS.get_by_name(rss.name) or rss
    fetch_lines = _fetch_status_lines(latest)
    await rss_cmd.finish(
        "\n".join(
            [
                f"✅ 已手动拉取：{latest.name}",
                f"失败次数：{latest.error_count}",
                f"最后成功：{latest.last_success_at or '无'}",
                f"最近错误：{latest.last_error or '无'}",
                *fetch_lines,
            ]
        )
    )


@rss_cmd.assign("状态")
async def rss_status(event, name: str | None = None):
    rss_list = visible_rss_list(event)
    if name:
        rss_list = [rss for rss in rss_list if rss.name == name]
    if not rss_list:
        await rss_cmd.finish("❌ 没有找到订阅")

    lines = [f"📡 RSS 状态：{len(rss_list)} 条"]
    for rss in rss_list:
        lines.extend(
            [
                f"\n{'🔴' if rss.stop else '🟢'} {rss.name}",
                f"失败次数：{rss.error_count}",
                f"最后成功：{rss.last_success_at or '无'}",
                f"下次重试：{rss.next_retry_at or '无'}",
                f"下次推荐拉取：{rss.next_recommended_update_at or '无'}",
                f"Feed TTL：{rss.feed_ttl_minutes or '无'} 分钟",
                f"SkipHours：{rss.feed_skip_hours or '无'}",
                f"SkipDays：{rss.feed_skip_days or '无'}",
                f"ETag：{rss.etag or '无'}",
                f"Last-Modified：{rss.last_modified or '无'}",
                f"Bozo: {'yes' if rss.last_bozo else 'no'}",
                f"最近错误：{rss.last_error or rss.last_bozo_exception or '无'}",
                *_fetch_status_lines(rss),
                *_metrics_status_lines(rss),
            ]
        )
    await rss_cmd.finish("\n".join(lines))


@rss_cmd.assign("导出")
async def export_rss(event, name: str | None = None, result: Arparma | None = None):
    raw_args = result.all_matched_args if result else {}
    options_set = set(raw_args.get("options") or ())
    as_file = "file" in options_set or "文件" in options_set
    as_opml = "opml" in options_set or "OPML" in options_set
    raw_export = "raw" in options_set or "原始" in options_set
    mask_sensitive = plugin_config.export_mask_sensitive and not raw_export
    rss_list = visible_rss_list(event)
    if name:
        rss_list = [rss for rss in rss_list if rss.name == name]
    if not rss_list:
        await rss_cmd.finish("❌ 没有找到订阅")

    if as_opml:
        opml_text = export_opml(rss_list)
        if as_file and await _send_export_file(
            opml_text, name, suffix="opml", mimetype="text/x-opml+xml"
        ):
            await rss_cmd.finish("✅ 已导出 OPML 文件")
        await rss_cmd.finish(opml_text)

    payload = _export_payload(rss_list, mask_sensitive=mask_sensitive)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    if as_file and await _send_export_file(
        json_text, name, suffix="json", mimetype="application/json"
    ):
        await rss_cmd.finish("✅ 已导出 JSON 文件")
    await rss_cmd.finish(json_text)


@rss_cmd.assign("导入")
async def import_rss(event, data: tuple[str, ...]):
    text = " ".join(data).strip()
    if not text:
        await rss_cmd.finish("❌ 请提供 export 生成的 JSON 内容或 JSON 文件路径")

    dry_run = False
    if text.startswith("--dry-run "):
        dry_run = True
        text = text.removeprefix("--dry-run ").strip()
    elif text == "--dry-run":
        await rss_cmd.finish("❌ dry-run 需要提供 JSON 内容或文件路径")

    if text.startswith("file:"):
        text = text.removeprefix("file:").strip()
    path = Path(text)
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8")

    if looks_like_opml(text):
        feeds, errors = import_opml(text)
        feeds = [_attach_current_target(event, item) for item in feeds]
    else:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as e:
            await rss_cmd.finish(f"❌ JSON 解析失败：{e}")
        feeds, errors = _validate_import_payload(payload)

    if dry_run:
        await rss_cmd.finish(_import_summary(feeds, errors, dry_run=True))
    if not feeds:
        await rss_cmd.finish(_import_summary(feeds, errors, dry_run=False))

    imported: list[str] = []
    failed: list[str] = []
    for item in feeds:
        if not isinstance(item, dict) or not item.get("name") or not item.get("url"):
            failed.append(
                str(item.get("name", "未知")) if isinstance(item, dict) else "?"
            )
            continue
        try:
            existing = RSS.get_by_name(str(item.get("name")))
            if existing is not None:
                new_rss = RSS.from_record({**existing.to_record(), **item})
                new_rss.upsert(existing.name)
                rss = new_rss
            else:
                rss = RSS.from_record(item)
                rss.upsert()
            if not rss.stop:
                await create_rss_update_job(rss, run_immediately=False)
            imported.append(rss.name)
        except Exception:
            failed.append(str(item.get("name", "未知")))

    msg = [f"✅ 导入完成：{len(imported)} 条"]
    if imported:
        msg.append("成功：" + "，".join(imported))
    if failed:
        msg.append("失败：" + "，".join(failed))
    await rss_cmd.finish("\n".join(msg))
