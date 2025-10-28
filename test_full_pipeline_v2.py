#!/usr/bin/env python3
"""
완전한 파이프라인 v2: 크롤링 + LLM 구조화 + Supabase 저장

사용법:
    python test_full_pipeline_v2.py <네이버_블로그_URL>

예시:
    python test_full_pipeline_v2.py https://blog.naver.com/example-post
"""

import sys
import json
import asyncio
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from playwright.async_api import async_playwright
from supabase import create_client, Client
from dotenv import load_dotenv
import subprocess

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
            # 데이터 준비
            data = {
                "url": result.source_url,
                "extracted_sentence": result.extracted_data  # JSONB로 저장
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


def extract_with_llm(content: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Ollama의 Llama 3를 사용하여 블로그 콘텐츠에서 구조화된 데이터 추출

    Args:
        content: 블로그 본문 텍스트
        url: 블로그 URL

    Returns:
        구조화된 JSON 데이터 (도안, 실, 바늘 정보)
    """
    prompt = f"""다음은 뜨개질 블로그 포스트의 내용입니다. 이 내용에서 다음 정보를 추출하여 JSON 형식으로 반환해주세요.

추출할 정보:
- pattern: 도안 이름 또는 설명 (없으면 null)
- yarn: 실 정보 (제조사, 제품명, 색상 등, 없으면 null)
- needle: 바늘 정보 (크기, 종류 등, 없으면 null)
- project: 프로젝트 이름 또는 만든 작품 (없으면 null)
- date: 제작 날짜 또는 기간 (없으면 null)
- url: 원본 블로그 URL

응답은 반드시 유효한 JSON 형식이어야 하며, 다른 설명 없이 JSON만 반환하세요.

블로그 내용:
{content[:3000]}

URL: {url}

JSON 응답:"""

    try:
        # Ollama CLI를 통해 Llama 3 실행
        result = subprocess.run(
            ['ollama', 'run', 'llama3'],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            response_text = result.stdout.strip()

            # JSON 추출 (코드 블록이 있을 수 있음)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            # JSON 파싱
            extracted_data = json.loads(response_text)
            return extracted_data
        else:
            print_colored(f"⚠️  LLM 실행 실패: {result.stderr}", "yellow")
            return None

    except subprocess.TimeoutExpired:
        print_colored("⚠️  LLM 응답 타임아웃", "yellow")
        return None
    except json.JSONDecodeError as e:
        print_colored(f"⚠️  LLM 응답 JSON 파싱 실패: {e}", "yellow")
        print_colored(f"응답 내용: {result.stdout[:200]}", "yellow")
        return None
    except Exception as e:
        print_colored(f"⚠️  LLM 처리 중 오류: {e}", "yellow")
        return None


async def crawl_naver_blog(url: str) -> CrawlResult:
    """
    네이버 블로그에서 콘텐츠를 추출하고 LLM으로 구조화

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

            # LLM으로 구조화된 데이터 추출
            print_colored("🤖 LLM으로 데이터 구조화 중...", "yellow")
            extracted_data = extract_with_llm(content, url)

            if extracted_data:
                return CrawlResult(
                    extracted_data=extracted_data,
                    source_url=url,
                    success=True
                )
            else:
                return CrawlResult(
                    extracted_data=None,
                    source_url=url,
                    success=False,
                    error_message="LLM 데이터 추출 실패"
                )

    except Exception as e:
        return CrawlResult(
            extracted_data=None,
            source_url=url,
            success=False,
            error_message=f"크롤링 오류: {str(e)}"
        )


async def test_full_pipeline(url: str) -> None:
    """완전한 파이프라인 테스트: 크롤링 + LLM + DB 저장"""
    print_colored("="*80, "blue")
    print_colored("네이버 블로그 완전한 파이프라인 v2 테스트", "bold")
    print_colored("크롤링 → LLM 구조화 → Supabase 저장", "bold")
    print_colored("="*80, "blue")
    print()

    print_colored(f"대상 URL: {url}", "white")
    print()

    # 1단계: 크롤링 + LLM 구조화
    print_colored("📍 1단계: 콘텐츠 크롤링 및 LLM 구조화 중...", "yellow")
    result = await crawl_naver_blog(url)

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
        print_colored(f"추출된 데이터:", "green")
        print(json.dumps(result.extracted_data, ensure_ascii=False, indent=2))
        print_colored(f"\n데이터베이스 레코드 ID: {record_id}", "green")
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
