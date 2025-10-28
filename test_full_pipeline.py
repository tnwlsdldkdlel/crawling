#!/usr/bin/env python3
"""
완전한 파이프라인 테스트: 크롤링 + Supabase 저장

사용법:
    python test_full_pipeline.py <네이버_블로그_URL>

예시:
    python test_full_pipeline.py https://blog.naver.com/example-post
"""

import sys
import json
import asyncio
import os
from typing import Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from playwright.async_api import async_playwright
from supabase import create_client, Client
from dotenv import load_dotenv


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


@dataclass
class CrawlResult:
    """크롤링 결과 데이터 클래스"""
    extracted_sentence: Optional[str]
    source_url: str
    success: bool
    error_message: Optional[str] = None
    keywords_found: Optional[List[str]] = None

    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


class SupabaseManager:
    """Supabase 데이터베이스 관리자"""

    def __init__(self):
        """환경 변수에서 Supabase 클라이언트 설정 로드"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL 및 SUPABASE_KEY 환경 변수가 필요합니다")

        self.client: Client = create_client(supabase_url, supabase_key)

    def save_extraction(self, result: CrawlResult) -> Optional[int]:
        """추출 결과를 Supabase에 저장"""
        try:
            # 데이터 준비
            data = {
                "url": result.source_url,
                "extracted_sentence": result.extracted_sentence,
                "keywords": result.keywords_found if result.keywords_found else []
            }

            # Supabase에 삽입
            response = self.client.table("blog_extractions").insert(data).execute()

            if response.data and len(response.data) > 0:
                record_id = response.data[0].get('id')
                print_colored(f"✅ 데이터베이스에 저장됨 (ID: {record_id})", "green")
                return record_id
            else:
                print_colored("❌ 데이터베이스 저장 실패: 응답 데이터 없음", "red")
                return None

        except Exception as e:
            print_colored(f"❌ 데이터베이스 저장 실패: {e}", "red")
            return None


async def crawl_naver_blog(url: str, keywords: List[str]) -> CrawlResult:
    """
    네이버 블로그에서 키워드를 포함한 문장 추출.

    Args:
        url: 네이버 블로그 URL
        keywords: 검색할 키워드 리스트

    Returns:
        CrawlResult 객체
    """
    try:
        async with async_playwright() as p:
            # 브라우저 실행
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 페이지 로드
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # 네이버 블로그는 iframe 사용 - iframe 내부 콘텐츠 가져오기
            content = ""
            frames = page.frames

            for frame in frames:
                try:
                    # 메인 프레임 찾기
                    if "mainFrame" in frame.url or "PostView" in frame.url:
                        content = await frame.inner_text("body")
                        break
                except:
                    continue

            # iframe에서 못 찾으면 메인 페이지에서 가져오기
            if not content:
                content = await page.inner_text("body")

            await browser.close()

            # 키워드 검색
            found_keywords = []
            sentences_with_keywords = []

            # 콘텐츠를 문장 단위로 분리 (간단한 방식)
            sentences = content.replace("\n", " ").split(". ")

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # 이 문장에 포함된 키워드 찾기
                keywords_in_sentence = [kw for kw in keywords if kw in sentence]

                if keywords_in_sentence:
                    found_keywords.extend(keywords_in_sentence)
                    sentences_with_keywords.append({
                        "sentence": sentence,
                        "keywords": keywords_in_sentence
                    })

            # 결과 생성
            if sentences_with_keywords:
                # 가장 많은 키워드를 포함한 문장 선택
                best_match = max(
                    sentences_with_keywords,
                    key=lambda x: len(x["keywords"])
                )

                return CrawlResult(
                    extracted_sentence=best_match["sentence"],
                    source_url=url,
                    success=True,
                    keywords_found=list(set(found_keywords))
                )
            else:
                return CrawlResult(
                    extracted_sentence=None,
                    source_url=url,
                    success=False,
                    error_message=f"키워드를 포함한 문장을 찾지 못했습니다: {', '.join(keywords)}",
                    keywords_found=[]
                )

    except Exception as e:
        return CrawlResult(
            extracted_sentence=None,
            source_url=url,
            success=False,
            error_message=f"크롤링 오류: {str(e)}"
        )


async def test_full_pipeline(url: str, keywords: List[str]) -> None:
    """완전한 파이프라인 테스트: 크롤링 + DB 저장"""
    print_colored("="*80, "blue")
    print_colored("네이버 블로그 완전한 파이프라인 테스트", "bold")
    print_colored("크롤링 → Supabase 저장", "bold")
    print_colored("="*80, "blue")
    print()

    print_colored(f"대상 URL: {url}", "white")
    print_colored(f"검색 키워드: {', '.join(keywords)}", "white")
    print()

    # 1단계: 크롤링
    print_colored("📍 1단계: 콘텐츠 추출 중...", "yellow")
    result = await crawl_naver_blog(url, keywords)

    print()
    print_colored("="*80, "blue")
    print_colored("📊 추출 결과 (JSON)", "bold")
    print_colored("="*80, "blue")
    print()
    print(result.to_json())
    print()

    # 2단계: Supabase 저장
    print_colored("📍 2단계: Supabase에 저장 중...", "yellow")
    db_manager = SupabaseManager()
    record_id = db_manager.save_extraction(result)

    print()
    print_colored("="*80, "blue")

    if result.success and record_id:
        print_colored("✅ 파이프라인 완료!", "green")
        print_colored(f"추출된 문장: {result.extracted_sentence}", "green")
        if result.keywords_found:
            print_colored(f"발견된 키워드: {', '.join(result.keywords_found)}", "green")
        print_colored(f"데이터베이스 레코드 ID: {record_id}", "green")
    elif not result.success:
        print_colored("❌ 크롤링 실패", "red")
        print_colored(f"오류: {result.error_message}", "red")
    else:
        print_colored("⚠️  크롤링 성공, DB 저장 실패", "yellow")

    print_colored("="*80, "blue")


def main() -> int:
    """메인 함수"""
    if len(sys.argv) < 2:
        print_colored("❌ 사용법 오류", "red")
        print()
        print("사용법:")
        print(f"  python {sys.argv[0]} <네이버_블로그_URL>")
        print()
        print("예시:")
        print(f"  python {sys.argv[0]} https://blog.naver.com/example-post")
        return 1

    url = sys.argv[1]

    # URL 검증
    if not url.startswith("http"):
        print_colored("⚠️  경고: 유효한 URL이 아닐 수 있습니다.", "yellow")
        print()

    # 검색 키워드 설정
    keywords = ["yarn", "실", "바늘", "사용실"]

    try:
        asyncio.run(test_full_pipeline(url, keywords))
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
