from __future__ import annotations

import json
import re
from typing import Any


def sanitize_feed_name(name: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    if sanitized == "rss":
        sanitized = "rss_default"
    return sanitized


def feed_key(name: str) -> str:
    return sanitize_feed_name(name) or name


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default
