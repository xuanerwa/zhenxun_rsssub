from __future__ import annotations

from dataclasses import dataclass

from nonebot import get_driver
from nonebot.drivers import Request, Response

from .globals import plugin_config


@dataclass(slots=True)
class RssHttpResponse:
    status: int
    headers: dict[str, str]
    text: str
    content: bytes


def get_proxy(use_proxy: bool) -> str | None:
    if not use_proxy or not plugin_config.proxy:
        return None
    return str(plugin_config.proxy)


def _wrap_response(resp: Response) -> RssHttpResponse:
    content = resp.content or b""
    if isinstance(content, str):
        raw = content.encode("utf-8")
        text = content
    else:
        raw = bytes(content)
        encoding = _encoding_from_headers(
            {k.lower(): v for k, v in resp.headers.items()}
        )
        text = raw.decode(encoding, errors="replace")
    return RssHttpResponse(
        status=resp.status_code,
        headers={k.lower(): v for k, v in resp.headers.items()},
        text=text,
        content=raw,
    )


def _encoding_from_headers(headers: dict[str, str]) -> str:
    content_type = headers.get("content-type", "")
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("charset="):
            return part.split("=", 1)[1].strip() or "utf-8"
    return "utf-8"


def _raise_for_unaccepted(
    resp: Response, accept_status_codes: tuple[int, ...] | None
) -> None:
    if 200 <= resp.status_code < 300:
        return
    if accept_status_codes and resp.status_code in accept_status_codes:
        return
    text = _wrap_response(resp).text
    raise RuntimeError(f"HTTP {resp.status_code}: {text[:200]}")


async def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: str | dict[str, str] | None = None,
    proxy: str | None = None,
    timeout: float = 10,
) -> Response:
    return await get_driver().request(
        Request(
            method,
            url,
            headers=headers,
            params=params,
            proxy=proxy,
            timeout=timeout,
        )
    )


async def get_text_response(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    proxy: str | None = None,
    timeout: float = 10,
    accept_status_codes: tuple[int, ...] = (304,),
) -> RssHttpResponse:
    resp = await _request("GET", url, headers=headers, proxy=proxy, timeout=timeout)
    _raise_for_unaccepted(resp, accept_status_codes)
    return _wrap_response(resp)


async def get_bytes_response(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    proxy: str | None = None,
    timeout: float = 10,
    accept_status_codes: tuple[int, ...] | None = None,
) -> RssHttpResponse:
    resp = await _request("GET", url, headers=headers, proxy=proxy, timeout=timeout)
    _raise_for_unaccepted(resp, accept_status_codes)
    return _wrap_response(resp)
