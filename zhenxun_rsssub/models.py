from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class FetchResult:
    """Structured RSS fetch outcome used by status, retry and diagnostics."""

    ok: bool
    status: int | None
    url: str
    source: Literal["primary", "fallback"]
    cached: bool = False
    headers: dict[str, str] = field(default_factory=dict)
    bozo: bool = False
    bozo_exception: str | None = None
    error: str | None = None
    elapsed_ms: float = 0.0
    content_length: int = 0
    retry_after: int | None = None
    timing_hint_xml: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "url": self.url,
            "source": self.source,
            "cached": self.cached,
            "headers": self.headers,
            "bozo": self.bozo,
            "bozo_exception": self.bozo_exception,
            "error": self.error,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "content_length": self.content_length,
            "retry_after": self.retry_after,
        }


def compact_error(error: str | None, limit: int = 240) -> str | None:
    if not error:
        return None
    error = " ".join(str(error).split())
    if len(error) <= limit:
        return error
    return error[: limit - 3] + "..."
