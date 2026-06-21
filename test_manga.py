#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画搜索功能测试脚本"""

import asyncio
import json
import sys
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


class MangaSearchTester:
    def __init__(self):
        self.moe_api_url = "https://moegirl.icu/api.php"
        self.moe_page_url = "https://moegirl.icu"
        self.result_limit = 3
        self.intro_max_length = 160
        self.timeout_seconds = 8

    async def test_search(self, keyword: str):
        """测试漫画搜索功能"""
        print(f"\n{'='*60}")
        print(f"🔍 搜索关键词：{keyword}")
        print(f"{'='*60}\n")

        try:
            results = await self._search_moegirl_manga(keyword)

            if not results:
                print("❌ 没有找到结果")
                return

            print(f"✅ 找到 {len(results)} 个结果\n")

            for idx, item in enumerate(results, 1):
                print(f"【结果 {idx}】")
                print(f"标题：{item['title']}")
                print(f"链接：{item['url']}")
                if item.get('summary'):
                    summary = self._shorten(item['summary'], 200)
                    print(f"简介：{summary}")
                print()

        except Exception as e:
            print(f"❌ 搜索失败：{e}")
            import traceback
            traceback.print_exc()

    async def _search_moegirl_manga(self, keyword: str):
        """搜索萌娘百科漫画条目"""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "format": "json",
            "srlimit": self.result_limit * 2,
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
            })

        return results

    async def _get_moegirl_intro(self, title: str, fallback: str) -> str:
        """获取萌娘百科条目简介"""
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
                intro = str(page.get("extract", "")).strip()
                if intro:
                    return self._shorten(intro, self.intro_max_length)
        except Exception:
            pass
        return self._shorten(fallback, self.intro_max_length)

    async def _get_json(self, url: str):
        """异步获取 JSON 数据"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._blocking_get_json, url)

    def _blocking_get_json(self, url: str):
        """同步获取 JSON 数据"""
        headers = {
            "User-Agent": "AstrBot Media Suite Test/1.0",
            "Accept": "application/json,text/plain,*/*",
        }
        request = Request(url, headers=headers)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            content = response.read().decode(charset, errors="replace")
        return json.loads(content)

    @staticmethod
    def _shorten(value: str, limit: int) -> str:
        """截断过长的文本"""
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "…"


async def main():
    tester = MangaSearchTester()

    # 测试用例
    test_keywords = [
        "进击的巨人",
        "火影忍者",
        "海贼王",
        "鬼灭之刃",
    ]

    print("\n🚀 开始测试漫画搜索功能...")
    print(f"数据源：萌娘百科 ({tester.moe_api_url})")

    for keyword in test_keywords:
        await tester.test_search(keyword)
        await asyncio.sleep(1)  # 避免请求过快

    print(f"\n{'='*60}")
    print("✅ 测试完成！")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
