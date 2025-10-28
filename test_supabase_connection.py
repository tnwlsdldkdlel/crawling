#!/usr/bin/env python3
"""
Supabase 연결 테스트 스크립트
"""
import os
from dotenv import load_dotenv
import psycopg2
from supabase import create_client, Client

def test_postgres_connection():
    """PostgreSQL 직접 연결 테스트"""
    print("=" * 60)
    print("PostgreSQL 연결 테스트")
    print("=" * 60)

    try:
        load_dotenv()

        # 연결 정보
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")

        print(f"연결 대상: {db_user}@{db_host}:{db_port}/{db_name}")

        # PostgreSQL 연결
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )

        print("✓ PostgreSQL 연결 성공!")

        # 버전 확인
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL 버전: {version[:50]}...")

        # 테이블 목록 확인
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        print(f"\n✓ public 스키마의 테이블 ({len(tables)}개):")
        for table in tables:
            print(f"  - {table[0]}")

        # blog_extractions 테이블 상세 정보
        if any(t[0] == 'blog_extractions' for t in tables):
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'blog_extractions'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()

            print(f"\n✓ blog_extractions 테이블 스키마:")
            for col_name, data_type, nullable in columns:
                null_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"  - {col_name}: {data_type} ({null_str})")

            # 레코드 개수 확인
            cursor.execute("SELECT COUNT(*) FROM blog_extractions;")
            count = cursor.fetchone()[0]
            print(f"\n✓ blog_extractions 레코드 수: {count}개")

        cursor.close()
        conn.close()

        print("\n✓ PostgreSQL 연결 테스트 완료!")
        return True

    except Exception as e:
        print(f"\n✗ PostgreSQL 연결 실패: {e}")
        return False


def test_supabase_client():
    """Supabase 클라이언트 연결 테스트"""
    print("\n" + "=" * 60)
    print("Supabase 클라이언트 연결 테스트")
    print("=" * 60)

    try:
        load_dotenv()

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        print(f"연결 대상: {supabase_url}")

        # Supabase 클라이언트 생성
        supabase: Client = create_client(supabase_url, supabase_key)

        print("✓ Supabase 클라이언트 생성 성공!")

        # 간단한 쿼리 테스트
        response = supabase.table("blog_extractions").select("*").limit(1).execute()

        print(f"✓ 쿼리 실행 성공! (레코드 수: {len(response.data)})")

        if response.data:
            print(f"\n첫 번째 레코드 샘플:")
            print(f"  ID: {response.data[0].get('id', 'N/A')}")
            print(f"  URL: {response.data[0].get('url', 'N/A')[:50]}...")
            print(f"  생성일: {response.data[0].get('created_at', 'N/A')}")

        print("\n✓ Supabase 클라이언트 테스트 완료!")
        return True

    except Exception as e:
        print(f"\n✗ Supabase 클라이언트 연결 실패: {e}")
        return False


if __name__ == "__main__":
    print("\n🔍 Supabase 연결 테스트 시작...\n")

    # PostgreSQL 직접 연결 테스트
    pg_success = test_postgres_connection()

    # Supabase 클라이언트 테스트
    client_success = test_supabase_client()

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"PostgreSQL 연결: {'✓ 성공' if pg_success else '✗ 실패'}")
    print(f"Supabase 클라이언트: {'✓ 성공' if client_success else '✗ 실패'}")

    if pg_success and client_success:
        print("\n🎉 모든 연결 테스트 통과!")
    else:
        print("\n⚠️  일부 연결 테스트 실패")
