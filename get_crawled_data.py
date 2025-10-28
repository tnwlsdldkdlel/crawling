#!/usr/bin/env python3
"""
Supabase에서 크롤링된 데이터를 JSON으로 조회
"""
import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_crawled_data(url: str = None):
    """Supabase에서 크롤링된 데이터 조회"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    client: Client = create_client(supabase_url, supabase_key)

    # URL로 필터링하거나 전체 조회
    if url:
        response = client.table("blog_extractions").select("*").eq("url", url).execute()
    else:
        response = client.table("blog_extractions").select("*").execute()

    # JSON 형식으로 출력
    if response.data:
        print(json.dumps(response.data, ensure_ascii=False, indent=2))
        return response.data
    else:
        print("데이터를 찾을 수 없습니다.")
        return None

if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else None
    get_crawled_data(url)
