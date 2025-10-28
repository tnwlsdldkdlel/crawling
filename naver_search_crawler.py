#!/usr/bin/env python3
"""
네이버 블로그 검색 및 크롤링 파이프라인

사용법:
    python naver_search_crawler.py <검색_키워드> [개수]

예시:
    python naver_search_crawler.py "마들렌자켓" 10
"""

import sys
import json
import asyncio
import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from playwright.async_api import async_playwright
from supabase import create_client, Client
from dotenv import load_dotenv
import time

# 환경 변수 로드
load_dotenv()


def print_colored(text: str, color: str = "white") -> None:
    """컬러 출력 헬퍼 함수."""
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "white": "\033[0m",
        "bold": "\033[1m",
    }
    end = "\033[0m"
    print(f"{colors.get(color, '')}{text}{end}")


class SupabaseManager:
    """Supabase 데이터베이스 관리자"""

    def __init__(self):
        """환경 변수에서 Supabase 클라이언트 설정 로드"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL 및 SUPABASE_KEY 환경 변수가 필요합니다")

        self.client: Client = create_client(supabase_url, supabase_key)

    def url_exists(self, url: str) -> bool:
        """URL이 이미 데이터베이스에 존재하는지 확인"""
        try:
            response = self.client.table("extractions").select("id").eq("url", url).execute()
            return len(response.data) > 0
        except Exception as e:
            print_colored(f"❌ URL 확인 실패: {e}", "red")
            return False

    def save_extraction(self, url: str, keyword: str, extracted_data: Dict[str, Any]) -> Optional[int]:
        """추출 결과를 Supabase에 저장"""
        try:
            # extracted_sentence에서 project 제거
            extracted_sentence = extracted_data.copy()
            if "project" in extracted_sentence:
                del extracted_sentence["project"]

            # 데이터 준비
            data = {
                "url": url,
                "keyword": keyword,
                "extracted_sentence": extracted_sentence
            }

            # Supabase에 삽입 (중복 URL은 업데이트)
            response = self.client.table("extractions").upsert(
                data,
                on_conflict="url"
            ).execute()

            if response.data and len(response.data) > 0:
                record_id = response.data[0].get('id')
                return record_id
            else:
                return None

        except Exception as e:
            print_colored(f"❌ 데이터베이스 저장 실패: {e}", "red")
            return None


def extract_structured_data(content: str) -> Dict[str, Any]:
    """블로그 콘텐츠에서 구조화된 데이터 추출"""
    extracted = {
        "yarn": None,
        "needle": None,
        "project": None
    }

    # 실 정보 찾기
    yarn_keywords = ["실", "yarn", "사용실"]
    yarn_brands = ["라라뜨개", "솜솜뜨개", "니트러브", "앵콜스 뜨개실", "바늘이야기"]

    # 먼저 브랜드명이 포함된 문장 찾기
    for brand in yarn_brands:
        brand_pattern = rf"([^.\n]*{brand}[^.\n]*)"
        yarn_match = re.search(brand_pattern, content, re.IGNORECASE)
        if yarn_match:
            yarn_text = yarn_match.group(1).strip()[:200]

            # 불필요한 제목/태그 제거
            yarn_text = re.sub(r'\[.*?\]', '', yarn_text)
            yarn_text = re.sub(r'뜨개일기', '', yarn_text)
            yarn_text = re.sub(r'수민님?\s*', '', yarn_text)
            yarn_text = re.sub(r'마들렌\s*자?켓', '', yarn_text)
            yarn_text = re.sub(r'cardigan|자켓|조끼|가디건|베스트|스웨터', '', yarn_text, flags=re.IGNORECASE)

            # 괄호 내용만 추출 시도
            paren_match = re.search(r'\(([^)]+)\)', yarn_text)
            if paren_match:
                yarn_text = paren_match.group(1).strip()

            # mm 정보 제거
            yarn_text = re.sub(r'\s*\d+\.?\d*\s*mm.*', '', yarn_text).strip()
            yarn_text = yarn_text.strip('/ ').strip()

            if yarn_text:
                extracted["yarn"] = yarn_text
                break

    # 브랜드를 못 찾으면 "yarn :" 형식만 검색 (일반 "실" 키워드는 사용하지 않음)
    if not extracted["yarn"]:
        # "yarn :" 형식만 검색
        yarn_match = re.search(r"yarn\s*[:：]\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
        if yarn_match:
            yarn_text = yarn_match.group(1).strip()
            # mm 정보 제거
            yarn_text = re.sub(r'\s*\d+\.?\d*\s*mm.*', '', yarn_text).strip()
            if len(yarn_text) > 1:
                extracted["yarn"] = yarn_text

    # 바늘 정보 찾기
    needle_patterns = [
        r"needle\s*[:：]\s*(.+?)(?:\n|$)",  # needle : 밤부 4mm
        r"바늘\s*[:：]\s*(.+?)(?:\n|사용|$)",  # 바늘: 4mm
        r"([가-힣\s]*[\d.]+\s*mm)",  # 밤부 4mm, 치아오구 5mm 등
    ]
    for pattern in needle_patterns:
        needle = re.search(pattern, content, re.IGNORECASE)
        if needle:
            extracted["needle"] = needle.group(1).strip()[:100]
            break

    # 프로젝트/작품명 찾기
    project_patterns = [
        r"([가-힣]+(?:자켓|조끼|가디건|베스트|스웨터|cardigan|vest|sweater))",
        r"FO[:\s]*([^\n]+)"
    ]
    for pattern in project_patterns:
        project = re.search(pattern, content, re.IGNORECASE)
        if project:
            extracted["project"] = project.group(1).strip()[:100]
            break

    return extracted


async def search_naver_blogs(keyword: str, max_results: int = 10, max_pages: int = 3) -> List[str]:
    """
    네이버에서 블로그 검색하여 URL 리스트 반환

    Args:
        keyword: 검색 키워드
        max_results: 가져올 최대 결과 수
        max_pages: 검색할 최대 페이지 수

    Returns:
        블로그 URL 리스트
    """
    blog_urls = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 여러 페이지 순회
            for page_num in range(1, max_pages + 1):
                # 네이버 블로그 검색 (start: 1, 11, 21, 31, ...)
                start = (page_num - 1) * 10 + 1
                search_url = f"https://search.naver.com/search.naver?where=blog&query={keyword}&start={start}"

                print_colored(f"  페이지 {page_num} 검색 중... (start={start})", "blue")
                await page.goto(search_url, wait_until="networkidle", timeout=30000)

                # 블로그 링크 추출
                # 모든 링크를 가져와서 blog.naver.com 링크만 필터링
                all_links = await page.query_selector_all("a")

                page_blog_count = 0
                for link in all_links:
                    href = await link.get_attribute("href")
                    if href and "blog.naver.com" in href:
                        # 포스트 ID가 있는 링크만 (실제 블로그 포스트)
                        # 예: https://blog.naver.com/username/223844145249
                        if re.search(r'blog\.naver\.com/[^/]+/\d+', href):
                            # 중복 제거
                            if href not in blog_urls:
                                blog_urls.append(href)
                                page_blog_count += 1
                            if len(blog_urls) >= max_results:
                                break

                print_colored(f"    → {page_blog_count}개 발견", "blue")

                # 최대 결과 수에 도달하면 중단
                if len(blog_urls) >= max_results:
                    break

                # 페이지 간 딜레이 (네이버 서버 부하 방지)
                await asyncio.sleep(1)

            await browser.close()

    except Exception as e:
        print_colored(f"❌ 네이버 검색 실패: {e}", "red")

    return blog_urls


async def crawl_blog_content(url: str) -> Optional[str]:
    """블로그 콘텐츠 크롤링"""
    try:
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
            return content

    except Exception as e:
        print_colored(f"❌ 크롤링 실패 ({url}): {e}", "red")
        return None


async def process_search_and_crawl(keyword: str, max_results: int = 10, max_pages: int = 3):
    """검색 및 크롤링 전체 프로세스"""
    print_colored("="*80, "blue")
    print_colored("네이버 블로그 검색 및 크롤링 파이프라인", "bold")
    print_colored("="*80, "blue")
    print()
    print_colored(f"검색 키워드: {keyword}", "white")
    print_colored(f"최대 결과 수: {max_results}", "white")
    print_colored(f"검색 페이지: {max_pages}페이지", "white")
    print()

    # 1단계: 네이버 블로그 검색
    print_colored("📍 1단계: 네이버 블로그 검색 중...", "yellow")
    blog_urls = await search_naver_blogs(keyword, max_results, max_pages)

    if not blog_urls:
        print_colored("❌ 검색 결과가 없습니다.", "red")
        return

    print_colored(f"✓ {len(blog_urls)}개의 블로그를 찾았습니다.", "green")
    print()

    # 2단계: 각 블로그 크롤링 및 저장
    print_colored("📍 2단계: 블로그 크롤링 및 데이터 저장 중...", "yellow")
    print()

    db_manager = SupabaseManager()
    success_count = 0
    fail_count = 0
    skip_count = 0

    for idx, url in enumerate(blog_urls, 1):
        print_colored(f"[{idx}/{len(blog_urls)}] {url}", "white")

        # 이미 저장된 URL인지 확인
        if db_manager.url_exists(url):
            print_colored(f"  ⊘ 이미 저장된 URL (건너뛰기)", "yellow")
            skip_count += 1
            continue

        # 크롤링
        content = await crawl_blog_content(url)
        if not content:
            print_colored(f"  ✗ 크롤링 실패", "red")
            fail_count += 1
            continue

        # 데이터 추출
        extracted_data = extract_structured_data(content)

        # yarn AND needle 둘 다 유효한 값이어야 함
        yarn_valid = extracted_data.get("yarn") and len(extracted_data.get("yarn", "")) > 1
        needle_valid = extracted_data.get("needle") and len(extracted_data.get("needle", "")) > 1

        if not yarn_valid or not needle_valid:
            print_colored(f"  ✗ 실과 바늘 정보 모두 필요 (yarn: {yarn_valid}, needle: {needle_valid})", "yellow")
            fail_count += 1
            continue

        # 저장
        record_id = db_manager.save_extraction(url, keyword, extracted_data)

        if record_id:
            yarn_preview = extracted_data.get('yarn', 'N/A')
            if yarn_preview and yarn_preview != 'N/A':
                yarn_preview = yarn_preview[:30] + "..."
            print_colored(f"  ✓ 저장 완료 (ID: {record_id}) - yarn: {yarn_preview}", "green")
            success_count += 1
        else:
            print_colored(f"  ✗ 저장 실패", "red")
            fail_count += 1

        # 네이버 서버 부하 방지를 위한 딜레이
        await asyncio.sleep(1)

    # 결과 요약
    print()
    print_colored("="*80, "blue")
    print_colored("처리 완료!", "bold")
    print_colored("="*80, "blue")
    print_colored(f"✓ 성공: {success_count}개", "green")
    print_colored(f"✗ 실패: {fail_count}개", "red")
    print_colored(f"⊘ 건너뛰기: {skip_count}개 (이미 저장됨)", "yellow")
    print_colored(f"총 {len(blog_urls)}개 중 {success_count}개 저장됨", "white")


def main() -> int:
    """메인 함수"""
    if len(sys.argv) < 2:
        print_colored("❌ 사용법 오류", "red")
        print()
        print("사용법:")
        print(f"  python {sys.argv[0]} <검색_키워드> [개수]")
        print()
        print("예시:")
        print(f"  python {sys.argv[0]} 마들렌자켓 10")
        return 1

    keyword = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    try:
        asyncio.run(process_search_and_crawl(keyword, max_results))
        return 0
    except KeyboardInterrupt:
        print()
        print_colored("\n⚠️  사용자에 의해 중단됨", "yellow")
        return 130
    except Exception as e:
        print()
        print_colored(f"❌ 오류 발생: {e}", "red")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
