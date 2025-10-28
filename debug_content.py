#!/usr/bin/env python3
"""
블로그 원문 내용 확인
"""
import asyncio
from playwright.async_api import async_playwright

async def get_content(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle", timeout=30000)

        # iframe 내부 콘텐츠 가져오기
        content = ""
        frames = page.frames

        for frame in frames:
            try:
                if "mainFrame" in frame.url or "PostView" in frame.url:
                    content = await frame.inner_text("body")
                    break
            except:
                continue

        if not content:
            content = await page.inner_text("body")

        await browser.close()

        print("="*80)
        print("블로그 원문 내용:")
        print("="*80)
        print(content[:2000])  # 첫 2000자만 출력
        print("="*80)

if __name__ == "__main__":
    asyncio.run(get_content("https://blog.naver.com/ah-rchive/224047075395"))
