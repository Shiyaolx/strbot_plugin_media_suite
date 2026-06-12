import asyncio
import time
from datetime import date

import aiohttp

from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger, AstrBotConfig
import astrbot.api.message_components as Comp


@register(
    "astrbot_plugin_anime_pic",
    "时瑶",
    "二次元图片插件 - 随机获取二次元图片，支持标签搜索",
    "v1.0.0",
    "https://github.com/yourname/astrbot_plugin_anime_pic",
)
class AnimePicPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 读取配置项（带默认值兜底）
        self.default_api = config.get("default_api", "lolicon")
        self.enable_r18 = config.get("enable_r18", False)
        self.r18_whitelist = [str(g) for g in config.get("r18_whitelist_groups", [])]
        self.daily_limit = int(config.get("daily_limit", 0))
        self.cooldown = int(config.get("cooldown_seconds", 3))
        self.show_info = config.get("show_info", True)
        self.timeout = int(config.get("request_timeout", 30))
        self.proxy = config.get("proxy", "").strip()

        # 运行时状态
        self._last_request = {}      # user_id -> 上次请求时间戳
        self._daily_count = {}       # user_id -> [date, count]

        logger.info(
            f"[anime_pic] 已加载，默认API={self.default_api}, "
            f"R18={'开' if self.enable_r18 else '关'}"
        )

    # ---------- 限流 / 冷却 ----------
    def _check_cooldown(self, user_id: str) -> float:
        """返回剩余冷却秒数，0 表示可以请求"""
        if self.cooldown <= 0:
            return 0
        now = time.time()
        last = self._last_request.get(user_id, 0)
        remain = self.cooldown - (now - last)
        return remain if remain > 0 else 0

    def _check_daily_limit(self, user_id: str) -> bool:
        """返回 True 表示已达上限"""
        if self.daily_limit <= 0:
            return False
        today = date.today().isoformat()
        rec = self._daily_count.get(user_id)
        if not rec or rec[0] != today:
            return False
        return rec[1] >= self.daily_limit

    def _record_request(self, user_id: str):
        self._last_request[user_id] = time.time()
        today = date.today().isoformat()
        rec = self._daily_count.get(user_id)
        if not rec or rec[0] != today:
            self._daily_count[user_id] = [today, 1]
        else:
            rec[1] += 1

    def _r18_allowed(self, event: AstrMessageEvent) -> bool:
        """判断当前会话是否允许 R18"""
        if not self.enable_r18:
            return False
        if not self.r18_whitelist:
            return True
        group_id = event.get_group_id()
        # 私聊（无群号）在开启 R18 且白名单非空时默认允许
        if not group_id:
            return True
        return str(group_id) in self.r18_whitelist

    def _apply_proxy(self, url: str) -> str:
        """替换图片域名为反代地址"""
        if not self.proxy:
            return url
        for host in ("i.pixiv.re", "i.pximg.net", "pixiv.re"):
            if host in url:
                base = self.proxy.rstrip("/")
                path = url.split(host, 1)[1]
                return f"{base}{path}"
        return url

    # ---------- 各 API 获取实现 ----------
    async def _fetch_lolicon(self, session, keyword: str, r18: bool) -> dict:
        """Lolicon API: 支持标签搜索，返回 {url, title, author, pid} 或 None"""
        params = {
            "r18": 1 if r18 else 0,
            "num": 1,
            "size": "regular",
            "proxy": "i.pixiv.re",
        }
        if keyword:
            params["tag"] = keyword
        async with session.get(
            "https://api.lolicon.app/setu/v2", params=params
        ) as resp:
            data = await resp.json()
        items = data.get("data") or []
        if not items:
            return None
        it = items[0]
        urls = it.get("urls", {})
        url = urls.get("regular") or urls.get("original") or ""
        if not url:
            return None
        return {
            "url": url,
            "title": it.get("title", ""),
            "author": it.get("author", ""),
            "pid": it.get("pid", ""),
        }

    async def _fetch_anosu(self, session, keyword: str, r18: bool) -> dict:
        """Anosu 随机图 API"""
        params = {"r18": 1 if r18 else 0, "num": 1}
        if keyword:
            params["keyword"] = keyword
        async with session.get(
            "https://image.anosu.top/pixiv/json", params=params
        ) as resp:
            data = await resp.json()
        if not data:
            return None
        it = data[0] if isinstance(data, list) else data
        url = it.get("url", "")
        if not url:
            return None
        return {
            "url": url,
            "title": it.get("title", ""),
            "author": it.get("author", ""),
            "pid": it.get("pid", ""),
        }

    async def _fetch_dmoe(self, session, keyword: str, r18: bool) -> dict:
        """樱花/Dmoe 随机二次元图(不支持关键词，返回图片直链)"""
        async with session.get(
            "https://www.dmoe.cc/random.php", params={"return": "json"}
        ) as resp:
            data = await resp.json(content_type=None)
        url = data.get("imgurl", "")
        if not url:
            return None
        return {"url": url, "title": "", "author": "", "pid": ""}

    async def _fetch_image(self, api: str, keyword: str, r18: bool) -> dict:
        """根据 api 名称分发，返回图片信息 dict 或 None"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {"User-Agent": "Mozilla/5.0 AstrBot-AnimePic/1.0"}
        async with aiohttp.ClientSession(
            timeout=timeout, headers=headers
        ) as session:
            if api == "lolicon":
                return await self._fetch_lolicon(session, keyword, r18)
            elif api == "anosu":
                return await self._fetch_anosu(session, keyword, r18)
            elif api == "dmoe":
                return await self._fetch_dmoe(session, keyword, r18)
            else:
                return await self._fetch_lolicon(session, keyword, r18)

    # ---------- 指令处理 ----------
    @filter.command("涩图", alias={"setu", "二次元", "来张图"})
    async def get_anime_pic(self, event: AstrMessageEvent):
        """获取二次元图片。用法: /涩图 [关键词]  或  /涩图 r18 [关键词]"""
        user_id = event.get_sender_id()
        args = event.message_str.strip().split()
        # 去掉指令本身（第一个 token）
        if args:
            args = args[1:]

        # 解析是否请求 r18
        want_r18 = False
        keyword = ""
        if args and args[0].lower() in ("r18", "R18", "r-18"):
            want_r18 = True
            keyword = " ".join(args[1:]).strip()
        else:
            keyword = " ".join(args).strip()

        # 冷却检查
        remain = self._check_cooldown(user_id)
        if remain > 0:
            yield event.plain_result(f"⏳ 冷却中，请 {remain:.0f} 秒后再试~")
            return

        # 每日上限检查
        if self._check_daily_limit(user_id):
            yield event.plain_result(
                f"📵 你今天已经达到上限({self.daily_limit}次)啦，明天再来吧~"
            )
            return

        # R18 权限判定
        r18 = False
        if want_r18:
            if self._r18_allowed(event):
                r18 = True
            else:
                yield event.plain_result("🔞 当前会话未开启 R18 权限。")
                return

        # 先记录请求（防止并发刷）
        self._record_request(user_id)

        try:
            info = await self._fetch_image(self.default_api, keyword, r18)
        except asyncio.TimeoutError:
            yield event.plain_result("⌛ 请求超时了，待会儿再试试吧~")
            return
        except Exception as e:
            logger.error(f"[anime_pic] 获取图片失败: {e}")
            yield event.plain_result("😿 获取图片失败，可能是 API 暂时不可用。")
            return

        if not info or not info.get("url"):
            tip = f"找不到「{keyword}」相关的图片~" if keyword else "没有获取到图片，换个来源试试?"
            yield event.plain_result(f"🔍 {tip}")
            return

        img_url = self._apply_proxy(info["url"])

        # 组装消息链
        chain = [Comp.Image.fromURL(img_url)]
        if self.show_info and (info.get("title") or info.get("pid")):
            parts = []
            if info.get("title"):
                parts.append(f"标题: {info['title']}")
            if info.get("author"):
                parts.append(f"画师: {info['author']}")
            if info.get("pid"):
                parts.append(f"PID: {info['pid']}")
            chain.append(Comp.Plain("\n" + " | ".join(parts)))

        yield event.chain_result(chain)

    @filter.command("涩图帮助", alias={"setu帮助", "图片帮助"})
    async def pic_help(self, event: AstrMessageEvent):
        """显示插件使用帮助"""
        api_names = {"lolicon": "Lolicon", "anosu": "Anosu", "dmoe": "Dmoe樱花"}
        cur = api_names.get(self.default_api, self.default_api)
        msg = (
            "🎨 二次元图片插件使用帮助\n"
            "————————————\n"
            "/涩图            随机获取一张图\n"
            "/涩图 萝莉       按关键词/标签获取(仅lolicon支持)\n"
            "/涩图 r18 [词]   获取R18图(需管理员开启)\n"
            "/涩图帮助        显示本帮助\n"
            "————————————\n"
            f"当前图源: {cur}\n"
            f"R18: {'已开启' if self.enable_r18 else '已关闭'}\n"
            f"冷却: {self.cooldown}秒 | "
            f"每日上限: {'不限' if self.daily_limit == 0 else self.daily_limit}"
        )
        yield event.plain_result(msg)

    async def terminate(self):
        """插件卸载时清理状态"""
        self._last_request.clear()
        self._daily_count.clear()
        logger.info("[anime_pic] 插件已卸载")
