#!/usr/bin/env python3
"""
간단한 크롤링 테스트 스크립트

사용법:
    python test_crawling.py <네이버_블로그_URL>

예시:
    python test_crawling.py https://blog.naver.com/example-post
"""

import sys
import json
from typing import Optional

# src 모듈 임포트
from src.extractor import NaverBlogExtractor


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


def test_crawling(url: str) -> None:
    """
    단일 URL에서 크롤링 테스트 수행.

    Args:
        url: 테스트할 네이버 블로그 URL
    """
    print_colored("="*80, "blue")
    print_colored("네이버 블로그 AI 콘텐츠 추출 테스트", "bold")
    print_colored("="*80, "blue")
    print()

    print_colored(f"대상 URL: {url}", "white")
    print_colored("검색 단어: yarn, 실, 바늘, 사용실", "white")
    print()

    # Extractor 초기화 (커스텀 프롬프트 사용)
    print_colored("⏳ Llama 3.2 1B 모델 로딩 중...", "yellow")

    from scrapegraphai.graphs import SmartScraperGraph

    # 커스텀 프롬프트: 4개 단어 중 하나라도 포함된 문장 추출
    custom_prompt = """
    Find and extract the FIRST sentence that contains ANY of these terms:
    1. "yarn"
    2. "실" (Korean word for thread)
    3. "바늘" (Korean word for needle)
    4. "사용실" (Korean term for yarn/thread used)

    Return ONLY the complete sentence in JSON format with this structure:
    {
        "sentence": "the extracted sentence here",
        "found": true
    }

    If no sentence contains any of these terms, return:
    {
        "sentence": null,
        "found": false
    }
    """

    # ScrapeGraphAI 설정
    graph_config = {
        "llm": {
            "model": "ollama/llama3.2:1b",
            "temperature": 0.0,
            "format": "json",
        },
        "embeddings": {
            "model": "ollama/llama3.2:1b",
        },
        "headless": True,
        "verbose": False,
    }

    # 크롤링 수행
    print_colored("🔍 콘텐츠 추출 중...", "yellow")

    try:
        smart_scraper = SmartScraperGraph(
            prompt=custom_prompt,
            source=url,
            config=graph_config
        )

        raw_result = smart_scraper.run()

        # 결과 파싱
        from src.extractor import ExtractionResult

        if raw_result and isinstance(raw_result, dict):
            found = raw_result.get("found", False)
            sentence = raw_result.get("sentence")

            if found and sentence:
                result = ExtractionResult(
                    extracted_sentence=sentence,
                    source_url=url,
                    success=True
                )
            else:
                result = ExtractionResult(
                    extracted_sentence=None,
                    source_url=url,
                    success=False,
                    error_message="No sentence containing any of the search terms found"
                )
        else:
            result = ExtractionResult(
                extracted_sentence=None,
                source_url=url,
                success=False,
                error_message="Invalid extraction result format"
            )
    except Exception as e:
        result = ExtractionResult(
            extracted_sentence=None,
            source_url=url,
            success=False,
            error_message=f"Extraction error: {str(e)}"
        )

    print()
    print_colored("="*80, "blue")
    print_colored("📊 추출 결과 (JSON)", "bold")
    print_colored("="*80, "blue")
    print()

    # JSON 결과 출력
    json_str = result.to_json()
    print(json_str)
    print()

    # 결과 요약
    print_colored("="*80, "blue")
    if result.success:
        print_colored("✅ 성공!", "green")
        print_colored(f"추출된 문장: {result.extracted_sentence}", "green")
    else:
        print_colored("❌ 실패", "red")
        print_colored(f"오류: {result.error_message}", "red")
    print_colored("="*80, "blue")


def main() -> int:
    """메인 함수."""
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

    # URL 검증 (간단한 체크)
    if not url.startswith("http"):
        print_colored("⚠️  경고: 유효한 URL이 아닐 수 있습니다.", "yellow")
        print()

    try:
        test_crawling(url)
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
