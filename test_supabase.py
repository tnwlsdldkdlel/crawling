"""
Supabase 연결 테스트 스크립트
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 환경 변수 로드
load_dotenv()

def test_supabase_connection():
    """Supabase 연결 테스트"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    print(f"🔗 Supabase URL: {url}")
    print(f"🔑 API Key: {key[:20]}...")

    try:
        # Supabase 클라이언트 생성
        supabase: Client = create_client(url, key)
        print("✅ Supabase 클라이언트 생성 성공")

        # 테이블 목록 조회 시도
        response = supabase.table("blog_extractions").select("*").limit(1).execute()
        print(f"✅ 테이블 조회 성공: {len(response.data)} rows")

        return supabase

    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("Supabase 연결 테스트")
    print("=" * 50)

    client = test_supabase_connection()

    if client:
        print("\n✅ 모든 테스트 통과!")
    else:
        print("\n❌ 연결 실패")
