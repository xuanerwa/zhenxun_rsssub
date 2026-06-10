from __future__ import annotations

from tortoise import fields
from zhenxun.services.db_context import Model


class RssFeed(Model):
    """RSS订阅基本信息表"""
    
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    name = fields.CharField(255, description="订阅名称", unique=True)
    """订阅名称"""
    url = fields.CharField(500, description="订阅地址")
    """订阅地址"""
    user_id = fields.JSONField(description="订阅用户ID列表", default=list)
    """订阅用户ID列表"""
    group_id = fields.JSONField(description="订阅群组ID列表", default=list)
    """订阅群组ID列表"""
    use_proxy = fields.BooleanField(default=False, description="是否使用代理")
    """是否使用代理"""
    frequency = fields.CharField(50, default="5", description="更新频率(分钟/次)")
    """更新频率"""
    only_feed_title = fields.BooleanField(default=False, description="仅推送标题")
    """仅推送标题"""
    only_feed_pic = fields.BooleanField(default=False, description="仅推送图片")
    """仅推送图片"""
    download_pic = fields.BooleanField(default=False, description="是否下载图片")
    """是否下载图片"""
    cookie = fields.TextField(null=True, description="获取订阅更新时使用的cookie")
    """获取订阅更新时使用的cookie"""
    white_list_keyword = fields.TextField(null=True, description="白名单关键词")
    """白名单关键词"""
    black_list_keyword = fields.TextField(null=True, description="黑名单关键词")
    """黑名单关键词"""
    deduplication_modes = fields.JSONField(description="去重模式", default=list)
    """去重模式"""
    max_image_number = fields.IntField(default=0, description="图片数量限制")
    """图片数量限制"""
    content_to_remove = fields.JSONField(description="正文待移除内容", default=list)
    """正文待移除内容"""
    send_merged_msg = fields.BooleanField(default=False, description="是否发送合并消息")
    """是否发送合并消息"""
    show_hidden_content = fields.BooleanField(default=False, description="是否显示隐藏内容")
    """是否显示隐藏内容"""
    stop = fields.BooleanField(default=False, description="停止更新")
    """停止更新"""
    etag = fields.CharField(255, null=True, description="HTTP ETag")
    """HTTP ETag"""
    last_modified = fields.CharField(255, null=True, description="上次更新时间")
    """上次更新时间"""
    http_cache = fields.JSONField(description="HTTP缓存状态", default=dict)
    """HTTP缓存状态"""
    last_bozo = fields.BooleanField(default=False, description="最近一次feedparser解析异常标记")
    """最近一次feedparser解析异常标记"""
    last_bozo_exception = fields.TextField(null=True, description="最近一次feedparser解析异常说明")
    """最近一次feedparser解析异常说明"""
    error_count = fields.IntField(default=0, description="连续抓取失败的次数")
    """连续抓取失败的次数"""
    next_retry_at = fields.CharField(255, null=True, description="下一次允许重试的时间")
    """下一次允许重试的时间"""
    last_success_at = fields.CharField(255, null=True, description="最近一次成功抓取时间")
    """最近一次成功抓取时间"""
    last_error = fields.TextField(null=True, description="最近一次错误说明")
    """最近一次错误说明"""
    last_fetch_result = fields.JSONField(description="最近一次抓取结构化结果", default=dict)
    """最近一次抓取结构化结果"""
    feed_ttl_minutes = fields.IntField(null=True, description="feed推荐的最小更新间隔（分钟）")
    """feed推荐的最小更新间隔"""
    feed_skip_hours = fields.JSONField(description="feed建议跳过的小时", default=list)
    """feed建议跳过的小时"""
    feed_skip_days = fields.JSONField(description="feed建议跳过的星期", default=list)
    """feed建议跳过的星期"""
    next_recommended_update_at = fields.CharField(255, null=True, description="下次建议拉取时间")
    """下次建议拉取时间"""
    last_metrics = fields.JSONField(description="最近一次运行观测指标", default=dict)
    """最近一次运行观测指标"""
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    """创建时间"""
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    """更新时间"""

    class Meta:
        table = "rss_feeds"
        table_description = "RSS订阅基本信息"


class RssEntry(Model):
    """RSS文章条目表"""
    
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    feed_name = fields.CharField(255, description="订阅名称")
    """订阅名称"""
    entry_hash = fields.CharField(255, description="文章哈希值")
    """文章哈希值"""
    data = fields.JSONField(description="文章数据")
    """文章数据"""
    entry_datetime = fields.CharField(255, null=True, description="文章发布时间")
    """文章发布时间"""
    to_send = fields.BooleanField(default=False, description="是否待发送")
    """是否待发送"""
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    """创建时间"""
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    """更新时间"""

    class Meta:
        table = "rss_entries"
        table_description = "RSS文章条目"
        indexes = [("feed_name", "entry_hash")]


class RssDeliveryLog(Model):
    """RSS投递日志表"""
    
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    feed_name = fields.CharField(255, description="订阅名称")
    """订阅名称"""
    entry_hash = fields.CharField(255, description="文章哈希值")
    """文章哈希值"""
    target_type = fields.CharField(50, description="目标类型(private/group)")
    """目标类型"""
    target_id = fields.CharField(255, description="目标ID")
    """目标ID"""
    status = fields.CharField(50, description="投递状态(success/failed)")
    """投递状态"""
    error = fields.TextField(null=True, description="错误信息")
    """错误信息"""
    message_id = fields.CharField(255, null=True, description="消息ID")
    """消息ID"""
    time = fields.CharField(255, null=True, description="投递时间")
    """投递时间"""
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    """创建时间"""
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    """更新时间"""

    class Meta:
        table = "rss_delivery_log"
        table_description = "RSS投递日志"
        indexes = [("feed_name", "entry_hash", "target_type", "target_id")]


class RssFeedState(Model):
    """RSS订阅状态表"""
    
    id = fields.IntField(pk=True, generated=True, auto_increment=True)
    """自增id"""
    feed_name = fields.CharField(255, description="订阅名称")
    """订阅名称"""
    state_key = fields.CharField(255, description="状态键")
    """状态键"""
    state_value = fields.TextField(null=True, description="状态值")
    """状态值"""
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")
    """更新时间"""

    class Meta:
        table = "rss_feed_state"
        table_description = "RSS订阅状态"
        indexes = [("feed_name", "state_key")]
