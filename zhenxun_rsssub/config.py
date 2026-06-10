from typing import cast

from pydantic import AnyUrl, BaseModel, Field, HttpUrl


class ScopedConfig(BaseModel):
    debug: bool = False
    rsshub_url: HttpUrl = cast(HttpUrl, "https://rsshub.app")
    rsshub_fallback_urls: list[HttpUrl] = Field(default_factory=list)
    proxy: AnyUrl | None = None
    media_proxy: AnyUrl | None = None
    rss_entries_file_limit: int = 200
    export_mask_sensitive: bool = True
    scheduler_batch_concurrency: int = 4
    scheduler_per_host_concurrency: int = 1


class Config(BaseModel):
    dingyueji: ScopedConfig = Field(default_factory=ScopedConfig)
