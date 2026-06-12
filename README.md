# astrbot_plugin_anime_pic

AstrBot 二次元图片插件 —— 通过指令随机获取二次元图片，支持标签/关键词搜索、多图源切换、冷却与每日限流、R18 权限控制。

## 功能特性

- 多图源支持：Lolicon（支持标签搜索）、Anosu、Dmoe 樱花随机图，可在配置中切换
- 关键词/标签搜索（Lolicon 图源）
- R18 内容开关，默认关闭；可设置群号白名单
- 用户冷却时间 + 每日次数限制，防止刷屏
- 可选展示作品信息（标题 / 画师 / PID）
- 支持图片反代地址，解决 Pixiv 域名被墙问题

## 安装

将整个 `astrbot_plugin_anime_pic` 文件夹放入 AstrBot 的 `data/plugins/` 目录，重启或在管理面板重载插件。依赖 `aiohttp` 会自动安装（AstrBot 通常已自带）。

## 指令

| 指令 | 说明 |
| --- | --- |
| `/涩图` | 随机获取一张图 |
| `/涩图 <关键词>` | 按标签/关键词获取（仅 lolicon 支持） |
| `/涩图 r18 [关键词]` | 获取 R18 图片（需管理员开启权限） |
| `/涩图帮助` | 显示使用帮助 |

别名：`setu`、`二次元`、`来张图` 同样可触发主指令。

## 配置项

在 AstrBot 管理面板的插件配置页可视化修改：

- `default_api`：图片来源，`lolicon` / `anosu` / `dmoe`，默认 `lolicon`
- `enable_r18`：是否允许 R18，默认 `false`
- `r18_whitelist_groups`：R18 群号白名单，留空则所有会话可触发
- `daily_limit`：每用户每日上限，`0` 为不限
- `cooldown_seconds`：用户冷却秒数，默认 `3`
- `show_info`：是否附带作品信息，默认 `true`
- `request_timeout`：请求超时秒数，默认 `30`
- `proxy`：图片反代前缀（如 `https://your-proxy.com`），替换 `i.pixiv.re`

## 注意事项

- R18 功能默认关闭，开启后请确保符合所在平台与当地法律法规，风险自负。
- 图片 API 为第三方公益服务，稳定性受其影响；若某图源失效可在配置切换其他图源。
- Pixiv 图片在国内可能需要配置 `proxy` 反代才能正常加载。
