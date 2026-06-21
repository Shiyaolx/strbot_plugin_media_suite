#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""表情包功能测试脚本"""

import asyncio
import sys
import aiohttp

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

EMOJI_SOURCES = [
    {"url": "https://api.btstu.cn/sjbz/api.php?lx=dongman&format=json", "type": "json", "field": "imgurl"},
    {"url": "https://www.dmoe.cc/random.php", "type": "redirect"},
    {"url": "https://t.alcy.cc/moe", "type": "redirect"},
    {"url": "https://api.mtyqx.cn/api/random.php", "type": "redirect"},
]


class EmojiTester:
    def __init__(self):
        self.timeout = 20

    async def test_emoji_sources(self):
        """测试所有表情包源"""
        print("\n" + "="*60)
        print("😊 开始测试表情包功能")
        print("="*60 + "\n")

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for idx, src in enumerate(EMOJI_SOURCES, 1):
                print(f"【测试源 {idx}】")
                print(f"URL: {src['url']}")
                print(f"类型: {src['type']}")

                result = await self._try_source(session, src)
                if result:
                    print(f"✅ 成功: {result}")
                else:
                    print(f"❌ 失败")
                print()

    async def _try_source(self, session: aiohttp.ClientSession, src: dict) -> str | None:
        """尝试从一个源获取表情"""
        try:
            async with session.get(src["url"], allow_redirects=True) as resp:
                if resp.status != 200:
                    print(f"   状态码: {resp.status}")
                    return None

                if src["type"] == "redirect":
                    return str(resp.url)

                data = await resp.json(content_type=None)
                if isinstance(data, dict):
                    return data.get(src.get("field", "imgurl"))
                return None
        except asyncio.TimeoutError:
            print(f"   超时")
            return None
        except Exception as e:
            print(f"   错误: {e}")
            return None

    async def test_random_emoji(self, count: int = 3):
        """测试随机获取表情"""
        print("\n" + "="*60)
        print(f"🎲 随机获取 {count} 个表情")
        print("="*60 + "\n")

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        for i in range(count):
            print(f"【第 {i+1} 次】")
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for src in EMOJI_SOURCES:
                    url = await self._try_source(session, src)
                    if url:
                        print(f"✅ 获取成功: {url}")
                        break
                else:
                    print("❌ 所有源都失败了")
            print()
            if i < count - 1:
                await asyncio.sleep(1)


async def main():
    tester = EmojiTester()

    # 测试所有表情包源
    await tester.test_emoji_sources()

    # 测试随机获取
    await tester.test_random_emoji(3)

    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
