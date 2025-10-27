#!/usr/bin/env python3
"""
Supabase 데이터베이스에 schema.sql을 적용하는 스크립트
"""
import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def apply_schema():
    """schema.sql 파일을 Supabase 데이터베이스에 적용"""
    # 데이터베이스 연결 정보
    conn_params = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', 5432),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
    }

    # schema.sql 파일 읽기
    schema_path = Path(__file__).parent / 'schema.sql'
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # 데이터베이스 연결 및 스키마 적용
    try:
        print(f"Connecting to database at {conn_params['host']}...")
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True

        with conn.cursor() as cur:
            print("Applying schema.sql...")
            cur.execute(schema_sql)
            print("✓ Schema applied successfully!")

            # 테이블 확인
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'blog_extractions'
            """)
            result = cur.fetchone()
            if result:
                print(f"✓ Table 'blog_extractions' created successfully!")
            else:
                print("⚠ Warning: Table not found after creation")

        conn.close()
        print("\nDone!")

    except psycopg2.Error as e:
        print(f"✗ Database error: {e}")
        raise
    except FileNotFoundError:
        print(f"✗ Error: schema.sql not found at {schema_path}")
        raise
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise

if __name__ == '__main__':
    apply_schema()
