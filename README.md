# 订阅姬 - RSS 订阅插件

## 📖 功能介绍

本插件是真寻机器人（zhenxun_bot）的 RSS 订阅管理插件，提供以下功能：

- 通过命令添加、删除、查询、修改 RSS 订阅
- 翻译 RSS 订阅内容（支持 DeepL、百度翻译等）
- 个性化订阅设置
  - 更新频率（支持分钟间隔或 crontab 表达式）
  - 仅发送标题/图片
  - 自动下载图片至本地
  - 推送过滤黑名单/白名单
  - 限制单条推送图片数量
  - 合并转发、按发布时间窗口合并、正文截断与长消息分段
- 图片压缩（支持 GIF 和非 GIF 图片）
- 根据标题、链接、图片自动去重已发送的消息
- 和谐推送中的敏感关键词
- 支持 RSSHub 路由快捷订阅
- 支持导入/导出订阅（JSON/OPML 格式）

## 💿 安装方法

### 前提条件

本插件依赖于 [真寻机器人（zhenxun_bot）](https://github.com/zhenxun-org/zhenxun_bot)，请确保已正确安装和配置真寻机器人。

### 安装步骤

#### 方法一：手动安装（推荐）

1. **克隆插件仓库**

   ```bash
   git clone https://github.com/xuanerwa/zhenxun_rsssub.git
   ```

2. **将插件放入真寻机器人的插件目录**

   将 `zhenxun_rsssub` 文件夹复制到真寻机器人的 `plugins` 目录下：

   ```bash
   # Linux/macOS
   cp -r zhenxun_rsssub /path/to/zhenxun_bot/plugins/
   
   # Windows (PowerShell)
   Copy-Item -Recurse zhenxun_rsssub C:\path\to\zhenxun_bot\plugins\
   ```

3. **安装依赖**

   **使用 uv（推荐）：**

   在真寻机器人项目根目录下执行：

   ```bash
   cd /path/to/zhenxun_bot
   # 从插件的 requirements.txt 安装依赖
   uv pip install -r plugins/zhenxun_rsssub/requirements.txt
   ```

   **或使用 pip：**

   ```bash
   cd /path/to/zhenxun_bot
   pip install -r plugins/zhenxun_rsssub/requirements.txt
   ```

4. **重启真寻机器人**

   ```bash
   # 使用 uv
   uv run zx
   
   # 或使用 Python
   python bot.py
   ```

5. **配置插件**

   首次启动后，插件配置会自动注册到真寻机器人的配置系统中。你可以通过以下方式配置：

   - **WebUI 配置**：访问真寻机器人的 WebUI，在插件管理中找到"订阅姬"进行配置
   - **配置文件**：编辑 `data/config.yaml` 文件中的 `dingyueji` 模块配置

---

## ⚙️ 配置说明

### 通过 WebUI 配置（推荐）

1. 启动真寻机器人后，访问 WebUI（默认地址：`http://localhost:8080`）
2. 进入"插件管理" → "订阅姬"
3. 修改相应的配置项并保存

### 通过配置文件修改

编辑 `data/config.yaml` 文件，找到 `dingyueji` 模块：

```yaml
dingyueji:
   DEBUG: false                    # 调试模式
   RSSHUB_URL: "https://rsshub.app"  # 默认 RSSHub 地址
   RSSHUB_FALLBACK_URLS: []        # 备用 RSSHub 地址列表
   PROXY: null                     # 代理地址（如 "http://127.0.0.1:7890"）
   MEDIA_PROXY: null               # 媒体下载专用代理；为空时使用真寻全局 system_proxy
   RSS_ENTRIES_FILE_LIMIT: 200     # RSS 条目文件保存数量限制
   EXPORT_MASK_SENSITIVE: true     # 导出时脱敏敏感字段
   SCHEDULER_BATCH_CONCURRENCY: 4  # 调度器批次并发数（静态配置）
   SCHEDULER_PER_HOST_CONCURRENCY: 1# 每个主机并发数（静态配置）
```

## 🔧 运行时配置（可热更）

说明：可通过 WebUI 或运行时命令修改，修改后立即生效，无需重启。仅超级用户可修改；在群组中操作时需要 @ 机器人。

主要运行时配置（键名为内部 `snake_case`，命令中也支持中文别名或键名）：

- `private_subscribe_superuser_only`（私聊仅超级用户）
- `group_whitelist_enabled`（启用群白名单）
- `group_whitelist`（群白名单）
- `black_words`（全局屏蔽词）
- `blockquote`（是否保留引用块）
- `push_with_link`（推送正文是否附带原文链接）
- `push_on_image_parse_failed`（图片解析失败时是否仍推送）
- `cache_expire`（去重缓存天数）
- `image_compress_size`（图片压缩阈值，注意：单位为像素，表示最长边像素长度）
- `gif_compress_size`（GIF 大小阈值，单位为 KB）
- `enable_online_gif_compress`（在线 GIF 压缩开关，当前服务已移除）
- `media_download_concurrency`（媒体下载并发数）
- `media_download_timeout_seconds`（单张媒体下载超时，秒）
- `media_cache_ttl_seconds`（媒体缓存存活时间，秒）
- `media_cache_max_items`（媒体缓存最大条目数）
- `max_media_bytes_per_update`（单轮媒体字节预算）
- `max_media_errors_per_update`（单轮媒体失败上限）
- `message_send_timeout_seconds`（单目标消息发送超时，秒）
- `scheduler_batch_interval_seconds`（调度扫描间隔，秒）
- `scheduler_update_timeout_seconds`（单订阅更新超时，秒）

示例命令（均以机器人命令前缀 `订阅姬` 开始，需为超级用户；群内需 @ 机器人）：

- 查看运行时配置状态：

```text
订阅姬 配置 状态
```

- 查看配置帮助（包含可用名称与填写示例）：

```text
订阅姬 配置 帮助
```

- 修改某项（支持键名或中文别名）：

```text
订阅姬 配置 图片失败推送=开
// 或
订阅姬 配置 push_on_image_parse_failed=on
```

- 修改群白名单（快捷命令示例）：

```text
订阅姬 配置 群白名单 添加 141514 123456
订阅姬 配置 群白名单 删除 141514
订阅姬 配置 群白名单 清空
```

修改后即时生效，错误或权限不足会返回相应提示；更多用法见机器人的帮助或 WebUI 中的插件说明。

### 翻译 API 配置（可选）

如需使用翻译功能，需要在 `.env` 文件中配置：

```env
# DeepL 翻译 API（可选）
DEEPL_API_KEY="your_deepl_api_key"

# 百度翻译 API（可选）
BAIDU_TRANSLATE_APPID="your_baidu_appid"
BAIDU_TRANSLATE_KEY="your_baidu_key"
```

修改后需重启真寻机器人使配置生效。

## 📜 使用说明

### 基本命令

所有命令均以 `订阅姬` 为前缀，也可以使用别名 `RSS` 或 `RSS订阅`。

#### 查看帮助

```text
订阅姬 帮助
```

获取详细的命令帮助信息。

---

### 订阅管理

#### 添加订阅

```text
订阅姬 添加 <订阅名> <订阅地址>
```

**示例：**

```text
订阅姬 添加 真寻更新 https://example.com/feed.xml
订阅姬 添加 B站动态 /bilibili/user/video/123456
订阅姬 添加 TG频道 /telegram/channel/botnews
```

**说明：**

- 订阅地址可以是完整的 URL 或 RSSHub 路由（以 `/` 开头）
- 订阅名不能包含空格

---

#### 删除订阅

```text
订阅姬 删除 <订阅名> [订阅名 ...]
```

**示例：**

```text
订阅姬 删除 真寻更新
订阅姬 删除 订阅1 订阅2 订阅3
```

**说明：** 支持批量删除多个订阅

#### 彻底删除订阅（仅超级用户）

```text
订阅姬 彻底删除 <订阅名> [订阅名 ...]
```

**说明：** 只有超级用户可以执行该命令，执行后会删除订阅及其全部状态数据。

---

#### 查看订阅列表

```text
订阅姬 列表
```

查看当前会话（群聊或私聊）的所有订阅。

---

#### 查看订阅详情

```text
订阅姬 详情 <订阅名>
```

**示例：**

```text
订阅姬 详情 真寻更新
```

获取指定订阅的详细信息，包括配置、状态等。

---

#### 修改订阅属性

```text
订阅姬 设置 <订阅名> <属性>=<值> [属性=值 ...]
```

**示例：**

```text
订阅姬 设置 真寻更新 频率=30 图片=5
订阅姬 设置 真寻更新 代理=开 暂停=关
```

**常用属性说明：**

| 属性 | 取值 | 说明 |
| :-: | :-: | :- |
| 频率 | 正整数 | 更新间隔（分钟） |
| 代理 | 开/关 | 是否使用全局代理 |
| 仅标题 | 开/关 | 仅推送标题 |
| 仅图片 | 开/关 | 仅推送图片 |
| 下载图片 | 开/关 | 下载图片后再推送 |
| 图片 | 0 或正整数 | 限制单条推送图片数量，0 表示不限制 |
| 白名单 | 正则表达式 或 -1 | 设置白名单关键词（支持正则），-1 清空 |
| 黑名单 | 正则表达式 或 -1 | 设置黑名单关键词（支持正则），-1 清空 |
| cookie | 字符串 | 设置抓取 Cookie |
| 合并 | 开/关 | 是否尝试合并转发 |
| 合并窗口 | 0 或正整数 | 按发布时间在指定分钟内合并成一条转发，0 表示按固定批次 |
| 隐藏内容 | 显示/隐藏 | 是否显示 Telegram/RSS 隐藏内容 |
| 正文长度 | 0 或正整数 | 正文超过该字符长度后截断，0 表示不截断 |
| 分段长度 | 0 或正整数 | 单条消息超过该字符长度后按合并转发分段，0 表示不分段 |
| 暂停 | 开/关 | 暂停/恢复订阅 |

---

#### 测试订阅

```text
订阅姬 测试 <订阅名>
```

**示例：**

```text
订阅姬 测试 真寻更新
```

**说明：** 抓取并预览解析结果，不会实际发送消息，也不会写入去重状态。用于调试订阅配置。

---

#### 立即拉取更新

```text
订阅姬 拉取 <订阅名>
```

**示例：**

```text
订阅姬 拉取 真寻更新
```

立即抓取并推送订阅的最新内容，不受更新频率限制。

---

#### 查看订阅状态

```text
订阅姬 状态 [订阅名]
```

**示例：**

```text
订阅姬 状态
订阅姬 状态 真寻更新
```

**说明：**

- 不指定订阅名：查看所有订阅的运行状态
- 指定订阅名：查看指定订阅的详细状态、抓取诊断和最近错误

---

### 导入/导出

#### 导出订阅

```text
订阅姬 导出 [订阅名] [file] [raw] [opml]
```

**示例：**

```text
订阅姬 导出                      # 导出所有订阅为 JSON
订阅姬 导出 真寻更新              # 导出指定订阅
订阅姬 导出 file                  # 以文件形式发送
订阅姬 导出 opml                  # 导出为 OPML 格式
订阅姬 导出 raw                   # 不脱敏敏感字段（如 cookie）
```

**参数说明：**

- `订阅名`：可选，不填则导出所有订阅
- `file`：以文件形式发送导出内容
- `raw`：不脱敏敏感字段
- `opml`：导出为 OPML 格式（默认 JSON）

---

#### 导入订阅

```text
订阅姬 导入 [--dry-run] <JSON内容|OPML内容|file:路径>
```

**示例：**

```text
订阅姬 导入 file:rss_export.json           # 从文件导入
订阅姬 导入 --dry-run file:test.json       # 预检模式，不实际导入
订阅姬 导入 {"feeds": [...]}               # 直接传入 JSON 内容
```

**参数说明：**

- `--dry-run`：预检模式，只显示将要导入的内容，不实际执行
- `file:路径`：从文件导入
- 直接传入 JSON 或 OPML 内容字符串

---

### 高级用法

#### 使用 RSSHub 路由

对于支持 RSSHub 的订阅源，可以直接使用路由：

```text
订阅姬 添加 B站用户视频 /bilibili/user/video/123456
订阅姬 添加 GitHub趋势 /github/trending/daily
订阅姬 添加 TG频道 /telegram/channel/botnews
订阅姬 添加 Twitter用户 /twitter/user/username
```

#### 批量设置属性

可以一次性设置多个属性：

```text
订阅姬 设置 真寻更新 频率=30 图片=5 代理=开 下载图片=关
订阅姬 设置 TG频道 合并=开 合并窗口=1 隐藏内容=显示 正文长度=1200 分段长度=500
```

#### 使用正则表达式过滤

白名单和黑名单支持正则表达式：

```text
订阅姬 设置 真寻更新 白名单=(?i)公告|更新
订阅姬 设置 真寻更新 黑名单=(?i)抽奖|活动
```
