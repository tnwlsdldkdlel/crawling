#!/usr/bin/env python3
"""
Supabase 데이터베이스 테이블 생성 스크립트

기존 스키마 + 원본 크롤링 데이터 저장 테이블 생성
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_config
from src.database import DatabaseManager


def create_all_tables(db_manager: DatabaseManager):
    """모든 테이블 생성"""

    print("="*80)
    print("Supabase 테이블 생성 시작")
    print("="*80)
    print()

    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:

            # ========================================
            # 1. 원본 크롤링 데이터 테이블
            # ========================================
            print("📦 1. raw_crawl_data 테이블 생성 중...")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_crawl_data (
                id SERIAL PRIMARY KEY,
                source_url TEXT NOT NULL,
                raw_content JSONB NOT NULL,
                extracted_sentence TEXT,
                keywords_found TEXT[],
                crawled_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT unique_source_url_crawled UNIQUE(source_url, crawled_at)
            );
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_crawl_source_url
            ON raw_crawl_data(source_url);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_crawl_crawled_at
            ON raw_crawl_data(crawled_at DESC);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_crawl_raw_content
            ON raw_crawl_data USING GIN(raw_content);
            """)

            print("   ✅ raw_crawl_data 테이블 생성 완료")
            print()

            # ========================================
            # 2. 정제된 실 정보 테이블
            # ========================================
            print("🧶 2. yarns 테이블 생성 중...")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS yarns (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                manufacturer TEXT,
                color TEXT,
                weight TEXT,
                amount TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT unique_yarn_name UNIQUE(name, manufacturer, color)
            );
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_yarns_name
            ON yarns(name);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_yarns_manufacturer
            ON yarns(manufacturer);
            """)

            print("   ✅ yarns 테이블 생성 완료")
            print()

            # ========================================
            # 3. 패턴 정보 테이블
            # ========================================
            print("📐 3. patterns 테이블 생성 중...")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT unique_pattern_name UNIQUE(name)
            );
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_patterns_name
            ON patterns(name);
            """)

            print("   ✅ patterns 테이블 생성 완료")
            print()

            # ========================================
            # 4. 패턴-실 연결 테이블
            # ========================================
            print("🔗 4. pattern_yarn_link 테이블 생성 중...")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS pattern_yarn_link (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                pattern_id UUID NOT NULL REFERENCES patterns(id) ON DELETE CASCADE,
                yarn_id UUID NOT NULL REFERENCES yarns(id) ON DELETE CASCADE,
                source_crawl_id INTEGER REFERENCES raw_crawl_data(id),
                created_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT unique_pattern_yarn_link UNIQUE(pattern_id, yarn_id, source_crawl_id)
            );
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern_yarn_pattern_id
            ON pattern_yarn_link(pattern_id);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern_yarn_yarn_id
            ON pattern_yarn_link(yarn_id);
            """)

            print("   ✅ pattern_yarn_link 테이블 생성 완료")
            print()

            # ========================================
            # 5. 정제된 크롤링 데이터 테이블
            # ========================================
            print("📊 5. processed_yarn_data 테이블 생성 중...")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_yarn_data (
                id SERIAL PRIMARY KEY,
                raw_data_id INTEGER NOT NULL REFERENCES raw_crawl_data(id) ON DELETE CASCADE,

                -- 정제된 필드들
                yarn_type TEXT,
                yarn_weight_value NUMERIC,
                yarn_weight_unit TEXT,
                yarn_amount_value NUMERIC,
                yarn_amount_unit TEXT,
                needle_sizes TEXT[],

                -- 연결된 마스터 데이터
                yarn_id UUID REFERENCES yarns(id),
                pattern_id UUID REFERENCES patterns(id),

                -- 메타데이터
                processing_status TEXT DEFAULT 'pending',
                processing_error TEXT,
                processing_version INTEGER DEFAULT 1,
                processed_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT unique_raw_data_id UNIQUE(raw_data_id)
            );
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed_raw_data_id
            ON processed_yarn_data(raw_data_id);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed_status
            ON processed_yarn_data(processing_status);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed_yarn_id
            ON processed_yarn_data(yarn_id);
            """)

            print("   ✅ processed_yarn_data 테이블 생성 완료")
            print()

            # ========================================
            # 6. 바늘 정보 테이블 (정규화)
            # ========================================
            print("🪡 6. needle_sizes 테이블 생성 중...")

            cur.execute("""
            CREATE TABLE IF NOT EXISTS needle_sizes (
                id SERIAL PRIMARY KEY,
                processed_data_id INTEGER NOT NULL REFERENCES processed_yarn_data(id) ON DELETE CASCADE,
                size_value NUMERIC NOT NULL,
                size_unit TEXT DEFAULT 'mm',
                needle_type TEXT,

                created_at TIMESTAMP DEFAULT NOW()
            );
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_needle_processed_data_id
            ON needle_sizes(processed_data_id);
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_needle_size_value
            ON needle_sizes(size_value);
            """)

            print("   ✅ needle_sizes 테이블 생성 완료")
            print()

            # Commit
            conn.commit()

            print("="*80)
            print("✅ 모든 테이블 생성 완료!")
            print("="*80)
            print()

            # 테이블 목록 출력
            print("📋 생성된 테이블 목록:")
            cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """)

            tables = cur.fetchall()
            for i, (table_name,) in enumerate(tables, 1):
                print(f"   {i}. {table_name}")

            print()


def drop_all_tables(db_manager: DatabaseManager):
    """모든 테이블 삭제 (주의!!)"""

    print("⚠️  WARNING: 모든 테이블을 삭제합니다!")
    print()

    response = input("정말 삭제하시겠습니까? (yes/no): ")

    if response.lower() != 'yes':
        print("취소되었습니다.")
        return

    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            print("\n🗑️  테이블 삭제 중...")

            # 역순으로 삭제 (외래키 때문에)
            tables = [
                "needle_sizes",
                "processed_yarn_data",
                "pattern_yarn_link",
                "patterns",
                "yarns",
                "raw_crawl_data"
            ]

            for table in tables:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                print(f"   ✅ {table} 삭제됨")

            conn.commit()
            print("\n✅ 모든 테이블이 삭제되었습니다.")


def show_schema(db_manager: DatabaseManager):
    """테이블 스키마 출력"""

    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:

            # 테이블 목록 조회
            cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
            """)

            tables = cur.fetchall()

            for (table_name,) in tables:
                print("="*80)
                print(f"📋 {table_name}")
                print("="*80)

                # 컬럼 정보 조회
                cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                ORDER BY ordinal_position;
                """, (table_name,))

                columns = cur.fetchall()

                for col_name, data_type, nullable, default in columns:
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"  - {col_name}: {data_type} {null_str}{default_str}")

                print()


def main():
    """메인 함수"""

    if len(sys.argv) < 2:
        print("사용법:")
        print("  python scripts/create_tables.py create   # 테이블 생성")
        print("  python scripts/create_tables.py drop     # 테이블 삭제")
        print("  python scripts/create_tables.py schema   # 스키마 보기")
        return 1

    command = sys.argv[1]

    try:
        # 설정 로드
        print("📡 Supabase 연결 중...")
        config = get_config()
        db_manager = DatabaseManager(config.database)

        # 연결 테스트
        with db_manager.get_connection():
            print("✅ 연결 성공!\n")

        # 명령 실행
        if command == "create":
            create_all_tables(db_manager)
        elif command == "drop":
            drop_all_tables(db_manager)
        elif command == "schema":
            show_schema(db_manager)
        else:
            print(f"❌ 알 수 없는 명령: {command}")
            return 1

        return 0

    except ValueError as e:
        print(f"\n❌ 설정 오류: {e}")
        print("\n.env 파일을 확인하세요:")
        print("  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        return 1

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
