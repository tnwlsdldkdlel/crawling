#!/usr/bin/env python3
"""
완전한 파이프라인 v3: 크롤링 + 패턴 추출 + Supabase 저장

사용법:
    python test_full_pipeline_v3.py <네이버_블로그_URL>

예시:
    python test_full_pipeline_v3.py https://blog.naver.com/example-post
"""

import sys
import json
import asyncio
import os
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
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
    extracted_data: Optional[Dict[str, Any]]
    source_url: str
    success: bool
    error_message: Optional[str] = None

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
            # keyword 분리 (project -> keyword)
            keyword = result.extracted_data.get("project") if result.extracted_data else None

            # extracted_sentence에서 project 제거
            extracted_sentence = result.extracted_data.copy() if result.extracted_data else {}
            if "project" in extracted_sentence:
                del extracted_sentence["project"]

            # 데이터 준비
            data = {
                "url": result.source_url,
                "keyword": keyword,
                "extracted_sentence": extracted_sentence  # JSONB로 저장
            }

            # Supabase에 삽입 (중복 URL은 업데이트)
            response = self.client.table("extractions").upsert(
                data,
                on_conflict="url"
            ).execute()

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


def extract_structured_data(content: str, url: str) -> Dict[str, Any]:
    """
    블로그 콘텐츠에서 구조화된 데이터 추출 (정규표현식 기반)

    Args:
        content: 블로그 본문 텍스트
        url: 블로그 URL

    Returns:
        구조화된 JSON 데이터
    """
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

            # 불필요한 제목/태그 제거 ([...], 뜨개일기, 마들렌 자켓 등)
            yarn_text = re.sub(r'\[.*?\]', '', yarn_text)  # [뜨개일기] 등 제거
            yarn_text = re.sub(r'뜨개일기', '', yarn_text)
            yarn_text = re.sub(r'수민님?\s*', '', yarn_text)
            yarn_text = re.sub(r'마들렌\s*자?켓', '', yarn_text)
            yarn_text = re.sub(r'cardigan|자켓|조끼|가디건|베스트|스웨터', '', yarn_text, flags=re.IGNORECASE)

            # 괄호 내용만 추출 시도 (실 정보가 괄호 안에 있는 경우)
            paren_match = re.search(r'\(([^)]+)\)', yarn_text)
            if paren_match:
                yarn_text = paren_match.group(1).strip()

            # mm 정보 제거 (바늘 정보이므로)
            yarn_text = re.sub(r'\s*\d+\.?\d*\s*mm.*', '', yarn_text).strip()

            # 앞뒤 공백 및 특수문자 정리
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


async def crawl_naver_blog(url: str) -> CrawlResult:
    """
    네이버 블로그에서 콘텐츠를 추출하고 구조화

    Args:
        url: 네이버 블로그 URL

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

            # 구조화된 데이터 추출
            print_colored("📝 데이터 구조화 중...", "yellow")
            extracted_data = extract_structured_data(content, url)

            # yarn AND needle 둘 다 유효한 값이어야 함
            yarn_valid = extracted_data.get("yarn") and len(extracted_data.get("yarn", "")) > 1
            needle_valid = extracted_data.get("needle") and len(extracted_data.get("needle", "")) > 1

            if extracted_data and yarn_valid and needle_valid:
                return CrawlResult(
                    extracted_data=extracted_data,
                    source_url=url,
                    success=True
                )
            else:
                return CrawlResult(
                    extracted_data=extracted_data,
                    source_url=url,
                    success=False,
                    error_message=f"실과 바늘 정보 모두 필요 (yarn: {yarn_valid}, needle: {needle_valid})"
                )

    except Exception as e:
        return CrawlResult(
            extracted_data=None,
            source_url=url,
            success=False,
            error_message=f"크롤링 오류: {str(e)}"
        )


async def test_full_pipeline(url: str) -> None:
    """완전한 파이프라인 테스트: 크롤링 + 구조화 + DB 저장"""
    print_colored("="*80, "blue")
    print_colored("네이버 블로그 완전한 파이프라인 v3 테스트", "bold")
    print_colored("크롤링 → 패턴 추출 → Supabase 저장", "bold")
    print_colored("="*80, "blue")
    print()

    print_colored(f"대상 URL: {url}", "white")
    print()

    # 1단계: 크롤링 + 구조화
    print_colored("📍 1단계: 콘텐츠 크롤링 및 구조화 중...", "yellow")
    result = await crawl_naver_blog(url)

    print()
    print_colored("="*80, "blue")
    print_colored("📊 추출 결과 (JSON)", "bold")
    print_colored("="*80, "blue")
    print()
    if result.extracted_data:
        print(json.dumps(result.extracted_data, ensure_ascii=False, indent=2))
    else:
        print(result.to_json())
    print()

    # 2단계: Supabase 저장
    if result.success:
        print_colored("📍 2단계: Supabase에 저장 중...", "yellow")
        db_manager = SupabaseManager()
        record_id = db_manager.save_extraction(result)

        print()
        print_colored("="*80, "blue")

        if record_id:
            print_colored("✅ 파이프라인 완료!", "green")
            print_colored(f"\n추출된 데이터:", "green")
            print(json.dumps(result.extracted_data, ensure_ascii=False, indent=2))
            print_colored(f"\n데이터베이스 레코드 ID: {record_id}", "green")
        else:
            print_colored("⚠️  크롤링 성공, DB 저장 실패", "yellow")
    else:
        print_colored("="*80, "blue")
        print_colored("❌ 크롤링 실패", "red")
        print_colored(f"오류: {result.error_message}", "red")

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

    try:
        asyncio.run(test_full_pipeline(url))
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
