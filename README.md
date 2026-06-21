# 🎨 图文聚合插件

[![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)](https://github.com/yourusername/astrbot_plugin_media_suite)
[![AstrBot](https://img.shields.io/badge/AstrBot-插件-green.svg)](https://github.com/Soulter/AstrBot)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

一个功能丰富的 AstrBot 二次元聚合插件,包括了壁纸、二次元图片、表情包、番剧搜索、漫画搜索、以图搜番/搜图、一言、Galgame 搜索等多种实用功能。

## ✨ 功能特性

- 🖼️ **壁纸获取** - 多源壁纸，支持分类筛选
- 🎨 **二次元图片** - Pixiv 图片搜索，支持关键词和 R18
- 😊 **表情包** - 随机二次元表情，聊天必备
- 📚 **漫画搜索** - 搜索漫画作品信息
- 📺 **番剧搜索** - Bilibili 番剧数据，含放送表
- 🔍 **以图搜索** - 以图搜番（trace.moe）+ 以图搜图（SauceNAO）
- 💬 **一言语录** - 二次元经典语录
- 🎮 **Galgame 搜索** - 萌娘百科 + 鲲论坛聚合

## 📦 安装

1. 将插件文件夹放入 AstrBot 的 `plugins` 目录
2. 安装依赖：
```bash
pip install -r requirements.txt
```
3. 重启 AstrBot

> **注意**：如果之前安装过独立的壁纸、涩图、Galgame 等插件，请先停用它们以避免命令冲突。

## 📖 使用指南

### 🖼️ 壁纸功能

获取各类高清壁纸，支持多个图源自动切换。

**命令：**
- `/壁纸` - 随机获取一张壁纸
- `/壁纸 [分类]` - 获取指定分类的壁纸
- `/壁纸帮助` - 查看可用分类

**支持的分类：**
- `随机` - 随机壁纸（默认）
- `二次元` / `动漫` / `anime` - 动漫壁纸
- `风景` / `自然` - 风景壁纸
- `必应` / `每日` / `bing` - 必应每日壁纸
- `手机` / `竖屏` / `mobile` - 手机竖屏壁纸

**示例：**
```
/壁纸
/壁纸 二次元
/壁纸 风景
```

---

### 🎨 二次元图片

从 Pixiv 等平台获取高质量二次元图片，支持关键词搜索。

**命令：**
- `/涩图` - 随机获取一张二次元图片
- `/涩图 [关键词]` - 按关键词搜索图片
- `/涩图 r18 [关键词]` - 获取 R18 图片（需配置权限）
- `/涩图帮助` - 查看使用说明

**功能特点：**
- ✅ 支持关键词搜索（仅 Lolicon API）
- ✅ 显示作品信息（标题、画师、PID）
- ✅ 冷却时间和每日限制（可配置）
- ✅ R18 白名单机制

**示例：**
```
/涩图
/涩图 萝莉
/涩图 r18 猫娘
```

**配置项：**
- `default_api` - 图片 API（lolicon/anosu/dmoe）
- `enable_r18` - 是否启用 R18
- `r18_whitelist_groups` - R18 白名单群组
- `daily_limit` - 每日调用上限
- `cooldown_seconds` - 冷却时间（秒）

---

### 😊 表情包功能 <Badge text="v1.6.0 新增" type="tip"/>

快速发送随机二次元表情包，为聊天增添趣味。

**命令：**
- `/表情` - 随机发送一个二次元表情
- `/表情包` / `/emoji` - 同上
- `/表情帮助` - 查看帮助

**特点：**
- 🎲 每次随机，不重复
- 🔄 多图源备份，高可用
- ⚡ 快速响应

**示例：**
```
/表情
/表情包
```

---

### 📚 漫画搜索 <Badge text="v1.5.0 新增" type="tip"/>

搜索漫画作品信息，基于萌娘百科数据源。

**命令：**
- `/漫画 <作品名>` - 搜索漫画
- `/搜漫画` / `/manga` / `/comic` - 别名
- `/漫画帮助` - 查看帮助

**返回信息：**
- 📖 作品标题
- 📝 作品简介
- 🔗 萌娘百科链接
- 📑 相关作品推荐

**示例：**
```
/漫画 进击的巨人
/漫画 鬼灭之刃
/漫画 海贼王
```

**特点：**
- ✅ 国内可直接访问
- ✅ 详细的作品介绍
- ✅ 多结果展示

---

### 📺 番剧搜索

搜索番剧信息和查看放送表，基于 Bilibili 数据源。

**命令：**
- `/番剧 <关键词>` - 搜索番剧
- `/今日番剧 [星期]` - 查看放送表
- `/番剧表 [星期]` - 同上

**别名：**
- 搜番、动画、anime

**返回信息：**
- 🖼️ 番剧封面（可配置）
- ⭐ 评分
- 🌏 地区
- 🏷️ 标签分类
- 📅 开播日期
- 📖 剧情简介
- 🔗 Bilibili 链接

**放送表功能：**
支持查看指定星期的番剧放送，可输入：
- `今天` / `today` / `今日`
- `明天` / `tomorrow` / `明日`
- `昨天` / `yesterday` / `昨日`
- `周一` / `1` / `一` / `Monday`
- `周二` / `2` / `二` / `Tuesday`
- ... 依此类推

**示例：**
```
/番剧 间谍过家家
/今日番剧
/番剧表 周六
/番剧表 明天
```

**技术说明：**
- 使用 Bilibili WBI 签名机制，绕过风控
- 自动获取和缓存 buvid3 cookie
- 国内服务器可直连，无需代理
- 偶发风控时会自动重置缓存

---

### 🔍 以图搜索

通过图片搜索番剧出处或图片来源。

#### 以图搜番（trace.moe）

识别动画截图来自哪部番剧、第几集、什么时间点。

**命令：**
- `/搜番图` - 以图搜番
- `/以图搜番` / `/截图搜番` / `/搜动画` - 别名

**返回信息：**
- 📺 番剧名称
- 📼 集数
- ⏰ 时间点
- 🎯 相似度

#### 以图搜图（SauceNAO）

查找图片的原始出处（Pixiv、Twitter 等）。

**命令：**
- `/搜图` - 以图搜图
- `/识图` / `/以图搜图` / `/搜源` / `/找图源` - 别名

**返回信息：**
- 🖼️ 作品标题
- 👤 作者/画师
- 🎨 Pixiv ID（如有）
- 🔗 原始链接
- 🎯 相似度

**使用方式（三选一）：**

1. **指令和图片一起发送**
   ```
   [图片] /搜番图
   ```

2. **引用带图片的消息**
   ```
   [引用包含图片的消息] /搜图
   ```

3. **先发指令，后补图**
   ```
   用户: /搜番图
   机器人: 请发送要搜索的动画截图~（60秒内有效）
   用户: [发送图片]
   ```

**配置项：**
- `saucenao_api_key` - SauceNAO API Key（建议配置）
- `trace_min_similarity` - trace.moe 最低相似度（0-1）
- `saucenao_min_similarity` - SauceNAO 最低相似度（0-100）
- `image_search_timeout` - 等待用户补图的超时时间（秒）

> **提示**：SauceNAO 免费账号有调用限制，建议申请 API Key 以提升配额。

---

### 💬 一言功能

获取随机的二次元经典语录。

**命令：**
- `/一言` - 随机一言
- `/一言 [类型]` - 指定类型的一言
- `/hitokoto` / `/语录` / `/来句话` - 别名

**支持的类型：**
- `动画` / `anime` - 动画语录
- `漫画` / `manga` - 漫画语录
- `游戏` / `game` - 游戏语录
- `文学` - 文学作品
- `原创` - 原创内容
- `网络` - 网络流行
- `其他` - 其他类型
- `影视` - 影视作品
- `诗词` - 诗词歌赋
- `网易云` - 网易云音乐评论
- `哲学` - 哲学名言
- `抖机灵` - 段子笑话

**示例：**
```
/一言
/一言 动画
/一言 游戏
```

**配置项：**
- `hitokoto_default_type` - 默认类型（留空则随机）
- `hitokoto_show_source` - 是否显示出处

---

### 🎮 Galgame 搜索

聚合搜索萌娘百科和鲲 Galgame 论坛的 Galgame 作品信息。

**命令：**
- `/gal <关键词>` - 聚合搜索（萌娘百科 + 鲲论坛各1条）
- `/galmoe <关键词>` - 只搜索萌娘百科
- `/galkun <关键词>` - 只搜索鲲论坛

**别名：**
- `/galgame` - 同 `/gal`
- `/萌百` / `/萌娘百科` - 同 `/galmoe`
- `/鲲` / `/鲲论坛` - 同 `/galkun`

**返回信息：**
- 📖 作品名称
- 📝 作品简介
- 🎮 平台信息
- 🌍 语言版本
- 🔞 分级信息
- 📊 浏览/点赞数据
- 🔗 详情链接

**示例：**
```
/gal 白色相簿2
/galmoe 樱之诗
/galkun ATRI
```

**配置项：**
- `result_limit` - 单源最大结果数
- `search_kun_topics` - 是否搜索鲲论坛话题（作品搜不到时）

**配置项：**
- `result_limit` - 单源最大结果数
- `search_kun_topics` - 是否搜索鲲论坛话题（作品搜不到时）

---

## ⚙️ 配置说明

插件支持丰富的配置选项，可在 AstrBot 配置文件中修改。

### 壁纸配置

```json
{
  "wallpaper_timeout": 20,
  "wallpaper_proxy": ""
}
```

- `wallpaper_timeout` - 请求超时时间（秒）
- `wallpaper_proxy` - HTTP 代理地址（如需要）

### 二次元图片配置

```json
{
  "default_api": "lolicon",
  "enable_r18": false,
  "r18_whitelist_groups": [],
  "daily_limit": 0,
  "cooldown_seconds": 3,
  "show_info": true,
  "request_timeout": 30,
  "anime_proxy": ""
}
```

- `default_api` - 图片 API（`lolicon` / `anosu` / `dmoe`）
- `enable_r18` - 是否启用 R18 功能
- `r18_whitelist_groups` - R18 白名单群组 ID 列表
- `daily_limit` - 每日调用上限（0 为不限制）
- `cooldown_seconds` - 冷却时间（秒）
- `show_info` - 是否显示图片信息
- `request_timeout` - 请求超时时间（秒）
- `anime_proxy` - Pixiv 图片反代地址（如 `https://i.pixiv.re`）

### 番剧配置

```json
{
  "bili_search_api": "https://api.bilibili.com/x/web-interface/search/type",
  "bili_timeline_api": "https://api.bilibili.com/pgc/web/timeline",
  "bangumi_result_limit": 3,
  "bangumi_calendar_limit": 12,
  "bangumi_show_cover": true
}
```

- `bangumi_result_limit` - 搜索结果数量限制
- `bangumi_calendar_limit` - 放送表显示数量
- `bangumi_show_cover` - 是否显示番剧封面

### 以图搜索配置

```json
{
  "trace_api_url": "https://api.trace.moe/search",
  "trace_anilist_chat": true,
  "trace_min_similarity": 0.85,
  "saucenao_api_url": "https://saucenao.com/search.php",
  "saucenao_api_key": "",
  "saucenao_result_limit": 3,
  "saucenao_min_similarity": 50,
  "image_search_timeout": 60
}
```

- `trace_min_similarity` - trace.moe 最低相似度阈值（0-1）
- `saucenao_api_key` - SauceNAO API Key（强烈建议配置）
- `saucenao_result_limit` - SauceNAO 结果数量
- `saucenao_min_similarity` - SauceNAO 最低相似度（0-100）
- `image_search_timeout` - 等待用户补图的超时时间（秒）

### Galgame 搜索配置

```json
{
  "result_limit": 3,
  "aggregate_result_limit": 2,
  "intro_max_length": 160,
  "timeout_seconds": 8,
  "search_kun_topics": true,
  "moegirl_api_url": "https://moegirl.icu/api.php",
  "moegirl_page_url": "https://moegirl.icu",
  "kungal_api_base": "https://www.kungal.com/api",
  "kungal_site_url": "https://www.kungal.com"
}
```

- `result_limit` - 单源最大结果数
- `intro_max_length` - 简介最大长度
- `search_kun_topics` - 作品搜不到时是否搜索话题

### 一言配置

```json
{
  "hitokoto_api_url": "https://v1.hitokoto.cn",
  "hitokoto_default_type": "",
  "hitokoto_show_source": true
}
```

- `hitokoto_default_type` - 默认类型代码（留空则随机）
- `hitokoto_show_source` - 是否显示语录出处

---

## 🔧 技术细节

### 数据源

| 功能 | 数据源 | 访问性 |
|------|--------|--------|
| 壁纸 | dmoe.cc、btstu.cn、alcy.cc 等 | 国内直连 |
| 二次元图片 | Lolicon API、Anosu、Dmoe | 国内直连 |
| 表情包 | dmoe.cc、alcy.cc、mtyqx.cn | 国内直连 |
| 漫画搜索 | 萌娘百科 | 国内直连 |
| 番剧搜索 | Bilibili API | 国内直连 |
| 以图搜番 | trace.moe | 需国外访问 |
| 以图搜图 | SauceNAO | 需国外访问 |
| 一言 | hitokoto.cn | 国内直连 |
| Galgame | 萌娘百科 + 鲲论坛 | 国内直连 |

### 架构特点

- ✅ **异步设计**：使用 `aiohttp` 实现高性能异步请求
- ✅ **多源备份**：壁纸、表情包等功能支持多图源自动切换
- ✅ **错误处理**：完善的异常捕获和用户友好的错误提示
- ✅ **缓存机制**：Bilibili buvid3 缓存，减少重复请求
- ✅ **会话等待**：以图搜索支持会话等待，用户体验更好
- ✅ **配置灵活**：丰富的配置项，满足不同需求

### API 限制说明

1. **SauceNAO**
   - 免费账号：每 30 秒 6 次，每日 200 次
   - 建议申请 API Key 以提升配额
   - 申请地址：https://saucenao.com/user.php

2. **trace.moe**
   - 并发限制：每秒 1 次
   - 配额限制：每分钟 10 次
   - 无需 API Key

3. **Lolicon API**
   - 免费使用，有频率限制
   - 建议配置冷却时间避免触发限制

---

## 📋 命令速查表

| 功能 | 命令 | 说明 |
|------|------|------|
| 壁纸 | `/壁纸 [分类]` | 获取壁纸 |
| 二次元图片 | `/涩图 [关键词]` | 获取图片 |
| 表情包 | `/表情` | 随机表情 |
| 漫画搜索 | `/漫画 <作品名>` | 搜索漫画 |
| 番剧搜索 | `/番剧 <关键词>` | 搜索番剧 |
| 放送表 | `/今日番剧 [星期]` | 查看放送 |
| 以图搜番 | `/搜番图` | 识别动画截图 |
| 以图搜图 | `/搜图` | 查找图片出处 |
| 一言 | `/一言 [类型]` | 获取语录 |
| Galgame | `/gal <关键词>` | 搜索 Galgame |

---

## 🐛 常见问题

### Q: 番剧搜索提示风控怎么办？
A: 插件会自动处理风控，清除缓存后重试即可。如果频繁出现，建议等待几分钟后再试。

### Q: 以图搜索没有反应？
A: 检查以下几点：
1. 图片 URL 是否可以被外部访问
2. 服务器网络是否可以访问 trace.moe / SauceNAO
3. 是否触发了 API 频率限制

### Q: SauceNAO 提示限流？
A: 建议在配置中填写 `saucenao_api_key`，可以大幅提升调用配额。

### Q: 涩图功能不返回结果？
A: 可能是关键词不匹配或 API 暂时无响应，可以：
1. 换一个关键词试试
2. 不带关键词，获取随机图片
3. 切换其他 API（配置 `default_api`）

### Q: 如何开启 R18 功能？
A: 在配置中设置：
```json
{
  "enable_r18": true,
  "r18_whitelist_groups": ["群组ID1", "群组ID2"]
}
```

### Q: 壁纸/表情包加载失败？
A: 插件会自动切换到备用图源，如果所有源都失败，可能是网络问题。可以配置代理：
```json
{
  "wallpaper_proxy": "http://127.0.0.1:7890"
}
```

---

## 📝 更新日志

### v1.6.0 (2026-06-21)
- ✨ 新增：二次元表情包功能
- 🔄 优化：多图源备份机制
- 📝 更新：完善文档

### v1.5.0 (2026-06-21)
- ✨ 新增：漫画搜索功能（萌娘百科）
- 📝 新增：详细的搜索结果展示

### v1.4.0
- 🎉 初始版本
- ✨ 整合壁纸、二次元图片、番剧、Galgame、以图搜索、一言等功能

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

如果你有好的功能建议或发现了 Bug，请：
1. 提交 Issue 描述问题
2. Fork 本项目并创建新分支
3. 提交你的改动
4. 发起 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

感谢以下项目和服务：

- [AstrBot](https://github.com/Soulter/AstrBot) - 优秀的 QQ 机器人框架
- [Lolicon API](https://api.lolicon.app/) - 提供高质量二次元图片
- [萌娘百科](https://moegirl.icu/) - 提供 ACG 百科数据
- [鲲 Galgame 论坛](https://www.kungal.com/) - Galgame 资讯平台
- [Bilibili](https://www.bilibili.com/) - 番剧数据来源
- [trace.moe](https://trace.moe/) - 以图搜番服务
- [SauceNAO](https://saucenao.com/) - 以图搜图服务
- [Hitokoto](https://hitokoto.cn/) - 一言 API

---

## 📧 联系方式

- 作者：Shiyao
- 版本：1.6.0
- 问题反馈：[提交 Issue](https://github.com/Shiyaolx/strbot_plugin_media_suite)

---

<div align="center">

**如果觉得这个插件对你有帮助，请给个 ⭐ Star 吧！**

Made with ❤️ by Shiyao

</div>
