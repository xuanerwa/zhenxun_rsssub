from pydantic import AnyUrl, BaseModel, Field, HttpUrl


class ScopedConfig(BaseModel):
    debug: bool = False
    rsshub_url: HttpUrl = "https://rsshub.app"
    rsshub_fallback_urls: list[HttpUrl] = Field(default_factory=list)
    proxy: AnyUrl | None = None
    black_words: list[str] | None = None
    cache_expire: int = 14
    blockquote: bool = True
    image_compress_size: int = 2 * 1024
    gif_compress_size: int = 6 * 1024
    enable_online_gif_compress: bool = False
    media_download_concurrency: int = 4
    media_cache_ttl_seconds: int = 300
    media_cache_max_items: int = 256
    max_media_bytes_per_update: int = 20 * 1024 * 1024
    max_length: int = 500
    rss_entries_file_limit: int = 200
    export_mask_sensitive: bool = True
    scheduler_batch_interval_seconds: int = 60
    scheduler_batch_concurrency: int = 4
    scheduler_per_host_concurrency: int = 1


class Config(BaseModel):
    dingyueji: ScopedConfig = Field(default_factory=ScopedConfig)
