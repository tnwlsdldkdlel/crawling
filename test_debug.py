#!/usr/bin/env python3
"""
디버깅용 크롤링 스크립트 - 실제 블로그 내용을 확인합니다.
"""

import sys
from scrapegraphai.graphs import SmartScraperGraph

def debug_crawl(url: str):
    """URL의 실제 텍스트 내용을 크롤링해서 보여줍니다."""

    print("="*80)
    print("블로그 텍스트 내용 확인 (디버그 모드)")
    print("="*80)
    print(f"\n대상 URL: {url}\n")

    # 간단한 프롬프트: 모든 텍스트 가져오기
    prompt = """
    Extract all the main text content from this blog post.
    Return it in JSON format:
    {
        "content": "all text content here"
    }
    """

    config = {
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

    print("🔍 블로그 콘텐츠 스크래핑 중...\n")

    try:
        scraper = SmartScraperGraph(
            prompt=prompt,
            source=url,
            config=config
        )

        result = scraper.run()

        if result and isinstance(result, dict):
            content = result.get("content", "")

            print("="*80)
            print("📄 추출된 텍스트 내용:")
            print("="*80)
            print(content[:2000])  # 처음 2000자만 출력

            if len(content) > 2000:
                print(f"\n... (총 {len(content)}자, 처음 2000자만 표시)")

            print("\n" + "="*80)
            print("🔍 키워드 검색 결과:")
            print("="*80)

            keywords = ["yarn", "실", "바늘", "사용실"]
            for keyword in keywords:
                if keyword in content:
                    print(f"✅ '{keyword}' 발견!")
                    # 해당 키워드 주변 텍스트 표시
                    idx = content.find(keyword)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + 50)
                    print(f"   컨텍스트: ...{content[start:end]}...")
                else:
                    print(f"❌ '{keyword}' 없음")

            print("="*80)
        else:
            print("❌ 결과를 가져오지 못했습니다.")
            print(f"Raw result: {result}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test_debug.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    debug_crawl(url)
