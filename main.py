from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import socket
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Awaitable
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import aiohttp

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


EMOJI_SOURCES = [
    {"url": "https://api.btstu.cn/sjbz/api.php?lx=dongman&format=json", "type": "json", "field": "imgurl"},
    {"url": "https://www.dmoe.cc/random.php", "type": "redirect"},
    {"url": "https://t.alcy.cc/moe", "type": "redirect"},
    {"url": "https://api.mtyqx.cn/api/random.php", "type": "redirect"},
]

SOURCES = {
    "随机": [
        {"url": "https://www.dmoe.cc/random.php", "type": "redirect"},
        {"url": "https://api.btstu.cn/sjbz/api.php?lx=suiji&format=json", "type": "json", "field": "imgurl"},
        {"url": "https://t.alcy.cc/moe", "type": "redirect"},
        {"url": "https://api.mtyqx.cn/api/random.php", "type": "redirect"},
    ],
    "二次元": [
        {"url": "https://www.dmoe.cc/random.php", "type": "redirect"},
        {"url": "https://t.alcy.cc/moe", "type": "redirect"},
        {"url": "https://api.btstu.cn/sjbz/api.php?lx=dongman&format=json", "type": "json", "field": "imgurl"},
        {"url": "https://api.lolicon.app/setu/v2", "type": "json", "field": "imgurl"},
    ],
    "风景": [
        {"url": "https://t.alcy.cc/fj", "type": "redirect"},
        {"url": "https://api.btstu.cn/sjbz/api.php?lx=fengjing&format=json", "type": "json", "field": "imgurl"},
        {"url": "https://api.dujin.org/bing/1920.php", "type": "redirect"},
    ],
    "必应": [
        {"url": "https://bing.img.run/rand.php", "type": "redirect"},
        {"url": "https://api.dujin.org/bing/1920.php", "type": "redirect"},
        {"url": "https://api.btstu.cn/sjbz/api.php?lx=fengjing&format=json", "type": "json", "field": "imgurl"},
    ],
    "手机": [
        {"url": "https://t.alcy.cc/mp", "type": "redirect"},
        {"url": "https://api.btstu.cn/sjbz/api.php?lx=suiji&method=mobile&format=json", "type": "json", "field": "imgurl"},
        {"url": "https://www.dmoe.cc/random.php", "type": "redirect"},
    ],
}

ALIASES = {
    "动漫": "二次元",
    "anime": "二次元",
    "自然": "风景",
    "每日": "必应",
    "bing": "必应",
    "竖屏": "手机",
    "mobile": "手机",
}

# 星期映射：用户输入 -> ISO 星期号（1=周一 ... 7=周日），与 Bangumi calendar 的 weekday.id 一致
WEEKDAY_ALIASES = {
    "1": 1, "一": 1, "周一": 1, "星期一": 1, "礼拜一": 1, "mon": 1, "monday": 1,
    "2": 2, "二": 2, "周二": 2, "星期二": 2, "礼拜二": 2, "tue": 2, "tuesday": 2,
    "3": 3, "三": 3, "周三": 3, "星期三": 3, "礼拜三": 3, "wed": 3, "wednesday": 3,
    "4": 4, "四": 4, "周四": 4, "星期四": 4, "礼拜四": 4, "thu": 4, "thursday": 4,
    "5": 5, "五": 5, "周五": 5, "星期五": 5, "礼拜五": 5, "fri": 5, "friday": 5,
    "6": 6, "六": 6, "周六": 6, "星期六": 6, "礼拜六": 6, "sat": 6, "saturday": 6,
    "7": 7, "日": 7, "天": 7, "周日": 7, "周天": 7, "星期日": 7, "星期天": 7, "礼拜日": 7, "礼拜天": 7, "sun": 7, "sunday": 7,
}

WEEKDAY_NAMES = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}

# 一言（hitokoto）句子类型：用户输入 -> API 的 c 参数
HITOKOTO_TYPES = {
    "动画": "a", "anime": "a",
    "漫画": "b", "manga": "b",
    "游戏": "c", "game": "c",
    "文学": "d",
    "原创": "e",
    "网络": "f",
    "其他": "g",
    "影视": "h",
    "诗词": "i",
    "网易云": "j",
    "哲学": "k",
    "抖机灵": "l",
}


@dataclass
class SearchItem:
    source: str
    title: str
    url: str
    summary: str = ""
    meta: str = ""


@register(
    "astrbot_plugin_media_suite",
    "Codex",
    "壁纸、二次元图片、番剧搜索、以图搜番/搜图、一言与 Galgame 聚合搜索的合并插件。",
    "1.4.0",
    "",
)
class MediaSuitePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.wallpaper_timeout = int(config.get("wallpaper_timeout", 20) or 20)
        self.wallpaper_proxy = str(config.get("wallpaper_proxy", "") or "").strip()

        self.default_api = str(config.get("default_api", "lolicon") or "lolicon")
        self.enable_r18 = bool(config.get("enable_r18", False))
        self.r18_whitelist = [str(g) for g in config.get("r18_whitelist_groups", [])]
        self.daily_limit = int(config.get("daily_limit", 0) or 0)
        self.cooldown = int(config.get("cooldown_seconds", 3) or 3)
        self.show_info = bool(config.get("show_info", True))
        self.request_timeout = int(config.get("request_timeout", 30) or 30)
        self.anime_proxy = str(config.get("anime_proxy", "") or "").strip()
        self._last_request: dict[str, float] = {}
        self._daily_count: dict[str, list[Any]] = {}

        self.result_limit = self._clamp_int(config.get("result_limit", 3), 1, 5)
        self.aggregate_limit = self._clamp_int(config.get("aggregate_result_limit", 2), 1, 10)
        self.intro_max_length = self._clamp_int(config.get("intro_max_length", 160), 80, 300)
        self.timeout_seconds = self._clamp_float(config.get("timeout_seconds", 8), 2, 30)
        self.search_kun_topics = bool(config.get("search_kun_topics", True))
        self.moe_api_url = str(config.get("moegirl_api_url", "https://moegirl.icu/api.php")).rstrip("/")
        self.moe_page_url = str(config.get("moegirl_page_url", "https://moegirl.icu")).rstrip("/")
        self.kun_api_base = str(config.get("kungal_api_base", "https://www.kungal.com/api")).rstrip("/")
        self.kun_site_url = str(config.get("kungal_site_url", "https://www.kungal.com")).rstrip("/")

        # 番剧（Bilibili 数据源，国内可直连）相关配置
        self.bili_search_api = str(
            config.get("bili_search_api", "https://api.bilibili.com/x/web-interface/search/type")
        ).strip()
        self.bili_timeline_api = str(
            config.get("bili_timeline_api", "https://api.bilibili.com/pgc/web/timeline")
        ).strip()
        self.bgm_result_limit = self._clamp_int(config.get("bangumi_result_limit", 3), 1, 8)
        self.bgm_calendar_limit = self._clamp_int(config.get("bangumi_calendar_limit", 12), 1, 30)
        self.bgm_show_cover = bool(config.get("bangumi_show_cover", True))
        # 缓存 buvid3（B 站搜索需带该 cookie 绕过风控）
        self._bili_buvid3: str | None = None

        # 以图搜番（trace.moe）/ 以图搜图（SauceNAO）相关配置
        self.trace_api_url = str(config.get("trace_api_url", "https://api.trace.moe/search")).strip()
        self.trace_anilist_chat = bool(config.get("trace_anilist_chat", True))
        self.trace_min_similarity = self._clamp_float(config.get("trace_min_similarity", 0.85), 0, 1)
        self.saucenao_api_url = str(config.get("saucenao_api_url", "https://saucenao.com/search.php")).strip()
        self.saucenao_api_key = str(config.get("saucenao_api_key", "") or "").strip()
        self.saucenao_result_limit = self._clamp_int(config.get("saucenao_result_limit", 3), 1, 8)
        self.saucenao_min_similarity = self._clamp_float(config.get("saucenao_min_similarity", 50), 0, 100)
        # 以图搜索的会话等待超时（秒），用户发送指令后在此时间内补发图片
        self.image_search_timeout = self._clamp_int(config.get("image_search_timeout", 60), 15, 300)

        # 二次元一言（hitokoto）相关配置
        self.hitokoto_api_url = str(config.get("hitokoto_api_url", "https://v1.hitokoto.cn")).strip()
        # 句子类型：a 动画 b 漫画 c 游戏 d 文学 e 原创 f 网络 g 其他 h 影视 i 诗词 j 网易云 k 哲学 l 抖机灵
        self.hitokoto_default_type = str(config.get("hitokoto_default_type", "") or "").strip()
        self.hitokoto_show_source = bool(config.get("hitokoto_show_source", True))

        logger.info(
            "[media_suite] loaded: "
            f"api={self.default_api}, "
            f"r18={'on' if self.enable_r18 else 'off'}, "
            f"gal_limit={self.result_limit}"
        )

    def _wallpaper_timeout(self) -> aiohttp.ClientTimeout:
        return aiohttp.ClientTimeout(total=self.wallpaper_timeout)

    def _wallpaper_effective_proxy(self) -> str | None:
        proxy = self.wallpaper_proxy.strip()
        return proxy or None

    async def _try_source(self, session: aiohttp.ClientSession, src: dict) -> str | None:
        try:
            async with session.get(
                src["url"],
                proxy=self._wallpaper_effective_proxy(),
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"[media_suite] wallpaper source {src['url']} status {resp.status}")
                    return None
                if src["type"] == "redirect":
                    return str(resp.url)
                data = await resp.json(content_type=None)
                if isinstance(data, dict):
                    return data.get(src.get("field", "imgurl"))
                return None
        except Exception:
            logger.warning(f"[media_suite] wallpaper source failed: {src['url']}", exc_info=True)
            return None

    async def _fetch_wallpaper(self, category: str) -> str | None:
        key = category.strip() if category else "随机"
        key = ALIASES.get(key.lower(), key)
        sources = SOURCES.get(key) or SOURCES.get("随机")

        async with aiohttp.ClientSession(timeout=self._wallpaper_timeout()) as session:
            for src in sources:
                url = await self._try_source(session, src)
                if url:
                    return url

        logger.error(f"[media_suite] wallpaper category failed: {key}")
        return None

    async def _fetch_emoji(self) -> str | None:
        """获取随机二次元表情包。"""
        async with aiohttp.ClientSession(timeout=self._wallpaper_timeout()) as session:
            for src in EMOJI_SOURCES:
                url = await self._try_source(session, src)
                if url:
                    return url

        logger.error("[media_suite] emoji fetch failed: all sources unavailable")
        return None

    @filter.command("壁纸", alias={"wallpaper", "bz"})
    async def wallpaper(self, event: AstrMessageEvent, category: str = ""):
        """获取一张壁纸。"""
        url = await self._fetch_wallpaper(category)
        if not url:
            yield event.plain_result("所有图源都没响应，稍后再试或换个分类吧。")
            return

        yield event.chain_result([Comp.Image.fromURL(url)])

    @filter.command("壁纸帮助", alias={"壁纸分类"})
    async def wallpaper_help(self, event: AstrMessageEvent):
        """查看可用的壁纸分类。"""
        lines = [
            "🖼️ 壁纸插件使用说明",
            "",
            "/壁纸          随机来一张",
            "/壁纸 二次元    动漫壁纸",
            "/壁纸 风景      风景壁纸",
            "/壁纸 必应      必应每日壁纸",
            "/壁纸 手机      竖屏壁纸",
            "",
            "可用分类：随机、二次元、风景、必应、手机",
        ]
        yield event.plain_result("\n".join(lines))

    @filter.command("表情", alias={"表情包", "emoji", "来个表情"})
    async def emoji(self, event: AstrMessageEvent):
        """随机获取一个二次元表情包。"""
        url = await self._fetch_emoji()
        if not url:
            yield event.plain_result("所有表情源都没响应，稍后再试吧。")
            return

        yield event.chain_result([Comp.Image.fromURL(url)])

    @filter.command("表情帮助")
    async def emoji_help(self, event: AstrMessageEvent):
        """查看表情包使用帮助。"""
        msg = (
            "😊 表情包使用说明\n"
            "————————————\n"
            "/表情          随机发送一个二次元表情\n"
            "/表情包        同上\n"
            "/表情帮助      显示本帮助\n"
            "————————————\n"
            "表情类型：二次元角色表情包"
        )
        yield event.plain_result(msg)

    def _check_cooldown(self, user_id: str) -> float:
        if self.cooldown <= 0:
            return 0
        now = time.time()
        last = self._last_request.get(user_id, 0)
        remain = self.cooldown - (now - last)
        return remain if remain > 0 else 0

    def _check_daily_limit(self, user_id: str) -> bool:
        if self.daily_limit <= 0:
            return False
        today = date.today().isoformat()
        rec = self._daily_count.get(user_id)
        if not rec or rec[0] != today:
            return False
        return rec[1] >= self.daily_limit

    def _record_request(self, user_id: str) -> None:
        self._last_request[user_id] = time.time()
        today = date.today().isoformat()
        rec = self._daily_count.get(user_id)
        if not rec or rec[0] != today:
            self._daily_count[user_id] = [today, 1]
        else:
            rec[1] += 1

    def _r18_allowed(self, event: AstrMessageEvent) -> bool:
        if not self.enable_r18:
            return False
        if not self.r18_whitelist:
            return True
        group_id = event.get_group_id()
        if not group_id:
            return True
        return str(group_id) in self.r18_whitelist

    def _apply_proxy(self, url: str) -> str:
        if not self.anime_proxy:
            return url
        for host in ("i.pixiv.re", "i.pximg.net", "pixiv.re"):
            if host in url:
                base = self.anime_proxy.rstrip("/")
                path = url.split(host, 1)[1]
                return f"{base}{path}"
        return url

    async def _fetch_lolicon(self, session: aiohttp.ClientSession, keyword: str, r18: bool) -> dict | None:
        params = {
            "r18": 1 if r18 else 0,
            "num": 1,
            "size": "regular",
            "proxy": "i.pixiv.re",
        }
        if keyword:
            params["tag"] = keyword
        async with session.get("https://api.lolicon.app/setu/v2", params=params) as resp:
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

    async def _fetch_anosu(self, session: aiohttp.ClientSession, keyword: str, r18: bool) -> dict | None:
        params = {"r18": 1 if r18 else 0, "num": 1}
        if keyword:
            params["keyword"] = keyword
        async with session.get("https://image.anosu.top/pixiv/json", params=params) as resp:
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

    async def _fetch_dmoe(self, session: aiohttp.ClientSession, keyword: str, r18: bool) -> dict | None:
        async with session.get("https://www.dmoe.cc/random.php", params={"return": "json"}) as resp:
            data = await resp.json(content_type=None)
        url = data.get("imgurl", "")
        if not url:
            return None
        return {"url": url, "title": "", "author": "", "pid": ""}

    async def _fetch_image(self, api: str, keyword: str, r18: bool) -> dict | None:
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        headers = {"User-Agent": "Mozilla/5.0 AstrBot-AnimePic/1.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            if api == "lolicon":
                return await self._fetch_lolicon(session, keyword, r18)
            if api == "anosu":
                return await self._fetch_anosu(session, keyword, r18)
            if api == "dmoe":
                return await self._fetch_dmoe(session, keyword, r18)
            return await self._fetch_lolicon(session, keyword, r18)

    @filter.command("涩图", alias={"setu", "二次元", "来张图"})
    async def get_anime_pic(self, event: AstrMessageEvent):
        """获取二次元图片。"""
        user_id = event.get_sender_id()
        args = event.message_str.strip().split()
        if args:
            args = args[1:]

        want_r18 = False
        if args and args[0].lower() in ("r18", "r-18"):
            want_r18 = True
            keyword = " ".join(args[1:]).strip()
        else:
            keyword = " ".join(args).strip()

        remain = self._check_cooldown(user_id)
        if remain > 0:
            yield event.plain_result(f"⏳ 冷却中，请 {remain:.0f} 秒后再试~")
            return

        if self._check_daily_limit(user_id):
            yield event.plain_result(f"📵 你今天已经达到上限({self.daily_limit}次)啦，明天再来吧~")
            return

        r18 = False
        if want_r18:
            if self._r18_allowed(event):
                r18 = True
            else:
                yield event.plain_result("🔞 当前会话未开启 R18 权限。")
                return

        self._record_request(user_id)

        try:
            info = await self._fetch_image(self.default_api, keyword, r18)
        except asyncio.TimeoutError:
            yield event.plain_result("⌛ 请求超时了，待会儿再试试吧~")
            return
        except Exception:
            logger.error("[media_suite] anime image fetch failed", exc_info=True)
            yield event.plain_result("😿 获取图片失败，可能是 API 暂时不可用。")
            return

        if not info or not info.get("url"):
            tip = f"找不到「{keyword}」相关的图片~" if keyword else "没有获取到图片，换个来源试试?"
            yield event.plain_result(f"🔍 {tip}")
            return

        img_url = self._apply_proxy(info["url"])
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
        """显示插件使用帮助。"""
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

    @dataclass
    class _SearchState:
        items: list[SearchItem]
        error: str | None = None

    @filter.command("gal", alias={"galgame", "搜gal"})
    async def search_all(self, event: AstrMessageEvent, keyword: str):
        """聚合搜索萌娘百科和鲲 Galgame 论坛。"""
        keyword = keyword.strip()
        if not keyword:
            yield event.plain_result("请输入要搜索的 Galgame 关键词，例如 /gal 樱之诗")
            return

        try:
            moe_task = self._collect_source("萌娘百科", self._search_moegirl(keyword))
            kun_task = self._collect_source("鲲论坛", self._search_kungal(keyword))
            moe_result, kun_result = await asyncio.gather(moe_task, kun_task)

            items = moe_result.items[:1] + kun_result.items[:1]
            errors = [err for err in (moe_result.error, kun_result.error) if err]
            yield event.plain_result(self._format_results(keyword, items, "聚合搜索", errors))
        except Exception:
            logger.error("[media_suite] gal aggregate search failed", exc_info=True)
            yield event.plain_result("搜索时出错了，请稍后再试。")

    @filter.command("galmoe", alias={"萌百", "萌娘百科"})
    async def search_moegirl(self, event: AstrMessageEvent, keyword: str):
        """搜索萌娘百科条目。"""
        keyword = keyword.strip()
        if not keyword:
            yield event.plain_result("请输入要搜索的关键词，例如 /galmoe 樱之诗")
            return

        try:
            items = await self._search_moegirl(keyword)
            yield event.plain_result(self._format_results(keyword, items, "萌娘百科"))
        except Exception:
            logger.error("[media_suite] moegirl search failed", exc_info=True)
            yield event.plain_result("搜索萌娘百科时出错了，请稍后再试。")

    @filter.command("漫画", alias={"搜漫画", "manga", "comic"})
    async def search_manga(self, event: AstrMessageEvent, keyword: str = ""):
        """搜索漫画作品（萌娘百科数据源）。"""
        keyword = keyword.strip()
        if not keyword:
            yield event.plain_result("请输入要搜索的漫画名，例如 /漫画 进击的巨人")
            return

        try:
            items = await self._search_moegirl_manga(keyword)
            if not items:
                yield event.plain_result(f"🔍 没找到与「{keyword}」相关的漫画~")
                return
            yield event.plain_result(self._format_manga_results(keyword, items))
        except Exception:
            logger.error("[media_suite] manga search failed", exc_info=True)
            yield event.plain_result("搜索漫画时出错了，请稍后再试。")

    @filter.command("漫画帮助", alias={"漫画说明"})
    async def manga_help(self, event: AstrMessageEvent):
        """显示漫画搜索帮助。"""
        msg = (
            "📚 漫画搜索使用帮助\n"
            "————————————\n"
            "/漫画 作品名       搜索漫画作品\n"
            "/漫画 进击的巨人   示例搜索\n"
            "/漫画帮助          显示本帮助\n"
            "————————————\n"
            "数据源：萌娘百科\n"
            "支持：日漫、国漫、韩漫等各类漫画作品"
        )
        yield event.plain_result(msg)

    @filter.command("galkun", alias={"鲲", "鲲论坛"})
    async def search_kungal(self, event: AstrMessageEvent, keyword: str):
        """搜索鲲 Galgame 论坛作品与话题。"""
        keyword = keyword.strip()
        if not keyword:
            yield event.plain_result("请输入要搜索的关键词，例如 /galkun 樱之诗")
            return

        try:
            items = await self._search_kungal(keyword)
            yield event.plain_result(self._format_results(keyword, items, "鲲论坛"))
        except Exception:
            logger.error("[media_suite] kungal search failed", exc_info=True)
            yield event.plain_result("搜索鲲论坛时出错了，请稍后再试。")

    @filter.command("番剧", alias={"搜番", "动画", "anime"})
    async def search_anime(self, event: AstrMessageEvent, keyword: str = ""):
        """搜索番剧（Bangumi），返回封面、评分、简介等信息。"""
        keyword = keyword.strip()
        if not keyword:
            yield event.plain_result("请输入要搜索的番剧名，例如 /番剧 间谍过家家")
            return

        try:
            items = await self._search_bangumi(keyword)
        except Exception as exc:
            logger.error("[media_suite] bangumi search failed", exc_info=True)
            yield event.plain_result(self._bangumi_error_tip(exc))
            return

        if not items:
            yield event.plain_result(f"🔍 没找到与「{keyword}」相关的番剧~")
            return

        # 第一个结果附带封面与详情，其余作为相关结果列表展示，避免刷屏
        first = items[0]
        chain: list[Any] = []
        if self.bgm_show_cover and first.get("cover"):
            chain.append(Comp.Image.fromURL(first["cover"]))
        chain.append(Comp.Plain(self._format_bangumi_detail(first)))

        if len(items) > 1:
            extra_lines = ["", "📺 其他相关结果："]
            for it in items[1:]:
                name = it.get("name") or it.get("name_cn") or "未知"
                extra_lines.append(f"· {name}  {it.get('url', '')}")
            chain.append(Comp.Plain("\n".join(extra_lines)))

        yield event.chain_result(chain)

    @filter.command("今日番剧", alias={"番剧表", "放送", "每日放送", "放送表"})
    async def anime_calendar(self, event: AstrMessageEvent, day: str = ""):
        """查看每日番剧放送表，可指定星期，如 /番剧表 周三、/今日番剧 明天。"""
        weekday, label = self._resolve_weekday(day)

        try:
            entries = await self._fetch_bangumi_calendar(weekday)
        except Exception as exc:
            logger.error("[media_suite] bangumi calendar failed", exc_info=True)
            yield event.plain_result(self._bangumi_error_tip(exc))
            return

        if not entries:
            yield event.plain_result(f"{label}暂时没有放送的番剧哦~")
            return

        lines = [f"📅 {label}放送番剧（共 {len(entries)} 部）", "————————————"]
        for it in entries[: self.bgm_calendar_limit]:
            name = it.get("name") or "未知"
            # 放送时间 + 更新到第几话
            meta = []
            if it.get("pub_time"):
                meta.append(it["pub_time"])
            if it.get("pub_index"):
                meta.append(it["pub_index"])
            meta_text = f"  ({' '.join(meta)})" if meta else ""
            lines.append(f"· {name}{meta_text}")
        if len(entries) > self.bgm_calendar_limit:
            lines.append(f"…… 还有 {len(entries) - self.bgm_calendar_limit} 部未显示")
        yield event.plain_result("\n".join(lines))

    def _resolve_weekday(self, day: str) -> tuple[int, str]:
        """将用户输入解析为 ISO 星期号与展示标签。无输入则返回今天。"""
        day = (day or "").strip().lower()
        today_iso = date.today().isoweekday()
        if not day or day in ("今天", "today", "今日"):
            return today_iso, "今日"
        if day in ("明天", "tomorrow", "明日"):
            wd = today_iso % 7 + 1
            return wd, f"明天（{WEEKDAY_NAMES[wd]}）"
        if day in ("昨天", "yesterday", "昨日"):
            wd = (today_iso - 2) % 7 + 1
            return wd, f"昨天（{WEEKDAY_NAMES[wd]}）"
        wd = WEEKDAY_ALIASES.get(day)
        if wd:
            return wd, WEEKDAY_NAMES[wd]
        # 无法识别时回退到今天
        return today_iso, "今日"

    def _bangumi_error_tip(self, exc: Exception) -> str:
        """根据异常类型给出针对性的番剧错误提示。"""
        is_timeout = isinstance(exc, (asyncio.TimeoutError, TimeoutError))
        is_network = isinstance(exc, (URLError, OSError, ConnectionError))
        text = (str(getattr(exc, "reason", exc)) or str(exc)).lower()
        if is_timeout or is_network or "unreachable" in text or "refused" in text or "timed out" in text:
            return "📡 连接 Bilibili 接口失败，请检查服务器网络后重试。"
        if "code=" in text or "风控" in text or "412" in text:
            # B 站搜索风控：清除缓存的 buvid，下次重新获取
            self._bili_buvid3 = None
            return "🚧 番剧搜索被 Bilibili 风控拦截了，请稍后再试一次。"
        return "搜索番剧时出错了，可能是接口暂时不可用，请稍后再试。"

    # ==================== 以图搜番 / 以图搜图 ====================

    @filter.command("搜番图", alias={"以图搜番", "截图搜番", "搜动画"})
    async def search_anime_by_image(self, event: AstrMessageEvent):
        """以图搜番：识别动画截图来自哪部番、第几集、什么时间点（trace.moe）。"""
        async for result in self._image_search_entry(event, "trace"):
            yield result

    @filter.command("搜图", alias={"识图", "以图搜图", "搜源", "找图源"})
    async def search_image_source(self, event: AstrMessageEvent):
        """以图搜图：查找图片出处（Pixiv/画师/作品等，SauceNAO）。"""
        async for result in self._image_search_entry(event, "sauce"):
            yield result

    def _extract_image_url(self, event: AstrMessageEvent) -> str | None:
        """从消息链中提取第一张图片的 URL（含被引用的消息）。"""
        try:
            components = list(getattr(event.message_obj, "message", None) or [])
        except Exception:
            components = []

        def pick_from(comp: Any) -> str | None:
            cls_name = type(comp).__name__
            if cls_name == "Image":
                # 不同适配器可能用 url 或 file 承载链接
                url = getattr(comp, "url", None) or getattr(comp, "file", None)
                url = str(url or "").strip()
                if url.startswith("http"):
                    return url
            return None

        for comp in components:
            url = pick_from(comp)
            if url:
                return url
            # 处理引用消息：Reply 组件内可能嵌套图片
            if type(comp).__name__ == "Reply":
                nested = getattr(comp, "chain", None) or []
                for sub in nested:
                    url = pick_from(sub)
                    if url:
                        return url
        return None

    async def _image_search_entry(self, event: AstrMessageEvent, mode: str):
        """以图搜索统一入口：当前消息有图直接搜，否则进入会话等待用户补发图片。"""
        img_url = self._extract_image_url(event)
        if img_url:
            async for result in self._do_image_search(event, mode, img_url):
                yield result
            return

        # 没有图片，进入会话等待
        tip = "请发送要搜索的动画截图~" if mode == "trace" else "请发送要查找出处的图片~"
        yield event.plain_result(f"🖼️ {tip}（{self.image_search_timeout} 秒内有效）")

        try:
            from astrbot.core.utils.session_waiter import session_waiter, SessionController
        except Exception:
            logger.warning("[media_suite] session_waiter 不可用，跳过会话等待")
            return

        plugin = self

        @session_waiter(timeout=self.image_search_timeout, record_history_chains=False)
        async def _wait_image(controller: "SessionController", inner_event: AstrMessageEvent):
            url = plugin._extract_image_url(inner_event)
            if not url:
                await inner_event.send(inner_event.plain_result("没识别到图片哦，请直接发送一张图片~"))
                controller.keep(timeout=plugin.image_search_timeout, reset_timeout=True)
                return
            async for result in plugin._do_image_search(inner_event, mode, url):
                await inner_event.send(result)
            controller.stop()

        try:
            await _wait_image(event)
        except TimeoutError:
            yield event.plain_result("⌛ 等待超时，已取消本次搜索。")
        except Exception:
            logger.error("[media_suite] image search waiter failed", exc_info=True)
            yield event.plain_result("搜索过程出错了，请稍后再试。")
        finally:
            event.stop_event()

    async def _do_image_search(self, event: AstrMessageEvent, mode: str, img_url: str):
        """执行实际的以图搜索并 yield 结果消息。"""
        try:
            if mode == "trace":
                text = await self._search_trace_moe(img_url)
            else:
                text = await self._search_saucenao(img_url)
        except asyncio.TimeoutError:
            yield event.plain_result("⌛ 搜索请求超时了，待会儿再试试吧~")
            return
        except RuntimeError as exc:
            # 接口返回了非 JSON 内容，通常是限流 / 被拦截 / IP 被封
            logger.warning(f"[media_suite] {mode} image search bad response: {exc}")
            hint = ""
            if mode == "sauce" and not self.saucenao_api_key:
                hint = "\n可能触发了限流，建议在配置中填写 saucenao_api_key 后重试。"
            elif mode == "sauce":
                hint = "\n可能触发了频率限制，请稍后再试。"
            else:
                hint = "\n可能触发了频率限制或图片无法被接口访问，请稍后再试。"
            yield event.plain_result(f"😿 搜索接口返回异常。{hint}")
            return
        except Exception:
            logger.error(f"[media_suite] {mode} image search failed", exc_info=True)
            yield event.plain_result("😿 搜索失败，可能是接口暂时不可用。")
            return
        yield event.plain_result(text)

    async def _aiohttp_get_json(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        force_ipv4: bool = False,
        proxy: str | None = None,
    ) -> Any:
        """通过 aiohttp 发起 GET 并安全解析 JSON。

        部分接口在限流/出错时会返回 HTML 错误页而非 JSON，这里读取原始文本后
        再尝试解析，失败时抛出带状态码与内容片段的异常，便于上层给出友好提示。

        force_ipv4 为 True 时强制使用 IPv4：某些服务器解析到目标的 IPv6 地址却没有
        IPv6 出口，直连会立刻报 Network unreachable，强制 IPv4 可绕开该问题。
        proxy 指定 HTTP 代理地址（如 http://127.0.0.1:7890），用于访问被网络阻断的站点。
        """
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        # 走代理时不强制 IPv4，交由代理自行解析目标地址
        use_ipv4 = force_ipv4 and not proxy
        connector = aiohttp.TCPConnector(family=socket.AF_INET) if use_ipv4 else None
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(url, headers=headers, proxy=proxy or None) as resp:
                status = resp.status
                raw = await resp.text()
        raw = (raw or "").strip()
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            snippet = re.sub(r"\s+", " ", raw)[:80]
            raise RuntimeError(f"非 JSON 响应 (HTTP {status})：{snippet or '空内容'}")

    async def _search_trace_moe(self, img_url: str) -> str:
        params = {"url": img_url}
        if self.trace_anilist_chat:
            params["anilistInfo"] = ""  # 附带 AniList 元数据（标题等）
        url = f"{self.trace_api_url}?{urlencode(params)}"
        data = await self._aiohttp_get_json(url)

        if not isinstance(data, dict):
            return "trace.moe 返回了无法解析的数据。"
        if data.get("error"):
            return f"trace.moe 报错：{data['error']}"
        results = data.get("result") or []
        if not results:
            return "🔍 没找到匹配的番剧，换张更清晰的截图试试？"

        best = results[0]
        similarity = float(best.get("similarity") or 0)
        title = self._pick_trace_title(best.get("anilist"))
        episode = best.get("episode")
        at = best.get("from")
        lines = ["📺 以图搜番结果（trace.moe）", "————————————"]
        lines.append(f"番名：{title}")
        if episode not in (None, "", 0):
            lines.append(f"集数：第 {episode} 集")
        if isinstance(at, (int, float)):
            lines.append(f"时间点：{self._format_timestamp(at)}")
        lines.append(f"相似度：{similarity * 100:.1f}%")
        if similarity < self.trace_min_similarity:
            lines.append("⚠️ 相似度偏低，结果可能不准确。")
        return "\n".join(lines)

    @staticmethod
    def _pick_trace_title(anilist: Any) -> str:
        if isinstance(anilist, dict):
            title = anilist.get("title")
            if isinstance(title, dict):
                return (
                    str(title.get("native") or "").strip()
                    or str(title.get("romaji") or "").strip()
                    or str(title.get("english") or "").strip()
                    or "未知"
                )
        return "未知"

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        total = int(seconds)
        return f"{total // 60:02d}:{total % 60:02d}"

    async def _search_saucenao(self, img_url: str) -> str:
        params = {
            "url": img_url,
            "output_type": 2,  # JSON
            "numres": self.saucenao_result_limit,
            "db": 999,  # 检索所有索引库
        }
        if self.saucenao_api_key:
            params["api_key"] = self.saucenao_api_key
        url = f"{self.saucenao_api_url}?{urlencode(params)}"
        data = await self._aiohttp_get_json(url)

        if not isinstance(data, dict):
            return "SauceNAO 返回了无法解析的数据。"
        header = data.get("header") or {}
        if header.get("status", 0) < 0:
            msg = header.get("message") or "请求被拒绝"
            extra = "" if self.saucenao_api_key else "（建议在配置中填写 saucenao_api_key 提升配额）"
            return f"SauceNAO 报错：{msg}{extra}"
        results = data.get("results") or []
        # 按相似度过滤并取前 N 条
        picked = []
        for item in results:
            if not isinstance(item, dict):
                continue
            h = item.get("header") or {}
            try:
                sim = float(h.get("similarity") or 0)
            except (TypeError, ValueError):
                sim = 0
            if sim >= self.saucenao_min_similarity:
                picked.append((sim, item))
            if len(picked) >= self.saucenao_result_limit:
                break

        if not picked:
            tip = "（可调低 saucenao_min_similarity 阈值再试）" if results else ""
            return f"🔍 没找到足够相似的图片出处~{tip}"

        lines = ["🖼️ 以图搜图结果（SauceNAO）", "————————————"]
        for idx, (sim, item) in enumerate(picked, 1):
            lines.append(f"{idx}. 相似度 {sim:.1f}%")
            detail = self._format_saucenao_data(item.get("data") or {})
            lines.extend(detail)
            if idx < len(picked):
                lines.append("")
        return "\n".join(lines)

    def _format_saucenao_data(self, data: dict[str, Any]) -> list[str]:
        """SauceNAO 不同索引库字段不一，这里通用提取标题、出处链接、作者。"""
        lines: list[str] = []
        title = (
            data.get("title")
            or data.get("source")
            or data.get("eng_name")
            or data.get("material")
            or ""
        )
        title = self._clean_text(str(title)).strip()
        if title:
            lines.append(f"   标题：{self._shorten(title, 80)}")

        author = (
            data.get("member_name")
            or data.get("author_name")
            or data.get("creator")
            or data.get("author")
            or ""
        )
        if isinstance(author, list):
            author = ", ".join(str(a) for a in author if a)
        author = str(author).strip()
        if author:
            lines.append(f"   作者：{self._shorten(author, 60)}")

        if data.get("pixiv_id"):
            lines.append(f"   Pixiv：https://www.pixiv.net/artworks/{data['pixiv_id']}")

        ext_urls = data.get("ext_urls") or []
        if isinstance(ext_urls, list) and ext_urls:
            lines.append(f"   出处：{ext_urls[0]}")
        return lines

    # ==================== 二次元一言 ====================

    @filter.command("一言", alias={"hitokoto", "语录", "来句话"})
    async def hitokoto(self, event: AstrMessageEvent, category: str = ""):
        """获取一条二次元一言/语录，可指定类型，如 /一言 动画。"""
        category = (category or "").strip().lower()
        type_code = HITOKOTO_TYPES.get(category, self.hitokoto_default_type)

        params = {}
        if type_code:
            params["c"] = type_code
        url = self.hitokoto_api_url
        if params:
            url = f"{url}?{urlencode(params)}"

        try:
            data = await self._get_json(url)
        except asyncio.TimeoutError:
            yield event.plain_result("⌛ 一言接口超时了，待会儿再试试吧~")
            return
        except Exception:
            logger.error("[media_suite] hitokoto fetch failed", exc_info=True)
            yield event.plain_result("😿 获取一言失败，可能是接口暂时不可用。")
            return

        if not isinstance(data, dict) or not str(data.get("hitokoto") or "").strip():
            yield event.plain_result("没拿到一言内容，换个类型再试试？")
            return

        text = str(data["hitokoto"]).strip()
        lines = [f"『{text}』"]
        if self.hitokoto_show_source:
            source = self._format_hitokoto_source(data)
            if source:
                lines.append(source)
        yield event.plain_result("\n".join(lines))

    @staticmethod
    def _format_hitokoto_source(data: dict[str, Any]) -> str:
        """组合一言出处：—— 作者「作品」。"""
        who = str(data.get("from_who") or "").strip()
        work = str(data.get("from") or "").strip()
        if who and work:
            return f"     —— {who}「{work}」"
        if work:
            return f"     —— 「{work}」"
        if who:
            return f"     —— {who}"
        return ""

    async def _search_moegirl(self, keyword: str) -> list[SearchItem]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "format": "json",
            "srlimit": self.result_limit,
            "utf8": 1,
        }
        url = f"{self.moe_api_url}?{urlencode(params)}"
        data = await self._get_json(url)
        search_items = data.get("query", {}).get("search", [])

        first_item = next((item for item in search_items if str(item.get("title", "")).strip()), None)
        if not first_item:
            return []

        title = str(first_item.get("title", "")).strip()
        summary = await self._get_moegirl_intro(title, fallback=str(first_item.get("snippet", "")))
        page_slug = quote(title.replace(" ", "_"), safe="")
        page_url = f"{self.moe_page_url}/{page_slug}"
        return [
            SearchItem(
                source="萌娘百科",
                title=title,
                url=page_url,
                summary=summary,
            )
        ]

    async def _search_moegirl_manga(self, keyword: str) -> list[dict[str, Any]]:
        """搜索萌娘百科漫画条目，返回多个结果便于用户选择。"""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "format": "json",
            "srlimit": self.result_limit * 2,  # 多获取一些结果用于过滤
            "utf8": 1,
        }
        url = f"{self.moe_api_url}?{urlencode(params)}"
        data = await self._get_json(url)
        search_items = data.get("query", {}).get("search", [])

        if not search_items:
            return []

        results = []
        for item in search_items[:self.result_limit]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue

            # 获取详细信息
            summary = await self._get_moegirl_intro(title, fallback=str(item.get("snippet", "")))
            page_slug = quote(title.replace(" ", "_"), safe="")
            page_url = f"{self.moe_page_url}/{page_slug}"

            results.append({
                "title": title,
                "summary": summary,
                "url": page_url,
                "snippet": self._clean_text(str(item.get("snippet", ""))),
            })

        return results

    def _format_manga_results(self, keyword: str, items: list[dict[str, Any]]) -> str:
        """格式化漫画搜索结果。"""
        if not items:
            return f"🔍 没找到与「{keyword}」相关的漫画~"

        lines = [f"📚 漫画搜索「{keyword}」：", "————————————"]

        # 显示第一个结果的详细信息
        first = items[0]
        lines.append(f"📖 {first['title']}")
        if first.get("summary"):
            lines.append(f"简介：{self._shorten(first['summary'], self.intro_max_length)}")
        lines.append(f"链接：{first['url']}")

        # 如果有多个结果，列出其他相关结果
        if len(items) > 1:
            lines.append("")
            lines.append("📑 其他相关结果：")
            for item in items[1:]:
                lines.append(f"· {item['title']}")
                lines.append(f"  {item['url']}")

        return "\n".join(lines)

    async def _get_moegirl_intro(self, title: str, fallback: str) -> str:
        params = {
            "action": "query",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "redirects": 1,
            "titles": title,
            "format": "json",
            "utf8": 1,
        }
        try:
            url = f"{self.moe_api_url}?{urlencode(params)}"
            data = await self._get_json(url)
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                intro = self._clean_text(str(page.get("extract", "")))
                if intro:
                    return self._shorten(intro, self.intro_max_length)
        except Exception:
            logger.warning("[media_suite] moegirl intro fetch failed", exc_info=True)
        return self._shorten(self._clean_text(fallback), self.intro_max_length)

    async def _collect_source(
        self,
        source_name: str,
        task: Awaitable[list[SearchItem]],
    ) -> _SearchState:
        try:
            return self._SearchState(await task, None)
        except Exception as exc:
            logger.warning(f"[media_suite] {source_name} search failed", exc_info=True)
            return self._SearchState([], f"{source_name}暂时不可用：{exc}")

    async def _search_kungal(self, keyword: str) -> list[SearchItem]:
        galgames = await self._search_kungal_type(keyword, "galgame")
        if galgames or not self.search_kun_topics:
            return galgames[:1]
        topics = await self._search_kungal_type(keyword, "topic")
        return topics[:1]

    async def _search_kungal_type(self, keyword: str, search_type: str) -> list[SearchItem]:
        params = {
            "keywords": keyword,
            "type": search_type,
            "page": 1,
            "limit": self.result_limit,
        }
        url = f"{self.kun_api_base}/search?{urlencode(params)}"
        data = await self._get_json(url)
        payload = data.get("data", data)
        raw_items = payload.get("items", []) if isinstance(payload, dict) else []

        results: list[SearchItem] = []
        for item in raw_items[:1]:
            if not isinstance(item, dict):
                continue
            if search_type == "galgame":
                result = await self._format_kungal_galgame(item)
            else:
                result = self._format_kungal_topic(item)
            if result:
                results.append(result)
        return results

    async def _format_kungal_galgame(self, item: dict[str, Any]) -> SearchItem | None:
        gid = item.get("id")
        name = item.get("name", {})
        title = self._pick_name(name) if isinstance(name, dict) else str(name or "")
        if not gid or not title:
            return None

        platform = ", ".join(item.get("platform") or [])
        language = ", ".join(item.get("language") or [])
        content_limit = str(item.get("contentLimit") or "").upper()
        meta_parts = [part for part in [platform, language, content_limit] if part]
        summary = await self._get_kungal_intro(str(gid))
        if not summary:
            summary = f"浏览 {item.get('view', 0)} / 喜欢 {item.get('likeCount', 0)}"
        return SearchItem(
            source="鲲 Galgame",
            title=title,
            url=f"{self.kun_site_url}/galgame/{gid}",
            summary=summary,
            meta=" | ".join(meta_parts),
        )

    async def _get_kungal_intro(self, gid: str) -> str:
        try:
            data = await self._get_json(f"{self.kun_api_base}/galgame/{gid}")
            payload = data.get("data", data)
            if not isinstance(payload, dict):
                return ""
            introduction = payload.get("introduction", {})
            if isinstance(introduction, dict):
                intro = self._pick_localized_text(introduction)
            else:
                intro = str(introduction or "")
            intro = self._clean_text(intro)
            return self._shorten(intro, self.intro_max_length)
        except Exception:
            logger.warning("[media_suite] kungal intro fetch failed", exc_info=True)
            return ""

    def _format_kungal_topic(self, item: dict[str, Any]) -> SearchItem | None:
        topic_id = item.get("id")
        title = str(item.get("title") or "").strip()
        if not topic_id or not title:
            return None

        tags = item.get("tag") or []
        summary = (
            f"浏览 {item.get('view', 0)} / 回复 {item.get('replyCount', 0)} "
            f"/ 喜欢 {item.get('likeCount', 0)}"
        )
        return SearchItem(
            source="鲲话题",
            title=title,
            url=f"{self.kun_site_url}/topic/{topic_id}",
            summary=summary,
            meta=", ".join(tags[:4]),
        )

    @staticmethod
    def _normalize_url(url: str) -> str:
        """补全协议相对链接并将 http 升级为 https（部分平台发图要求 https）。"""
        url = str(url or "").strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http://"):
            return "https://" + url[len("http://"):]
        return url

    def _bili_headers(self) -> dict[str, str]:
        """B 站接口需要带常见浏览器 UA 和 Referer，否则易触发风控。"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://www.bilibili.com",
        }
        if self._bili_buvid3:
            headers["Cookie"] = f"buvid3={self._bili_buvid3}; buvid4={self._bili_buvid3}"
        return headers

    async def _ensure_bili_buvid(self) -> None:
        """获取并缓存 buvid3。B 站搜索接口需带此 cookie 才能绕过 -412 风控。"""
        if self._bili_buvid3:
            return
        try:
            data = await self._aiohttp_get_json(
                "https://api.bilibili.com/x/frontend/finger/spi",
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"},
            )
            buvid = (data.get("data") or {}).get("b_3") if isinstance(data, dict) else None
            if buvid:
                self._bili_buvid3 = str(buvid)
        except Exception:
            logger.warning("[media_suite] 获取 bilibili buvid 失败", exc_info=True)

    def _extract_bili_search_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """从 B 站番剧搜索结果中提取常用字段。"""
        score_obj = item.get("media_score") or {}
        score = score_obj.get("score") if isinstance(score_obj, dict) else None
        # styles 可能是字符串或列表
        styles = item.get("styles")
        if isinstance(styles, list):
            styles = "/".join(str(s) for s in styles if s)
        pubtime = item.get("pubtime")
        air_date = ""
        if isinstance(pubtime, (int, float)) and pubtime > 0:
            air_date = date.fromtimestamp(int(pubtime)).isoformat()
        return {
            "id": item.get("season_id") or item.get("media_id"),
            # 搜索结果标题含 <em class="keyword"> 高亮标签，需清理
            "name": self._clean_text(str(item.get("title") or "")),
            "name_cn": "",  # B 站 title 已是中文名，单独保留原名到 org
            "org_title": str(item.get("org_title") or "").strip(),
            "cover": self._normalize_url(str(item.get("cover") or "")),
            "score": score,
            "area": str(item.get("areas") or "").strip(),
            "styles": str(styles or "").strip(),
            "air_date": air_date,
            "eps": item.get("ep_size"),
            "summary": self._clean_text(str(item.get("desc") or "")),
            "url": str(item.get("url") or "").strip(),
        }

    async def _get_wbi_mixin_key(self) -> str:
        """获取 B 站 WBI 签名的 mixin_key（img_key + sub_key）。"""
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"}
        url = "https://api.bilibili.com/x/web-interface/nav"
        try:
            data = await self._aiohttp_get_json(url, headers=headers)
            wbi = (data.get("data") or {}).get("wbi_img") or {}
            img_url = wbi.get("img_url", "")
            sub_url = wbi.get("sub_url", "")
            if not img_url or not sub_url:
                raise RuntimeError("无法获取 wbi_img")
            img_key = re.search(r"/([^/]+)\.png", img_url).group(1)
            sub_key = re.search(r"/([^/]+)\.png", sub_url).group(1)
            return img_key + sub_key
        except Exception as e:
            logger.warning(f"[media_suite] 获取 WBI mixin_key 失败: {e}")
            raise

    def _wbi_sign(self, params: dict[str, Any], mixin_key: str) -> dict[str, Any]:
        """对参数字典进行 WBI 签名，返回含 wts 和 w_rid 的新字典。"""
        keys = sorted(params.keys())
        signed = {k: params[k] for k in keys}
        signed["wts"] = int(time.time())
        query = urlencode(signed)
        signed["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
        return signed

    async def _search_bangumi(self, keyword: str) -> list[dict[str, Any]]:
        mixin_key = await self._get_wbi_mixin_key()
        params = self._wbi_sign({"keyword": keyword, "page": 1}, mixin_key)
        url = f"https://api.bilibili.com/x/web-interface/wbi/search/all/v2?{urlencode(params)}"
        data = await self._aiohttp_get_json(url, headers=self._bili_headers())
        if not isinstance(data, dict):
            return []
        if data.get("code") != 0:
            raise RuntimeError(f"bilibili WBI 搜索返回 code={data.get('code')}: {data.get('message')}")
        # 从综合搜索结果中提取番剧类型的结果
        result_list = (data.get("data") or {}).get("result") or []
        bangumi_data = []
        for block in result_list:
            if isinstance(block, dict) and block.get("result_type") == "media_bangumi":
                bangumi_data = block.get("data") or []
                break
        if not isinstance(bangumi_data, list):
            return []
        results: list[dict[str, Any]] = []
        for item in bangumi_data[: self.bgm_result_limit]:
            if isinstance(item, dict) and (item.get("season_id") or item.get("media_id")):
                results.append(self._extract_bili_search_item(item))
        return results

    def _extract_bili_timeline_item(self, ep: dict[str, Any]) -> dict[str, Any]:
        """从 B 站放送 timeline 的 episode 中提取字段。"""
        sid = ep.get("season_id")
        return {
            "id": sid,
            "name": str(ep.get("title") or "").strip(),
            "cover": self._normalize_url(str(ep.get("cover") or "")),
            "pub_index": str(ep.get("pub_index") or "").strip(),
            "pub_time": str(ep.get("pub_time") or "").strip(),
            "published": ep.get("published"),
            "url": f"https://www.bilibili.com/bangumi/play/ss{sid}" if sid else "",
        }

    async def _fetch_bangumi_calendar(self, weekday: int) -> list[dict[str, Any]]:
        # before/after 各取 3 天，确保覆盖到目标星期
        params = {"types": 1, "before": 3, "after": 3}
        url = f"{self.bili_timeline_api}?{urlencode(params)}"
        data = await self._aiohttp_get_json(url, headers=self._bili_headers())
        if not isinstance(data, dict) or data.get("code") != 0:
            return []
        blocks = data.get("result") or []
        if not isinstance(blocks, list):
            return []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("day_of_week") == weekday:
                eps = block.get("episodes") or []
                return [
                    self._extract_bili_timeline_item(ep)
                    for ep in eps
                    if isinstance(ep, dict) and ep.get("season_id")
                ]
        return []

    def _format_bangumi_detail(self, item: dict[str, Any]) -> str:
        name = item.get("name") or item.get("name_cn") or "未知作品"
        lines = [f"📺 {name}"]
        if item.get("org_title") and item.get("org_title") != name:
            lines.append(f"原名：{item['org_title']}")
        info_parts = []
        if item.get("score"):
            info_parts.append(f"评分 {item['score']}")
        if item.get("area"):
            info_parts.append(item["area"])
        if item.get("air_date"):
            info_parts.append(f"开播 {item['air_date']}")
        if item.get("eps"):
            info_parts.append(f"{item['eps']} 话")
        if info_parts:
            lines.append(" | ".join(info_parts))
        if item.get("styles"):
            lines.append(f"标签：{item['styles']}")
        if item.get("summary"):
            lines.append("简介：" + self._shorten(item["summary"], self.intro_max_length))
        if item.get("url"):
            lines.append("链接：" + item["url"])
        return "\n".join(lines)


    async def _get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._blocking_get_json, url, headers)

    def _blocking_get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        merged_headers = {
            "User-Agent": "AstrBot Media Suite/1.0",
            "Accept": "application/json,text/plain,*/*",
        }
        if headers:
            merged_headers.update(headers)
        request = Request(url, headers=merged_headers)
        last_error: Exception | None = None
        for _ in range(2):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    content = response.read().decode(charset, errors="replace")
                return json.loads(content)
            except TimeoutError as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("empty HTTP response")

    def _format_results(
        self,
        keyword: str,
        items: list[SearchItem],
        source_name: str,
        errors: list[str] | None = None,
    ) -> str:
        if not items:
            if errors:
                return (
                    f"{source_name}没有拿到「{keyword}」的结果。\n"
                    + "\n".join(f"- {error}" for error in errors)
                )
            return f"{source_name}没有找到与「{keyword}」相关的结果。"

        lines = [f"{source_name}「{keyword}」："]
        if errors:
            lines.extend(f"提示：{error}" for error in errors)
        for item in items:
            lines.append(f"[{item.source}] {item.title}")
            detail = self._compact_detail(item)
            if detail:
                lines.append(f"简介：{detail}")
            lines.append(f"链接：{item.url}")
        return "\n".join(lines)

    @staticmethod
    def _compact_detail(item: SearchItem) -> str:
        parts = []
        if item.meta:
            parts.append(item.meta)
        if item.summary:
            parts.append(item.summary)
        return " / ".join(parts)

    @staticmethod
    def _pick_localized_text(values: dict[str, Any]) -> str:
        for key in ("zh-cn", "zh-tw", "ja-jp", "en-us"):
            value = str(values.get(key) or "").strip()
            if value:
                return value
        for value in values.values():
            text = str(value or "").strip()
            if text:
                return text
        return ""

    @staticmethod
    def _pick_name(name: dict[str, Any]) -> str:
        for key in ("zh-cn", "zh-tw", "ja-jp", "en-us"):
            value = str(name.get(key) or "").strip()
            if value:
                return value
        for value in name.values():
            text = str(value or "").strip()
            if text:
                return text
        return ""

    @staticmethod
    def _clean_text(value: str) -> str:
        value = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", value)
        value = re.sub(r"(?i)</\s*(p|div|h[1-6]|li)\s*>", "\n", value)
        value = re.sub(r"<[^>]+>", "", value)
        value = html.unescape(html.unescape(value))
        value = re.sub(r"\s+", " ", value).strip()
        value = re.sub(r"^(STORY|剧情|简介)\s*", "", value, flags=re.IGNORECASE)
        return value

    @staticmethod
    def _shorten(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "…"

    @staticmethod
    def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = minimum
        return max(minimum, min(maximum, number))

    @staticmethod
    def _clamp_float(value: Any, minimum: float, maximum: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = minimum
        return max(minimum, min(maximum, number))

    async def terminate(self):
        self._last_request.clear()
        self._daily_count.clear()
        logger.info("[media_suite] plugin terminated")
