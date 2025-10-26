#!/usr/bin/env python3
"""
Playwright를 직접 사용해서 블로그 내용 확인
"""

import sys
import asyncio
from playwright.async_api import async_playwright


async def simple_crawl(url: str):
    """Playwright로 직접 페이지 텍스트 가져오기"""

    print("="*80)
    print("네이버 블로그 직접 크롤링 (Playwright)")
    print("="*80)
    print(f"\n대상 URL: {url}\n")

    async with async_playwright() as p:
        print("🌐 브라우저 실행 중...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("📥 페이지 로딩 중...")
        await page.goto(url, wait_until="networkidle")

        # iframe 내부의 콘텐츠 가져오기 (네이버 블로그는 iframe 사용)
        print("🔍 콘텐츠 추출 중...\n")

        # 메인 프레임의 텍스트
        main_content = await page.inner_text("body")

        # iframe 체크
        frames = page.frames
        iframe_content = ""

        for frame in frames:
            try:
                if "mainFrame" in frame.url or "PostView" in frame.url:
                    iframe_content = await frame.inner_text("body")
                    break
            except:
                pass

        await browser.close()

        # 결과 출력
        content = iframe_content if iframe_content else main_content

        print("="*80)
        print("📄 추출된 텍스트 내용:")
        print("="*80)
        print(content[:2000])

        if len(content) > 2000:
            print(f"\n... (총 {len(content)}자, 처음 2000자만 표시)")

        print("\n" + "="*80)
        print("🔍 키워드 검색 결과:")
        print("="*80)

        keywords = ["yarn", "실", "바늘", "사용실", "뜨개질", "코바늘"]
        for keyword in keywords:
            if keyword in content:
                print(f"✅ '{keyword}' 발견!")
                # 해당 키워드 주변 텍스트 표시
                idx = content.find(keyword)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(keyword) + 50)
                context = content[start:end].replace("\n", " ")
                print(f"   컨텍스트: ...{context}...")
            else:
                print(f"❌ '{keyword}' 없음")

        print("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test_simple.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    asyncio.run(simple_crawl(url))
