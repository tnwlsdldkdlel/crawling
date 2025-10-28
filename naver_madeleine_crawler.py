#!/usr/bin/env python3
"""
네이버 블로그 검색 크롤러 - 마들렌자켓
키워드로 검색하여 블로그 URL 수집 및 콘텐츠 추출
"""
import asyncio
import json
import re
from typing import List, Dict, Optional
from urllib.parse import urlencode, parse_qs, urlparse
from playwright.async_api import async_playwright, Page
from scrapegraphai.graphs import SmartScraperGraph


class NaverBlogSearchCrawler:
    """네이버 블로그 검색 크롤러"""

    def __init__(self, keyword: str, pages: int = 3):
        self.keyword = keyword
        self.pages = pages
        self.base_url = "https://search.naver.com/search.naver"
        self.collected_urls: List[str] = []

        # LLM 설정 (Llama 3 via Ollama)
        self.graph_config = {
            "llm": {
                "model": "ollama/llama3",
                "temperature": 0,
                "format": "json",
                "base_url": "http://localhost:11434",
            },
            "embeddings": {
                "model": "ollama/nomic-embed-text",
                "base_url": "http://localhost:11434",
            },
            "verbose": True,
            "headless": True,
        }

    def _build_search_url(self, page_num: int = 1) -> str:
        """네이버 블로그 검색 URL 생성"""
        params = {
            "where": "blog",
            "sm": "tab_jum",
            "query": self.keyword,
        }

        # 2페이지부터는 start 파라미터 추가
        if page_num > 1:
            params["start"] = (page_num - 1) * 10 + 1

        return f"{self.base_url}?{urlencode(params)}"

    async def _extract_blog_urls_from_page(self, page: Page) -> List[str]:
        """페이지에서 블로그 URL 추출"""
        blog_urls = []

        # 네이버 블로그 검색 결과에서 블로그 링크 찾기
        # 여러 셀렉터 시도
        selectors = [
            'a[href*="blog.naver.com"]',
            '.title_link',
            '.api_txt_lines',
        ]

        for selector in selectors:
            links = await page.query_selector_all(selector)
            for link in links:
                href = await link.get_attribute("href")
                if href and "blog.naver.com" in href:
                    # URL 정제
                    clean_url = self._clean_blog_url(href)
                    if clean_url and clean_url not in blog_urls:
                        blog_urls.append(clean_url)

        return blog_urls

    def _clean_blog_url(self, url: str) -> Optional[str]:
        """블로그 URL 정제 (리다이렉트 제거)"""
        try:
            # 네이버 검색 결과의 리다이렉트 URL 처리
            if "blog.naver.com" in url:
                # 이미 직접 URL이면 그대로 반환
                if url.startswith("http"):
                    return url
                # 상대 경로면 절대 경로로 변환
                elif url.startswith("/"):
                    return f"https://blog.naver.com{url}"

            return None
        except Exception as e:
            print(f"URL 정제 오류: {e}")
            return None

    async def collect_blog_urls(self) -> List[str]:
        """지정된 페이지 수만큼 블로그 URL 수집"""
        print(f"\n{'='*60}")
        print(f"네이버 블로그 검색 크롤링 시작")
        print(f"키워드: {self.keyword}")
        print(f"페이지 수: {self.pages}")
        print(f"{'='*60}\n")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for page_num in range(1, self.pages + 1):
                search_url = self._build_search_url(page_num)
                print(f"[페이지 {page_num}] 검색 중: {search_url}")

                try:
                    await page.goto(search_url, wait_until="networkidle", timeout=30000)

                    # 페이지 로드 대기
                    await asyncio.sleep(2)

                    # 블로그 URL 추출
                    page_urls = await self._extract_blog_urls_from_page(page)
                    print(f"[페이지 {page_num}] {len(page_urls)}개 URL 발견")

                    for url in page_urls:
                        if url not in self.collected_urls:
                            self.collected_urls.append(url)
                            print(f"  → {url}")

                except Exception as e:
                    print(f"[페이지 {page_num}] 오류: {e}")

                # 다음 페이지 요청 전 대기
                await asyncio.sleep(1)

            await browser.close()

        print(f"\n총 {len(self.collected_urls)}개의 고유 블로그 URL 수집 완료\n")
        return self.collected_urls

    async def extract_content_from_blog(self, blog_url: str) -> Optional[Dict]:
        """블로그에서 콘텐츠 추출 (Playwright 사용 - iframe 처리)"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # 블로그 페이지 로드
                await page.goto(blog_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # 기본 정보 추출
                data = {
                    "source_url": blog_url,
                    "title": None,
                    "author": None,
                    "content_preview": None,
                    "image_count": 0
                }

                # 네이버 블로그는 iframe 구조 - mainFrame 찾기
                frames = page.frames
                main_frame = None

                for frame in frames:
                    frame_url = frame.url
                    if 'MainFrame' in frame_url or 'PostView' in frame_url:
                        main_frame = frame
                        break

                # iframe이 없으면 메인 페이지 사용
                if not main_frame:
                    main_frame = page

                # 제목 추출 시도
                try:
                    title_selectors = [
                        '.se-title-text',
                        '.pcol1',
                        'h3.se_textarea',
                        '.post_ct h3',
                        '.se-fs-',
                        '.htitle',
                        'div.se-module.se-module-text h3',
                    ]
                    for selector in title_selectors:
                        title_elem = await main_frame.query_selector(selector)
                        if title_elem:
                            title_text = await title_elem.inner_text()
                            if title_text and title_text.strip():
                                data["title"] = title_text.strip()
                                break
                except Exception as e:
                    print(f"  제목 추출 실패: {e}")

                # 작성자 추출 시도
                try:
                    author_selectors = [
                        '.nick',
                        '.blog_author',
                        '.ell',
                        '.name',
                    ]
                    for selector in author_selectors:
                        author_elem = await main_frame.query_selector(selector)
                        if author_elem:
                            author_text = await author_elem.inner_text()
                            if author_text and author_text.strip():
                                data["author"] = author_text.strip()
                                break
                except Exception as e:
                    print(f"  작성자 추출 실패: {e}")

                # 본문 내용 추출
                try:
                    content_selectors = [
                        '.se-main-container',
                        '#postViewArea',
                        '.post-view',
                        '.se-main-container',
                        'div.se-main-container',
                    ]
                    for selector in content_selectors:
                        content_elem = await main_frame.query_selector(selector)
                        if content_elem:
                            content_text = await content_elem.inner_text()
                            if content_text and content_text.strip():
                                # 처음 500자만 저장
                                data["content_preview"] = content_text[:500].strip()
                                break
                except Exception as e:
                    print(f"  본문 추출 실패: {e}")

                # 이미지 개수 세기
                try:
                    images = await main_frame.query_selector_all('img')
                    data["image_count"] = len(images)
                except:
                    pass

                await browser.close()
                return data

        except Exception as e:
            print(f"콘텐츠 추출 오류 ({blog_url}): {e}")
            return None

    async def run(self) -> List[Dict]:
        """전체 크롤링 파이프라인 실행"""
        # 1. 블로그 URL 수집
        urls = await self.collect_blog_urls()

        if not urls:
            print("수집된 URL이 없습니다.")
            return []

        # 2. 각 블로그에서 콘텐츠 추출
        print(f"\n{'='*60}")
        print(f"콘텐츠 추출 시작 ({len(urls)}개 블로그)")
        print(f"{'='*60}\n")

        extracted_data = []
        for idx, url in enumerate(urls, 1):
            print(f"[{idx}/{len(urls)}] 추출 중: {url}")

            data = await self.extract_content_from_blog(url)
            if data:
                extracted_data.append(data)
                print(f"  ✓ 추출 완료")
            else:
                print(f"  ✗ 추출 실패")

            # API 부하 방지를 위한 대기
            await asyncio.sleep(2)

        print(f"\n총 {len(extracted_data)}개 블로그에서 콘텐츠 추출 완료\n")
        return extracted_data


async def main():
    """메인 실행 함수"""
    # 크롤러 생성 (마들렌자켓, 3페이지)
    crawler = NaverBlogSearchCrawler(keyword="마들렌자켓", pages=3)

    # 크롤링 실행
    results = await crawler.run()

    # 결과 저장
    output_file = "madeleine_jacket_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"결과가 {output_file}에 저장되었습니다.")

    # 결과 요약 출력
    print(f"\n{'='*60}")
    print("추출 결과 요약")
    print(f"{'='*60}")
    for idx, result in enumerate(results, 1):
        print(f"\n[{idx}] {result.get('title', 'N/A')}")
        print(f"작성자: {result.get('author', 'N/A')}")
        print(f"URL: {result.get('source_url', 'N/A')}")
        content_preview = result.get('content_preview', 'N/A')
        if content_preview and content_preview != 'N/A':
            print(f"미리보기: {content_preview[:100]}...")
        else:
            print(f"미리보기: N/A")


if __name__ == "__main__":
    asyncio.run(main())
