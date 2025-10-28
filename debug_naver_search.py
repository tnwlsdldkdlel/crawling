#!/usr/bin/env python3
"""
네이버 검색 페이지 디버그
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        keyword = "마들렌자켓"
        search_url = f"https://search.naver.com/search.naver?where=blog&query={keyword}"

        print(f"검색 URL: {search_url}")
        await page.goto(search_url, wait_until="networkidle", timeout=30000)

        # 스크린샷 저장
        await page.screenshot(path="naver_search_debug.png")
        print("스크린샷 저장: naver_search_debug.png")

        # 모든 링크 찾기
        all_links = await page.query_selector_all("a")
        print(f"\n총 {len(all_links)}개의 링크 발견")

        blog_links = []
        for link in all_links:
            href = await link.get_attribute("href")
            if href and "blog.naver.com" in href:
                blog_links.append(href)

        print(f"\n블로그 링크 {len(blog_links)}개 발견:")
        for idx, url in enumerate(blog_links[:10], 1):
            print(f"{idx}. {url}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_search())
